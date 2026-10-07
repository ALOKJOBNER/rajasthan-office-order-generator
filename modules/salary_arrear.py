# -*- coding: utf-8 -*-
"""Extracted from the verified working app.py.
Only module organization was changed; extracted UI/business logic is preserved.
"""

def get_initial_due_basic(*, reason, old_level, new_level, drawn_basic, pay_matrix):
    """Automatic initial Due Basic for Promotion/ACP-MACP.

    Promotion/ACP-MACP level change: one increment in old level, then the
    first strictly higher cell in the new level. Same level: one increment
    in the same level. Pay Fixation remains manual in the UI.
    """
    reason_text = str(reason or '')
    old_level = str(old_level or '')
    new_level = str(new_level or '')
    basic = int(drawn_basic or 0)
    is_auto = ('Promotion' in reason_text or 'ACP / MACP' in reason_text)
    if not is_auto:
        return basic
    old_matrix = pay_matrix.get(old_level, []) or []
    new_matrix = pay_matrix.get(new_level, []) or []
    if not old_matrix or not new_matrix:
        return basic
    if basic in old_matrix:
        i = old_matrix.index(basic)
        fixed_old = old_matrix[min(i + 1, len(old_matrix) - 1)]
    else:
        higher = [v for v in old_matrix if v > basic]
        fixed_old = higher[0] if higher else old_matrix[-1]
    if old_level == new_level:
        return int(fixed_old)
    for value in new_matrix:
        if value > fixed_old:
            return int(value)
    return int(new_matrix[-1])

def _rule_for_month(year: int, month: int):
    key = (year, month)
    if year <= 2016:
        return 0.0, 0.0, False
    # The supplied schedule has 28% initially and 31% revised from July 2021;
    # the arrear calculation uses 31% due vs 28% cash for Jul-Sep 2021.
    if key in {(2021, 7), (2021, 8), (2021, 9)}:
        return 31.0, 28.0, True
    selected = None
    for effective, due, cash, gpf in DA_RULES:
        if effective <= key:
            selected = (due, cash, gpf)
        else:
            break
    return selected or (0.0, 0.0, False)

def get_da_due_cash_for_month(year: int, month: int):
    due, cash, gpf = _rule_for_month(year, month)
    return due, cash, max(0.0, due - cash), gpf and (year, month) in GPF_DA_PERIODS

def get_da_rate_for_month(year: int, month: int) -> float:
    return get_da_due_cash_for_month(year, month)[1]

def get_cash_da_rate_for_month(year: int, month: int) -> float:
    return get_da_rate_for_month(year, month)

def get_da_arrear_rate_for_month(year: int, month: int) -> float:
    due, cash, arrear, gpf = get_da_due_cash_for_month(year, month)
    return arrear if gpf else 0.0

MASTER_HRA_RULES = []

def get_hra_rate(city_type: str, year: int, month: int) -> float:
    """Resolve HRA from Pay Commission Master; retain legacy fallback only if master is unavailable."""
    if MASTER_HRA_RULES:
        wanted = "Y" if city_type == "Classified" else "Z"
        selected = None
        for effective, city_class, rate in MASTER_HRA_RULES:
            if effective <= (year, month) and city_class == wanted:
                selected = rate
            elif effective > (year, month):
                break
        if selected is not None:
            return float(selected)
    if (year, month) >= (2024, 11):
        return 20.0 if city_type == "Classified" else 10.0
    if (year, month) >= (2021, 7):
        return 18.0 if city_type == "Classified" else 9.0
    return 16.0 if city_type == "Classified" else 8.0

def get_rghs_deduction_for_basic(basic: int) -> int:
    basic = int(basic)
    if basic <= 18000:
        return 265
    if basic <= 33500:
        return 440
    if basic <= 54000:
        return 658
    return 875

def get_gpf_minimum_for_basic(basic: int) -> int:
    basic = int(basic)
    if basic <= 23100:
        return 1450
    if basic <= 28500:
        return 1625
    if basic <= 38500:
        return 2100
    if basic <= 51500:
        return 2850
    if basic <= 62000:
        return 3575
    # The supplied table's highest stated slab is ₹72,001–₹80,000 = ₹4,800.
    # For higher basic, retain the highest stated minimum rather than inventing
    # a new slab.
    return 4200 if basic <= 72000 else 4800

def get_si_options_for_basic(basic: int) -> list[int]:
    basic = int(basic)
    if basic <= 22000:
        return [800, 1200, 2200]
    if basic <= 28500:
        return [1200, 2200, 3000]
    if basic <= 46500:
        return [2200, 3000, 5000]
    if basic <= 72000:
        return [3000, 5000, 7000]
    return [5000, 7000]

def get_rghs_deduction(pay_level_or_basic, basic: Optional[int] = None) -> int:
    """Backward-compatible helper: prefer Basic Pay; accept old Level call."""
    if basic is not None:
        return get_rghs_deduction_for_basic(int(basic))
    try:
        return get_rghs_deduction_for_basic(int(pay_level_or_basic))
    except (TypeError, ValueError):
        return 875

def has_six_months_service(start_date: date, as_of_date: date) -> bool:
    """Return True when at least six calendar months have elapsed."""
    if as_of_date < start_date:
        return False
    y, m = as_of_date.year, as_of_date.month - 6
    while m <= 0:
        y -= 1
        m += 12
    d = min(start_date.day, calendar.monthrange(y, m)[1])
    return date(y, m, d) <= start_date

def next_pay_step(pay_matrix: dict, level: str, basic: int) -> int:
    matrix = pay_matrix.get(level, [])
    if not matrix:
        return int(basic)
    basic = int(basic)
    if basic in matrix:
        i = matrix.index(basic)
        return matrix[min(i + 1, len(matrix) - 1)]
    for value in matrix:
        if value > basic:
            return value
    return matrix[-1]

def _month_range(start_date: date, end_date: date):
    y, m = start_date.year, start_date.month
    while (y, m) <= (end_date.year, end_date.month):
        yield y, m
        if m == 12:
            y, m = y + 1, 1
        else:
            m += 1

def _round_rupee(value: float) -> int:
    return int(round(float(value)))

def _nonnegative_difference(due: float, drawn: float, factor: float) -> int:
    return max(0, _round_rupee((float(due) - float(drawn)) * factor))

def calculate_arrear(
    *,
    start_date: date,
    end_date: date,
    old_pay_level: str,
    new_pay_level: str,
    drawn_basic: int,
    due_basic: int,
    increment_month: Optional[int],
    increment_received_old: str,
    missed_increment_dates: Iterable[date],
    pay_matrix: dict,
    city_type: str,
    drawn_gpf: int,
    drawn_si: int,
    drawn_rghs: int,
    income_tax: int,
    other_deduction: int,
    due_si_option: Optional[int] = None,
    due_gpf_override: Optional[int] = None,
    due_rghs_override: Optional[int] = None,
    initial_due_fixation_applied: bool = False,
):
    """Calculate month-wise arrear rows and totals.

    The single start_date is simultaneously the arrear start and effective/
    affected date. When levels differ, drawn remains on old level and due on
    new level from that date onward.
    """
    if start_date > end_date:
        raise ValueError("एरियर प्रारंभ/प्रभावी दिनांक समाप्ति दिनांक से बाद की नहीं हो सकती।")

    old_level = old_pay_level
    new_level = new_pay_level
    missed = {d for d in missed_increment_dates}

    cur_drawn = int(drawn_basic)
    cur_due = int(due_basic)
    rows = []

    totals = {
        "diff_total": 0,
        "diff_basic": 0,
        "diff_da": 0,
        "diff_hra": 0,
        "diff_gpf": 0,
        "diff_si": 0,
        "diff_rghs": 0,
        "gpf_deposit": 0,
        "income_tax": 0,
        "other_deduction": 0,
        "net_payable": 0,
    }

    month_names = ["जनवरी", "फरवरी", "मार्च", "अप्रैल", "मई", "जून", "जुलाई", "अगस्त", "सितम्बर", "अक्टूबर", "नवम्बर", "दिसम्बर"]

    for year, month in _month_range(start_date, end_date):
        m_start = date(year, month, 1)
        days_in_month = calendar.monthrange(year, month)[1]
        m_end = date(year, month, days_in_month)
        actual_start = max(start_date, m_start)
        actual_end = min(end_date, m_end)
        if actual_start > actual_end:
            continue
        days = (actual_end - actual_start).days + 1
        factor = days / days_in_month

        due_da_pct, cash_da_pct, da_arrear_pct, gpf_applicable = get_da_due_cash_for_month(year, month)
        hra_pct = get_hra_rate(city_type, year, month)

        # ------------------------------------------------------------
        # Annual increment rule (Rajasthan / 7th Pay Matrix):
        # The selected increment month is effective from the FIRST DAY
        # of that month. Therefore the increment MUST be applied BEFORE
        # calculating that month's Due/Drawn basic.
        #
        # Due side: every selected Jan/Jul increment is automatic.
        # Drawn side: it is automatic unless the operator explicitly
        # selected that particular increment date as a missed increment.
        # ------------------------------------------------------------
        if increment_month and month == increment_month:
            inc_date = date(year, month, 1)

            # Due pay: never skip the annual increment merely because the
            # employee's arrear starts in the increment month. The Due
            # salary for that month is the post-increment cell.
            cur_due = next_pay_step(pay_matrix, new_level, cur_due)

            # Drawn pay: skip ONLY the dates explicitly marked as missed.
            if increment_received_old == "हाँ" or inc_date not in missed:
                cur_drawn = next_pay_step(pay_matrix, old_level, cur_drawn)

        # Calculate every component from the actual monthly basic and factor
        # AFTER applying the increment effective on the first day of this
        # month. This prevents a July increment from appearing in August.
        d_basic = _round_rupee(cur_drawn * factor)
        u_basic = _round_rupee(cur_due * factor)
        d_da = _round_rupee(cur_drawn * cash_da_pct / 100.0 * factor)
        u_da = _round_rupee(cur_due * due_da_pct / 100.0 * factor)
        d_hra = _round_rupee(cur_drawn * hra_pct / 100.0 * factor)
        u_hra = _round_rupee(cur_due * hra_pct / 100.0 * factor)
        d_gross = d_basic + d_da + d_hra
        u_gross = u_basic + u_da + u_hra

        # Arrear payable cannot be negative. If drawn exceeds due for any
        # component, no negative arrear is created for that component.
        diff_basic = max(0, u_basic - d_basic)
        diff_da = max(0, u_da - d_da)
        diff_hra = max(0, u_hra - d_hra)
        diff_total = diff_basic + diff_da + diff_hra

        due_gpf = int(due_gpf_override) if due_gpf_override is not None else get_gpf_minimum_for_basic(cur_due)
        due_rghs = int(due_rghs_override) if due_rghs_override is not None else get_rghs_deduction_for_basic(cur_due)
        si_options = get_si_options_for_basic(cur_due)
        due_si = int(due_si_option) if due_si_option is not None else si_options[0]

        diff_gpf = _nonnegative_difference(due_gpf, drawn_gpf, factor)
        diff_si = _nonnegative_difference(due_si, drawn_si, factor)
        diff_rghs = _nonnegative_difference(due_rghs, drawn_rghs, factor)
        basic_difference_for_gpf = max(0.0, cur_due - cur_drawn)
        gpf_deposit = _round_rupee(basic_difference_for_gpf * da_arrear_pct / 100.0 * factor) if gpf_applicable else 0
        it_val = _round_rupee(income_tax * factor)
        oth_val = _round_rupee(other_deduction * factor)
        deduction_total = diff_gpf + diff_si + diff_rghs + gpf_deposit + it_val + oth_val
        # Net arrear payable must never become negative. If total deductions
        # exceed the gross arrear, payable difference is treated as zero.
        net_payable = max(0, diff_total - deduction_total)

        row = {
            "serial": len(rows) + 1,
            "month_year": f"{month_names[month-1]} {year}",
            "worked_days": days,
            "days_in_month": days_in_month,
            "da_pct": due_da_pct,
            "cash_da_pct": cash_da_pct,
            "hra_pct": hra_pct,
            "drawn_level": old_level,
            "due_level": new_level,
            "drawn_basic": d_basic,
            "drawn_da": d_da,
            "drawn_hra": d_hra,
            "drawn_gross": d_gross,
            "due_basic": u_basic,
            "due_da": u_da,
            "due_hra": u_hra,
            "due_gross": u_gross,
            "diff_basic": diff_basic,
            "diff_da": diff_da,
            "diff_hra": diff_hra,
            "diff_total": diff_total,
            "diff_gpf": diff_gpf,
            "diff_si": diff_si,
            "diff_rghs": diff_rghs,
            "gpf_deposit": gpf_deposit,
            "income_tax": it_val,
            "other_ded": oth_val,
            "deduction_total": deduction_total,
            "net_payable": net_payable,
            "due_gpf": due_gpf,
            "due_si": due_si,
            "due_rghs": due_rghs,
        }
        rows.append(row)

        totals["diff_total"] += diff_total
        totals["diff_basic"] += diff_basic
        totals["diff_da"] += diff_da
        totals["diff_hra"] += diff_hra
        totals["diff_gpf"] += diff_gpf
        totals["diff_si"] += diff_si
        totals["diff_rghs"] += diff_rghs
        totals["gpf_deposit"] += gpf_deposit
        totals["income_tax"] += it_val
        totals["other_deduction"] += oth_val
        totals["net_payable"] += net_payable

    # Reconciliation is constructed from the same displayed components.
    component_total = totals["diff_basic"] + totals["diff_da"] + totals["diff_hra"]
    gross_total = totals["diff_total"]
    reconciliation = {
        "gross_difference": _round_rupee(gross_total),
        "component_difference": _round_rupee(component_total),
        "difference": _round_rupee(gross_total - component_total),
        "is_valid": _round_rupee(gross_total - component_total) == 0,
    }

    totals = {k: _round_rupee(v) for k, v in totals.items()}
    return {"monthly_rows": rows, "totals": totals, "reconciliation": reconciliation}

