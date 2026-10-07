# -*- coding: utf-8 -*-
"""Extracted from the verified working app.py.
Only module organization was changed; extracted UI/business logic is preserved.
"""

import io
from html import escape
import re
import pandas as pd
import shutil
from datetime import datetime as _datetime


def _norm(value):
    return " ".join(str(value or "").strip().casefold().split())

def _clean(value):
    if pd.isna(value):
        return ""
    return str(value).strip()

def _load_component_master_by_level(username):
    """Load Component Master records and strictly separate SEC/ELE.

    Master Data Management is the authoritative source.  We deliberately do
    not merge the built-in SNA component list with user Master Data because
    doing so causes Elementary/Secondary cross-contamination in Sanchalan.
    """
    result = {"SEC": [], "ELE": []}
    username = str(username or "").strip().lower()
    if not username:
        return result
    try:
        from master_data_service import get_service
        svc = get_service(username)
        masters = svc.list_masters(include_system=False) or []
        master = next(
            (m for m in masters if _norm(m.get("master_name", "")) == _norm("Component Master Data")),
            None,
        )
        if not master:
            return result

        fields = svc.get_field_definitions(master["master_id"]) or []
        def field_id(*names):
            wanted = {_norm(x) for x in names}
            for f in fields:
                if _norm(f.get("field_name", "")) in wanted:
                    return f.get("field_id")
            return None

        name_id = field_id("Component Name", "Component Name ")
        level_id = field_id("Component Level", "LEVEL", "Level")
        code_id = field_id("Component Code", "CODE", "Code")
        active_id = field_id("Active", "ACTIVE", "Is Active")
        if not name_id:
            return result

        records = svc.get_records(master["master_id"], active_only=False) or []
        seen = {"SEC": set(), "ELE": set()}
        for rec in records:
            if not isinstance(rec, dict) or rec.get("_active") is False:
                continue
            name = _clean(rec.get(name_id, ""))
            if not name:
                continue

            active_value = _norm(rec.get(active_id, "")) if active_id else ""
            if active_value in {"no", "false", "0", "inactive", "नहीं"}:
                continue

            raw_level = _clean(rec.get(level_id, "")) if level_id else ""
            level = _norm(raw_level)
            if level in {"secondary", "sec", "secondary (sec)", "secondary upto xii"}:
                bucket = "SEC"
            elif level in {"elementary", "ele", "elementary (ele)"}:
                bucket = "ELE"
            else:
                # Compatibility fallback for older Component Master records
                # which did not yet contain a Component Level field.  Prefer
                # an explicit level marker in the component name, then code.
                name_norm = _norm(name)
                if ("elementary" in name_norm or "(elem.)" in name_norm
                        or "(elementary)" in name_norm):
                    bucket = "ELE"
                elif "secondary" in name_norm or "(sec.)" in name_norm or "(secondary)" in name_norm:
                    bucket = "SEC"
                else:
                    code = _clean(rec.get(code_id, "")) if code_id else ""
                    c = _norm(code).replace("-", " ")
                    if c.startswith("sec ") or c.startswith("sec_"):
                        bucket = "SEC"
                    elif c.startswith("ele ") or c.startswith("ele_"):
                        bucket = "ELE"
                    else:
                        continue

            key = _norm(name)
            if key in seen[bucket]:
                continue
            seen[bucket].add(key)
            result[bucket].append(name)

        result["SEC"].sort(key=lambda x: _norm(x))
        result["ELE"].sort(key=lambda x: _norm(x))
    except Exception:
        # A missing/broken master should not crash the whole Sanchalan page.
        # The caller will show the normal "no component" message.
        return {"SEC": [], "ELE": []}
    return result


def _find_devanagari_font(bold=False):
    """Find a real Devanagari TTF on Windows/Linux without hard-coding one path."""
    from pathlib import Path
    import os
    import glob
    candidates = []
    win_dirs = [r"C:\Windows\Fonts", r"C:\WinNT\Fonts"]
    linux_dirs = [
        "/usr/share/fonts/truetype/noto",
        "/usr/share/fonts/opentype/noto",
        "/usr/share/fonts/truetype/lohit-devanagari",
        "/usr/share/fonts/truetype/dejavu",
    ]
    patterns_bold = ["NirmalaUI-Bold.ttf", "NirmalaB.ttf", "Mangalb.ttf", "NotoSansDevanagari-Bold.ttf", "NotoSansDevanagari-SemiBold.ttf"]
    patterns_regular = ["NirmalaUI.ttf", "Nirmala.ttf", "Mangal.ttf", "NotoSansDevanagari-Regular.ttf", "Lohit-Devanagari.ttf"]
    for d in win_dirs + linux_dirs:
        if not os.path.isdir(d):
            continue
        for name in (patterns_bold if bold else patterns_regular):
            candidates.append(os.path.join(d, name))
        # Last-resort glob for Windows font naming variants.
        for pat in (["*Nirmala*", "*NotoSansDevanagari*", "*Mangal*"] if bold else ["*Nirmala*", "*NotoSansDevanagari-Regular*", "*Lohit-Devanagari*"]):
            candidates.extend(glob.glob(os.path.join(d, pat + ".ttf")))
    # Matplotlib is often installed with this application and can locate
    # fonts from the system font registry even when Windows uses a different filename.
    try:
        from matplotlib import font_manager
        for family in (["Nirmala UI", "Noto Sans Devanagari", "Mangal"] if bold else ["Nirmala UI", "Noto Sans Devanagari", "Mangal", "Lohit Devanagari"]):
            try:
                path = font_manager.findfont(family, fallback_to_default=False)
                if path and Path(path).exists():
                    candidates.insert(0, path)
            except Exception:
                pass
    except Exception:
        pass
    seen = set()
    for item in candidates:
        try:
            path = str(Path(item))
            if path in seen:
                continue
            seen.add(path)
            if Path(path).exists():
                return path
        except Exception:
            continue
    return None



def _canonical_component_name(name):
    """Return a stable display/group name for equivalent component spellings."""
    s = _clean(name)
    key = _norm(s).replace("&", "and")
    key = re.sub(r"\s+", " ", key)
    # The existing data contains historical spellings of the same Youth & Eco Club.
    if key in {
        "yuth and eco club",
        "youth and eco club",
        "youth & eco club",
    }:
        return "Youth and Eco Club"
    return s

def _parse_bill_voucher_date(value):
    """Extract the actual Bill/Voucher date for sanction ordering.

    The sanction sequence must never use Sanction Date.  Bill/Voucher values in
    existing records commonly look like ``243/19-08-2026`` or
    ``252/03-10-2026``; the helper also accepts slash-separated dates and
    datetime-like values.  Missing/unreadable dates sort after dated entries.
    """
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return _datetime.max
    if hasattr(value, "to_pydatetime"):
        try:
            value = value.to_pydatetime()
        except Exception:
            pass
    if isinstance(value, _datetime):
        return value
    text = str(value).strip()
    if not text:
        return _datetime.max
    # Prefer the date portion embedded in a bill/voucher number.
    patterns = (
        r"(?<!\d)(\d{1,2})[-/](\d{1,2})[-/](\d{4})(?!\d)",
        r"(?<!\d)(\d{4})[-/](\d{1,2})[-/](\d{1,2})(?!\d)",
    )
    for pat in patterns:
        m = re.search(pat, text)
        if not m:
            continue
        try:
            a, b, c = (int(x) for x in m.groups())
            if len(m.group(1)) == 4:
                return _datetime(a, b, c)
            return _datetime(c, b, a)
        except ValueError:
            continue
    # Last compatibility attempt for a plain date string.
    for fmt in ("%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d", "%Y/%m/%d", "%d-%m-%y", "%d/%m/%y"):
        try:
            return _datetime.strptime(text, fmt)
        except ValueError:
            pass
    return _datetime.max


def _prepare_sanction_groups(items):
    """Create one common, deterministic Component+Level dataset for PDF/Excel.

    IMPORTANT: entry order in the saved list is deliberately ignored at
    sanction-generation time.  The output sequence is always:
      1. all Secondary (SEC) component groups;
      2. all Elementary (ELE) component groups.
    Within each level, component groups are ordered by their earliest
    Bill/Voucher date, and entries inside every component are ordered by
    Bill/Voucher date (oldest -> newest).  Sanction Date is never used.

    Component identity remains (Level + canonical Component Name), so a
    same-named component that legitimately exists in both SEC and ELE remains
    in its selected level instead of being merged across levels.
    """
    groups = []
    index = {}
    for original_index, original in enumerate(items or []):
        if not isinstance(original, dict):
            continue
        comp = str(original.get("comp_rem", "") or "")
        if comp.startswith("[SEC]"):
            level = "SEC"
            name = comp[5:].strip()
        elif comp.startswith("[ELE]"):
            level = "ELE"
            name = comp[5:].strip()
        else:
            level = ""
            name = comp.strip()
        name = _canonical_component_name(name)
        key = (level, _norm(name))
        if key not in index:
            index[key] = len(groups)
            groups.append({
                "level": level,
                "name": name,
                "items": [],
                "total": 0.0,
                "_first_bill_date": _datetime.max,
                "_first_input_index": original_index,
            })
        row = dict(original)
        row["comp_rem"] = f"[{level}] {name}" if level else name
        try:
            amount = float(row.get("amount", 0) or 0)
        except Exception:
            amount = 0.0
        row["_group_key"] = key
        row["_input_index"] = original_index
        row["_bill_sort_date"] = _parse_bill_voucher_date(row.get("bill", ""))
        groups[index[key]]["items"].append(row)
        groups[index[key]]["total"] += amount

    # Sort entries inside each Component+Level group by Bill/Voucher date only.
    # The original input index is only a deterministic tie-breaker when two
    # entries have the same bill date; it is never the primary sequence.
    for g in groups:
        g["items"].sort(key=lambda r: (r.get("_bill_sort_date", _datetime.max), r.get("_input_index", 0)))
        if g["items"]:
            g["_first_bill_date"] = g["items"][0].get("_bill_sort_date", _datetime.max)

    # First every Secondary component, then every Elementary component.
    # Within each level, use the earliest Bill/Voucher date of the component as
    # its position; component name/input index are only deterministic tie-breakers.
    level_rank = {"SEC": 0, "ELE": 1}
    groups.sort(key=lambda g: (
        level_rank.get(g.get("level", ""), 2),
        g.get("_first_bill_date", _datetime.max),
        _norm(g.get("name", "")),
        g.get("_first_input_index", 0),
    ))

    serial = 1
    for g in groups:
        for row in g["items"]:
            row["_display_sno"] = serial
            serial += 1
    return groups

def _grouped_items_flat(items):
    groups = _prepare_sanction_groups(items)
    return [row for g in groups for row in g["items"]]

