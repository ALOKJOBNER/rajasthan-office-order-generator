import os
import json
import hashlib
import streamlit as st

USERS_FILE = "users_db.json"

def load_users():
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("users", {})
        except Exception:
            return {}
    return {}

def save_users(users_dict):
    os.makedirs(".", exist_ok=True)
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump({"users": users_dict}, f, ensure_ascii=False, indent=4)

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def register_user(username, password, full_name, email):
    users = load_users()
    if username in users:
        return False, "⚠️ यह User ID पहले से मौजूद है। कृपया दूसरी ID चुनें।"
    
    users[username] = {
        "password": hash_password(password),
        "full_name": full_name,
        "email": email
    }
    save_users(users)
    return True, "✅ रजिस्ट्रेशन सफल रहा! अब आप लॉगिन कर सकते हैं।"

def verify_user(username, password):
    users = load_users()
    if username in users:
        if users[username]["password"] == hash_password(password):
            return True, "🎉 लॉगिन सफल!"
    return False, "❌ गलत User ID या Password!"

def recover_username(full_name, email):
    users = load_users()
    for uname, details in users.items():
        if details.get("full_name", "").strip().lower() == full_name.strip().lower() and details.get("email", "").strip().lower() == email.strip().lower():
            return True, f"🔍 आपका User ID है: {uname}"
    return False, "❌ दर्ज किए गए विवरण से कोई User ID नहीं मिला।"

def reset_password(username, email, new_password):
    users = load_users()
    if username in users:
        if users[username].get("email", "").strip().lower() == email.strip().lower():
            users[username]["password"] = hash_password(new_password)
            save_users(users)
            return True, "✅ पासवर्ड सफलतापूर्वक बदल दिया गया है!"
        else:
            return False, "❌ User ID और Email ID आपस में मैच नहीं हो रहे हैं।"
    return False, "❌ यह User ID सिस्टम में मौजूद नहीं है।"

def render_auth_portal():
    """यह फंक्शन सॉफ्टवेयर की थीम से मैच करता हुआ आकर्षक और स्पष्ट लॉगिन इंटरफेस रेंडर करता है"""
    
    # CSS स्टाइलिंग ताकि बटन्स और टेक्स्ट पूरी तरह स्पष्ट और कलरफुल दिखें
    st.markdown("""
    <style>
        .auth-card {
            max-width: 500px;
            margin: 40px auto;
            background-color: #132743;
            padding: 30px;
            border-radius: 14px;
            border: 2px solid #f4d03f;
            box-shadow: 0 0 25px rgba(0,0,0,0.8);
            color: #ffffff;
        }
        /* फॉर्म के बटन्स और टेक्स्ट के बीच साफ कंट्रास्ट */
        div[data-testid="stFormSubmitButton"] > button {
            background-color: #27ae60 !important;
            color: #ffffff !important;
            font-weight: bold !important;
            border: 2px solid #2ecc71 !important;
            border-radius: 6px !important;
            width: 100% !important;
            padding: 10px !important;
            box-shadow: 0 4px 0 #1e8449 !important;
        }
        div[data-testid="stFormSubmitButton"] > button * {
            color: #ffffff !important;
            font-size: 16px !important;
        }
    </style>
    """, unsafe_allow_html=True)

    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "logged_in_user" not in st.session_state:
        st.session_state.logged_in_user = ""

    if not st.session_state.authenticated:
        st.markdown("""
        <div class="auth-card">
            <h2 style="color: #f4d03f; text-align: center; margin: 0; font-size: 24px;">🔐 सॉफ्टवेयर सुरक्षा पोर्टल</h2>
            <p style="color: #aed6f1; text-align: center; font-size: 13px; margin-top: 5px; font-style: italic;">
                राजस्थान गवर्नमेंट ऑफिस ऑर्डर जनरेटर सॉफ्टवेयर
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        tab1, tab2, tab3, tab4 = st.tabs(["🔑 Login", "📝 Register", "❓ Forgot Password", "👤 Forgot Username"])
        
        with tab1:
            st.markdown("<p style='color: #5dade2; font-weight: bold;'>अपने क्रेडेंशियल से लॉगिन करें:</p>", unsafe_allow_html=True)
            with st.form("login_form_main"):
                l_user = st.text_input("User ID / Username")
                l_pass = st.text_input("Password", type="password")
                l_sub = st.form_submit_button("🚀 लॉगिन करें")
                if l_sub:
                    success, msg = verify_user(l_user, l_pass)
                    if success:
                        st.session_state.authenticated = True
                        st.session_state.logged_in_user = l_user
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)
                        
        with tab2:
            st.markdown("<p style='color: #2ecc71; font-weight: bold;'>नया खाता बनाएं:</p>", unsafe_allow_html=True)
            with st.form("reg_form_main"):
                r_user = st.text_input("नया User ID चुनें")
                r_pass = st.text_input("Password चुनें", type="password")
                r_name = st.text_input("पूरा नाम (Full Name)")
                r_email = st.text_input("Email ID (रिकवरी हेतु)")
                r_sub = st.form_submit_button("✨ रजिस्टर करें")
                if r_sub:
                    if not r_user or not r_pass or not r_name or not r_email:
                        st.error("⚠️ कृपया सभी फील्ड्स भरें!")
                    else:
                        success, msg = register_user(r_user, r_pass, r_name, r_email)
                        if success:
                            st.success(msg)
                        else:
                            st.error(msg)
                            
        with tab3:
            st.markdown("<p style='color: #f39c12; font-weight: bold;'>पासवर्ड रीसेट करें:</p>", unsafe_allow_html=True)
            with st.form("fp_form_main"):
                fp_user = st.text_input("अपना User ID दर्ज करें")
                fp_email = st.text_input("पंजीकृत Email ID दर्ज करें")
                fp_new = st.text_input("नया Password दर्ज करें", type="password")
                fp_sub = st.form_submit_button("🔄 पासवर्ड बदलें")
                if fp_sub:
                    success, msg = reset_password(fp_user, fp_email, fp_new)
                    if success:
                        st.success(msg)
                    else:
                        st.error(msg)
                        
        with tab4:
            st.markdown("<p style='color: #e74c3c; font-weight: bold;'>यूजर आईडी का पता लगाएं:</p>", unsafe_allow_html=True)
            with st.form("fu_form_main"):
                fu_name = st.text_input("अपना पूरा नाम दर्ज करें")
                fu_email = st.text_input("पंजीकृत Email ID दर्ज करें")
                fu_sub = st.form_submit_button("🔍 यूजर आईडी खोजें")
                if fu_sub:
                    success, msg = recover_username(fu_name, fu_email)
                    if success:
                        st.success(msg)
                    else:
                        st.error(msg)
        st.stop()
    else:
        # लॉगिन के बाद साइडबार में यूजर का नाम और लॉगआउट बटन
        with st.sidebar:
            st.markdown(f"""
            <div style="background-color: #132743; padding: 10px; border-radius: 6px; border: 1px solid #f4d03f; text-align: center; margin-bottom: 10px;">
                <p style="color: #f4d03f; margin: 0; font-size: 13px;"><b>सक्रिय यूजर (Logged In)</b></p>
                <p style="color: #2ecc71; margin: 5px 0 0 0; font-size: 15px;"><b>{st.session_state.logged_in_user}</b></p>
            </div>
            """, unsafe_allow_html=True)
            if st.button("🚪 सुरक्षित लॉगआउट"):
                st.session_state.authenticated = False
                st.session_state.logged_in_user = ""
                st.rerun()
