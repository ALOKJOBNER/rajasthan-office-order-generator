# -*- coding: utf-8 -*-
"""Master Data Management UI - extensible, user-wise, Pay Commission protected."""
from __future__ import annotations

import hashlib
import io
import uuid
from copy import deepcopy
from datetime import datetime

import pandas as pd
import streamlit as st

PAY_TOKEN = "pay commission"
SYSTEM_OWNER = "system"


def norm(v) -> str:
    return " ".join(str(v or "").strip().casefold().split())


def is_system_master(master: dict) -> bool:
    return master.get("owner_type") == SYSTEM_OWNER or PAY_TOKEN in norm(master.get("master_name"))


def active_fields(master: dict) -> list[dict]:
    return sorted(
        [f for f in master.get("fields", []) if f.get("active", True)],
        key=lambda x: x.get("field_order", 0),
    )


def display_value(v) -> str:
    if v is None:
        return ""
    if v is True:
        return "हाँ"
    if v is False:
        return "नहीं"
    return str(v)


def convert_value(v, field: dict):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return ""
    s = str(v).strip()
    if not s:
        return ""
    typ = str(field.get("field_type", "text")).lower()
    if typ == "number":
        try:
            return int(float(s))
        except Exception:
            return s
    if typ == "decimal":
        try:
            return float(s)
        except Exception:
            return s
    if typ == "boolean":
        if norm(s) in ("yes", "true", "1", "हाँ", "हां"):
            return True
        if norm(s) in ("no", "false", "0", "नहीं"):
            return False
    return s


def validate_record(master: dict, values: dict) -> None:
    for field in active_fields(master):
        if field.get("required") and str(values.get(field["field_id"], "")).strip() == "":
            raise ValueError(f"Mandatory field '{field.get('field_name')}' खाली है।")


def make_template(master: dict) -> bytes:
    """Create an annotated Excel template for Admin and User Master Data."""
    fields = active_fields(master)
    columns = [f["field_name"] + (" *" if f.get("required") else "") for f in fields]
    data = pd.DataFrame([{c: "" for c in columns}])
    definitions = pd.DataFrame([
        {
            "Field Name": f["field_name"],
            "Field Type": f.get("field_type", "text"),
            "Mandatory": "Yes — अनिवार्य" if f.get("required") else "No — वैकल्पिक",
            "Description": f.get("description", ""),
            "Options": ", ".join(map(str, f.get("options", []))),
        } for f in fields
    ])
    instructions = pd.DataFrame({"Master Data Entry Instructions": [
        f"{master.get('master_name', 'Master Data')} — Excel Template",
        "जिस Field के नाम के आगे * लगा है, वह अनिवार्य (Mandatory) है।",
        "अनिवार्य (*) Field खाली छोड़ने पर Record Save/Excel Import नहीं होगा।",
        "वैकल्पिक Field को आवश्यकता होने पर खाली छोड़ा जा सकता है।",
        "Field_Definitions sheet में प्रत्येक Field की Mandatory स्थिति और विवरण दिया गया है।",
        "Pay Commission Master User Excel Template में शामिल नहीं किया जाता; वह Universal/Locked Master है।",
    ]})
    out = io.BytesIO()
    with pd.ExcelWriter(out, engine="openpyxl") as writer:
        data.to_excel(writer, index=False, sheet_name="Data")
        definitions.to_excel(writer, index=False, sheet_name="Field_Definitions")
        instructions.to_excel(writer, index=False, sheet_name="Instructions")
        wb = writer.book
        ws = wb["Data"]
        from openpyxl.styles import Font, PatternFill, Alignment
        from openpyxl.comments import Comment
        mandatory_fill = PatternFill(fill_type="solid", fgColor="FFF2CC")
        for col_idx, field in enumerate(fields, 1):
            cell = ws.cell(row=1, column=col_idx)
            cell.font = Font(bold=True)
            if field.get("required"):
                cell.fill = mandatory_fill
                cell.comment = Comment("अनिवार्य Field: खाली छोड़ने पर Record Save/Excel Import नहीं होगा।", "Office Order Software")
            ws.column_dimensions[cell.column_letter].width = max(16, min(32, len(str(cell.value)) + 4))
        for cell in wb["Field_Definitions"][1]:
            cell.font = Font(bold=True)
        wsi = wb["Instructions"]
        wsi.column_dimensions["A"].width = 105
        for cell in wsi["A"]:
            cell.alignment = Alignment(wrap_text=True, vertical="top")
        wsi["A1"].font = Font(bold=True, size=12)
    return out.getvalue()


