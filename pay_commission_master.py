# -*- coding: utf-8 -*-
"""Universal / locked Pay Commission Master for Rajasthan Government software.

Source basis: Rajasthan Finance Department orders/rules for RCS (RP) Rules,
2008 and RCS (Revised Pay) Rules, 2017.  The data is intentionally read-only
for normal users; future statutory amendments can be added centrally without
changing dependent module interfaces.
"""
from __future__ import annotations
from copy import deepcopy
from datetime import date, datetime
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "pay_commission_master_data.json"

# 6th CPC: Rajasthan RCS (Revised Pay) Rules, 2008.
SIXTH_PAY_SCALES = [
    {"pre_scale":"2550-55-2660-60-3200","pay_band":"PB-1 (5200-20200)","grade_pay":1700,"grade_pay_no":"2"},
    {"pre_scale":"2610-60-3150-65-3540","pay_band":"PB-1 (5200-20200)","grade_pay":1750,"grade_pay_no":"3"},
    {"pre_scale":"2650-65-3300-70-4000","pay_band":"PB-1 (5200-20200)","grade_pay":1900,"grade_pay_no":"4"},
    {"pre_scale":"2750-70-3800-75-4400","pay_band":"PB-1 (5200-20200)","grade_pay":2000,"grade_pay_no":"5"},
    {"pre_scale":"4000-100-6000","pay_band":"PB-1 (5200-20200)","grade_pay":2400,"grade_pay_no":"9"},
    {"pre_scale":"4500-125-7000","pay_band":"PB-1 (5200-20200)","grade_pay":2800,"grade_pay_no":"10"},
    {"pre_scale":"5000-150-8000","pay_band":"PB-2 (9300-34800)","grade_pay":3600,"grade_pay_no":"11"},
    {"pre_scale":"6500-200-10500","pay_band":"PB-2 (9300-34800)","grade_pay":4200,"grade_pay_no":"12"},
    {"pre_scale":"7500-250-12000","pay_band":"PB-2 (9300-34800)","grade_pay":4800,"grade_pay_no":"14"},
    {"pre_scale":"8000-275-13500","pay_band":"PB-2 (9300-34800)","grade_pay":5400,"grade_pay_no":"15"},
    {"pre_scale":"8000-275-13500","pay_band":"PB-3 (15600-39100)","grade_pay":5400,"grade_pay_no":"15"},
    {"pre_scale":"9000-300-14400","pay_band":"PB-3 (15600-39100)","grade_pay":6000,"grade_pay_no":"16"},
    {"pre_scale":"10000-325-15200","pay_band":"PB-3 (15600-39100)","grade_pay":6600,"grade_pay_no":"17"},
    {"pre_scale":"10650-325-15850","pay_band":"PB-3 (15600-39100)","grade_pay":6800,"grade_pay_no":"18"},
    {"pre_scale":"11300-350-16200","pay_band":"PB-3 (15600-39100)","grade_pay":7200,"grade_pay_no":"19"},
    {"pre_scale":"12000-375-16500","pay_band":"PB-3 (15600-39100)","grade_pay":7600,"grade_pay_no":"20"},
    {"pre_scale":"13500-400-17500","pay_band":"PB-3 (15600-39100)","grade_pay":8200,"grade_pay_no":"21"},
    {"pre_scale":"14300-400-18300","pay_band":"PB-4 (37400-67000)","grade_pay":8700,"grade_pay_no":"22"},
    {"pre_scale":"16400-450-20000","pay_band":"PB-4 (37400-67000)","grade_pay":8900,"grade_pay_no":"23"},
    {"pre_scale":"18400-500-22400","pay_band":"PB-4 (37400-67000)","grade_pay":10000,"grade_pay_no":"24"},
]