def _estimate_payment_row_height_mm(vals):
    """Estimate a rendered table row without the old overly-conservative padding.

    The estimate is intentionally close to the browser-rendered row height so that
    the pagination engine uses the available A4-landscape page area efficiently.
    A row is never split; if one row is unusually tall it is kept intact.
    """
    def lines(value, chars):
        s = str(value or "")
        if not s:
            return 1
        return max(1, (len(s) + chars - 1) // chars) + s.count("\n")

    reimb = str(vals.get("reimb_status", ""))
    bank = str(vals.get("bank_ifsc", ""))
    role = str(vals.get("payment_type", ""))
    recipient = str(vals.get("payment_recipient", ""))
    if role == "Staff Reimbursement" or "Paid by Staff:" in reimb or "भुगतान: " in reimb:
        staff = recipient or (reimb.split(":", 1)[1].rstrip(")").strip() if ":" in reimb else "संबंधित स्टाफ कर्मचारी")
        bank += f" बिल का भुगतान स्टाफ कर्मचारी {staff} द्वारा फर्म को किया जा चुका है; अतः पुनर्भरण सीधे संबंधित स्टाफ कर्मचारी को किया जा रहा है।"
    elif role == "Beneficiary" or "Not Applicable" in reimb:
        bank += f" भुगतान लाभार्थी {recipient or vals.get('firm','')} को सीधे किया जा रहा है।"
    elif role == "Vendor":
        bank += f" भुगतान संबंधित वेंडर/फर्म {recipient or vals.get('firm','')} को सीधे किया जा रहा है।"

    max_lines = max(
        lines(vals.get("inst", ""), 30),
        lines(vals.get("firm", ""), 18),
        lines(bank, 48),
        lines(vals.get("bill", ""), 18),
        lines(reimb, 16),
        lines(vals.get("comp_rem", ""), 24),
    )
    # Previous 3.7mm-per-line estimate created unnecessary 3-page output.
    return min(24.0, max(12.0, 3.5 + max_lines * 2.7))


def _paginate_sanction_groups(groups):
    """Paginate by actual usable space, reserving the final signature/copy block.

    The first page carries the office heading/introduction; continuation pages only
    carry the table heading. The final page reserves room for: final component
    total, first seal, grand total, copies and second seal. Rows are never split.
    """
    all_rows = [row for g in groups for row in g["items"]]
    if not all_rows:
        return [[]]

    def row_h(row):
        return _estimate_payment_row_height_mm(row)

    def overhead_for(index):
        row = all_rows[index]
        key = row.get("_group_key")
        prev_key = all_rows[index - 1].get("_group_key") if index > 0 else None
        next_key = all_rows[index + 1].get("_group_key") if index + 1 < len(all_rows) else None
        overhead = 6.5 if key != prev_key else 0.0
        if key != next_key:
            overhead += 6.5
        return overhead

    def span_height(start, end):
        return sum(row_h(all_rows[i]) + overhead_for(i) for i in range(start, end))

    # Use the available page height aggressively. Only the final page reserves
    # space for the final summary/grand-total/copy/seal block. Earlier pages are
    # filled sequentially until the next complete row/group cannot fit.
    first_capacity = 145.0
    middle_capacity = 158.0
    final_table_capacity = 92.0

    n = len(all_rows)

    # Find the largest final suffix that fits in the reserved final-page table
    # area. This prevents an unnecessarily early page break (the old 4+4+2 bug).
    final_start = n
    used = 0.0
    for i in range(n - 1, -1, -1):
        add = row_h(all_rows[i]) + overhead_for(i)
        if final_start < n and used + add > final_table_capacity:
            break
        if final_start == n and add > final_table_capacity:
            final_start = i
            used += add
            break
        used += add
        final_start = i

    # If the whole dataset itself fits on one page including the final block, keep
    # it on one page. Otherwise reserve the suffix for the final page.
    final_reserved_total = 68.0
    if span_height(0, n) + final_reserved_total <= first_capacity:
        return [all_rows]

    chunks = []
    pos = 0
    first = True

    while pos < final_start:
        capacity = first_capacity if first else middle_capacity
        start = pos
        used = 0.0
        while pos < final_start:
            add = row_h(all_rows[pos]) + overhead_for(pos)
            if pos > start and used + add > capacity:
                break
            used += add
            pos += 1
        if pos == start:
            pos += 1
        chunks.append(all_rows[start:pos])
        first = False

    # Final page always gets the reserved suffix.
    if final_start < n:
        chunks.append(all_rows[final_start:])
    elif not chunks:
        chunks.append(all_rows)

    return chunks

def _extract_block_name(office):
    m = re.search(r"पंचायत\s*समिति\s+([^,|]+)", str(office or ""))
    if m:
        return m.group(1).strip()
    m = re.search(r"(?:ब्लॉक|Block)\s*[:\-]?\s*([^,|]+)", str(office or ""), re.I)
    return m.group(1).strip() if m else "संबंधित ब्लॉक"

def _build_copy_lines(items, office):
    institutions = []
    seen = set()
    for row in items or []:
        name = _clean(row.get("inst", ""))
        k = _norm(name)
        if name and k not in seen:
            seen.add(k)
            institutions.append(name)
    block = _extract_block_name(office)
    lines = [
        f"1. श्रीमान मुख्य ब्लॉक शिक्षा अधिकारी, {block}।",
        "2. स्थानीय PEEO/UCEEO कार्यालय लेखा शाखा।",
    ]
    if institutions:
        joined = "<br>".join(
            f"&nbsp;&nbsp;&nbsp;({i}) {escape(inst)}" for i, inst in enumerate(institutions, 1)
        )
        lines.append(f"3. निम्नलिखित संबंधित शिक्षण संस्थानों के संस्था प्रधानों को:<br>{joined}")
    else:
        lines.append("3. संबंधित शिक्षण संस्थान के संस्था प्रधानों को।")
    lines.append("4. रक्षित पत्रावली।")
    return lines


def _build_sanction_pdf_bytes(office, district, order_no, order_date, items, developer_text):
    """Generate the final A4-landscape sanction PDF.

    PDF and Excel use the same grouped dataset. Component+level groups are kept
    contiguous, each group's total is printed immediately below its entries,
    and the separate component-summary table is intentionally removed.
    """
    from html import escape as _html_escape
    from pathlib import Path as _Path
    import os as _os
    import subprocess as _subprocess
    import tempfile as _tempfile

    def esc(v):
        return _html_escape(str(v or ""), quote=True)

    def nl(v):
        return esc(v).replace("\n", "<br>")

    def money(v):
        try:
            return f"{float(v or 0):,.2f}"
        except Exception:
            return "0.00"

    date_text = order_date.strftime("%d/%m/%Y") if hasattr(order_date, "strftime") else str(order_date)
    groups = _prepare_sanction_groups(items)
    grouped_items = [row for g in groups for row in g["items"]]
    chunks = _paginate_sanction_groups(groups)
    group_totals = {(g["level"], _norm(g["name"])): g["total"] for g in groups}
    group_names = {(g["level"], _norm(g["name"])): g["name"] for g in groups}

    headers = [
        "क.स.",
        "मुख्य ब्लॉक शिक्षा अधिकारी आदेश क्रमांक",
        "संस्था का नाम",
        "फर्म का नाम /<br>प्राप्तकर्ता",
        "खाता संख्या व IFSC कोड /<br>विशिष्ट टिप्पणी",
        "बिल/वाउचर सं.<br>एवं दिनांक",
        "राशि (₹)",
        "पुनर्भरण",
        "कंपोनेंट व स्तर<br>(SEC/ELE)",
    ]
    col_pct = [3.5, 12.0, 15.5, 10.0, 27.0, 8.0, 5.5, 10.0, 8.5]

    def payment_row(vals):
        reimb = str(vals.get("reimb_status", ""))
        bank = str(vals.get("bank_ifsc", ""))
        role = str(vals.get("payment_type", ""))
        recipient = str(vals.get("payment_recipient", ""))
        if role == "Staff Reimbursement" or "Paid by Staff:" in reimb or "भुगतान: " in reimb:
            staff = recipient or (reimb.split(":", 1)[1].rstrip(")").strip() if ":" in reimb else "संबंधित स्टाफ कर्मचारी")
            bank += f"\nबिल का भुगतान स्टाफ कर्मचारी {staff} द्वारा फर्म को किया जा चुका है; अतः पुनर्भरण सीधे संबंधित स्टाफ कर्मचारी को किया जा रहा है।"
        elif role == "Beneficiary" or "Not Applicable" in reimb:
            bank += f"\nभुगतान लाभार्थी {recipient or vals.get('firm','')} को सीधे किया जा रहा है।"
        elif role == "Vendor":
            bank += f"\nभुगतान संबंधित वेंडर/फर्म {recipient or vals.get('firm','')} को सीधे किया जा रहा है।"
        comp = str(vals.get("comp_rem", ""))
        level = "SEC" if comp.startswith("[SEC]") else ("ELE" if comp.startswith("[ELE]") else "")
        return f"""
        <tr class="entry-row">
          <td class="c">{vals.get('_display_sno','')}</td>
          <td class="c">{nl(vals.get('cbeo_order_no',''))}</td>
          <td class="institution">{nl(vals.get('inst',''))}</td>
          <td class="c strong">{nl(vals.get('firm',''))}</td>
          <td class="bank">{nl(bank)}</td>
          <td class="c">{nl(vals.get('bill',''))}</td>
          <td class="money">{money(vals.get('amount',0))}</td>
          <td class="c">{nl(reimb)}</td>
          <td class="c">{esc(level)}</td>
        </tr>"""

    def group_header(level, name, continued=False):
        level_text = "Secondary (SEC)" if level == "SEC" else ("Elementary (ELE)" if level == "ELE" else level)
        suffix = " — जारी" if continued else ""
        level_class = "sec-group" if level == "SEC" else ("ele-group" if level == "ELE" else "other-group")
        return f"<tr class='group-header {level_class}'><td colspan='9'>{esc(level_text)} — {esc(name)}{suffix}</td></tr>"

    def group_total(level, name, amount):
        level_text = "SEC" if level == "SEC" else ("ELE" if level == "ELE" else level)
        return f"""
        <tr class="component-total">
          <td colspan="9">कंपोनेंट कुल — {esc(level_text)} {esc(name)} <span class="component-total-amount">₹ {money(amount)}</span></td>
        </tr>"""

    flat_index = {id(row): i for i, row in enumerate(grouped_items)}

    def payment_table(subset, is_first_page, is_final_page):
        head = "".join(f"<th>{h}</th>" for h in headers)
        body = []
        for local_idx, row in enumerate(subset):
            key = row.get("_group_key")
            global_idx = flat_index[id(row)]
            starts = local_idx == 0 or subset[local_idx - 1].get("_group_key") != key
            if starts:
                already_started = global_idx > 0 and grouped_items[global_idx - 1].get("_group_key") == key
                body.append(group_header(key[0], group_names.get(key, row.get("comp_rem","")), continued=already_started))
            body.append(payment_row(row))
            next_key = subset[local_idx + 1].get("_group_key") if local_idx + 1 < len(subset) else None
            global_next_key = grouped_items[global_idx + 1].get("_group_key") if global_idx + 1 < len(grouped_items) else None
            if next_key != key and global_next_key != key:
                body.append(group_total(key[0], group_names.get(key, row.get("comp_rem","")), group_totals.get(key, 0.0)))

        return f"""
        <table class="payment-table">
          <colgroup>{''.join(f'<col style="width:{p}%">' for p in col_pct)}</colgroup>
          <thead><tr>{head}</tr></thead>
          <tbody>{''.join(body)}</tbody>
        </table>"""

    grand_total = sum(float(x.get("amount", 0) or 0) for x in grouped_items)

    def header_html():
        return f"""
        <div class="header">
          <div class="office">कार्यालय {nl(office)}</div>
          <div class="district">जिला : {nl(district)}</div>
          <div class="order-title">भुगतान स्वीकृति आदेश</div>
        </div>
        <div class="meta">
          <div><b>क्रमांक:</b> {nl(order_no)}</div>
          <div class="date"><b>दिनांक:</b> {esc(date_text)}</div>
        </div>
        <div class="intro">
          राजस्थान स्कूल शिक्षा परिषद जयपुर द्वारा प्रदत्त निर्देशानुसार संचालन पोर्टल से भुगतान किये जाने की प्रक्रिया के अन्तर्गत स्थानीय विद्यालय / अधोहस्ताक्षकर्ता के नियंत्रणाधीन संबंधित संस्थाओं हेतु जारी मद में जारी संचालन पोर्टल लिमिट से सम्बन्धित वेंडर / बेनिफिशियरी को निम्नानुसार भुगतान किये जाने की स्वीकृति प्रदान की जाती है:-
        </div>"""

    copy_lines = _build_copy_lines(grouped_items, office)
    copy_html = "<br>".join(copy_lines)

    first_inst = grouped_items[0].get("inst", "") if grouped_items else office
    seal_name = make_short_name(first_inst)

    def seal_html():
        # Right-hand side area; all three lines are centered on the same axis.
        return f"""
        <div class="seal-area">
          <div class="seal-box">
            <div><b>हस्ताक्षर मय सील</b></div>
            <div>प्रधानाचार्य / पीईईओ</div>
            <div>{nl(seal_name)}</div>
          </div>
        </div>"""

    def component_summary_html():
        rows = []
        for g in groups:
            level_text = "Secondary (SEC)" if g["level"] == "SEC" else ("Elementary (ELE)" if g["level"] == "ELE" else g["level"])
            rows.append(
                f'<div class="summary-line"><span>{esc(level_text)} — {esc(g["name"])}</span><strong>₹ {money(g["total"])}</strong></div>'
            )
        return f"""
        <div class="component-summary">
          <div class="summary-title">कंपोनेंट-वार संक्षिप्त योग</div>
          {''.join(rows)}
        </div>"""

    def final_block():
        # Final page order: component summary -> grand total -> first seal ->
        # order number/copies -> second seal. Both seals use the same right-side
        # center axis.
        return f"""
        {component_summary_html()}
        <div class="grand-total">
          <span>कुल योग (Grand Total):</span>
          <strong>₹ {money(grand_total)}</strong>
        </div>
        {seal_html()}
        <div class="copy-block">
          <div class="copy-meta"><b>क्रमांक:</b> {nl(order_no)} <span class="copy-date"><b>दिनांक:</b> {esc(date_text)}</span></div>
          <div class="copy-heading">प्रतिलिपि :- सूचनार्थ एवं आवश्यक कार्यवाही हेतु प्रेषित :-</div>
          <div class="copy-lines">{copy_html}</div>
        </div>
        {seal_html()}
        """

    def page_shell(content, first=False, final=False):
        return f"""
        <section class="page {'first-page' if first else ''} {'final-page' if final else ''}">
          <div class="page-border"></div>
          <div class="page-content">{content}</div>
          <div class="footer-left">{esc(developer_text)}</div>
        </section>"""

    pages = []
    for page_index, chunk in enumerate(chunks):
        first = page_index == 0
        final = page_index == len(chunks) - 1
        content = header_html() if first else f'<div class="continued-title">भुगतान स्वीकृति आदेश — शेष भुगतान विवरण<br><span class="continued-order">क्रमांक: {esc(order_no)}</span></div>'
        content += payment_table(chunk, first, final)
        if final:
            content += final_block()
        pages.append(page_shell(content, first=first, final=final))

    html = f"""<!doctype html>
<html lang="hi"><head><meta charset="utf-8"><style>
@page {{ size: A4 landscape; margin: 8mm 9mm 9mm 9mm; }}
* {{ box-sizing:border-box; }}
html, body {{ margin:0; padding:0; background:#fff; }}
body {{ font-family:"Nirmala UI","Mangal","Noto Sans Devanagari",Arial,sans-serif; color:#000; font-size:9.1pt; line-height:1.12; }}
.page {{ position:relative; width:100%; min-height:178mm; height:178mm; page-break-after:always; padding:4mm 4mm 7mm 4mm; overflow:visible; }}
.page:last-child {{ page-break-after:auto; }}
.page-border {{ position:absolute; left:0; right:0; top:0; bottom:5mm; border:1.25pt solid #000; pointer-events:none; }}
.page-content {{ position:relative; z-index:1; width:100%; }}
.footer-left {{ position:absolute; left:4mm; bottom:-3.6mm; font-size:7pt; font-style:italic; white-space:nowrap; }}
.header {{ text-align:center; }}
.office {{ display:inline-block; background:#0b4f8a; color:#fff; border:1pt solid #083b68; border-radius:2mm; padding:1.8mm 8mm; font-size:15.5pt; font-weight:700; line-height:1.12; }}
.district {{ display:inline-block; color:#8b1e3f; background:#fff0f5; border-bottom:1pt solid #d36b8a; padding:1mm 6mm; margin-top:1mm; font-size:12pt; font-weight:700; line-height:1.05; }}
.order-title {{ background:#ffe8a3; color:#6b3f00; border:1pt solid #d6a62a; border-radius:1.5mm; padding:1.5mm 3mm; font-size:16.5pt; font-weight:700; margin-top:4mm; margin-bottom:3mm; }}
.meta {{ display:flex; justify-content:space-between; align-items:flex-end; font-size:9.7pt; margin-bottom:1.4mm; color:#123a63; }}
.meta .date {{ text-align:right; }}
.intro {{ width:100%; background:#eef7ff; border-left:3pt solid #1683c5; padding:1.8mm 2.2mm; font-size:8.5pt; line-height:1.1; text-align:left; margin-bottom:2mm; }}
.continued-title {{ text-align:center; font-size:12pt; font-weight:700; margin:1mm 0 3mm 0; }}
.continued-order {{ font-size:8.7pt; font-weight:600; }}
table {{ border-collapse:collapse; width:100%; table-layout:fixed; }}
.payment-table {{ font-size:8.0pt; }}
.payment-table th, .payment-table td {{ border:.6pt solid #000; padding:1.35mm 1.1mm; vertical-align:middle; overflow-wrap:anywhere; }}
.payment-table th {{ background:#0b4f8a; color:#fff; border-color:#083b68; text-align:center; font-size:8.3pt; line-height:1.03; font-weight:700; }}
.payment-table td {{ line-height:1.06; }}
.payment-table td.c {{ text-align:center; }}
.payment-table td.bank {{ text-align:left; }}
.payment-table td.money {{ text-align:right; white-space:nowrap; }}
.payment-table td.institution {{ color:#174a7c; font-weight:700; }}
.payment-table .sec-group td {{ background:#dff1ff; color:#0b4f8a; }}
.payment-table .ele-group td {{ background:#e8f7e9; color:#176b2c; }}
.payment-table .group-header td, .group-header {{ background:#dff1ff; color:#0b4f8a; border-color:#5aa9d6; font-weight:700; text-align:left; font-size:8.7pt; }}
.payment-table .component-total td {{ font-weight:700; background:#fff0d9; color:#7a3e00; border-color:#d99a52; }}
.payment-table .component-total td:first-child {{ text-align:right; }}
.component-total-amount {{ float:right; white-space:nowrap; margin-left:8mm; }}
.component-summary {{ margin-top:2.5mm; border:1pt solid #4d8c57; background:#f1fbf2; padding:1.5mm 2.5mm; font-size:8.7pt; }}
.summary-title {{ color:#176b2c; background:#d9f2dd; font-weight:700; text-align:center; margin-bottom:1mm; padding:1mm; }}
.summary-line {{ display:flex; justify-content:space-between; align-items:center; border-bottom:.5pt solid #555; padding:.65mm 0; }}
.summary-line:last-child {{ border-bottom:none; }}
.strong {{ font-weight:700; }}
.grand-total {{ display:flex; justify-content:flex-end; align-items:center; gap:12mm; border:1.2pt solid #b0185a; background:#ffe4f1; color:#8a0d46; padding:2.2mm 3mm; margin-top:2.5mm; font-size:10.5pt; font-weight:700; }}
.copy-block {{ margin-top:4mm; font-size:8.9pt; line-height:1.16; }}
.copy-meta {{ margin-bottom:1.3mm; }}
.copy-date {{ float:right; }}
.copy-heading {{ color:#8b1e3f; background:#fff0f5; border-left:3pt solid #d36b8a; padding:1mm 1.5mm; font-weight:700; margin-bottom:1mm; }}
.copy-lines {{ line-height:1.16; }}
.seal-area {{ width:100%; display:flex; justify-content:flex-end; margin-top:3mm; padding-right:8mm; }}
.seal-box {{ width:58mm; text-align:center; font-size:9.5pt; line-height:1.18; margin:0; padding:2mm 3mm; border:1pt solid #4c78a8; background:#f0f7ff; border-radius:1.5mm; }}
.seal-box > div {{ width:100%; text-align:center; margin:0; padding:0; }}
@media print {{ .page {{ break-after:page; }} .page:last-child {{ break-after:auto; }} }}
</style></head><body>{''.join(pages)}</body></html>"""

    def find_browser():
        candidates = [
            _os.environ.get("CHROME_PATH", ""),
            _os.environ.get("GOOGLE_CHROME_BIN", ""),
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            str(_Path(_os.environ.get("LOCALAPPDATA", "")) / "Google/Chrome/Application/chrome.exe"),
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            str(_Path(_os.environ.get("PROGRAMFILES", "")) / "Microsoft/Edge/Application/msedge.exe"),
        ]
        for raw in candidates:
            if raw:
                p = _Path(raw)
                if p.exists() and p.is_file():
                    return str(p)
        for name in ("chrome.exe", "msedge.exe", "chrome", "chromium", "chromium-browser"):
            found = shutil.which(name)
            if found:
                return found
        return None

    # Streamlit Cloud/Linux generally does not have Chrome/Edge installed.
    # WeasyPrint is already included in requirements.txt and can render this
    # same HTML/CSS directly to PDF, including Devanagari text. Prefer it
    # when available; retain Chrome/Edge as the Windows/local fallback.
    browser = find_browser()
    if not browser:
        try:
            from weasyprint import HTML as _WeasyHTML
            return _WeasyHTML(string=html, base_url=str(_Path.cwd())).write_pdf()
        except Exception as weasy_exc:
            raise RuntimeError(
                "Streamlit पर PDF बनाने के लिए WeasyPrint उपलब्ध/कार्यशील नहीं है। "
                f"WeasyPrint error: {weasy_exc}"
            ) from weasy_exc

    temp_dir = _Path(_tempfile.mkdtemp(prefix="sanchalan_pdf_"))
    html_path = temp_dir / "sanchalan_order.html"
    pdf_path = temp_dir / "sanchalan_order.pdf"
    try:
        html_path.write_text(html, encoding="utf-8", newline="\n")
        cmd = [
            browser, "--headless=new", "--disable-gpu", "--disable-gpu-compositing", "--use-gl=swiftshader",
            "--disable-dev-shm-usage", "--no-sandbox",
            "--allow-file-access-from-files",
            "--run-all-compositor-stages-before-draw",
            "--virtual-time-budget=1500", "--no-pdf-header-footer",
            f"--print-to-pdf={pdf_path}", html_path.as_uri(),
        ]
        proc = _subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if proc.returncode != 0 or not pdf_path.exists() or pdf_path.stat().st_size < 1000:
            detail = (proc.stderr or proc.stdout or "Chrome PDF generation failed").strip()
            raise RuntimeError(f"Chrome PDF generation failed: {detail[-1500:]}")
        raw_pdf = pdf_path.read_bytes()

        # Stamp actual page numbers after Chrome rendering.
        try:
            from pypdf import PdfReader, PdfWriter
            from reportlab.pdfgen import canvas
            from reportlab.lib.colors import black
            from io import BytesIO
            reader = PdfReader(BytesIO(raw_pdf))
            total_pages = len(reader.pages)
            writer = PdfWriter()
            for page_no, page in enumerate(reader.pages, start=1):
                width = float(page.mediabox.width)
                height = float(page.mediabox.height)
                buf = BytesIO()
                cv = canvas.Canvas(buf, pagesize=(width, height))
                cv.setFillColor(black)
                cv.setFont("Helvetica-Bold", 7.5)
                cv.drawRightString(width - 10.5 * 2.83465, 3.8 * 2.83465, f"Page {page_no} of {total_pages}")
                cv.save()
                buf.seek(0)
                overlay = PdfReader(buf).pages[0]
                page.merge_page(overlay)
                writer.add_page(page)
            out_buf = BytesIO()
            writer.write(out_buf)
            return out_buf.getvalue()
        except Exception as stamp_exc:
            print(f"PDF page-number stamping skipped: {stamp_exc}")
            return raw_pdf
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def _build_sanction_excel_bytes(office, district, order_no, order_date, items):
    """Create the Excel copy from the exact same grouped dataset used by PDF."""
    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
    from openpyxl.utils import get_column_letter
    from openpyxl.worksheet.page import PageMargins
    from openpyxl.worksheet.pagebreak import Break

    out = io.BytesIO()
    wb = Workbook()
    ws = wb.active
    ws.title = "Sanction Order"

    black = "000000"
    header_fill = PatternFill("solid", fgColor="0B4F8A")
    group_fill = PatternFill("solid", fgColor="DFF1FF")
    sec_group_fill = PatternFill("solid", fgColor="DFF1FF")
    ele_group_fill = PatternFill("solid", fgColor="E8F7E9")
    total_fill = PatternFill("solid", fgColor="FFF0D9")
    grand_fill = PatternFill("solid", fgColor="FFE4F1")
    office_fill = PatternFill("solid", fgColor="0B4F8A")
    district_fill = PatternFill("solid", fgColor="FFF0F5")
    title_fill = PatternFill("solid", fgColor="FFE8A3")
    thin = Side(style="thin", color=black)
    medium = Side(style="medium", color=black)
    thin_border = Border(left=thin, right=thin, top=thin, bottom=thin)

    title = Font(name="Nirmala UI", size=14, bold=True, color="FFFFFF")
    subtitle = Font(name="Nirmala UI", size=12, bold=True, color="8B1E3F")
    order_title = Font(name="Nirmala UI", size=13, bold=True, color="6B3F00")
    bold = Font(name="Nirmala UI", size=9, bold=True)
    normal = Font(name="Nirmala UI", size=9)
    small = Font(name="Nirmala UI", size=8)
    date_text = order_date.strftime("%d/%m/%Y") if hasattr(order_date, "strftime") else str(order_date)

    groups = _prepare_sanction_groups(items)
    grouped_items = [row for g in groups for row in g["items"]]
    chunks = _paginate_sanction_groups(groups)
    grand = sum(float(x.get("amount", 0) or 0) for x in grouped_items)

    headers = [
        "क.स.", "मुख्य ब्लॉक शिक्षा अधिकारी आदेश क्रमांक", "संस्था का नाम", "फर्म का नाम /\nप्राप्तकर्ता",
        "खाता संख्या व IFSC कोड /\nविशिष्ट टिप्पणी",
        "बिल/वाउचर सं.\nएवं दिनांक", "राशि (₹)", "पुनर्भरण",
        "कंपोनेंट व स्तर\n(SEC/ELE)",
    ]
    widths = [6, 18, 22, 16, 38, 12, 10, 17, 16]
    for i, width in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = width

    # First-page-only office heading.
    ws.merge_cells("A1:I1")
    ws["A1"] = f"कार्यालय {office}"
    ws["A1"].font = title
    ws["A1"].fill = office_fill
    ws["A1"].alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 23

    ws.merge_cells("A2:I2")
    ws["A2"] = f"जिला : {district}"
    ws["A2"].font = subtitle
    ws["A2"].fill = district_fill
    ws["A2"].alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[2].height = 20

    ws.merge_cells("A3:I3")
    ws["A3"] = "भुगतान स्वीकृति आदेश"
    ws["A3"].font = order_title
    ws["A3"].fill = title_fill
    ws["A3"].alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[3].height = 24

    ws.merge_cells("A4:E4")
    ws["A4"] = f"क्रमांक: {order_no}"
    ws["A4"].font = normal
    ws["A4"].alignment = Alignment(horizontal="left", vertical="center")
    ws.merge_cells("F4:I4")
    # F4 is the top-left cell of the merged F4:I4 range.
    # Writing to E4 here raises: AttributeError: 'MergedCell' object attribute 'value' is read-only
    # because E4 belongs to the preceding merged A4:E4 range.
    ws["F4"] = f"दिनांक: {date_text}"
    ws["F4"].font = normal
    ws["F4"].alignment = Alignment(horizontal="right", vertical="center")

    intro = (
        "राजस्थान स्कूल शिक्षा परिषद जयपुर द्वारा प्रदत्त निर्देशानुसार संचालन पोर्टल से भुगतान "
        "किये जाने की प्रक्रिया के अन्तर्गत स्थानीय विद्यालय / अधोहस्ताक्षकर्ता के नियंत्रणाधीन "
        "संबंधित संस्थाओं हेतु जारी मद में जारी संचालन पोर्टल लिमिट से सम्बन्धित वेंडर / "
        "बेनिफिशियरी को निम्नानुसार भुगतान किये जाने की स्वीकृति प्रदान की जाती है:-"
    )
    ws.merge_cells("A5:I5")
    ws["A5"] = intro
    ws["A5"].font = small
    ws["A5"].alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
    ws.row_dimensions[5].height = 38
    ws.row_dimensions[6].height = 15
    ws.merge_cells("A6:I6")
    ws["A6"] = f"भुगतान स्वीकृति आदेश — क्रमांक: {order_no}"
    ws["A6"].font = Font(name="Nirmala UI", size=8, bold=True)
    ws["A6"].alignment = Alignment(horizontal="center", vertical="center")

    header_row = 7
    for c, h in enumerate(headers, 1):
        cell = ws.cell(header_row, c, h)
        cell.font = Font(name="Nirmala UI", size=9, bold=True, color="FFFFFF")
        cell.fill = header_fill
        cell.border = thin_border
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    ws.row_dimensions[header_row].height = 32

    def payment_note(v):
        reimb = str(v.get("reimb_status", ""))
        role = str(v.get("payment_type", ""))
        recipient = str(v.get("payment_recipient", ""))
        if role == "Staff Reimbursement" or "Paid by Staff:" in reimb or "भुगतान: " in reimb:
            staff = recipient or (reimb.split(":", 1)[1].rstrip(")").strip() if ":" in reimb else "संबंधित स्टाफ कर्मचारी")
            return f"बिल का भुगतान स्टाफ कर्मचारी {staff} द्वारा फर्म को किया जा चुका है; अतः पुनर्भरण सीधे संबंधित स्टाफ कर्मचारी को किया जा रहा है।"
        if role == "Beneficiary" or "Not Applicable" in reimb:
            return f"भुगतान लाभार्थी {recipient or v.get('firm','')} को सीधे किया जा रहा है।"
        if role == "Vendor":
            return f"भुगतान संबंधित वेंडर/फर्म {recipient or v.get('firm','')} को सीधे किया जा रहा है।"
        return ""

    def bank_display(v):
        base = str(v.get("bank_ifsc", ""))
        note = payment_note(v)
        return f"{base}\n{note}" if note else base

    group_map = {(g["level"], _norm(g["name"])): g for g in groups}
    flat_index = {id(row): i for i, row in enumerate(grouped_items)}
    current_row = 8
    page_end_rows = []
    first_page_end = None

    for page_no, chunk in enumerate(chunks):
        page_start = current_row if page_no > 0 else 1
        if page_no > 0:
            # The repeated row 7 is the table header on printed continuation pages.
            pass

        prev_key = None
        for local_i, v in enumerate(chunk):
            key = v.get("_group_key")
            global_i = flat_index[id(v)]
            if local_i == 0 or prev_key != key:
                already_started = global_i > 0 and grouped_items[global_i - 1].get("_group_key") == key
                r = current_row
                ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=9)
                g = group_map[key]
                ws.cell(r, 1, f"{'Secondary (SEC)' if key[0]=='SEC' else 'Elementary (ELE)'} — {g['name']}" + (" — जारी" if already_started else ""))
                ws.cell(r, 1).font = Font(name="Nirmala UI", size=9, bold=True, color=("0B4F8A" if key[0] == "SEC" else "176B2C"))
                ws.cell(r, 1).fill = sec_group_fill if key[0] == "SEC" else (ele_group_fill if key[0] == "ELE" else group_fill)
                ws.cell(r, 1).alignment = Alignment(horizontal="left", vertical="center")
                for c in range(1, 10):
                    ws.cell(r, c).border = thin_border
                ws.row_dimensions[r].height = 20
                current_row += 1

            vals = [
                v.get("_display_sno", ""),
                v.get("cbeo_order_no", ""),
                v.get("inst", ""),
                v.get("firm", ""),
                bank_display(v),
                v.get("bill", ""),
                float(v.get("amount", 0) or 0),
                v.get("reimb_status", ""),
                "SEC" if str(v.get("comp_rem","")).startswith("[SEC]") else ("ELE" if str(v.get("comp_rem","")).startswith("[ELE]") else ""),
            ]
            r = current_row
            for c, val in enumerate(vals, 1):
                cell = ws.cell(r, c, val)
                cell.font = Font(name="Nirmala UI", size=9, color=("174A7C" if c == 3 else "000000"))
                cell.border = thin_border
                cell.alignment = Alignment(
                    horizontal="right" if c == 7 else ("center" if c in (1,2,4,6,8,9) else "left"),
                    vertical="center", wrap_text=True,
                )
            ws.cell(r, 7).number_format = '#,##0.00'
            ws.row_dimensions[r].height = max(38, _estimate_payment_row_height_mm(v) * 2.6)
            current_row += 1

            next_global = global_i + 1
            next_key = grouped_items[next_global].get("_group_key") if next_global < len(grouped_items) else None
            if next_key != key:
                r = current_row
                g = group_map[key]
                ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=9)
                ws.cell(r, 1, f"कंपोनेंट कुल — {key[0]} {g['name']}    ₹ {g['total']:,.2f}")
                ws.cell(r, 1).font = Font(name="Nirmala UI", size=9, bold=True, color="7A3E00")
                ws.cell(r, 1).alignment = Alignment(horizontal="right", vertical="center", wrap_text=True)
                for c in range(1, 10):
                    ws.cell(r, c).fill = total_fill
                    ws.cell(r, c).border = thin_border
                ws.row_dimensions[r].height = 20
                current_row += 1
            prev_key = key

        page_end_rows.append(current_row - 1)
        if page_no == 0:
            first_page_end = current_row - 1

    # Final page information: first seal immediately after the final component
    # total, then Grand Total, copies, and the second seal.
    first_inst = grouped_items[0].get("inst", "") if grouped_items else office
    seal_name = make_short_name(first_inst)

    # Bottom component summary (same order/values as PDF).
    current_row += 1
    ws.merge_cells(start_row=current_row, start_column=1, end_row=current_row, end_column=9)
    ws.cell(current_row, 1, "कंपोनेंट-वार संक्षिप्त योग")
    ws.cell(current_row, 1).font = Font(name="Nirmala UI", size=9, bold=True, color="176B2C")
    ws.cell(current_row, 1).fill = PatternFill("solid", fgColor="D9F2DD")
    ws.cell(current_row, 1).alignment = Alignment(horizontal="center", vertical="center")
    current_row += 1
    for g in groups:
        ws.merge_cells(start_row=current_row, start_column=1, end_row=current_row, end_column=7)
        ws.merge_cells(start_row=current_row, start_column=8, end_row=current_row, end_column=9)
        level_text = "SEC" if g["level"] == "SEC" else ("ELE" if g["level"] == "ELE" else g["level"])
        ws.cell(current_row, 1, f"{level_text} — {g['name']}")
        ws.cell(current_row, 8, g["total"])
        ws.cell(current_row, 8).number_format = '#,##0.00'
        for c in range(1,10):
            ws.cell(current_row,c).border = thin_border
        ws.cell(current_row,1).alignment = Alignment(horizontal="left", vertical="center")
        ws.cell(current_row,8).alignment = Alignment(horizontal="right", vertical="center")
        current_row += 1

    r = current_row + 1
    ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=6)
    ws.merge_cells(start_row=r, start_column=7, end_row=r, end_column=9)
    ws.cell(r, 1, "कुल योग (Grand Total):")
    ws.cell(r, 7, grand)
    ws.cell(r, 7).number_format = '#,##0.00'
    for c in range(1, 10):
        ws.cell(r, c).font = Font(name="Nirmala UI", size=9, bold=True, color="8A0D46")
        ws.cell(r, c).fill = grand_fill
        ws.cell(r, c).border = thin_border
    current_row = r + 2

    # First seal: immediately after the bottom component summary and Grand Total.
    for line in ("हस्ताक्षर मय सील", "प्रधानाचार्य / पीईईओ", seal_name):
        ws.merge_cells(start_row=current_row, start_column=7, end_row=current_row, end_column=9)
        ws.cell(current_row, 7, line)
        ws.cell(current_row, 7).font = bold if line == "हस्ताक्षर मय सील" else normal
        ws.cell(current_row, 7).alignment = Alignment(horizontal="center", vertical="center")
        current_row += 1

    current_row += 1
    ws.merge_cells(start_row=current_row, start_column=1, end_row=current_row, end_column=9)
    ws.cell(current_row, 1, f"क्रमांक: {order_no}    दिनांक: {date_text}")
    ws.cell(current_row, 1).font = normal
    current_row += 1
    ws.merge_cells(start_row=current_row, start_column=1, end_row=current_row, end_column=9)
    ws.cell(current_row, 1, "प्रतिलिपि :- सूचनार्थ एवं आवश्यक कार्यवाही हेतु प्रेषित :-")
    ws.cell(current_row, 1).font = bold
    current_row += 1

    copy_lines = _build_copy_lines(grouped_items, office)
    for line in copy_lines:
        plain = re.sub(r"<[^>]+>", "", line).replace("&nbsp;", " ")
        ws.merge_cells(start_row=current_row, start_column=1, end_row=current_row, end_column=9)
        ws.cell(current_row, 1, plain)
        ws.cell(current_row, 1).alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)
        current_row += 1

    current_row += 1
    # Second seal: immediately after the fourth (final) copy line.
    for line in ("हस्ताक्षर मय सील", "प्रधानाचार्य / पीईईओ", seal_name):
        ws.merge_cells(start_row=current_row, start_column=7, end_row=current_row, end_column=9)
        ws.cell(current_row, 7, line)
        ws.cell(current_row, 7).font = bold if line == "हस्ताक्षर मय सील" else normal
        ws.cell(current_row, 7).alignment = Alignment(horizontal="center", vertical="center")
        current_row += 1

    final_row = current_row - 1
    if page_end_rows:
        page_end_rows[-1] = final_row
    ws.oddFooter.left.text = "&Iसॉफ्टवेयर डेवलपर: आलोक कुमार सिंह, वरिष्ठ अध्यापक, राजकीय उच्च माध्यमिक विद्यालय, रोजड़ी"
    ws.oddFooter.right.text = "Page &P of &N"
    ws.oddFooter.left.size = 7
    ws.oddFooter.right.size = 8
    ws.freeze_panes = "A8"
    ws.sheet_view.showGridLines = False
    ws.page_setup.orientation = "landscape"
    ws.page_setup.paperSize = ws.PAPERSIZE_A4
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.page_margins = PageMargins(left=0.18, right=0.18, top=0.2, bottom=0.35, header=0.08, footer=0.15)
    ws.print_title_rows = "6:7"
    ws.print_area = f"A1:I{final_row}"

    # Manual page breaks match the same chunks used by the PDF.
    # The final information block always begins on the last chunk's page.
    for end_row in page_end_rows[:-1]:
        try:
            ws.row_breaks.append(Break(id=end_row))
        except Exception:
            pass

    # Page-sized outer boxes: first page includes the office header; continuation
    # pages start at the repeated table header row 7.
    page_starts = [1] + [7] * (len(page_end_rows) - 1)
    for start, end in zip(page_starts, page_end_rows):
        for c in range(1, 10):
            top = medium if start == 1 or start == 7 else thin
            bottom = medium if end in page_end_rows else thin
            left = medium if c == 1 else thin
            right = medium if c == 9 else thin
            ws.cell(start, c).border = Border(
                left=left,
                right=right,
                top=medium if start in (1, 7) else ws.cell(start, c).border.top,
                bottom=ws.cell(start, c).border.bottom,
            )
            ws.cell(end, c).border = Border(
                left=ws.cell(end, c).border.left,
                right=ws.cell(end, c).border.right,
                top=ws.cell(end, c).border.top,
                bottom=medium,
            )

    wb.save(out)
    out.seek(0)
    return out.getvalue()