def parse_excel(upload, master: dict) -> list[dict]:
    sheets = pd.read_excel(upload, sheet_name=None, dtype=object)
    df = sheets.get("Data", next(iter(sheets.values())))
    fields = active_fields(master)
    by_name = {norm(f["field_name"]): f for f in fields}
    mapping = {}
    for col in df.columns:
        key = norm(col)
        # Mandatory template headers are written as "Field Name *". Accept
        # both marked and legacy/plain headers for backward compatibility.
        key_plain = key.rstrip("*").strip()
        if key_plain == "_record_id":
            mapping[col] = "_record_id"
        elif key_plain in by_name:
            mapping[col] = by_name[key_plain]
    if not any(isinstance(x, dict) for x in mapping.values()):
        raise ValueError("Excel headers वर्तमान Master के fields से match नहीं करते।")

    result = []
    for row_no, (_, row) in enumerate(df.iterrows(), 2):
        if all(pd.isna(x) or str(x).strip() == "" for x in row.tolist()):
            continue
        values = {}
        record_id = ""
        for col, field in mapping.items():
            if field == "_record_id":
                raw = row.get(col, "")
                record_id = "" if pd.isna(raw) else str(raw).strip()
            else:
                values[field["field_id"]] = convert_value(row.get(col, ""), field)
        for field in fields:
            values.setdefault(field["field_id"], "")
        try:
            validate_record(master, values)
        except ValueError as exc:
            raise ValueError(f"Excel row {row_no}: {exc}") from exc
        values["_record_id"] = record_id
        result.append(values)
    if not result:
        raise ValueError("Excel में कोई data row नहीं मिली।")
    return result