# Historical 6th-CPC DA rates used for Rajasthan RCS (RP) 2008 pay.
SIXTH_DA = [
    ("2007-01-01", 6), ("2007-07-01", 9), ("2008-01-01", 12),
    ("2008-07-01", 16), ("2009-01-01", 22), ("2009-07-01", 27),
    ("2010-01-01", 35), ("2010-07-01", 45), ("2011-01-01", 51),
    ("2011-07-01", 58), ("2012-01-01", 65), ("2012-07-01", 72),
    ("2013-01-01", 80), ("2013-07-01", 90), ("2014-01-01", 100),
    ("2014-07-01", 107), ("2015-01-01", 113), ("2015-07-01", 119),
    ("2016-01-01", 125),
]

# 7th CPC DA rates. Rajasthan follows the State Finance Department orders;
# 2020-21 installments were frozen at 17%, then 28% from 01-07-2021.
SEVENTH_DA = [
    ("2017-01-01", 4), ("2017-07-01", 5), ("2018-01-01", 7),
    ("2018-07-01", 9), ("2019-01-01", 12), ("2019-07-01", 17),
    ("2021-07-01", 28), ("2022-01-01", 34), ("2022-07-01", 38),
    ("2023-01-01", 42), ("2023-07-01", 46), ("2024-01-01", 50),
    ("2024-07-01", 53), ("2025-01-01", 55), ("2025-07-01", 58),
    ("2026-01-01", 60),
]

SEVENTH_HRA = [
    ("2017-10-01", "Y", 16), ("2017-10-01", "Z", 8),
    ("2021-07-01", "Y", 18), ("2021-07-01", "Z", 9),
    ("2024-11-01", "Y", 20), ("2024-11-01", "Z", 10),
]
SIXTH_HRA = [
    ("2008-09-01", "Y", 20), ("2008-09-01", "Z", 10),
]