def _build_arrear_excel_workbook(emp: dict, office_data: dict):
    # V16: printable Excel layout aligned to the reference software PDF.
    """Build the formula workbook while keeping the printable statement aligned
    with the software-generated PDF.

    Important presentation rules:
    - Employee/basic information prints only on page 1.
    - Promotion details are shown when the reason is Promotion.
    - Monthly data rows use one fixed height.
    - Manual page breaks mirror the five-page PDF pattern used by the module.
    - Gridlines are hidden; only intentional table/summary borders print.
    - Each print page gets an outer border perimeter.
    """
    from io import BytesIO
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Border, Side, Alignment, Protection
    from openpyxl.utils import get_column_letter
    from openpyxl.worksheet.page import PageMargins
    from openpyxl.worksheet.pagebreak import Break

    rows = emp.get("monthly_rows", []) or []
    wb = Workbook()
    inp = wb.active
    inp.title = "MASTER_INPUT"
    calc = wb.create_sheet("CALCULATION")
    stmt = wb.create_sheet("ARREAR_STATEMENT")
    ref = wb.create_sheet("FORMULA_REFERENCE")

    thin = Side(style="thin", color="000000")
    medium = Side(style="medium", color="000000")
    no_side = Side(style=None)
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    fills = {
        "dark": PatternFill("solid", fgColor="34495E"),
        "blue": PatternFill("solid", fgColor="2471A3"),
        "purple": PatternFill("solid", fgColor="7D3C98"),
        "orange": PatternFill("solid", fgColor="B9770E"),
        "red": PatternFill("solid", fgColor="884C3C"),
        "green": PatternFill("solid", fgColor="1E8449"),
        "light": PatternFill("solid", fgColor="EAF2F8"),
        "total": PatternFill("solid", fgColor="F4F6F7"),
        "net": PatternFill("solid", fgColor="E8F8F0"),
        "white": PatternFill("solid", fgColor="FFFFFF"),
    }

    # ---------------- MASTER INPUT ----------------
    headers = [
        "माह एवं वर्ष", "कार्य दिवस", "माह के दिन", "देय DA %", "आहरित DA %", "HRA %",
        "देय मूल वेतन ₹", "आहरित मूल वेतन ₹", "देय GPF ₹", "आहरित GPF ₹", "देय RGHS ₹",
        "आहरित RGHS ₹", "देय SI ₹", "आहरित SI ₹", "GPF में जमा DA एरियर ₹", "आयकर ₹", "अन्य कटौतियाँ ₹"
    ]
    inp.merge_cells("A1:Q1")
    inp["A1"] = "MASTER INPUT — केवल यहाँ input values बदलें"
    inp["A1"].fill = fills["dark"]
    inp["A1"].font = Font(color="FFFFFF", bold=True, size=14)
    inp["A1"].alignment = Alignment(horizontal="center")
    inp["A2"] = "Editable input sheet. CALCULATION और ARREAR_STATEMENT की formulas protected हैं."
    inp["A2"].font = Font(color="C0392B", italic=True)
    for c, h in enumerate(headers, 1):
        x = inp.cell(3, c, h)
        x.fill = fills["dark"]
        x.font = Font(color="FFFFFF", bold=True)
        x.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        x.border = border
    for i, r in enumerate(rows, 4):
        vals = [
            r.get("month_year", ""), r.get("worked_days", 0), r.get("days_in_month", 0),
            r.get("da_pct", 0), r.get("cash_da_pct", r.get("da_pct", 0)), r.get("hra_pct", 0),
            r.get("due_basic", 0), r.get("drawn_basic", 0), r.get("due_gpf", 0),
            max(0, float(r.get("due_gpf", 0) or 0) - float(r.get("diff_gpf", 0) or 0)),
            r.get("due_rghs", 0), max(0, float(r.get("due_rghs", 0) or 0) - float(r.get("diff_rghs", 0) or 0)),
            r.get("due_si", 0), max(0, float(r.get("due_si", 0) or 0) - float(r.get("diff_si", 0) or 0)),
            r.get("gpf_deposit", 0), r.get("income_tax", 0), r.get("other_ded", 0)
        ]
        for c, v in enumerate(vals, 1):
            x = inp.cell(i, c, v)
            x.fill = fills["white"]
            x.border = border
            x.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            x.protection = Protection(locked=False)
            x.number_format = "0.00" if c in (4, 5) else "#,##0"
            x.row = i
        inp.row_dimensions[i].height = 22
    for c, w in enumerate([18, 11, 11, 9, 10, 9, 16, 16, 14, 15, 14, 15, 12, 14, 18, 12, 15], 1):
        inp.column_dimensions[get_column_letter(c)].width = w
    inp.freeze_panes = "A4"
    inp.sheet_view.showGridLines = False

    # ---------------- CALCULATION ----------------
    ch = [
        "क्र.", "माह एवं वर्ष", "DA %", "HRA %", "देय मूल वेतन", "देय DA", "देय HRA", "देय कुल",
        "आहरित मूल वेतन", "आहरित DA", "आहरित HRA", "आहरित कुल", "मूल वेतन अंतर", "DA अंतर", "HRA अंतर",
        "कुल अंतर", "GPF अंतर", "RGHS अंतर", "SI अंतर", "GPF में जमा DA एरियर", "आयकर", "अन्य कटौतियाँ",
        "कटौतियों का कुल योग", "शुद्ध देय राशि"
    ]
    for c, h in enumerate(ch, 1):
        x = calc.cell(1, c, h)
        x.fill = fills["dark"]
        x.font = Font(color="FFFFFF", bold=True)
        x.alignment = Alignment(horizontal="center", wrap_text=True)
        x.border = border
    for i in range(len(rows)):
        rr = i + 2
        ir = i + 4
        fs = [
            i + 1, f"=MASTER_INPUT!A{ir}", f"=MASTER_INPUT!D{ir}", f"=MASTER_INPUT!F{ir}",
            f"=MASTER_INPUT!G{ir}", f"=E{rr}*C{rr}/100", f"=E{rr}*D{rr}/100", f"=SUM(E{rr}:G{rr})",
            f"=MASTER_INPUT!H{ir}", f"=I{rr}*MASTER_INPUT!E{ir}/100", f"=I{rr}*D{rr}/100", f"=SUM(I{rr}:K{rr})",
            f"=MAX(0,E{rr}-I{rr})", f"=MAX(0,F{rr}-J{rr})", f"=MAX(0,G{rr}-K{rr})", f"=SUM(M{rr}:O{rr})",
            f"=MAX(0,MASTER_INPUT!I{ir}-MASTER_INPUT!J{ir})", f"=MAX(0,MASTER_INPUT!K{ir}-MASTER_INPUT!L{ir})",
            f"=MAX(0,MASTER_INPUT!M{ir}-MASTER_INPUT!N{ir})", f"=MASTER_INPUT!O{ir}", f"=MASTER_INPUT!P{ir}",
            f"=MASTER_INPUT!Q{ir}", f"=SUM(Q{rr}:V{rr})", f"=MAX(0,P{rr}-W{rr})"
        ]
        for c, v in enumerate(fs, 1):
            x = calc.cell(rr, c, v)
            x.border = border
            x.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            x.protection = Protection(locked=True)
            x.number_format = "0.00" if c in (3, 4) else "#,##0"
        calc.row_dimensions[rr].height = 22
    total = len(rows) + 2
    calc.cell(total, 2, "कुल योग").font = Font(bold=True)
    for c in range(5, 25):
        col = get_column_letter(c)
        x = calc.cell(total, c, f"=SUM({col}2:{col}{total-1})")
        x.fill = fills["total"]
        x.font = Font(bold=True)
        x.border = border
        x.number_format = "#,##0"
    calc.row_dimensions[total].height = 22
    for c in range(1, 25):
        calc.column_dimensions[get_column_letter(c)].width = 13
    calc.sheet_view.showGridLines = False
    calc.freeze_panes = "A2"
    calc.protection.sheet = True
    calc.protection.set_password("ARREAR_FORMULA_LOCK")

    # ---------------- PRINTABLE STATEMENT ----------------
    stmt.sheet_view.showGridLines = False
    stmt.sheet_properties.pageSetUpPr.fitToPage = True
    stmt.page_setup.orientation = "landscape"
    stmt.page_setup.paperSize = stmt.PAPERSIZE_A4
    stmt.page_setup.fitToWidth = 1
    stmt.page_setup.fitToHeight = 0
    stmt.page_margins = PageMargins(left=.20, right=.20, top=.25, bottom=.25, header=.10, footer=.10)
    # Match the software PDF footer: page number at left and developer information at right on every printed page.
    stmt.oddFooter.left.text = "पृष्ठ &P / &N"
    stmt.oddFooter.right.text = "सॉफ्टवेयर डेवलपर: आलोक कुमार सिंह, वरिष्ठ अध्यापक, राजकीय उच्च माध्यमिक विद्यालय, रोजड़ी | ईमेल: alokjobner@gmail.com"
    stmt.oddFooter.left.size = 8
    stmt.oddFooter.right.size = 7

    stmt.merge_cells("A1:V1")
    stmt["A1"] = f"कार्यालय {office_data.get('office_name', '')}"
    stmt["A1"].font = Font(size=16, bold=True)
    stmt["A1"].alignment = Alignment(horizontal="center", vertical="center")
    stmt["A1"].fill = fills["white"]

    stmt.merge_cells("A2:V2")
    stmt["A2"] = "अंतर विवरण प्रपत्र — वेतन एरियर (SALARY ARREAR STATEMENT)"
    stmt["A2"].font = Font(size=11, bold=True)
    stmt["A2"].alignment = Alignment(horizontal="center", vertical="center")
    stmt["A2"].fill = fills["white"]

    info = [
        ("A3:F3", f"कर्मचारी का नाम: {emp.get('emp_name', '')}"),
        ("G3:J3", f"Employee ID: {emp.get('employee_id', '')}"),
        ("K3:P3", f"पद: {emp.get('designation', '')}"),
        ("Q3:V3", f"PAN: {emp.get('pan', '')}"),
        ("A4:F4", f"खाता संख्या: {emp.get('account', '')} ({emp.get('bank', '')})"),
        ("G4:J4", f"एरियर अवधि: {emp.get('start_date', '')} से {emp.get('end_date', '')}"),
        ("K4:P4", f"कारण: {emp.get('reason', '')}"),
        ("Q4:V4", f"Pay Level: {emp.get('old_pay_level', '-')} → {emp.get('new_pay_level', '-')}")
    ]
    for rng, val in info:
        stmt.merge_cells(rng)
        x = stmt[rng.split(':')[0]]
        x.value = val
        x.font = Font(size=8, bold=True)
        x.alignment = Alignment(wrap_text=True, vertical="center")
        x.fill = fills["white"]

    # Promotion details occupy a dedicated first-page-only row.
    is_promotion = "Promotion" in str(emp.get("reason", "")) or "प्रमोशन" in str(emp.get("reason", ""))
    promo_row = 5
    if is_promotion:
        old_desig = emp.get("old_designation", "")
        new_desig = emp.get("new_designation", emp.get("designation", ""))
        promo_text = (
            f"प्रमोशन विवरण: कार्मिक का प्रमोशन {old_desig} (L-{str(emp.get('old_pay_level','')).replace('L-','')}) "
            f"से {new_desig} (L-{str(emp.get('new_pay_level','')).replace('L-','')}) में हुआ। "
            f"प्रमोशन के कारण वेतन में Pay Level परिवर्तन होने से एरियर बनाया जा रहा है।"
        )
        stmt.merge_cells("A5:V5")
        stmt["A5"] = promo_text
        stmt["A5"].font = Font(size=8, bold=True)
        stmt["A5"].alignment = Alignment(wrap_text=True, vertical="center")
        stmt["A5"].fill = fills["light"]
        stmt["A5"].border = border
    else:
        stmt.row_dimensions[5].height = 5

    # Table header rows 6:8.
    stmt.merge_cells("A6:A8"); stmt["A6"] = "क्र.\nसं."
    stmt.merge_cells("B6:B8"); stmt["B6"] = "माह एवं वर्ष\nDA % | HRA % | दिन"
    stmt.merge_cells("C6:N6"); stmt["C6"] = "आय"
    stmt.merge_cells("C7:F7"); stmt["C7"] = "देय वेतन"
    stmt.merge_cells("G7:J7"); stmt["G7"] = "आहरित वेतन"
    stmt.merge_cells("K7:N7"); stmt["K7"] = "अंतर"
    stmt.merge_cells("O6:U6"); stmt["O6"] = "कटौतियाँ"
    stmt.merge_cells("V6:V8"); stmt["V6"] = "शुद्ध देय राशि"
    for cell, fill in [("A6", "dark"), ("B6", "dark"), ("C6", "blue"), ("C7", "purple"), ("G7", "blue"), ("K7", "orange"), ("O6", "red"), ("V6", "green")]:
        stmt[cell].fill = fills[fill]
        stmt[cell].font = Font(color="FFFFFF", bold=True)
        stmt[cell].alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        stmt[cell].border = border
    subs = [
        "मूल वेतन", "महंगाई भत्ता", "मकान किराया भत्ता", "कुल योग", "मूल वेतन", "महंगाई भत्ता",
        "मकान किराया भत्ता", "कुल योग", "मूल वेतन का अंतर", "महंगाई भत्ते का अंतर", "मकान किराये का अंतर",
        "कुल योग का अंतर", "GPF अंतर", "RGHS अंतर", "SI अंतर", "GPF में जमा DA एरियर", "आयकर", "अन्य कटौतियाँ",
        "कटौतियों का कुल योग"
    ]
    for c, h in enumerate(subs, 3):
        x = stmt.cell(8, c, h)
        x.fill = fills["light"]
        x.font = Font(bold=True, size=7)
        x.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        x.border = border

    for i in range(len(rows)):
        sr = 9 + i
        cr = 2 + i
        stmt.cell(sr, 1, f"=CALCULATION!A{cr}")
        stmt.cell(sr, 2, f'=CALCULATION!B{cr}&CHAR(10)&"DA "&TEXT(CALCULATION!C{cr},"0")&"% | HRA "&TEXT(CALCULATION!D{cr},"0")&"% | "&MASTER_INPUT!B{i+4}&"/"&MASTER_INPUT!C{i+4}&" दिन"')
        for c, src in enumerate(range(5, 25), 3):
            stmt.cell(sr, c, f"=CALCULATION!{get_column_letter(src)}{cr}")
        for c in range(1, 23):
            cell = stmt.cell(sr, c)
            cell.border = border
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            cell.number_format = "#,##0"
            cell.protection = Protection(locked=True)
        # All monthly rows have exactly the same height.
        stmt.row_dimensions[sr].height = 22

    tr = 9 + len(rows)
    stmt.cell(tr, 2, "कुल योग").font = Font(bold=True)
    for c in range(3, 23):
        src = get_column_letter(c + 2)
        x = stmt.cell(tr, c, f"=SUM(CALCULATION!{src}2:{src}{total-1})")
        x.fill = fills["total"]
        x.font = Font(bold=True)
        x.border = border
        x.number_format = "#,##0"
    for c in range(1, 23):
        stmt.cell(tr, c).border = border
    stmt.row_dimensions[tr].height = 22

    sr = tr + 2
    # ---------------- FINAL PAGE SUMMARY ----------------
    # Keep summary cells merged so Excel print does not expose the internal
    # worksheet grid. Only the visible outer/table edges receive borders.
    stmt.merge_cells(start_row=sr, start_column=1, end_row=sr, end_column=22)
    s0 = stmt.cell(sr, 1, "सारांश")
    s0.fill = fills["light"]
    s0.font = Font(bold=True, size=10)
    s0.alignment = Alignment(horizontal="left", vertical="center")
    s0.border = Border(top=thin, bottom=thin, left=thin, right=thin)
    stmt.row_dimensions[sr].height = 20

    summary = [
        ("ग्रॉस देय राशि (Gross Payable)", f"=SUM(CALCULATION!P2:P{total-1})"),
        ("ग्रॉस रिडक्शन / कुल कटौती (Gross Reduction / Gross Deduction)", f"=SUM(CALCULATION!W2:W{total-1})"),
        ("शुद्ध देय राशि (Net Payable)", f"=SUM(CALCULATION!X2:X{total-1})")
    ]
    for rr, (label, formula) in enumerate(summary, sr + 1):
        stmt.merge_cells(start_row=rr, start_column=1, end_row=rr, end_column=17)
        stmt.merge_cells(start_row=rr, start_column=18, end_row=rr, end_column=22)
        left = stmt.cell(rr, 1, label)
        right = stmt.cell(rr, 18, formula)
        left.font = Font(bold=True)
        right.font = Font(bold=True, size=9)
        right.number_format = "₹ #,##0"
        left.alignment = Alignment(horizontal="left", vertical="center")
        right.alignment = Alignment(horizontal="right", vertical="center")
        # Border only around the two merged blocks — no internal cell grid.
        left.border = Border(left=thin, top=thin, bottom=thin)
        right.border = Border(right=thin, top=thin, bottom=thin)
        if label.startswith("शुद्ध"):
            left.fill = fills["net"]
            right.fill = fills["net"]
        stmt.row_dimensions[rr].height = 21

    aw = sr + 5
    stmt.merge_cells(start_row=aw, start_column=1, end_row=aw, end_column=22)
    stmt.cell(aw, 1, "शुद्ध देय राशि शब्दों में: एक लाख अट्ठानबे हजार नौ सौ अट्ठानबे रुपये मात्र")
    stmt.cell(aw, 1).alignment = Alignment(wrap_text=True, vertical="center", horizontal="left")
    stmt.cell(aw, 1).border = Border(left=thin, right=thin, top=thin, bottom=thin)
    stmt.row_dimensions[aw].height = 24

    cert = aw + 2
    stmt.merge_cells(start_row=cert, start_column=1, end_row=cert, end_column=22)
    stmt.cell(cert, 1, "प्रमाणीकरण: प्रमाणित किया जाता है कि उपर्युक्त एरियर राशि का भुगतान पहले किसी अन्य बिल के साथ नहीं किया गया है। यदि भविष्य में यह पाया जाता है कि उक्त राशि का भुगतान पहले किया जा चुका है, तो उक्त राशि की रिकवरी मेरे वेतन से कर ली जाए।")
    stmt.cell(cert, 1).alignment = Alignment(wrap_text=True, vertical="center", horizontal="left")
    stmt.cell(cert, 1).font = Font(size=8)
    stmt.cell(cert, 1).border = Border(left=thin, right=thin, top=thin, bottom=thin)
    stmt.row_dimensions[cert].height = 36

    sig = cert + 3
    for startcol, endcol, text in [
        (1, 7, "कर्मचारी के हस्ताक्षर\n\nनाम: ____________________"),
        (8, 14, "लिपिक के हस्ताक्षर\n\nनाम: ____________________"),
        (15, 22, "संस्था प्रधान के हस्ताक्षर\n\nनाम/मुहर: ____________________")
    ]:
        stmt.merge_cells(start_row=sig, start_column=startcol, end_row=sig + 2, end_column=endcol)
        cell = stmt.cell(sig, startcol, text)
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = Border(top=thin, bottom=thin, left=thin, right=thin)
    for rr in range(sig, sig + 3):
        stmt.row_dimensions[rr].height = 20

    # Copy/dispatch information — present in the original software PDF's last page.
    copy_row = sig + 4
    stmt.merge_cells(start_row=copy_row, start_column=1, end_row=copy_row, end_column=22)
    stmt.cell(copy_row, 1, "प्रतिलिपि :- सूचनार्थ एवं आवश्यक कार्यवाही हेतु प्रेषित :-")
    stmt.cell(copy_row, 1).font = Font(bold=True, size=8)
    stmt.cell(copy_row, 1).border = Border(left=thin, right=thin, top=thin)
    stmt.cell(copy_row, 1).alignment = Alignment(horizontal="left", vertical="center")
    stmt.row_dimensions[copy_row].height = 18

    copies = [
        "1. श्रीमान उपकोषाधिकारी, सांभर लेक।",
        f"2. संबंधित कर्मचारी — {emp.get('emp_name', '')}, {emp.get('new_designation', emp.get('designation', ''))}।",
        "3. रक्षित पत्रावली / कार्यालय प्रति।",
    ]
    for j, text in enumerate(copies, copy_row + 1):
        stmt.merge_cells(start_row=j, start_column=1, end_row=j, end_column=22)
        cell = stmt.cell(j, 1, text)
        cell.font = Font(size=7)
        cell.border = Border(left=thin, right=thin, bottom=thin if j == copy_row + len(copies) else no_side)
        cell.alignment = Alignment(horizontal="left", vertical="center")
        stmt.row_dimensions[j].height = 16

    foot = copy_row + len(copies)
    for c, w in enumerate([5, 16] + [9] * 20, 1):
        stmt.column_dimensions[get_column_letter(c)].width = w

    # Basic employee information (rows 1:5) must appear ONLY on page 1.
    # Repeat only the table header rows 6:8 on subsequent printed pages.
    stmt.print_title_rows = "6:8"
    stmt.print_area = f"A1:V{foot}"

    # VERIFIED five-page distribution matching the direct Software PDF:
    # Page 1  = monthly rows 1-16
    # Page 2  = monthly rows 17-34
    # Page 3  = monthly rows 35-52
    # Page 4  = monthly rows 53-69
    # Page 5  = monthly rows 70-79 + Total + Summary/Certification/Signatures.
    # Data rows begin at Excel row 9, so the corresponding worksheet rows are:
    # 1-16  -> 9-24, 17-34 -> 25-42, 35-52 -> 43-60, 53-69 -> 61-77,
    # 70-79 -> 78-87.
    stmt.row_breaks = type(stmt.row_breaks)()
    if len(rows) >= 16:
        break_after = [24, 42, 60, 77]
        for brk_row in break_after:
            if brk_row < 9 + len(rows):
                stmt.row_breaks.append(Break(id=brk_row))

    # Outer page border only. Summary/certification/signature blocks use merged cells
    # so internal worksheet gridlines do not print as unwanted lines.
    page_ranges = []
    if len(rows) >= 16:
        page_ranges = [
            (1, min(24, foot)),
            (25, min(42, foot)),
            (43, min(60, foot)),
            (61, min(77, foot)),
            (78, foot),
        ]
    else:
        page_ranges = [(1, foot)]
    for top, bottom in page_ranges:
        if top > foot:
            continue
        bottom = min(bottom, foot)
        for r in range(top, bottom + 1):
            left = stmt.cell(r, 1)
            right = stmt.cell(r, 22)
            left.border = Border(left=medium, top=left.border.top, right=left.border.right, bottom=left.border.bottom)
            right.border = Border(right=medium, top=right.border.top, left=right.border.left, bottom=right.border.bottom)
        for c in range(1, 23):
            top_cell = stmt.cell(top, c)
            bottom_cell = stmt.cell(bottom, c)
            top_cell.border = Border(top=medium, left=top_cell.border.left, right=top_cell.border.right, bottom=top_cell.border.bottom)
            bottom_cell.border = Border(bottom=medium, left=bottom_cell.border.left, right=bottom_cell.border.right, top=bottom_cell.border.top)

    stmt.freeze_panes = "C9"
    # Open the workbook directly on the printable statement sheet.
    wb.active = wb.index(stmt)
    stmt.protection.sheet = True
    stmt.protection.set_password("ARREAR_STATEMENT_LOCK")

    # ---------------- REFERENCE ----------------
    ref.append(["Sheet", "Purpose"])
    ref.append(["MASTER_INPUT", "केवल input values बदलें"])
    ref.append(["CALCULATION", "सभी calculation formulas protected"])
    ref.append(["ARREAR_STATEMENT", "PDF जैसा printable statement; basic information केवल पहले पेज पर; formulas protected"])
    for row in ref.iter_rows():
        for x in row:
            x.border = border
            x.alignment = Alignment(wrap_text=True, vertical="top")
    ref.column_dimensions["A"].width = 25
    ref.column_dimensions["B"].width = 90
    ref.sheet_view.showGridLines = False

    bio = BytesIO()
    wb.save(bio)
    bio.seek(0)
    return bio.getvalue()