def _legacy_to_records(vendor_dict, beneficiary_dict):
    vendors=[]
    for name, info in (vendor_dict or {}).items():
        info=info or {}
        vendors.append({"name": str(name).strip(), "bank_name": str(info.get("bank_name", "")).strip(), "account": str(info.get("account", "")).strip(), "ifsc": str(info.get("ifsc", "")).strip()})
    beneficiaries=[]
    for name, info in (beneficiary_dict or {}).items():
        info=info or {}
        beneficiaries.append({"name": str(name).strip(), "account": str(info.get("account", "")).strip(), "ifsc": str(info.get("ifsc", "")).strip(), "bank": str(info.get("bank", "")).strip()})
    return vendors, beneficiaries

def _vendor_key(row):
    return (_norm(row.get("name")), _norm(row.get("account")))

def _beneficiary_key(row):
    return (_norm(row.get("name")), _norm(row.get("account")))

def _school_key(name):
    return _norm(name)

def _make_template_bytes():
    out=io.BytesIO()
    with pd.ExcelWriter(out, engine="openpyxl") as writer:
        pd.DataFrame(columns=["school_name"]).to_excel(writer, index=False, sheet_name="Schools")
        pd.DataFrame(columns=["vendor_name", "bank_name", "account", "ifsc"]).to_excel(writer, index=False, sheet_name="Vendors")
        pd.DataFrame(columns=["beneficiary_name", "account", "ifsc", "bank"]).to_excel(writer, index=False, sheet_name="Beneficiaries")
    out.seek(0)
    return out.getvalue()