# Extracted from the project's existing verified 7th-CPC matrix, whose values
# correspond to Schedule-I Part-B of Rajasthan RCS (Revised Pay) Rules, 2017.
SEVENTH_PAY_MATRIX = {'L-1': [17700, 18200, 18700, 19300, 19900, 20500, 21100, 21700, 22400, 23100, 23800, 24500, 25200, 26000, 26800, 27600, 28400, 29300, 30200, 31100, 32000, 33000, 34000, 35000, 36100, 37200, 38300, 39400, 40600, 41800, 43100, 44400, 45700, 47100, 48500, 50000, 51500, 53000, 54600, 56200], 'L-2': [17900, 18400, 19000, 19600, 20200, 20800, 21400, 22000, 22700, 23400, 24100, 24800, 25500, 26300, 27100, 27900, 28700, 29600, 30500, 31400, 32300, 33300, 34300, 35300, 36400, 37500, 38600, 39800, 41000, 42200, 43500, 44800, 46100, 47500, 48900, 50400, 51900, 53500, 55100, 56800], 'L-3': [18200, 18700, 19300, 19900, 20500, 21100, 21700, 22400, 23100, 23800, 24500, 25200, 26000, 26800, 27600, 28400, 29300, 30200, 31100, 32000, 33000, 34000, 35000, 36100, 37200, 38300, 39400, 40600, 41800, 43100, 44400, 45700, 47100, 48500, 50000, 51500, 53000, 54600, 56200, 57900], 'L-4': [19200, 19800, 20400, 21000, 21600, 22200, 22900, 23600, 24300, 25000, 25800, 26600, 27400, 28200, 29000, 29900, 30800, 31700, 32700, 33700, 34700, 35700, 36800, 37900, 39000, 40200, 41400, 42600, 43900, 45200, 46600, 48000, 49400, 50900, 52400, 54000, 55600, 57300, 59000, 60800], 'L-5': [20800, 21400, 22000, 22700, 23400, 24100, 24800, 25500, 26300, 27100, 27900, 28700, 29600, 30500, 31400, 32300, 33300, 34300, 35300, 36400, 37500, 38600, 39800, 41000, 42200, 43500, 44800, 46100, 47500, 48900, 50400, 51900, 53500, 55100, 56800, 58500, 60300, 62100, 64000, 65900], 'L-6': [21500, 22100, 22800, 23500, 24200, 24900, 25600, 26400, 27200, 28000, 28800, 29700, 30600, 31500, 32400, 33400, 34400, 35400, 36500, 37600, 38700, 39900, 41100, 42300, 43600, 44900, 46200, 47600, 49000, 50500, 52000, 53600, 55200, 56900, 58600, 60400, 62200, 64100, 66000, 68000], 'L-7': [22400, 23100, 23800, 24500, 25200, 26000, 26800, 27600, 28400, 29300, 30200, 31100, 32000, 33000, 34000, 35000, 36100, 37200, 38300, 39400, 40600, 41800, 43100, 44400, 45700, 47100, 48500, 50000, 51500, 53000, 54600, 56200, 57900, 59600, 61400, 63200, 65100, 67100, 69100, 71200], 'L-8': [26300, 27100, 27900, 28700, 29600, 30500, 31400, 32300, 33300, 34300, 35300, 36400, 37500, 38600, 39800, 41000, 42200, 43500, 44800, 46100, 47500, 48900, 50400, 51900, 53500, 55100, 56800, 58500, 60300, 62100, 64000, 65900, 67900, 69900, 72000, 74200, 76400, 78700, 81100, 83500], 'L-9': [28700, 29600, 30500, 31400, 32300, 33300, 34300, 35300, 36400, 37500, 38600, 39800, 41000, 42200, 43500, 44800, 46100, 47500, 48900, 50400, 51900, 53500, 55100, 56800, 58500, 60300, 62100, 64000, 65900, 67900, 69900, 72000, 74200, 76400, 78700, 81100, 83500, 86000, 88600, 91300], 'L-10': [33800, 34800, 35800, 36900, 38000, 39100, 40300, 41500, 42700, 44000, 45300, 46700, 48100, 49500, 51000, 52500, 54100, 55700, 57400, 59100, 60900, 62700, 64600, 66500, 68500, 70600, 72700, 74900, 77100, 79400, 81800, 84300, 86800, 89400, 92100, 94900, 97700, 100600, 103600, 106700], 'L-11': [37800, 38900, 40100, 41300, 42500, 43800, 45100, 46500, 47900, 49300, 50800, 52300, 53900, 55500, 57200, 58900, 60700, 62500, 64400, 66300, 68300, 70300, 72400, 74600, 76800, 79100, 81500, 83900, 86400, 89000, 91700, 94500, 97300, 100200, 103200, 106300, 109500, 112800, 116200, 119700], 'L-12': [44300, 45600, 47000, 48400, 49900, 51400, 52900, 54500, 56100, 57800, 59500, 61300, 63100, 65000, 67000, 69000, 71100, 73200, 75400, 77700, 80000, 82400, 84900, 87400, 90000, 92700, 95500, 98400, 101400, 104400, 107500, 110700, 114000, 117400, 120900, 124500, 128200, 132000, 136000, 140100], 'L-13': [53100, 54700, 56300, 58000, 59700, 61500, 63300, 65200, 67200, 69200, 71300, 73400, 75600, 77900, 80200, 82600, 85100, 87700, 90300, 93000, 95800, 98700, 101700, 104800, 107900, 111100, 114400, 117800, 121300, 124900, 128600, 132500, 136500, 140600, 144800, 149100, 153600, 158200, 162900, 167800], 'L-14': [56100, 57800, 59500, 61300, 63100, 65000, 67000, 69000, 71100, 73200, 75400, 77700, 80000, 82400, 84900, 87400, 90000, 92700, 95500, 98400, 101400, 104400, 107500, 110700, 114000, 117400, 120900, 124500, 128200, 132000, 136000, 140100, 144300, 148600, 153100, 157700, 162400, 167300, 172300, 177500], 'L-15': [60700, 62500, 64400, 66300, 68300, 70300, 72400, 74600, 76800, 79100, 81500, 83900, 86400, 89000, 91700, 94500, 97300, 100200, 103200, 106300, 109500, 112800, 116200, 119700, 123300, 127000, 130800, 134700, 138700, 142900, 147200, 151600, 156100, 160800, 165600, 170600, 175700, 181000, 186400, 192000], 'L-16': [67300, 69300, 71400, 73500, 75700, 78000, 80300, 82700, 85200, 87800, 90400, 93100, 95900, 98800, 101800, 104900, 108000, 111200, 114500, 117900, 121400, 125000, 128800, 132700, 136700, 140800, 145000, 149400, 153900, 158500, 163300, 168200, 173200, 178400, 183800, 189300, 195000], 'L-17': [71000, 73100, 75300, 77600, 79900, 82300, 84800, 87300, 89900, 92600, 95400, 98300, 101200, 104200, 107300, 110500, 113800, 117200, 120700, 124300, 128000, 131800, 135800, 139900, 144100, 148400, 152900, 157500, 162200, 167100, 172100, 177300, 182600, 188100, 193700, 199500], 'L-18': [75300, 77600, 79900, 82300, 84800, 87300, 89900, 92600, 95400, 98300, 101200, 104200, 107300, 110500, 113800, 117200, 120700, 124300, 128000, 131800, 135800, 139900, 144100, 148400, 152900, 157500, 162200, 167100, 172100, 177300, 182600, 188100, 193700, 199500], 'L-19': [79900, 82300, 84800, 87300, 89900, 92600, 95400, 98300, 101200, 104200, 107300, 110500, 113800, 117200, 120700, 124300, 128000, 131800, 135800, 139900, 144100, 148400, 152900, 157500, 162200, 167100, 172100, 177300, 182600, 188100, 193700, 199500], 'L-20': [88900, 91600, 94300, 97100, 100000, 103000, 106100, 109300, 112600, 116000, 119500, 123100, 126800, 130600, 134500, 138500, 142700, 147000, 151400, 155900, 160600, 165400, 170400, 175500, 180800, 186200, 191800, 197600, 203500], 'L-21': [123100, 126800, 130600, 134500, 138500, 142700, 147000, 151400, 155900, 160600, 165400, 170400, 175500, 180800, 186200, 191800, 197600, 203500], 'L-22': [129700, 133600, 137600, 141700, 146000, 150400, 154900, 159500, 164300, 169200, 174300, 179500, 184900, 190400, 196100, 202000, 208100], 'L-23': [145800, 150200, 154700, 159300, 164100, 169000, 174100, 179300, 184700, 190200, 195900, 201800, 207900, 214100], 'L-24': [148800, 153300, 157900, 162600, 167500, 172500, 177700, 183000, 188500, 194200, 200000, 206000, 212200, 218600]}



