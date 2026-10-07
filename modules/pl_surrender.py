# -*- coding: utf-8 -*-
"""Extracted from the verified working app.py.
Only module organization was changed; extracted UI/business logic is preserved.
"""

def render(context):
    # Receive the existing app namespace; no second import of app.py is performed.
    globals().update({name: context[name] for name in ['DA_PRESETS', 'DESIG_LIST', 'PL_DATA_FILE', '_show_module_cloud_status', 'datetime', 'load_json_data', 'save_json_data', 'st']})
    from master_data_service import MasterDataService
    md_service = MasterDataService(str(st.session_state.get('logged_username') or 'local_user'), ensure_system_master=True)
    employee_catalog = md_service.employee_catalog()
    employee_map = {str(e.get('_record_id')): e for e in employee_catalog}
    _show_module_cloud_status("pl_surrender")
    if st.button("⬅ मुख्य डैशबोर्ड पर वापस जाएँ", key="back_dashboard_pl", use_container_width=False):
        st.query_params["page"] = "dashboard"
        st.rerun()

    if "pl_bundle_loaded" not in st.session_state:
        pl_bundle = load_json_data(PL_DATA_FILE)
        st.session_state.pl_office = pl_bundle.get("office_data", {})
        st.session_state.pl_employees = pl_bundle.get("employees", [])
        st.session_state.pl_bundle_loaded = True

    saved_pl_off = st.session_state.pl_office

    st.markdown("""
    <div class="main-header" style="padding: 12px; margin-bottom: 15px;">
        <h2 style="color: #f4d03f; margin:0; font-size: 22px;">उपार्जित अवकाश समर्पण (PL Surrender) आदेश मॉड्यूल</h2>
        <p style="color: #aed6f1; margin:3px 0 0 0; font-size: 12px;">कार्यालय आदेश संपादन, स्वतः गणना एवं PDF जनरेटर प्रणाली</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<h5 style='color:#f39c12; margin-bottom: 4px;'>१. कार्यालय एवं आदेश सामान्य विवरण</h5>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        pl_office = st.text_input("कार्यालय का नाम:", saved_pl_off.get("office_name", "प्रधानाचार्य, रा.उ.मा.वि. रोजड़ी (जयपुर)"), key="w_pl_off")
        pl_order_no = st.text_input("आदेश क्रमांक:", saved_pl_off.get("order_no", "संस्था/लेखा/2026/...."), key="w_pl_ord_no")
    with c2:
        fin_years = [f"{y}-{str(y+1)[2:]}" for y in range(2035, 1999, -1)]
        fy_def = saved_pl_off.get("fin_year", "2026-27")
        fy_idx = fin_years.index(fy_def) if fy_def in fin_years else 9
        pl_fin_year = st.selectbox("वित्तीय वर्ष:", fin_years, index=fy_idx, key="w_pl_fy")
        pl_order_date = st.date_input("आदेश दिनांक:", datetime.now(), key="w_pl_odt")
    with c3:
        months = ["जनवरी", "फरवरी", "मार्च", "अप्रैल", "मई", "जून", "जुलाई", "अगस्त", "सितम्बर", "अक्टूबर", "नवम्बर", "दिसम्बर"]
        m_def = saved_pl_off.get("pay_month_name", "सितम्बर")
        m_idx = months.index(m_def) if m_def in months else 8
        pl_month = st.selectbox("भुगतान माह:", months, index=m_idx, key="w_pl_m")
        pl_treasury = st.text_input("उपकोष कार्यालय:", saved_pl_off.get("sub_treasury", "सांभर लेक"), key="w_pl_tr")

    st.markdown("<hr style='border-color: #1b4f72; margin: 12px 0;'>", unsafe_allow_html=True)
    # ------------------------------------------------------------------
    # STEP 2: Employee selection comes FIRST. STEP 3 is the editable
    # autofilled employee detail. The selected master record remains the
    # single source of truth, and corrections made here are written back
    # to Employee Master.
    # ------------------------------------------------------------------
    st.markdown("<h5 style='color:#f1c40f; margin-bottom: 4px;'>२. Masters → Employee Master से कर्मचारी चयन</h5>", unsafe_allow_html=True)
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
            key="w_pl_emp_master"
        )
        selected_emp = employee_map.get(selected_emp_id, {}) if selected_emp_id else {}

    # Section 1 already contains Financial Year + Payment Month.  Do not
    # create a second FY selector here; Section 3 uses the same values.
    pl_calc_fin_year = pl_fin_year

    # ------------------------------------------------------------------
    # STEP 3: Autofill. Values remain visible on the dark application theme
    # and are editable so a verified correction can be written back to the
    # Employee Master. Commission is derived from the employee's 7th-CPC
    # level or 6th-CPC band/grade-pay fields.
    # ------------------------------------------------------------------
    st.markdown("<h5 style='color:#5dade2; margin: 14px 0 4px 0;'>३. कर्मचारी प्रविष्टि विवरण — Employee Master से AutoFill</h5>", unsafe_allow_html=True)

    inferred_comm = md_service.infer_employee_commission(selected_emp) if selected_emp else ""
    # Employee Master now stores an explicit Pay Commission field. Use that
    # value first; infer from Pay Level / Pay Band only for legacy records.
    master_comm_value = str(selected_emp.get("pay_commission") or "").strip() if selected_emp else ""
    commission_options = ["7th Pay Commission", "6th Pay Commission"]

    # Keep temporary edits in widget/session state only.  Employee Master is
    # changed only by the explicit "Master Data में सुधार सेव करें" action.
    emp_key_suffix = str(selected_emp_id or "none").replace("-", "_")
    if selected_emp_id:
        def _num(v, default=0):
            try: return int(float(v))
            except (TypeError, ValueError): return default
        def _str(v):
            return "" if v is None else str(v)
        def _norm_level(v):
            raw = _str(v).strip().upper().replace("–", "-").replace(" ", "")
            if raw.startswith("L") and not raw.startswith("L-") and raw[1:].isdigit():
                raw = "L-" + raw[1:]
            return raw

        if st.session_state.get("pl_last_selected_emp_id") != selected_emp_id:
            st.session_state["pl_last_selected_emp_id"] = selected_emp_id
            st.session_state[f"pl_name_{emp_key_suffix}"] = _str(selected_emp.get("employee_name"))
            st.session_state[f"pl_desig_{emp_key_suffix}"] = _str(selected_emp.get("designation"))
            st.session_state[f"pl_basic_{emp_key_suffix}"] = _num(selected_emp.get("basic_pay"))
            st.session_state[f"pl_comm_{emp_key_suffix}"] = (master_comm_value if master_comm_value in commission_options else inferred_comm) or commission_options[0]
            st.session_state[f"pl_level_{emp_key_suffix}"] = _norm_level(selected_emp.get("pay_level"))
            st.session_state[f"pl_band_{emp_key_suffix}"] = _str(selected_emp.get("pay_band"))
            st.session_state[f"pl_gp_{emp_key_suffix}"] = _str(selected_emp.get("grade_pay"))

    if selected_emp_id:
        ec1, ec2, ec3 = st.columns(3)
        with ec1:
            pl_emp_name = st.text_input("कर्मचारी का नाम (Employee Master):", key=f"pl_name_{emp_key_suffix}")
            pl_app_date = st.date_input("आवेदन दिनांक:", datetime.now(), key=f"w_pl_app_dt_{emp_key_suffix}")
        with ec2:
            pl_desig = st.text_input("पद (Employee Master):", key=f"pl_desig_{emp_key_suffix}")
            pl_basic = st.number_input("मूल वेतन (₹):", min_value=0, max_value=500000, step=100, key=f"pl_basic_{emp_key_suffix}")
        with ec3:
            current_comm = st.session_state.get(f"pl_comm_{emp_key_suffix}", inferred_comm or commission_options[0])
            if current_comm not in commission_options:
                current_comm = inferred_comm or commission_options[0]
            pl_comm = st.selectbox("वेतन आयोग:", commission_options, index=commission_options.index(current_comm), key=f"pl_comm_{emp_key_suffix}")

        master_comm = (master_comm_value if master_comm_value in commission_options else inferred_comm) or ""
        commission_changed = bool(master_comm and pl_comm != master_comm)
        if commission_changed:
            if pl_comm == "6th Pay Commission":
                st.warning("⚠️ Employee Master में 7th Pay Commission दर्ज है, लेकिन आपने 6th Pay Commission चुना है। यह केवल अस्थायी परिवर्तन है। यदि इसे स्थायी रूप से बदलना चाहते हैं तो कृपया Pay Band और Grade Pay दर्ज करें और ‘Master Data में सुधार सेव करें’ बटन दबाएँ।")
            else:
                st.warning("⚠️ Employee Master में 6th Pay Commission दर्ज है, लेकिन आपने 7th Pay Commission चुना है। यह केवल अस्थायी परिवर्तन है। यदि इसे स्थायी रूप से बदलना चाहते हैं तो कृपया Pay Level दर्ज करें और ‘Master Data में सुधार सेव करें’ बटन दबाएँ।")
            if st.button("↩ Employee Master के अनुसार वापस करें", key=f"pl_cancel_comm_{emp_key_suffix}"):
                st.session_state[f"pl_comm_{emp_key_suffix}"] = master_comm
                st.session_state[f"pl_level_{emp_key_suffix}"] = _str(selected_emp.get("pay_level"))
                st.session_state[f"pl_band_{emp_key_suffix}"] = _str(selected_emp.get("pay_band"))
                st.session_state[f"pl_gp_{emp_key_suffix}"] = _str(selected_emp.get("grade_pay"))
                st.session_state[f"pl_basic_{emp_key_suffix}"] = _num(selected_emp.get("basic_pay"))
                st.rerun()

        if pl_comm == "7th Pay Commission":
            p1, p2 = st.columns(2)
            with p1:
                pl_level = st.text_input("Pay Level (7th CPC):", key=f"pl_level_{emp_key_suffix}", placeholder="जैसे L-12")
            with p2:
                st.text_input("Pay Band / Grade Pay (6th CPC):", value="लागू नहीं — 7th CPC", disabled=True, key=f"pl_legacy_{emp_key_suffix}")
            pl_level = _norm_level(pl_level)
            pl_band = ""
            pl_gp = ""
        else:
            p1, p2 = st.columns(2)
            with p1:
                pl_band = st.text_input("Pay Band (6th CPC):", key=f"pl_band_{emp_key_suffix}")
            with p2:
                pl_gp = st.text_input("Grade Pay (6th CPC):", key=f"pl_gp_{emp_key_suffix}")
            pl_level = ""

        # ---------- Pay Commission / Basic Pay validation ----------
        def _to_float(v):
            try: return float(str(v).replace(",", "").strip())
            except (TypeError, ValueError): return None

        def _sixth_band_bounds(text):
            """Read PB-1/PB-2 etc. range from the universal Pay Commission Master."""
            import re
            m = re.search(r"₹?\s*([0-9][0-9,]*)\s*[–-]\s*₹?\s*([0-9][0-9,]*)", str(text or ""))
            if not m:
                return None
            return float(m.group(1).replace(",", "")), float(m.group(2).replace(",", ""))

        def _validate_6th(basic, band, gp):
            b = _to_float(basic); g = _to_float(gp)
            if not str(band).strip() or g is None:
                return False, "छठे वेतन आयोग के लिए Pay Band और Grade Pay दोनों दर्ज करना आवश्यक है।"
            structures = md_service.pay_structure("6th Pay Commission")
            band_rows = [r for r in structures if md_service._norm(r.get("pay_band")) == md_service._norm(band)]
            if not band_rows:
                # Also allow the exact stored band text to be selected/typed.
                band_rows = [r for r in structures if str(r.get("pay_band") or "").strip().casefold() == str(band or "").strip().casefold()]
            if not band_rows:
                return False, "⚠️ दर्ज किया गया Pay Band, 6th CPC Pay Commission Master में उपलब्ध नहीं है।"
            gp_ok = any(_to_float(r.get("grade_pay")) == g for r in band_rows)
            if not gp_ok:
                return False, "⚠️ दर्ज किया गया Grade Pay, चयनित 6th CPC Pay Band के अनुरूप नहीं है। कृपया Pay Band और Grade Pay की जाँच करें।"
            bounds = _sixth_band_bounds(band)
            if b is None or b <= 0:
                return False, "⚠️ मूल वेतन दर्ज करें।"
            if bounds:
                lower, upper = bounds
                pay_in_band = b - g
                if pay_in_band < lower or pay_in_band > upper:
                    return False, "⚠️ चेतावनी: आपका मूल वेतन छठे वेतन आयोग के Pay Band एवं Grade Pay के अनुरूप नहीं है। कृपया Pay Band, Grade Pay तथा मूल वेतन की जाँच करें। यदि मूल वेतन में भी परिवर्तन आवश्यक है तो पहले उसे सही करें।"
            return True, ""

        def _validate_7th(basic, level):
            b = _to_float(basic)
            if not str(level).strip():
                return False, "7th CPC के लिए Pay Level दर्ज करना आवश्यक है।"
            rows = md_service.pay_structure("7th Pay Commission")
            target = None
            for r in rows:
                if _norm_level(r.get("pay_level")) == _norm_level(level):
                    target = r; break
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
                return False, "⚠️ चेतावनी: आपका मूल वेतन चयनित 7th CPC Pay Level की Pay Matrix के अनुरूप नहीं है। कृपया Pay Level तथा मूल वेतन की जाँच करें। यदि मूल वेतन में भी परिवर्तन आवश्यक है तो पहले उसे सही करें।"
            return True, ""

        if pl_comm == "6th Pay Commission":
            basic_valid, basic_message = _validate_6th(pl_basic, pl_band, pl_gp)
        else:
            basic_valid, basic_message = _validate_7th(pl_basic, pl_level)
        if not basic_valid:
            st.error(basic_message)
        else:
            st.success("✓ Pay Commission, Pay Structure और मूल वेतन का मिलान सही है।")

        # DA is resolved from Pay Commission Master using the selected FY +
        # payment month, not the order/application date.
        def _month_date_from_fy(fy_text, month_name):
            y1 = int(str(fy_text).split("-")[0])
            month_map = {"जनवरी":1,"फरवरी":2,"मार्च":3,"अप्रैल":4,"मई":5,"जून":6,
                         "जुलाई":7,"अगस्त":8,"सितम्बर":9,"अक्टूबर":10,"नवम्बर":11,"दिसम्बर":12}
            mm = month_map.get(str(month_name), 9)
            year = y1 if mm >= 4 else y1 + 1
            return f"{year:04d}-{mm:02d}-01"

        da_calc_date = _month_date_from_fy(pl_calc_fin_year, pl_month)
        da_rows = md_service.da_rates(pl_comm)
        dated_da = []
        undated_da = []
        for r in da_rows:
            try:
                rate = float(r.get("da_rate"))
            except (TypeError, ValueError):
                continue
            eff = str(r.get("effective_date") or "")[:10]
            if len(eff) == 10:
                if eff <= da_calc_date:
                    dated_da.append((eff, rate, r))
            else:
                undated_da.append((rate, r))
        dated_da.sort(key=lambda x: x[0])
        if dated_da:
            da_effective_date = dated_da[-1][0]
            pl_da_value = dated_da[-1][1]
            da_source_row = dated_da[-1][2]
        else:
            # Never guess a historical DA rate from an undated legacy option.
            # The user must enter an effective date/rate and explicitly save it.
            pl_da_value = None
            da_effective_date = da_calc_date
            da_source_row = {}

        da_col1, da_col2 = st.columns(2)
        with da_col1:
            pl_da_effective = st.date_input(
                "DA प्रभावी दिनांक (Pay Commission Master):",
                datetime.strptime(da_effective_date, "%Y-%m-%d").date() if da_effective_date else datetime.now().date(),
                key=f"pl_da_eff_{emp_key_suffix}"
            )
        with da_col2:
            pl_da_edit = st.number_input(
                "महंगाई भत्ता (DA % — Master से):",
                min_value=0.0, max_value=1000.0, step=1.0,
                value=float(pl_da_value or 0), format="%.2f",
                key=f"pl_da_edit_{emp_key_suffix}"
            )

        if pl_da_value is not None:
            st.success(f"इस वित्तीय वर्ष/भुगतान माह के लिए लागू DA: **{pl_da_edit:g}%** (प्रभावी {pl_da_effective.strftime('%d/%m/%Y')})")
        else:
            st.warning("चयनित Pay Commission के लिए इस वित्तीय वर्ष/माह की DA दर Master में उपलब्ध नहीं है। कृपया DA प्रभावी दिनांक और दर दर्ज करके Master में सेव करें।")
        if undated_da and not dated_da:
            st.warning("⚠️ इस Pay Commission के Master में DA की कुछ पुरानी entries बिना प्रभावी दिनांक के हैं। इसलिए उन्हें किसी FY/माह पर स्वतः लागू नहीं किया गया है। सही प्रभावी दिनांक और DA % दर्ज करके ही Master में सेव करें।")

        st.warning("⚠️ चेतावनी: इस विकल्प का उपयोग तभी करें जब वास्तव में संबंधित Pay Commission के DA प्रतिशत में परिवर्तन हुआ हो। गलत DA प्रतिशत दर्ज करने पर भविष्य की गणनाएँ प्रभावित हो सकती हैं।")
        if st.button("💾 DA प्रतिशत/प्रभावी दिनांक Pay Commission Master में स्थायी सेव करें", key=f"pl_save_da_{emp_key_suffix}", type="secondary"):
            try:
                md_service.update_da_rate(
                    pl_comm, pl_da_effective.isoformat(), float(pl_da_edit),
                    cash_da_rate=float(pl_da_edit)
                )
                st.success(f"{pl_comm} की DA दर {pl_da_edit:g}% और प्रभावी दिनांक {pl_da_effective.strftime('%d/%m/%Y')} Pay Commission Master में स्थायी रूप से सेव हो गई है।")
                st.rerun()
            except Exception as exc:
                st.error(f"DA Master अपडेट नहीं हो सका: {exc}")

        pl_da_value = float(pl_da_edit)

        # Explicit save-back button: corrections are persisted only when the
        # user intentionally clicks this button.
        st.warning("⚠️ चेतावनी: ‘Master Data में सुधार सेव करें’ का उपयोग केवल तब करें जब Employee Master की जानकारी वास्तव में गलत हो। सही जानकारी होने पर इस बटन का उपयोग न करें।")
        if st.button("✏️ Master Data में सुधार सेव करें", key=f"pl_save_master_{emp_key_suffix}", type="secondary"):
            try:
                if not basic_valid:
                    raise ValueError("Master Data सेव नहीं किया जा सकता क्योंकि Pay Commission, Pay Structure और मूल वेतन का मिलान सही नहीं है। पहले ऊपर दी गई चेतावनी के अनुसार जानकारी सही करें।")
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
                        if x: return x
                    return None
                values = {}
                mapping = {
                    fid("Employee Name", "कर्मचारी का नाम"): pl_emp_name.strip(),
                    fid("Designation", "पद"): pl_desig.strip(),
                    fid("Basic Pay", "मूल वेतन"): int(pl_basic),
                    fid("Pay Level", "पे लेवल"): pl_level,
                    fid("Pay Band", "Pay Band (6th CPC)", "वेतन बैंड"): pl_band,
                    fid("Grade Pay", "ग्रेड Pay", "ग्रेड पे"): pl_gp,
                    fid("Pay Commission", "वेतन आयोग", "Pay Commission Name"): pl_comm,
                }
                for k, v in mapping.items():
                    if k: values[k] = v
                md_service.store.update_record(master["master_id"], selected_emp_id, values)
                st.success("Employee Master Data में सुधार सफलतापूर्वक अपडेट हो गया है।")
                st.rerun()
            except Exception as exc:
                st.error(f"Master Data अपडेट नहीं हो सका: {exc}")
    else:
        pl_emp_name = ""
        pl_desig = ""
        pl_basic = 0
        pl_comm = ""
        pl_level = ""
        pl_band = ""
        pl_gp = ""
        pl_da_value = None
        pl_app_date = datetime.now().date()
        st.info("पहले ऊपर STEP 2 में Employee Master से कर्मचारी चुनें। चयन के बाद STEP 3 में उसकी पूरी detail स्वतः आएगी।")

    col_pl1, col_pl2 = st.columns(2)
    with col_pl1:
        pl_total = st.number_input("कुल उपार्जित अवकाश:", min_value=0, max_value=300, value=265, step=1, key="w_pl_tot")
    with col_pl2:
        pl_surr = st.selectbox("समर्पित दिन:", [15, 14, 13, 12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1], key="w_pl_surr")

    pl_da = "" if pl_da_value is None else (f"{int(pl_da_value)}%" if float(pl_da_value).is_integer() else f"{pl_da_value:g}%")

    with st.form("pl_add_form"):
        submit_pl = st.form_submit_button("➕ कर्मचारी सूची में जोड़ें")
        if submit_pl:
            if not selected_emp_id or not pl_emp_name.strip():
                st.error("कृपया पहले STEP 2 में Employee Master से कर्मचारी चुनें!")
            elif pl_basic <= 0:
                st.error("चयनित कर्मचारी का मूल वेतन उपलब्ध नहीं है।")
            elif not pl_comm:
                st.error("चयनित कर्मचारी का Pay Commission उपलब्ध नहीं है।")
            elif pl_da_value is None:
                st.error("चयनित Pay Commission की DA दर Pay Commission Master में उपलब्ध नहीं है।")
            elif pl_surr > pl_total:
                st.error("समर्पित अवकाश कुल अवकाश से अधिक नहीं हो सकता!")
            else:
                da_rate = float(pl_da_value)
                bal = pl_total - pl_surr
                b_share = round((pl_basic / 30.0) * pl_surr)
                d_share = round(((pl_basic * da_rate / 100.0) / 30.0) * pl_surr)
                tot_pay = b_share + d_share
                st.session_state.pl_employees.append({
                    "emp_name": pl_emp_name.strip(),
                    "employee_id": selected_emp.get("employee_id", ""),
                    "employee_master_record_id": selected_emp.get("_record_id", ""),
                    "designation": pl_desig.strip(),
                    "pay_commission": pl_comm,
                    "pay_level": pl_level,
                    "pay_band": pl_band,
                    "grade_pay": pl_gp,
                    "app_date": pl_app_date.strftime("%d/%m/%Y"),
                    "fin_year": pl_calc_fin_year,
                    "pay_month": pl_month,
                    "da_rate": float(pl_da_value),
                    "da_effective_date": pl_da_effective.strftime("%d/%m/%Y"),
                    "basic_pay": int(pl_basic),
                    "total_pl": int(pl_total),
                    "surrender_pl": int(pl_surr),
                    "balance_pl": int(bal),
                    "basic_share": b_share,
                    "da_share": d_share,
                    "total_payable": tot_pay
                })
                cur_off = {
                    "office_name": pl_office.strip(), "fin_year": pl_calc_fin_year.strip(),
                    "pay_month_name": pl_month.strip(), "order_no": pl_order_no.strip(),
                    "sub_treasury": pl_treasury.strip()
                }
                save_json_data(PL_DATA_FILE, {"office_data": cur_off, "employees": st.session_state.pl_employees})
                st.success(f"कार्मिक '{pl_emp_name}' तालिका में जुड़ गया है!")
                st.rerun()

    if st.session_state.pl_employees:
        st.markdown("<hr style='border-color: #1b4f72; margin: 12px 0;'>", unsafe_allow_html=True)
        st.markdown("<h5 style='color:#2ecc71; margin-bottom: 4px;'>४. आदेश में सम्मिलित कार्मिकों की तालिका</h5>", unsafe_allow_html=True)

        tbl_html = """<table class="custom-table">
        <thead><tr>
            <th>क्र.</th><th>कार्मिक का नाम</th><th>पद</th><th>आवेदन दिनांक</th><th>मूल वेतन (₹)</th>
            <th>कुल PL</th><th>समर्पण</th><th>शेष PL</th><th>मूल वेतन अंश (₹)</th><th>DA अंश (₹)</th><th>कुल योग (₹)</th>
        </tr></thead><tbody>"""
        for idx, emp in enumerate(st.session_state.pl_employees, 1):
            tbl_html += f"""<tr>
                <td>{idx}</td><td style='text-align:left; font-weight:bold;'>{emp['emp_name']}</td>
                <td>{emp['designation']}</td><td>{emp['app_date']}</td><td style='text-align:right;'>{emp['basic_pay']:,}</td>
                <td>{emp['total_pl']}</td><td>{emp['surrender_pl']}</td><td style='font-weight:bold;'>{emp['balance_pl']}</td>
                <td style='text-align:right;'>{emp['basic_share']:,}</td><td style='text-align:right;'>{emp['da_share']:,}</td>
                <td style='text-align:right; font-weight:bold; color:#2ecc71;'>{emp['total_payable']:,}</td>
            </tr>"""
        tbl_html += "</tbody></table>"
        st.markdown(tbl_html, unsafe_allow_html=True)

        b_col1, b_col2 = st.columns(2)
        with b_col1:
            del_idx = st.selectbox("हटाने हेतु कार्मिक चुनें:", range(1, len(st.session_state.pl_employees) + 1), format_func=lambda x: f"{x}. {st.session_state.pl_employees[x-1]['emp_name']}", key="del_pl_sel")
            if st.button("🗑 चयनित कार्मिक हटाएं", key="btn_del_pl"):
                del st.session_state.pl_employees[del_idx - 1]
                cur_off = {
                    "office_name": pl_office.strip(), "fin_year": pl_calc_fin_year.strip(),
                    "pay_month_name": pl_month.strip(), "order_no": pl_order_no.strip(),
                    "sub_treasury": pl_treasury.strip()
                }
                save_json_data(PL_DATA_FILE, {"office_data": cur_off, "employees": st.session_state.pl_employees})
                st.rerun()
        with b_col2:
            st.write("")
            st.write("")
            if st.button("🔄 सूची खाली करें (New Order)", key="btn_clr_pl"):
                st.session_state.pl_employees = []
                cur_off = {
                    "office_name": pl_office.strip(), "fin_year": pl_calc_fin_year.strip(),
                    "pay_month_name": pl_month.strip(), "order_no": pl_order_no.strip(),
                    "sub_treasury": pl_treasury.strip()
                }
                save_json_data(PL_DATA_FILE, {"office_data": cur_off, "employees": []})
                st.rerun()

        t_rows = ""
        for idx, item in enumerate(st.session_state.pl_employees, 1):
            t_rows += f"""<tr>
              <td>{idx}</td><td style='text-align:left; padding-left:6px;'><b>{item['emp_name']}</b></td>
              <td>{item['designation']}</td><td>{item['app_date']}</td><td>{item['basic_pay']:,}</td>
              <td>{item['total_pl']}</td><td>{item['surrender_pl']}</td><td><b>{item['balance_pl']}</b></td>
              <td>{item['basic_share']:,}</td><td>{item['da_share']:,}</td><td><b>{item['total_payable']:,}</b></td>
            </tr>"""

        plural_text = "निम्न अधिकारियों / कर्मचारियों" if len(st.session_state.pl_employees) > 1 else "निम्न अधिकारी / कर्मचारी"
        cert_plural = "उक्त कार्मिकों ने" if len(st.session_state.pl_employees) > 1 else "उक्त कार्मिक ने"
        record_plural = "कार्मिकों की सेवा पुस्तिका" if len(st.session_state.pl_employees) > 1 else "कार्मिक की सेवा पुस्तिका"

        pl_html = f"""<!DOCTYPE html><html><head><meta charset='UTF-8'><title>PL Surrender Order</title>
        <style>
          @page {{ size: A4 portrait; margin: 8mm 8mm 12mm 8mm; }}
          body {{ font-family: 'Noto Sans Devanagari', Arial, sans-serif; font-size: 10.5pt; color: #000; margin:0; padding:0; }}
          .page-box {{ border: 2px solid #000; padding: 14px 18px; min-height: calc(100vh - 22mm); }}
          .office-header {{ text-align: center; margin-bottom: 6mm; }}
          .office-title {{ font-size: 15pt; font-weight: bold; text-decoration: underline; margin-bottom: 4px; }}
          .order-title {{ font-size: 13pt; font-weight: bold; margin-bottom: 10px; }}
          .order-body {{ text-align: justify; text-indent: 35px; font-size: 10.5pt; line-height: 1.65; margin-bottom: 10px; }}
          table {{ width: 100%; border-collapse: collapse; margin: 6px 0 12mm 0; font-size: 9pt; }}
          th, td {{ border: 1px solid #000; padding: 4px 2px; text-align: center; }}
          th {{ background-color: #f2f2f2; font-weight: bold; }}
          .cert-text {{ font-size: 10pt; line-height: 1.55; margin: 10px 0 8px 0; text-align: justify; }}
          .sig-container {{ width: 100%; display: flex; justify-content: flex-end; margin-bottom: 10px; }}
          .sig-box {{ text-align: center; min-width: 230px; line-height: 1.35; }}
          .sig-space {{ height: 48px; }}
          .dispatch-section {{ border-top: 1px dashed #777; padding-top: 8mm; margin-top: 6mm; }}
          .dispatch-row {{ width: 100%; display: flex; justify-content: space-between; font-size: 10pt; font-weight: bold; margin-bottom: 6px; }}
          .copy-list {{ margin: 4px 0 10px 25px; padding: 0; font-size: 9.5pt; line-height: 1.55; }}
          .footer-outside {{ margin-top: 4px; font-size: 8pt; color: #333; display: flex; justify-content: space-between; }}
        </style></head><body>
        <div class='page-box'>
          <div class='office-header'><div class='office-title'>कार्यालय {pl_office}</div><div class='order-title'>कार्यालय आदेश</div></div>
          <div class='order-body'>वित्त विभाग, राजस्थान सरकार के आदेश क्रमांक : <b>F 1(12) FD / Rules / 2008</b> जयपुर, दिनांक <b>06-02-2009</b> के अनुसार {plural_text} को उनके आवेदन किये जाने पर वित्तीय वर्ष <b>{pl_fin_year}</b> हेतु माह <b>{pl_month}</b> का निम्नानुसार उपार्जित अवकाश के नकद भुगतान किये जाने की स्वीकृति प्रदान की जाती है।</div>
          <table><thead><tr><th rowspan='2'>क्र.सं.</th><th rowspan='2'>नाम कर्मचारी</th><th rowspan='2'>पद</th><th rowspan='2'>आवेदन दिनांक</th><th rowspan='2'>मूल वेतन (₹)</th><th colspan='3'>समर्पित अवकाश विवरण</th><th colspan='3'>भुगतान योग्य राशि (₹)</th></tr>
          <tr><th>कुल</th><th>समर्पण</th><th>शेष</th><th>मूल वेतन</th><th>महंगाई भत्ता</th><th>योग</th></tr></thead><tbody>{t_rows}</tbody></table>
          <div class='cert-text'><b>प्रमाणित किया जाता है</b> कि ब्लॉक वर्ष <b>{pl_fin_year}</b> में {cert_plural} उपार्जित अवकाश के नकद भुगतान का लाभ पूर्व में प्राप्त नहीं किया है तथा उपरोक्तानुसार {record_plural} / अवकाश लेखे में समर्पित अवकाश का इन्द्राज कर दिया गया है।</div>
          <div class='sig-container'><div class='sig-box'><div class='sig-space'></div><div style='font-weight:bold;'>हस्ताक्षर कार्यालय अध्यक्ष</div><div style='font-size:9pt;'>(मोहर सहित)</div></div></div>
          <div class='dispatch-section'><div class='dispatch-row'><div>क्रमांक: {pl_order_no}</div><div>दिनांक : {pl_order_date.strftime('%d/%m/%Y')}</div></div>
          <div style='font-weight:bold; font-size:9.5pt;'>प्रतिलिपि- सूचनार्थ एवं आवश्यक कार्यवाही हेतु प्रेषित:</div>
          <ol class='copy-list'><li>उपकोष कार्यालय {pl_treasury}।</li><li>लेखा शाखा ।</li><li>व्यक्तिगत पंजिका (संबंधित कार्मिक)।</li><li>रक्षित पत्रावली।</li></ol>
          <div class='sig-container' style='margin-bottom:0;'><div class='sig-box'><div class='sig-space'></div><div style='font-weight:bold;'>हस्ताक्षर कार्यालय अध्यक्ष</div><div style='font-size:9pt;'>(मोहर सहित)</div></div></div>
          </div>
        </div>
        <div class='footer-outside'><div>सॉफ्टवेयर डेवलपर: <b>आलोक कुमार सिंह, वरिष्ठ अध्यापक, रा.उ.मा.वि. रोजड़ी, सांभर लेक</b> | ईमेल: <b>alokjobner@gmail.com</b></div><div>Office Order Generator</div></div>
        </body></html>"""

        st.download_button(
            label="✨ आदेश जनरेट करें (PDF / Print Preview) 🖨",
            data=pl_html,
            file_name=f"PL_Order_{pl_month}.html",
            mime="text/html"
        )
