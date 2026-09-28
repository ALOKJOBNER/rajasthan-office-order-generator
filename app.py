import streamlit as st
import base64
import math
import os
import json
import calendar
from datetime import datetime, date

# 1. पेज कॉन्फ़िगरेशन
st.set_page_config(
    page_title="राजस्थान गवर्नमेंट ऑफिस ऑर्डर जनरेटर सॉफ्टवेयर",
    page_icon="📜",
    layout="wide"
)

# 2. डेटा फ़ाइल पाथ्स एवं ऑटो-लोडिंग लॉजिक
PL_DATA_FILE = os.path.join("output", "saved_pl_data.json")
INC_DATA_FILE = os.path.join("output", "saved_increment_data.json")
SAN_DATA_FILE = os.path.join("output", "saved_sanchalan_data.json")
ARREAR_DATA_FILE = os.path.join("output", "saved_arrear_data.json")
MASTER_VENDORS_FILE = "master_vendors.json"
MASTER_SCHOOLS_FILE = "master_schools.json"
MASTER_BENEFICIARIES_FILE = "master_beneficiaries.json"

def load_json_data(file_path, default_val=None):
    if default_val is None:
        default_val = {"office_data": {}, "employees": []}
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default_val
    return default_val

def save_json_data(file_path, data):
    os.makedirs("output", exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_json_file(filename, default_val):
    if os.path.exists(filename):
        try:
            with open(filename, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default_val
    return default_val

def save_json_file(filename, data):
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception:
        pass

# 3. ग्लोबल डेटा डेफिनिशन
DESIG_LIST = [
    "वरिष्ठ अध्यापक", "प्रधानाचार्य", "उप प्रधानाचार्य", "व्याख्याता", 
    "अध्यापक लेवल 2", "अध्यापक लेवल 1", "शारीरिक शिक्षक", "पुस्तकालय अध्यक्ष", 
    "सहायक प्रशासनिक अधिकारी", "कनिष्ठ लिपिक", "चतुर्थ श्रेणी कर्मचारी", "अन्य"
]

DA_PRESETS = {
    "7th Pay Commission": ["60%", "58%", "55%", "53%", "50%", "46%", "42%", "38%", "34%", "31%", "17%", "12%", "9%", "7%", "5%", "4%"],
    "6th Pay Commission": ["246%", "239%", "230%", "221%", "212%", "203%", "196%", "189%", "164%", "154%", "142%", "132%", "125%", "119%", "113%", "107%", "100%"],
    "5th Pay Commission": ["443%", "427%", "412%", "398%", "381%", "368%", "356%", "341%", "324%", "305%", "295%", "250%", "200%"]
}

PAY_MATRIX_7TH = {
    "L-1": [17700, 18200, 18700, 19300, 19900, 20500, 21100, 21700, 22400, 23100, 23800, 24500, 25200, 26000, 26800, 27600, 28400, 29300, 30200, 31100, 32000, 33000, 34000, 35000, 36100, 37200, 38300, 39400, 40600, 41800, 43100, 44400, 45700, 47100, 48500, 50000, 51500, 53000, 54600, 56200],
    "L-2": [17900, 18400, 19000, 19600, 20200, 20800, 21400, 22000, 22700, 23400, 24100, 24800, 25500, 26300, 27100, 27900, 28700, 29600, 30500, 31400, 32300, 33300, 34300, 35300, 36400, 37500, 38600, 39800, 41000, 42200, 43500, 44800, 46100, 47500, 48900, 50400, 51900, 53500, 55100, 56800],
    "L-3": [18200, 18700, 19300, 19900, 20500, 21100, 21700, 22400, 23100, 23800, 24500, 25200, 26000, 26800, 27600, 28400, 29300, 30200, 31100, 32000, 33000, 34000, 35000, 36100, 37200, 38300, 39400, 40600, 41800, 43100, 44400, 45700, 47100, 48500, 50000, 51500, 53000, 54600, 56200, 57900],
    "L-4": [19200, 19800, 20400, 21000, 21600, 22200, 22900, 23600, 24300, 25000, 25800, 26600, 27400, 28200, 29000, 29900, 30800, 31700, 32700, 33700, 34700, 35700, 36800, 37900, 39000, 40200, 41400, 42600, 43900, 45200, 46600, 48000, 49400, 50900, 52400, 54000, 55600, 57300, 59000, 60800],
    "L-5": [20800, 21400, 22000, 22700, 23400, 24100, 24800, 25500, 26300, 27100, 27900, 28700, 29600, 30500, 31400, 32300, 33300, 34300, 35300, 36400, 37500, 38600, 39800, 41000, 42200, 43500, 44800, 46100, 47500, 48900, 50400, 51900, 53500, 55100, 56800, 58500, 60300, 62100, 64000, 65900],
    "L-6": [21500, 22100, 22800, 23500, 24200, 24900, 25600, 26400, 27200, 28000, 28800, 29700, 30600, 31500, 32400, 33400, 34400, 35400, 36500, 37600, 38700, 39900, 41100, 42300, 43600, 44900, 46200, 47600, 49000, 50500, 52000, 53600, 55200, 56900, 58600, 60400, 62200, 64100, 66000, 68000],
    "L-7": [22400, 23100, 23800, 24500, 25200, 26000, 26800, 27600, 28400, 29300, 30200, 31100, 32000, 33000, 34000, 35000, 36100, 37200, 38300, 39400, 40600, 41800, 43100, 44400, 45700, 47100, 48500, 50000, 51500, 53000, 54600, 56200, 57900, 59600, 61400, 63200, 65100, 67100, 69100, 71200],
    "L-8": [26300, 27100, 27900, 28700, 29600, 30500, 31400, 32300, 33300, 34300, 35300, 36400, 37500, 38600, 39800, 41000, 42200, 43500, 44800, 46100, 47500, 48900, 50400, 51900, 53500, 55100, 56800, 58500, 60300, 62100, 64000, 65900, 67900, 69900, 72000, 74200, 76400, 78700, 81100, 83500],
    "L-9": [28700, 29600, 30500, 31400, 32300, 33300, 34300, 35300, 36400, 37500, 38600, 39800, 41000, 42200, 43500, 44800, 46100, 47500, 48900, 50400, 51900, 53500, 55100, 56800, 58500, 60300, 62100, 64000, 65900, 67900, 69900, 72000, 74200, 76400, 78700, 81100, 83500, 86000, 88600, 91300],
    "L-10": [33800, 34800, 35800, 36900, 38000, 39100, 40300, 41500, 42700, 44000, 45300, 46700, 48100, 49500, 51000, 52500, 54100, 55700, 57400, 59100, 60900, 62700, 64600, 66500, 68500, 70600, 72700, 74900, 77100, 79400, 81800, 84300, 86800, 89400, 92100, 94900, 97700, 100600, 103600, 106700],
    "L-11": [37800, 38900, 40100, 41300, 42500, 43800, 45100, 46500, 47900, 49300, 50800, 52300, 53900, 55500, 57200, 58900, 60700, 62500, 64400, 66300, 68300, 70300, 72400, 74600, 76800, 79100, 81500, 83900, 86400, 89000, 91700, 94500, 97300, 100200, 103200, 106300, 109500, 112800, 116200, 119700],
    "L-12": [44300, 45600, 47000, 48400, 49900, 51400, 52900, 54500, 56100, 57800, 59500, 61300, 63100, 65000, 67000, 69000, 71100, 73200, 75400, 77700, 80000, 82400, 84900, 87400, 90000, 92700, 95500, 98400, 101400, 104400, 107500, 110700, 114000, 117400, 120900, 124500, 128200, 132000, 136000, 140100],
    "L-13": [53100, 54700, 56300, 58000, 59700, 61500, 63300, 65200, 67200, 69200, 71300, 73400, 75600, 77900, 80200, 82600, 85100, 87700, 90300, 93000, 95800, 98700, 101700, 104800, 107900, 111100, 114400, 117800, 121300, 124900, 128600, 132500, 136500, 140600, 144800, 149100, 153600, 158200, 162900, 167800],
    "L-14": [56100, 57800, 59500, 61300, 63100, 65000, 67000, 69000, 71100, 73200, 75400, 77700, 80000, 82400, 84900, 87400, 90000, 92700, 95500, 98400, 101400, 104400, 107500, 110700, 114000, 117400, 120900, 124500, 128200, 132000, 136000, 140100, 144300, 148600, 153100, 157700, 162400, 167300, 172300, 177500],
    "L-15": [60700, 62500, 64400, 66300, 68300, 70300, 72400, 74600, 76800, 79100, 81500, 83900, 86400, 89000, 91700, 94500, 97300, 100200, 103200, 106300, 109500, 112800, 116200, 119700, 123300, 127000, 130800, 134700, 138700, 142900, 147200, 151600, 156100, 160800, 165600, 170600, 175700, 181000, 186400, 192000],
    "L-16": [67300, 69300, 71400, 73500, 75700, 78000, 80300, 82700, 85200, 87800, 90400, 93100, 95900, 98800, 101800, 104900, 108000, 111200, 114500, 117900, 121400, 125000, 128800, 132700, 136700, 140800, 145000, 149400, 153900, 158500, 163300, 168200, 173200, 178400, 183800, 189300, 195000, 199500, 199500, 199500],
    "L-17": [71000, 73100, 75300, 77600, 79900, 82300, 84800, 87300, 89900, 92600, 95400, 98300, 101200, 104200, 107300, 110500, 113800, 117200, 120700, 124300, 128000, 131800, 135800, 139900, 144100, 148400, 152900, 157500, 162200, 167100, 172100, 177300, 182600, 188100, 193700, 199500, 199500, 199500, 199500, 199500],
    "L-18": [75300, 77600, 79900, 82300, 84800, 87300, 89900, 92600, 95400, 98300, 101200, 104200, 107300, 110500, 113800, 117200, 120700, 124300, 128000, 131800, 135800, 139900, 144100, 148400, 152900, 157500, 162200, 167100, 172100, 177300, 182600, 188100, 193700, 199500, 199500, 199500, 199500, 199500, 199500, 199500]
}

SNA_COMPONENTS = {
    "SEC": [
        "ICT Lab & Smart Class (आई.सी.टी. लैब एवं स्मार्ट क्लास)",
        "Library Books & Grants (पुस्तकालय पुस्तकें एवं अनुदान)",
        "School Maintenance & Repair (विद्यालय रखरखाव एवं मरम्मत)",
        "Civil Works & Minor Repair (सिविल कार्य एवं लघु मरम्मत)",
        "Composite School Grant (कंपोजिट स्कूल ग्रांट)",
        "Sports & Physical Education (खेलकूद एवं शारीरिक शिक्षा)",
        "Grants for Special Training (विशेष प्रशिक्षण अनुदान)",
        "Media & Publicity (मीडिया एवं प्रचार-प्रसार)",
        "Other Component (अन्य कंपोनेंट)"
    ],
    "ELE": [
        "Free Textbooks (निःशुल्क पाठ्यपुस्तकें)",
        "School Uniforms (निःशुल्क गणवेश/यूनिफॉर्म)",
        "Library Books & Grants (पुस्तकालय पुस्तकें एवं अनुदान)",
        "School Maintenance & Repair (विद्यालय रखरखाव एवं मरम्मत)",
        "Civil Works & Minor Repair (सिविल कार्य एवं लघु मरम्मत)",
        "Composite School Grant (कंपोजिट स्कूल ग्रांट)",
        "Sports & Physical Education (खेलकूद एवं शारीरिक शिक्षा)",
        "Grants for Special Training (विशेष प्रशिक्षण अनुदान)",
        "Media & Publicity (मीडिया एवं प्रचार-प्रसार)",
        "Other Component (अन्य कंपोनेंट)"
    ]
}

ARREAR_REASONS = [
    "प्रमोशन (Promotion)",
    "एसीपी / एमएसीपी (ACP / MACP)",
    "वेतन निर्धारण उपरांत (Pay Fixation)",
    "वेतन वृद्धि के कारण (Due to Annual Increment)",
    "पीएल सरेंडर डीए एरियर (PL Surrender DA Arrear)",
    "सेवानिवृत्ति पश्चात पीएल नगद भुगतान एरियर (Retirement PL Cash Payment Arrear)",
    "अन्य प्रशासनिक कारण (Other Administrative Reason)"
]


# राष्ट्रीयकृत बैंकों की सूची — Arrear Module dropdown
NATIONALIZED_BANKS = [
    "State Bank of India",
    "Bank of Baroda",
    "Bank of India",
    "Bank of Maharashtra",
    "Canara Bank",
    "Central Bank of India",
    "Indian Bank",
    "Indian Overseas Bank",
    "Punjab & Sind Bank",
    "Punjab National Bank",
    "UCO Bank",
    "Union Bank of India",
]

# Arrear calculation engine is integrated below; no external arrear module import is required.



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
    """Annual-increment helper used by the existing Annual Increment module."""
    if "7th" in str(commission):
        return get_next_pay_step(level_str, int(current_basic))
    return int(current_basic)


def make_short_name(full_name):
    if not full_name:
        return ""
    replaced = full_name.replace("राजकीय उच्च माध्यमिक विद्यालय", "रा.उ.मा.वि.")
    replaced = replaced.replace("राजकीय उच्च प्राथमिक विद्यालय", "रा.उ.प्रा.वि.")
    replaced = replaced.replace("पंचायत समिति", "प.स.")
    return replaced

def get_image_base64():
    for ext in [".jpg", ".png", ".jpeg", ".JPG", ".PNG"]:
        p = f"aloksingh{ext}"
        if os.path.exists(p):
            with open(p, "rb") as f:
                return base64.b64encode(f.read()).decode()
    return ""

img_b64 = get_image_base64()

def generate_sun_rays_svg():
    cx, cy = 130, 130
    inner_r = 66
    num_rays = 24
    polygons = []
    for i in range(num_rays):
        deg = i * (360 / num_rays)
        if i % 2 == 0:
            outer_r = 122
            half_base = 5.0
            color = "#f1c40f"
        else:
            outer_r = 96
            half_base = 3.5
            color = "#ff9f43"
        rad_tip = math.radians(deg)
        rad_left = math.radians(deg - half_base)
        rad_right = math.radians(deg + half_base)
        x1 = cx + inner_r * math.cos(rad_left)
        y1 = cy + inner_r * math.sin(rad_left)
        xtip = cx + outer_r * math.cos(rad_tip)
        ytip = cy + outer_r * math.sin(rad_tip)
        x2 = cx + inner_r * math.cos(rad_right)
        y2 = cy + inner_r * math.sin(rad_right)
        polygons.append(f'<polygon points="{x1:.1f},{y1:.1f} {xtip:.1f},{ytip:.1f} {x2:.1f},{y2:.1f}" fill="{color}" />')
    polys_str = "".join(polygons)
    return f'''<svg class="spinning-rays" viewBox="0 0 260 260" width="260" height="260">
        <circle cx="{cx}" cy="{cy}" r="{inner_r + 1}" stroke="#f39c12" stroke-width="3" fill="none" />
        {polys_str}
    </svg>'''

rays_svg_html = generate_sun_rays_svg()

st.markdown("""
<style>
    .stApp { background-color: #0c1d36; color: #ffffff; }
    
    .main-header {
        background: linear-gradient(90deg, #102a45, #1b4f72);
        padding: 16px;
        border-radius: 10px;
        text-align: center;
        border: 2px solid #f4d03f;
        margin-bottom: 20px;
    }
    
    .profile-card {
        background-color: #132743;
        padding: 18px;
        border-radius: 12px;
        border: 1px solid #f39c12;
        text-align: center;
    }

    .sun-box {
        position: relative;
        width: 260px;
        height: 260px;
        margin: 0 auto 5px auto;
        display: flex;
        align-items: center;
        justify-content: center;
    }

    .spinning-rays {
        position: absolute;
        animation: spinClockwise 12s linear infinite;
        z-index: 1;
    }

    @keyframes spinClockwise {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }

    .profile-center-img {
        position: relative;
        width: 130px;
        height: 130px;
        border-radius: 50%;
        border: 3px solid #f39c12;
        background-size: cover;
        background-position: center 25%;
        z-index: 2;
        box-shadow: 0 0 16px rgba(0,0,0,0.8);
    }

    .scope-box {
        background-color: #132743;
        border: 1px solid #f4d03f;
        border-radius: 8px;
        padding: 14px 18px;
        margin-bottom: 20px;
        font-size: 13.5px;
        line-height: 1.6;
    }

    label, [data-testid="stWidgetLabel"] p, [data-testid="stWidgetLabel"] span, .stRadio label p, div[data-baseweb="radio"] div {
        color: #f4d03f !important;
        font-size: 14.5px !important;
        font-weight: bold !important;
        opacity: 1 !important;
    }

    input, select, textarea, [data-baseweb="select"], [data-baseweb="textarea"] {
        background-color: #1c3b60 !important;
        color: #ffffff !important;
        font-weight: bold !important;
        border: 1px solid #2e5b88 !important;
        border-radius: 6px !important;
    }

    [data-testid="stExpander"] {
        background-color: #132743 !important;
        border: 1px solid #f4d03f !important;
        border-radius: 8px !important;
    }
    [data-testid="stExpander"] summary span {
        color: #f4d03f !important;
        font-weight: bold !important;
    }
    .stExpander textarea {
        background-color: #0c1d36 !important;
        color: #2ecc71 !important;
        font-family: monospace !important;
        font-size: 12.5px !important;
    }

    .menu-btn-pl {
        display: block; width: 100%; background-color: #1f618d; color: #ffffff !important;
        text-decoration: none !important; padding: 14px 20px; font-size: 16px; font-weight: bold;
        border-radius: 8px; border: 2px solid #2980b9; box-shadow: 0 4px 0 #154360; margin-bottom: 12px; text-align: left;
    }
    .menu-btn-pl:hover { background-color: #2980b9; }

    .menu-btn-inc {
        display: block; width: 100%; background-color: #27ae60; color: #ffffff !important;
        text-decoration: none !important; padding: 14px 20px; font-size: 16px; font-weight: bold;
        border-radius: 8px; border: 2px solid #2ecc71; box-shadow: 0 4px 0 #1e8449; margin-bottom: 12px; text-align: left;
    }
    .menu-btn-inc:hover { background-color: #2ecc71; }

    .menu-btn-san {
        display: block; width: 100%; background-color: #8e44ad; color: #ffffff !important;
        text-decoration: none !important; padding: 14px 20px; font-size: 16px; font-weight: bold;
        border-radius: 8px; border: 2px solid #9b59b6; box-shadow: 0 4px 0 #512e5f; margin-bottom: 12px; text-align: left;
    }
    .menu-btn-san:hover { background-color: #9b59b6; }

    .menu-btn-arr {
        display: block; width: 100%; background-color: #d35400; color: #ffffff !important;
        text-decoration: none !important; padding: 14px 20px; font-size: 16px; font-weight: bold;
        border-radius: 8px; border: 2px solid #e67e22; box-shadow: 0 4px 0 #a04000; margin-bottom: 12px; text-align: left;
    }
    .menu-btn-arr:hover { background-color: #e67e22; }

    .menu-btn-rel {
        display: block; width: 100%; background-color: #212f3d; color: #a6acaf !important;
        text-decoration: none !important; padding: 12px 20px; font-size: 15px; border-radius: 8px;
        border: 1px solid #34495e; box-shadow: 0 3px 0 #17202a; text-align: left;
    }

    .back-btn {
        display: inline-block; background-color: #c0392b; color: #ffffff !important;
        text-decoration: none !important; padding: 8px 18px; font-size: 14px; font-weight: bold;
        border-radius: 6px; border: 1px solid #e74c3c; margin-bottom: 15px;
    }
    .back-btn:hover { background-color: #e74c3c; }

    button, div.stButton > button, div[data-testid="stFormSubmitButton"] > button {
        background-color: #2980b9 !important;
        color: #ffffff !important;
        font-weight: bold !important;
        border: 2px solid #3498db !important;
        border-radius: 6px !important;
        box-shadow: 0 4px 0 #1b4f72 !important;
    }
    button *, div.stButton > button *, div[data-testid="stFormSubmitButton"] > button * {
        color: #ffffff !important;
        font-weight: bold !important;
    }

    div[data-testid="stFormSubmitButton"] > button {
        background-color: #27ae60 !important;
        border-color: #2ecc71 !important;
        box-shadow: 0 4px 0 #1e8449 !important;
    }

    div[data-testid="stDownloadButton"] > button {
        background-color: #d35400 !important;
        border: 2px solid #e67e22 !important;
        border-radius: 8px !important;
        box-shadow: 0 6px 0 #a04000 !important;
        width: 100% !important;
        padding: 14px !important;
        margin-top: 15px !important;
    }
    div[data-testid="stDownloadButton"] > button * {
        color: #ffffff !important;
        font-size: 17px !important;
        font-weight: 800 !important;
    }

    .custom-table {
        width: 100%; border-collapse: collapse; margin: 10px 0; font-size: 13px;
    }
    .custom-table th {
        background-color: #1b4f72; color: #ffffff; padding: 8px; border: 1px solid #2e5b88; text-align: center;
    }
    .custom-table td {
        background-color: #0e2338; color: #ffffff; padding: 8px; border: 1px solid #2e5b88; text-align: center;
    }
</style>
""", unsafe_allow_html=True)

params = st.query_params
active_page = params.get("page", "dashboard")

# =============================================================================
# पृष्ठ 1: मुख्य डैशबोर्ड
# =============================================================================

# ---------------------------------------------------------------------------
# Integrated arrear helper: initial Due Basic / Pay Fixation
# ---------------------------------------------------------------------------
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

DA_RULES = [
    ((2017, 1), 4.0, 4.0, False),
    ((2017, 7), 5.0, 5.0, False),
    ((2018, 1), 7.0, 5.0, True),
    ((2018, 3), 7.0, 7.0, False),
    ((2018, 7), 9.0, 7.0, True),
    ((2018, 9), 9.0, 9.0, False),
    ((2019, 1), 12.0, 9.0, True),
    ((2019, 3), 12.0, 12.0, False),
    ((2019, 7), 17.0, 12.0, True),
    ((2020, 3), 17.0, 17.0, False),
    ((2021, 7), 31.0, 28.0, True),
    ((2021, 10), 31.0, 31.0, False),
    ((2022, 1), 34.0, 31.0, True),
    ((2022, 4), 34.0, 34.0, False),
    ((2022, 7), 38.0, 34.0, True),
    ((2022, 10), 38.0, 38.0, False),
    ((2023, 1), 42.0, 38.0, True),
    ((2023, 4), 42.0, 42.0, False),
    ((2023, 7), 46.0, 42.0, True),
    ((2023, 11), 46.0, 46.0, False),
    ((2024, 1), 50.0, 46.0, True),
    ((2024, 3), 50.0, 50.0, False),
    ((2024, 7), 53.0, 50.0, True),
    ((2024, 11), 53.0, 53.0, False),
    ((2025, 1), 55.0, 50.0, True),
    ((2025, 4), 55.0, 55.0, False),
    ((2025, 7), 58.0, 55.0, True),
    ((2025, 10), 58.0, 58.0, False),
    ((2026, 1), 60.0, 58.0, True),
    ((2026, 5), 60.0, 60.0, False),
]

# Exact GPF-credit periods supplied by the user.
GPF_DA_PERIODS = {
    (2018, 1), (2018, 2),
    (2018, 7), (2018, 8),
    (2019, 1), (2019, 2),
    *{(y, m) for y in (2019,) for m in range(7, 13)},
    (2020, 1), (2020, 2),
    (2021, 7), (2021, 8), (2021, 9),
    (2022, 1), (2022, 2), (2022, 3),
    (2022, 7), (2022, 8), (2022, 9),
    (2023, 1), (2023, 2), (2023, 3),
    (2023, 7), (2023, 8), (2023, 9), (2023, 10),
    (2024, 1), (2024, 2),
    (2024, 7), (2024, 8), (2024, 9), (2024, 10),
    (2025, 1), (2025, 2), (2025, 3),
    (2025, 7), (2025, 8), (2025, 9),
    (2026, 1), (2026, 2), (2026, 3), (2026, 4),
}


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


def get_hra_rate(city_type: str, year: int, month: int) -> float:
    """Keep the existing city-category HRA interface used by the UI."""
    if (year, month) >= (2024, 11):
        return 20.0 if city_type == "Classified" else 10.0
    if (year, month) >= (2021, 7):
        return 18.0 if city_type == "Classified" else 9.0
    return 16.0 if city_type == "Classified" else 8.0


# User-supplied deduction slabs.
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

if active_page == "dashboard":
    st.markdown("""
    <div class="main-header">
        <h1 style="color: #f4d03f; margin:0; font-size: 27px;">राजस्थान गवर्नमेंट ऑफिस ऑर्डर जनरेटर सॉफ्टवेयर</h1>
        <p style="color: #d5dbdb; margin:5px 0 0 0; font-style: italic; font-size: 13px;">
            शासकीय एवं प्रशासनिक आदेश स्वचालन प्रणाली (Rajasthan Service Rules Compliant)
        </p>
    </div>
    """, unsafe_allow_html=True)

    col_left, col_right = st.columns([1.1, 3])

    with col_left:
        st.markdown(f"""
        <div class="profile-card">
            <div class="sun-box">
                {rays_svg_html}
                <div class="profile-center-img" style="background-image: url('data:image/jpeg;base64,{img_b64}');"></div>
            </div>
            <div style="color: #f39c12; font-weight: bold; font-size: 13px; margin-top: 4px;">★ सॉफ्टवेयर डेवलपर ★</div>
            <h3 style="color: #ffffff; margin: 4px 0 6px 0;">आलोक कुमार सिंह</h3>
            <p style="color: #85c1e9; margin: 0; font-size: 12.5px; line-height: 1.5;">
                वरिष्ठ अध्यापक<br>राजकीय उच्च माध्यमिक विद्यालय, रोजड़ी<br>पंचायत समिति: सांभर लेक (जयपुर)
            </p>
            <div style="background-color: #0c1d36; border: 1px solid #2c3e50; border-radius: 6px; padding: 8px; margin-top: 12px; text-align: left;">
                <p style="color: #2ecc71; margin: 2px 0; font-size: 12.5px;">📞 <b>मोबाइल: 9414818991</b></p>
                <p style="color: #5dade2; margin: 2px 0; font-size: 11.5px;">✉ <b>alokjobner@gmail.com</b></p>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col_right:
        st.markdown("""
        <div class="scope-box">
            <span style="color: #f4d03f; font-weight: bold; font-size: 15px;">सॉफ्टवेयर के कार्य एवं भावी विस्तार योजना:</span><br>
            <span style="color: #2ecc71;">✔ वर्तमान क्षमताएं:</span> उपार्जित अवकाश (PL Surrender) की सटीक नियमानुसार ऑटो-कैलकुलेशन, वार्षिक सामयिक वेतन वृद्धि (Annual Increment) आदेश, संचालन पोर्टल भुगतान स्वीकृति आदेश (SNA Sanction Order), <b>7th Pay Commission आधारित लैंडस्केप रो-वाइज वेतन एरियर (Salary Arrear) गणना एवं अंतर विवरण प्रपत्र</b>, मल्टीपल कार्मिक/वेंडर प्रविष्टि, A4 लैंडस्केप बॉर्डर प्रिंट आदेश.<br>
            <span style="color: #f39c12;">🚀 भविष्य में संभावित कार्य:</span> कार्यमुक्ति (Relieving) व कार्यग्रहण (Joining) आदेश, बाल देखरेख अवकाश (CCL) स्वीकृति, स्थायीकरण (Confirmation) आदेश तथा समस्त वित्तीय व प्रशासनिक स्वीकृतियों का केंद्रीकृत स्वचालन।
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<h4 style='color:#5dade2; margin-bottom: 14px;'>कार्यालय आदेश मॉड्यूल चयन करें:</h4>", unsafe_allow_html=True)

        st.markdown("""
        <a href="/?page=pl_surrender" target="_self" class="menu-btn-pl">
            1. उपार्जित अवकाश समर्पण (PL Surrender) आदेश जनरेटर ▶
        </a>
        <a href="/?page=increment_order" target="_self" class="menu-btn-inc">
            2. वार्षिक सामयिक वेतन वृद्धि (Annual Increment) आदेश जनरेटर ▶
        </a>
        <a href="/?page=sanchalan_portal" target="_self" class="menu-btn-san">
            3. संचालन पोर्टल भुगतान स्वीकृति आदेश (SNA Sanction Order) जनरेटर ▶
        </a>
        <a href="/?page=salary_arrear" target="_self" class="menu-btn-arr">
            4. वेतन एरियर (Salary Arrear) अंतर विवरण प्रपत्र एवं गणना (7th CPC Landscape) ▶
        </a>
        <div class="menu-btn-rel">
            5. कार्यमुक्ति / कार्यग्रहण (Relieving / Joining) आदेश [शीघ्र उपलब्ध]
        </div>
        """, unsafe_allow_html=True)

# =============================================================================
# पृष्ठ 2: उपार्जित अवकाश समर्पण (PL Surrender) विंडो
# =============================================================================
elif active_page == "pl_surrender":
    st.markdown('<a href="/?page=dashboard" target="_self" class="back-btn">⬅ मुख्य डैशबोर्ड पर वापस जाएँ</a>', unsafe_allow_html=True)

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
    st.markdown("<h5 style='color:#5dade2; margin-bottom: 4px;'>२. कर्मचारी प्रविष्टि विवरण</h5>", unsafe_allow_html=True)
    
    e1, e2, e3 = st.columns(3)
    with e1:
        pl_emp_name = st.text_input("कर्मचारी का नाम:", key="w_pl_name")
        pl_app_date = st.date_input("आवेदन दिनांक:", datetime.now(), key="w_pl_app_dt")
    with e2:
        pl_desig = st.selectbox("पद (Designation):", DESIG_LIST, index=0, key="w_pl_d")
        if pl_desig == "अन्य":
            pl_desig = st.text_input("यदि 'अन्य' है तो पद लिखें:", key="w_pl_oth_d")
        pl_basic = st.number_input("मूल वेतन (Basic Pay ₹):", min_value=10000, max_value=250000, value=65000, step=100, key="w_pl_b")
    with e3:
        if "w_pl_comm" not in st.session_state:
            st.session_state.w_pl_comm = "7th Pay Commission"

        def update_da_options():
            selected_comm = st.session_state.w_pl_comm
            available_list = DA_PRESETS.get(selected_comm, DA_PRESETS["7th Pay Commission"])
            st.session_state.w_pl_da = available_list[0]

        pl_comm = st.selectbox(
            "वेतन आयोग:", 
            list(DA_PRESETS.keys()), 
            key="w_pl_comm", 
            on_change=update_da_options
        )
        
        current_das = DA_PRESETS.get(pl_comm, DA_PRESETS["7th Pay Commission"])
        
        if "w_pl_da" not in st.session_state or st.session_state.w_pl_da not in current_das:
            st.session_state.w_pl_da = current_das[0]

        pl_da = st.selectbox(
            "महंगाई भत्ता (DA %):", 
            current_das, 
            key="w_pl_da"
        )
        
        col_pl1, col_pl2 = st.columns(2)
        with col_pl1:
            pl_total = st.number_input("कुल उपार्जित अवकाश:", min_value=15, max_value=300, value=265, step=1, key="w_pl_tot")
        with col_pl2:
            pl_surr = st.selectbox("समर्पित दिन:", [15, 14, 13, 12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1], key="w_pl_surr")

    with st.form("pl_add_form"):
        submit_pl = st.form_submit_button("➕ कर्मचारी सूची में जोड़ें")
        if submit_pl:
            if not pl_emp_name.strip():
                st.error("कृपया कर्मचारी का नाम भरें!")
            elif pl_surr > pl_total:
                st.error("समर्पित अवकाश कुल अवकाश से अधिक नहीं हो सकता!")
            else:
                da_rate = float(str(pl_da).replace("%", "").strip())
                bal = pl_total - pl_surr
                b_share = round((pl_basic / 30.0) * pl_surr)
                d_share = round(((pl_basic * da_rate / 100.0) / 30.0) * pl_surr)
                tot_pay = b_share + d_share

                st.session_state.pl_employees.append({
                    "emp_name": pl_emp_name.strip(),
                    "designation": pl_desig,
                    "app_date": pl_app_date.strftime("%d/%m/%Y"),
                    "basic_pay": int(pl_basic),
                    "total_pl": int(pl_total),
                    "surrender_pl": int(pl_surr),
                    "balance_pl": int(bal),
                    "basic_share": b_share,
                    "da_share": d_share,
                    "total_payable": tot_pay
                })

                cur_off = {
                    "office_name": pl_office.strip(), "fin_year": pl_fin_year.strip(),
                    "pay_month_name": pl_month.strip(), "order_no": pl_order_no.strip(),
                    "sub_treasury": pl_treasury.strip()
                }
                save_json_data(PL_DATA_FILE, {"office_data": cur_off, "employees": st.session_state.pl_employees})
                st.success(f"कार्मिक '{pl_emp_name}' तालिका में जुड़ गया है!")
                st.rerun()

    if st.session_state.pl_employees:
        st.markdown("<hr style='border-color: #1b4f72; margin: 12px 0;'>", unsafe_allow_html=True)
        st.markdown("<h5 style='color:#2ecc71; margin-bottom: 4px;'>३. आदेश में सम्मिलित कार्मिकों की तालिका</h5>", unsafe_allow_html=True)
        
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
                    "office_name": pl_office.strip(), "fin_year": pl_fin_year.strip(),
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
                    "office_name": pl_office.strip(), "fin_year": pl_fin_year.strip(),
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

# =============================================================================
# पृष्ठ 3: सामयिक वार्षिक वेतन वृद्धि (Annual Increment) विंडो
# =============================================================================
elif active_page == "increment_order":
    st.markdown('<a href="/?page=dashboard" target="_self" class="back-btn">⬅ मुख्य डैशबोर्ड पर वापस जाएँ</a>', unsafe_allow_html=True)

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
    
    ie1, ie2, ie3 = st.columns(3)
    with ie1:
        inc_emp_name = st.text_input("अधिकारी/कार्मिक का नाम:", key="w_inc_name")
        inc_desig = st.selectbox("पद (Designation):", DESIG_LIST, index=0, key="w_inc_d")
        if inc_desig == "अन्य":
            inc_desig = st.text_input("यदि 'अन्य' है तो पद लिखें:", key="w_inc_oth_d")
    with ie2:
        inc_status = st.selectbox("स्थायी / अस्थायी:", ["स्थायी", "अस्थायी"], key="w_inc_st")
        inc_comm = st.selectbox("वेतन आयोग:", ["7th Pay Commission", "6th Pay Commission", "5th Pay Commission"], key="w_inc_comm")
        inc_level = st.selectbox("पे-लेवल (7th CPC):", [f"L-{k}" for k in range(1, 19)], index=11, key="w_inc_lvl")
    with ie3:
        inc_cur_basic = st.number_input("वर्तमान मूल वेतन (₹):", min_value=10000, max_value=250000, value=65000, step=100, key="w_inc_cb")
        inc_cur_dt = st.date_input("वर्तमान वेतनवृद्धि दिनांक:", calc_cur_date, key="w_inc_cdt")
        inc_nxt_dt = st.date_input("आगामी दिनांक:", calc_nxt_date, key="w_inc_ndt")

    auto_next_val = get_calculated_next_pay(inc_comm, inc_level, int(inc_cur_basic))
    calc_state_key = f"{inc_cur_basic}_{inc_level}_{inc_comm}"

    if st.session_state.get("last_calc_key") != calc_state_key:
        st.session_state["w_inc_nb"] = auto_next_val
        st.session_state["last_calc_key"] = calc_state_key

    inc_next_basic = st.number_input("भावी वेतन (स्वतः गणना ₹):", min_value=10000, max_value=300000, key="w_inc_nb")

    with st.form("inc_add_form"):
        st.write("")
        submit_inc = st.form_submit_button("➕ कर्मचारी सूची में जोड़ें")
        if submit_inc:
            if not inc_emp_name.strip():
                st.error("कृपया कार्मिक का नाम भरें!")
            elif inc_next_basic <= inc_cur_basic:
                st.error("भावी वेतन वर्तमान मूल वेतन से अधिक होना चाहिए!")
            else:
                st.session_state.inc_employees.append({
                    "emp_name": inc_emp_name.strip(),
                    "designation": inc_desig,
                    "service_status": inc_status,
                    "pay_level": inc_level if "7th" in inc_comm else inc_comm.split()[0],
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

# =============================================================================
# पृष्ठ 4: संचालन पोर्टल भुगतान स्वीकृति आदेश (Sanchalan Portal Sanction) विंडो
# =============================================================================
elif active_page == "sanchalan_portal":
    st.markdown('<a href="/?page=dashboard" target="_self" class="back-btn">⬅ मुख्य डैशबोर्ड पर वापस जाएँ</a>', unsafe_allow_html=True)

    if "san_bundle_loaded" not in st.session_state:
        san_bundle = load_json_data(SAN_DATA_FILE, {"office_data": {}, "items": []})
        st.session_state.san_office = san_bundle.get("office_data", {})
        st.session_state.san_items = san_bundle.get("items", [])
        st.session_state.san_bundle_loaded = True

    saved_san_off = st.session_state.san_office

    schools_data = load_json_file(MASTER_SCHOOLS_FILE, {"schools": ["राजकीय उच्च माध्यमिक विद्यालय, रोजड़ी (GSSS ROJRI)", "राजकीय उच्च प्राथमिक विद्यालय, ढाणी"]})
    vendors_data = load_json_file(MASTER_VENDORS_FILE, {"vendors": {"UPS SARPANCH KI DHANI": {"bank_name": "SBI", "account": "30389303113", "ifsc": "SBIN0011305"}}})
    
    default_beneficiaries = {
        "DEEWAN SINGH MEENA": {"account": "51069173703", "ifsc": "SBIN0031749", "bank": "STATE BANK OF INDIA"},
        "ANITA KUMARI": {"account": "51104138727", "ifsc": "SBIN0031340", "bank": "STATE BANK OF INDIA"},
        "PRABHA SHARMA": {"account": "51069165307", "ifsc": "SBIN0031749", "bank": "STATE BANK OF INDIA"},
        "Manju Jatav": {"account": "61011477170", "ifsc": "SBIN0031846", "bank": "STATE BANK OF INDIA"},
        "ALOK KUMAR SINGH": {"account": "30389303113", "ifsc": "SBIN0011305", "bank": "STATE BANK OF INDIA"},
        "BHAGWAN SAHAI JAT": {"account": "51050538187", "ifsc": "SBIN0031044", "bank": "STATE BANK OF INDIA"},
        "NARESH KUMAR KUMAWAT": {"account": "51069170496", "ifsc": "SBIN0031749", "bank": "STATE BANK OF INDIA"},
        "PRAMILA YADAV": {"account": "61032452060", "ifsc": "SBIN0031497", "bank": "STATE BANK OF INDIA"},
        "SHIMBHU SINGH": {"account": "51106211968", "ifsc": "SBIN0031788", "bank": "STATE BANK OF INDIA"},
        "PRABHU DAYAL KUMAWAT": {"account": "11346168754", "ifsc": "SBIN0000712", "bank": "STATE BANK OF INDIA"},
        "RENU BANSAL": {"account": "61236901934", "ifsc": "SBIN0032163", "bank": "STATE BANK OF INDIA"},
        "VIJENDRA KUMAR JAIMINI": {"account": "51052691600", "ifsc": "SBIN0031039", "bank": "STATE BANK OF INDIA"},
        "GANGA RAM DUKYA": {"account": "51084183156", "ifsc": "SBIN0031977", "bank": "STATE BANK OF INDIA"},
        "BHAGWATI SINGH": {"account": "61330346392", "ifsc": "SBIN0063844", "bank": "STATE BANK OF INDIA"},
        "SUNITA": {"account": "41560532725", "ifsc": "SBIN0031749", "bank": "STATE BANK OF INDIA"},
        "KANA RAM CHODHARY": {"account": "51111890475", "ifsc": "SBIN0032095", "bank": "STATE BANK OF INDIA"},
        "RAJENDRA KULHARY": {"account": "35183654160", "ifsc": "SBIN0000712", "bank": "STATE BANK OF INDIA"},
        "VIJAY PRAKASH SHARMA": {"account": "35831016552", "ifsc": "SBIN0008428", "bank": "STATE BANK OF INDIA"},
        "RAKESH KUMAR MOURYA": {"account": "52611164325", "ifsc": "SBIN0031976", "bank": "STATE BANK OF INDIA"},
        "AMIT YADAV": {"account": "61010039544", "ifsc": "SBIN0031854", "bank": "STATE BANK OF INDIA"},
        "RAHUL KUMAR": {"account": "61157960161", "ifsc": "SBIN0031990", "bank": "STATE BANK OF INDIA"},
        "MUKESH YADAV": {"account": "41729318680", "ifsc": "SBIN0031976", "bank": "STATE BANK OF INDIA"},
        "JAYANTI SINGH": {"account": "30374520419", "ifsc": "SBIN0008190", "bank": "STATE BANK OF INDIA"},
        "UDHISHTER RAJ SHARMA": {"account": "61011477170", "ifsc": "SBIN0031749", "bank": "STATE BANK OF INDIA"},
        "KIRAN KUMARI": {"account": "51100162639", "ifsc": "SBIN0031795", "bank": "STATE BANK OF INDIA"},
        "ASHUTOSH SHARMA": {"account": "61205832171", "ifsc": "SBIN0032365", "bank": "STATE BANK OF INDIA"},
        "SANJEEV KUMAR": {"account": "61057525949", "ifsc": "SBIN0031976", "bank": "STATE BANK OF INDIA"},
        "RAMESHWAR LAL DABRIA": {"account": "11346168197", "ifsc": "SBIN0000712", "bank": "STATE BANK OF INDIA"},
        "KRISHNA RANI": {"account": "61006285269", "ifsc": "SBIN0031798", "bank": "STATE BANK OF INDIA"}
    }
    beneficiaries_data = load_json_file(MASTER_BENEFICIARIES_FILE, {"beneficiaries": default_beneficiaries})

    st.markdown("""
    <div class="main-header" style="padding: 12px; margin-bottom: 15px;">
        <h2 style="color: #f4d03f; margin:0; font-size: 22px;">संचालन पोर्टल भुगतान स्वीकृति आदेश (SNA Sanction Order) मॉड्यूल</h2>
        <p style="color: #aed6f1; margin:3px 0 0 0; font-size: 12px;">समग्र शिक्षा SNA पोर्टल भुगतान स्वीकृति, पुनर्भरण (Reimbursement) एवं SEC/ELE स्वतः गणना प्रणाली</p>
    </div>
    """, unsafe_allow_html=True)

    with st.expander("⚙️ मास्टर डेटा प्रबंधन (स्कूल, वेंडर और 29 एम्प्लॉयीज बेनिफिशियरी देखें/बदले)"):
        st.markdown("<span style='color: #f4d03f; font-weight: bold;'>आप यहाँ अपनी आवश्यकतानुसार मास्टर डेटा JSON प्रारूप में अपडेट कर सकते हैं:</span>", unsafe_allow_html=True)
        
        m_col1, m_col2, m_col3 = st.columns(3)
        with m_col1:
            st.markdown("<span style='color: #2ecc71; font-weight: bold;'>विद्यालय सूची</span>", unsafe_allow_html=True)
            edit_schools = st.text_area("Schools:", value=", ".join(schools_data.get("schools", [])), height=120, key="edit_sch_ta")
        with m_col2:
            st.markdown("<span style='color: #2ecc71; font-weight: bold;'>वेंडर मास्टर डेटा</span>", unsafe_allow_html=True)
            edit_vendors = st.text_area("Vendors:", value=json.dumps(vendors_data.get("vendors", {}), ensure_ascii=False, indent=2), height=120, key="edit_ven_ta")
        with m_col3:
            st.markdown("<span style='color: #2ecc71; font-weight: bold;'>बेनिफिशियरी (29 कार्मिक)</span>", unsafe_allow_html=True)
            edit_bens = st.text_area("Beneficiaries:", value=json.dumps(beneficiaries_data.get("beneficiaries", {}), ensure_ascii=False, indent=2), height=120, key="edit_ben_ta")

        if st.button("💾 समस्त मास्टर डेटा अपडेट करें", key="btn_save_master_st"):
            try:
                s_list = [s.strip() for s in edit_schools.split(",") if s.strip()]
                save_json_file(MASTER_SCHOOLS_FILE, {"schools": s_list})
                
                v_dict = json.loads(edit_vendors)
                save_json_file(MASTER_VENDORS_FILE, {"vendors": v_dict})
                
                b_dict = json.loads(edit_bens)
                save_json_file(MASTER_BENEFICIARIES_FILE, {"beneficiaries": b_dict})
                
                st.success("मास्टर डेटा सफलतापूर्वक अपडेट हो गया है! कृपया पेज रिफ्रेश करें।")
            except Exception as e:
                st.error(f"डेटा सहेजने में विफल (JSON फॉर्मेट जांचें): {e}")

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
        st.markdown("<div style='padding-top: 10px; color:#2ecc71; font-weight:bold;'>✔ मास्टर डेटा (29 एम्प्लॉयीज) सक्रिय</div>", unsafe_allow_html=True)

    st.markdown("<hr style='border-color: #1b4f72; margin: 12px 0;'>", unsafe_allow_html=True)
    st.markdown("<h5 style='color:#5dade2; margin-bottom: 4px;'>२. भुगतान विवरण प्रविष्टि (मास्टर ऑटो-फिल समर्थित)</h5>", unsafe_allow_html=True)

    school_list = schools_data.get("schools", ["राजकीय उच्च माध्यमिक विद्यालय, रोजड़ी"])
    vendor_dict = vendors_data.get("vendors", {})
    ben_dict = beneficiaries_data.get("beneficiaries", {})

    r_col1, r_col2, r_col3 = st.columns(3)
    with r_col1:
        san_inst = st.selectbox("संस्था का नाम:", school_list, key="w_san_inst")
        san_firm = st.selectbox("फर्म/प्राप्तकर्ता का नाम:", list(vendor_dict.keys()), key="w_san_firm")
    with r_col2:
        san_reimb = st.radio("पुनर्भरण (Reimbursement):", ["No (नहीं)", "Yes (हाँ)"], horizontal=True, key="w_san_reimb_radio")
        
        san_ben = ""
        if "Yes" in san_reimb:
            san_ben = st.selectbox("बेनिफिशियरी (29 कार्मिक चुनें):", list(ben_dict.keys()), key="w_san_ben_sel")
    with r_col3:
        default_bank_str = ""
        if "Yes" in san_reimb and san_ben in ben_dict:
            b_info = ben_dict[san_ben]
            default_bank_str = f"भुगतान: {san_ben} (खाता: {b_info.get('account', '')}, IFSC: {b_info.get('ifsc', '')})"
        elif san_firm in vendor_dict:
            v_info = vendor_dict[san_firm]
            default_bank_str = f"खाता: {v_info.get('account', '')}, IFSC: {v_info.get('ifsc', '')}"

        san_bank = st.text_input("खाता संख्या व IFSC कोड:", value=default_bank_str, key="w_san_bank")
        san_bill = st.text_input("बिल/वाउचर सं. एवं दिनांक:", value="5225 / 25.08.2025", key="w_san_bill")

    r2_c1, r2_c2, r2_c3 = st.columns(3)
    with r2_c1:
        san_amt = st.number_input("राशि (₹):", min_value=1, max_value=5000000, value=56436, step=1, key="w_san_amt")
    with r2_c2:
        san_level = st.selectbox("स्तर (SEC/ELE):", ["SEC", "ELE"], key="w_san_lvl")
    with r2_c3:
        comp_opts = SNA_COMPONENTS.get(san_level, SNA_COMPONENTS["SEC"])
        san_comp = st.selectbox("कंपोनेंट चयन:", comp_opts, key="w_san_comp")

    if st.button("➕ पंक्ति तालिका में जोड़ें", key="btn_add_san_row"):
        if not san_firm.strip() or not san_bill.strip():
            st.error("कृपया फर्म का नाम और बिल संख्या अवश्य भरें!")
        else:
            reimb_status_val = f"Yes (भुगतान: {san_ben})" if "Yes" in san_reimb else "No"
            comp_rem_val = f"[{san_level}] {san_comp}"

            st.session_state.san_items.append({
                "inst": san_inst,
                "firm": san_firm,
                "bank_ifsc": san_bank,
                "bill": san_bill,
                "amount": float(san_amt),
                "reimb_status": reimb_status_val,
                "comp_rem": comp_rem_val
            })

            cur_off = {
                "office_name": san_office.strip(), "district": san_district.strip(),
                "order_no": san_order_no.strip()
            }
            save_json_data(SAN_DATA_FILE, {"office_data": cur_off, "items": st.session_state.san_items})
            st.success("भुगतान विवरण तालिका में सफलतापूर्वक जोड़ दिया गया है!")
            st.rerun()

    if st.session_state.san_items:
        st.markdown("<hr style='border-color: #1b4f72; margin: 12px 0;'>", unsafe_allow_html=True)
        st.markdown("<h5 style='color:#2ecc71; margin-bottom: 4px;'>३. दर्ज भुगतान विवरण तालिका</h5>", unsafe_allow_html=True)

        tbl_san_html = """<table class="custom-table">
        <thead><tr>
            <th>क्र.</th><th>संस्था का नाम</th><th>फर्म का नाम</th><th>खाता संख्या व IFSC कोड</th>
            <th>बिल/वाउचर सं. एवं दिनांक</th><th>राशि (₹)</th><th>पुनर्भरण</th><th>कंपोनेंट व स्तर</th>
        </tr></thead><tbody>"""
        for idx, item in enumerate(st.session_state.san_items, 1):
            tbl_san_html += f"""<tr>
                <td>{idx}</td><td>{item['inst']}</td><td style='font-weight:bold;'>{item['firm']}</td>
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
            st.write("")
            st.write("")
            if st.button("🔄 सूची खाली करें (New Order)", key="btn_clr_san"):
                st.session_state.san_items = []
                cur_off = {
                    "office_name": san_office.strip(), "district": san_district.strip(),
                    "order_no": san_order_no.strip()
                }
                save_json_data(SAN_DATA_FILE, {"office_data": cur_off, "items": []})
                st.rerun()

        short_office_name = make_short_name(san_office)
        sec_totals = {}
        ele_totals = {}
        grand_total = 0.0

        for vals in st.session_state.san_items:
            try:
                amt = float(vals['amount'])
            except:
                amt = 0.0
            grand_total += amt
            comp_info = vals['comp_rem']
            if "[SEC]" in comp_info:
                c_name = comp_info.replace("[SEC]", "").strip()
                sec_totals[c_name] = sec_totals.get(c_name, 0.0) + amt
            elif "[ELE]" in comp_info:
                c_name = comp_info.replace("[ELE]", "").strip()
                ele_totals[c_name] = ele_totals.get(c_name, 0.0) + amt

        summary_html = """
        <div style="margin-top: 10px; font-size: 11px;">
            <b>समेक्षित कंपोनेंट-वार योग (Component-wise Total Summary):</b>
            <table style="width: 100%; margin-top: 5px;">
                <tr>
                    <th>स्तर (Level)</th>
                    <th>कंपोनेंट का नाम (Component Name)</th>
                    <th>कुल राशि (₹)</th>
                </tr>
        """
        for c, t in sec_totals.items():
            summary_html += f"<tr><td><b>Secondary (SEC)</b></td><td>{c}</td><td style='text-align: right;'><b>{t:,.2f}</b></td></tr>"
        for c, t in ele_totals.items():
            summary_html += f"<tr><td><b>Elementary (ELE)</b></td><td>{c}</td><td style='text-align: right;'><b>{t:,.2f}</b></td></tr>"
        
        summary_html += f"""
                <tr style="background-color: #eaeded;">
                    <td colspan="2" style="text-align: right;"><b>कुल योग (Grand Total):</b></td>
                    <td style="text-align: right;"><b>{grand_total:,.2f}</b></td>
                </tr>
            </table>
        </div>
        """

        max_on_page1 = 7
        all_san_items = st.session_state.san_items
        page1_data = all_san_items[:max_on_page1]
        page2_data = all_san_items[max_on_page1:]

        def get_san_rows_html(subset, start_sno=1):
            h = ""
            for idx, vals in enumerate(subset, start=start_sno):
                firm_name = vals['firm']
                bank_info = vals['bank_ifsc']
                bill_info = vals['bill']
                reimb_val = vals['reimb_status']
                comp_info = vals['comp_rem']

                if "Yes" in reimb_val:
                    bank_info += f"<br><b style='color:#c0392b;'>चूंकि उक्त बिल संख्या {bill_info} का भुगतान बेनिफिशियरी द्वारा फर्म को किया जा चुका है, अतः इस समस्त राशि का भुगतान सीधे बेनिफिशियरी को किया जा रहा है।</b>"

                h += f"""
                        <tr>
                            <td>{idx}</td>
                            <td>{vals['inst']}</td>
                            <td>{firm_name}</td>
                            <td>{bank_info}</td>
                            <td>{bill_info}</td>
                            <td>{vals['amount']:,.2f}</td>
                            <td>{reimb_val}</td>
                            <td>{comp_info}</td>
                        </tr>
                """
            return h

        page1_rows = get_san_rows_html(page1_data, 1)
        developer_text = "सॉफ्टवेयर डेवलपर: आलोक कुमार सिंह, वरिष्ठ अध्यापक, राजकीय उच्च माध्यमिक विद्यालय, रोजड़ी | ईमेल: alokjobner@gmail.com"

        if not page2_data:
            san_html = f"""<!DOCTYPE html><html><head><meta charset='UTF-8'><title>Sanchalan Payment Sanction Order</title>
            <style>
                @page {{ size: A4 landscape; margin: 6mm; }}
                body {{ font-family: 'Arial', sans-serif; margin: 0; padding: 0; background: #fff; color: #000; }}
                .page-box {{ border: 3px solid black; padding: 12px 15px; width: 100%; box-sizing: border-box; min-height: 92vh; position: relative; }}
                .header {{ text-align: center; font-weight: bold; margin-bottom: 5px; }}
                .header h3, .header h2, .header h4 {{ margin: 2px 0; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 8px; }}
                th, td {{ border: 1px solid black; padding: 4px 6px; text-align: center; font-size: 11px; }}
                th {{ background-color: #f2f2f2; }}
                .signature-section {{ margin-top: 15px; width: 100%; text-align: right; }}
                .signature-box {{ display: inline-block; text-align: center; font-size: 12px; line-height: 1.2; }}
                .copy-section {{ margin-top: 12px; font-size: 11px; }}
                .page-footer-info {{ position: absolute; bottom: 8px; left: 15px; font-size: 9px; font-style: italic; color: #333; }}
                .page-number {{ position: absolute; bottom: 8px; right: 15px; font-size: 10px; font-weight: bold; }}
            </style></head><body>
            <div class='page-box'>
                <div class='header'>
                    <h3>कार्यालय {san_office}</h3>
                    <h4>जिला : {san_district}</h4>
                    <br>
                    <h2>भुगतान स्वीकृति आदेश</h2>
                </div>
                
                <p style="margin: 4px 0;"><b>क्रमांक:</b> {san_order_no} <span style="float: right;"><b>दिनांक:</b> {san_order_date.strftime('%d/%m/%Y')}</span></p>
                
                <p style="text-align: justify; line-height: 1.2; font-size: 11px; margin: 4px 0;">
                राजस्थान स्कूल शिक्षा परिषद जयपुर द्वारा प्रदत्त निर्देशानुसार संचालन पोर्टल से भुगतान किये जाने की प्रक्रिया के अन्तर्गत स्थानीय विद्यालय / अधोहस्ताक्षरकर्ता के नियंत्रणाधीन संबंधित संस्थाओं हेतु जारी मद में जारी संचालन पोर्टल लिमिट से सम्बन्धित वेंडर / बेनिफिशियरी को निम्नानुसार भुगतान किये जाने की स्वीकृति प्रदान की जाती है:-
                </p>
                
                <table>
                    <tr>
                        <th>क.स.</th><th>संस्था का नाम</th><th>फर्म का नाम / प्राप्तकर्ता</th>
                        <th>खाता संख्या व IFSC कोड / विशिष्ट टिप्पणी</th><th>बिल/वाउचर सं. एवं दिनांक</th>
                        <th>राशि (₹)</th><th>पुनर्भरण</th><th>कंपोनेंट व स्तर (SEC/ELE)</th>
                    </tr>
                    {page1_rows}
                </table>

                {summary_html}
                
                <div class='signature-section'>
                    <div class='signature-box'>
                        <b>हस्ताक्षर मय सील</b><br>प्रधानाचार्य / पीईईओ<br>{short_office_name}
                    </div>
                </div>
                
                <div class='copy-section'>
                    <p style="margin: 2px 0;"><b>क्रमांक:</b> {san_order_no} <span style="float: right;"><b>दिनांक:</b> {san_order_date.strftime('%d/%m/%Y')}</span></p>
                    <p style="margin: 2px 0;"><b>प्रतिलिपि :- सूचनार्थ एवं आवश्यक कार्यवाही हेतु प्रेषित :-</b></p>
                    <ol style="margin: 2px 0; padding-left: 18px; line-height: 1.2;">
                        <li>रोकड / लेखा शाखा स्थानीय विद्यालय।</li>
                        <li>संबंधित संस्था प्रधान की ओर सूचनार्थ।</li>
                        <li>कार्यालय प्रति ।</li>
                    </ol>
                    <div style="text-align: right; margin-top: 5px;">
                        <div class='signature-box'>
                            <b>हस्ताक्षर मय सील</b><br>प्रधानाचार्य / पीईईओ<br>{short_office_name}
                        </div>
                    </div>
                </div>

                <div class='page-footer-info'>{developer_text}</div>
                <div class='page-number'>Page 1 of 1</div>
            </div>
            </body></html>"""
        else:
            page2_rows = get_san_rows_html(page2_data, max_on_page1 + 1)
            san_html = f"""<!DOCTYPE html><html><head><meta charset='UTF-8'><title>Sanchalan Payment Sanction Order</title>
            <style>
                @page {{ size: A4 landscape; margin: 6mm; }}
                body {{ font-family: 'Arial', sans-serif; margin: 0; padding: 0; background: #fff; color: #000; }}
                .page-box {{ border: 3px solid black; padding: 12px 15px; width: 100%; box-sizing: border-box; min-height: 92vh; position: relative; }}
                .header {{ text-align: center; font-weight: bold; margin-bottom: 5px; }}
                .header h3, .header h2, .header h4 {{ margin: 2px 0; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 8px; }}
                th, td {{ border: 1px solid black; padding: 4px 6px; text-align: center; font-size: 11px; }}
                th {{ background-color: #f2f2f2; }}
                .signature-section {{ margin-top: 15px; width: 100%; text-align: right; }}
                .signature-box {{ display: inline-block; text-align: center; font-size: 12px; line-height: 1.2; }}
                .copy-section {{ margin-top: 12px; font-size: 11px; }}
                .page-footer-info {{ position: absolute; bottom: 8px; left: 15px; font-size: 9px; font-style: italic; color: #333; }}
                .page-number {{ position: absolute; bottom: 8px; right: 15px; font-size: 10px; font-weight: bold; }}
            </style></head><body>
            <!-- PAGE 1 -->
            <div class='page-box'>
                <div class='header'>
                    <h3>कार्यालय {san_office}</h3>
                    <h4>जिला : {san_district}</h4>
                    <br>
                    <h2>भुगतान स्वीकृति आदेश</h2>
                </div>
                
                <p style="margin: 4px 0;"><b>क्रमांक:</b> {san_order_no} <span style="float: right;"><b>दिनांक:</b> {san_order_date.strftime('%d/%m/%Y')}</span></p>
                
                <p style="text-align: justify; line-height: 1.2; font-size: 11px; margin: 4px 0;">
                राजस्थान स्कूल शिक्षा परिषद जयपुर द्वारा प्रदत्त निर्देशानुसार संचालन पोर्टल से भुगतान किये जाने की प्रक्रिया के अन्तर्गत स्थानीय विद्यालय / अधोहस्ताक्षरकर्ता के नियंत्रणाधीन संबंधित संस्थाओं हेतु जारी मद में जारी संचालन पोर्टल लिमिट से सम्बन्धित वेंडर / बेनिफिशियरी को निम्नानुसार भुगतान किये जाने की स्वीकृति प्रदान की जाती है:-
                </p>
                
                <table>
                    <tr>
                        <th>क.स.</th><th>संस्था का नाम</th><th>फर्म का नाम / प्राप्तकर्ता</th>
                        <th>खाता संख्या व IFSC कोड / विशिष्ट टिप्पणी</th><th>बिल/वाउचर सं. एवं दिनांक</th>
                        <th>राशि (₹)</th><th>पुनर्भरण</th><th>कंपोनेंट व स्तर (SEC/ELE)</th>
                    </tr>
                    {page1_rows}
                </table>
                <div class='page-footer-info'>{developer_text}</div>
                <div class='page-number'>Page 1 of 2</div>
            </div>

            <!-- PAGE 2 -->
            <div class='page-box'>
                <table>
                    <tr>
                        <th>क.स.</th><th>संस्था का नाम</th><th>फर्म का नाम / प्राप्तकर्ता</th>
                        <th>खाता संख्या व IFSC कोड / विशिष्ट टिप्पणी</th><th>बिल/वाउचर सं. एवं दिनांक</th>
                        <th>राशि (₹)</th><th>पुनर्भरण</th><th>कंपोनेंट व स्तर (SEC/ELE)</th>
                    </tr>
                    {page2_rows}
                </table>

                {summary_html}
                
                <div class='signature-section'>
                    <div class='signature-box'>
                        <b>हस्ताक्षर मय सील</b><br>प्रधानाचार्य / पीईईओ<br>{short_office_name}
                    </div>
                </div>
                
                <div class='copy-section'>
                    <p style="margin: 2px 0;"><b>क्रमांक:</b> {san_order_no} <span style="float: right;"><b>दिनांक:</b> {san_order_date.strftime('%d/%m/%Y')}</span></p>
                    <p style="margin: 2px 0;"><b>प्रतिलिपि :- सूचनार्थ एवं आवश्यक कार्यवाही हेतु प्रेषित :-</b></p>
                    <ol style="margin: 2px 0; padding-left: 18px; line-height: 1.2;">
                        <li>रोकड / लेखा शाखा स्थानीय विद्यालय।</li>
                        <li>संबंधित संस्था प्रधान की ओर सूचनार्थ।</li>
                        <li>कार्यालय प्रति ।</li>
                    </ol>
                    <div style="text-align: right; margin-top: 5px;">
                        <div class='signature-box'>
                            <b>हस्ताक्षर मय सील</b><br>प्रधानाचार्य / पीईईओ<br>{short_office_name}
                        </div>
                    </div>
                </div>

                <div class='page-footer-info'>{developer_text}</div>
                <div class='page-number'>Page 2 of 2</div>
            </div>
            </body></html>"""

        st.download_button(
            label="✨ संचालन पोर्टल आदेश जनरेट करें (PDF / Print Preview) 🖨",
            data=san_html,
            file_name=f"Sanchalan_Sanction_Order_{datetime.now().strftime('%Y%m%d')}.html",
            mime="text/html"
        )

# =============================================================================
# पृष्ठ 5: वेतन एरियर (Salary Arrear) गणना एवं अंतर विवरण प्रपत्र मॉड्यूल (7th CPC Landscape Final Fixes)
# =============================================================================
elif active_page == "salary_arrear":
    # IMPORTANT: The arrear calculation engine is intentionally kept outside
    # app.py. This page only collects UI inputs, calls calculate_arrear(), and
    # renders the returned data. Other modules/pages are left untouched.
    st.markdown('<a href="/?page=dashboard" target="_self" class="back-btn">⬅ मुख्य डैशबोर्ड पर वापस जाएँ</a>', unsafe_allow_html=True)

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

    e_c1, e_c2, e_c3 = st.columns(3)
    with e_c1:
        arr_emp_name = st.text_input("कर्मचारी का नाम:", key="w_arr_name")
        arr_emp_id = st.text_input("Employee ID:", key="w_arr_emp_id")
        arr_desig = st.selectbox("पद (Designation):", DESIG_LIST, key="w_arr_desig")
        arr_pan = st.text_input("PAN Number:", value="ABCDE1234F", key="w_arr_pan")
    with e_c2:
        arr_bank = st.selectbox("बैंक का नाम:", NATIONALIZED_BANKS, index=0, key="w_arr_bank")
        arr_acc = st.text_input("Account Number:", value="30389303113", key="w_arr_acc")
        arr_ifsc = st.text_input("IFSC Code:", value="SBIN0011305", key="w_arr_ifsc")
    with e_c3:
        arr_start_dt = st.date_input("एरियर प्रारंभ / वास्तविक प्रभावित (प्रभावी) दिनांक:", datetime(2025, 3, 15), key="w_arr_sdt")
        arr_end_dt = st.date_input("एरियर समाप्ति दिनांक (To):", datetime(2026, 6, 30), key="w_arr_edt")
        city_cat = st.selectbox("शहर श्रेणी (HRA हेतु):", ["Classified (जयपुर, जोधपुर आदि)", "Other Places (अन्य स्थान)"], key="w_arr_city")

    level_change_reason = any(x in arr_reason for x in ["Promotion", "ACP / MACP"])
    pay_fixation_reason = "Pay Fixation" in arr_reason
    old_level = new_level = None

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
        pc1, pc2 = st.columns(2)
        with pc1:
            old_level = st.selectbox("पूर्व Pay Level:", [f"L-{k}" for k in range(1, 19)], index=10, key="w_arr_old_level")
        with pc2:
            new_level = st.selectbox("पश्चात Pay Level:", [f"L-{k}" for k in range(1, 19)], index=11, key="w_arr_new_level")
    else:
        pay_lvl_input = st.selectbox("Pay Level:", [f"L-{k}" for k in range(1, 19)], index=11, key="w_arr_plvl")
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

    if level_change_reason and old_level == new_level:
        st.info("ACP / MACP में Pay Level समान है — प्रारंभिक देय वेतन उसी Level की अगली Pay Matrix Cell से स्वतः निर्धारित होगा।")
    elif level_change_reason and old_level != new_level:
        st.info("Promotion/ACP-MACP में Pay Level बदला है — पहले पूर्व Level में एक Increment, फिर पश्चात Level में उससे अगली उच्च Cell पर Pay Fixation होगा।")

    st.markdown("<h5 style='color:#f39c12;margin-top:15px;margin-bottom:4px;'>३. मूल वेतन, Increment एवं मासिक कटौतियाँ</h5>", unsafe_allow_html=True)
    m_c1, m_c2, m_c3, m_c4 = st.columns(4)
    with m_c1:
        drawn_basic_def = st.number_input("प्रारंभिक आहरित मूल वेतन (पूर्व Level) ₹:", min_value=0, value=65000, step=100, key="w_arr_db")

        auto_fixation_reason = level_change_reason
        auto_due_basic = get_initial_due_basic(
            reason=arr_reason,
            old_level=old_level,
            new_level=new_level,
            drawn_basic=int(drawn_basic_def),
            pay_matrix=PAY_MATRIX_7TH,
        )
        auto_due_state_key = f"{arr_reason}|{old_level}|{new_level}|{int(drawn_basic_def)}"
        if st.session_state.get("w_arr_dub_auto_state_key") != auto_due_state_key:
            st.session_state["w_arr_dub_auto"] = int(auto_due_basic)
            st.session_state["w_arr_dub_auto_state_key"] = auto_due_state_key
        if auto_fixation_reason:
            due_basic_def = st.number_input(
                "प्रारंभिक देय मूल वेतन (स्वतः Pay Fixation) ₹:",
                min_value=0,
                value=int(auto_due_basic),
                step=100,
                disabled=True,
                key="w_arr_dub_auto"
            )
            st.caption("यह राशि Promotion/ACP-MACP के Pay Fixation नियम से स्वतः निर्धारित है; इसमें manual बदलाव नहीं किया जा सकता।")
        else:
            due_basic_def = st.number_input(
                "प्रारंभिक देय मूल वेतन (पश्चात Level) ₹:",
                min_value=0,
                value=67000,
                step=100,
                key="w_arr_dub_manual"
            )
    with m_c2:
        st.markdown("**GPF**")
        drawn_gpf_m = st.number_input("मासिक आहरित GPF (₹):", min_value=0, value=2850, step=50, key="w_arr_dgpf")
        due_gpf_auto = get_gpf_minimum_for_basic(int(due_basic_def))
        gpf_due_display = st.number_input("मासिक देय GPF (slab minimum) ₹:", min_value=0, value=due_gpf_auto, step=50, key="w_arr_dugpf")
    with m_c3:
        st.markdown("**SI**")
        drawn_si_m = st.number_input("मासिक आहरित SI (₹):", min_value=0, value=3000, step=500, key="w_arr_dsi")
        si_options = get_si_options_for_basic(int(due_basic_def))
        default_si = si_options[0] if 3000 not in si_options else 3000
        due_si_m = st.selectbox("मासिक देय SI (slab विकल्प):", si_options, index=si_options.index(default_si), key="w_arr_dusi")
    with m_c4:
        st.markdown("**RGHS**")
        drawn_rghs_m = st.number_input("मासिक आहरित RGHS (₹):", min_value=0, value=get_rghs_deduction_for_basic(int(due_basic_def)), step=50, key="w_arr_drghs")
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
                st.success(f"कार्मिक '{arr_emp_name}' का माह-वार एरियर सफलतापूर्वक गणना कर लिया गया है।")
                st.rerun()

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

            header_block = "" if not is_first else f"""
              <div class='header'>
                <div class='office-title'>{arr_office}</div>
                <div class='form-title'>अंतर विवरण प्रपत्र — वेतन एरियर</div>
                <div class='info-grid'>
                  <span><b>कर्मचारी का नाम:</b> {emp.get('emp_name','')}</span><span><b>एम्प्लॉय आईडी:</b> {emp.get('employee_id','—')}</span>
                  <span><b>पद:</b> {emp.get('designation','')}</span><span><b>PAN:</b> {emp.get('pan','')}</span>
                  <span><b>खाता संख्या:</b> {emp.get('account','')} ({emp.get('bank','')})</span><span><b>एरियर अवधि:</b> {emp.get('start_date','')} से {emp.get('end_date','')}</span>
                  <span><b>एरियर बनाने का कारण:</b> {emp.get('reason','')}</span><span><b>Pay Level:</b> {emp.get('old_pay_level','-')} → {emp.get('new_pay_level','-')}</span>
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

        st.download_button(
            label=f"✨ '{emp.get('emp_name','')}' का पूर्ण माह-वार एरियर प्रपत्र (PDF/Print) डाउनलोड करें 🖨",
            data=arrear_html,
            file_name=f"Arrear_Statement_Final_{emp.get('emp_name','employee').replace(' ','_')}.html",
            mime="text/html"
        )