MASTER_SCHEMA = [
    ("Record Type", "dropdown", True, ["PAY_LEVEL", "DA_RATE", "HRA_RATE", "INCREMENT_RULE"]),
    ("Pay Commission", "dropdown", True, ["6th Pay Commission", "7th Pay Commission"]),
    ("Effective From", "date", True, []),
    ("Effective To", "date", False, []),
    ("Pay Band", "text", False, []),
    ("Grade Pay", "number", False, []),
    ("Grade Pay No", "text", False, []),
    ("Level", "text", False, []),
    ("Pre-Revised Scale", "text", False, []),
    ("Cell No", "number", False, []),
    ("Basic Pay", "number", False, []),
    ("DA Rate %", "decimal", False, []),
    ("HRA Class", "text", False, []),
    ("HRA Rate %", "decimal", False, []),
    ("Increment Method", "text", False, []),
    ("Next Increment Date", "text", False, []),
    ("Notes", "text", False, []),
]


def build_records() -> List[Dict[str, Any]]:
    out = []
    for x in SIXTH_PAY_SCALES:
        out.append({"Record Type":"PAY_LEVEL","Pay Commission":"6th Pay Commission",
                    "Effective From":"2006-09-01","Pay Band":x["pay_band"],
                    "Grade Pay":x["grade_pay"],"Grade Pay No":x["grade_pay_no"],
                    "Pre-Revised Scale":x["pre_scale"],
                    "Increment Method":"3% of (Pay in Running Pay Band + Grade Pay), rounded to next multiple of 10",
                    "Next Increment Date":"1 July; 6 months and above qualifying service",
                    "Notes":"Rajasthan RCS (RP) Rules, 2008"})
    for level, cells in SEVENTH_PAY_MATRIX.items():
        for i, basic in enumerate(cells, 1):
            out.append({"Record Type":"PAY_LEVEL","Pay Commission":"7th Pay Commission",
                        "Effective From":"2016-01-01","Level":level,"Cell No":i,"Basic Pay":basic,
                        "Increment Method":"Next vertical Cell in the same Level",
                        "Next Increment Date":"1 July; 6 months and above in the Level",
                        "Notes":"Rajasthan RCS (Revised Pay) Rules, 2017"})
    for eff, rate in SIXTH_DA:
        out.append({"Record Type":"DA_RATE","Pay Commission":"6th Pay Commission","Effective From":eff,"DA Rate %":rate,
                    "Notes":"DA on Basic Pay (Pay in Running Pay Band + Grade Pay)"})
    for eff, rate in SEVENTH_DA:
        out.append({"Record Type":"DA_RATE","Pay Commission":"7th Pay Commission","Effective From":eff,"DA Rate %":rate,
                    "Notes":"DA on Basic Pay drawn in prescribed Level"})
    for eff, cls, rate in SIXTH_HRA:
        out.append({"Record Type":"HRA_RATE","Pay Commission":"6th Pay Commission","Effective From":eff,"HRA Class":cls,"HRA Rate %":rate,
                    "Notes":"Y=20%, Z=10% from 01-09-2008"})
    for eff, cls, rate in SEVENTH_HRA:
        out.append({"Record Type":"HRA_RATE","Pay Commission":"7th Pay Commission","Effective From":eff,"HRA Class":cls,"HRA Rate %":rate,
                    "Notes":"Y/Z rates change when DA crosses prescribed thresholds"})
    out.append({"Record Type":"INCREMENT_RULE","Pay Commission":"6th Pay Commission","Effective From":"2006-09-01",
                "Increment Method":"3% of Pay Band + Grade Pay, rounded to next multiple of 10; add to Running Pay Band",
                "Next Increment Date":"1 July; 6 months and above"})
    out.append({"Record Type":"INCREMENT_RULE","Pay Commission":"7th Pay Commission","Effective From":"2016-01-01",
                "Increment Method":"Move to next vertical cell of applicable Pay Level",
                "Next Increment Date":"1 July; 6 months and above"})
    return out


