# -*- coding: utf-8 -*-
"""Extracted from the verified working app.py.
Only module organization was changed; extracted UI/business logic is preserved.
"""

def get_next_pay_step(level_str, current_basic):
    # Existing Annual Increment module helper; arrear calculation itself is
    # implemented only in arrear_calculation.py.
    matrix = PAY_MATRIX_7TH.get(level_str, [])
    current_basic = int(current_basic)
    if current_basic in matrix:
        idx = matrix.index(current_basic)
        return matrix[min(idx + 1, len(matrix) - 1)]
    for val in matrix:
        if val > current_basic:
            return val
    return matrix[-1] if matrix else current_basic

def get_calculated_next_pay(commission, level_str, current_basic):
    """Return the next pay amount using the selected Pay Commission Master rule."""
    if "6th" in str(commission):
        # 6th CPC annual increment: 3% of the existing basic/pay-band+grade-pay
        # aggregate, rounded to the next multiple of 10.
        basic=int(current_basic)
        return basic + ((basic * 3 + 99) // 1000) * 10
    if "7th" in str(commission):
        level_key = str(level_str).strip().upper().replace("–", "-").replace(" ", "")
        if level_key in {"FIXEDPAY", "FIXED-PAY"}:
            # Fixed Pay is not a 7th-CPC matrix level. Keep the current basic
            # as the automatic baseline; the operator may edit the future-pay
            # field when required by the applicable rule.
            return int(current_basic)
        if not level_key.startswith("L-") and level_key.startswith("L"):
            level_key = "L-" + level_key[1:]
        return get_next_pay_step(level_key, int(current_basic))
    return int(current_basic)

def _sync_increment_future_pay():
    """Synchronize Future Basic only for 7th CPC matrix levels.

    5th/6th CPC and 7th-CPC Fixed Pay remain manual for both current and
    future pay because their fixation rules have intentionally not yet been
    implemented.
    """
    try:
        # The increment module now keeps a separate working-copy key for each
        # selected employee, so changing commission/level/basic pay must update
        # that employee's future-pay field without affecting another employee.
        selected_id = st.session_state.get("inc_last_selected_emp_id")
        if selected_id:
            suffix = str(selected_id).replace("-", "_")
            commission = st.session_state.get(f"inc_comm_{suffix}", "7th Pay Commission")
            level = st.session_state.get(f"inc_level_{suffix}", "L-12")
            current = int(st.session_state.get(f"inc_basic_{suffix}", 65000))
            nb_key = f"inc_nb_{suffix}"
        else:
            commission = st.session_state.get("w_inc_comm", "7th Pay Commission")
            level = st.session_state.get("w_inc_lvl", "L-12")
            current = int(st.session_state.get("w_inc_cb", 65000))
            nb_key = "w_inc_nb"
        if "7th" in str(commission) and level != "Fixed Pay":
            st.session_state[nb_key] = get_calculated_next_pay(commission, level, current)
        elif "6th" in str(commission):
            st.session_state[nb_key] = get_calculated_next_pay(commission, level, current)
        elif "7th" not in str(commission):
            st.session_state[nb_key] = current
        elif level == "Fixed Pay":
            st.session_state[nb_key] = current
    except (TypeError, ValueError):
        pass


SIXTH_PAY_BANDS = {
    "PB-1 (₹5200–₹20200)": ["1700", "1750", "1900", "2000", "2400", "2800", "3600"],
    "PB-2 (₹9300–₹34800)": ["4200", "4800", "5400", "6000", "6600", "6800", "7200", "7600", "8200"],
    "PB-3 (₹15600–₹39100)": ["8700", "8900", "9500", "10000"],
    "PB-4 (₹37400–₹67000)": [],
}

def render(context):
    # Receive the existing app namespace; no second import of app.py is performed.
    globals().update({name: context[name] for name in ['DESIG_LIST', 'INC_DATA_FILE', 'PAY_MATRIX_7TH', '_show_module_cloud_status', 'datetime', 'load_json_data', 'save_json_data', 'st']})
    from master_data_service import MasterDataService
    md_service = MasterDataService(str(st.session_state.get('logged_username') or 'local_user'), ensure_system_master=True)
    employee_catalog = md_service.employee_catalog()
    employee_map = {str(e.get('_record_id')): e for e in employee_catalog}
    master_matrix = {}
    for row in md_service.pay_structure('7th Pay Commission'):
        level = str(row.get('pay_level') or '').strip()
        if level:
            try: master_matrix[level] = [int(x) for x in __import__('json').loads(row.get('pay_matrix_cells','[]'))]
            except Exception: master_matrix[level] = []
    if master_matrix:
        PAY_MATRIX_7TH = master_matrix
    master_6th = md_service.pay_structure('6th Pay Commission')
    _show_module_cloud_status("increment_order")
    if st.button("⬅ मुख्य डैशबोर्ड पर वापस जाएँ", key="back_dashboard_increment", use_container_width=False):
        st.query_params["page"] = "dashboard"
        st.rerun()

    if "inc_bundle_loaded" not in st.session_state:
        inc_bundle = load_json_data(INC_DATA_FILE)
        st.session_state.inc_office = inc_bundle.get("office_data", {})
        st.session_state.inc_employees = inc_bundle.get("employees", [])
        st.session_state.inc_bundle_loaded = True

    saved_inc_off = st.session_state.inc_office

    st.markdown("""
    <div class="main-header" style="padding: 12px; margin-bottom: 15px;">
        <h2 style="color: #f4d03f; margin:0; font-size: 22px;">सामयिक वार्षिक वेतन वृद्धि (Annual Increment) आदेश मॉड्यूल</h2>
        <p style="color: #aed6f1; margin:3px 0 0 0; font-size: 12px;">राजस्थान सेवा नियम (RSR) 7th, 6th & 5th CPC पे-मैट्रिक्स स्वतः गणना प्रणाली</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<h5 style='color:#f39c12; margin-bottom: 4px;'>१. कार्यालय एवं वेतन वृद्धि चक्र सामान्य विवरण</h5>", unsafe_allow_html=True)
    ic1, ic2, ic3 = st.columns(3)
    with ic1:
        inc_office = st.text_input("कार्यालय का नाम:", saved_inc_off.get("office_name", "प्रधानाचार्य, रा.उ.मा.वि. रोजड़ी (जयपुर)"), key="w_inc_off")
        inc_order_no = st.text_input("आदेश क्रमांक:", saved_inc_off.get("order_no", "संस्था/वेतनवृद्धि/2026/...."), key="w_inc_ord_no")
    with ic2:
        inc_year_val = saved_inc_off.get("inc_year", "2026")
        years_list = [str(y) for y in range(2035, 1999, -1)]
        y_idx = years_list.index(inc_year_val) if inc_year_val in years_list else 9
        inc_year_str = st.selectbox("वेतन वृद्धि वर्ष (2000-2035):", years_list, index=y_idx, key="w_inc_yr")
        inc_year = int(inc_year_str)
        inc_order_date = st.date_input("आदेश दिनांक:", datetime.now(), key="w_inc_odt")
    with ic3:
        cycle_def = saved_inc_off.get("inc_cycle", "जुलाई (01 July)")
        cycle_opts = ["जुलाई (01 July)", "जनवरी (01 January)"]
        c_idx = cycle_opts.index(cycle_def) if cycle_def in cycle_opts else 0
        inc_cycle = st.selectbox("वेतन वृद्धि चक्र (माह):", cycle_opts, index=c_idx, key="w_inc_cyc")
        inc_treasury = st.text_input("उपकोष कार्यालय:", saved_inc_off.get("sub_treasury", "सांभर लेक"), key="w_inc_tr")

    if "जुलाई" in inc_cycle:
        col6_title = f"30 जून {inc_year} को मूल वेतन"
        m_txt = "जुलाई"
        calc_cur_date = datetime(inc_year, 7, 1)
        calc_nxt_date = datetime(inc_year + 1, 7, 1)
    else:
        col6_title = f"31 दिसम्बर {inc_year - 1} को मूल वेतन"
        m_txt = "जनवरी"
        calc_cur_date = datetime(inc_year, 1, 1)
        calc_nxt_date = datetime(inc_year + 1, 1, 1)

    st.info(f"कॉलम 6 हेडर स्वतः सेट: **{col6_title}** | वेतन वृद्धि दिनांक: **{calc_cur_date.strftime('%d/%m/%Y')}** | आगामी दिनांक: **{calc_nxt_date.strftime('%d/%m/%Y')}**")

    st.markdown("<hr style='border-color: #1b4f72; margin: 12px 0;'>", unsafe_allow_html=True)
    st.markdown("<h5 style='color:#5dade2; margin-bottom: 4px;'>२. कर्मचारी विवरण एवं वेतन वृद्धि गणना</h5>", unsafe_allow_html=True)

    # ------------------------------------------------------------------
    # STEP 2: Employee Master selection.  General details above remain
    # unchanged.  Selecting an employee loads a temporary working copy.
    # ------------------------------------------------------------------
    if not employee_catalog:
        st.warning("Employee Master Data में कोई सक्रिय कर्मचारी उपलब्ध नहीं है। पहले Master Data → Employee Master Data अपडेट करें।")
        selected_emp_id = None
        selected_emp = {}
    else:
        employee_options = [str(e.get('_record_id')) for e in employee_catalog if str(e.get('_record_id', '')).strip()]
        selected_emp_id = st.selectbox(
            "कर्मचारी चुनें (Employee Master Data):",
            employee_options,
            index=None,
            placeholder="कृपया Employee Master से कर्मचारी चुनें...",
            format_func=lambda rid: f"{employee_map[rid].get('employee_name','')} — {employee_map[rid].get('employee_id','')}".strip(' —'),
            key="w_inc_emp_master"
        )
        selected_emp = employee_map.get(selected_emp_id, {}) if selected_emp_id else {}

    # ------------------------------------------------------------------
    # STEP 3: Employee details.  Employee Master is the source of truth;
    # edits here are temporary until the explicit Master Data save action.
    # ------------------------------------------------------------------
    st.markdown("<h5 style='color:#5dade2; margin: 14px 0 4px 0;'>३. कर्मचारी विवरण एवं वार्षिक वेतन वृद्धि गणना</h5>", unsafe_allow_html=True)

    inferred_comm = md_service.infer_employee_commission(selected_emp) if selected_emp else ""
    master_comm_value = str(selected_emp.get("pay_commission") or "").strip() if selected_emp else ""
    commission_options = [c for c in ["7th Pay Commission", "6th Pay Commission"] if md_service.pay_structure(c)]
    if not commission_options:
        commission_options = [inferred_comm or "7th Pay Commission"]

    emp_key_suffix = str(selected_emp_id or "none").replace("-", "_")

    def _num(v, default=0):
        try:
            return int(float(v))
        except (TypeError, ValueError):
            return default

    def _str(v):
        return "" if v is None else str(v)

    def _norm_level(v):
        raw = _str(v).strip().upper().replace("–", "-").replace(" ", "")
        if raw.startswith("L") and not raw.startswith("L-") and raw[1:].isdigit():
            raw = "L-" + raw[1:]
        return raw

    if selected_emp_id:
        # A new employee selection gets a fresh working copy from Master Data.
        if st.session_state.get("inc_last_selected_emp_id") != selected_emp_id:
            st.session_state["inc_last_selected_emp_id"] = selected_emp_id
            initial_comm = master_comm_value if master_comm_value in commission_options else (inferred_comm or commission_options[0])
            st.session_state[f"inc_name_{emp_key_suffix}"] = _str(selected_emp.get("employee_name"))
            st.session_state[f"inc_desig_{emp_key_suffix}"] = _str(selected_emp.get("designation"))
            st.session_state[f"inc_basic_{emp_key_suffix}"] = _num(selected_emp.get("basic_pay"))
            st.session_state[f"inc_comm_{emp_key_suffix}"] = initial_comm
            st.session_state[f"inc_status_{emp_key_suffix}"] = "स्थायी"
            st.session_state[f"inc_level_{emp_key_suffix}"] = _norm_level(selected_emp.get("pay_level"))
            st.session_state[f"inc_band_{emp_key_suffix}"] = _str(selected_emp.get("pay_band"))
            st.session_state[f"inc_gp_{emp_key_suffix}"] = _str(selected_emp.get("grade_pay"))
            st.session_state[f"inc_cur_dt_{emp_key_suffix}"] = calc_cur_date.date()
            st.session_state[f"inc_nxt_dt_{emp_key_suffix}"] = calc_nxt_date.date()
            st.session_state[f"inc_nb_{emp_key_suffix}"] = _num(selected_emp.get("basic_pay"))

        current_comm = st.session_state.get(f"inc_comm_{emp_key_suffix}", master_comm_value or inferred_comm or commission_options[0])
        if current_comm not in commission_options:
            current_comm = inferred_comm or commission_options[0]
            st.session_state[f"inc_comm_{emp_key_suffix}"] = current_comm

        # Pay Commission change is temporary.  Required structure fields are
        # exposed immediately so the user can correct the working copy.
        ec1, ec2, ec3 = st.columns(3)
        with ec1:
            inc_emp_name = st.text_input("नाम (Employee Master):", key=f"inc_name_{emp_key_suffix}")
            inc_cur_basic = st.number_input("वर्तमान मूल वेतन (₹):", min_value=0, max_value=500000, step=100, key=f"inc_basic_{emp_key_suffix}", on_change=_sync_increment_future_pay)
        with ec2:
            inc_desig = st.text_input("पद (Employee Master):", key=f"inc_desig_{emp_key_suffix}")
            inc_status = st.selectbox("स्थायी / अस्थायी:", ["स्थायी", "अस्थायी"], key=f"inc_status_{emp_key_suffix}")
        with ec3:
            inc_comm = st.selectbox(
                "वेतन आयोग (Employee Master):",
                commission_options,
                index=commission_options.index(current_comm),
                key=f"inc_comm_{emp_key_suffix}",
                on_change=_sync_increment_future_pay
            )

        master_comm = (master_comm_value if master_comm_value in commission_options else inferred_comm) or ""
        commission_changed = bool(master_comm and inc_comm != master_comm)
        if commission_changed:
            if inc_comm == "6th Pay Commission":
                st.warning("⚠️ Employee Master में 7th Pay Commission दर्ज है, लेकिन आपने 6th Pay Commission चुना है। यह केवल अस्थायी परिवर्तन है। यदि इसे स्थायी रूप से बदलना चाहते हैं तो Pay Band और Grade Pay सही दर्ज करके ‘Master Data में सुधार सेव करें’ दबाएँ।")
            elif inc_comm == "7th Pay Commission":
                st.warning("⚠️ Employee Master में 6th Pay Commission दर्ज है, लेकिन आपने 7th Pay Commission चुना है। यह केवल अस्थायी परिवर्तन है। यदि इसे स्थायी रूप से बदलना चाहते हैं तो Pay Level सही दर्ज करके ‘Master Data में सुधार सेव करें’ दबाएँ।")
            if st.button("↩ Employee Master के अनुसार वापस करें", key=f"inc_cancel_comm_{emp_key_suffix}"):
                st.session_state[f"inc_comm_{emp_key_suffix}"] = master_comm
                st.session_state[f"inc_level_{emp_key_suffix}"] = _norm_level(selected_emp.get("pay_level"))
                st.session_state[f"inc_band_{emp_key_suffix}"] = _str(selected_emp.get("pay_band"))
                st.session_state[f"inc_gp_{emp_key_suffix}"] = _str(selected_emp.get("grade_pay"))
                st.session_state[f"inc_basic_{emp_key_suffix}"] = _num(selected_emp.get("basic_pay"))
                st.rerun()

        if "7th" in inc_comm:
            level_options = ["Fixed Pay"] + [f"L-{k}" for k in range(1, 25)]
            level_default = _norm_level(selected_emp.get("pay_level")) or "Fixed Pay"
            level_current = st.session_state.get(f"inc_level_{emp_key_suffix}", level_default)
            if level_current not in level_options:
                level_current = "Fixed Pay"
            inc_level = st.selectbox(
                "Pay Level (7th CPC):", level_options,
                index=level_options.index(level_current),
                key=f"inc_level_{emp_key_suffix}",
                on_change=_sync_increment_future_pay
            )
            inc_running_band = ""
            inc_grade_pay = ""
            st.caption(f"Pay Matrix cells: {len(master_matrix.get(inc_level, [])) if inc_level != 'Fixed Pay' else 0}")
        elif "6th" in inc_comm:
            bands = []
            for row in master_6th:
                b = str(row.get("pay_band") or "")
                if b and b not in bands:
                    bands.append(b)
            emp_band = _str(selected_emp.get("pay_band"))
            band_current = st.session_state.get(f"inc_band_{emp_key_suffix}", emp_band)
            if band_current not in bands and band_current:
                bands = [band_current] + bands
            inc_running_band = st.selectbox(
                "Pay Band (6th CPC):", bands or [band_current],
                index=(bands.index(band_current) if band_current in bands else 0),
                key=f"inc_band_{emp_key_suffix}"
            )
            gps = []
            for row in master_6th:
                if str(row.get("pay_band") or "") == inc_running_band and str(row.get("grade_pay") or "") not in ("", "None"):
                    try:
                        gp = str(int(float(row.get("grade_pay"))))
                    except Exception:
                        gp = str(row.get("grade_pay"))
                    if gp not in gps:
                        gps.append(gp)
            emp_gp = _str(selected_emp.get("grade_pay"))
            gp_current = st.session_state.get(f"inc_gp_{emp_key_suffix}", emp_gp)
            if gp_current not in gps and gp_current:
                gps = [gp_current] + gps
            inc_grade_pay = st.selectbox(
                "Grade Pay (6th CPC):", gps or [gp_current],
                index=(gps.index(gp_current) if gp_current in gps else 0),
                key=f"inc_gp_{emp_key_suffix}"
            )
            inc_level = f"{inc_running_band} / GP {inc_grade_pay}"
        else:
            inc_running_band = ""
            inc_grade_pay = ""
            inc_level = "Manual"

        # Current and upcoming increment dates are module data, not Employee
        # Master fields. They remain editable in this working copy.
        dc1, dc2 = st.columns(2)
        with dc1:
            inc_cur_dt = st.date_input("वर्तमान वेतन वृद्धि दिनांक:", key=f"inc_cur_dt_{emp_key_suffix}")
        with dc2:
            inc_nxt_dt = st.date_input("आगामी वेतन वृद्धि दिनांक:", key=f"inc_nxt_dt_{emp_key_suffix}")

        # Keep future-pay calculation isolated per selected employee.
        is_7th_matrix = "7th" in inc_comm and inc_level != "Fixed Pay"
        is_6th_auto = "6th" in inc_comm
        if is_7th_matrix or is_6th_auto:
            calculated_next = get_calculated_next_pay(inc_comm, inc_level, int(inc_cur_basic))
            if f"inc_nb_{emp_key_suffix}" not in st.session_state or st.session_state.get("inc_nb_owner") != selected_emp_id:
                st.session_state[f"inc_nb_{emp_key_suffix}"] = calculated_next
                st.session_state["inc_nb_owner"] = selected_emp_id
        else:
            st.session_state.setdefault(f"inc_nb_{emp_key_suffix}", int(inc_cur_basic))
        inc_next_label = "भावी वेतन (स्वतः गणना ₹):" if is_7th_matrix else "भावी वेतन (Manual Entry ₹):"
        inc_next_basic = st.number_input(inc_next_label, min_value=1, max_value=500000, step=100, key=f"inc_nb_{emp_key_suffix}")

        # Same correction workflow as PL Surrender: validate first, then save
        # only when the user explicitly requests a permanent Master Data fix.
        def _to_float(v):
            try:
                return float(str(v).replace(",", "").strip())
            except (TypeError, ValueError):
                return None

        def _sixth_band_bounds(text):
            import re
            m = re.search(r"₹?\s*([0-9][0-9,]*)\s*[–-]\s*₹?\s*([0-9][0-9,]*)", str(text or ""))
            if not m:
                return None
            return float(m.group(1).replace(",", "")), float(m.group(2).replace(",", ""))

        def _validate_6th(basic, band, gp):
            b = _to_float(basic); g = _to_float(gp)
            if not str(band).strip() or g is None:
                return False, "⚠️ 6th CPC के लिए Pay Band और Grade Pay दोनों दर्ज करना आवश्यक है।"
            structures = md_service.pay_structure("6th Pay Commission")
            band_rows = [r for r in structures if str(r.get("pay_band") or "").strip().casefold() == str(band or "").strip().casefold()]
            if not band_rows:
                return False, "⚠️ दर्ज किया गया Pay Band, 6th CPC Pay Commission Master में उपलब्ध नहीं है।"
            if not any(_to_float(r.get("grade_pay")) == g for r in band_rows):
                return False, "⚠️ दर्ज किया गया Grade Pay, चयनित 6th CPC Pay Band के अनुरूप नहीं है।"
            bounds = _sixth_band_bounds(band)
            if b is None or b <= 0:
                return False, "⚠️ मूल वेतन दर्ज करें।"
            if bounds:
                lower, upper = bounds
                pay_in_band = b - g
                if pay_in_band < lower or pay_in_band > upper:
                    return False, "⚠️ चेतावनी: आपका मूल वेतन छठे वेतन आयोग के Pay Band एवं Grade Pay के अनुरूप नहीं है। कृपया Pay Band, Grade Pay तथा मूल वेतन की जाँच करें।"
            return True, ""

        def _validate_7th(basic, level):
            b = _to_float(basic)
            if not str(level).strip():
                return False, "7th CPC के लिए Pay Level दर्ज करना आवश्यक है।"
            rows = md_service.pay_structure("7th Pay Commission")
            target = next((r for r in rows if _norm_level(r.get("pay_level")) == _norm_level(level)), None)
            if not target:
                return False, "⚠️ दर्ज किया गया Pay Level, 7th CPC Pay Commission Master में उपलब्ध नहीं है।"
            cells = target.get("pay_matrix_cells") or []
            if isinstance(cells, str):
                import json
                try: cells = json.loads(cells)
                except Exception: cells = []
            nums = {_to_float(x) for x in cells}
            if b is None or b <= 0:
                return False, "⚠️ मूल वेतन दर्ज करें।"
            if nums and b not in nums:
                return False, "⚠️ चेतावनी: आपका मूल वेतन चयनित 7th CPC Pay Level की Pay Matrix के अनुरूप नहीं है। कृपया Pay Level तथा मूल वेतन की जाँच करें।"
            return True, ""

        if inc_comm == "6th Pay Commission":
            basic_valid, basic_message = _validate_6th(inc_cur_basic, inc_running_band, inc_grade_pay)
        elif inc_comm == "7th Pay Commission":
            basic_valid, basic_message = _validate_7th(inc_cur_basic, inc_level)
        else:
            basic_valid, basic_message = True, ""
        if not basic_valid:
            st.error(basic_message)
        else:
            st.success("✓ Pay Commission, Pay Structure और वर्तमान मूल वेतन का मिलान सही है।")

        st.warning("⚠️ चेतावनी: ‘Master Data में सुधार सेव करें’ का उपयोग केवल तब करें जब Employee Master की जानकारी वास्तव में गलत हो। सही जानकारी होने पर इस बटन का उपयोग न करें।")
        if st.button("✏️ Master Data में सुधार सेव करें", key=f"inc_save_master_{emp_key_suffix}", type="secondary"):
            try:
                if not basic_valid:
                    raise ValueError("Master Data सेव नहीं किया जा सकता क्योंकि Pay Commission, Pay Structure और मूल वेतन का मिलान सही नहीं है।")
                master = md_service.get_employee_master()
                if not master:
                    raise ValueError("Employee Master Data उपलब्ध नहीं है।")
                raw_record = md_service.get_record(master["master_id"], selected_emp_id)
                if not raw_record:
                    raise ValueError("चयनित Employee Master record नहीं मिला।")
                fields = {str(f.get("field_name", "")).strip().casefold(): f.get("field_id") for f in master.get("fields", [])}
                def fid(*names):
                    for n in names:
                        x = fields.get(str(n).strip().casefold())
                        if x:
                            return x
                    return None
                mapping = {
                    fid("Employee Name", "कर्मचारी का नाम"): inc_emp_name.strip(),
                    fid("Designation", "पद"): inc_desig.strip(),
                    fid("Basic Pay", "मूल वेतन"): int(inc_cur_basic),
                    fid("Pay Level", "पे लेवल"): inc_level if inc_comm == "7th Pay Commission" else "",
                    fid("Pay Band", "Pay Band (6th CPC)", "वेतन बैंड"): inc_running_band if inc_comm == "6th Pay Commission" else "",
                    fid("Grade Pay", "ग्रेड Pay", "ग्रेड पे"): inc_grade_pay if inc_comm == "6th Pay Commission" else "",
                    fid("Pay Commission", "वेतन आयोग", "Pay Commission Name"): inc_comm,
                }
                values = {k: v for k, v in mapping.items() if k}
                md_service.store.update_record(master["master_id"], selected_emp_id, values)
                st.success("Employee Master Data में सुधार सफलतापूर्वक स्थायी रूप से अपडेट हो गया है।")
                st.rerun()
            except Exception as exc:
                st.error(f"Employee Master Data अपडेट नहीं हो सका: {exc}")
    else:
        inc_emp_name = ""
        inc_desig = ""
        inc_cur_basic = 0
        inc_comm = ""
        inc_status = "स्थायी"
        inc_level = ""
        inc_running_band = ""
        inc_grade_pay = ""
        inc_cur_dt = calc_cur_date.date()
        inc_nxt_dt = calc_nxt_date.date()
        inc_next_basic = 0
        st.info("पहले STEP 2 में Employee Master से कर्मचारी चुनें। चयन के बाद STEP 3 में उसकी पूरी detail स्वतः आएगी।")

    with st.form("inc_add_form"):
        st.write("")
        submit_inc = st.form_submit_button("➕ कर्मचारी सूची में जोड़ें")
        if submit_inc:
            if not selected_emp_id or not inc_emp_name.strip():
                st.error("कृपया पहले STEP 2 में Employee Master से कर्मचारी चुनें!")
            elif inc_cur_basic <= 0:
                st.error("चयनित कर्मचारी का वर्तमान मूल वेतन उपलब्ध नहीं है।")
            elif not inc_comm:
                st.error("चयनित कर्मचारी का Pay Commission उपलब्ध नहीं है।")
            elif inc_next_basic <= inc_cur_basic:
                st.error("भावी वेतन वर्तमान मूल वेतन से अधिक होना चाहिए!")
            else:
                st.session_state.inc_employees.append({
                    "emp_name": inc_emp_name.strip(),
                    "employee_id": selected_emp.get("employee_id", ""),
                    "employee_master_record_id": selected_emp.get("_record_id", ""),
                    "designation": inc_desig,
                    "pay_commission": inc_comm,
                    "pay_band": inc_running_band,
                    "grade_pay": inc_grade_pay,
                    "service_status": inc_status,
                    "pay_level": (inc_level if "7th" in inc_comm else (f"{inc_running_band} / GP {inc_grade_pay}" if "6th" in inc_comm else "Manual")),
                    "current_basic": int(inc_cur_basic),
                    "cur_inc_date": inc_cur_dt.strftime("%d/%m/%Y"),
                    "next_basic": int(inc_next_basic),
                    "next_inc_date": inc_nxt_dt.strftime("%d/%m/%Y")
                })

                cur_off = {
                    "office_name": inc_office.strip(), "inc_year": str(inc_year),
                    "inc_cycle": inc_cycle.strip(), "order_no": inc_order_no.strip(),
                    "sub_treasury": inc_treasury.strip()
                }
                save_json_data(INC_DATA_FILE, {"office_data": cur_off, "employees": st.session_state.inc_employees})
                st.success(f"कार्मिक '{inc_emp_name}' सूची में जुड़ गया है!")
                st.rerun()

    if st.session_state.inc_employees:
        st.markdown("<hr style='border-color: #1b4f72; margin: 12px 0;'>", unsafe_allow_html=True)
        st.markdown("<h5 style='color:#2ecc71; margin-bottom: 4px;'>३. सामयिक वेतन वृद्धि आदेश में सम्मिलित कार्मिकों की सूची</h5>", unsafe_allow_html=True)

        inc_tbl_html = """<table class="custom-table">
        <thead><tr>
            <th>क्र.</th><th>अधिकारी/कार्मिक का नाम</th><th>पद</th><th>स्थिति</th><th>पे-लेवल</th>
            <th>वर्तमान वेतन (₹)</th><th>वृद्धि दिनांक</th><th>भावी वेतन (₹)</th><th>आगामी दिनांक</th>
        </tr></thead><tbody>"""
        for idx, emp in enumerate(st.session_state.inc_employees, 1):
            inc_tbl_html += f"""<tr>
                <td>{idx}</td><td style='text-align:left; font-weight:bold;'>{emp['emp_name']}</td>
                <td>{emp['designation']}</td><td>{emp['service_status']}</td><td>{emp['pay_level']}</td>
                <td style='text-align:right;'>{emp['current_basic']:,}</td><td>{emp['cur_inc_date']}</td>
                <td style='text-align:right; font-weight:bold; color:#2ecc71;'>{emp['next_basic']:,}</td><td>{emp['next_inc_date']}</td>
            </tr>"""
        inc_tbl_html += "</tbody></table>"
        st.markdown(inc_tbl_html, unsafe_allow_html=True)

        ib_col1, ib_col2 = st.columns(2)
        with ib_col1:
            del_inc_idx = st.selectbox("हटाने हेतु कार्मिक चुनें:", range(1, len(st.session_state.inc_employees) + 1), format_func=lambda x: f"{x}. {st.session_state.inc_employees[x-1]['emp_name']}", key="del_inc_sel")
            if st.button("🗑 चयनित कार्मिक हटाएं", key="btn_del_inc"):
                del st.session_state.inc_employees[del_inc_idx - 1]
                cur_off = {
                    "office_name": inc_office.strip(), "inc_year": str(inc_year),
                    "inc_cycle": inc_cycle.strip(), "order_no": inc_order_no.strip(),
                    "sub_treasury": inc_treasury.strip()
                }
                save_json_data(INC_DATA_FILE, {"office_data": cur_off, "employees": st.session_state.inc_employees})
                st.rerun()
        with ib_col2:
            st.write("")
            st.write("")
            if st.button("🔄 सूची खाली करें (New Order)", key="btn_clr_inc"):
                st.session_state.inc_employees = []
                cur_off = {
                    "office_name": inc_office.strip(), "inc_year": str(inc_year),
                    "inc_cycle": inc_cycle.strip(), "order_no": inc_order_no.strip(),
                    "sub_treasury": inc_treasury.strip()
                }
                save_json_data(INC_DATA_FILE, {"office_data": cur_off, "employees": []})
                st.rerun()

        inc_rows = ""
        for idx, item in enumerate(st.session_state.inc_employees, 1):
            inc_rows += f"""<tr>
              <td>{idx}</td><td style='text-align:left; padding-left:6px;'><b>{item['emp_name']}</b></td>
              <td>{item['designation']}</td><td>{item['service_status']}</td><td>{item['pay_level']}</td>
              <td>{item['current_basic']:,}</td><td>{item['cur_inc_date']}</td>
              <td><b>{item['next_basic']:,}</b></td><td>{item['next_inc_date']}</td>
            </tr>"""

        cert_text = (
            f"प्रमाणित किया जाता है कि उक्त कार्मिकों ने ऐसे किसी असाधारण अवकाश का उपभोग नहीं किया है, जिससे उनकी वेतन वृद्धि प्रभावित होती हो। "
            f"{m_txt} माह की प्रथम तारीख को कार्मिक के आकस्मिक अवकाश के अतिरिक्त अन्य अवकाश पर होने की स्थिति में "
            f"वेतन वृद्धि का आर्थिक लाभ वास्तविक कार्यग्रहण करने की तिथि से देय होगा।"
        )

        inc_html = f"""<!DOCTYPE html><html><head><meta charset='UTF-8'><title>Increment Order</title>
        <style>
          @page {{ size: A4 portrait; margin: 8mm 8mm 12mm 8mm; }}
          body {{ font-family: 'Noto Sans Devanagari', Arial, sans-serif; font-size: 10pt; color: #000; margin:0; padding:0; }}
          .page-box {{ border: 2px solid #000; padding: 14px 18px; min-height: calc(100vh - 22mm); }}
          .office-header {{ text-align: center; margin-bottom: 6mm; }}
          .office-title {{ font-size: 15pt; font-weight: bold; text-decoration: underline; margin-bottom: 4px; }}
          .order-title {{ font-size: 13pt; font-weight: bold; margin-bottom: 8px; }}
          .order-body {{ text-align: justify; text-indent: 30px; font-size: 10pt; line-height: 1.6; margin-bottom: 8px; }}
          table {{ width: 100%; border-collapse: collapse; margin: 6px 0 12mm 0; font-size: 9pt; }}
          th, td {{ border: 1px solid #000; padding: 4px 2px; text-align: center; }}
          th {{ background-color: #f2f2f2; font-weight: bold; }}
          .sub-th {{ font-size: 8pt; font-weight: normal; color: #444; }}
          .cert-text {{ font-size: 9.5pt; line-height: 1.5; margin: 8px 0 6px 0; text-align: justify; }}
          .sig-container {{ width: 100%; display: flex; justify-content: flex-end; margin-bottom: 10px; }}
          .sig-box {{ text-align: center; min-width: 230px; line-height: 1.35; }}
          .sig-space {{ height: 48px; }}
          .dispatch-section {{ border-top: 1px dashed #777; padding-top: 8px; margin-top: 6px; }}
          .dispatch-row {{ width: 100%; display: flex; justify-content: space-between; font-size: 10pt; font-weight: bold; margin-bottom: 6px; }}
          .copy-list {{ margin: 4px 0 10px 25px; padding: 0; font-size: 9.5pt; line-height: 1.5; }}
          .footer-outside {{ margin-top: 4px; font-size: 8pt; color: #333; display: flex; justify-content: space-between; }}
        </style></head><body>
        <div class='page-box'>
          <div class='office-header'><div class='office-title'>कार्यालय {inc_office}</div><div class='order-title'>-:: सामयिक वेतन वृद्धि आदेश ::-</div></div>
          <div class='order-body'>राज्य सरकार के वित्त विभाग के आदेश क्रमांक:- <b>F.15 (1) FD (Rules)/2017 Jaipur Dated 30 Oct. 2017</b> व द्वितीय संशोधन दिनांक <b>09-12-2017</b> के प्रावधानों के अनुसरण में निम्नलिखित कार्मिकों की एक वर्ष की संतोषजनक सेवा पूर्ण करने पर उनके नाम के सम्मुख कॉलम संख्या 7 में अंकित दिनांक से वार्षिक वेतन वृद्धि कॉलम संख्या 8 के अनुसार स्वीकृत की जाकर तदनुसार वेतन एवं भत्ते भुगतान किये जाने की स्वीकृति प्रदान की जाती है।</div>
          <table><thead><tr><th style='width:4%;'>क्र.सं.</th><th style='width:19%;'>नाम अधिकारी / कार्मिक</th><th style='width:15%;'>पद</th><th style='width:9%;'>स्थायी / अस्थायी</th><th style='width:9%;'>पद का वेतन लेवल</th><th style='width:12%;'>{col6_title}</th><th style='width:10%;'>वर्तमान वेतनवृद्धि की दिनांक</th><th style='width:11%;'>भावी वेतन (₹)</th><th style='width:11%;'>आगामी वेतनवृद्धि की दिनांक</th></tr>
          <tr class='sub-th'><th>1</th><th>2</th><th>3</th><th>4</th><th>5</th><th>6</th><th>7</th><th>8</th><th>9</th></tr></thead><tbody>{inc_rows}</tbody></table>
          <div class='cert-text'>{cert_text}</div>
          <div class='sig-container'><div class='sig-box'><div class='sig-space'></div><div style='font-weight:bold;'>हस्ताक्षर कार्यालय अध्यक्ष</div><div style='font-size:9pt;'>(मोहर सहित)</div></div></div>
          <div class='dispatch-section'><div class='dispatch-row'><div>क्रमांक: {inc_order_no}</div><div>दिनांक : {inc_order_date.strftime('%d/%m/%Y')}</div></div>
          <div style='font-weight:bold; font-size:9.5pt;'>प्रतिलिपि- सूचनार्थ एवं आवश्यक कार्यवाही हेतु प्रेषित:</div>
          <ol class='copy-list'><li>श्रीमान उपकोषाधिकारी {inc_treasury}।</li><li>लेखा शाखा / संस्थापन शाखा ।</li><li>व्यक्तिगत पंजिका (सम्बन्धित कार्मिक)।</li><li>रक्षित पत्रावली।</li></ol>
          <div class='sig-container' style='margin-bottom:0;'><div class='sig-box'><div class='sig-space'></div><div style='font-weight:bold;'>हस्ताक्षर कार्यालय अध्यक्ष</div><div style='font-size:9pt;'>(मोहर सहित)</div></div></div>
          </div>
        </div>
        <div class='footer-outside'><div>सॉफ्टवेयर डेवलपर: <b>आलोक कुमार सिंह, वरिष्ठ अध्यापक, राजकीय उच्च माध्यमिक विद्यालय, रोजड़ी, पंचायत समिति, सांभर लेक (जयपुर)</b> | ईमेल: <b>alokjobner@gmail.com</b></div><div>Office Order Generator</div></div>
        </body></html>"""

        st.download_button(
            label="✨ सामयिक वेतन वृद्धि आदेश जनरेट करें (PDF / Print Preview) 🖨",
            data=inc_html,
            file_name=f"Increment_Order_{inc_year}_{m_txt}.html",
            mime="text/html"
        )
