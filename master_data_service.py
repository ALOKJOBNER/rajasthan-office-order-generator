"""
Master Data Service - Step 8
Backward-compatible application service for Master Data retrieval.
Adds purpose-based read-only resolution for Sanchalan without changing
Master Data definitions or records.
"""
from __future__ import annotations
from copy import deepcopy
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from master_data import (
    PAY_COMMISSION_MASTER_NAME,
    PAY_COMMISSION_MASTER_DESCRIPTION,
    SYSTEM_MASTER,
    MasterDefinitionStore,
    normalize_username,
)

SERVICE_VERSION = "1.5.0"


class MasterDataService:
    def __init__(self, username: str, *, ensure_system_master: bool = False):
        self.username = normalize_username(username)
        self.store = MasterDefinitionStore(self.username)
        # Every new user receives only blank user-master definitions.
        # Records are NEVER copied from another user.
        self.ensure_user_master_templates()
        # Employee Master explicitly stores Pay Commission. Existing records are
        # migrated from their existing pay structure: Pay Level => 7th CPC;
        # Pay Band/Grade Pay => 6th CPC. The field is optional so genuinely
        # unknown legacy records are not guessed.
        self.ensure_employee_pay_commission_field()

    @staticmethod
    def _norm(value: Any) -> str:
        return " ".join(str(value or "").strip().casefold().split())

    def list_masters(self, include_system: bool = True) -> List[Dict[str, Any]]:
        masters = self.store.list_masters() if hasattr(self.store, "list_masters") else []
        if include_system:
            return deepcopy(masters)
        return [deepcopy(m) for m in masters if m.get("owner_type") != SYSTEM_MASTER]

    def get_master(self, master_id: str) -> Optional[Dict[str, Any]]:
        master = self.store.get_master(master_id)
        return deepcopy(master) if master else None

    def get_master_by_name(self, master_name: str) -> Optional[Dict[str, Any]]:
        master = self.store.get_master_by_name(master_name)
        return deepcopy(master) if master else None

    def ensure_user_master_templates(self) -> List[str]:
        """Create missing standard User Master definitions with blank records.

        Definitions/fields come from the checked-in schema template only.
        No records from Admin or any other user are copied. Existing user
        masters and their records are never overwritten.
        Pay Commission Master is deliberately excluded because it is universal.
        """
        template_path = Path(__file__).resolve().parent / "user_master_templates.json"
        if not template_path.exists():
            return []
        try:
            payload = json.loads(template_path.read_text(encoding="utf-8"))
        except Exception:
            return []
        changed = []
        for template in payload.get("masters", []):
            name = str(template.get("master_name") or "").strip()
            if not name or self._norm(name) == self._norm(PAY_COMMISSION_MASTER_NAME):
                continue
            if self.store.get_master_by_name(name):
                continue
            master = self.store.create_master(name, str(template.get("description") or ""))
            for field in template.get("fields", []):
                self.store.add_field(
                    master["master_id"],
                    str(field.get("field_name") or "").strip(),
                    str(field.get("field_type") or "text"),
                    bool(field.get("required", False)),
                    bool(field.get("active", True)),
                    list(field.get("options") or []),
                    str(field.get("description") or ""),
                )
            changed.append(name)
        return changed

    def _universal_pay_commission_path(self) -> Path:
        return Path(__file__).resolve().parent / "output" / "universal_pay_commission_master.json"

    def sync_universal_pay_commission(self, master: Optional[Dict[str, Any]] = None, records: Optional[List[Dict[str, Any]]] = None) -> None:
        """Persist the Administrator's approved Pay Commission changes to the
        single universal read-only source used by all normal users."""
        if str(self.username).strip().lower() == "":
            raise ValueError("Username आवश्यक है।")
        master = master or self.store.get_master_by_name(PAY_COMMISSION_MASTER_NAME)
        if not master:
            raise ValueError("Pay Commission Master उपलब्ध नहीं है।")
        payload = {
            "version": "1.0.0",
            "master_name": PAY_COMMISSION_MASTER_NAME,
            "description": PAY_COMMISSION_MASTER_DESCRIPTION,
            "locked": True,
            "fields": deepcopy(master.get("fields", [])),
            "records": deepcopy(records if records is not None else self.store.load_records(master["master_id"])),
        }
        path = self._universal_pay_commission_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def _load_universal_pay_commission(self) -> Optional[Dict[str, Any]]:
        path = self._universal_pay_commission_path()
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(data, dict) or not data.get("records"):
                return None
            return data
        except Exception:
            return None

    def get_pay_commission_master(self) -> Optional[Dict[str, Any]]:
        # User accounts never receive a visible/local Pay Commission Master.
        # They read the single universal, locked source.
        universal = self._load_universal_pay_commission()
        if universal:
            return {
                "master_id": "SYSTEM-PAY-COMMISSION",
                "master_name": PAY_COMMISSION_MASTER_NAME,
                "owner_type": SYSTEM_MASTER,
                "status": "active",
                "fields": deepcopy(universal.get("fields", [])),
                "_universal_records": deepcopy(universal.get("records", [])),
            }
        # Backward-compatible fallback for an installation that still has
        # the protected master in the current user's store.
        master = self.get_master_by_name(PAY_COMMISSION_MASTER_NAME)
        if master:
            return master
        return {
            "master_id": "SYSTEM-PAY-COMMISSION",
            "master_name": PAY_COMMISSION_MASTER_NAME,
            "owner_type": SYSTEM_MASTER,
            "status": "active",
            "fields": [],
            "_universal_records": [],
        }


    def get_employee_master(self) -> Optional[Dict[str, Any]]:
        """Return the user's Employee Master Data definition."""
        return self.resolve_master_by_purpose("staff")

    def ensure_employee_pay_commission_field(self) -> bool:
        """Add and populate the explicit Pay Commission field in Employee Master.

        This is an idempotent compatibility migration. It does not overwrite an
        already populated employee Pay Commission value. Legacy records are
        populated only when their existing Pay Level or Pay Band/Grade Pay makes
        the commission unambiguous.
        """
        master = self.resolve_master_by_purpose("staff")
        if not master or self.store.is_system_master(master.get("master_id")):
            return False
        fields = {self._norm(f.get("field_name")): f for f in master.get("fields", [])}
        field = fields.get(self._norm("Pay Commission"))
        changed = False
        if not field:
            field = self.store.add_field(
                master["master_id"],
                "Pay Commission",
                "dropdown",
                False,
                True,
                ["5th Pay Commission", "6th Pay Commission", "7th Pay Commission"],
                "कर्मचारी का लागू वेतन आयोग। Pay Level होने पर सामान्यतः 7th CPC तथा Pay Band/Grade Pay होने पर 6th CPC।"
            )
            changed = True
        else:
            desired = ["5th Pay Commission", "6th Pay Commission", "7th Pay Commission"]
            if field.get("field_type") != "dropdown" or field.get("options") != desired or not field.get("active", True):
                self.store.update_field(
                    master["master_id"], field["field_id"], field_type="dropdown",
                    active=True, options=desired,
                    description="कर्मचारी का लागू वेतन आयोग। Pay Level होने पर सामान्यतः 7th CPC तथा Pay Band/Grade Pay होने पर 6th CPC।"
                )
                changed = True

        records = self.store.load_records(master["master_id"])
        fid = field.get("field_id")
        pay_level_f = next((f.get("field_id") for f in master.get("fields", []) if self._norm(f.get("field_name")) in {self._norm("Pay Level"), self._norm("पे लेवल")}), None)
        pay_band_f = next((f.get("field_id") for f in master.get("fields", []) if self._norm(f.get("field_name")) in {self._norm("Pay Band"), self._norm("Pay Band (6th CPC)"), self._norm("वेतन बैंड")}), None)
        grade_pay_f = next((f.get("field_id") for f in master.get("fields", []) if self._norm(f.get("field_name")) in {self._norm("Grade Pay"), self._norm("ग्रेड पे")}), None)
        for rec in records:
            current = str(rec.get(fid) or "").strip()
            if current:
                continue
            level = str(rec.get(pay_level_f) or "").strip() if pay_level_f else ""
            band = str(rec.get(pay_band_f) or "").strip() if pay_band_f else ""
            gp = str(rec.get(grade_pay_f) or "").strip() if grade_pay_f else ""
            inferred = "7th Pay Commission" if level else "6th Pay Commission" if (band or gp) else ""
            if inferred:
                rec[fid] = inferred
                rec["_updated_at"] = __import__('datetime').datetime.now().isoformat(timespec='seconds')
                changed = True
        if changed:
            self.store.save_records(master["master_id"], records)
        return changed

    def get_employee_records(self, active_only: bool = True) -> List[Dict[str, Any]]:
        master = self.get_employee_master()
        if not master:
            return []
        return self.get_records(master["master_id"], active_only=active_only)

    def get_employee_rows(self, active_only: bool = True) -> List[Dict[str, Any]]:
        master = self.get_employee_master()
        if not master:
            return []
        return self.get_rows(master["master_id"], active_only=active_only)

    def employee_value(self, row: Dict[str, Any], aliases: Iterable[str]) -> Any:
        normalized = [self._norm(a) for a in aliases]
        for key, value in row.items():
            if self._norm(key) in normalized:
                return value
        return ""

    def employee_catalog(self) -> List[Dict[str, Any]]:
        """Flatten Employee Master rows into stable module-facing values."""
        rows = self.get_employee_rows(active_only=True)
        out=[]
        for row in rows:
            name=self.employee_value(row,["Employee Name","कर्मचारी का नाम"])
            if not str(name).strip():
                continue
            raw_level=self.employee_value(row,["Pay Level","पे लेवल"])
            level_text=str(raw_level or "").strip().upper().replace("–","-").replace(" ","")
            if level_text.startswith("L") and not level_text.startswith("L-") and level_text[1:].isdigit():
                level_text="L-"+level_text[1:]
            out.append({
                "_record_id": row.get("_record_id",""),
                "employee_name": name,
                "employee_id": self.employee_value(row,["Employee ID","Employee Code","कर्मचारी आईडी"]),
                "designation": self.employee_value(row,["Designation","पद"]),
                "basic_pay": self.employee_value(row,["Basic Pay","मूल वेतन"]),
                "pay_commission": self.employee_value(row,["Pay Commission","वेतन आयोग","Pay Commission Name"]),
                "pay_level": level_text,
                "pay_band": self.employee_value(row,["Pay Band","Pay Band (6th CPC)","वेतन बैंड"]),
                "grade_pay": self.employee_value(row,["Grade Pay","ग्रेड पे"]),
                "gpf_pran": self.employee_value(row,["GPF / PRAN Number","GPF Number","PRAN Number"]),
                "pan": self.employee_value(row,["PAN Number","PAN"]),
                "mobile": self.employee_value(row,["Mobile Number","Mobile","मोबाइल"]),
                "bank_name": self.employee_value(row,["Bank Name","बैंक नाम"]),
                "account": self.employee_value(row,["Account Number","Account No","Bank Account"]),
                "ifsc": self.employee_value(row,["IFSC","IFSC Code"]),
                "appointment_date": self.employee_value(row,["Appointment Date","नियुक्ति दिनांक"]),
                "joining_date": self.employee_value(row,["Joining Date","कार्यग्रहण दिनांक"]),
            })
        return out

    def pay_commission_records(self, commission: Optional[str] = None, record_type: Optional[str] = None) -> List[Dict[str, Any]]:
        master = self.get_pay_commission_master()
        if not master or not master.get("master_id"):
            return []
        records = self.get_records(master["master_id"], active_only=True)
        fields = {f.get("field_id"): f.get("field_name") for f in master.get("fields", [])}
        rows=[]
        for rec in records:
            row={fields.get(fid,fid): val for fid,val in rec.items() if fid in fields}
            if commission and self._norm(row.get("pay_commission")) != self._norm(commission):
                continue
            if record_type and self._norm(row.get("record_type")) != self._norm(record_type):
                continue
            rows.append(row)
        return rows

    def pay_structure(self, commission: str) -> List[Dict[str, Any]]:
        return self.pay_commission_records(commission, "PAY_STRUCTURE")

    def da_rates(self, commission: str) -> List[Dict[str, Any]]:
        return self.pay_commission_records(commission, "DA_RATE") + self.pay_commission_records(commission, "DA_RATE_OPTION")


    def update_da_rate(self, commission: str, effective_date: str, da_rate: float, *, cash_da_rate=None, gpf_credit=None) -> Dict[str, Any]:
        """Controlled module update for the locked Pay Commission Master DA table.

        The universal master remains locked for normal user CRUD/import, but approved
        module workflows (such as PL Surrender) may update a DA rate through this
        audited service method.
        """
        master = self.get_pay_commission_master()
        if not master or not master.get("master_id"):
            raise ValueError("Pay Commission Master उपलब्ध नहीं है।")
        fields = {str(f.get("field_name", "")).strip(): f.get("field_id") for f in master.get("fields", [])}
        def fid(name):
            return fields.get(name)
        records = self.store.load_records(master["master_id"])
        target = None
        for rec in records:
            vals = {name: rec.get(fid(name)) for name in fields if fid(name)}
            if self._norm(vals.get("record_type")) in {"da_rate", "da_rate_option"} and self._norm(vals.get("pay_commission")) == self._norm(commission) and str(vals.get("effective_date") or "")[:10] == str(effective_date)[:10]:
                target = rec
                break
        if target is None:
            target = {"_record_id": f"REC-DA-{str(commission).replace(' ', '_')}-{str(effective_date)[:10]}", "_created_at": __import__('datetime').datetime.now().isoformat(timespec='seconds')}
            target[fid("record_type")] = "DA_RATE"
            target[fid("pay_commission")] = commission
            target[fid("effective_date")] = str(effective_date)[:10]
            records.append(target)
        target[fid("da_rate")] = float(da_rate)
        if fid("cash_da_rate"):
            target[fid("cash_da_rate")] = float(da_rate if cash_da_rate is None else cash_da_rate)
        if fid("gpf_credit") and gpf_credit is not None:
            target[fid("gpf_credit")] = bool(gpf_credit)
        target["_updated_at"] = __import__('datetime').datetime.now().isoformat(timespec='seconds')
        self.store.save_records(master["master_id"], records)
        return self.record_to_row(master["master_id"], target)

    def hra_rates(self, commission: str) -> List[Dict[str, Any]]:
        return self.pay_commission_records(commission, "HRA_RATE")

    def da_rule_tuples(self, commission: str) -> List[tuple]:
        rows = self.da_rates(commission)
        out=[]
        for row in rows:
            d=str(row.get("effective_date") or "")
            try:
                parts=d[:10].split("-"); key=(int(parts[0]),int(parts[1]))
                due=float(row.get("da_rate") or 0); cash=float(row.get("cash_da_rate") if row.get("cash_da_rate") not in (None,"") else due)
                gpf=bool(row.get("gpf_credit",False))
                out.append((key,due,cash,gpf))
            except Exception:
                continue
        return sorted(out,key=lambda x:x[0])

    def hra_rule_tuples(self, commission: str) -> List[tuple]:
        rows=self.hra_rates(commission); out=[]
        for row in rows:
            try:
                d=str(row.get("effective_date") or "")[:10].split("-")
                out.append(((int(d[0]),int(d[1])),str(row.get("city_class") or ""),float(row.get("hra_rate") or 0)))
            except Exception:
                continue
        return sorted(out,key=lambda x:x[0])

    def infer_employee_commission(self, employee: Dict[str, Any]) -> str:
        explicit = str(employee.get("pay_commission", "")).strip()
        if explicit:
            return explicit
        if str(employee.get("pay_level", "")).strip():
            return "7th Pay Commission"
        if str(employee.get("pay_band", "")).strip() or str(employee.get("grade_pay", "")).strip():
            return "6th Pay Commission"
        return "7th Pay Commission"

    def get_master_metadata(self, master_name: str) -> Optional[Dict[str, Any]]:
        if self._norm(master_name) == self._norm(PAY_COMMISSION_MASTER_NAME):
            return {
                "name": PAY_COMMISSION_MASTER_NAME,
                "owner": SYSTEM_MASTER,
                "universal": True,
                "locked": True,
                "editable": False,
                "deletable": False,
                "creatable_by_user": False,
                "fields_manageable": False,
                "description": PAY_COMMISSION_MASTER_DESCRIPTION,
            }
        master = self.get_master_by_name(master_name)
        if not master:
            return None
        locked = master.get("owner_type") == SYSTEM_MASTER
        return {
            "name": master.get("master_name", master_name),
            "owner": master.get("owner_type", "user"),
            "universal": False,
            "locked": locked,
            "editable": not locked,
            "deletable": not locked,
            "creatable_by_user": not locked,
            "fields_manageable": not locked,
            "description": master.get("description", ""),
        }

    def is_system_master(self, master_name: str) -> bool:
        meta = self.get_master_metadata(master_name)
        return bool(meta and meta.get("owner") == SYSTEM_MASTER)

    def is_universal_master(self, master_name: str) -> bool:
        meta = self.get_master_metadata(master_name)
        return bool(meta and meta.get("universal") is True)

    def is_locked_master(self, master_name: str) -> bool:
        meta = self.get_master_metadata(master_name)
        return bool(meta and meta.get("locked") is True)

    def get_records(self, master_id: str, active_only: bool = False) -> List[Dict[str, Any]]:
        if str(master_id) == "SYSTEM-PAY-COMMISSION":
            master = self.get_pay_commission_master()
            records = deepcopy((master or {}).get("_universal_records", []))
            if active_only:
                records = [r for r in records if r.get("_active", True) is not False]
            return records
        master = self.store.get_master(master_id)
        if not master:
            raise ValueError("Master नहीं मिला।")
        records = self.store.load_records(master_id)
        if active_only:
            records = [r for r in records if r.get("_active", True) is not False]
        return deepcopy(records)

    def get_record(self, master_id: str, record_id: str) -> Optional[Dict[str, Any]]:
        for record in self.store.load_records(master_id):
            if str(record.get("_record_id", "")) == str(record_id):
                return deepcopy(record)
        return None

    def get_field_definitions(self, master_id: str, active_only: bool = True) -> List[Dict[str, Any]]:
        master = self.store.get_master(master_id)
        if not master:
            raise ValueError("Master नहीं मिला।")
        fields = sorted(master.get("fields", []), key=lambda f: f.get("field_order", 0))
        if active_only:
            fields = [f for f in fields if f.get("active", True)]
        return deepcopy(fields)

    def record_to_row(self, master_id: str, record: Dict[str, Any]) -> Dict[str, Any]:
        master = self.store.get_master(master_id)
        if not master:
            raise ValueError("Master नहीं मिला।")
        row: Dict[str, Any] = {}
        for field in sorted(master.get("fields", []), key=lambda f: f.get("field_order", 0)):
            row[field.get("field_name", field.get("field_id"))] = record.get(field.get("field_id"), "")
        row["_record_id"] = record.get("_record_id", "")
        return row

    def get_rows(self, master_id: str, active_only: bool = False) -> List[Dict[str, Any]]:
        return [self.record_to_row(master_id, r) for r in self.get_records(master_id, active_only=active_only)]

    def find_records(self, master_id: str, field_name: Optional[str] = None, value: Any = None, *, active_only: bool = True) -> List[Dict[str, Any]]:
        records = self.get_records(master_id, active_only=active_only)
        if field_name is None:
            return records
        master = self.store.get_master(master_id)
        if not master:
            raise ValueError("Master नहीं मिला।")
        field = next((f for f in master.get("fields", []) if self._norm(f.get("field_name")) == self._norm(field_name)), None)
        if not field:
            raise ValueError(f"Field नहीं मिला: {field_name}")
        wanted = self._norm(value)
        fid = field.get("field_id")
        return [r for r in records if self._norm(r.get(fid, "")) == wanted]

    def first_field_value(self, master_id: str, record: Dict[str, Any], aliases: Iterable[str]) -> Any:
        master = self.store.get_master(master_id)
        if not master:
            return ""
        normalized = [self._norm(a) for a in aliases]
        for field in master.get("fields", []):
            if self._norm(field.get("field_name")) in normalized:
                return record.get(field.get("field_id"), "")
        return ""

    def bank_details(self, master_id: str, record: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "account": self.first_field_value(master_id, record, [
                "Account Number", "Account No", "Bank Account", "Bank Account Number",
                "A/C No", "A/C Number", "खाता संख्या", "खाता नंबर", "बैंक खाता"
            ]),
            "ifsc": self.first_field_value(master_id, record, [
                "IFSC", "IFSC Code", "आईएफएससी", "आईएफएससी कोड"
            ]),
            "bank": self.first_field_value(master_id, record, [
                "Bank", "Bank Name", "बैंक", "बैंक का नाम"
            ]),
        }

    def _purpose_score(self, master: Dict[str, Any], purpose: str) -> int:
        name = self._norm(master.get("master_name"))
        fields = [self._norm(f.get("field_name")) for f in master.get("fields", [])]
        text = " ".join([name] + fields)
        score = 0
        if purpose == "vendor":
            for token in ("vendor", "वेंडर", "firm", "फर्म", "supplier", "दुकानदार"):
                if token in text: score += 5
            if any("account" in f or "खाता" in f for f in fields): score += 2
            if any("ifsc" in f or "आईएफएससी" in f for f in fields): score += 2
        elif purpose == "beneficiary":
            for token in ("beneficiary", "बेनिफिशियरी", "लाभार्थी"):
                if token in text: score += 5
        elif purpose == "staff":
            for token in ("employee", "कर्मचारी", "staff", "स्टाफ", "कार्मिक"):
                if token in text: score += 5
        return score

    def resolve_master_by_purpose(self, purpose: str) -> Optional[Dict[str, Any]]:
        purpose = self._norm(purpose)
        candidates = []
        for master in self.list_masters(include_system=False):
            if master.get("status", "active") != "active":
                continue
            score = self._purpose_score(master, purpose)
            if score:
                candidates.append((score, master))
        candidates.sort(key=lambda x: (-x[0], self._norm(x[1].get("master_name"))))
        return deepcopy(candidates[0][1]) if candidates else None

    def get_records_for_purpose(self, purpose: str, active_only: bool = True) -> List[Dict[str, Any]]:
        master = self.resolve_master_by_purpose(purpose)
        if not master:
            return []
        return self.get_records(master["master_id"], active_only=active_only)

    def get_rows_for_purpose(self, purpose: str, active_only: bool = True) -> List[Dict[str, Any]]:
        master = self.resolve_master_by_purpose(purpose)
        if not master:
            return []
        return self.get_rows(master["master_id"], active_only=active_only)

    def bank_details_for_purpose(self, purpose: str, record: Dict[str, Any]) -> Dict[str, Any]:
        master = self.resolve_master_by_purpose(purpose)
        if not master:
            return {"account": "", "ifsc": "", "bank": ""}
        return self.bank_details(master["master_id"], record)