def ensure_standard_masters(service) -> list[str]:
    """One-time, idempotent migration of requested standard masters.

    It only adds missing user fields/Student Master and deactivates the legacy
    Next Increment Date field. The protected Pay Commission Master is never touched.
    """
    changed = []
    store = service.store

    def find(name):
        return store.get_master_by_name(name)

    def add_if_missing(master, field_name, field_type="text", required=False, options=None, description=""):
        if not master:
            return
        if any(norm(f.get("field_name")) == norm(field_name) for f in master.get("fields", [])):
            return
        store.add_field(master["master_id"], field_name, field_type, required, True, options or [], description)
        changed.append(f"{master.get('master_name')}: +{field_name}")

    employee = find("Employee Master Data")
    if employee and not is_system_master(employee):
        for legacy in ("Next Increment Date", "Next Increment", "अगली वेतन वृद्धि तिथि"):
            field = next((f for f in employee.get("fields", []) if norm(f.get("field_name")) == norm(legacy)), None)
            if field and field.get("active", True):
                store.update_field(employee["master_id"], field["field_id"], active=False)
                changed.append(f"Employee Master Data: deactivated {legacy}")
        add_if_missing(employee, "Bank Name", description="कर्मचारी के बैंक का नाम")
        add_if_missing(employee, "Branch", description="बैंक शाखा")
        add_if_missing(employee, "Account Number", description="बैंक खाता संख्या")
        add_if_missing(employee, "IFSC", description="IFSC Code")

        # Safety rules for salary/pay calculation. These are enforced for both
        # Admin-owned and User-owned Employee Masters.
        employee_fields = {norm(f.get("field_name")): f for f in employee.get("fields", [])}
        gpf = employee_fields.get(norm("GPF / PRAN Number")) or employee_fields.get(norm("GPF Number"))
        if gpf and not gpf.get("required"):
            store.update_field(employee["master_id"], gpf["field_id"], required=True, active=True,
                               description="GPF/PRAN Number — यह Master Data field अनिवार्य है।")
            changed.append("Employee Master Data: GPF / PRAN Number made mandatory")
        pc = employee_fields.get(norm("Pay Commission"))
        if pc and not pc.get("required"):
            store.update_field(employee["master_id"], pc["field_id"], required=True, active=True,
                               description="लागू Pay Commission — यह field अनिवार्य है।")
            changed.append("Employee Master Data: Pay Commission made mandatory")
        basic = employee_fields.get(norm("Basic Pay"))
        if basic and not basic.get("required"):
            store.update_field(employee["master_id"], basic["field_id"], required=True, active=True,
                               description="वर्तमान मूल वेतन — यह field अनिवार्य है।")
            changed.append("Employee Master Data: Basic Pay made mandatory")
        level = employee_fields.get(norm("Pay Level")) or employee_fields.get(norm("पे लेवल"))
        if level:
            level_options = ["Fixed Pay"] + [f"L-{i}" for i in range(1, 25)]
            if level.get("field_type") != "dropdown" or level.get("options") != level_options:
                store.update_field(employee["master_id"], level["field_id"], field_type="dropdown",
                                   options=level_options, active=True,
                                   description="7th CPC Pay Level. 5th/6th CPC कर्मचारी के लिए इसे खाली रखा जा सकता है।")
                changed.append("Employee Master Data: Pay Level converted to controlled dropdown")

    component = find("Component Master Data")
    if component and not is_system_master(component):
        # Only Component Name remains mandatory. Level is deliberately optional.
        for f in component.get("fields", []):
            if norm(f.get("field_name")) != norm("Component Name") and f.get("required"):
                store.update_field(component["master_id"], f["field_id"], required=False)
                changed.append(f"Component Master Data: {f.get('field_name')} made optional")
        add_if_missing(
            component,
            "Component Level",
            field_type="dropdown",
            required=False,
            options=["Elementary", "Secondary"],
            description="Component को Elementary या Secondary में रखें।",
        )

    student = find("Student Master Data")
    if not student:
        student = store.create_master("Student Master Data", "विद्यार्थी Master Data — भविष्य के Sanchalan/अन्य मॉड्यूल उपयोग के लिए")
        changed.append("Created Student Master Data")
    student_fields = [
        ("Student Name", "text", True, "विद्यार्थी का नाम"),
        ("SR Number", "text", True, "SR/Scholar Register Number"),
        ("Class", "text", False, "कक्षा"),
        ("Father's Name", "text", False, "पिता का नाम"),
        ("Mother's Name", "text", False, "माता का नाम"),
        ("Mobile Number", "phone", False, "मोबाइल नंबर"),
        ("Bank Name", "text", True, "बैंक का नाम"),
        ("Branch", "text", True, "बैंक शाखा"),
        ("Account Number", "text", True, "बैंक खाता संख्या"),
        ("IFSC", "text", True, "IFSC Code"),
        ("Aadhaar", "text", False, "आधार संख्या"),
        ("Jan Aadhaar", "text", False, "जन आधार संख्या"),
    ]
    for name, typ, required, desc in student_fields:
        existing = next((f for f in student.get("fields", []) if norm(f.get("field_name")) == norm(name)), None)
        if existing:
            if bool(existing.get("required")) != required or not existing.get("active", True):
                store.update_field(student["master_id"], existing["field_id"], required=required, active=True)
                changed.append(f"Student Master Data: updated {name}")
        else:
            store.add_field(student["master_id"], name, typ, required, True, [], desc)
            changed.append(f"Student Master Data: +{name}")

    return changed


def render_form(service, master: dict, record: dict | None = None):
    values = {}
    fields = active_fields(master)
    # IMPORTANT: New-record and edit-record widgets must never share Streamlit
    # keys. Otherwise a blank/new form can retain its session_state and the
    # selected record appears blank when Edit is pressed.
    form_scope = f"edit_{record.get('_record_id')}" if record else "new"
    columns = st.columns(3)
    for idx, field in enumerate(fields):
        fid = field["field_id"]
        old = (record or {}).get(fid, "")
        label = field["field_name"] + (" *" if field.get("required") else "")
        with columns[idx % 2]:
            typ = str(field.get("field_type", "text")).lower()
            if typ == "dropdown":
                options = [str(x) for x in field.get("options", [])]
                if not field.get("required"):
                    options = [""] + options
                current = display_value(old)
                values[fid] = st.selectbox(
                    label,
                    options or [""],
                    index=options.index(current) if current in options else 0,
                    key=f"mdf_{master['master_id']}_{form_scope}_{fid}",
                )
            elif typ == "boolean":
                options = ["", "हाँ", "नहीं"]
                current = "हाँ" if old is True else "नहीं" if old is False else ""
                selected = st.selectbox(label, options, index=options.index(current), key=f"mdf_{master['master_id']}_{form_scope}_{fid}")
                values[fid] = True if selected == "हाँ" else False if selected == "नहीं" else ""
            else:
                values[fid] = st.text_input(label, value=display_value(old), key=f"mdf_{master['master_id']}_{form_scope}_{fid}")

    left, right = st.columns(2)
    with left:
        save = st.button("💾 Save Changes" if record else "💾 Save Record", type="primary", use_container_width=True, key=f"mdsave_{master['master_id']}_{form_scope}")
    with right:
        cancel = st.button("✖ Cancel", use_container_width=True, key=f"mdcancel_{master['master_id']}_{form_scope}")
    if cancel:
        st.session_state[f"md_mode_{master['master_id']}"] = None
        st.rerun()
    if save:
        values = {f["field_id"]: convert_value(values.get(f["field_id"], ""), f) for f in fields}
        validate_record(master, values)
        if record:
            service.store.update_record(master["master_id"], record["_record_id"], values)
        else:
            service.store.add_record(master["master_id"], values)
        st.session_state[f"md_mode_{master['master_id']}"] = None
        st.success("Record सफलतापूर्वक save/update हो गया।")
        st.rerun()