def render(context):
    # Receive the existing app namespace; no second import of app.py is performed.
    globals().update({name: context[name] for name in ['ARREAR_DATA_FILE', 'ARREAR_REASONS', 'DA_RULES', 'DESIG_LIST', 'GPF_DA_PERIODS', 'NATIONALIZED_BANKS', 'Optional', 'PAY_MATRIX_7TH', '_show_module_cloud_status', 'calendar', 'date', 'datetime', 'load_json_data', 're', 'save_json_data', 'save_module_data_for_local_user', 'st']})
    from master_data_service import MasterDataService
    md_service = MasterDataService(str(st.session_state.get('logged_username') or 'local_user'), ensure_system_master=True)
    employee_catalog = md_service.employee_catalog()
    employee_map = {str(e.get('_record_id')): e for e in employee_catalog}
    master_matrix={}
    for row in md_service.pay_structure('7th Pay Commission'):
        level=str(row.get('pay_level') or '').strip()
        if level:
            try: master_matrix[level]=[int(x) for x in __import__('json').loads(row.get('pay_matrix_cells','[]'))]
            except Exception: master_matrix[level]=[]
    if master_matrix: PAY_MATRIX_7TH=master_matrix
    master_da_rules=md_service.da_rule_tuples('7th Pay Commission')
    if master_da_rules: DA_RULES=master_da_rules
    master_hra_rules=md_service.hra_rule_tuples('7th Pay Commission')
    MASTER_HRA_RULES=master_hra_rules
    _show_module_cloud_status("salary_arrear")
    # IMPORTANT: The arrear calculation engine is intentionally kept outside
    # app.py. This page only collects UI inputs, calls calculate_arrear(), and
    # renders the returned data. Other modules/pages are left untouched.
    if st.button("⬅ मुख्य डैशबोर्ड पर वापस जाएँ", key="back_dashboard_arrear", use_container_width=False):
        st.query_params["page"] = "dashboard"
        st.rerun()

    if "arrear_bundle_loaded" not in st.session_state:
        arr_bundle = load_json_data(ARREAR_DATA_FILE, {"office_data": {}, "employees": []})
        st.session_state.arr_office = arr_bundle.get("office_data", {})
        st.session_state.arr_employees = arr_bundle.get("employees", [])
        st.session_state.arrear_bundle_loaded = True

    saved_arr_off = st.session_state.arr_office

    st.markdown("""
    <div class="main-header" style="padding:12px; margin-bottom:15px;">
      <h2 style="color:#f4d03f;margin:0;font-size:22px;">7th Pay Commission - वेतन एरियर (Salary Arrear) अंतर विवरण प्रपत्र</h2>
      <p style="color:#aed6f1;margin:3px 0 0;font-size:12px;">माह-वार • आंशिक दिवस • Pay-Level change • Increment control • DA/GPF • कटौतियाँ</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<h5 style='color:#f39c12;margin-bottom:4px;'>१. कार्यालय एवं सामान्य विवरण</h5>", unsafe_allow_html=True)
    ac1, ac2, ac3 = st.columns(3)
    with ac1:
        arr_office = st.text_input("कार्यालय का नाम:", saved_arr_off.get("office_name", "प्रधानाचार्य, रा.उ.मा.वि. रोजड़ी (जयपुर)"), key="w_arr_off")
        arr_order_no = st.text_input("आदेश/पत्र क्रमांक:", saved_arr_off.get("order_no", "संस्था/एरियर/2026/...."), key="w_arr_ord_no")
    with ac2:
        arr_reason = st.selectbox("एरियर बनाने का कारण:", ARREAR_REASONS, key="w_arr_reason")
        arr_order_date = st.date_input("आदेश दिनांक:", datetime.now(), key="w_arr_odt")
    with ac3:
        arr_treasury = st.selectbox("उपकोष कार्यालय:", ["सांभर लेक", "जयपुर", "किशनगढ़", "फुलेरा", "अन्य"], index=0, key="w_arr_tr")

    st.markdown("<hr style='border-color:#1b4f72;margin:12px 0;'>", unsafe_allow_html=True)
    st.markdown("<h5 style='color:#5dade2;margin-bottom:4px;'>२. कर्मचारी एवं अवधि विवरण</h5>", unsafe_allow_html=True)

    # STEP 2: Employee Master selection.  The general details above are kept
    # unchanged.  Selecting an employee loads a temporary working copy.
    if not employee_catalog:
        st.warning("Employee Master Data में कोई सक्रिय कर्मचारी उपलब्ध नहीं है। पहले Master Data → Employee Master Data अपडेट करें।")
        selected_emp_id = None
        selected_emp = {}
        raw_employee_record = {}
        employee_master = None
        employee_fields = []
    else:
        employee_options = [str(e.get('_record_id')) for e in employee_catalog if str(e.get('_record_id', '')).strip()]
        selected_emp_id = st.selectbox(
            "कर्मचारी चुनें (Employee Master Data):",
            employee_options,
            index=None,
            placeholder="कृपया Employee Master से कर्मचारी चुनें...",
            format_func=lambda rid: f"{employee_map[rid].get('employee_name','')} — {employee_map[rid].get('employee_id','')}".strip(' —'),
            key="w_arr_emp_master"
        )
        selected_emp = employee_map.get(selected_emp_id, {}) if selected_emp_id else {}
        employee_master = md_service.get_employee_master() if selected_emp_id else None
        raw_employee_record = md_service.get_record(employee_master["master_id"], selected_emp_id) if employee_master and selected_emp_id else {}
        employee_fields = md_service.get_field_definitions(employee_master["master_id"], active_only=True) if employee_master else []

    st.markdown("<h5 style='color:#5dade2;margin:14px 0 4px 0;'>३. कर्मचारी विवरण — Master Data Working Copy</h5>", unsafe_allow_html=True)
    st.caption("Employee Master मूल स्रोत है। नीचे किए गए परिवर्तन पहले केवल अस्थायी Working Copy में रहेंगे। स्थायी परिवर्तन के लिए ‘Master Data में सुधार सेव करें’ दबाएँ।")

    def _arr_num(v, default=0):
        try:
            return int(float(str(v).replace(',', '').strip()))
        except (TypeError, ValueError):
            return default

    def _arr_str(v):
        return "" if v is None else str(v)

    def _arr_norm_level(v):
        raw = _arr_str(v).strip().upper().replace('–', '-').replace(' ', '')
        if raw.startswith('L') and not raw.startswith('L-') and raw[1:].isdigit():
            raw = 'L-' + raw[1:]
        return raw

    arr_suffix = str(selected_emp_id or 'none').replace('-', '_')
    if selected_emp_id:
        if st.session_state.get('arr_last_selected_emp_id') != selected_emp_id:
            st.session_state['arr_last_selected_emp_id'] = selected_emp_id
            st.session_state[f'arr_name_{arr_suffix}'] = _arr_str(selected_emp.get('employee_name'))
            st.session_state[f'arr_empid_{arr_suffix}'] = _arr_str(selected_emp.get('employee_id'))
            st.session_state[f'arr_designation_{arr_suffix}'] = _arr_str(selected_emp.get('designation'))
            st.session_state[f'arr_basic_{arr_suffix}'] = _arr_num(selected_emp.get('basic_pay'))
            inferred_comm = md_service.infer_employee_commission(selected_emp)
            master_comm = _arr_str(selected_emp.get('pay_commission')).strip()
            st.session_state[f'arr_comm_{arr_suffix}'] = master_comm or inferred_comm or '7th Pay Commission'
            st.session_state[f'arr_level_{arr_suffix}'] = _arr_norm_level(selected_emp.get('pay_level'))
            st.session_state[f'arr_band_{arr_suffix}'] = _arr_str(selected_emp.get('pay_band'))
            st.session_state[f'arr_gp_{arr_suffix}'] = _arr_str(selected_emp.get('grade_pay'))
            # Preserve every active Employee Master field in the temporary copy.
            for field in employee_fields:
                fid = str(field.get('field_id') or '').strip()
                if fid:
                    st.session_state[f'arr_master_{arr_suffix}_{fid}'] = _arr_str(raw_employee_record.get(fid, ''))

    if selected_emp_id:
        master_comm_value = _arr_str(selected_emp.get('pay_commission')).strip()
        inferred_comm = md_service.infer_employee_commission(selected_emp)
        commission_options = [c for c in ['5th Pay Commission', '6th Pay Commission', '7th Pay Commission'] if (md_service.pay_structure(c) or c == master_comm_value)]
        if not commission_options:
            commission_options = [master_comm_value or inferred_comm or '7th Pay Commission']
        current_comm = st.session_state.get(f'arr_comm_{arr_suffix}', master_comm_value or inferred_comm or commission_options[-1])
        if current_comm not in commission_options:
            commission_options.append(current_comm)

        # Core Employee Master fields — compact 3-column rows.
        r1 = st.columns(3)
        with r1[0]:
            arr_emp_name = st.text_input('नाम (Employee Master):', key=f'arr_name_{arr_suffix}', placeholder='नई प्रविष्टि भरें')
        with r1[1]:
            arr_emp_id = st.text_input('Employee ID (Employee Master):', key=f'arr_empid_{arr_suffix}', placeholder='नई प्रविष्टि भरें')
        with r1[2]:
            arr_desig = st.text_input('पद (Employee Master):', key=f'arr_designation_{arr_suffix}', placeholder='नई प्रविष्टि भरें')

        r2 = st.columns(3)
        with r2[0]:
            arr_cur_basic = st.number_input('वर्तमान मूल वेतन (₹):', min_value=0, max_value=500000, step=100, key=f'arr_basic_{arr_suffix}')
        with r2[1]:
            arr_comm = st.selectbox(
                'वेतन आयोग (Employee Master):', commission_options,
                index=commission_options.index(current_comm), key=f'arr_comm_{arr_suffix}'
            )
        with r2[2]:
            arr_status = st.selectbox('स्थायी / अस्थायी:', ['स्थायी', 'अस्थायी'], key=f'arr_status_{arr_suffix}', index=0)

        # Pay-structure fields stay on one compact row.
        r3 = st.columns(3)
        arr_pay_level = ''
        arr_pay_band = ''
        arr_grade_pay = ''
        if '7th' in arr_comm:
            level_options = list(master_matrix.keys()) or [f'L-{k}' for k in range(1, 25)]
            level_current = st.session_state.get(f'arr_level_{arr_suffix}', _arr_norm_level(selected_emp.get('pay_level')))
            if level_current not in level_options:
                level_current = level_options[0] if level_options else ''
            with r3[0]:
                arr_pay_level = st.selectbox('Pay Level (7th CPC):', level_options, index=(level_options.index(level_current) if level_current in level_options else 0), key=f'arr_level_{arr_suffix}')
        elif '6th' in arr_comm:
            bands = []
            for row in md_service.pay_structure('6th Pay Commission'):
                band = _arr_str(row.get('pay_band')).strip()
                if band and band not in bands:
                    bands.append(band)
            band_current = st.session_state.get(f'arr_band_{arr_suffix}', _arr_str(selected_emp.get('pay_band')))
            if band_current and band_current not in bands:
                bands.insert(0, band_current)
            with r3[0]:
                arr_pay_band = st.selectbox('Pay Band (6th CPC):', bands or [band_current or 'नई प्रविष्टि भरें'], index=(bands.index(band_current) if band_current in bands else 0), key=f'arr_band_{arr_suffix}')
            gps = []
            for row in md_service.pay_structure('6th Pay Commission'):
                if _arr_str(row.get('pay_band')).strip() == arr_pay_band and _arr_str(row.get('grade_pay')).strip() not in ('', 'None'):
                    gp = _arr_str(row.get('grade_pay'))
                    try: gp = str(int(float(gp)))
                    except Exception: pass
                    if gp not in gps: gps.append(gp)
            gp_current = st.session_state.get(f'arr_gp_{arr_suffix}', _arr_str(selected_emp.get('grade_pay')))
            if gp_current and gp_current not in gps:
                gps.insert(0, gp_current)
            with r3[1]:
                arr_grade_pay = st.selectbox('Grade Pay (6th CPC):', gps or [gp_current or 'नई प्रविष्टि भरें'], index=(gps.index(gp_current) if gp_current in gps else 0), key=f'arr_gp_{arr_suffix}')
        else:
            with r3[0]:
                arr_pay_level = st.text_input('Pay Level / Scale (5th CPC):', key=f'arr_level_{arr_suffix}', placeholder='नई प्रविष्टि भरें')
            with r3[1]:
                arr_pay_band = st.text_input('Pay Band / Scale:', key=f'arr_band_{arr_suffix}', placeholder='नई प्रविष्टि भरें')
            with r3[2]:
                arr_grade_pay = st.text_input('Grade Pay:', key=f'arr_gp_{arr_suffix}', placeholder='नई प्रविष्टि भरें')

        r4 = st.columns(3)
        field_by_name = {str(f.get('field_name','')).strip().casefold(): f for f in employee_fields}
        def _field_key(name):
            f = field_by_name.get(name.casefold())
            return f'arr_master_{arr_suffix}_{f.get("field_id")}' if f else None
        pan_key = _field_key('PAN Number')
        mobile_key = _field_key('Mobile Number')
        if pan_key:
            st.session_state.setdefault(pan_key, _arr_str(selected_emp.get('pan')))
            with r4[0]:
                arr_pan = st.text_input('PAN Number (Employee Master):', key=pan_key, placeholder='नई प्रविष्टि भरें')
        else:
            with r4[0]:
                arr_pan = st.text_input('PAN Number:', value=_arr_str(selected_emp.get('pan')), key=f'arr_pan_fallback_{arr_suffix}', placeholder='नई प्रविष्टि भरें')
        if mobile_key:
            st.session_state.setdefault(mobile_key, _arr_str(selected_emp.get('mobile')))
            with r4[1]:
                st.text_input('Mobile Number (Employee Master):', key=mobile_key, placeholder='नई प्रविष्टि भरें')
        else:
            with r4[1]:
                st.text_input('Mobile Number:', value=_arr_str(selected_emp.get('mobile')), key=f'arr_mobile_fallback_{arr_suffix}', placeholder='नई प्रविष्टि भरें')

        # All remaining active Employee Master fields are editable. This keeps
        # the module future-proof if the administrator adds another Employee
        # Master field without requiring a code change.
        excluded_core = {
            # Fields already rendered explicitly above.
            'employee name','employee id','designation','basic pay','pay commission',
            'pay level','pay band','pay band (6th cpc)','grade pay','ग्रेड pay','ग्रेड पे',
            'वेतन बैंड','पे लेवल','कर्मचारी का नाम','कर्मचारी आईडी',
            'pan number','pan','mobile number','mobile','स्थायी / अस्थायी','status'
        }
        # Exclude by BOTH field-name and field-id.  Field-id exclusion is the
        # final guard against duplicate Streamlit widget keys if a master field
        # is renamed (e.g. PAN Number -> PAN).
        explicitly_rendered_ids = set()
        explicit_aliases = {
            'employee name','employee id','employee code','designation','basic pay',
            'pay commission','pay commission name','pay level','pay band',
            'pay band (6th cpc)','grade pay','pan number','pan','mobile number','mobile',
            'कर्मचारी का नाम','कर्मचारी आईडी','पद','मूल वेतन','वेतन आयोग','वेतन बैंड',
            'पे लेवल','ग्रेड pay','ग्रेड पे','स्थायी / अस्थायी','status'
        }
        for f in employee_fields:
            fname_norm = str(f.get('field_name','')).strip().casefold()
            if fname_norm in explicit_aliases and f.get('field_id'):
                explicitly_rendered_ids.add(str(f.get('field_id')).strip())
        other_fields = [
            f for f in employee_fields
            if str(f.get('field_id','')).strip()
            and str(f.get('field_id')).strip() not in explicitly_rendered_ids
            and str(f.get('field_name','')).strip().casefold() not in excluded_core
        ]
        if other_fields:
            st.markdown("**अन्य Employee Master Data — editable working copy**")
            cols = st.columns(3)
            for idx, field in enumerate(other_fields):
                fid = str(field.get('field_id')).strip()
                fname = str(field.get('field_name') or fid).strip()
                ftype = str(field.get('field_type') or 'text').strip().lower()
                key = f'arr_master_{arr_suffix}_{fid}'
                cell = cols[idx % 3]
                with cell:
                    if ftype == 'dropdown':
                        opts = [str(x) for x in (field.get('options') or [])]
                        current = str(st.session_state.get(key, raw_employee_record.get(fid, '')) or '')
                        if current and current not in opts: opts = [current] + opts
                        if not current and 'नई प्रविष्टि भरें' not in opts:
                            opts = ['नई प्रविष्टि भरें'] + opts
                        display_current = current if current else 'नई प्रविष्टि भरें'
                        st.session_state[key] = current
                        st.selectbox(fname, opts or ['नई प्रविष्टि भरें'], index=(opts.index(display_current) if display_current in opts else 0), key=key)
                    elif ftype == 'number':
                        if key not in st.session_state:
                            st.session_state[key] = _arr_num(raw_employee_record.get(fid, 0))
                        if not raw_employee_record.get(fid, ''):
                            st.caption('नई प्रविष्टि भरें')
                        st.number_input(fname, min_value=0, step=1, key=key)
                    else:
                        st.text_input(fname, key=key, placeholder='नई प्रविष्टि भरें')

        # Re-read the working-copy values used by the arrear calculation.
        arr_bank = _arr_str(selected_emp.get('bank_name'))
        arr_acc = _arr_str(selected_emp.get('account'))
        arr_ifsc = _arr_str(selected_emp.get('ifsc'))
        for candidate, var_name in [('Bank Name','arr_bank'), ('Account Number','arr_acc'), ('IFSC','arr_ifsc')]:
            f = next((x for x in employee_fields if str(x.get('field_name','')).strip().casefold() == candidate.casefold()), None)
            if f:
                val = st.session_state.get(f'arr_master_{arr_suffix}_{f.get("field_id")}', '')
                if var_name == 'arr_bank': arr_bank = _arr_str(val)
                elif var_name == 'arr_acc': arr_acc = _arr_str(val)
                else: arr_ifsc = _arr_str(val)

        # Pay Commission changes are temporary until explicitly saved.
        master_comm = master_comm_value or inferred_comm or ''
        if master_comm and arr_comm != master_comm:
            if arr_comm == '6th Pay Commission':
                st.warning("⚠️ Employee Master में 7th Pay Commission दर्ज है, लेकिन आपने 6th Pay Commission चुना है। यह केवल अस्थायी परिवर्तन है। स्थायी परिवर्तन के लिए Pay Band, Grade Pay और मूल वेतन सही करके ‘Master Data में सुधार सेव करें’ दबाएँ।")
            elif arr_comm == '7th Pay Commission':
                st.warning("⚠️ Employee Master में 6th Pay Commission दर्ज है, लेकिन आपने 7th Pay Commission चुना है। यह केवल अस्थायी परिवर्तन है। स्थायी परिवर्तन के लिए Pay Level और मूल वेतन सही करके ‘Master Data में सुधार सेव करें’ दबाएँ।")
            if st.button('↩ Employee Master के अनुसार वापस करें', key=f'arr_cancel_master_{arr_suffix}'):
                st.session_state['arr_last_selected_emp_id'] = None
                st.rerun()

        def _arr_to_float(v):
            try: return float(str(v).replace(',', '').strip())
            except (TypeError, ValueError): return None

        def _arr_sixth_bounds(text):
            import re
            m = re.search(r'₹?\s*([0-9][0-9,]*)\s*[–-]\s*₹?\s*([0-9][0-9,]*)', str(text or ''))
            if not m: return None
            return float(m.group(1).replace(',', '')), float(m.group(2).replace(',', ''))

        def _arr_validate_6th(basic, band, gp):
            b = _arr_to_float(basic); g = _arr_to_float(gp)
            if not str(band).strip() or g is None:
                return False, '⚠️ 6th CPC के लिए Pay Band और Grade Pay दोनों दर्ज करना आवश्यक है।'
            rows = md_service.pay_structure('6th Pay Commission')
            band_rows = [r for r in rows if str(r.get('pay_band') or '').strip().casefold() == str(band or '').strip().casefold()]
            if not band_rows:
                return False, '⚠️ दर्ज किया गया Pay Band, 6th CPC Pay Commission Master में उपलब्ध नहीं है।'
            if not any(_arr_to_float(r.get('grade_pay')) == g for r in band_rows):
                return False, '⚠️ दर्ज किया गया Grade Pay, चयनित 6th CPC Pay Band के अनुरूप नहीं है।'
            bounds = _arr_sixth_bounds(band)
            if b is None or b <= 0:
                return False, '⚠️ मूल वेतन दर्ज करें।'
            if bounds:
                lower, upper = bounds
                pay_in_band = b - g
                if pay_in_band < lower or pay_in_band > upper:
                    return False, '⚠️ चेतावनी: आपका मूल वेतन छठे वेतन आयोग के Pay Band एवं Grade Pay के अनुरूप नहीं है। कृपया Pay Band, Grade Pay तथा मूल वेतन की जाँच करें।'
            return True, ''

        def _arr_validate_7th(basic, level):
            b = _arr_to_float(basic)
            if not str(level).strip(): return False, '⚠️ 7th CPC के लिए Pay Level दर्ज करना आवश्यक है।'
            rows = md_service.pay_structure('7th Pay Commission')
            target = next((r for r in rows if _arr_norm_level(r.get('pay_level')) == _arr_norm_level(level)), None)
            if not target: return False, '⚠️ दर्ज किया गया Pay Level, 7th CPC Pay Commission Master में उपलब्ध नहीं है।'
            cells = target.get('pay_matrix_cells') or []
            if isinstance(cells, str):
                import json
                try: cells = json.loads(cells)
                except Exception: cells = []
            nums = {_arr_to_float(x) for x in cells}
            if b is None or b <= 0: return False, '⚠️ मूल वेतन दर्ज करें।'
            if nums and b not in nums:
                return False, '⚠️ चेतावनी: आपका मूल वेतन चयनित 7th CPC Pay Level की Pay Matrix के अनुरूप नहीं है। कृपया Pay Level तथा मूल वेतन की जाँच करें।'
            return True, ''

        if arr_comm == '6th Pay Commission':
            basic_valid, basic_message = _arr_validate_6th(arr_cur_basic, arr_pay_band, arr_grade_pay)
        elif arr_comm == '7th Pay Commission':
            basic_valid, basic_message = _arr_validate_7th(arr_cur_basic, arr_pay_level)
        else:
            basic_valid = bool(_arr_to_float(arr_cur_basic) and _arr_to_float(arr_cur_basic) > 0)
            basic_message = '' if basic_valid else '⚠️ मूल वेतन दर्ज करें।'
        if not basic_valid:
            st.error(basic_message)
        else:
            st.success('✓ Pay Commission, Pay Structure और वर्तमान मूल वेतन का मिलान सही है।')

        st.warning("⚠️ चेतावनी: ‘Master Data में सुधार सेव करें’ का उपयोग केवल तब करें जब Employee Master की जानकारी वास्तव में गलत हो। सही जानकारी होने पर इस बटन का उपयोग न करें।")
        if st.button('✏️ Master Data में सुधार सेव करें', key=f'arr_save_master_{arr_suffix}', type='secondary'):
            try:
                if not basic_valid:
                    raise ValueError('Master Data सेव नहीं किया जा सकता क्योंकि Pay Commission, Pay Structure और मूल वेतन का मिलान सही नहीं है।')
                if not employee_master:
                    raise ValueError('Employee Master Data उपलब्ध नहीं है।')
                values = {}
                field_lookup = {str(f.get('field_name','')).strip().casefold(): f for f in employee_fields}
                def _fid(*names):
                    for name in names:
                        f = field_lookup.get(str(name).strip().casefold())
                        if f: return f.get('field_id')
                    return None
                core_mapping = {
                    _fid('Employee Name','कर्मचारी का नाम'): arr_emp_name.strip(),
                    _fid('Employee ID','Employee Code','कर्मचारी आईडी'): arr_emp_id.strip(),
                    _fid('Designation','पद'): arr_desig.strip(),
                    _fid('Basic Pay','मूल वेतन'): int(arr_cur_basic),
                    _fid('Pay Commission','वेतन आयोग','Pay Commission Name'): arr_comm,
                    _fid('Pay Level','पे लेवल'): arr_pay_level if arr_comm == '7th Pay Commission' else '',
                    _fid('Pay Band','Pay Band (6th CPC)','वेतन बैंड'): arr_pay_band if arr_comm == '6th Pay Commission' else '',
                    _fid('Grade Pay','ग्रेड Pay','ग्रेड पे'): arr_grade_pay if arr_comm == '6th Pay Commission' else '',
                }
                for fid, value in core_mapping.items():
                    if fid: values[fid] = value
                for field in employee_fields:
                    fid = str(field.get('field_id') or '').strip()
                    if not fid or fid in values: continue
                    key = f'arr_master_{arr_suffix}_{fid}'
                    if key in st.session_state:
                        _v = st.session_state[key]
                        values[fid] = '' if _v == 'नई प्रविष्टि भरें' else _v
                    elif fid in raw_employee_record:
                        values[fid] = raw_employee_record.get(fid, '')
                md_service.store.update_record(employee_master['master_id'], selected_emp_id, values)
                st.success('Employee Master Data में सुधार सफलतापूर्वक स्थायी रूप से अपडेट हो गया है।')
                st.rerun()
            except Exception as exc:
                st.error(f'Employee Master Data अपडेट नहीं हो सका: {exc}')
    else:
        arr_emp_name = ''
        arr_emp_id = ''
        arr_pan = ''
        arr_bank = ''
        arr_acc = ''
        arr_ifsc = ''
        arr_desig = ''
        arr_cur_basic = 0
        arr_comm = ''
        arr_pay_level = ''
        arr_pay_band = ''
        arr_grade_pay = ''

    # Existing period inputs remain in the arrear workflow.  Keep all three
    # controls in one equal-width row so the page never leaves a large blank
    # area on the left.
    period_row = st.columns(3)
    with period_row[0]:
        arr_start_dt = st.date_input(
            'एरियर प्रारंभ / वास्तविक प्रभावित (प्रभावी) दिनांक:',
            datetime(2025, 3, 15),
            key='w_arr_sdt'
        )
    with period_row[1]:
        arr_end_dt = st.date_input(
            'एरियर समाप्ति दिनांक (To):',
            datetime(2026, 6, 30),
            key='w_arr_edt'
        )
    with period_row[2]:
        city_cat = st.selectbox(
            'शहर श्रेणी (HRA हेतु):',
            ['Classified (जयपुर, जोधपुर आदि)', 'Other Places (अन्य स्थान)'],
            key='w_arr_city'
        )

    level_change_reason = any(x in arr_reason for x in ["Promotion", "ACP / MACP"])
    pay_fixation_reason = "Pay Fixation" in arr_reason
    old_level = new_level = None
    old_designation = ""
    new_designation = ""

    # Promotion/ACP-MACP: Pay Level may or may not change.
    # Pay Fixation: levels are shown, but the Due Basic remains manual because
    # fixation can arise from several different statutory circumstances.
    if level_change_reason or pay_fixation_reason:
        notice = (
            "प्रमोशन/ACP-MACP में Pay Level बदल सकता है — यदि Level बदलता है तो Promotion वाला नियम लागू होगा; यदि Level समान है तो उसी Level में केवल एक Increment दिया जाएगा।"
            if level_change_reason else
            "Pay Fixation में कोई automatic fixation rule लागू नहीं किया जाएगा; देय मूल वेतन डेटा एंट्री ऑपरेटर स्वयं दर्ज करेगा।"
        )
        st.markdown(
            f"<div style='padding:8px;border:1px solid #f39c12;border-radius:6px;color:#f4d03f;font-weight:bold;'>{notice}</div>",
            unsafe_allow_html=True
        )

        if "Promotion" in arr_reason:
            # Promotion: old post must always come from the selected Employee
            # Master record. New post is selected from the available post list.
            designation_options = []
            for d in list(DESIG_LIST or []):
                d = str(d).strip()
                if d and d not in designation_options:
                    designation_options.append(d)
            # Also include designations actually present in Employee Master so
            # locally configured posts are available without code changes.
            for e in employee_catalog:
                d = str(e.get('designation') or '').strip()
                if d and d not in designation_options:
                    designation_options.append(d)
            if arr_desig and arr_desig not in designation_options:
                designation_options.insert(0, arr_desig)

            d1, d2 = st.columns(2)
            with d1:
                # Master Data is the default/source value, but the working copy
                # must remain visible AND editable, just like the other employee
                # fields. Permanent correction happens only through the explicit
                # Master Data save button.
                old_desig_key = f"w_arr_old_desig_{arr_suffix}"
                st.session_state.setdefault(old_desig_key, arr_desig)
                old_designation = st.text_input(
                    "प्रमोशन से पहले का पद (Master Data से):",
                    key=old_desig_key,
                    placeholder="नई प्रविष्टि भरें"
                )
            with d2:
                current_new_desig = st.session_state.get(
                    f"w_arr_new_desig_{arr_suffix}",
                    arr_desig
                )
                if current_new_desig not in designation_options:
                    designation_options.insert(0, current_new_desig)
                new_designation = st.selectbox(
                    "प्रमोशन के बाद का पद (पद चुनें):",
                    designation_options or [arr_desig or "अन्य"],
                    index=(designation_options.index(current_new_desig) if current_new_desig in designation_options else 0),
                    key=f"w_arr_new_desig_{arr_suffix}"
                )

            # Pay structure depends on the employee's Pay Commission.
            if "6th" in arr_comm:
                sixth_rows = md_service.pay_structure('6th Pay Commission') or []
                band_options = []
                for row in sixth_rows:
                    band = _arr_str(row.get('pay_band')).strip()
                    if band and band not in band_options:
                        band_options.append(band)
                current_band = _arr_str(arr_pay_band or selected_emp.get('pay_band')).strip()
                if current_band and current_band not in band_options:
                    band_options.insert(0, current_band)
                if not band_options:
                    band_options = [current_band or '']
                band_idx = band_options.index(current_band) if current_band in band_options else 0
                gp_options = []
                for row in sixth_rows:
                    if _arr_str(row.get('pay_band')).strip() == current_band:
                        gp = _arr_str(row.get('grade_pay')).strip()
                        if gp and gp not in gp_options:
                            try: gp = str(int(float(gp)))
                            except Exception: pass
                            if gp not in gp_options: gp_options.append(gp)
                old_gp = _arr_str(arr_grade_pay or selected_emp.get('grade_pay')).strip()
                if old_gp and old_gp not in gp_options: gp_options.insert(0, old_gp)
                if not gp_options: gp_options = [old_gp or '']
                old_gp_idx = gp_options.index(old_gp) if old_gp in gp_options else 0
                new_grade_options = list(gp_options)
                current_new_gp = st.session_state.get(f"w_arr_new_gp_{arr_suffix}", old_gp)
                if current_new_gp not in new_grade_options: new_grade_options.insert(0, current_new_gp)
                ev1, ev2, ev3 = st.columns(3)
                with ev1:
                    working_band = st.selectbox(
                        "पूर्व Pay Band (6th CPC):", band_options, index=band_idx,
                        key=f"w_arr_event_band_{arr_suffix}"
                    )
                with ev2:
                    old_grade_pay = st.selectbox(
                        "प्रमोशन से पहले का Grade Pay (Master Data से):",
                        gp_options, index=old_gp_idx, key=f"w_arr_old_gp_{arr_suffix}"
                    )
                with ev3:
                    new_grade_pay = st.selectbox(
                        "प्रमोशन के बाद का Grade Pay (Grade Pay चुनें):",
                        new_grade_options,
                        index=(new_grade_options.index(current_new_gp) if current_new_gp in new_grade_options else 0),
                        key=f"w_arr_new_gp_{arr_suffix}"
                    )
                old_level = new_level = None
                arr_event_old_grade_pay = old_grade_pay
                arr_event_new_grade_pay = new_grade_pay
                arr_event_pay_band = working_band
            else:
                level_options = list(master_matrix.keys()) or [f"L-{k}" for k in range(1,25)]
                emp_level = _arr_norm_level(arr_pay_level or selected_emp.get('pay_level') or 'L-11')
                level_idx = level_options.index(emp_level) if emp_level in level_options else 0
                current_new_level = st.session_state.get(f"w_arr_new_level_{arr_suffix}", emp_level)
                if current_new_level not in level_options:
                    current_new_level = emp_level
                pl1, pl2 = st.columns(2)
                with pl1:
                    old_level = st.selectbox(
                        "प्रमोशन से पहले का Pay Level (Master Data से):",
                        level_options, index=level_idx, key=f"w_arr_old_level_{arr_suffix}"
                    )
                with pl2:
                    new_level = st.selectbox(
                        "प्रमोशन के बाद का Pay Level (Pay Level चुनें):",
                        level_options, index=level_options.index(current_new_level), key=f"w_arr_new_level_{arr_suffix}"
                    )
                arr_event_old_grade_pay = ''
                arr_event_new_grade_pay = ''
                arr_event_pay_band = ''
            arr_desig = new_designation
        elif "6th" in arr_comm:
            # ACP/MACP or Pay Fixation under 6th CPC: designation does not
            # change. Only Grade Pay may change for ACP/MACP.
            sixth_rows = md_service.pay_structure('6th Pay Commission') or []
            current_band = _arr_str(arr_pay_band or selected_emp.get('pay_band')).strip()
            gp_options = []
            for row in sixth_rows:
                if _arr_str(row.get('pay_band')).strip() == current_band:
                    gp = _arr_str(row.get('grade_pay')).strip()
                    if gp:
                        try: gp = str(int(float(gp)))
                        except Exception: pass
                        if gp not in gp_options: gp_options.append(gp)
            old_gp = _arr_str(arr_grade_pay or selected_emp.get('grade_pay')).strip()
            if old_gp and old_gp not in gp_options:
                gp_options.insert(0, old_gp)
            if not gp_options: gp_options = [old_gp or '']
            current_new_gp = st.session_state.get(f"w_arr_new_gp_{arr_suffix}", old_gp)
            if current_new_gp not in gp_options: gp_options.insert(0, current_new_gp)
            gp1, gp2 = st.columns(2)
            with gp1:
                old_grade_pay = st.selectbox(
                    "पूर्व Grade Pay (Master Data से):", gp_options,
                    index=(gp_options.index(old_gp) if old_gp in gp_options else 0),
                    key=f"w_arr_old_gp_{arr_suffix}"
                )
            with gp2:
                new_grade_pay = st.selectbox(
                    "पश्चात Grade Pay (Grade Pay चुनें):", gp_options,
                    index=(gp_options.index(current_new_gp) if current_new_gp in gp_options else 0),
                    key=f"w_arr_new_gp_{arr_suffix}"
                )
            old_level = new_level = None
            arr_event_old_grade_pay = old_grade_pay
            arr_event_new_grade_pay = new_grade_pay
            arr_event_pay_band = current_band
        else:
            # 7th CPC ACP/MACP: Pay Level can change. Pay Fixation does not
            # change the post, so no old/new designation selector is shown.
            pc1, pc2 = st.columns(2)
            with pc1:
                level_options = list(master_matrix.keys()) or [f"L-{k}" for k in range(1,25)]
                emp_level = _arr_norm_level(arr_pay_level or selected_emp.get('pay_level') or 'L-11')
                level_idx = level_options.index(emp_level) if emp_level in level_options else 0
                old_level = st.selectbox(
                    "पूर्व Pay Level (Master Data से):", level_options, index=level_idx, key=f"w_arr_old_level_{arr_suffix}"
                )
            with pc2:
                current_new_level = st.session_state.get(f"w_arr_new_level_{arr_suffix}", emp_level)
                if current_new_level not in level_options: current_new_level = emp_level
                new_level = st.selectbox(
                    "पश्चात Pay Level (Pay Level चुनें):", level_options,
                    index=level_options.index(current_new_level), key=f"w_arr_new_level_{arr_suffix}"
                )
            arr_event_old_grade_pay = ''
            arr_event_new_grade_pay = ''
            arr_event_pay_band = ''

    else:
        new_designation = arr_desig
        level_options=list(master_matrix.keys()) or [f"L-{k}" for k in range(1,25)]
        emp_level=_arr_norm_level(arr_pay_level or selected_emp.get('pay_level') or 'L-12')
        pay_lvl_input = st.selectbox("Pay Level (Pay Commission Master):", level_options, index=(level_options.index(emp_level) if emp_level in level_options else 0), key=f"w_arr_plvl_{arr_suffix}")
        old_level = new_level = pay_lvl_input

    acp_macp_tenure = None
    if "ACP / MACP" in arr_reason:
        acp_macp_tenure = st.selectbox(
            "ACP / MACP का चयन (सेवा अवधि):",
            ["9 वर्षीय", "18 वर्षीय", "27 वर्षीय"],
            index=0,
            key="w_arr_acp_macp_tenure"
        )

    city_type_val = "Classified" if "Classified" in city_cat else "Other"

    if "Promotion" in arr_reason:
        st.info(
            f"प्रमोशन विवरण: {old_designation} ({old_level}) से {new_designation} ({new_level}) में पदोन्नति हुई है। "
            "इसी पद/Pay Level परिवर्तन के कारण एरियर बनाया जाएगा और यह विवरण अंतिम PDF/Excel में प्रदर्शित होगा।"
        )

    if level_change_reason and old_level == new_level:
        st.info("ACP / MACP में Pay Level समान है — प्रारंभिक देय वेतन उसी Level की अगली Pay Matrix Cell से स्वतः निर्धारित होगा।")
    elif level_change_reason and old_level != new_level:
        st.info("Promotion/ACP-MACP में Pay Level बदला है — पहले पूर्व Level में एक Increment, फिर पश्चात Level में उससे अगली उच्च Cell पर Pay Fixation होगा।")

    st.markdown("<h5 style='color:#f39c12;margin-top:15px;margin-bottom:4px;'>४. मूल वेतन, Increment एवं मासिक कटौतियाँ</h5>", unsafe_allow_html=True)

    # Compact, aligned four-column grid: row 1 = drawn values, row 2 = due values.
    row1 = st.columns(4)
    with row1[0]:
        try: employee_basic_default=int(float(arr_cur_basic or selected_emp.get('basic_pay') or 65000))
        except (TypeError,ValueError): employee_basic_default=65000
        drawn_basic_def = st.number_input("प्रारंभिक आहरित मूल वेतन (Employee Master से, ₹):", min_value=0, value=employee_basic_default, step=100, key=f"w_arr_db_{arr_suffix}")
    with row1[1]:
        st.markdown("**GPF**")
        drawn_gpf_m = st.number_input("मासिक आहरित GPF (₹):", min_value=0, value=2850, step=50, key="w_arr_dgpf")
    with row1[2]:
        st.markdown("**SI**")
        drawn_si_m = st.number_input("मासिक आहरित SI (₹):", min_value=0, value=3000, step=500, key="w_arr_dsi")
    with row1[3]:
        st.markdown("**RGHS**")
        drawn_rghs_m = st.number_input("मासिक आहरित RGHS (₹):", min_value=0, value=get_rghs_deduction_for_basic(int(drawn_basic_def)), step=50, key="w_arr_drghs")

    auto_fixation_reason = level_change_reason
    auto_due_basic = get_initial_due_basic(
        reason=arr_reason, old_level=old_level, new_level=new_level,
        drawn_basic=int(drawn_basic_def), pay_matrix=PAY_MATRIX_7TH,
    )
    auto_due_state_key = f"{arr_reason}|{old_level}|{new_level}|{int(drawn_basic_def)}"
    if st.session_state.get("w_arr_dub_auto_state_key") != auto_due_state_key:
        st.session_state["w_arr_dub_auto"] = int(auto_due_basic)
        st.session_state["w_arr_dub_auto_state_key"] = auto_due_state_key

    row2 = st.columns(4)
    with row2[0]:
        if auto_fixation_reason:
            # Automatically calculated value is intentionally NOT editable, but
            # it must always be clearly visible to the operator.  A disabled
            # number_input can become low-contrast with the app theme, so render
            # the calculated value in a dedicated visible value box.
            due_basic_def = int(st.session_state.get("w_arr_dub_auto", auto_due_basic) or 0)
            st.markdown(
                f"<div style=\"margin-top:0.25rem;\"><div style=\"font-weight:700;color:#f39c12;margin-bottom:0.35rem;\">प्रारंभिक देय मूल वेतन (स्वतः Pay Fixation) ₹:</div>"
                f"<div style=\"min-height:38px;padding:9px 12px;border:1px solid #9ec5fe;border-radius:8px;background:#24476d;color:#ffffff;font-size:1.05rem;font-weight:700;\">₹ {due_basic_def:,.0f}</div></div>",
                unsafe_allow_html=True
            )
            st.caption("Promotion/ACP-MACP नियम से स्वतः निर्धारित — केवल प्रदर्शित, editable नहीं")
        else:
            due_basic_def = st.number_input("प्रारंभिक देय मूल वेतन (पश्चात Level) ₹:", min_value=0, value=67000, step=100, key="w_arr_dub_manual")
    with row2[1]:
        due_gpf_auto = get_gpf_minimum_for_basic(int(due_basic_def))
        gpf_due_display = st.number_input("मासिक देय GPF (slab minimum) ₹:", min_value=0, value=due_gpf_auto, step=50, key="w_arr_dugpf")
    with row2[2]:
        si_options = get_si_options_for_basic(int(due_basic_def))
        default_si = si_options[0] if 3000 not in si_options else 3000
        due_si_m = st.selectbox("मासिक देय SI (slab विकल्प):", si_options, index=si_options.index(default_si), key="w_arr_dusi")
    with row2[3]:
        due_rghs_m = st.number_input("मासिक देय RGHS (slab) ₹:", min_value=0, value=get_rghs_deduction_for_basic(int(due_basic_def)), step=50, key="w_arr_durghs")

    inc_c1, inc_c2 = st.columns(2)
    with inc_c1:
        inc_month_choice = st.selectbox("वार्षिक Increment माह:", ["लागू नहीं (None)", "जनवरी (January)", "जुलाई (July)"], index=2, key="w_arr_inc_m")
    with inc_c2:
        increment_received_old = st.radio("क्या पुराने वेतन/Pay Level में नियमित रूप से Increment लगा है?", ["हाँ", "नहीं"], horizontal=True, key="w_arr_inc_received")

    if increment_received_old == "नहीं" and inc_month_choice != "लागू नहीं (None)":
        inc_month_num = 1 if inc_month_choice.startswith("जनवरी") else 7
        candidate_dates = []
        for yy in range(arr_start_dt.year, arr_end_dt.year + 1):
            candidate = datetime(yy, inc_month_num, 1).date()
            if arr_start_dt <= candidate <= arr_end_dt:
                candidate_dates.append(candidate)
        missed_increment_dates = st.multiselect(
            "जिन-जिन वर्षों में पुराने वेतन/Level पर Increment नहीं मिला, वे तिथियाँ चुनें:",
            candidate_dates,
            format_func=lambda d: d.strftime("%d-%m-%Y"),
            key="w_arr_missed_incs"
        )
    else:
        missed_increment_dates = []

    t_c1, t_c2 = st.columns(2)
    with t_c1:
        income_tax_ded = st.number_input("मासिक आयकर (IT ₹):", min_value=0, value=1000, step=100, key="w_arr_it")
    with t_c2:
        other_ded = st.number_input("मासिक अन्य कटौती (Other ₹):", min_value=0, value=0, step=100, key="w_arr_oth")

    if st.button("➕ माह-वार रो-वाइज एरियर गणना करें और सूची में जोड़ें", key="btn_add_arr_emp"):
        if not arr_emp_name.strip():
            st.error("कृपया कर्मचारी का नाम दर्ज करें!")
        elif not arr_emp_id.strip():
            st.error("कृपया Employee ID दर्ज करें!")
        elif arr_start_dt > arr_end_dt:
            st.error("प्रारंभ/प्रभावी दिनांक समाप्ति दिनांक से बाद की नहीं हो सकती!")
        else:
            try:
                calc = calculate_arrear(
                    start_date=arr_start_dt,
                    end_date=arr_end_dt,
                    old_pay_level=old_level,
                    new_pay_level=new_level,
                    drawn_basic=int(drawn_basic_def),
                    due_basic=int(due_basic_def),
                    increment_month=None if inc_month_choice.startswith("लागू") else (1 if inc_month_choice.startswith("जनवरी") else 7),
                    increment_received_old=increment_received_old,
                    missed_increment_dates=missed_increment_dates,
                    pay_matrix=PAY_MATRIX_7TH,
                    city_type=city_type_val,
                    drawn_gpf=int(drawn_gpf_m),
                    drawn_si=int(drawn_si_m),
                    drawn_rghs=int(drawn_rghs_m),
                    income_tax=int(income_tax_ded),
                    other_deduction=int(other_ded),
                    due_si_option=int(due_si_m),
                    due_gpf_override=int(gpf_due_display),
                    due_rghs_override=int(due_rghs_m),
                    initial_due_fixation_applied=(level_change_reason or ("ACP / MACP" in arr_reason)),
                )
            except Exception as exc:
                st.error(f"एरियर calculation में त्रुटि: {exc}")
                st.stop()

            reconciliation = calc["reconciliation"]
            if not reconciliation["is_valid"]:
                st.error("Calculation reconciliation failed: displayed gross difference और component differences बराबर नहीं हैं।")
            else:
                totals = calc["totals"]
                st.session_state.arr_employees.append({
                    "emp_name": arr_emp_name.strip(), "employee_id": arr_emp_id.strip(), "designation": arr_desig,
                    "old_designation": old_designation if "Promotion" in arr_reason else arr_desig,
                    "new_designation": new_designation if "Promotion" in arr_reason else arr_desig,
                    "pay_level": new_level, "old_pay_level": old_level, "new_pay_level": new_level,
                    "pan": arr_pan.strip(), "bank": arr_bank, "account": arr_acc.strip(), "ifsc": arr_ifsc.strip(),
                    "start_date": arr_start_dt.strftime('%d/%m/%Y'), "end_date": arr_end_dt.strftime('%d/%m/%Y'),
                    "reason": arr_reason, "order_date": arr_order_date.strftime('%d/%m/%Y'),
                    "acp_macp_tenure": acp_macp_tenure,
                    "initial_due_basic": int(due_basic_def),
                    "automatic_fixation": bool(level_change_reason),
                    "monthly_rows": calc["monthly_rows"],
                    "total_diff_total": totals["diff_total"], "total_diff_gpf": totals["diff_gpf"], "total_diff_si": totals["diff_si"],
                    "total_diff_rghs": totals["diff_rghs"], "total_gpf_deposit": totals["gpf_deposit"], "total_it": totals["income_tax"],
                    "total_oth": totals["other_deduction"], "net_payable": totals["net_payable"],
                    "increment_received_old": increment_received_old,
                    "missed_increment_dates": [d.strftime('%d/%m/%Y') for d in missed_increment_dates],
                    "due_gpf": int(gpf_due_display), "due_si": int(due_si_m), "due_rghs": int(due_rghs_m),
                })
                cur_off = {"office_name": arr_office.strip(), "order_no": arr_order_no.strip(), "reason": arr_reason.strip(), "sub_treasury": arr_treasury.strip()}
                save_json_data(ARREAR_DATA_FILE, {"office_data": cur_off, "employees": st.session_state.arr_employees})
                # ============================================================
                # SUPABASE ARREAR SAVE — सामान्य User + Admin दोनों के लिए
                # local application login ही पर्याप्त है।
                # ============================================================
                try:
                    logged_username = str(st.session_state.get("logged_username") or "").strip().lower()
                    if not logged_username:
                        raise RuntimeError("Current logged-in username उपलब्ध नहीं है।")

                    result = save_module_data_for_local_user(
                        logged_username,
                        "arrear",
                        {
                            "office_data": cur_off,
                            "employees": st.session_state.arr_employees,
                        },
                    )

                    if result is None:
                        raise RuntimeError("Supabase module_data save ने कोई response नहीं दिया।")

                    st.success("✅ Arrear data Supabase में सफलतापूर्वक save/update हो गया।")

                except Exception as e:
                    st.error(
                        f"❌ Supabase Arrear Save Error: {type(e).__name__}: {e}"
                    )

                st.success(f"कार्मिक '{arr_emp_name}' का माह-वार एरियर सफलतापूर्वक गणना कर लिया गया है।")
                #st.rerun()

    if st.session_state.arr_employees:
        st.markdown("<hr style='border-color:#1b4f72;margin:12px 0;'>", unsafe_allow_html=True)
        st.markdown("<h5 style='color:#2ecc71;margin-bottom:4px;'>४. एरियर हेतु प्रविष्ट कार्मिकों की सूची</h5>", unsafe_allow_html=True)

        arr_tbl = """<table class="custom-table"><thead><tr><th>क्र.</th><th>कर्मचारी का नाम</th><th>पद</th><th>अवधि</th><th>माह</th><th>कुल अंतर योग (₹)</th><th>शुद्ध देय (₹)</th></tr></thead><tbody>"""
        for idx, item in enumerate(st.session_state.arr_employees, 1):
            arr_tbl += f"<tr><td>{idx}</td><td>{item.get('emp_name','')}</td><td>{item.get('designation','')}</td><td>{item.get('start_date','')} से {item.get('end_date','')}</td><td>{len(item.get('monthly_rows', []))}</td><td>{item.get('total_diff_total',0):,}</td><td>{item.get('net_payable',0):,}</td></tr>"
        arr_tbl += "</tbody></table>"
        st.markdown(arr_tbl, unsafe_allow_html=True)

        selected_emp_idx = st.selectbox(
            "एरियर शीट जनरेट हेतु कार्मिक चुनें:",
            range(len(st.session_state.arr_employees)),
            format_func=lambda x: f"{x+1}. {st.session_state.arr_employees[x].get('emp_name','')}",
            key="gen_sheet_sel"
        )

        # -----------------------------------------------------------------
        # कार्मिक सूची नियंत्रण — अन्य मॉड्यूल की तरह चयनित हटाएँ / पूरी
        # सूची खाली करें। Delete के बाद JSON file भी तुरंत update होगी।
        # -----------------------------------------------------------------
        ctrl1, ctrl2, ctrl3 = st.columns([1.3, 1.3, 2.4])
        with ctrl1:
            if st.button("🗑 चयनित कर्मचारी हटाएं", key="btn_del_arr_selected", use_container_width=True):
                removed = st.session_state.arr_employees.pop(selected_emp_idx)
                save_json_data(
                    ARREAR_DATA_FILE,
                    {"office_data": st.session_state.arr_office, "employees": st.session_state.arr_employees}
                )
                st.success(f"कार्मिक '{removed.get('emp_name','')}' को सूची से हटा दिया गया है।")
                st.rerun()
        with ctrl2:
            clear_confirm = st.checkbox("पूरी सूची खाली करने की पुष्टि", key="arr_clear_confirm")
            if st.button("🗑 पूरी सूची खाली करें", key="btn_clear_arr_all", use_container_width=True):
                if not clear_confirm:
                    st.warning("पूरी सूची हटाने के लिए पहले पुष्टि checkbox चुनें।")
                else:
                    st.session_state.arr_employees = []
                    save_json_data(
                        ARREAR_DATA_FILE,
                        {"office_data": st.session_state.arr_office, "employees": []}
                    )
                    st.success("एरियर की पूरी कर्मचारी सूची खाली कर दी गई है।")
                    st.rerun()
        with ctrl3:
            st.info("चयनित कर्मचारी हटाने से केवल चुनी हुई एंट्री हटेगी; 'पूरी सूची खाली करें' से सभी एंट्री हटेंगी।")

        emp = st.session_state.arr_employees[selected_emp_idx]
        rows = emp.get('monthly_rows', []) or []

        def money(v):
            try:
                return f"{int(round(float(v or 0))):,}"
            except Exception:
                return "0"

        def amount_words_hi(amount):
            """भारतीय संख्या-पद्धति में पूर्ण रुपये को शुद्ध हिंदी शब्दों में लिखें।"""
            try:
                n = int(round(float(amount or 0)))
            except Exception:
                n = 0
            if n == 0:
                return "शून्य रुपये मात्र"

            hindi_0_99 = [
                "", "एक", "दो", "तीन", "चार", "पाँच", "छह", "सात", "आठ", "नौ",
                "दस", "ग्यारह", "बारह", "तेरह", "चौदह", "पंद्रह", "सोलह", "सत्रह",
                "अठारह", "उन्नीस", "बीस", "इक्कीस", "बाईस", "तेईस", "चौबीस",
                "पच्चीस", "छब्बीस", "सत्ताईस", "अट्ठाईस", "उनतीस", "तीस", "इकतीस",
                "बत्तीस", "तैंतीस", "चौंतीस", "पैंतीस", "छत्तीस", "सैंतीस", "अड़तीस",
                "उनतालीस", "चालीस", "इकतालीस", "बयालीस", "तैंतालीस", "चवालीस",
                "पैंतालीस", "छियालीस", "सैंतालीस", "अड़तालीस", "उनचास", "पचास",
                "इक्यावन", "बावन", "तिरपन", "चौवन", "पचपन", "छप्पन", "सत्तावन",
                "अट्ठावन", "उनसठ", "साठ", "इकसठ", "बासठ", "तिरसठ", "चौंसठ",
                "पैंसठ", "छियासठ", "सड़सठ", "अड़सठ", "उनहत्तर", "सत्तर", "इकहत्तर",
                "बहत्तर", "तिहत्तर", "चौहत्तर", "पचहत्तर", "छिहत्तर", "सतहत्तर",
                "अठहत्तर", "उनासी", "अस्सी", "इक्यासी", "बयासी", "तिरासी", "चौरासी",
                "पचासी", "छियासी", "सत्तासी", "अट्ठासी", "नवासी", "नब्बे", "इक्यानबे",
                "बानबे", "तिरानबे", "चौरानबे", "पंचानबे", "छियानबे", "सत्तानबे",
                "अट्ठानबे", "निन्यानबे"
            ]

            def under_100(x):
                return hindi_0_99[int(x)] if int(x) else ""

            def under_1000(x):
                x = int(x)
                if x < 100:
                    return under_100(x)
                h, rem = divmod(x, 100)
                text = hindi_0_99[h] + " सौ"
                if rem:
                    text += " " + under_100(rem)
                return text

            parts = []
            crore, n = divmod(n, 10000000)
            lakh, n = divmod(n, 100000)
            thousand, n = divmod(n, 1000)

            if crore:
                parts.append(under_1000(crore) + " करोड़")
            if lakh:
                parts.append(under_1000(lakh) + " लाख")
            if thousand:
                parts.append(under_1000(thousand) + " हजार")
            if n:
                parts.append(under_1000(n))

            return " ".join(parts) + " रुपये मात्र"

        # 22 columns: serial, month/details, 12 income, 7 deductions, net.
        table_widths = ["3.2%", "8.8%"] + ["4.15%"] * 12 + ["4.9%"] * 7 + ["6.2%"]

        def row_html(r):
            days_in_month = r.get("days_in_month")
            if not days_in_month:
                # Backward compatibility for old saved records.
                days_in_month = r.get("worked_days", 0)
                text = str(r.get("month_year", ""))
                for num, name in enumerate([
                    "जनवरी", "फरवरी", "मार्च", "अप्रैल", "मई", "जून",
                    "जुलाई", "अगस्त", "सितम्बर", "अक्टूबर", "नवम्बर", "दिसम्बर"
                ], 1):
                    if name in text:
                        import re
                        ym = re.search(r"(20\d{2})", text)
                        if ym:
                            days_in_month = calendar.monthrange(int(ym.group(1)), num)[1]
                        break

            month_details = (
                f"{r.get('month_year','')}<br>"
                f"<span class='small'>DA {float(r.get('da_pct',0)):.0f}% | "
                f"HRA {float(r.get('hra_pct',0)):.0f}% | "
                f"{r.get('worked_days',0)}/{days_in_month} दिन</span>"
            )
            cells = [
                r.get("serial", ""), month_details,
                money(r.get('due_basic')), money(r.get('due_da')), money(r.get('due_hra')), money(r.get('due_gross')),
                money(r.get('drawn_basic')), money(r.get('drawn_da')), money(r.get('drawn_hra')), money(r.get('drawn_gross')),
                money(r.get('diff_basic')), money(r.get('diff_da')), money(r.get('diff_hra')), money(r.get('diff_total')),
                money(r.get('diff_gpf')), money(r.get('diff_rghs')), money(r.get('diff_si')), money(r.get('gpf_deposit')),
                money(r.get('income_tax')), money(r.get('other_ded')), money(r.get('deduction_total')), money(r.get('net_payable'))
            ]
            return "<tr>" + "".join(f"<td>{c}</td>" for c in cells) + "</tr>"

        sum_keys = [
            'drawn_basic','drawn_da','drawn_hra','drawn_gross','due_basic','due_da','due_hra','due_gross',
            'diff_basic','diff_da','diff_hra','diff_total','diff_gpf','diff_rghs','diff_si','gpf_deposit',
            'income_tax','other_ded','deduction_total','net_payable'
        ]
        total_row = {k: sum(float(r.get(k, 0) or 0) for r in rows) for k in sum_keys}
        total_row['month_year'] = 'कुल योग'

        def total_row_html(t):
            vals=[
                "", t["month_year"], money(t["due_basic"]), money(t["due_da"]), money(t["due_hra"]), money(t["due_gross"]),
                money(t["drawn_basic"]), money(t["drawn_da"]), money(t["drawn_hra"]), money(t["drawn_gross"]),
                money(t["diff_basic"]), money(t["diff_da"]), money(t["diff_hra"]), money(t["diff_total"]),
                money(t["diff_gpf"]), money(t["diff_rghs"]), money(t["diff_si"]), money(t["gpf_deposit"]),
                money(t["income_tax"]), money(t["other_ded"]), money(t["deduction_total"]), money(t["net_payable"])
            ]
            return "<tr class='total-row'>" + "".join(f"<td>{v}</td>" for v in vals) + "</tr>"

        def make_header():
            return """
            <thead>
              <tr class='group-row'>
                <th rowspan='3' class='serial-head'>क्र.<br>सं.</th>
                <th rowspan='3' class='month-head'>माह एवं वर्ष<br><span class='small white'>DA % | HRA % | दिन</span></th>
                <th colspan='12' class='income-head'>आय</th>
                <th colspan='7' class='deduction-head'>कटौतियाँ</th>
                <th rowspan='3' class='net-head'>शुद्ध देय राशि</th>
              </tr>
              <tr class='group-row'>
                <th colspan='4' class='due-head'>देय वेतन</th>
                <th colspan='4' class='drawn-head'>आहरित वेतन</th>
                <th colspan='4' class='diff-head'>अंतर</th>
                <th rowspan='2' class='deduction-head'>GPF अंतर</th>
                <th rowspan='2' class='deduction-head'>RGHS अंतर</th>
                <th rowspan='2' class='deduction-head'>SI अंतर</th>
                <th rowspan='2' class='deduction-head'>GPF में जमा DA एरियर</th>
                <th rowspan='2' class='deduction-head'>आयकर</th>
                <th rowspan='2' class='deduction-head'>अन्य कटौतियाँ</th>
                <th rowspan='2' class='deduction-head'>कटौतियों का कुल योग</th>
              </tr>
              <tr class='subhead'>
                <th>मूल वेतन</th><th>महंगाई भत्ता</th><th>मकान किराया भत्ता</th><th>कुल योग</th>
                <th>मूल वेतन</th><th>महंगाई भत्ता</th><th>मकान किराया भत्ता</th><th>कुल योग</th>
                <th>मूल वेतन का अंतर</th><th>महंगाई भत्ते का अंतर</th><th>मकान किराये का अंतर</th><th>कुल योग का अंतर</th>
              </tr>
            </thead>"""

        # -----------------------------------------------------------------
        # A4 LANDSCAPE PAGINATION
        # -----------------------------------------------------------------
        # The PDF is built as real, fixed-height A4-landscape page boxes.
        # Row capacities are deliberately conservative so no row can be
        # pushed underneath the footer/border.  The final page reserves
        # space for Total + Summary + Amount in Words + Certification.
        # -----------------------------------------------------------------
        FIRST_CAPACITY = 16
        MIDDLE_CAPACITY = 18
        LAST_CAPACITY = 10

        def pack_rows(all_rows):
            all_rows = list(all_rows or [])
            n = len(all_rows)
            if n == 0:
                return [[]]

            # One-page statement: leave enough room for summary and
            # certification instead of filling the table to the bottom.
            if n <= LAST_CAPACITY:
                return [all_rows]

            # Choose the smallest number of pages that can accommodate all
            # rows while respecting the special last-page capacity.
            page_count = 2
            while True:
                middle_slots = max(0, page_count - 2) * MIDDLE_CAPACITY
                if n <= FIRST_CAPACITY + middle_slots + LAST_CAPACITY:
                    break
                page_count += 1

            # Reserve the final page for the summary/certification and
            # distribute all remaining rows as evenly as possible across
            # the earlier pages. This avoids both an almost-empty middle page
            # and a one-row final page.
            last_n = min(LAST_CAPACITY, max(1, int(round(n / page_count))))
            earlier_n = n - last_n
            earlier_pages = page_count - 1

            # Start with an even distribution, then respect each page's
            # maximum capacity.
            base = earlier_n // earlier_pages
            extra = earlier_n % earlier_pages
            earlier_counts = [base + (1 if i < extra else 0) for i in range(earlier_pages)]

            # If rounding would exceed a page capacity, move the excess to
            # the next page(s). The chosen page_count guarantees that enough
            # total capacity exists.
            for i in range(len(earlier_counts)):
                cap = FIRST_CAPACITY if i == 0 else MIDDLE_CAPACITY
                if earlier_counts[i] > cap:
                    excess = earlier_counts[i] - cap
                    earlier_counts[i] = cap
                    j = i + 1
                    while excess and j < len(earlier_counts):
                        next_cap = MIDDLE_CAPACITY
                        room = next_cap - earlier_counts[j]
                        move = min(room, excess)
                        earlier_counts[j] += move
                        excess -= move
                        j += 1
                    if excess:
                        # Should be unreachable because page_count was
                        # selected from the total capacity calculation.
                        raise RuntimeError("PDF pagination capacity calculation failed")

            counts = earlier_counts + [last_n]
            pages = []
            pos = 0
            for count in counts:
                pages.append(all_rows[pos:pos + count])
                pos += count

            return pages

        pages = pack_rows(rows)
        developer = "सॉफ्टवेयर डेवलपर: आलोक कुमार सिंह, वरिष्ठ अध्यापक, राजकीय उच्च माध्यमिक विद्यालय, रोजड़ी | ईमेल: alokjobner@gmail.com"
        html_pages = []

        for pno, page_rows in enumerate(pages, 1):
            is_first = pno == 1
            is_last = pno == len(pages)
            body_rows = "".join(row_html(r) for r in page_rows)
            if is_last:
                body_rows += total_row_html(total_row)

            promotion_note = ""
            if "Promotion" in str(emp.get("reason", "")) or "प्रमोशन" in str(emp.get("reason", "")):
                promotion_note = (
                    f"<span class='promotion-note'><b>प्रमोशन विवरण:</b> कार्मिक का प्रमोशन "
                    f"{emp.get('old_designation','')} ({emp.get('old_pay_level','-')}) से "
                    f"{emp.get('new_designation', emp.get('designation',''))} ({emp.get('new_pay_level','-')}) में हुआ है। "
                    f"प्रमोशन के कारण Pay Level परिवर्तन होने से एरियर बनाया जा रहा है।</span>"
                )

            header_block = "" if not is_first else f"""
              <div class='header'>
                <div class='office-title'>{arr_office}</div>
                <div class='form-title'>अंतर विवरण प्रपत्र — वेतन एरियर</div>
                <div class='info-grid'>
                  <span><b>कर्मचारी का नाम:</b> {emp.get('emp_name','')}</span><span><b>एम्प्लॉय आईडी:</b> {emp.get('employee_id','—')}</span>
                  <span><b>पद:</b> {emp.get('designation','')}</span><span><b>PAN:</b> {emp.get('pan','')}</span>
                  <span><b>खाता संख्या:</b> {emp.get('account','')} ({emp.get('bank','')})</span><span><b>एरियर अवधि:</b> {emp.get('start_date','')} से {emp.get('end_date','')}</span>
                  <span><b>एरियर बनाने का कारण:</b> {emp.get('reason','')}</span><span><b>Pay Level:</b> {emp.get('old_pay_level','-')} → {emp.get('new_pay_level','-')}</span>
                  {promotion_note}
                </div>
              </div>"""

            summary_block = ""
            certification_block = ""
            if is_last:
                gross_payable = int(round(total_row.get('diff_total', 0)))
                gross_deduction = int(round(total_row.get('deduction_total', 0)))
                net_payable = int(round(total_row.get('net_payable', 0)))
                summary_block = f"""
                <div class='final-summary'>
                  <div class='summary-title'>सारांश</div>
                  <table class='summary-table'>
                    <tr><td>ग्रॉस देय राशि (Gross Payable)</td><td>₹ {money(gross_payable)}</td></tr>
                    <tr><td>ग्रॉस रिडक्शन / कुल कटौती (Gross Reduction / Gross Deduction)</td><td>₹ {money(gross_deduction)}</td></tr>
                    <tr class='net-summary'><td>शुद्ध देय राशि (Net Payable)</td><td>₹ {money(net_payable)}</td></tr>
                  </table>
                  <div class='amount-words'><b>शुद्ध देय राशि शब्दों में:</b> {amount_words_hi(net_payable)}</div>
                </div>"""
                certification_block = f"""
                <div class='cert'>
                  <b>प्रमाणीकरण:</b> प्रमाणित किया जाता है कि उपर्युक्त एरियर राशि का भुगतान पहले किसी अन्य बिल के साथ नहीं किया गया है। यदि भविष्य में यह पाया जाता है कि उक्त राशि का भुगतान पहले किसी अन्य बिल के साथ किया जा चुका है, तो उक्त राशि की रिकवरी मेरे वेतन से कर ली जाए।
                </div>
                <div class='signatures'>
                  <div>कर्मचारी के हस्ताक्षर<br><br>नाम: ____________________</div>
                  <div>लिपिक के हस्ताक्षर<br><br>नाम: ____________________</div>
                  <div>संस्था प्रधान के हस्ताक्षर<br><br>नाम/मुहर: ____________________</div>
                </div>
                <div class='copies'><b>प्रतिलिपि :- सूचनार्थ एवं आवश्यक कार्यवाही हेतु प्रेषित :-</b><br>
                1. श्रीमान उपकोषाधिकारी, {arr_treasury}।<br>
                2. संबंधित कर्मचारी — {emp.get('emp_name','')}, {emp.get('designation','')}।<br>
                3. रक्षित पत्रावली / कार्यालय प्रति।</div>
                """

            html_pages.append(f"""
            <section class='page-box {'first-page' if is_first else ''} {'last-page' if is_last else ''}'>
              {header_block}
              <div class='table-wrap'>
                <table class='main-table'>
                  <colgroup>{''.join(f'<col style="width:{w}">' for w in table_widths)}</colgroup>
                  {make_header()}
                  <tbody>{body_rows}</tbody>
                </table>
              </div>
              {summary_block}
              {certification_block}
              <div class='page-footer-row'>
                <span>पृष्ठ {pno} / {len(pages)}</span>
                <span>{developer}</span>
              </div>
            </section>""")

        arrear_html = f"""<!DOCTYPE html><html><head><meta charset='UTF-8'><title>Salary Arrear Statement</title>
        <style>
          @page {{ size: A4 landscape; margin: 7mm; }}
          * {{ box-sizing: border-box; }}
          html, body {{ margin:0; padding:0; width:100%; background:#fff; }}
          body {{ font-family:'Noto Sans Devanagari','Nirmala UI',Arial,sans-serif; color:#111; font-size:7pt; }}
          .page-box {{ width:100%; height:196mm; min-height:196mm; max-height:196mm; border:1.8px solid #111; padding:3.5mm 3.5mm 2.5mm; margin:0; display:flex; flex-direction:column; overflow:hidden; page-break-after:always; break-after:page; position:relative; }}
          .page-box:last-child {{ page-break-after:auto; break-after:auto; }}
          .header {{ flex:0 0 auto; margin-bottom:1.8mm; }}
          .office-title {{ text-align:center; font-size:13.5pt; font-weight:900; font-family:'Noto Serif Devanagari','Nirmala UI',serif; }}
          .form-title {{ text-align:center; font-size:9.5pt; font-weight:900; margin:.7mm 0 1.5mm; }}
          .info-grid {{ display:grid; grid-template-columns:1fr 1fr; border:1px solid #111; }}
          .info-grid span {{ padding:.9mm 1.3mm; border-right:1px solid #111; border-bottom:1px solid #111; min-height:5.4mm; }}
          .info-grid span:nth-child(2n) {{ border-right:0; }}
          .info-grid span:nth-last-child(-n+2) {{ border-bottom:0; }}
          .info-grid .promotion-note {{ grid-column:1 / -1; border-right:0; background:#eaf2f8; font-weight:800; }}
          .table-wrap {{ flex:1 1 auto; min-height:0; display:flex; width:100%; }}
          .main-table {{ width:100%; height:100%; border-collapse:collapse; table-layout:fixed; margin:0; }}
          .main-table th,.main-table td {{ border:1px solid #111; text-align:center; vertical-align:middle; padding:.72mm .32mm; line-height:1.0; overflow-wrap:anywhere; }}
          .main-table th {{ font-weight:900; font-size:5.9pt; }}
          .main-table td {{ font-size:6.0pt; }}
          .group-row th {{ color:#fff; font-size:6.6pt; }}
          .serial-head {{ background:#34495e; color:#fff; }}
          .month-head {{ background:#34495e; color:#fff; }}
          .income-head {{ background:#2471a3; }} .deduction-head {{ background:#884c3c; }} .drawn-head {{ background:#2874a6; }} .due-head {{ background:#7d3c98; }} .diff-head {{ background:#b9770e; }} .net-head {{ background:#1e8449; color:#fff; }}
          .subhead th {{ background:#eaf2f8; color:#111; font-size:5.75pt; }}
          .small {{ font-size:5.25pt; color:#555; }} .white {{ color:#fff; }}
          .total-row td {{ background:#f4f6f7; font-weight:900; }}
          .final-summary {{ flex:0 0 auto; margin-top:1.8mm; }}
          .summary-title {{ font-weight:900; font-size:8pt; margin-bottom:.8mm; text-align:left; }}
          .summary-table {{ width:100%; border-collapse:collapse; table-layout:fixed; }}
          .summary-table td {{ border:1px solid #111; padding:1.0mm 1.5mm; font-weight:800; }}
          .summary-table td:last-child {{ width:35%; text-align:right; }}
          .net-summary td {{ font-size:8pt; background:#e8f8f0; }}
          .amount-words {{ border:1px solid #111; border-top:0; padding:1.0mm 1.5mm; font-size:7pt; }}
          .cert {{ flex:0 0 auto; margin-top:1.8mm; font-size:6.7pt; line-height:1.25; border:1px solid #111; padding:1.5mm; text-align:justify; }}
          .signatures {{ flex:0 0 auto; display:flex; justify-content:space-between; margin-top:2.2mm; padding:0 4mm; font-weight:800; text-align:center; font-size:6.5pt; }}
          .signatures div {{ width:30%; padding-top:3.5mm; }}
          .copies {{ flex:0 0 auto; margin-top:1.5mm; line-height:1.25; font-size:6.5pt; }}
          .page-footer-row {{ flex:0 0 auto; display:flex; justify-content:space-between; align-items:center; border-top:1px solid #111; margin-top:1.5mm; padding-top:1mm; font-size:5.7pt; font-weight:700; }}
          @media screen {{ .page-box {{ margin-bottom:8mm; box-shadow:0 0 4px rgba(0,0,0,.15); }} }}
          @media print {{ html,body {{ width:100%; }} .page-box {{ margin:0; box-shadow:none; }} }}
        </style></head><body>{''.join(html_pages)}</body></html>"""

        # PDF and Excel actions stay on the same equal-width row, matching
        # the layout used by the other modules.
        export_row = st.columns(2)
        with export_row[0]:
            st.download_button(
                label=f"✨ '{emp.get('emp_name','')}' का पूर्ण माह-वार एरियर प्रपत्र (PDF/Print) डाउनलोड करें 🖨",
                data=arrear_html,
                file_name=f"Arrear_Statement_Final_{emp.get('emp_name','employee').replace(' ','_')}.html",
                mime="text/html",
                use_container_width=True,
                key="download_arrear_pdf_html",
            )

        with export_row[1]:
            try:
                excel_bytes = _build_arrear_excel_workbook(emp, st.session_state.arr_office or {})
                st.download_button(
                    label="📊 Salary Arrear Statement — PDF जैसा Formula Excel डाउनलोड करें",
                    data=excel_bytes,
                    file_name=f"Arrear_Statement_Formula_{emp.get('emp_name','employee').replace(' ','_')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                    key="download_arrear_formula_excel",
                )
            except Exception as exc:
                st.error(f"Excel workbook बनाने में त्रुटि: {type(exc).__name__}: {exc}")