def ensure_data_file() -> Path:
    records = build_records()
    payload = {"version":"1.0.0","scope":"Rajasthan Government","locked":True,
               "source":"Rajasthan Finance Department RCS (RP) Rules, 2008 and RCS (Revised Pay) Rules, 2017",
               "schema":MASTER_SCHEMA,"records":records}
    DATA_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return DATA_FILE


def load_master() -> Dict[str, Any]:
    if not DATA_FILE.exists():
        ensure_data_file()
    try:
        return json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except Exception:
        ensure_data_file()
        return json.loads(DATA_FILE.read_text(encoding="utf-8"))


def _d(s: Any) -> Optional[date]:
    try: return datetime.strptime(str(s), "%Y-%m-%d").date()
    except Exception: return None


def get_records(record_type: Optional[str] = None, commission: Optional[str] = None) -> List[Dict[str, Any]]:
    rows = load_master().get("records", [])
    if record_type: rows = [r for r in rows if r.get("Record Type") == record_type]
    if commission: rows = [r for r in rows if r.get("Pay Commission") == commission]
    return deepcopy(rows)


def get_da_rate(commission: str, on_date: Any) -> float:
    dt = on_date if isinstance(on_date, date) else _d(on_date)
    rows = get_records("DA_RATE", commission)
    selected = 0.0
    for r in rows:
        eff = _d(r.get("Effective From"))
        if eff and dt and eff <= dt: selected = float(r.get("DA Rate %") or 0)
    return selected


