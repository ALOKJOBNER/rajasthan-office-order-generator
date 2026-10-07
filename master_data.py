from __future__ import annotations
import json, re, uuid
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
try:
    import tkinter as tk
    from tkinter import ttk, messagebox, simpledialog, filedialog
    TK_AVAILABLE = True
except Exception:
    # Streamlit Cloud/Linux may not provide Tk.
    # The Master Data engine remains fully available; only the optional
    # standalone Tkinter GUI is disabled.
    tk = None
    ttk = None
    messagebox = None
    simpledialog = None
    filedialog = None
    TK_AVAILABLE = False
import xml.etree.ElementTree as ET

MASTER_DATA_ENGINE_VERSION = "2.0.0"
BASE_DIR = Path(__file__).resolve().parent
USER_DATA_DIR = BASE_DIR / "output" / "user_data"
MASTER_DEFINITION_FILE = "master_definitions.json"
SYSTEM_MASTER, USER_MASTER = "system", "user"
MASTER_STATUS_ACTIVE, MASTER_STATUS_INACTIVE = "active", "inactive"
PAY_COMMISSION_MASTER_NAME = "Pay Commission Master [UNIVERSAL / LOCKED]"
PAY_COMMISSION_MASTER_DESCRIPTION = "Universal system master. User cannot create, rename, edit, delete, or manage its fields."
MASTER_RECORDS_DIR = "master_records"
FIELD_TYPES = {
    "text":"Text", "number":"Number", "decimal":"Decimal", "date":"Date",
    "datetime":"Date & Time", "boolean":"Yes / No", "dropdown":"Dropdown",
    "email":"Email", "phone":"Mobile / Phone"
}

def now_iso(): return datetime.now().isoformat(timespec="seconds")
def generate_id(prefix="MD"): return f"{prefix}-{uuid.uuid4().hex[:12].upper()}"
def normalize_username(username):
    username=str(username or "").strip().lower()
    if not username: raise ValueError("Username आवश्यक है।")
    return re.sub(r"[^a-zA-Z0-9_.@-]", "_", username)

def empty_master_definition(master_name, description="", owner_type=USER_MASTER):
    if not str(master_name).strip(): raise ValueError("Master का नाम आवश्यक है।")
    if owner_type not in (SYSTEM_MASTER, USER_MASTER): raise ValueError("अमान्य owner_type")
    t=now_iso()
    return {"master_id":generate_id("MD"),"master_name":str(master_name).strip(),
            "description":str(description).strip(),"owner_type":owner_type,
            "status":MASTER_STATUS_ACTIVE,"fields":[],"created_at":t,
            "updated_at":t,"engine_version":MASTER_DATA_ENGINE_VERSION}

def create_field_definition(field_name, field_type="text", required=False,
                            active=True, options=None, description=""):
    if not str(field_name).strip(): raise ValueError("Field का नाम आवश्यक है।")
    field_type=str(field_type).strip().lower()
    if field_type not in FIELD_TYPES: raise ValueError(f"अमान्य field type: {field_type}")
    opts=[]
    for x in options or []:
        x=str(x).strip()
        if x and x not in opts: opts.append(x)
    if field_type=="dropdown" and not opts: raise ValueError("Dropdown field के लिए options आवश्यक हैं।")
    return {"field_id":generate_id("FLD"),"field_name":str(field_name).strip(),
            "field_type":field_type,"required":bool(required),"active":bool(active),
            "description":str(description).strip(),"options":opts}

# -------------------- Excel Template / Import Engine --------------------
XLSX_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"