def _parse_master_excel(uploaded):
    sheets=pd.read_excel(uploaded, sheet_name=None, dtype=str)
    def pick(name, aliases):
        for key in aliases:
            if key in sheets: return sheets[key].fillna("")
        return pd.DataFrame()
    schools_df=pick("Schools", ["Schools", "School", "विद्यालय"])
    vendors_df=pick("Vendors", ["Vendors", "Vendor", "वेंडर"])
    bens_df=pick("Beneficiaries", ["Beneficiaries", "Beneficiary", "बेनिफिशियरीज"])
    schools=[]
    if not schools_df.empty:
        col=next((c for c in schools_df.columns if _norm(c) in {_norm("school_name"),_norm("school"),_norm("विद्यालय का नाम")}), schools_df.columns[0])
        schools=[_clean(x) for x in schools_df[col].tolist() if _clean(x)]
    vendors=[]
    if not vendors_df.empty:
        cols={_norm(c):c for c in vendors_df.columns}
        ncol=next((cols[x] for x in [_norm("vendor_name"),_norm("vendor"),_norm("वेंडर का नाम")] if x in cols), None)
        acol=next((cols[x] for x in [_norm("account"),_norm("account_number"),_norm("खाता संख्या")] if x in cols), None)
        bcol=next((cols[x] for x in [_norm("bank_name"),_norm("bank"),_norm("बैंक")] if x in cols), None)
        icol=next((cols[x] for x in [_norm("ifsc"),_norm("ifsc_code"),_norm("आईएफएससी")] if x in cols), None)
        if ncol:
            for _,r in vendors_df.iterrows():
                row={"name":_clean(r.get(ncol)),"bank_name":_clean(r.get(bcol)) if bcol else "","account":_clean(r.get(acol)) if acol else "","ifsc":_clean(r.get(icol)) if icol else ""}
                if row["name"]: vendors.append(row)
    beneficiaries=[]
    if not bens_df.empty:
        cols={_norm(c):c for c in bens_df.columns}
        ncol=next((cols[x] for x in [_norm("beneficiary_name"),_norm("name"),_norm("कर्मचारी का नाम"),_norm("बेनिफिशियरी का नाम")] if x in cols), None)
        acol=next((cols[x] for x in [_norm("account"),_norm("account_number"),_norm("खाता संख्या")] if x in cols), None)
        bcol=next((cols[x] for x in [_norm("bank"),_norm("bank_name"),_norm("बैंक")] if x in cols), None)
        icol=next((cols[x] for x in [_norm("ifsc"),_norm("ifsc_code"),_norm("आईएफएससी")] if x in cols), None)
        if ncol:
            for _,r in bens_df.iterrows():
                row={"name":_clean(r.get(ncol)),"account":_clean(r.get(acol)) if acol else "","ifsc":_clean(r.get(icol)) if icol else "","bank":_clean(r.get(bcol)) if bcol else ""}
                if row["name"]: beneficiaries.append(row)
    if not schools and not vendors and not beneficiaries:
        raise ValueError("Excel में Schools, Vendors या Beneficiaries की मान्य शीट/डेटा नहीं मिला।")
    return schools,vendors,beneficiaries