def render_admin_pay_commission_master(service):
    """Admin-only CRUD for the protected Pay Commission Master records.

    The master remains a system/locked master for normal users.  Administrator
    may correct/add/delete individual statutory master records when an approved
    correction is necessary.  Field/schema management remains locked.
    """
    if str(st.session_state.get("logged_role") or "").strip().lower() != "admin":
        st.error("⛔ Pay Commission Master केवल Administrator के लिए उपलब्ध है।")
        return

    try:
        master = service.store.ensure_pay_commission_master()
    except Exception as exc:
        st.error(f"Pay Commission Master load नहीं हुआ: {type(exc).__name__}: {exc}")
        return

    fields = active_fields(master)
    records = service.store.load_records(master["master_id"])
    st.markdown("### 🔐 Pay Commission Master — Administrator Only")
    st.warning(
        "⚠️ यह Universal Pay Commission Master है। यहाँ बदलाव केवल वास्तविक/स्वीकृत "
        "Pay Commission नियम, DA, HRA, Pay Level/Pay Matrix या Increment rule में "
        "सुधार होने पर ही करें। गलत बदलाव से PL Surrender, Annual Increment और "
        "Salary Arrear की गणना प्रभावित हो सकती है।"
    )

    if records:
        summary_fields = fields[:5]
        st.dataframe(
            pd.DataFrame([{f.get("field_name", ""): r.get(f.get("field_id"), "") for f in summary_fields} for r in records]),
            use_container_width=True, hide_index=True
        )

    labels = ["-- Select Record --"]
    for i, rec in enumerate(records, 1):
        parts = []
        for f in fields[:3]:
            v = display_value(rec.get(f.get("field_id"), ""))
            if v:
                parts.append(v)
        labels.append(f"{i}. " + " | ".join(parts) + f"  [{rec.get('_record_id','')}]")
    selected = st.selectbox("Pay Commission Record चुनें:", labels, key="admin_pc_record_select")
    selected_record = None
    if selected != labels[0] and records:
        selected_record = records[labels.index(selected) - 1]

    c1, c2, c3 = st.columns(3)
    with c1:
        add = st.button("➕ Add New Record", use_container_width=True, key="admin_pc_add")
    with c2:
        edit = st.button("✏️ Edit Selected", use_container_width=True, disabled=selected_record is None, key="admin_pc_edit")
    with c3:
        delete = st.button("🗑 Delete Selected", use_container_width=True, disabled=selected_record is None, key="admin_pc_delete")

    mode_key = "admin_pc_mode"
    if add:
        st.session_state[mode_key] = {"action": "new", "nonce": uuid.uuid4().hex}
        st.rerun()
    if edit and selected_record:
        st.session_state[mode_key] = {"action": "edit", "record_id": selected_record.get("_record_id"), "nonce": uuid.uuid4().hex}
        st.rerun()
    if delete and selected_record:
        st.session_state["admin_pc_delete_pending"] = selected_record.get("_record_id")
        st.rerun()

    pending_delete = st.session_state.get("admin_pc_delete_pending")
    if pending_delete:
        target = next((r for r in records if r.get("_record_id") == pending_delete), None)
        if target:
            st.error("⚠️ क्या आप चयनित Pay Commission record को स्थायी रूप से delete करना चाहते हैं?")
            d1, d2 = st.columns(2)
            with d1:
                if st.button("हाँ, Delete करें", type="primary", use_container_width=True, key="admin_pc_delete_confirm"):
                    data = [r for r in records if r.get("_record_id") != pending_delete]
                    service.store.save_records(master["master_id"], data)
                    st.session_state.pop("admin_pc_delete_pending", None)
                    st.session_state.pop(mode_key, None)
                    st.success("Pay Commission record delete हो गया।")
                    st.rerun()
            with d2:
                if st.button("✖ Cancel", use_container_width=True, key="admin_pc_delete_cancel"):
                    st.session_state.pop("admin_pc_delete_pending", None)
                    st.rerun()

    mode = st.session_state.get(mode_key)
    if not isinstance(mode, dict):
        return

    record = None
    if mode.get("action") == "edit":
        record = next((r for r in records if r.get("_record_id") == mode.get("record_id")), None)
        if record is None:
            st.session_state.pop(mode_key, None)
            st.warning("चयनित Pay Commission record अब उपलब्ध नहीं है।")
            return

    st.markdown("---")
    st.markdown("### ✏️ Pay Commission Master Edit" if record else "### ➕ Pay Commission Master — New Record")
    if not record:
        st.info("नया record जोड़ने के लिए सभी आवश्यक values भरें।")

    values = {}
    scope = f"{mode.get('action')}_{mode.get('record_id','new')}_{mode.get('nonce','')}"
    columns = st.columns(3)
    for idx, field in enumerate(fields):
        fid = field.get("field_id")
        old = (record or {}).get(fid, "")
        label = field.get("field_name", "") + (" *" if field.get("required") else "")
        with columns[idx % 3]:
            typ = str(field.get("field_type", "text")).lower()
            key = f"admin_pc_{scope}_{fid}"
            if typ == "dropdown":
                options = [str(x) for x in field.get("options", [])]
                if not field.get("required"):
                    options = [""] + options
                current = display_value(old)
                values[fid] = st.selectbox(label, options or [""], index=options.index(current) if current in options else 0, key=key)
            elif typ == "boolean":
                options = ["", "हाँ", "नहीं"]
                current = "हाँ" if old is True else "नहीं" if old is False else ""
                selected_bool = st.selectbox(label, options, index=options.index(current), key=key)
                values[fid] = True if selected_bool == "हाँ" else False if selected_bool == "नहीं" else ""
            else:
                values[fid] = st.text_input(label, value=display_value(old), key=key)

    s1, s2 = st.columns(2)
    with s1:
        save = st.button("💾 Save Changes" if record else "💾 Save Record", type="primary", use_container_width=True, key=f"admin_pc_save_{scope}")
    with s2:
        cancel = st.button("✖ Cancel", use_container_width=True, key=f"admin_pc_cancel_{scope}")
    if cancel:
        st.session_state.pop(mode_key, None)
        st.rerun()
    if save:
        try:
            clean = {f.get("field_id"): convert_value(values.get(f.get("field_id"), ""), f) for f in fields}
            validate_record(master, clean)
            if record:
                new_records = service.store.load_records(master["master_id"])
                for row in new_records:
                    if row.get("_record_id") == record.get("_record_id"):
                        row.update(clean)
                        row["_record_id"] = record.get("_record_id")
                        row["_updated_at"] = datetime.now().isoformat(timespec="seconds")
                        break
                else:
                    raise ValueError("Record नहीं मिला।")
            else:
                new_records = service.store.load_records(master["master_id"])
                rec = dict(clean)
                rec["_record_id"] = "REC-" + uuid.uuid4().hex[:12].upper()
                rec["_created_at"] = datetime.now().isoformat(timespec="seconds")
                rec["_updated_at"] = datetime.now().isoformat(timespec="seconds")
                new_records.append(rec)
            service.store.save_records(master["master_id"], new_records)
            st.session_state.pop(mode_key, None)
            st.success("Pay Commission Master record सफलतापूर्वक save/update हो गया।")
            st.rerun()
        except Exception as exc:
            st.error(f"Save failed: {type(exc).__name__}: {exc}")


