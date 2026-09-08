import streamlit as st
import base64
import math
import os
import json
from datetime import datetime

# 1. पेज कॉन्फ़िगरेशन
st.set_page_config(
    page_title="राजस्थान गवर्नमेंट ऑफिस ऑर्डर जनरेटर सॉफ्टवेयर",
    page_icon="📜",
    layout="wide"
)

# 2. डेटा फ़ाइल पाथ्स एवं ऑटो-लोडिंग लॉजिक
PL_DATA_FILE = os.path.join("output", "saved_pl_data.json")
INC_DATA_FILE = os.path.join("output", "saved_increment_data.json")

def load_json_data(file_path):
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"office_data": {}, "employees": []}
    return {"office_data": {}, "employees": []}

def save_json_data(file_path, office_data, employees):
    os.makedirs("output", exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump({"office_data": office_data, "employees": employees}, f, ensure_ascii=False, indent=2)

# 3. ग्लोबल डेटा डेफिनिशन
DESIG_LIST = [
    "वरिष्ठ अध्यापक", "प्रधानाचार्य", "उप प्रधानाचार्य", "व्याख्याता", 
    "अध्यापक लेवल 2", "अध्यापक लेवल 1", "शारीरिक शिक्षक", "पुस्तकालय अध्यक्ष", 
    "सहायक प्रशासनिक अधिकारी", "कनिष्ठ लिपिक", "चतुर्थ श्रेणी कर्मचारी", "अन्य"
]

DA_PRESETS = {
    "7th Pay Commission": ["58%", "55%", "53%", "50%", "46%", "42%", "38%", "34%", "31%", "28%", "17%", "12%", "9%", "7%", "5%", "4%", "2%", "0%"],
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

def get_calculated_next_pay(comm, lvl, cur_b):
    if "7th" in comm:
        col = PAY_MATRIX_7TH.get(lvl, [])
        if cur_b in col:
            idx = col.index(cur_b)
            return col[min(idx + 1, len(col) - 1)]
        else:
            for step in col:
                if step > cur_b:
                    return step
            return col[-1] if col else cur_b
    elif "6th" in comm:
        inc = round(cur_b * 0.03)
        rem = (cur_b + inc) % 10
        return (cur_b + inc) if rem == 0 else (cur_b + inc + (10 - rem))
    else:
        return cur_b + round(cur_b * 0.03)

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

# यूनिवर्सल CSS: सभी बटनों को पूर्ण रंगीन एवं दृश्यमान बनाना
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

    /* सभी लेबल्स */
    label, [data-testid="stWidgetLabel"] p, [data-testid="stWidgetLabel"] span {
        color: #f4d03f !important;
        font-size: 14.5px !important;
        font-weight: bold !important;
        opacity: 1 !important;
    }

    /* इनपुट बॉक्स */
    input, select, [data-baseweb="select"] {
        background-color: #1c3b60 !important;
        color: #ffffff !important;
        font-weight: bold !important;
        border: 1px solid #2e5b88 !important;
        border-radius: 6px !important;
    }

    /* 3D मेनू बटन */
    .menu-btn-pl {
        display: block; width: 100%; background-color: #1f618d; color: #ffffff !important;
        text-decoration: none !important; padding: 15px 20px; font-size: 17px; font-weight: bold;
        border-radius: 8px; border: 2px solid #2980b9; box-shadow: 0 5px 0 #154360; margin-bottom: 14px; text-align: left;
    }
    .menu-btn-pl:hover { background-color: #2980b9; }

    .menu-btn-inc {
        display: block; width: 100%; background-color: #27ae60; color: #ffffff !important;
        text-decoration: none !important; padding: 15px 20px; font-size: 17px; font-weight: bold;
        border-radius: 8px; border: 2px solid #2ecc71; box-shadow: 0 5px 0 #1e8449; margin-bottom: 14px; text-align: left;
    }
    .menu-btn-inc:hover { background-color: #2ecc71; }

    .menu-btn-rel {
        display: block; width: 100%; background-color: #212f3d; color: #a6acaf !important;
        text-decoration: none !important; padding: 13px 20px; font-size: 15px; border-radius: 8px;
        border: 1px solid #34495e; box-shadow: 0 4px 0 #17202a; text-align: left;
    }

    .back-btn {
        display: inline-block; background-color: #c0392b; color: #ffffff !important;
        text-decoration: none !important; padding: 8px 18px; font-size: 14px; font-weight: bold;
        border-radius: 6px; border: 1px solid #e74c3c; margin-bottom: 15px;
    }
    .back-btn:hover { background-color: #e74c3c; }

    /* ========================================================== */
    /* सभी एक्शन बटनों को जबरन रंगीन बनाना (सफेद बटन की छुट्टी) */
    /* ========================================================== */
    
    /* 1. हरा बटन (कर्मचारी जोड़ें) */
    div[data-testid="stFormSubmitButton"] > button {
        background-color: #27ae60 !important;
        background: #27ae60 !important;
        border: 2px solid #2ecc71 !important;
        box-shadow: 0 4px 0 #1e8449 !important;
        width: 100% !important;
        padding: 12px !important;
    }
    div[data-testid="stFormSubmitButton"] > button * {
        color: #ffffff !important;
        font-size: 16px !important;
        font-weight: bold !important;
    }
    div[data-testid="stFormSubmitButton"] > button:hover { background-color: #2ecc71 !important; }

    /* 2. लाल बटन (चयनित हटाएं) - Streamlit सामान्य बटन ओवरराइड */
    div.stButton:nth-of-type(1) > button {
        background-color: #c0392b !important;
        background: #c0392b !important;
        color: #ffffff !important;
        border: 2px solid #e74c3c !important;
        box-shadow: 0 4px 0 #922b21 !important;
    }

    /* 3. ग्रे बटन (सूची खाली करें) */
    div.stButton:nth-of-type(2) > button {
        background-color: #7f8c8d !important;
        background: #7f8c8d !important;
        color: #ffffff !important;
        border: 2px solid #95a5a6 !important;
        box-shadow: 0 4px 0 #616a6b !important;
    }

    /* यूनिवर्सल बटन टेक्स्ट सुरक्षा */
    div.stButton > button, div.stButton > button * {
        color: #ffffff !important;
        font-weight: bold !important;
    }

    /* 4. नारंगी बटन (आदेश जनरेट करें) */
    div[data-testid="stDownloadButton"] > button {
        background-color: #d35400 !important;
        background: #d35400 !important;
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
    div[data-testid="stDownloadButton"] > button:hover { background-color: #e67e22 !important; }

    /* टेबल स्टाइल */
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

# 7. स्क्रीन नेविगेशन
params = st.query_params
active_page = params.get("page", "dashboard")

# =============================================================================
# पृष्ठ 1: मुख्य डैशबोर्ड
# =============================================================================
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
            <span style="color: #2ecc71;">✔ वर्तमान क्षमताएं:</span> उपार्जित अवकाश (PL Surrender) की सटीक नियमानुसार ऑटो-कैलकुलेशन, वार्षिक सामयिक वेतन वृद्धि (Annual Increment - जनवरी एवं जुलाई चक्र) आदेश 7th CPC पे-मैट्रिक्स अनुसार स्वतः गणना, मल्टीपल कार्मिक प्रविष्टि, A4 सटीक बॉर्डर प्रिंट आदेश।<br>
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
        <div class="menu-btn-rel">
            3. कार्यमुक्ति / कार्यग्रहण (Relieving / Joining) आदेश [शीघ्र उपलब्ध]
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
    
    with st.form("pl_add_form"):
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
            pl_comm = st.selectbox("वेतन आयोग:", list(DA_PRESETS.keys()), key="w_pl_comm")
            pl_da = st.selectbox("महंगाई भत्ता (DA %):", DA_PRESETS[pl_comm], key="w_pl_da")
            col_pl1, col_pl2 = st.columns(2)
            with col_pl1:
                pl_total = st.number_input("कुल उपार्जित अवकाश:", min_value=15, max_value=300, value=265, step=1, key="w_pl_tot")
            with col_pl2:
                pl_surr = st.selectbox("समर्पित दिन:", [15, 14, 13, 12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1], key="w_pl_surr")

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
                save_json_data(PL_DATA_FILE, cur_off, st.session_state.pl_employees)
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
                save_json_data(PL_DATA_FILE, cur_off, st.session_state.pl_employees)
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
                save_json_data(PL_DATA_FILE, cur_off, [])
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
          .office-header {{ text-align: center; margin-bottom: 6px; }}
          .office-title {{ font-size: 15pt; font-weight: bold; text-decoration: underline; margin-bottom: 4px; }}
          .order-title {{ font-size: 13pt; font-weight: bold; margin-bottom: 10px; }}
          .order-body {{ text-align: justify; text-indent: 35px; font-size: 10.5pt; line-height: 1.65; margin-bottom: 10px; }}
          table {{ width: 100%; border-collapse: collapse; margin: 6px 0 12px 0; font-size: 9pt; }}
          th, td {{ border: 1px solid #000; padding: 4px 2px; text-align: center; }}
          th {{ background-color: #f2f2f2; font-weight: bold; }}
          .cert-text {{ font-size: 10pt; line-height: 1.55; margin: 10px 0 8px 0; text-align: justify; }}
          .sig-container {{ width: 100%; display: flex; justify-content: flex-end; margin-bottom: 10px; }}
          .sig-box {{ text-align: center; min-width: 230px; line-height: 1.35; }}
          .sig-space {{ height: 48px; }}
          .dispatch-section {{ border-top: 1px dashed #777; padding-top: 8px; margin-top: 6px; }}
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
                save_json_data(INC_DATA_FILE, cur_off, st.session_state.inc_employees)
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
            st.markdown('<div class="del-btn-container">', unsafe_allow_html=True)
            if st.button("🗑 चयनित कार्मिक हटाएं", key="btn_del_inc"):
                del st.session_state.inc_employees[del_inc_idx - 1]
                cur_off = {
                    "office_name": inc_office.strip(), "inc_year": str(inc_year),
                    "inc_cycle": inc_cycle.strip(), "order_no": inc_order_no.strip(),
                    "sub_treasury": inc_treasury.strip()
                }
                save_json_data(INC_DATA_FILE, cur_off, st.session_state.inc_employees)
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        with ib_col2:
            st.write("")
            st.write("")
            st.markdown('<div class="clr-btn-container">', unsafe_allow_html=True)
            if st.button("🔄 सूची खाली करें (New Order)", key="btn_clr_inc"):
                st.session_state.inc_employees = []
                cur_off = {
                    "office_name": inc_office.strip(), "inc_year": str(inc_year),
                    "inc_cycle": inc_cycle.strip(), "order_no": inc_order_no.strip(),
                    "sub_treasury": inc_treasury.strip()
                }
                save_json_data(INC_DATA_FILE, cur_off, [])
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

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
          .office-header {{ text-align: center; margin-bottom: 6px; }}
          .office-title {{ font-size: 15pt; font-weight: bold; text-decoration: underline; margin-bottom: 4px; }}
          .order-title {{ font-size: 13pt; font-weight: bold; margin-bottom: 8px; }}
          .order-body {{ text-align: justify; text-indent: 30px; font-size: 10pt; line-height: 1.6; margin-bottom: 8px; }}
          table {{ width: 100%; border-collapse: collapse; margin: 6px 0 12px 0; font-size: 9pt; }}
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
          <div class='sig-container'><div class='sig-box'><div class='sig-space'></div><div style='font-weight:bold;'>हस्ताक्षर कार्यालय अध्यक्ष</div><div style='font-size:9pt;(मोहर सहित)</div></div></div>
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