def get_hra_rate(commission: str, city_class: str, on_date: Any) -> float:
    dt = on_date if isinstance(on_date, date) else _d(on_date)
    cls = "Y" if str(city_class).upper().startswith(("Y", "CLASSIFIED")) else "Z"
    rows = [r for r in get_records("HRA_RATE", commission) if r.get("HRA Class") == cls]
    selected = 0.0
    for r in rows:
        eff = _d(r.get("Effective From"))
        if eff and dt and eff <= dt: selected = float(r.get("HRA Rate %") or 0)
    return selected


def get_7th_level(level: str) -> Dict[str, Any]:
    key = str(level or "").upper().replace(" ", "")
    if not key.startswith("L-") and key.startswith("L"): key = "L-" + key[1:]
    matrix = SEVENTH_PAY_MATRIX.get(key, [])
    return {"level":key,"cells":deepcopy(matrix),"first_cell":matrix[0] if matrix else None}


def get_6th_options() -> List[Dict[str, Any]]:
    return deepcopy(SIXTH_PAY_SCALES)


def calculate_6th_increment(pay_in_band: int, grade_pay: int) -> int:
    """Return revised Basic after one 6th-CPC annual increment."""
    pay_in_band = int(pay_in_band)
    grade_pay = int(grade_pay)
    total = pay_in_band + grade_pay
    inc = int(((total * 0.03) + 9) // 10) * 10
    return pay_in_band + inc + grade_pay


def calculate_7th_increment(level: str, basic: int) -> int:
    cells = get_7th_level(level).get("cells", [])
    b = int(basic)
    if not cells: return b
    if b in cells:
        i = cells.index(b)
        return cells[min(i+1, len(cells)-1)]
    for v in cells:
        if v > b: return v
    return cells[-1]


def employee_pay_profile(username: str, record: Dict[str, Any]) -> Dict[str, Any]:
    # Accept raw Employee Master record and map by field labels via service.
    try:
        from master_data_service import MasterDataService
        svc = MasterDataService(username, ensure_system_master=True)
        emp = svc.get_master_by_name("Employee Master Data")
        if not emp: return {}
        def val(*aliases): return svc.first_field_value(emp["master_id"], record, aliases)
        return {
            "name": val("Employee Name", "Name", "कर्मचारी का नाम"),
            "employee_id": val("Employee ID"), "designation": val("Designation", "पद"),
            "basic": int(float(val("Basic Pay", "मूल वेतन") or 0)),
            "level": str(val("Pay Level", "Level") or "").strip().upper().replace(" ", ""),
            "pay_band": val("Pay Band"), "grade_pay": int(float(val("Grade Pay") or 0)),
            "appointment_date": val("Appointment Date"), "joining_date": val("Joining Date"),
            "gpf": val("GPF / PRAN Number"), "pan": val("PAN Number"),
            "bank": val("Bank Name"), "branch": val("Branch"), "account": val("Account Number"), "ifsc": val("IFSC"),
        }
    except Exception:
        return {}


def employee_master_records(username: str) -> List[Dict[str, Any]]:
    try:
        from master_data_service import MasterDataService
        svc = MasterDataService(username, ensure_system_master=True)
        emp = svc.get_master_by_name("Employee Master Data")
        return svc.get_records(emp["master_id"]) if emp else []
    except Exception:
        return []