def get_service(username: str) -> MasterDataService:
    return MasterDataService(username)


def get_master_id(username: str, master_name: str) -> Optional[str]:
    master = get_service(username).get_master_by_name(master_name)
    return str(master.get("master_id")) if master else None


def get_master_records(username: str, master_name: str) -> List[Dict[str, Any]]:
    service = get_service(username)
    master = service.get_master_by_name(master_name)
    return service.get_records(master["master_id"]) if master else []


def get_master_rows(username: str, master_name: str) -> List[Dict[str, Any]]:
    service = get_service(username)
    master = service.get_master_by_name(master_name)
    return service.get_rows(master["master_id"]) if master else []


def get_bank_details_for_record(username: str, master_name: str, record_id: str) -> Dict[str, Any]:
    service = get_service(username)
    master = service.get_master_by_name(master_name)
    if not master:
        raise ValueError(f"Master नहीं मिला: {master_name}")
    record = service.get_record(master["master_id"], record_id)
    if not record:
        raise ValueError(f"Record नहीं मिला: {record_id}")
    return service.bank_details(master["master_id"], record)


def _self_test() -> None:
    username = "__master_service_test__"
    service = MasterDataService(username)
    pay = service.get_pay_commission_master()
    meta = service.get_master_metadata(PAY_COMMISSION_MASTER_NAME)
    assert pay is not None, "Pay Commission Master उपलब्ध नहीं है।"
    assert meta and meta["owner"] == SYSTEM_MASTER
    assert meta["universal"] is True
    assert meta["locked"] is True
    assert meta["editable"] is False
    assert meta["deletable"] is False
    assert meta["fields_manageable"] is False
    print("=" * 64)
    print("MASTER DATA SERVICE STEP-8 TEST PASSED")
    print("=" * 64)
    print("Service Version        :", SERVICE_VERSION)
    print("Pay Commission Master  :", PAY_COMMISSION_MASTER_NAME)
    print("Owner                  :", meta["owner"])
    print("Universal              :", meta["universal"])
    print("Locked                 :", meta["locked"])
    print("Mode                   : READ-ONLY")
    print("=" * 64)


if __name__ == "__main__":
    _self_test()