def render_new_master(service):
    with st.expander("➕ नया Master Data बनाएं — Future Expansion", expanded=False):
        st.info("यहाँ बनाया गया सामान्य User Master आगे इसी स्क्रीन पर Manual Entry और Excel Template/Upload के साथ उपलब्ध होगा। Pay Commission Master इस सुविधा से सुरक्षित है।")
        name = st.text_input("Master Name *", key="new_master_name")
        description = st.text_input("Description", key="new_master_description")
        if st.button("Create Master", type="primary", key="create_new_master"):
            if not name.strip():
                st.error("Master Name आवश्यक है।")
            else:
                service.store.create_master(name.strip(), description.strip())
                st.success(f"'{name.strip()}' Master बनाया गया। अब Master चुनकर Fields जोड़ें।")
                st.rerun()


def render_field_manager(service, master: dict):
    if is_system_master(master):
        return
    with st.expander("🧩 इस Master के Fields प्रबंधित करें", expanded=False):
        st.caption("सामान्य User Master में आगे नए fields जोड़ सकते हैं। Existing records सुरक्षित रहेंगे।")
        fields = active_fields(master)
        if fields:
            st.dataframe(
                pd.DataFrame([
                    {"Field": f.get("field_name", ""), "Type": f.get("field_type", "text"), "Mandatory": "Yes" if f.get("required") else "No"}
                    for f in fields
                ]),
                use_container_width=True,
                hide_index=True,
            )
        with st.form(f"add_field_form_{master['master_id']}"):
            c1, c2 = st.columns(2)
            with c1:
                field_name = st.text_input("New Field Name *")
                field_type = st.selectbox("Field Type", ["text", "number", "decimal", "date", "datetime", "boolean", "dropdown", "email", "phone"])
            with c2:
                required = st.checkbox("Mandatory", value=False)
                description = st.text_input("Description")
                options_text = st.text_input("Dropdown Options (comma separated)")
            submitted = st.form_submit_button("➕ Add Field", type="primary")
        if submitted:
            options = [x.strip() for x in options_text.split(",") if x.strip()]
            try:
                service.store.add_field(master["master_id"], field_name, field_type, required, True, options, description)
                st.success("Field जोड़ दिया गया।")
                st.rerun()
            except Exception as exc:
                st.error(f"Field add नहीं हुआ: {type(exc).__name__}: {exc}")