def make_short_name(full_name):
    """Create the seal caption from the first institution's official name."""
    if not full_name:
        return ""
    replaced = str(full_name).strip()
    replaced = re.sub(r"राजकीय\s+उच्च\s+माध्यमिक\s+विद्यालय", "रा.उ.मा.वि.", replaced)
    replaced = re.sub(r"राजकीय\s+उच्च\s+प्राथमिक\s+विद्यालय", "रा.उ.प्रा.वि.", replaced)
    replaced = re.sub(r"राजकीय\s+प्राथमिक\s+विद्यालय", "रा.प्रा.वि.", replaced)
    replaced = re.sub(r"पंचायत\s+समिति", "प.स.", replaced)
    replaced = re.sub(r"\s{2,}", " ", replaced)
    return replaced

def render(context):
    # Receive the existing app namespace; no second import of app.py is performed.
    globals().update({name: context[name] for name in [
        "SAN_DATA_FILE", "_show_module_cloud_status", "datetime",
        "load_json_data", "save_json_data", "st"
    ] if name in context})
    _show_module_cloud_status("sanchalan_portal")
    if st.button("⬅ मुख्य डैशबोर्ड पर वापस जाएँ", key="back_dashboard_sanchalan", use_container_width=False):
        st.query_params["page"] = "dashboard"
        st.rerun()

    if "san_bundle_loaded" not in st.session_state:
        san_bundle = load_json_data(SAN_DATA_FILE, {"office_data": {}, "items": []})
        st.session_state.san_office = san_bundle.get("office_data", {})
        st.session_state.san_items = san_bundle.get("items", [])
        st.session_state.san_bundle_loaded = True
    saved_san_off = st.session_state.get("san_office", {}) or {}
    # ------------------------------------------------------------------
    # MASTER DATA ONLY ARCHITECTURE
    # ------------------------------------------------------------------
    # Sanchalan does NOT maintain a second copy of School/Vendor/Beneficiary
    # data. Master Data Management is the single source of truth.
    username = str(st.session_state.get("logged_username") or "").strip().lower()
    if not username:
        st.error("❌ वर्तमान logged-in user उपलब्ध नहीं है। Master Data लोड नहीं किया जा सकता।")
        return

    try:
        from master_data_service import get_service
        md_service = get_service(username)
    except Exception as exc:
        st.error(f"❌ Master Data Service उपलब्ध नहीं है: {type(exc).__name__}: {exc}")
        return

    def _row_map(row):
        return {_norm(k): v for k, v in (row or {}).items() if not str(k).startswith("_")}

    def _first(row, *names):
        mapped = _row_map(row)
        for name in names:
            key = _norm(name)
            if key in mapped:
                return _clean(mapped[key])
        return ""

    def _load_rows(master_name):
        try:
            master = md_service.get_master_by_name(master_name)
            if not master or master.get("status", "active") != "active":
                return []
            return md_service.get_rows(master["master_id"], active_only=True) or []
        except Exception as exc:
            raise RuntimeError(f"{master_name} पढ़ने में समस्या: {exc}") from exc

    try:
        school_rows = _load_rows("School Master Data")
        vendor_rows = _load_rows("Vendor Master Data")
        beneficiary_rows = _load_rows("Beneficiary Master Data")
        staff_rows = _load_rows("Employee Master Data")
    except RuntimeError as exc:
        st.error(f"❌ {exc}")
        return

    def _records(rows, kind):
        out, seen = [], set()
        for row in rows:
            if kind == "vendor":
                name = _first(row, "Vendor Name", "VENDOR NAME", "Vendor", "वेंडर का नाम")
            elif kind == "beneficiary":
                name = _first(row, "Beneficiary Name", "BENEFICIARY NAME", "Name", "बेनिफिशियरी का नाम")
            else:
                name = _first(row, "Employee Name", "EMPLOYEE NAME", "Name", "कर्मचारी का नाम", "Staff Name")
            rec = {
                "name": name,
                "bank": _first(row, "Bank Name", "BANK NAME", "Bank", "बैंक"),
                "branch": _first(row, "Branch", "Branch Name", "BRANCH", "बैंक शाखा"),
                "account": _first(row, "Account Number", "ACCOUNT NUMBER", "Account", "खाता संख्या"),
                "ifsc": _first(row, "IFSC", "IFSC Code", "IFSC CODE", "आईएफएससी"),
                "employee_id": _first(row, "Employee ID", "EMPLOYEE ID", "EMPLOYEE CODE", "कार्मिक आईडी"),
            }
            key = (_norm(rec["name"]), _norm(rec["account"]))
            if rec["name"] and key not in seen:
                seen.add(key); out.append(rec)
        return out

    school_list = []
    seen_school = set()
    for row in school_rows:
        name = _first(row, "School Name", "SCHOOL NAME", "School", "विद्यालय का नाम")
        if name and _norm(name) not in seen_school:
            seen_school.add(_norm(name)); school_list.append(name)

    vendor_records = _records(vendor_rows, "vendor")
    beneficiary_records = _records(beneficiary_rows, "beneficiary")
    staff_records = _records(staff_rows, "staff")

    if not school_list:
        st.warning("⚠️ School Master Data में अभी कोई विद्यालय उपलब्ध नहीं है। पहले Master Data Management में विद्यालय जोड़ें।")
        return
    if not vendor_records and not beneficiary_records:
        st.warning("⚠️ Vendor/Beneficiary Master Data में कोई record उपलब्ध नहीं है। पहले Master Data Management में records जोड़ें।")

    component_master = _load_component_master_by_level(username)

    # Repair only the level tag of previously saved Sanchalan rows when the
    # component name unambiguously belongs to the opposite Master bucket.
    # This preserves the old payment rows while correcting the exact defect
    # that produced e.g. [SEC] Composite School Grant (Elementary).
    # Build a name -> set(levels) map. A component name may legitimately
    # exist in both Elementary and Secondary (for example, Youth and Eco Club).
    # In that case the name alone is ambiguous and MUST NOT be used to rewrite
    # the saved [SEC]/[ELE] tag. Only unambiguous names may be auto-repaired.
    component_levels_by_name = {}
    for _level, _names in component_master.items():
        for _name in _names:
            component_levels_by_name.setdefault(_norm(_name), set()).add(_level)
    _items_changed = False
    for _item in st.session_state.get("san_items", []):
        _comp = str(_item.get("comp_rem", ""))
        if _comp.startswith("[SEC]") or _comp.startswith("[ELE]"):
            _old_level = "SEC" if _comp.startswith("[SEC]") else "ELE"
            _comp_name = _comp[5:].strip()
            _levels = component_levels_by_name.get(_norm(_comp_name), set())
            # Repair only when the component name belongs to exactly one level.
            # If the same name exists in both SEC and ELE, preserve the user's
            # explicit selection instead of silently forcing one level.
            if len(_levels) == 1:
                _actual_level = next(iter(_levels))
                if _actual_level != _old_level:
                    _item["comp_rem"] = f"[{_actual_level}] {_comp_name}"
                    _items_changed = True
    if _items_changed:
        save_json_data(SAN_DATA_FILE, {
            "office_data": st.session_state.get("san_office", {}) or {},
            "items": st.session_state.get("san_items", [])
        })

    st.markdown("""
    <div class="main-header" style="padding: 12px; margin-bottom: 15px;">
        <h2 style="color: #f4d03f; margin:0; font-size: 22px;">संचालन पोर्टल भुगतान स्वीकृति आदेश (SNA Sanction Order) मॉड्यूल</h2>
        <p style="color: #aed6f1; margin:3px 0 0 0; font-size: 12px;">
            School / Vendor / Beneficiary / Component विवरण केवल Master Data Management से प्राप्त होंगे।
        </p>
    </div>
    """, unsafe_allow_html=True)
    st.markdown(
        f"<div style='padding:8px 12px;border:1px solid #2ecc71;border-radius:7px;"
        f"background:#132743;color:#2ecc71;font-weight:700;'>"
        f"✔ Master Data सक्रिय &nbsp;|&nbsp; School: {len(school_list)} "
        f"&nbsp;|&nbsp; Vendor: {len(vendor_records)} "
        f"&nbsp;|&nbsp; Beneficiary: {len(beneficiary_records)} "
        f"&nbsp;|&nbsp; SEC Component: {len(component_master.get('SEC', []))}"
        f" &nbsp;|&nbsp; ELE Component: {len(component_master.get('ELE', []))} &nbsp;|&nbsp; Staff: {len(staff_records)}</div>",
        unsafe_allow_html=True,
    )
    st.markdown("<h5 style='color:#f39c12; margin-bottom: 4px;'>१. प्रधान कार्यालय एवं आदेश विवरण</h5>", unsafe_allow_html=True)
    sc1, sc2, sc3 = st.columns(3)
    with sc1:
        san_office = st.text_input("प्रधान कार्यालय का नाम:", saved_san_off.get("office_name", "राजकीय उच्च माध्यमिक विद्यालय, रोजड़ी, पंचायत समिति सांभर लेक"), key="w_san_off")
        san_order_no = st.text_input("आदेश क्रमांक:", saved_san_off.get("order_no", "राउमावि/रोजड़ी/एसएनए सेंक्सन/2026-27/2345"), key="w_san_ord_no")
    with sc2:
        san_district = st.text_input("जिला:", saved_san_off.get("district", "जयपुर"), key="w_san_dist")
        san_order_date = st.date_input("आदेश दिनांक:", datetime.now(), key="w_san_odt")
    with sc3:
        st.write("")
        st.markdown("<div style='padding-top: 10px; color:#2ecc71; font-weight:bold;'>✔ मास्टर डेटा सक्रिय</div>", unsafe_allow_html=True)

    st.session_state.setdefault("san_edit_idx", None)

    st.markdown("<hr style='border-color: #1b4f72; margin: 12px 0;'>", unsafe_allow_html=True)
    st.markdown("<h5 style='color:#5dade2; margin-bottom: 4px;'>२. भुगतान विवरण प्रविष्टि (मास्टर ऑटो-फिल समर्थित)</h5>", unsafe_allow_html=True)

    # ------------------------------------------------------------------
    # PAYMENT ROUTING — STRICT MASTER DATA
    # Beneficiary route: beneficiary only.
    # Vendor + Reimbursement No: vendor.
    # Vendor + Reimbursement Yes: staff reimbursement.
    # No Vendor/Beneficiary/Staff editing is permitted here.
    # ------------------------------------------------------------------
    vendor_indices = list(range(len(vendor_records)))
    ben_indices = list(range(len(beneficiary_records)))
    staff_indices = list(range(len(staff_records)))
    vendor_map = {i: vendor_records[i] for i in vendor_indices}
    ben_map = {i: beneficiary_records[i] for i in ben_indices}
    staff_map = {i: staff_records[i] for i in staff_indices}

    r_col1, r_col2, r_col3 = st.columns(3)
    payment_type = "Beneficiary"
    san_firm = ""; san_ben = ""; san_staff = ""
    payment_recipient = None; payment_role = ""

    with r_col1:
        san_inst = st.selectbox("संस्था का नाम:", school_list, key="w_san_inst")
        payment_type = st.radio(
            "भुगतान किसे किया जाना है?",
            ["Beneficiary (लाभार्थी)", "Vendor / Firm (वेंडर / फर्म)"],
            horizontal=True, key="w_san_payment_type"
        )

    with r_col2:
        if payment_type.startswith("Beneficiary"):
            if beneficiary_records:
                san_ben_idx = st.selectbox(
                    "Beneficiary (लाभार्थी):", ben_indices,
                    format_func=lambda i: beneficiary_records[i]["name"], key="w_san_ben_sel"
                )
                san_ben = beneficiary_records[san_ben_idx]["name"]
                payment_recipient = beneficiary_records[san_ben_idx]
                payment_role = "Beneficiary"
            else:
                st.error("❌ Beneficiary Master Data में कोई record उपलब्ध नहीं है।")
        else:
            if vendor_records:
                san_firm_idx = st.selectbox(
                    "Vendor / Firm (वेंडर / फर्म):", vendor_indices,
                    format_func=lambda i: vendor_records[i]["name"], key="w_san_firm_idx"
                )
                san_firm = vendor_records[san_firm_idx]["name"]
                san_reimb = st.radio(
                    "पुनर्भरण (Reimbursement):", ["No (नहीं)", "Yes (हाँ)"],
                    horizontal=True, key="w_san_reimb_radio"
                )
                if san_reimb.startswith("Yes"):
                    if staff_records:
                        san_staff_idx = st.selectbox(
                            "स्टाफ कर्मचारी (पुनर्भरण प्राप्तकर्ता):", staff_indices,
                            format_func=lambda i: staff_records[i]["name"], key="w_san_staff_sel"
                        )
                        san_staff = staff_records[san_staff_idx]["name"]
                        payment_recipient = staff_records[san_staff_idx]
                        payment_role = "Staff Reimbursement"
                    else:
                        st.error("❌ Employee Master Data में कोई Staff record उपलब्ध नहीं है।")
                else:
                    payment_recipient = vendor_records[san_firm_idx]
                    payment_role = "Vendor"
            else:
                st.error("❌ Vendor Master Data में कोई record उपलब्ध नहीं है।")

    with r_col3:
        if payment_recipient:
            bank_name = payment_recipient.get("bank", "")
            branch_name = payment_recipient.get("branch", "")
            account_no = payment_recipient.get("account", "")
            ifsc_code = payment_recipient.get("ifsc", "")
            st.markdown(
                f"<div style='padding:10px;border:1px solid #2e86c1;border-radius:8px;background:#163a5b;'>"
                f"<b style='color:#f4d03f;'>भुगतान प्राप्तकर्ता: {escape(payment_recipient.get('name',''))}</b><br>"
                f"बैंक: <b>{escape(bank_name)}</b><br>"
                f"शाखा: <b>{escape(branch_name)}</b><br>"
                f"खाता: <b>{escape(account_no)}</b><br>"
                f"IFSC: <b>{escape(ifsc_code)}</b></div>", unsafe_allow_html=True
            )
            san_bank = f"बैंक: {bank_name} | शाखा: {branch_name} | खाता: {account_no} | IFSC: {ifsc_code}"
        else:
            san_bank = ""
            st.info("भुगतान प्राप्तकर्ता चुनने पर Master Data से बैंक विवरण स्वतः आएंगे।")
        san_bill = st.text_input("बिल/वाउचर सं. एवं दिनांक:", value="", key="w_san_bill")

    cbeo_order_no = st.text_input("मुख्य ब्लॉक शिक्षा अधिकारी आदेश क्रमांक:", value="", key="w_san_cbeo_order_no")

    r2_c1, r2_c2, r2_c3 = st.columns(3)
    with r2_c1:
        san_amt = st.number_input("राशि (₹):", min_value=1, max_value=5000000, value=1, step=1, key="w_san_amt")
    with r2_c2:
        san_level = st.selectbox("स्तर (SEC/ELE):", ["SEC", "ELE"], key="w_san_lvl")
    with r2_c3:
        component_master = _load_component_master_by_level(username)
        comp_opts = list(component_master.get(san_level, []))
        if not comp_opts:
            comp_opts = ["-- इस स्तर में कोई Component उपलब्ध नहीं --"]
        san_comp = st.selectbox("कंपोनेंट चयन:", comp_opts, key=f"w_san_comp_{san_level}")
        st.caption(f"Master Data से {san_level} के {len(component_master.get(san_level, []))} Component उपलब्ध हैं।")

    if san_comp.startswith("-- "):
        san_comp = ""

    if st.button("➕ पंक्ति तालिका में जोड़ें", key="btn_add_san_row"):
        if not san_bill.strip():
            st.error("कृपया बिल/वाउचर संख्या एवं दिनांक अवश्य भरें।")
        elif payment_type.startswith("Beneficiary") and not san_ben.strip():
            st.error("कृपया Beneficiary Master से लाभार्थी चुनें।")
        elif not payment_type.startswith("Beneficiary") and not san_firm.strip():
            st.error("कृपया Vendor / Firm चुनें।")
        elif not payment_type.startswith("Beneficiary") and san_reimb.startswith("Yes") and not san_staff.strip():
            st.error("कृपया Staff Master से पुनर्भरण प्राप्तकर्ता चुनें।")
        elif not san_comp:
            st.error("कृपया Master Data से उपलब्ध Component चुनें।")
        else:
            if payment_type.startswith("Beneficiary"):
                recipient_name = san_ben
                recipient_role = "Beneficiary"
                reimb_status_val = "Not Applicable"
                display_party = san_ben
            elif san_reimb.startswith("Yes"):
                recipient_name = san_staff
                recipient_role = "Staff Reimbursement"
                reimb_status_val = f"Yes (Paid by Staff: {san_staff})"
                display_party = san_firm
            else:
                recipient_name = san_firm
                recipient_role = "Vendor"
                reimb_status_val = "No"
                display_party = san_firm

            st.session_state.san_items.append({
                "inst": san_inst, "cbeo_order_no": cbeo_order_no.strip(), "firm": display_party, "bank_ifsc": san_bank,
                "bill": san_bill, "amount": float(san_amt),
                "reimb_status": reimb_status_val, "comp_rem": f"[{san_level}] {san_comp}",
                "payment_type": recipient_role, "payment_recipient": recipient_name,
                "vendor_name": san_firm, "beneficiary_name": san_ben, "staff_name": san_staff,
            })
            cur_off = {"office_name": san_office.strip(), "district": san_district.strip(), "order_no": san_order_no.strip()}
            save_json_data(SAN_DATA_FILE, {"office_data": cur_off, "items": st.session_state.san_items})
            st.success("भुगतान विवरण तालिका में सफलतापूर्वक जोड़ दिया गया है!")
            st.rerun()

    if st.session_state.san_items:
        st.markdown("<hr style='border-color: #1b4f72; margin: 12px 0;'>", unsafe_allow_html=True)
        st.markdown("<h5 style='color:#2ecc71; margin-bottom: 4px;'>३. दर्ज भुगतान विवरण तालिका</h5>", unsafe_allow_html=True)

        tbl_san_html = """<table class="custom-table">
        <thead><tr>
            <th>क्र.</th><th>मुख्य ब्लॉक शिक्षा अधिकारी आदेश क्रमांक</th><th>संस्था का नाम</th><th>फर्म का नाम</th><th>खाता संख्या व IFSC कोड</th>
            <th>बिल/वाउचर सं. एवं दिनांक</th><th>राशि (₹)</th><th>पुनर्भरण</th><th>कंपोनेंट व स्तर</th>
        </tr></thead><tbody>"""
        for idx, item in enumerate(st.session_state.san_items, 1):
            tbl_san_html += f"""<tr>
                <td>{idx}</td><td>{item.get('cbeo_order_no','')}</td><td>{item['inst']}</td><td style='font-weight:bold;'>{item['firm']}</td>
                <td style='text-align:left;'>{item['bank_ifsc']}</td><td>{item['bill']}</td>
                <td style='text-align:right; font-weight:bold; color:#2ecc71;'>{item['amount']:,}</td>
                <td>{item['reimb_status']}</td><td style='text-align:left;'>{item['comp_rem']}</td>
            </tr>"""
        tbl_san_html += "</tbody></table>"
        st.markdown(tbl_san_html, unsafe_allow_html=True)

        sb_col1, sb_col2 = st.columns(2)
        with sb_col1:
            del_san_idx = st.selectbox("हटाने हेतु पंक्ति चुनें:", range(1, len(st.session_state.san_items) + 1), format_func=lambda x: f"{x}. {st.session_state.san_items[x-1]['firm']} - ₹{st.session_state.san_items[x-1]['amount']:,}", key="del_san_sel")
            if st.button("🗑 चयनित पंक्ति हटाएं", key="btn_del_san"):
                del st.session_state.san_items[del_san_idx - 1]
                cur_off = {
                    "office_name": san_office.strip(), "district": san_district.strip(),
                    "order_no": san_order_no.strip()
                }
                save_json_data(SAN_DATA_FILE, {"office_data": cur_off, "items": st.session_state.san_items})
                st.rerun()
        with sb_col2:
            edit_san_idx = st.selectbox(
                "संपादित करने हेतु पंक्ति चुनें:",
                range(1, len(st.session_state.san_items) + 1),
                format_func=lambda x: f"{x}. {st.session_state.san_items[x-1].get('inst','')} - {st.session_state.san_items[x-1].get('firm','')} - ₹{st.session_state.san_items[x-1].get('amount',0):,}",
                key="edit_san_sel"
            )
            if st.button("✏️ चयनित प्रविष्टि संपादित करें", key="btn_edit_san"):
                st.session_state.san_edit_idx = edit_san_idx - 1
                st.rerun()
            st.write("")
            if st.button("🔄 सूची खाली करें (New Order)", key="btn_clr_san"):
                st.session_state.san_items = []
                cur_off = {
                    "office_name": san_office.strip(), "district": san_district.strip(),
                    "order_no": san_order_no.strip()
                }
                save_json_data(SAN_DATA_FILE, {"office_data": cur_off, "items": []})
                st.rerun()

        # Edit a saved Sanchalan entry in-place. The original row is replaced; no duplicate is created.
        if st.session_state.get("san_edit_idx") is not None:
            _ei = int(st.session_state.san_edit_idx)
            if 0 <= _ei < len(st.session_state.san_items):
                _old = st.session_state.san_items[_ei]
                st.markdown("### ✏️ प्रविष्टि संपादित करें")
                ec1, ec2 = st.columns(2)
                with ec1:
                    _e_inst = st.text_input("संस्था का नाम", value=str(_old.get("inst", "")), key="edit_inst")
                    _e_cbeo = st.text_input("मुख्य ब्लॉक शिक्षा अधिकारी आदेश क्रमांक", value=str(_old.get("cbeo_order_no", "")), key="edit_cbeo")
                    _e_firm = st.text_input("फर्म/प्राप्तकर्ता", value=str(_old.get("firm", "")), key="edit_firm")
                    _e_bank = st.text_area("खाता संख्या व IFSC कोड / टिप्पणी", value=str(_old.get("bank_ifsc", "")), key="edit_bank")
                with ec2:
                    _e_bill = st.text_input("बिल/वाउचर सं. एवं दिनांक", value=str(_old.get("bill", "")), key="edit_bill")
                    _e_amt = st.number_input("राशि (₹)", min_value=0.0, value=float(_old.get("amount", 0) or 0), step=1.0, key="edit_amt")
                    _old_comp = str(_old.get("comp_rem", ""))
                    _e_level = st.selectbox("स्तर", ["SEC", "ELE"], index=0 if _old_comp.startswith("[SEC]") else 1, key="edit_level")
                    _e_comp_name = _old_comp[5:].strip() if _old_comp.startswith(("[SEC]", "[ELE]")) else _old_comp
                    _edit_master = _load_component_master_by_level(username)
                    _e_opts = list(_edit_master.get(_e_level, [])) or [_e_comp_name]
                    if _e_comp_name not in _e_opts:
                        _e_opts.insert(0, _e_comp_name)
                    _e_comp = st.selectbox("कंपोनेंट", _e_opts, index=_e_opts.index(_e_comp_name), key="edit_comp")
                    _e_reimb = st.text_input("पुनर्भरण", value=str(_old.get("reimb_status", "")), key="edit_reimb")
                eu1, eu2 = st.columns(2)
                with eu1:
                    if st.button("💾 संशोधित प्रविष्टि सुरक्षित करें", key="btn_save_edit"):
                        _updated = dict(_old)
                        _updated.update({"inst": _e_inst.strip(), "cbeo_order_no": _e_cbeo.strip(), "firm": _e_firm.strip(), "bank_ifsc": _e_bank, "bill": _e_bill.strip(), "amount": float(_e_amt), "comp_rem": f"[{_e_level}] {_e_comp}", "reimb_status": _e_reimb})
                        st.session_state.san_items[_ei] = _updated
                        save_json_data(SAN_DATA_FILE, {"office_data": {"office_name": san_office.strip(), "district": san_district.strip(), "order_no": san_order_no.strip()}, "items": st.session_state.san_items})
                        st.session_state.san_edit_idx = None
                        st.success("प्रविष्टि सफलतापूर्वक संशोधित कर दी गई है।")
                        st.rerun()
                with eu2:
                    if st.button("✖ संपादन रद्द करें", key="btn_cancel_edit"):
                        st.session_state.san_edit_idx = None
                        st.rerun()

        # Lightweight HTML fallback for environments where Chrome/Edge is unavailable.
        # The real PDF and Excel both use the common grouped dataset above.
        fallback_groups = _prepare_sanction_groups(st.session_state.san_items)
        fallback_rows = [r for g in fallback_groups for r in g["items"]]
        fallback_total = sum(float(r.get("amount", 0) or 0) for r in fallback_rows)
        fallback_html_rows = []
        for r in fallback_rows:
            fallback_html_rows.append(
                "<tr>"
                f"<td>{r.get('_display_sno','')}</td><td>{escape(r.get('cbeo_order_no',''))}</td><td>{escape(r.get('inst',''))}</td>"
                f"<td>{escape(r.get('firm',''))}</td><td>{escape(r.get('bank_ifsc',''))}</td>"
                f"<td>{escape(r.get('bill',''))}</td><td>{float(r.get('amount',0) or 0):,.2f}</td>"
                f"<td>{escape(r.get('reimb_status',''))}</td><td>{escape(r.get('comp_rem',''))}</td>"
                "</tr>"
            )
        fallback_html = f"""<!doctype html><html lang="hi"><head><meta charset="utf-8">
        <style>@page{{size:A4 landscape;margin:8mm}}body{{font-family:Arial,sans-serif;font-size:10pt}}
        .box{{border:2px solid #000;padding:8px}}table{{width:100%;border-collapse:collapse}}
        th,td{{border:1px solid #000;padding:4px;vertical-align:middle}}th{{background:#0b4f8a;color:#fff}}
        .total{{font-weight:bold;text-align:right}}</style></head><body>
        <div class="box"><h3 style="text-align:center;color:#0b4f8a">कार्यालय {escape(san_office)}</h3>
        <h4 style="text-align:center">जिला : {escape(san_district)}</h4>
        <h2 style="text-align:center">भुगतान स्वीकृति आदेश</h2>
        <p><b>क्रमांक:</b> {escape(san_order_no)}
        <span style="float:right"><b>दिनांक:</b> {san_order_date.strftime('%d/%m/%Y')}</span></p>
        <table><tr><th>क.स.</th><th>मुख्य ब्लॉक शिक्षा अधिकारी आदेश क्रमांक</th><th>संस्था का नाम</th><th>फर्म/प्राप्तकर्ता</th>
        <th>खाता/IFSC</th><th>बिल/वाउचर</th><th>राशि</th><th>पुनर्भरण</th><th>कंपोनेंट व स्तर</th></tr>
        {''.join(fallback_html_rows)}</table>
        <p class="total">कुल योग: ₹ {fallback_total:,.2f}</p>
        </div></body></html>"""

        # FINAL OUTPUTS
        # PDF and Excel are intentionally generated independently.
        developer_text = "सॉफ्टवेयर डेवलपर: आलोक कुमार सिंह, वरिष्ठ अध्यापक, राजकीय उच्च माध्यमिक विद्यालय, रोजड़ी | ईमेल: alokjobner@gmail.com"

        pdf_bytes = None
        excel_bytes = None
        pdf_error = None
        excel_error = None

        # PDF: Chrome/Edge engine retained for correct Devanagari shaping.
        try:
            pdf_bytes = _build_sanction_pdf_bytes(
                san_office, san_district, san_order_no, san_order_date,
                st.session_state.san_items, developer_text
            )
        except Exception as exc:
            pdf_error = f"{type(exc).__name__}: {exc}"

        # Excel is completely independent from PDF generation.
        try:
            excel_bytes = _build_sanction_excel_bytes(
                san_office, san_district, san_order_no, san_order_date,
                st.session_state.san_items
            )
        except Exception as exc:
            excel_error = f"{type(exc).__name__}: {exc}"

        out1, out2 = st.columns(2)

        with out1:
            if pdf_bytes:
                st.download_button(
                    label="📄 संचालन पोर्टल आदेश डाउनलोड करें (PDF)",
                    data=pdf_bytes,
                    file_name=f"Sanchalan_Sanction_Order_{datetime.now().strftime('%Y%m%d')}.pdf",
                    mime="application/pdf",
                    key="download_sanchalan_pdf",
                    use_container_width=True,
                )
                st.caption("यदि PDF में सैंक्शन का प्रारूप सही नहीं है तो आप एक्सेल फाइल डाउनलोड करके उसे अपने अनुसार प्रारूप में बदल लें।")
            else:
                st.error(f"PDF बनाने में समस्या: {pdf_error}")
                st.download_button(
                    label="🖨 Print Preview (HTML)",
                    data=fallback_html,
                    file_name=f"Sanchalan_Sanction_Order_{datetime.now().strftime('%Y%m%d')}.html",
                    mime="text/html",
                    key="download_sanchalan_html_fallback",
                    use_container_width=True,
                )

        with out2:
            if excel_bytes:
                st.download_button(
                    label="📊 संचालन पोर्टल आदेश डाउनलोड करें (Excel)",
                    data=excel_bytes,
                    file_name=f"Sanchalan_Sanction_Order_{datetime.now().strftime('%Y%m%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="download_sanchalan_excel",
                    use_container_width=True,
                )
            else:
                st.error(f"Excel बनाने में समस्या: {excel_error}")