def _xml_escape(value):
    return (str(value).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;").replace("'", "&apos;"))

def _excel_col(n):
    s = ""
    while n:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s

def create_xlsx_template(master_name, fields, output_path):
    headers = [str(f.get("field_name", "")).strip() for f in fields if f.get("active", True)]
    headers = [h for h in headers if h]
    if not headers:
        raise ValueError("इस Master में कोई Active Field नहीं है। पहले Field जोड़िए।")

    header_cells = []
    for i, h in enumerate(headers, 1):
        ref = f"{_excel_col(i)}1"
        header_cells.append(
            f'<c r="{ref}" t="inlineStr"><is><t>{_xml_escape(h)}</t></is></c>'
        )
    row_xml = f'<row r="1">{"".join(header_cells)}</row>'

    last_col = _excel_col(len(headers))
    sheet = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="{XLSX_NS}" xmlns:r="{REL_NS}">
<dimension ref="A1:{last_col}1"/>
<sheetData>{row_xml}</sheetData>
</worksheet>"""

    workbook = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="{XLSX_NS}" xmlns:r="{REL_NS}">
<sheets><sheet name="Data" sheetId="1" r:id="rId1"/></sheets>
</workbook>"""

    rels = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="{PKG_REL_NS}">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
</Relationships>"""

    root_rels = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="{PKG_REL_NS}">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>"""

    content_types = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
</Types>"""

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", content_types)
        z.writestr("_rels/.rels", root_rels)
        z.writestr("xl/workbook.xml", workbook)
        z.writestr("xl/_rels/workbook.xml.rels", rels)
        z.writestr("xl/worksheets/sheet1.xml", sheet)
    return output_path

def _xlsx_cell_value(cell, shared_strings):
    t = cell.attrib.get("t")
    v = cell.find(f"{{{XLSX_NS}}}v")
    is_node = cell.find(f"{{{XLSX_NS}}}is")
    if t == "inlineStr" and is_node is not None:
        return "".join(is_node.itertext())
    if v is None:
        return ""
    value = v.text or ""
    if t == "s":
        try:
            return shared_strings[int(value)]
        except Exception:
            return ""
    return value

def read_xlsx_rows(path):
    with zipfile.ZipFile(path, "r") as z:
        names = set(z.namelist())
        shared_strings = []
        if "xl/sharedStrings.xml" in names:
            root = ET.fromstring(z.read("xl/sharedStrings.xml"))
            for si in root.findall(f"{{{XLSX_NS}}}si"):
                shared_strings.append("".join(si.itertext()))

        sheet_name = "xl/worksheets/sheet1.xml"
        if sheet_name not in names:
            raise ValueError("Excel की पहली worksheet नहीं मिली।")
        root = ET.fromstring(z.read(sheet_name))

        rows = []
        for row in root.findall(f".//{{{XLSX_NS}}}row"):
            cells = {}
            max_col = 0
            for cell in row.findall(f"{{{XLSX_NS}}}c"):
                ref = cell.attrib.get("r", "A1")
                letters = "".join(ch for ch in ref if ch.isalpha())
                num = 0
                for ch in letters:
                    num = num * 26 + (ord(ch.upper()) - 64)
                max_col = max(max_col, num)
                cells[num] = _xlsx_cell_value(cell, shared_strings)
            rows.append([cells.get(i, "") for i in range(1, max_col + 1)])
        return rows


def _norm_duplicate_value(value):
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value).strip()).casefold()

def _field_tokens(field):
    return f"{field.get('field_name', '')} {field.get('field_id', '')}".casefold()

def infer_duplicate_fields(master_def):
    """Infer identity fields from the Master type/field names.
    Mobile, Aadhaar, Jan Aadhaar and Name are deliberately NOT universal
    duplicate keys. Composite identity is supported by selecting multiple
    strong identity fields when they are present.
    """
    fields = [
        f for f in sorted(master_def.get("fields", []), key=lambda x: x.get("field_order", 0))
        if f.get("active", True)
    ]
    groups = [
        ("employee", ["employee id","employee code","employee no","employee number",
                      "emp id","emp code","emp no","staff id","staff code","staff no"]),
        ("gpf", ["gpf number","gpf no","gpf"]),
        ("vendor", ["vendor id","vendor code","vendor no","supplier id","supplier code"]),
        ("beneficiary", ["beneficiary id","beneficiary code","beneficiary no"]),
        ("student", ["student id","student code","student no","enrollment no",
                      "enrollment number","admission no","admission number","scholar no"]),
        ("institution", ["school code","institution code","udise code","udise"]),
        ("tax", ["gstin","gst number","gst no","pan","pan number","pan no"]),
        ("account", ["account number","account no","bank account","bank account number"]),
    ]
    selected = []
    used = set()
    for _, names in groups:
        for f in fields:
            tokens = _field_tokens(f)
            if any(name in tokens for name in names):
                fid = f.get("field_id")
                if fid not in used:
                    selected.append(f)
                    used.add(fid)
                break
    return selected

def duplicate_key_for_record(record, identity_fields):
    vals = []
    for f in identity_fields:
        v = _norm_duplicate_value(record.get(f.get("field_id"), ""))
        if not v:
            return None
        vals.append(v)
    return tuple(vals) if vals else None

def normalize_import_value(value, field):
    value = str(value).strip()
    ftype = field.get("field_type", "text")
    if value == "":
        return ""
    if ftype == "number":
        try: return int(float(value))
        except ValueError: return value
    if ftype == "decimal":
        try: return float(value)
        except ValueError: return value
    if ftype == "boolean":
        v = value.casefold()
        if v in ("yes", "true", "1", "हाँ", "हां"): return True
        if v in ("no", "false", "0", "नहीं"): return False
    return value

# -----------------------------------------------------------------------
class MasterDefinitionStore:
    def __init__(self, username):
        self.username=normalize_username(username)
        self.user_dir=USER_DATA_DIR/self.username
        self.user_dir.mkdir(parents=True, exist_ok=True)
        self.definition_file=self.user_dir/MASTER_DEFINITION_FILE
        self.definitions=[]
        self.load()
    def load(self):
        if not self.definition_file.exists(): self.definitions=[]; return self.definitions
        try:
            data=json.loads(self.definition_file.read_text(encoding="utf-8"))
            self.definitions=data if isinstance(data,list) else []
        except (json.JSONDecodeError,OSError): self.definitions=[]
        return self.definitions
    def save(self):
        """Safe Windows persistence for master_definitions.json."""
        import os
        import shutil
        import time
        target = self.definition_file
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(self.definitions, ensure_ascii=False, indent=4)
        if target.exists():
            backup = target.with_name(target.name + ".before_last_write.bak")
            try:
                shutil.copy2(target, backup)
            except Exception:
                pass
        tmp = target.with_suffix(".tmp")
        tmp.write_text(payload, encoding="utf-8")
        last_error = None
        for _ in range(5):
            try:
                os.replace(str(tmp), str(target))
                return
            except PermissionError as exc:
                last_error = exc
                time.sleep(0.25)
            except OSError as exc:
                last_error = exc
                time.sleep(0.15)
        try:
            with open(target, "w", encoding="utf-8") as fh:
                fh.write(payload)
                fh.flush()
                os.fsync(fh.fileno())
            try:
                if tmp.exists(): tmp.unlink()
            except Exception:
                pass
            return
        except (PermissionError, OSError) as exc:
            last_error = exc
        raise PermissionError(f"master_definitions.json लिख नहीं सका: {last_error}") from last_error
    def get_master(self, master_id):
        return next((m for m in self.definitions if m.get("master_id")==str(master_id).strip()),None)
    def get_master_by_name(self,name):
        n=str(name).strip().casefold()
        return next((m for m in self.definitions if str(m.get("master_name","")).strip().casefold()==n),None)
    def create_master(self,name,description=""):
        if self.get_master_by_name(name): raise ValueError(f"'{name}' नाम का Master पहले से मौजूद है।")
        m=empty_master_definition(name,description,USER_MASTER); self.definitions.append(m); self.save(); return m
    def update_master_info(self,master_id,master_name=None,description=None):
        m=self.get_master(master_id)
        if not m: raise ValueError("Master नहीं मिला।")
        if master_name is not None:
            existing=self.get_master_by_name(master_name)
            if existing and existing.get("master_id")!=master_id: raise ValueError(f"'{master_name}' नाम पहले से मौजूद है।")
            if not str(master_name).strip(): raise ValueError("Master का नाम खाली नहीं हो सकता।")
            m["master_name"]=str(master_name).strip()
        if description is not None: m["description"]=str(description).strip()
        m["updated_at"]=now_iso(); self.save(); return m
    def add_field(self,master_id,field_name,field_type="text",required=False,active=True,options=None,description=""):
        m=self.get_master(master_id)
        if not m: raise ValueError("Master नहीं मिला।")
        if any(str(f.get("field_name","")).casefold()==str(field_name).strip().casefold() for f in m.get("fields",[])):
            raise ValueError(f"'{field_name}' field पहले से मौजूद है।")
        f=create_field_definition(field_name,field_type,required,active,options,description)
        f["field_order"]=len(m.get("fields",[]))+1; m["fields"].append(f); m["updated_at"]=now_iso(); self.save(); return f
    def get_field(self,master_id,field_id):
        m=self.get_master(master_id)
        return next((f for f in (m or {}).get("fields",[]) if f.get("field_id")==field_id),None)
    def update_field(self,master_id,field_id,field_name=None,field_type=None,required=None,active=None,options=None,description=None):
        f=self.get_field(master_id,field_id)
        if not f: raise ValueError("Field नहीं मिला।")
        m=self.get_master(master_id)
        if field_name is not None:
            if any(x.get("field_id")!=field_id and str(x.get("field_name","")).casefold()==str(field_name).strip().casefold() for x in m["fields"]):
                raise ValueError(f"'{field_name}' field पहले से मौजूद है।")
            f["field_name"]=str(field_name).strip()
        if field_type is not None:
            field_type=str(field_type).lower()
            if field_type not in FIELD_TYPES: raise ValueError("अमान्य field type")
            f["field_type"]=field_type
        if required is not None: f["required"]=bool(required)
        if active is not None: f["active"]=bool(active)
        if description is not None: f["description"]=str(description).strip()
        if options is not None: f["options"]=list(dict.fromkeys(str(x).strip() for x in options if str(x).strip()))
        if f["field_type"]=="dropdown" and not f["options"]: raise ValueError("Dropdown field के लिए options आवश्यक हैं।")
        m["updated_at"]=now_iso(); self.save(); return f
    def delete_field(self,master_id,field_id):
        m=self.get_master(master_id)
        if not m: raise ValueError("Master नहीं मिला।")
        old=len(m["fields"]); m["fields"]=[f for f in m["fields"] if f.get("field_id")!=field_id]
        if len(m["fields"])==old: raise ValueError("Field नहीं मिला।")
        for i,f in enumerate(m["fields"],1): f["field_order"]=i
        m["updated_at"]=now_iso(); self.save()
    def records_file(self, master_id):
        folder = self.user_dir / MASTER_RECORDS_DIR
        folder.mkdir(parents=True, exist_ok=True)
        return folder / f"{str(master_id).strip()}.json"

    def load_records(self, master_id):
        path = self.records_file(master_id)
        if not path.exists():
            return []
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except (json.JSONDecodeError, OSError):
            return []

    def save_records(self, master_id, records):
        path = self.records_file(master_id)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(path)


    def records_file(self, master_id):
        folder = self.user_dir / "master_records"
        folder.mkdir(parents=True, exist_ok=True)
        return folder / f"{str(master_id).strip()}.json"

    def load_records(self, master_id):
        path = self.records_file(master_id)
        if not path.exists():
            return []
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(data, list):
                return []
            changed = False
            for rec in data:
                if isinstance(rec, dict) and not rec.get("_record_id"):
                    rec["_record_id"] = generate_id("REC")
                    rec["_created_at"] = rec.get("_imported_at", now_iso())
                    rec["_updated_at"] = now_iso()
                    changed = True
            if changed:
                self.save_records(master_id, data)
            return data
        except (json.JSONDecodeError, OSError):
            return []

    def save_records(self, master_id, records):
        path = self.records_file(master_id)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(path)

    def _identity_fields(self, master_id):
        m = self.get_master(master_id)
        if not m:
            raise ValueError("Master नहीं मिला।")
        return infer_duplicate_fields(m)

    def _conflict(self, master_id, candidate, exclude_id=None):
        fields = self._identity_fields(master_id)
        key = duplicate_key_for_record(candidate, fields)
        if key is None:
            return None
        for rec in self.load_records(master_id):
            if exclude_id and rec.get("_record_id") == exclude_id:
                continue
            if duplicate_key_for_record(rec, fields) == key:
                return {"fields": fields, "key": key, "record": rec}
        return None

    def add_record(self, master_id, values):
        m = self.get_master(master_id)
        if not m:
            raise ValueError("Master नहीं मिला।")
        if m.get("owner_type") == SYSTEM_MASTER:
            raise ValueError("Universal Pay Commission Master में records बदले नहीं जा सकते।")
        conflict = self._conflict(master_id, values)
        if conflict:
            names = ", ".join(f.get("field_name", "") for f in conflict["fields"])
            vals = " + ".join(conflict["key"])
            raise ValueError(f"Duplicate Record मिला।\nDuplicate Check Fields: {names}\nValue: {vals}")
        rec = dict(values)
        rec["_record_id"] = generate_id("REC")
        rec["_created_at"] = now_iso()
        rec["_updated_at"] = now_iso()
        data = self.load_records(master_id)
        data.append(rec)
        self.save_records(master_id, data)
        return rec

    def update_record(self, master_id, record_id, values):
        m = self.get_master(master_id)
        if not m:
            raise ValueError("Master नहीं मिला।")
        if m.get("owner_type") == SYSTEM_MASTER:
            raise ValueError("Universal Pay Commission Master में records बदले नहीं जा सकते।")
        conflict = self._conflict(master_id, values, exclude_id=record_id)
        if conflict:
            names = ", ".join(f.get("field_name", "") for f in conflict["fields"])
            vals = " + ".join(conflict["key"])
            raise ValueError(f"Duplicate Record मिला।\nDuplicate Check Fields: {names}\nValue: {vals}")
        data = self.load_records(master_id)
        for rec in data:
            if rec.get("_record_id") == record_id:
                rec.update(values)
                rec["_record_id"] = record_id
                rec["_updated_at"] = now_iso()
                self.save_records(master_id, data)
                return rec
        raise ValueError("Record नहीं मिला।")

    def delete_record(self, master_id, record_id):
        m = self.get_master(master_id)
        if not m:
            raise ValueError("Master नहीं मिला।")
        if m.get("owner_type") == SYSTEM_MASTER:
            raise ValueError("Universal Pay Commission Master में records बदले नहीं जा सकते।")
        data = self.load_records(master_id)
        new_data = [r for r in data if r.get("_record_id") != record_id]
        if len(new_data) == len(data):
            raise ValueError("Record नहीं मिला।")
        self.save_records(master_id, new_data)

    def duplicate_analysis(self, master_id):
        m = self.get_master(master_id)
        if not m:
            raise ValueError("Master नहीं मिला।")
        fields = infer_duplicate_fields(m)
        seen = {}
        duplicates = []
        for n, rec in enumerate(self.load_records(master_id), start=1):
            key = duplicate_key_for_record(rec, fields)
            if key is None:
                continue
            if key in seen:
                duplicates.append((n, seen[key], key))
            else:
                seen[key] = n
        return fields, duplicates

    def import_records_from_excel(self, master_id, excel_path):
        m = self.get_master(master_id)
        if not m:
            raise ValueError("Master नहीं मिला।")
        if m.get("owner_type") == SYSTEM_MASTER:
            raise ValueError("Universal Pay Commission Master में user data import नहीं किया जा सकता।")

        active_fields = [f for f in sorted(m.get("fields", []), key=lambda x: x.get("field_order", 0))
                         if f.get("active", True)]
        if not active_fields:
            raise ValueError("इस Master में कोई Active Field नहीं है।")

        rows = read_xlsx_rows(excel_path)
        if not rows:
            raise ValueError("Excel file खाली है।")

        headers = [str(x).strip() for x in rows[0]]
        field_by_name = {str(f.get("field_name", "")).strip().casefold(): f for f in active_fields}
        mapped = [field_by_name.get(h.casefold()) if h else None for h in headers]

        if not any(mapped):
            raise ValueError("Excel header में Master के कोई matching Field नहीं मिले।")

        records = []
        for row in rows[1:]:
            if not any(str(x).strip() for x in row):
                continue
            rec = {}
            for idx, field in enumerate(mapped):
                if field is not None:
                    raw = row[idx] if idx < len(row) else ""
                    rec[field["field_id"]] = normalize_import_value(raw, field)
            for field in active_fields:
                fid = field["field_id"]
                if fid not in rec:
                    rec[fid] = ""
                if field.get("required") and str(rec[fid]).strip() == "":
                    raise ValueError(
                        f"Required Field '{field.get('field_name')}' में row {len(records)+2} पर value नहीं है।"
                    )
            rec["_imported_at"] = now_iso()
            records.append(rec)

        # Reject duplicates both against existing records and inside this Excel.
        identity_fields = infer_duplicate_fields(m)
        if identity_fields:
            seen = {}
            for existing in self.load_records(master_id):
                key = duplicate_key_for_record(existing, identity_fields)
                if key is not None:
                    seen[key] = "existing"

            duplicates = []
            for row_no, rec in enumerate(records, start=2):
                key = duplicate_key_for_record(rec, identity_fields)
                if key is None:
                    continue
                if key in seen:
                    duplicates.append((row_no, key, seen[key]))
                else:
                    seen[key] = row_no

            if duplicates:
                names = ", ".join(f.get("field_name", "") for f in identity_fields)
                details = "\n".join(
                    f"Excel Row {row}: {' + '.join(key)}"
                    for row, key, _ in duplicates[:10]
                )
                more = "" if len(duplicates) <= 10 else f"\n... और {len(duplicates)-10} duplicate(s)"
                raise ValueError(
                    f"Duplicate Record(s) मिले।\n\n"
                    f"Duplicate Check Fields: {names}\n{details}{more}\n\n"
                    "कोई record save नहीं किया गया।"
                )

        for rec in records:
            rec["_record_id"] = generate_id("REC")
            rec["_created_at"] = now_iso()
            rec["_updated_at"] = now_iso()

        self.save_records(master_id, records + self.load_records(master_id))
        return len(records)

    def ensure_pay_commission_master(self):
        """Ensure the locked universal Pay Commission Master has its schema/data.

        The actual 6th/7th CPC values live in output/pay_commission_master_seed.json;
        modules must read them through MasterDataService instead of carrying their own
        pay-commission tables.  This function only seeds/refreshes the protected
        system master and never exposes it to user edit/import/delete operations.
        """
        existing = next(
            (m for m in self.definitions
             if str(m.get("master_name", "")).strip().casefold() == PAY_COMMISSION_MASTER_NAME.casefold()),
            None
        )
        if existing:
            changed = False
            if existing.get("owner_type") != SYSTEM_MASTER:
                existing["owner_type"] = SYSTEM_MASTER
                changed = True
            if existing.get("status") != MASTER_STATUS_ACTIVE:
                existing["status"] = MASTER_STATUS_ACTIVE
                changed = True
            if existing.get("description") != PAY_COMMISSION_MASTER_DESCRIPTION:
                existing["description"] = PAY_COMMISSION_MASTER_DESCRIPTION
                changed = True
            if changed:
                existing["updated_at"] = now_iso()
                self.save()
            self._seed_pay_commission_master_data(existing)
            return existing

        m = empty_master_definition(
            PAY_COMMISSION_MASTER_NAME,
            PAY_COMMISSION_MASTER_DESCRIPTION,
            SYSTEM_MASTER
        )
        self.definitions.append(m)
        self.save()
        self._seed_pay_commission_master_data(m)
        return m

    def _seed_pay_commission_master_data(self, master):
        """Populate the protected system master from the checked-in seed JSON."""
        try:
            seed_path = BASE_DIR / "output" / "pay_commission_master_seed.json"
            if not seed_path.exists():
                return
            payload = json.loads(seed_path.read_text(encoding="utf-8"))
            fields = payload.get("fields", [])
            # Stable field IDs are generated only when missing; once written they
            # remain stable so module lookups continue to work across upgrades.
            existing_by_name = {str(f.get("field_name", "")).strip().casefold(): f for f in master.get("fields", [])}
            out_fields=[]
            for idx, item in enumerate(fields, 1):
                name=str(item.get("field_name", "")).strip()
                if not name:
                    continue
                old=existing_by_name.get(name.casefold())
                f=deepcopy(old) if old else create_field_definition(name, item.get("field_type", "text"), active=True)
                f["field_order"]=idx; f["active"]=True
                out_fields.append(f)
            changed = master.get("fields") != out_fields or master.get("updated_from_seed") != payload.get("version")
            master["fields"] = out_fields
            master["updated_from_seed"] = payload.get("version", "")
            master["locked"] = True
            master["owner_type"] = SYSTEM_MASTER
            if changed:
                master["updated_at"] = now_iso()
                self.save()

            # Seed only when the protected master has no records, or when the
            # seed version has genuinely changed. Do NOT overwrite approved
            # in-application DA edits on every startup.
            existing_records = self.load_records(master["master_id"])
            seed_version = payload.get("version", "")
            stored_version = master.get("data_seed_version", "")
            if not existing_records:
                records=[]
                field_by_name={f["field_name"]: f["field_id"] for f in out_fields}
                for src in payload.get("records", []):
                    rec={}
                    for k,v in src.items():
                        fid=field_by_name.get(k)
                        if not fid:
                            continue
                        rec[fid] = json.dumps(v, ensure_ascii=False) if isinstance(v, list) else v
                    rec["_record_id"] = generate_id("REC")
                    rec["_created_at"] = now_iso(); rec["_updated_at"] = now_iso()
                    records.append(rec)
                self.save_records(master["master_id"], records)
                master["data_seed_version"] = seed_version
                master["allow_seed_refresh"] = True
                master["updated_at"] = now_iso()
                self.save()
            elif not stored_version:
                # Existing protected records may contain approved in-app edits;
                # mark them as the current baseline without overwriting them.
                master["data_seed_version"] = seed_version
                master["allow_seed_refresh"] = True
                master["updated_at"] = now_iso()
                self.save()
        except Exception:
            # Do not break application startup if a seed file is temporarily
            # unavailable. Existing master definitions remain intact.
            return

    def is_system_master(self, master_id):
        m = self.get_master(master_id)
        return bool(m and m.get("owner_type") == SYSTEM_MASTER)

    def delete_master(self, master_id):
        m = self.get_master(master_id)
        if not m:
            raise ValueError("Master नहीं मिला।")
        if m.get("owner_type") == SYSTEM_MASTER:
            raise ValueError("Universal/System Master को delete नहीं किया जा सकता।")
        self.definitions = [
            x for x in self.definitions if x.get("master_id") != str(master_id).strip()
        ]
        self.save()

    def list_masters(self):
        return sorted(deepcopy(self.definitions),key=lambda x:str(x.get("master_name","")).casefold())

if TK_AVAILABLE:
    class FieldDialog(tk.Toplevel):
        def __init__(self,parent,field=None):
            super().__init__(parent); self.result=None; field=field or {}
            self.title("Field"); self.geometry("520x360"); self.resizable(False,False)
            self.name=tk.StringVar(value=field.get("field_name",""))
            self.typ=tk.StringVar(value=field.get("field_type","text"))
            self.req=tk.BooleanVar(value=field.get("required",False))
            self.act=tk.BooleanVar(value=field.get("active",True))
            self.desc=tk.StringVar(value=field.get("description",""))
            self.opts=tk.StringVar(value=", ".join(field.get("options",[])))
            f=ttk.Frame(self,padding=18); f.pack(fill="both",expand=True)
            rows=[("Field Name:",self.name),("Description:",self.desc)]
            for i,(lab,var) in enumerate(rows):
                ttk.Label(f,text=lab).grid(row=i,column=0,sticky="w",pady=7); ttk.Entry(f,textvariable=var,width=42).grid(row=i,column=1,pady=7)
            ttk.Label(f,text="Field Type:").grid(row=2,column=0,sticky="w",pady=7)
            self.combo=ttk.Combobox(f,textvariable=self.typ,values=list(FIELD_TYPES),state="readonly",width=39); self.combo.grid(row=2,column=1); self.combo.bind("<<ComboboxSelected>>",self.toggle)
            ttk.Checkbutton(f,text="Required",variable=self.req).grid(row=3,column=1,sticky="w")
            ttk.Checkbutton(f,text="Active",variable=self.act).grid(row=4,column=1,sticky="w")
            ttk.Label(f,text="Dropdown Options:").grid(row=5,column=0,sticky="w",pady=7)
            self.optentry=ttk.Entry(f,textvariable=self.opts,width=42); self.optentry.grid(row=5,column=1,pady=7)
            ttk.Label(f,text="Dropdown में comma से अलग करें।").grid(row=6,column=1,sticky="w")
            b=ttk.Frame(f); b.grid(row=7,column=0,columnspan=2,pady=15)
            ttk.Button(b,text="Save",command=self.save).pack(side="left",padx=5); ttk.Button(b,text="Cancel",command=self.destroy).pack(side="left",padx=5)
            self.toggle(); self.transient(parent); self.grab_set()
        def toggle(self,event=None):
            self.optentry.configure(state="normal" if self.typ.get()=="dropdown" else "disabled")
        def save(self):
            if not self.name.get().strip(): messagebox.showwarning("Validation","Field Name आवश्यक है।",parent=self); return
            opts=[x.strip() for x in self.opts.get().split(",") if x.strip()] if self.typ.get()=="dropdown" else []
            if self.typ.get()=="dropdown" and not opts: messagebox.showwarning("Validation","Dropdown options आवश्यक हैं।",parent=self); return
            self.result={"field_name":self.name.get().strip(),"field_type":self.typ.get(),"required":self.req.get(),"active":self.act.get(),"options":opts,"description":self.desc.get().strip()}
            self.destroy()
    
    
    class RecordDialog(tk.Toplevel):
        def __init__(self, parent, master_def, record=None):
            super().__init__(parent)
            self.result = None
            self.master_def = master_def
            self.record = record or {}
            self.title(f"Record - {master_def.get('master_name', '')}")
            self.geometry("620x560")
            self.resizable(False, True)
            outer = ttk.Frame(self, padding=14)
            outer.pack(fill="both", expand=True)
    
            canvas = tk.Canvas(outer, highlightthickness=0)
            sb = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
            form = ttk.Frame(canvas)
            form.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
            canvas.create_window((0,0), window=form, anchor="nw")
            canvas.configure(yscrollcommand=sb.set)
            canvas.pack(side="left", fill="both", expand=True)
            sb.pack(side="right", fill="y")
    
            self.vars = {}
            fields = [f for f in sorted(master_def.get("fields", []), key=lambda x:x.get("field_order",0))
                      if f.get("active", True)]
            for r, f in enumerate(fields):
                fid = f["field_id"]
                ttk.Label(form, text=f.get("field_name","") + (" *" if f.get("required") else "")).grid(
                    row=r, column=0, sticky="w", padx=(0,10), pady=7)
                var = tk.StringVar(value="" if self.record.get(fid) is None else str(self.record.get(fid)))
                self.vars[fid] = (var, f)
                typ = f.get("field_type","text")
                if typ == "dropdown":
                    w = ttk.Combobox(form, textvariable=var, values=f.get("options",[]), state="readonly", width=38)
                elif typ == "boolean":
                    w = ttk.Combobox(form, textvariable=var, values=["Yes","No"], state="readonly", width=38)
                else:
                    w = ttk.Entry(form, textvariable=var, width=42)
                w.grid(row=r, column=1, sticky="ew", pady=7)
    
            b = ttk.Frame(self); b.pack(fill="x", padx=14, pady=10)
            ttk.Button(b, text="Save", command=self.save).pack(side="left", padx=4)
            ttk.Button(b, text="Cancel", command=self.destroy).pack(side="left", padx=4)
            self.transient(parent); self.grab_set()
    
        def save(self):
            values = {}
            for fid, (var, f) in self.vars.items():
                value = var.get().strip()
                if f.get("required") and not value:
                    messagebox.showwarning("Validation", f"Required Field '{f.get('field_name','')}' खाली है।", parent=self)
                    return
                values[fid] = normalize_import_value(value, f)
            self.result = values
            self.destroy()
    
    
    class RecordsWindow(tk.Toplevel):
        def __init__(self, parent, store, master_id):
            super().__init__(parent)
            self.store = store
            self.master_id = master_id
            self.master_def = store.get_master(master_id)
            self.title(f"Records - {self.master_def.get('master_name','')}")
            self.geometry("1200x650")
            self.minsize(900,500)
    
            outer = ttk.Frame(self, padding=10); outer.pack(fill="both", expand=True)
            top = ttk.Frame(outer); top.pack(fill="x", pady=(0,8))
            self.count_var = tk.StringVar()
            ttk.Label(top, textvariable=self.count_var, font=("Segoe UI",11,"bold")).pack(side="left")
            ttk.Button(top, text="Duplicate Check", command=self.check_duplicates).pack(side="right", padx=4)
            ttk.Button(top, text="Refresh", command=self.refresh).pack(side="right", padx=4)
    
            table = ttk.Frame(outer); table.pack(fill="both", expand=True)
            self.fields = [f for f in sorted(self.master_def.get("fields",[]), key=lambda x:x.get("field_order",0))
                           if f.get("active",True)]
            cols = [f["field_id"] for f in self.fields]
            self.tree = ttk.Treeview(table, columns=cols, show="headings", selectmode="browse")
            for f in self.fields:
                fid=f["field_id"]; self.tree.heading(fid,text=f.get("field_name",""))
                self.tree.column(fid,width=max(130,min(260,len(f.get("field_name",""))*10+50)))
            self.tree.pack(side="left",fill="both",expand=True)
            ysb=ttk.Scrollbar(table,orient="vertical",command=self.tree.yview); ysb.pack(side="right",fill="y")
            xsb=ttk.Scrollbar(outer,orient="horizontal",command=self.tree.xview); xsb.pack(fill="x")
            self.tree.configure(yscrollcommand=ysb.set,xscrollcommand=xsb.set)
    
            b=ttk.Frame(outer); b.pack(fill="x",pady=(8,0))
            locked=self.store.is_system_master(master_id)
            self.add_btn=ttk.Button(b,text="+ Add Record",command=self.add_record); self.add_btn.pack(side="left",padx=3)
            self.edit_btn=ttk.Button(b,text="Edit Record",command=self.edit_record); self.edit_btn.pack(side="left",padx=3)
            self.delete_btn=ttk.Button(b,text="Delete Record",command=self.delete_record); self.delete_btn.pack(side="left",padx=3)
            if locked:
                for w in (self.add_btn,self.edit_btn,self.delete_btn): w.configure(state="disabled")
            self.refresh()
    
        def refresh(self):
            for i in self.tree.get_children(): self.tree.delete(i)
            records=self.store.load_records(self.master_id)
            for rec in records:
                vals=[]
                for f in self.fields:
                    v=rec.get(f["field_id"],"")
                    vals.append("Yes" if isinstance(v,bool) and v else "No" if isinstance(v,bool) else v)
                self.tree.insert("", "end", iid=rec.get("_record_id"), values=vals)
            self.count_var.set(f"{self.master_def.get('master_name','')} — Total Records: {len(records)}")
    
        def selected_id(self):
            s=self.tree.selection()
            return s[0] if s else None
    
        def add_record(self):
            d=RecordDialog(self,self.master_def); self.wait_window(d)
            if d.result is not None:
                try: self.store.add_record(self.master_id,d.result); self.refresh()
                except Exception as e: messagebox.showerror("Record Error",str(e),parent=self)
    
        def edit_record(self):
            rid=self.selected_id()
            if not rid: return messagebox.showwarning("Selection","पहले Record चुनिए।",parent=self)
            rec=next((r for r in self.store.load_records(self.master_id) if r.get("_record_id")==rid),None)
            if not rec: return
            d=RecordDialog(self,self.master_def,rec); self.wait_window(d)
            if d.result is not None:
                try: self.store.update_record(self.master_id,rid,d.result); self.refresh()
                except Exception as e: messagebox.showerror("Record Error",str(e),parent=self)
    
        def delete_record(self):
            rid=self.selected_id()
            if not rid: return messagebox.showwarning("Selection","पहले Record चुनिए।",parent=self)
            if not messagebox.askyesno("Confirm Delete","क्या चयनित Record delete करना है?",parent=self): return
            try: self.store.delete_record(self.master_id,rid); self.refresh()
            except Exception as e: messagebox.showerror("Record Error",str(e),parent=self)
    
        def check_duplicates(self):
            try:
                fields, duplicates = self.store.duplicate_analysis(self.master_id)
                if not fields:
                    return messagebox.showinfo(
                        "Duplicate Check",
                        "इस Master के Fields में Software को कोई स्पष्ट identity field नहीं मिला।\n\n"
                        "Mobile/Aadhaar/Jan Aadhaar/Name को अकेले universal duplicate key नहीं माना गया।",
                        parent=self)
                if not duplicates:
                    return messagebox.showinfo(
                        "Duplicate Check",
                        "कोई duplicate record नहीं मिला।\n\nCheck Fields: " + ", ".join(f.get("field_name","") for f in fields),
                        parent=self)
                details="\n".join(f"Record Row {a} ↔ Row {b}: {' + '.join(k)}" for a,b,k in duplicates[:15])
                messagebox.showwarning(
                    "Duplicate Records Found",
                    f"Duplicate Check Fields: {', '.join(f.get('field_name','') for f in fields)}\n\n{details}",
                    parent=self)
            except Exception as e:
                messagebox.showerror("Duplicate Check Error",str(e),parent=self)
    
    
    class MasterDataGUI(tk.Tk):
        def __init__(self,username="alokjobner"):
            super().__init__(); self.store=MasterDefinitionStore(username); self.username=username; self.ids=[]; self.selected=None
            self.store.ensure_pay_commission_master()
            self.title("Master Data Management - Step 3"); self.geometry("1150x680")
            self.build(); self.refresh()
        def build(self):
            ttk.Label(self,text="MASTER DATA MANAGEMENT",font=("Segoe UI",18,"bold")).pack(anchor="w",padx=15,pady=12)
            body=ttk.Frame(self,padding=12); body.pack(fill="both",expand=True)
            left=ttk.LabelFrame(body,text="Masters",padding=8); left.pack(side="left",fill="y",padx=(0,8))
            self.lb=tk.Listbox(left,width=28,height=24,font=("Segoe UI",11)); self.lb.pack(fill="both",expand=True); self.lb.bind("<<ListboxSelect>>",self.select)
            ttk.Button(left,text="+ Add New Master Data",command=self.add_master).pack(fill="x",pady=7)
            ttk.Button(left,text="Refresh",command=self.refresh).pack(fill="x")
            right=ttk.Frame(body); right.pack(side="left",fill="both",expand=True)
            info=ttk.LabelFrame(right,text="Selected Master",padding=8); info.pack(fill="x")
            self.n=tk.StringVar(value="कोई Master चयनित नहीं"); self.d=tk.StringVar()
            ttk.Label(info,textvariable=self.n,font=("Segoe UI",12,"bold")).pack(side="left"); ttk.Label(info,textvariable=self.d).pack(side="left",padx=20)
            self.edit_master_btn = ttk.Button(info,text="Edit Master",command=self.edit_master)
            self.edit_master_btn.pack(side="right", padx=3)
            self.delete_master_btn = ttk.Button(info,text="Delete Master",command=self.delete_master)
            self.delete_master_btn.pack(side="right", padx=3)
            ff=ttk.LabelFrame(right,text="Manage Fields",padding=8); ff.pack(fill="both",expand=True,pady=8)
            cols=("order","name","type","required","active","description"); self.tree=ttk.Treeview(ff,columns=cols,show="headings")
            heads={"order":"Order","name":"Field Name","type":"Type","required":"Required","active":"Active","description":"Description"}
            widths={"order":70,"name":220,"type":130,"required":90,"active":80,"description":300}
            for c in cols: self.tree.heading(c,text=heads[c]); self.tree.column(c,width=widths[c])
            self.tree.pack(side="left",fill="both",expand=True); sb=ttk.Scrollbar(ff,orient="vertical",command=self.tree.yview); sb.pack(side="right",fill="y"); self.tree.configure(yscrollcommand=sb.set)
            b=ttk.Frame(right); b.pack(fill="x")
            self.add_field_btn = ttk.Button(b,text="+ Add Field",command=self.add_field)
            self.add_field_btn.pack(side="left",padx=3)
            self.edit_field_btn = ttk.Button(b,text="Edit Field",command=self.edit_field)
            self.edit_field_btn.pack(side="left",padx=3)
            self.delete_field_btn = ttk.Button(b,text="Delete Field",command=self.delete_field)
            self.delete_field_btn.pack(side="left",padx=3)
            self.template_btn = ttk.Button(b,text="Download Excel Template",command=self.download_template)
            self.template_btn.pack(side="left",padx=10)
            self.import_excel_btn = ttk.Button(b,text="Import Excel Data",command=self.import_excel)
            self.import_excel_btn.pack(side="left",padx=3)
            self.view_records_btn = ttk.Button(b,text="View Records",command=self.view_records)
            self.view_records_btn.pack(side="left",padx=10)
        def refresh(self):
            self.store.load(); self.lb.delete(0,tk.END); self.ids=[]
            for m in self.store.list_masters(): self.ids.append(m["master_id"]); self.lb.insert(tk.END,m["master_name"])
            self.selected=None; self.n.set("कोई Master चयनित नहीं"); self.d.set(""); self.update_master_controls(); self.refresh_fields()
        def update_master_controls(self):
            locked = False
            if self.selected:
                locked = self.store.is_system_master(self.selected)
    
            self.edit_master_btn.configure(
                state=("disabled" if locked else "normal")
            )
            self.delete_master_btn.configure(
                state=("disabled" if locked else "normal")
            )
    
            # Field buttons are created lazily below; if present, lock them too.
            if hasattr(self, "add_field_btn"):
                self.add_field_btn.configure(state=("disabled" if locked else "normal"))
            if hasattr(self, "edit_field_btn"):
                self.edit_field_btn.configure(state=("disabled" if locked else "normal"))
            if hasattr(self, "delete_field_btn"):
                self.delete_field_btn.configure(state=("disabled" if locked else "normal"))
            if hasattr(self, "template_btn"):
                self.template_btn.configure(state=("normal" if self.selected else "disabled"))
            if hasattr(self, "import_excel_btn"):
                self.import_excel_btn.configure(
                    state=("disabled" if (not self.selected or locked) else "normal")
                )
    
        def refresh_fields(self):
            for x in self.tree.get_children(): self.tree.delete(x)
            if not self.selected: return
            m=self.store.get_master(self.selected)
            if not m:return
            for f in sorted(m.get("fields",[]),key=lambda x:x.get("field_order",0)):
                self.tree.insert("", "end", iid=f["field_id"], values=(f.get("field_order"),f.get("field_name"),FIELD_TYPES.get(f.get("field_type"),f.get("field_type")), "Yes" if f.get("required") else "No","Yes" if f.get("active",True) else "No",f.get("description","")))
        def select(self,event=None):
            s=self.lb.curselection()
            if not s:return
            self.selected=self.ids[s[0]]; m=self.store.get_master(self.selected); self.n.set(m["master_name"]); self.d.set(m.get("description","")); self.update_master_controls(); self.refresh_fields()
        def download_template(self):
            if not self.selected:
                return messagebox.showwarning("Selection", "पहले Master चुनिए।", parent=self)
            m = self.store.get_master(self.selected)
            if not m:
                return
            fields = [f for f in sorted(m.get("fields", []), key=lambda x: x.get("field_order", 0))
                      if f.get("active", True)]
            if not fields:
                return messagebox.showwarning(
                    "No Active Fields",
                    "इस Master में कोई Active Field नहीं है। पहले Field जोड़िए।",
                    parent=self
                )
            safe = re.sub(r'[^A-Za-z0-9_\-\u0900-\u097F ]+', '_',
                          m.get("master_name", "Master")).strip() or "Master"
            path = filedialog.asksaveasfilename(
                parent=self,
                title="Download Excel Template",
                defaultextension=".xlsx",
                initialfile=f"{safe}_Template.xlsx",
                filetypes=[("Excel Workbook", "*.xlsx")]
            )
            if not path:
                return
            try:
                create_xlsx_template(m["master_name"], fields, path)
                messagebox.showinfo(
                    "Template Ready",
                    f"Excel Template तैयार है।\n\n{path}\n\nTemplate में केवल Active Fields के नाम columns के रूप में दिए गए हैं।",
                    parent=self
                )
            except Exception as e:
                messagebox.showerror("Excel Template Error", str(e), parent=self)
    
        def import_excel(self):
            if not self.selected:
                return messagebox.showwarning("Selection", "पहले Master चुनिए।", parent=self)
            m = self.store.get_master(self.selected)
            if not m:
                return
            if m.get("owner_type") == SYSTEM_MASTER:
                return messagebox.showwarning(
                    "Locked Master",
                    "Universal Pay Commission Master में Excel Data Import नहीं किया जा सकता।",
                    parent=self
                )
            path = filedialog.askopenfilename(
                parent=self,
                title="Import Excel Data",
                filetypes=[("Excel Workbook", "*.xlsx")]
            )
            if not path:
                return
            if not messagebox.askyesno(
                "Confirm Import",
                "Excel की rows पढ़कर इस Master का वर्तमान imported data replace किया जाएगा।\n\nक्या आगे बढ़ें?",
                parent=self
            ):
                return
            try:
                count = self.store.import_records_from_excel(self.selected, path)
                messagebox.showinfo(
                    "Import Successful",
                    f"{count} record(s) Master '{m.get('master_name')}' में import हो गए।",
                    parent=self
                )
            except Exception as e:
                messagebox.showerror("Excel Import Error", str(e), parent=self)
    
        def view_records(self):
            if not self.selected:
                return messagebox.showwarning("Selection","पहले Master चुनिए।",parent=self)
            if not self.store.get_master(self.selected):
                return messagebox.showwarning("Selection","Master नहीं मिला।",parent=self)
            RecordsWindow(self,self.store,self.selected)
    
        def add_master(self):
            name=simpledialog.askstring("Add New Master Data","Master का नाम:",parent=self)
            if name:
                try:self.store.create_master(name); self.refresh()
                except Exception as e:messagebox.showerror("Error",str(e),parent=self)
        def edit_master(self):
            if not self.selected:return messagebox.showwarning("Selection","पहले Master चुनिए।",parent=self)
            m=self.store.get_master(self.selected)
            if m.get("owner_type") == SYSTEM_MASTER:
                return messagebox.showwarning("Locked Master","Pay Commission Master [UNIVERSAL / LOCKED] को edit नहीं किया जा सकता।",parent=self)
            name=simpledialog.askstring("Edit Master","Master का नाम:",initialvalue=m["master_name"],parent=self)
            if name:
                try:self.store.update_master_info(self.selected,name,m.get("description","")); self.refresh()
                except Exception as e:messagebox.showerror("Error",str(e),parent=self)
        def delete_master(self):
            if not self.selected:
                return messagebox.showwarning("Selection","पहले Master चुनिए।",parent=self)
            m = self.store.get_master(self.selected)
            if not m:
                return messagebox.showwarning("Selection","Master नहीं मिला।",parent=self)
            if m.get("owner_type") == SYSTEM_MASTER:
                return messagebox.showwarning(
                    "Locked Master",
                    "Pay Commission Master [UNIVERSAL / LOCKED] को delete नहीं किया जा सकता।",
                    parent=self
                )
            if not messagebox.askyesno(
                "Confirm Delete",
                f"क्या '{m.get('master_name','')}' Master को delete करना है?\nयह क्रिया वापस नहीं होगी।",
                parent=self
            ):
                return
            try:
                self.store.delete_master(self.selected)
                self.refresh()
            except Exception as e:
                messagebox.showerror("Error",str(e),parent=self)
    
        def selected_field(self):
            s=self.tree.selection()
            if not s:return None
            return self.store.get_field(self.selected,s[0])
        def add_field(self):
            if not self.selected:return messagebox.showwarning("Selection","पहले Master चुनिए।",parent=self)
            if self.store.is_system_master(self.selected):
                return messagebox.showwarning("Locked Master","Universal Pay Commission Master के fields बदले नहीं जा सकते।",parent=self)
            d=FieldDialog(self); self.wait_window(d)
            if d.result:
                try:
                    x=d.result; self.store.add_field(self.selected,**x); self.refresh_fields()
                except Exception as e:messagebox.showerror("Error",str(e),parent=self)
        def edit_field(self):
            if not self.selected:return messagebox.showwarning("Selection","पहले Master चुनिए।",parent=self)
            if self.store.is_system_master(self.selected):
                return messagebox.showwarning("Locked Master","Universal Pay Commission Master के fields बदले नहीं जा सकते।",parent=self)
            old=self.selected_field()
            if not old:return messagebox.showwarning("Selection","पहले Field चुनिए।",parent=self)
            d=FieldDialog(self,deepcopy(old)); self.wait_window(d)
            if d.result:
                try:
                    x=d.result; self.store.update_field(self.selected,old["field_id"],**x); self.refresh_fields()
                except Exception as e:messagebox.showerror("Error",str(e),parent=self)
        def delete_field(self):
            if not self.selected:return
            if self.store.is_system_master(self.selected):
                return messagebox.showwarning("Locked Master","Universal Pay Commission Master के fields बदले नहीं जा सकते।",parent=self)
            old=self.selected_field()
            if not old:return messagebox.showwarning("Selection","पहले Field चुनिए।",parent=self)
            if messagebox.askyesno("Confirm",f"क्या '{old['field_name']}' हटाना है?",parent=self):
                try:self.store.delete_field(self.selected,old["field_id"]); self.refresh_fields()
                except Exception as e:messagebox.showerror("Error",str(e),parent=self)
    
    def run_gui(username="alokjobner"):
        MasterDataGUI(username).mainloop()
    
else:
    def run_gui(username="alokjobner"):
        raise RuntimeError("Tkinter GUI is not available in this Streamlit/Linux environment. Use the Streamlit Master Data interface.")
if __name__=="__main__":
    run_gui()