def render(context):
    user = str(st.session_state.get("logged_username") or "").strip().lower()
    if not user:
        st.error("Login user उपलब्ध नहीं है।")
        return
    try:
        from master_data_service import get_service
        service = get_service(user)
    except Exception as exc:
        st.error(f"Master Data Service load नहीं हुआ: {type(exc).__name__}: {exc}")
        return

    st.markdown(
        """
        <style>
        .md-header {padding:14px 18px;border-radius:12px;background:linear-gradient(135deg,#123e68,#1b4f72);margin-bottom:15px;}
        .md-header-title {font-size:24px;font-weight:900;color:#f4d03f;text-align:left;}
        .md-header-sub {color:#d6eaf8;text-align:left;margin-top:3px;}
        [data-testid="stFileUploader"] section {background:#163a5b !important;border:1px solid #2e86c1 !important;border-radius:8px !important;}
        [data-testid="stFileUploader"] section > div {background:#163a5b !important;}
        [data-testid="stFileUploader"] button {background:#2980b9 !important;color:#ffffff !important;border:1px solid #3498db !important;font-weight:700 !important;}
        [data-testid="stFileUploader"] button span,
        [data-testid="stFileUploader"] button p,
        [data-testid="stFileUploader"] span,
        [data-testid="stFileUploader"] small {color:#ffffff !important;}
        </style>
        <div class="md-header"><div class="md-header-title">⚙️ Master Data Management</div><div class="md-header-sub">User-wise Manual Entry • Edit • Delete • Excel Template • Excel Upload • Future Master Expansion</div></div>
        """,
        unsafe_allow_html=True,
    )

    if st.button("⬅️ मुख्य Dashboard पर वापस जाएँ", key="md_back"):
        st.query_params["page"] = "dashboard"
        st.rerun()

    # One-time, user-scoped migration. A transient migration error must never
    # block the page or hide the Dashboard button.
    migration_key = f"md_standard_migration_v2_{user}"
    if not st.session_state.get(migration_key):
        try:
            changes = ensure_standard_masters(service)
            st.session_state[migration_key] = True
            if changes:
                st.session_state["md_migration_message"] = changes
        except Exception as exc:
            st.session_state[migration_key] = True
            st.warning(
                "Standard Master setup अभी पूरा नहीं हो सका। मौजूदा Master Data उपलब्ध है। "
                f"तकनीकी कारण: {type(exc).__name__}: {exc}"
            )

    migration_message = st.session_state.pop("md_migration_message", None)
    if migration_message:
        st.success("Master Data structure updated: " + " | ".join(migration_message))

    render_new_master(service)

    is_admin = str(st.session_state.get("logged_role") or "").strip().lower() == "admin"
    if is_admin:
        try:
            service.store.ensure_pay_commission_master()
        except Exception:
            pass
    masters = [m for m in service.list_masters(include_system=True)
               if m.get("status", "active") == "active"
               and (is_admin or not is_system_master(m))]
    masters.sort(key=lambda x: (0 if is_system_master(x) else 1, norm(x.get("master_name"))))
    if not masters:
        st.warning("कोई user Master Data उपलब्ध नहीं है।")
        return

    master_names = [m.get("master_name", "") for m in masters]
    name = st.selectbox("Master चुनें:", master_names, key="md_master")
    master = next(x for x in masters if x.get("master_name") == name)
    if is_system_master(master):
        render_admin_pay_commission_master(service)
        return

    records = service.get_records(master["master_id"])
    fields = active_fields(master)

    st.markdown(f"### {master['master_name']}  \n**Records:** {len(records)} &nbsp;&nbsp; **Fields:** {len(fields)}")

    st.info("ℹ️ **अनिवार्य Field:** जिस Field के नाम के आगे *** लगा है वह अनिवार्य है। अनिवार्य Field खाली होने पर Record Save या Excel Import नहीं होगा। Excel Template में भी * और Mandatory स्थिति दी गई है।")

    # Component Master gets a clear Elementary/Secondary view without making
    # Component Level mandatory; only Component Name is mandatory.
    component_level_fid = next((f["field_id"] for f in fields if norm(f.get("field_name")) == norm("Component Level")), None)
    visible_records = records
    if component_level_fid:
        level_filter = st.radio("Component स्तर देखें:", ["All", "Elementary", "Secondary"], horizontal=True, key="component_level_filter")
        if level_filter != "All":
            visible_records = [r for r in records if norm(r.get(component_level_fid)) == norm(level_filter)]

    left, right = st.columns(2)
    with left:
        st.download_button(
            "📥 Excel Template Download",
            make_template(master),
            file_name=master["master_name"].replace(" ", "_") + "_Template.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            key=f"md_dl_{master['master_id']}",
        )
    with right:
        uploaded = st.file_uploader(
            "📤 Excel Upload",
            type=["xlsx"],
            key=f"md_up_{master['master_id']}",
        )

    if uploaded is not None:
        try:
            pending_key = "md_pending_" + master["master_id"]
            signature = hashlib.sha256(uploaded.getvalue()).hexdigest()
            if st.session_state.get(pending_key, {}).get("sig") != signature:
                st.session_state[pending_key] = {"sig": signature, "rows": parse_excel(io.BytesIO(uploaded.getvalue()), master)}
            rows = st.session_state[pending_key]["rows"]
            mode = st.radio(
                "Excel Import Mode",
                ["Existing data में Add / Update करें", "Existing data हटाकर Replace करें"],
                horizontal=True,
                key=f"md_mode_{master['master_id']}",
            )
            if st.button("✅ Excel Data लागू करें", type="primary", key=f"md_apply_{master['master_id']}"):
                old = deepcopy(service.store.load_records(master["master_id"]))
                try:
                    if "Replace" in mode:
                        service.store.save_records(master["master_id"], [])
                        for row in rows:
                            service.store.add_record(master["master_id"], {k: v for k, v in row.items() if k != "_record_id"})
                    else:
                        existing_ids = {str(r.get("_record_id")) for r in old}
                        for row in rows:
                            rid = str(row.get("_record_id") or "").strip()
                            values = {k: v for k, v in row.items() if k != "_record_id"}
                            if rid and rid in existing_ids:
                                service.store.update_record(master["master_id"], rid, values)
                            else:
                                service.store.add_record(master["master_id"], values)
                    st.session_state.pop(pending_key, None)
                    st.success(f"{len(rows)} records Excel से लागू हुए।")
                    st.rerun()
                except Exception:
                    # Full rollback protects against partial Excel updates.
                    service.store.save_records(master["master_id"], old)
                    raise
        except Exception as exc:
            st.error(f"Excel update failed: {type(exc).__name__}: {exc}")

    render_field_manager(service, master)

    st.markdown("---")
    st.markdown("### 📋 Existing Records")
    if visible_records:
        table = pd.DataFrame([{f["field_name"]: r.get(f["field_id"], "") for f in fields} for r in visible_records])
        st.dataframe(table, use_container_width=True, hide_index=True)
    else:
        st.info("इस Master में selected category के अनुसार कोई record नहीं है।")

    first_field = fields[0]["field_id"] if fields else None
    labels = ["-- Select Record --"] + [f"{i+1}. {display_value(r.get(first_field, ''))}" for i, r in enumerate(visible_records)] if first_field else ["-- Select Record --"]
    selected = st.selectbox("Record चुनें:", labels, key=f"md_rec_{master['master_id']}")

    selected_record = None
    if selected != "-- Select Record --" and visible_records:
        selected_record = visible_records[labels.index(selected) - 1]

    # Record actions: Add New is always available for normal User Masters.
    # Edit/Delete act only on the currently selected record.
    mode_key = f"md_mode_{master['master_id']}"
    mode = st.session_state.get(mode_key)
    locked = is_system_master(master)
    c_add, c_edit, c_delete = st.columns(3)
    with c_add:
        if st.button("➕ Add New Record", key=f"md_add_btn_{master['master_id']}", use_container_width=True, disabled=locked):
            st.session_state[mode_key] = "new"
            st.rerun()
    with c_edit:
        if st.button("✏️ Edit Selected", key=f"md_edit_btn_{master['master_id']}", use_container_width=True, disabled=locked or selected_record is None):
            st.session_state[mode_key] = {"action": "edit", "record_id": selected_record["_record_id"]}
            st.rerun()
    with c_delete:
        if st.button("🗑 Delete Selected", key=f"md_del_btn_{master['master_id']}", use_container_width=True, disabled=locked or selected_record is None):
            service.store.delete_record(master["master_id"], selected_record["_record_id"])
            st.session_state[mode_key] = None
            st.success("Record delete हो गया।")
            st.rerun()

    # The form mode is per-master, so one master cannot accidentally reuse another
    # master's edit/new record state. Add New always opens a genuinely blank form;
    # Edit Selected opens the selected record's complete values.
    if isinstance(mode, dict) and mode.get("action") == "edit":
        edit_id = mode.get("record_id")
        record = next((r for r in service.get_records(master["master_id"]) if r.get("_record_id") == edit_id), None)
        if record:
            st.markdown("---")
            st.markdown("### ✏️ Edit Record")
            render_form(service, master, record)
        else:
            st.session_state[mode_key] = None
    elif mode == "new":
        st.markdown("---")
        st.markdown("### ➕ Add New Record")
        render_form(service, master, None)


def render_admin_pay_commission_page(context=None):
    """Dedicated Administrator-only Pay Commission Master page."""
    if str(st.session_state.get("logged_role") or "").strip().lower() != "admin":
        st.error("⛔ यह पृष्ठ केवल Administrator के लिए है।")
        return
    user = str(st.session_state.get("logged_username") or "").strip().lower()
    if not user:
        st.error("Administrator Login user उपलब्ध नहीं है।")
        return
    try:
        from master_data_service import get_service
        service = get_service(user)
        service.store.ensure_pay_commission_master()
    except Exception as exc:
        st.error(f"Pay Commission Master Service load नहीं हुआ: {type(exc).__name__}: {exc}")
        return
    if st.button("⬅️ Master Data Management पर वापस जाएँ", key="admin_pc_back", use_container_width=True):
        st.query_params["page"] = "master_data"
        st.rerun()
    st.markdown("<div class='md-header'><div class='md-header-title'>🔐 Pay Commission Master</div><div class='md-header-sub'>Administrator Only • 6th CPC • 7th CPC • DA • HRA • Pay Matrix • Increment Rules</div></div>", unsafe_allow_html=True)
    render_admin_pay_commission_master(service)
