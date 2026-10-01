import streamlit as st
import base64
import math
import os
import json
import calendar
import uuid
import re
from datetime import datetime, date, timedelta
from typing import Any, Optional

# ============================================================
# 1. PAGE CONFIGURATION
# ============================================================
st.set_page_config(
    page_title="राजस्थान गवर्नमेंट ऑफिस ऑर्डर जनरेटर सॉफ्टवेयर",
    page_icon="📜",
    layout="wide"
)

# Global dark app shell is injected before both authentication and dashboard.
st.markdown("""
<style>
html, body, [data-testid="stApp"], [data-testid="stAppViewContainer"],
[data-testid="stAppViewBlockContainer"], [data-testid="stMainBlockContainer"],
section[data-testid="stMain"], main, div[data-testid="stMain"] {
    background:#06162b !important; color:#ffffff !important;
}
[data-testid="stAppViewContainer"] {
    background:linear-gradient(135deg,#06162b 0%,#0b2b4a 55%,#123e68 100%) !important;
}
[data-testid="stAppViewBlockContainer"], [data-testid="stMainBlockContainer"] { background:transparent !important; }
.element-container, [data-testid="stAppViewBlockContainer"], [data-testid="stMainBlockContainer"], [data-stale="true"] {
    opacity:1 !important; visibility:visible !important; filter:none !important; transition:none !important;
}
header[data-testid="stHeader"], [data-testid="stDecoration"], [data-testid="stStatusWidget"] { background:transparent !important; }
</style>
""", unsafe_allow_html=True)


# Shared visual assets for Login and Dashboard.
def _find_developer_photo():
    base_dir=os.path.dirname(os.path.abspath(__file__))
    for ext in (".jpg",".png",".jpeg",".JPG",".PNG",".JPEG"):
        path=os.path.join(base_dir,"aloksingh"+ext)
        if os.path.isfile(path):
            return path,{".jpg":"image/jpeg",".jpeg":"image/jpeg",".png":"image/png"}.get(ext.lower(),"image/jpeg")
    return "","image/jpeg"

def _shared_image_base64():
    path,mime=_find_developer_photo()
    if not path: return "","image/jpeg"
    try:
        with open(path,"rb") as fh: return base64.b64encode(fh.read()).decode("ascii"),mime
    except Exception: return "","image/jpeg"

def _shared_sun_rays_svg(css_class="spinning-rays"):
    cx=cy=130; inner_r=67; polygons=[]
    for i in range(24):
        deg=i*15; outer_r=122 if i%2==0 else 96; half_base=5.0 if i%2==0 else 3.5; color="#f1c40f" if i%2==0 else "#ff9f43"
        tip=math.radians(deg); left=math.radians(deg-half_base); right=math.radians(deg+half_base)
        polygons.append(f'<polygon points="{cx+inner_r*math.cos(left):.1f},{cy+inner_r*math.sin(left):.1f} {cx+outer_r*math.cos(tip):.1f},{cy+outer_r*math.sin(tip):.1f} {cx+inner_r*math.cos(right):.1f},{cy+inner_r*math.sin(right):.1f}" fill="{color}"/>')
    return f'<svg class="{css_class}" viewBox="0 0 260 260" width="260" height="260" preserveAspectRatio="xMidYMid meet"><circle cx="130" cy="130" r="67" stroke="#f39c12" stroke-width="3" fill="none"/>{"".join(polygons)}</svg>'

img_b64,img_mime=_shared_image_base64()
rays_svg_html=_shared_sun_rays_svg("spinning-rays")

# ============================================================
# INTEGRATED SUPABASE + AUTHENTICATION LAYER
# ------------------------------------------------------------
# इस app में अब अलग supabase_service.py की आवश्यकता नहीं है।
# मूल चारों module का UI/calculation code नीचे यथावत रखा गया है।
#
# Authentication:
#   - User Login
#   - Administrator Login
#   - User/Admin Forgot User ID + Password recovery
#   - One login for the complete application
#
# Storage:
#   - profiles: user identity/role
#   - module_data: user-wise module data
#   - module_data reserved event records: activity/visitor analytics
#
# IMPORTANT:
#   SUPABASE_SERVICE_ROLE_KEY केवल Streamlit server-side secret है।
#   इसे कभी client-side HTML/JS में न भेजें।
# ============================================================

try:
    from supabase import create_client, Client
except Exception as exc:
    st.error(
        "Supabase Python package उपलब्ध नहीं है। "
        "requirements.txt में 'supabase' जोड़ें और application restart करें।"
    )
    st.stop()

def _load_local_dotenv():
    """Load a local .env file without requiring python-dotenv.

    Streamlit/Python does not automatically read a project .env file.
    Existing OS environment variables are never overwritten.
    """
    candidates = [
        os.path.join(os.getcwd(), ".env"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"),
    ]
    seen = set()
    for env_path in candidates:
        env_path = os.path.abspath(env_path)
        if env_path in seen or not os.path.isfile(env_path):
            continue
        seen.add(env_path)
        try:
            with open(env_path, "r", encoding="utf-8") as fh:
                for raw_line in fh:
                    line = raw_line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if line.startswith("export "):
                        line = line[7:].strip()
                    if "=" not in line:
                        continue
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip()
                    if not key:
                        continue
                    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("\"", "'"):
                        value = value[1:-1]
                    os.environ.setdefault(key, value)
        except Exception:
            # .env is optional; Streamlit Secrets/environment variables remain usable.
            pass

_load_local_dotenv()


def _secret(name: str, default: str = "") -> str:
    """Streamlit Secrets -> local .env/OS environment fallback."""
    try:
        value = st.secrets.get(name)
        if value:
            return str(value)
    except Exception:
        pass
    return os.getenv(name, default)

SUPABASE_URL = _secret("SUPABASE_URL")
SUPABASE_KEY = _secret("SUPABASE_KEY")
SUPABASE_SERVICE_ROLE_KEY = _secret("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    st.error(
        "SUPABASE_URL / SUPABASE_KEY उपलब्ध नहीं हैं। "
        "Streamlit Secrets या local environment में दोनों values सेट करें।"
    )
    st.stop()

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
_service_supabase: Optional[Client] = None

def _get_service_client() -> Client:
    global _service_supabase
    if _service_supabase is None:
        if not SUPABASE_SERVICE_ROLE_KEY:
            raise RuntimeError(
                "SUPABASE_SERVICE_ROLE_KEY उपलब्ध नहीं है। "
                "यह server-side secret आवश्यक है।"
            )
        _service_supabase = create_client(
            SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY
        )
    return _service_supabase

def _safe_text(value: Any) -> str:
    return "" if value is None else str(value)

def _profile_by_username(username: str) -> Optional[dict]:
    username = _safe_text(username).strip().lower()
    if not username:
        return None
    response = (
        _get_service_client()
        .table("profiles")
        .select("user_id,username,full_name,address,mobile,email,role,is_active")
        .eq("username", username)
        .maybe_single()
        .execute()
    )
    return response.data if getattr(response, "data", None) else None

def _profile_by_identity(mobile: str, email: str) -> Optional[dict]:
    mobile = _safe_text(mobile).strip()
    email = _safe_text(email).strip().lower()
    if not mobile or not email:
        return None
    response = (
        _get_service_client()
        .table("profiles")
        .select("user_id,username,full_name,address,mobile,email,role,is_active")
        .eq("mobile", mobile)
        .eq("email", email)
        .maybe_single()
        .execute()
    )
    return response.data if getattr(response, "data", None) else None

def _profile_by_email(email: str) -> Optional[dict]:
    email = _safe_text(email).strip().lower()
    if not email:
        return None
    response = (
        _get_service_client()
        .table("profiles")
        .select("user_id,username,full_name,address,mobile,email,role,is_active")
        .eq("email", email)
        .maybe_single()
        .execute()
    )
    return response.data if getattr(response, "data", None) else None

def _set_supabase_session(access_token: str, refresh_token: str):
    if not access_token or not refresh_token:
        raise RuntimeError("Supabase Auth session tokens उपलब्ध नहीं हैं।")
    response = supabase.auth.set_session(access_token, refresh_token)
    session = getattr(response, "session", None)
    if session is not None:
        st.session_state.supabase_access_token = getattr(
            session, "access_token", access_token
        )
        st.session_state.supabase_refresh_token = getattr(
            session, "refresh_token", refresh_token
        )
    else:
        st.session_state.supabase_access_token = access_token
        st.session_state.supabase_refresh_token = refresh_token

def _supabase_password_login(profile: dict, password: str):
    response = supabase.auth.sign_in_with_password({
        "email": profile["email"],
        "password": password,
    })
    user = getattr(response, "user", None)
    session = getattr(response, "session", None)
    if user is None or session is None:
        raise RuntimeError("Supabase Auth session प्राप्त नहीं हुआ।")
    _set_supabase_session(
        getattr(session, "access_token", None),
        getattr(session, "refresh_token", None),
    )
    return user

def _create_supabase_user_and_profile(
    full_name: str,
    address: str,
    mobile: str,
    email: str,
    username: str,
    password: str,
    role: str = "user",
):
    """
    Registration को Supabase Auth + profiles दोनों में एक transaction-like
    sequence में तैयार करता है। यदि profile पहले से है तो उसे sync करता है।
    """
    service = _get_service_client()

    existing_profile = _profile_by_username(username)
    if existing_profile:
        raise RuntimeError("यह Login ID पहले से registered है।")

    # Email duplicate check पहले.
    existing_email_profile = _profile_by_email(email)
    if existing_email_profile:
        raise RuntimeError("यह Email पहले से registered है।")

    # Supabase Auth user create.
    auth_response = service.auth.admin.create_user({
        "email": email,
        "password": password,
        "email_confirm": True,
        "user_metadata": {
            "username": username,
            "full_name": full_name,
            "address": address,
            "mobile": mobile,
            "role": role,
        },
    })
    auth_user = getattr(auth_response, "user", None)
    if auth_user is None:
        raise RuntimeError("Supabase Auth User create नहीं हुआ।")

    user_id = str(auth_user.id)

    profile_payload = {
        "user_id": user_id,
        "username": username,
        "full_name": full_name,
        "address": address,
        "mobile": mobile,
        "email": email,
        "role": role,
        "is_active": True,
    }

    try:
        service.table("profiles").upsert(
            profile_payload, on_conflict="user_id"
        ).execute()
    except Exception:
        # Auth user बना लेकिन profile नहीं बना तो orphan account न रहे।
        try:
            service.auth.admin.delete_user(user_id)
        except Exception:
            pass
        raise

    return profile_payload

def _sync_profile_from_auth_user(
    username: str,
    full_name: str,
    address: str,
    mobile: str,
    email: str,
    role: str = "user",
):
    """Existing Supabase Auth user के लिए profiles row ensure/update."""
    service = _get_service_client()
    profile = _profile_by_username(username)
    if profile:
        payload = {
            "full_name": full_name,
            "address": address,
            "mobile": mobile,
            "email": email,
            "role": role,
            "is_active": True,
        }
        service.table("profiles").update(payload).eq(
            "user_id", str(profile["user_id"])
        ).execute()
        return _profile_by_username(username)

    # Existing Auth account को email से खोजने का प्रयत्न.
    try:
        users_response = service.auth.admin.list_users()
        users = getattr(users_response, "users", None) or []
        auth_user = next(
            (
                u for u in users
                if _safe_text(getattr(u, "email", "")).strip().lower()
                == email.lower()
            ),
            None,
        )
    except Exception:
        auth_user = None

    if auth_user is None:
        return None

    user_id = str(auth_user.id)
    payload = {
        "user_id": user_id,
        "username": username,
        "full_name": full_name,
        "address": address,
        "mobile": mobile,
        "email": email,
        "role": role,
        "is_active": True,
    }
    service.table("profiles").upsert(
        payload, on_conflict="user_id"
    ).execute()
    return payload


# ============================================================
# LEGACY SQLITE -> SUPABASE ONE-TIME LOGIN MIGRATION
# ------------------------------------------------------------
# पुराने app.py में users/password_hash/password_salt SQLite में थे।
# पहली बार पुराने credentials से login करने पर वही password verify करके
# Supabase Auth account/profile बनाया जाता है। Plain password कहीं save नहीं होता।
# ============================================================
import sqlite3

LEGACY_AUTH_DB = os.path.join("output", "user_auth.db")

def _legacy_connection():
    if not os.path.isfile(LEGACY_AUTH_DB):
        return None
    conn = sqlite3.connect(LEGACY_AUTH_DB, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def _legacy_user_by_username(username):
    conn = _legacy_connection()
    if conn is None:
        return None
    try:
        row = conn.execute(
            "SELECT * FROM users WHERE username = ? AND is_active = 1 LIMIT 1",
            (_safe_text(username).strip().lower(),),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

def _legacy_user_by_identity(mobile, email, role=None):
    conn = _legacy_connection()
    if conn is None:
        return None
    try:
        sql = "SELECT * FROM users WHERE mobile = ? AND lower(email) = ? AND is_active = 1"
        params = [_safe_text(mobile).strip(), _safe_text(email).strip().lower()]
        if role:
            sql += " AND role = ?"
            params.append(role)
        sql += " ORDER BY id LIMIT 1"
        row = conn.execute(sql, params).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

def _legacy_password_ok(user, password):
    if not user or not password:
        return False
    try:
        salt = user.get("password_salt", "")
        stored = user.get("password_hash", "")
        calculated = __import__("hashlib").pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt.encode("utf-8"), 200000
        ).hex()
        return __import__("secrets").compare_digest(calculated, stored)
    except Exception:
        return False

def _find_auth_user_by_email(email):
    try:
        users_response = _get_service_client().auth.admin.list_users()
        users = getattr(users_response, "users", None) or []
        return next(
            (u for u in users if _safe_text(getattr(u, "email", "")).strip().lower() == _safe_text(email).strip().lower()),
            None,
        )
    except Exception:
        return None

def _migrate_legacy_user_to_supabase(username, password):
    legacy = _legacy_user_by_username(username)
    if not legacy or not _legacy_password_ok(legacy, password):
        return None

    existing_profile = _profile_by_username(username)
    if existing_profile:
        # Legacy password को Supabase Auth में एक बार synchronize करें।
        # user_id सीधे profile से लिया जाता है; email lookup पर निर्भर नहीं।
        try:
            legacy_role = _safe_text(legacy.get("role") or "user").strip().lower()
            if legacy_role not in ("user", "admin"):
                legacy_role = "user"
            _get_service_client().auth.admin.update_user_by_id(
                str(existing_profile["user_id"]),
                {
                    "password": password,
                    "email": _safe_text(legacy.get("email")).strip().lower(),
                    "email_confirm": True,
                    "user_metadata": {
                        "username": _safe_text(legacy.get("username")).strip().lower(),
                        "full_name": legacy.get("full_name", ""),
                        "mobile": legacy.get("mobile", ""),
                        "role": legacy_role,
                    },
                },
            )
            synced = {
                "full_name": legacy.get("full_name", ""),
                "address": legacy.get("address", "") if "address" in legacy else existing_profile.get("address", ""),
                "mobile": legacy.get("mobile", ""),
                "email": _safe_text(legacy.get("email")).strip().lower(),
                "role": legacy_role,
                "is_active": True,
            }
            _get_service_client().table("profiles").update(synced).eq(
                "user_id", str(existing_profile["user_id"])
            ).execute()
            existing_profile.update(synced)
        except Exception:
            # Auth sync failure is surfaced later by the login attempt; do not
            # silently change the original module/UI behavior.
            pass
        return existing_profile

    email = _safe_text(legacy.get("email")).strip().lower()
    auth_user = _find_auth_user_by_email(email)

    if auth_user is None:
        auth_response = _get_service_client().auth.admin.create_user({
            "email": email,
            "password": password,
            "email_confirm": True,
            "user_metadata": {
                "username": legacy["username"],
                "full_name": legacy.get("full_name", ""),
                "mobile": legacy.get("mobile", ""),
                "role": legacy.get("role", "user"),
            },
        })
        auth_user = getattr(auth_response, "user", None)
        if auth_user is None:
            raise RuntimeError("पुराने account का Supabase Auth migration नहीं हो सका।")
    else:
        _get_service_client().auth.admin.update_user_by_id(
            str(auth_user.id), {"password": password, "email": email}
        )

    profile = {
        "user_id": str(auth_user.id),
        "username": _safe_text(legacy.get("username")).strip().lower(),
        "full_name": legacy.get("full_name", ""),
        "address": legacy.get("address", "") if "address" in legacy else "",
        "mobile": legacy.get("mobile", ""),
        "email": email,
        "role": legacy.get("role", "user"),
        "is_active": True,
    }
    _get_service_client().table("profiles").upsert(profile, on_conflict="user_id").execute()
    return profile

def _legacy_admin_exists():
    conn = _legacy_connection()
    if conn is None:
        return False
    try:
        row = conn.execute(
            "SELECT id FROM users WHERE role='admin' AND is_active=1 ORDER BY id LIMIT 1"
        ).fetchone()
        return row is not None
    finally:
        conn.close()

def _save_module_data(username: str, module: str, data: dict):
    username = _safe_text(username).strip().lower()
    if not username:
        raise RuntimeError("Current logged-in username उपलब्ध नहीं है।")
    cached = st.session_state.get("logged_profile") or {}
    if str(cached.get("username", "")).strip().lower() == username and cached.get("user_id"):
        profile = dict(cached)
    else:
        profile = _profile_by_username(username)
    if not profile:
        raise RuntimeError(f"Supabase profiles में username '{username}' नहीं मिला।")
    if not profile.get("is_active", True):
        raise RuntimeError("Supabase user profile inactive है।")
    user_id = str(profile.get("user_id") or st.session_state.get("supabase_user_id") or "").strip()
    if not user_id:
        raise RuntimeError("Current Supabase user_id उपलब्ध नहीं है।")
    table = _get_service_client().table("module_data")
    payload = {"user_id": user_id, "module": str(module), "data": data}
    try:
        response = table.upsert(payload, on_conflict="user_id,module").execute()
    except Exception as first_error:
        try:
            existing = table.select("id").eq("user_id", user_id).eq("module", str(module)).order("created_at", desc=True).limit(1).execute()
            rows = getattr(existing, "data", None) or []
            if rows:
                response = table.update({"data": data, "updated_at": datetime.now().isoformat()}).eq("id", rows[0]["id"]).execute()
            else:
                response = table.insert(payload).execute()
        except Exception as second_error:
            raise RuntimeError(f"Supabase {module} save failed: {second_error}. First upsert error: {first_error}") from second_error
    verify = table.select("user_id,module,data").eq("user_id", user_id).eq("module", str(module)).limit(1).execute()
    rows = getattr(verify, "data", None) or []
    if not rows:
        raise RuntimeError("Supabase write हुआ लेकिन read-back verification में record नहीं मिला।")
    return response

# Public compatibility name used by the arrear module and future module
# save hooks. It intentionally delegates to the same Supabase user-wise
# persistence function used by PL, Increment and Sanchalan.
def save_module_data_for_local_user(username: str, module: str, data: dict):
    return _save_module_data(username, module, data)

def load_module_data_for_local_user(username: str, module: str) -> Optional[dict]:
    return _read_module_data(username, module)

def _read_module_data(username: str, module: str) -> Optional[dict]:
    profile = _profile_by_username(username)
    if not profile:
        return None
    response = (
        _get_service_client()
        .table("module_data")
        .select("id,user_id,module,data,created_at,updated_at")
        .eq("user_id", str(profile["user_id"]))
        .eq("module", module)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    rows = getattr(response, "data", None) or []
    return rows[0].get("data") if rows else None

def _delete_module_data(username: str, module: str):
    profile = _profile_by_username(username)
    if not profile:
        return
    _get_service_client().table("module_data").delete().eq(
        "user_id", str(profile["user_id"])
    ).eq("module", module).execute()

# ------------------------------------------------------------
# Reserved event records in module_data
# ------------------------------------------------------------
def _event_insert(prefix: str, data: dict):
    username = _safe_text(st.session_state.get("logged_username")).strip().lower()
    if not username:
        return
    profile = _profile_by_username(username)
    if not profile:
        return
    event_module = f"{prefix}{uuid.uuid4()}"
    payload = {
        "user_id": str(profile["user_id"]),
        "module": event_module,
        "data": data,
    }
    try:
        _get_service_client().table("module_data").insert(payload).execute()
    except Exception:
        # Analytics कभी मुख्य module को रोकने का कारण नहीं बनेगा।
        pass

def _read_events(prefix: str) -> list[dict]:
    try:
        response = (
            _get_service_client()
            .table("module_data")
            .select("user_id,module,data,created_at,updated_at")
            .like("module", f"{prefix}%")
            .order("created_at", desc=True)
            .limit(5000)
            .execute()
        )
        return getattr(response, "data", None) or []
    except Exception:
        return []

def _all_profiles() -> list[dict]:
    try:
        response = (
            _get_service_client()
            .table("profiles")
            .select("user_id,username,full_name,address,mobile,email,role,is_active")
            .order("username")
            .execute()
        )
        return getattr(response, "data", None) or []
    except Exception:
        return []

# ============================================================
# APPLICATION SESSION STATE
# ============================================================
_STATE_DEFAULTS = {
    "authenticated": False,
    "logged_username": None,
    "logged_role": None,
    "login_mode": None,
    "supabase_user_id": None,
    "supabase_access_token": None,
    "supabase_refresh_token": None,
    "show_registration": False,
    "show_admin_login": False,
    "show_admin_recovery": False,
    "show_user_recovery": False,
    "recovery_verified": False,
    "recovery_mode": None,
    "recovery_email": None,
    "recovery_otp_sent": False,
    "recovery_profile": None,
    "recovery_user_id": None,
    "password_recovery_active": False,
    "recovery_callback_error": None,
    "last_tracked_module": None,
    "visitor_session_id": str(uuid.uuid4()),
    "logged_profile": None,
}

for _key, _default in _STATE_DEFAULTS.items():
    if _key not in st.session_state:
        st.session_state[_key] = _default

def _clear_module_session_state():
    """User बदलने पर पुराने user का in-memory module data हटाएँ।"""
    prefixes = (
        "pl_", "inc_", "san_", "arr_",
        "w_pl_", "w_inc_", "w_san_", "w_arr_",
        "del_pl_", "del_inc_", "del_san_",
    )
    exact = {
        "gen_sheet_sel", "arr_clear_confirm",
        "pl_bundle_loaded", "inc_bundle_loaded",
        "san_bundle_loaded", "arrear_bundle_loaded",
    }
    for key in list(st.session_state.keys()):
        if key in exact or any(key.startswith(prefix) for prefix in prefixes):
            try:
                del st.session_state[key]
            except Exception:
                pass

def _set_authenticated(profile: dict, auth_user=None):
    _clear_module_session_state()
    st.session_state.authenticated = True
    st.session_state.logged_username = profile["username"]
    st.session_state.logged_role = profile.get("role", "user")
    st.session_state.login_mode = (
        "admin" if profile.get("role") == "admin" else "user"
    )
    st.session_state.last_tracked_module = None
    st.session_state.logged_profile = dict(profile)
    if auth_user is not None:
        st.session_state.supabase_user_id = str(auth_user.id)
    else:
        st.session_state.supabase_user_id = str(profile["user_id"])

    # A previous Admin Visitor Analytics URL must never leak into a new login.
    # Always start a newly authenticated session on the Main Dashboard.
    try:
        st.query_params.clear()
        st.query_params["page"] = "dashboard"
    except Exception:
        pass

def _clear_auth_state():
    _clear_module_session_state()
    try:
        supabase.auth.sign_out()
    except Exception:
        pass
    for key, value in {
        "authenticated": False,
        "logged_username": None,
        "logged_role": None,
        "login_mode": None,
        "supabase_user_id": None,
        "supabase_access_token": None,
        "supabase_refresh_token": None,
        "last_tracked_module": None,
        "recovery_verified": False,
        "recovery_mode": None,
        "recovery_email": None,
        "recovery_otp_sent": False,
        "recovery_profile": None,
        "recovery_user_id": None,
        "password_recovery_active": False,
        "logged_profile": None,
    }.items():
        st.session_state[key] = value

def _record_activity(activity: str, module: str = "Authentication", details: str = ""):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    session_id = st.session_state.get("visitor_session_id") or str(uuid.uuid4())
    _event_insert("__activity__", {
        "username": st.session_state.get("logged_username", ""),
        "activity": activity,
        "module": module,
        "activity_time": now,
        "details": details,
        "session_id": session_id,
    })

def _record_visitor(module_name: str):
    session_id = st.session_state.get("visitor_session_id") or str(uuid.uuid4())
    now = datetime.now()
    _event_insert("__visitor__", {
        "Visitor ID": str(uuid.uuid4()),
        "Date": now.strftime("%d-%m-%Y"),
        "Time": now.strftime("%H:%M:%S"),
        "Module": module_name,
        "Session ID": session_id,
        "Username": st.session_state.get("logged_username", ""),
    })

# Compatibility names used by the unchanged module code.
def save_activity(username, activity, module=None, details=None):
    if not username:
        return
    old_username = st.session_state.get("logged_username")
    st.session_state.logged_username = username
    try:
        _record_activity(activity, module or "Authentication", details or "")
    finally:
        st.session_state.logged_username = old_username

def _visitor_get_session_id():
    if not st.session_state.get("visitor_session_id"):
        st.session_state.visitor_session_id = str(uuid.uuid4())
    return st.session_state.visitor_session_id

def _visitor_record_visit(module_name="Unknown"):
    session_key = f"visitor_recorded_{module_name}"
    if st.session_state.get(session_key, False):
        return
    _record_visitor(module_name)
    st.session_state[session_key] = True

# ============================================================
# USER-WISE DATA STORAGE COMPATIBILITY LAYER
# ------------------------------------------------------------
# मूल modules save_json_data/load_json_data ही इस्तेमाल करते हैं।
# इसलिए module UI/code को छुए बिना इन functions को Supabase-aware बनाया गया है।
# ============================================================
USER_DATA_ROOT = os.path.join("output", "user_data")
os.makedirs(USER_DATA_ROOT, exist_ok=True)

def _safe_username_for_path(username):
    value = str(username or "unknown_user").strip().lower()
    value = re.sub(r"[^a-zA-Z0-9_.-]", "_", value)
    return value[:80] or "unknown_user"

def get_current_user_data_dir():
    username = st.session_state.get("logged_username")
    if not username:
        return os.path.join(USER_DATA_ROOT, "_unauthenticated")
    folder = os.path.join(USER_DATA_ROOT, _safe_username_for_path(username))
    os.makedirs(folder, exist_ok=True)
    return folder

CURRENT_USER_DATA_DIR = get_current_user_data_dir()
PL_DATA_FILE = os.path.join(CURRENT_USER_DATA_DIR, "pl_data.json")
INC_DATA_FILE = os.path.join(CURRENT_USER_DATA_DIR, "increment_data.json")
SAN_DATA_FILE = os.path.join(CURRENT_USER_DATA_DIR, "sanchalan_data.json")
ARREAR_DATA_FILE = os.path.join(CURRENT_USER_DATA_DIR, "arrear_data.json")

MASTER_VENDORS_FILE = "master_vendors.json"
MASTER_SCHOOLS_FILE = "master_schools.json"
MASTER_BENEFICIARIES_FILE = "master_beneficiaries.json"

_MODULE_FILE_MAP = {
    "pl_data.json": "pl_surrender",
    "increment_data.json": "increment_order",
    "sanchalan_data.json": "sanchalan_portal",
    "arrear_data.json": "salary_arrear",
}

def load_json_data(file_path, default_val=None):
    if default_val is None:
        default_val = {"office_data": {}, "employees": []}

    # Supabase is the primary persistent source for authenticated users.
    username = st.session_state.get("logged_username")
    basename = os.path.basename(file_path)
    module = _MODULE_FILE_MAP.get(basename)

    if username and module:
        try:
            cloud_data = _read_module_data(username, module)
            if cloud_data is not None:
                return cloud_data
        except Exception:
            pass

    # Local fallback keeps the existing VS Code workflow functional.
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return default_val

def save_json_data(file_path, data):
    folder = os.path.dirname(os.path.abspath(file_path))
    os.makedirs(folder, exist_ok=True)

    # Existing local behavior retained.
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    # Supabase persistent save.
    username = st.session_state.get("logged_username")
    basename = os.path.basename(file_path)
    module = _MODULE_FILE_MAP.get(basename)
    if username and module:
        try:
            _save_module_data(username, module, data)
            st.session_state[f"supabase_saved_{module}"] = True
            st.session_state[f"supabase_saved_at_{module}"] = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
        except Exception as exc:
            st.session_state[f"supabase_saved_{module}"] = False
            st.warning(f"⚠️ {module} का local data save हो गया, लेकिन Supabase save नहीं हुआ: {type(exc).__name__}: {exc}")

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

# ============================================================
# REGISTRATION
# ============================================================
def registration_screen():
    st.markdown("""
    <div style="
        text-align:center;
        padding:18px;
        border-radius:12px;
        background:linear-gradient(135deg,#154360,#2874A6);
        margin-bottom:20px;">
        <h2 style="color:white;">📝 नया उपयोगकर्ता पंजीकरण</h2>
        <p style="color:white;">राजस्थान गवर्नमेंट ऑफिस ऑर्डर जनरेटर</p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        full_name = st.text_input("👤 पूरा नाम", key="reg_full_name")
        address = st.text_input("🏠 पता", key="reg_address")
        mobile = st.text_input("📱 मोबाइल नंबर", max_chars=10, key="reg_mobile")
        email = st.text_input("📧 Email Address", key="reg_email")
    with col2:
        username = st.text_input("🔑 Login ID / Username", key="reg_username")
        password = st.text_input("🔒 Password", type="password", key="reg_password")
        confirm_password = st.text_input(
            "🔒 Confirm Password", type="password", key="reg_confirm_password"
        )

    st.info("यह सामान्य User Account है। Administrator Account केवल अलग Admin Login से संचालित होगा।")

    if st.button("✅ Registration करें", use_container_width=True, key="register_user_button"):
        full_name = full_name.strip()
        address = address.strip()
        mobile = mobile.strip()
        email = email.strip().lower()
        username = username.strip().lower()

        if not full_name:
            st.error("कृपया पूरा नाम भरें।")
            return
        if not re.fullmatch(r"[0-9]{10}", mobile):
            st.error("कृपया 10 अंकों का मोबाइल नंबर भरें।")
            return
        if not re.fullmatch(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
            st.error("कृपया सही Email Address भरें।")
            return
        if not re.fullmatch(r"[a-zA-Z0-9_.-]{4,30}", username):
            st.error("Login ID 4 से 30 characters की हो।")
            return
        if len(password) < 6:
            st.error("Password कम से कम 6 characters का होना चाहिए।")
            return
        if password != confirm_password:
            st.error("Password और Confirm Password समान नहीं हैं।")
            return

        try:
            profile = _create_supabase_user_and_profile(
                full_name, address, mobile, email, username, password, "user"
            )
            st.success("Registration सफल रहा। अब Login करें।")
            st.session_state.show_registration = False
            st.session_state.show_user_recovery = False
            st.rerun()
        except Exception as exc:
            st.error(f"Registration Error: {type(exc).__name__}: {exc}")

# ============================================================
# USER LOGIN
# ============================================================
def _auth_visual_style():
    st.markdown("""
    <style>
    html, body, [data-testid="stApp"], [data-testid="stAppViewContainer"],
    [data-testid="stAppViewBlockContainer"], [data-testid="stMainBlockContainer"],
    section[data-testid="stMain"], main {
        background:#06162b !important;
    }
    .stApp, [data-testid="stAppViewContainer"], [data-testid="stAppViewBlockContainer"],
    [data-testid="stMainBlockContainer"], section[data-testid="stMain"] {
        background:linear-gradient(135deg,#06162b,#0b2b4a 55%,#123e68) !important;
    }
    /* Hide the previous Login DOM immediately during Streamlit rerun/navigation.
       This prevents the old black Login interface from remaining visible for
       1–2 seconds while the Main Dashboard is being rendered. The application
       background remains dark, so no white flash is introduced. */
    [data-stale="true"] {
        opacity:0 !important;
        visibility:hidden !important;
        pointer-events:none !important;
        transition:none !important;
        filter:none !important;
    }
    [data-testid="stAppViewBlockContainer"], [data-testid="stMainBlockContainer"] {
        transition:none !important;
    }
    [data-testid="stStatusWidget"], [data-testid="stDecoration"] { background:transparent !important; }
    header[data-testid="stHeader"] { background:transparent !important; }

    /* One identical header for every Login / ID-Recovery / Password-Recovery screen. */
    .auth-shell {
        background:linear-gradient(135deg,#081b34,#0c3155 55%,#164b79);
        padding:10px 16px; border:2px solid #f4d03f; border-radius:18px;
        box-shadow:0 10px 26px rgba(0,0,0,.34); margin:2px 0 12px;
        display:grid; grid-template-columns:282px minmax(0,1fr); align-items:center;
        min-height:262px; box-sizing:border-box;
    }
    .auth-visual-box {
        width:260px; height:260px; border:1px solid rgba(244,208,63,.48);
        border-radius:15px; background:rgba(3,18,35,.52); display:flex;
        align-items:center; justify-content:center; overflow:hidden; box-shadow:inset 0 0 18px rgba(0,0,0,.28);
    }
    .auth-sun { position:relative; width:260px; height:260px; display:flex; align-items:center; justify-content:center; flex:0 0 260px; overflow:visible; }
    .auth-sun-rotator { position:absolute; inset:0; width:260px; height:260px; z-index:1; animation:authspin 12s linear infinite; transform-origin:50% 50%; will-change:transform; }
    .auth-sun-rotator .spinning-rays { position:absolute; inset:0; width:260px !important; height:260px !important; display:block; }
    .auth-photo {
        position:absolute; left:50%; top:50%; transform:translate(-50%,-50%);
        width:134px; height:134px; box-sizing:border-box; border-radius:50%;
        border:3px solid #f39c12; z-index:3; display:block;
        background-repeat:no-repeat; background-position:center 25%; background-size:120%;
        background-color:#123e68;
        box-shadow:0 0 12px rgba(0,0,0,.78), inset 0 0 0 1px rgba(255,255,255,.18);
    }
    .auth-header-copy { min-width:0; padding:4px 20px 4px 18px; text-align:left; }
    .auth-title { color:#f4d03f !important; text-align:left; font-size:31px; line-height:1.12; font-weight:900; margin:0 0 10px; text-shadow:0 2px 0 rgba(0,0,0,.25); }
    .auth-subtitle { color:#d6eaf8 !important; text-align:left; font-size:17px; line-height:1.45; margin:0; font-weight:700; }
    .auth-module-info { color:#85c1e9 !important; text-align:left; font-size:14px; line-height:1.5; margin-top:8px; font-weight:600; }
    @keyframes authspin { from{transform:rotate(0deg)} to{transform:rotate(360deg)} }
    .auth-card { background:rgba(9,30,53,.96); border:1px solid #2e86c1; border-radius:16px; padding:18px; box-shadow:0 8px 22px rgba(0,0,0,.28); min-height:270px; }
    .auth-card h3,.auth-card h2 { color:#f4d03f !important; }
    .auth-card p { color:#ecf0f1 !important; line-height:1.55; }
    div[data-testid="stTextInput"] input { background:linear-gradient(180deg,#f2f5f8,#dce6ef) !important; color:#102a45 !important; border:2px solid #5dade2 !important; border-radius:11px !important; box-shadow:inset 0 2px 5px rgba(0,0,0,.12),0 3px 0 #1b4f72 !important; min-height:43px !important; font-weight:700 !important; }
    div[data-testid="stTextInput"] label p { color:#f4d03f !important; font-weight:800 !important; }
    /* Explicitly force Login Credentials / recovery headings to the same gold as the key icon. */
    div[class*="st-key-user_login_form"] h2, div[class*="st-key-admin_login_form"] h2,
    div[class*="st-key-user_recovery_form"] h2, div[class*="st-key-admin_recovery_form"] h2,
    div[class*="st-key-admin_password_reset_form"] h2, div[class*="st-key-user_login_form"] h3,
    div[class*="st-key-admin_login_form"] h3, div[class*="st-key-user_recovery_form"] h3,
    div[class*="st-key-admin_recovery_form"] h3, div[class*="st-key-admin_password_reset_form"] h3 { color:#f4d03f !important; }
    div[class*="st-key-user_login_form"], div[class*="st-key-admin_login_form"], div[class*="st-key-user_recovery_form"], div[class*="st-key-admin_recovery_form"], div[class*="st-key-admin_password_reset_form"] {
        background:rgba(9,30,53,.96) !important; border:1px solid #2e86c1 !important; border-radius:16px !important; padding:18px 18px 12px !important; box-shadow:0 8px 22px rgba(0,0,0,.28) !important;
    }
    div[class*="st-key-user_login_submit"] button { background:#27ae60 !important; border:2px solid #2ecc71 !important; box-shadow:0 4px 0 #1e8449 !important; }
    div[class*="st-key-admin_login_submit"] button { background:#d4ac0d !important; border:2px solid #f4d03f !important; box-shadow:0 4px 0 #9a7d0a !important; }
    div[class*="st-key-user_id_recovery_btn"] button, div[class*="st-key-admin_id_recovery_btn"] button { background:#8e44ad !important; border:2px solid #9b59b6 !important; box-shadow:0 4px 0 #6c3483 !important; }
    div[class*="st-key-user_password_recovery_btn"] button, div[class*="st-key-admin_password_recovery_btn"] button { background:#d35400 !important; border:2px solid #e67e22 !important; box-shadow:0 4px 0 #a04000 !important; }
    /* Login-page navigation buttons: dark backgrounds keep the white labels readable. */
    div[class*="st-key-open_user_registration"] button { background:#1f618d !important; border:2px solid #2980b9 !important; box-shadow:0 4px 0 #154360 !important; color:#fff !important; }
    div[class*="st-key-open_admin_login"] button { background:#8e44ad !important; border:2px solid #9b59b6 !important; box-shadow:0 4px 0 #6c3483 !important; color:#fff !important; }
    div[class*="st-key-back_login_btn"] button { background:#c0392b !important; border:2px solid #e74c3c !important; box-shadow:0 4px 0 #922b21 !important; }
    div[class*="st-key-auth_action"] button, div[class*="st-key-user_recovery_verify"] button, div[class*="st-key-admin_recovery_verify"] button { background:#2980b9 !important; border:2px solid #3498db !important; box-shadow:0 4px 0 #1b4f72 !important; }
    div[class*="st-key-auth_action"] button, div[class*="st-key-user_login_submit"] button, div[class*="st-key-admin_login_submit"] button, div[class*="st-key-user_id_recovery_btn"] button, div[class*="st-key-user_password_recovery_btn"] button, div[class*="st-key-admin_id_recovery_btn"] button, div[class*="st-key-admin_password_recovery_btn"] button, div[class*="st-key-back_login_btn"] button, div[class*="st-key-user_recovery_verify"] button, div[class*="st-key-admin_recovery_verify"] button { color:#fff !important; font-weight:900 !important; border-radius:10px !important; min-height:44px !important; }
    div[class*="st-key-module_nav_pl"] button { background:#1f618d !important; border:2px solid #2980b9 !important; box-shadow:0 4px 0 #154360 !important; color:#fff !important; }
    div[class*="st-key-module_nav_inc"] button { background:#27ae60 !important; border:2px solid #2ecc71 !important; box-shadow:0 4px 0 #1e8449 !important; color:#fff !important; }
    div[class*="st-key-module_nav_sna"] button { background:#8e44ad !important; border:2px solid #9b59b6 !important; box-shadow:0 4px 0 #6c3483 !important; color:#fff !important; }
    div[class*="st-key-module_nav_arr"] button { background:#d35400 !important; border:2px solid #e67e22 !important; box-shadow:0 4px 0 #a04000 !important; color:#fff !important; }
    </style>
    """, unsafe_allow_html=True)


def _processing_notice(message: str):
    """Show a persistent one-run notice after a navigation/recovery action."""
    notice = st.session_state.pop("auth_processing_notice", None)
    if notice:
        st.info(f"🔄 {notice}")

def _set_processing_notice(message: str):
    st.session_state["auth_processing_notice"] = message

def _login_visual_header(title, subtitle, accent="#f4d03f", icon="👤"):
    _auth_visual_style()
    if img_b64:
        photo = (
            f'<div class="auth-photo" aria-label="Developer Photo" '
            f'style="background-image:url(\'data:{img_mime};base64,{img_b64}\');"></div>'
        )
    else:
        photo = '<div class="auth-photo" style="display:flex;align-items:center;justify-content:center;color:#f4d03f;font-size:44px;">👤</div>'
    st.markdown(f"""
    <div class="auth-shell">
      <div class="auth-visual-box">
        <div class="auth-sun">
          <div class="auth-sun-rotator">{rays_svg_html}</div>
          {photo}
        </div>
      </div>
      <div class="auth-header-copy">
        <div class="auth-title" style="color:{accent} !important;">राजस्थान गवर्नमेंट ऑफिस ऑर्डर जनरेटर</div>
        <div class="auth-subtitle">{icon} {title} — राजस्थान गवर्नमेंट ऑफिस ऑर्डर जनरेटर — एक Login से सभी Modules</div>
        <div class="auth-module-info">{subtitle}</div>
      </div>
    </div>
    """, unsafe_allow_html=True)


def user_login_screen():
    _login_visual_header("User Login", "राजस्थान गवर्नमेंट ऑफिस ऑर्डर जनरेटर — एक Login से सभी Modules", "#f4d03f", "👤")
    _processing_notice("User Login प्रक्रिया शुरू हो गई है।")
    left,right=st.columns([1.05,1.0], gap="large")
    with left:
        st.markdown("""<div class="auth-card"><h3>✨ सॉफ्टवेयर की प्रमुख विशेषताएँ</h3><p>🔐 सुरक्षित User/Admin Login और एक session में सभी चार modules।</p><p>☁️ प्रत्येक User का data Supabase में user-wise सुरक्षित।</p><p>📊 Admin को visitor, session और module activity दिखाई देती है।</p><p>📄 Salary Arrear में PDF तथा formula-based editable Excel।</p><p>🔑 User ID और Password recovery के लिए Registered Email + Mobile verification।</p></div>""", unsafe_allow_html=True)
    with right:
        with st.container(key="user_login_form"):
            st.markdown('<h2 style="color:#f4d03f !important;">🔑 Login Credentials</h2>', unsafe_allow_html=True)
            username=st.text_input("Login ID", key="user_login_username")
            password=st.text_input("Password", type="password", key="user_login_password")
            with st.container(key="user_login_submit"):
                if st.button("🟢 User Login करें", use_container_width=True, key="user_login_button"):
                    username=username.strip().lower()
                    with st.spinner("🔄 User Login हो रहा है… कृपया प्रतीक्षा करें।"):
                        try:
                            profile=_profile_by_username(username)
                            if not profile: profile=_migrate_legacy_user_to_supabase(username,password)
                            if not profile or not profile.get("is_active",True): raise RuntimeError()
                            if profile.get("role")=="admin":
                                st.warning("यह Administrator Account है। Admin Login चुनें।")
                            else:
                                auth_user=_supabase_password_login(profile,password); _set_authenticated(profile,auth_user); _record_activity("LOGIN","Authentication","Successful User login"); st.rerun()
                        except Exception: st.error("Login ID या Password गलत है।")
            st.markdown('<hr style="border-color:#2e86c1;">',unsafe_allow_html=True)
            c1,c2=st.columns(2)
            with c1:
                if st.button("📝 नया User Account",use_container_width=True,key="open_user_registration"):
                    st.session_state.show_registration=True; st.session_state.show_admin_login=False; st.session_state.show_user_recovery=False; st.rerun()
                with st.container(key="user_id_recovery_btn"):
                    if st.button("🔑 Forgot User ID",use_container_width=True,key="open_user_id_recovery"):
                        _set_processing_notice("Forgot User ID screen खोला जा रहा है…")
                        st.session_state.show_user_recovery=True; st.session_state.recovery_mode="user_id"; st.session_state.recovery_otp_sent=False; st.session_state.recovery_verified=False; st.rerun()
            with c2:
                if st.button("👑 Admin Login",use_container_width=True,key="open_admin_login"):
                    st.session_state.show_admin_login=True; st.session_state.show_user_recovery=False; st.session_state.show_registration=False; st.rerun()
                with st.container(key="user_password_recovery_btn"):
                    if st.button("🔐 Forgot Password",use_container_width=True,key="open_password_recovery"):
                        _set_processing_notice("Forgot Password screen खोला जा रहा है…")
                        st.session_state.show_user_recovery=True; st.session_state.recovery_mode="password"; st.session_state.recovery_otp_sent=False; st.session_state.recovery_verified=False; st.rerun()




def _send_admin_password_reset(email):
    """Send the native Supabase password-reset email for an Admin account."""
    email = _safe_text(email).strip().lower()
    if not email:
        raise RuntimeError("Registered Admin Email आवश्यक है।")

    # Streamlit's server-side Python cannot read the browser URL fragment that
    # Supabase's default recovery link uses.  The Reset Password email template
    # therefore sends TokenHash to this same redirect URL as query parameters.
    redirect_url = "http://localhost:8501"
    return supabase.auth.reset_password_for_email(
        email,
        options={"redirect_to": redirect_url},
    )


def _handle_admin_password_recovery_callback():
    """Consume a TokenHash recovery link and establish a verified Admin recovery state.

    The actual password update is performed by the trusted server-side service client
    after the one-time recovery token has been verified. This avoids depending on a
    browser-side session surviving a Streamlit rerun.
    """
    if st.session_state.get("password_recovery_active"):
        return

    try:
        params = st.query_params
        token_hash = _safe_text(params.get("token_hash", "")).strip()
        token_type = _safe_text(params.get("type", "")).strip().lower()

        if not token_hash or token_type != "recovery":
            return

        response = supabase.auth.verify_otp({
            "token_hash": token_hash,
            "type": "recovery",
        })

        user = getattr(response, "user", None)
        if user is None:
            raise RuntimeError("Supabase recovery token verify हुआ, लेकिन user प्राप्त नहीं हुआ।")

        email = _safe_text(getattr(user, "email", "")).strip().lower()
        user_id = _safe_text(getattr(user, "id", "")).strip()
        profile = _profile_by_email(email) if email else None

        if not user_id or not profile or profile.get("role") != "admin":
            try:
                supabase.auth.sign_out()
            except Exception:
                pass
            raise RuntimeError("यह recovery link किसी registered Admin account का नहीं है।")

        st.session_state.recovery_email = email
        st.session_state.recovery_user_id = user_id
        st.session_state.recovery_profile = profile
        st.session_state.recovery_mode = "password"
        st.session_state.recovery_verified = True
        st.session_state.password_recovery_active = True
        st.session_state.recovery_otp_sent = False
        st.session_state.show_admin_recovery = True
        st.session_state.show_admin_login = False
        st.session_state.recovery_callback_error = None

        # Token is one-time; remove it from the visible URL after consumption.
        try:
            st.query_params.clear()
        except Exception:
            pass

    except Exception as exc:
        st.session_state.password_recovery_active = False
        st.session_state.recovery_verified = False
        st.session_state.recovery_user_id = None
        st.session_state.recovery_profile = None
        st.session_state.show_admin_recovery = True
        st.session_state.show_admin_login = False
        st.session_state.recovery_mode = "password"
        st.session_state.recovery_callback_error = f"{type(exc).__name__}: {exc}"


def _admin_password_reset_screen():
    """Dedicated Admin password page after a valid recovery link."""
    profile = st.session_state.get("recovery_profile") or {}
    user_id = _safe_text(st.session_state.get("recovery_user_id")).strip()
    _login_visual_header("Reset Admin Password", "Recovery link सत्यापित हो चुका है — अब नया Password बनाइए।", "#2ecc71", "🔐")
    _processing_notice("Admin Password Reset प्रक्रिया शुरू हो गई है।")
    left, right = st.columns([1.0, 1.05], gap="large")
    with left:
        st.markdown('<div class="auth-card"><h3>🔐 Password Recovery</h3><p>आपके Admin account की पहचान सफलतापूर्वक सत्यापित हो गई है।</p><p>अब नीचे नया Password बनाइए।</p><p><b>Registered Email:</b> '+email_html(_safe_text(profile.get("email", "")))+'</p></div>', unsafe_allow_html=True)
    with right:
        with st.container(key="admin_password_reset_form"):
            st.markdown('<h2 style="color:#f4d03f !important;">🔑 नया Admin Password</h2>', unsafe_allow_html=True)
            new_password = st.text_input("नया Password", type="password", key="native_admin_new_password")
            confirm_password = st.text_input("नया Password पुनः दर्ज करें", type="password", key="native_admin_confirm_password")
            with st.container(key="auth_action"):
                if st.button("🔄 Admin Password Reset करें", use_container_width=True, key="native_admin_password_reset_button"):
                    if len(new_password) < 6: st.error("Password कम से कम 6 characters का होना चाहिए।")
                    elif new_password != confirm_password: st.error("दोनों Password समान नहीं हैं।")
                    elif not user_id: st.error("Verified Admin User ID उपलब्ध नहीं है।")
                    else:
                        with st.spinner("🔄 Admin Password update हो रहा है… कृपया प्रतीक्षा करें।"):
                            try:
                                service = _get_service_client()
                                result = service.auth.admin.update_user_by_id(user_id, {"password": new_password})
                                if getattr(result, "user", None) is None: raise RuntimeError("Supabase Admin API ने password update की पुष्टि नहीं की।")
                                try: supabase.auth.sign_out()
                                except Exception: pass
                                st.session_state.password_recovery_active=False; st.session_state.recovery_verified=False; st.session_state.recovery_otp_sent=False; st.session_state.recovery_profile=None; st.session_state.recovery_user_id=None; st.session_state.recovery_email=None; st.session_state.recovery_callback_error=None; st.session_state.show_admin_recovery=False; st.session_state.show_admin_login=True
                                st.success("Admin Password सफलतापूर्वक बदल दिया गया है। अब नए Password से Login करें."); st.rerun()
                            except Exception as exc: st.error(f"Admin Password Reset Error: {type(exc).__name__}: {exc}")


def email_html(value: str) -> str:
    """Minimal HTML escaping for the recovery page."""
    import html
    return html.escape(_safe_text(value))

def _verify_user_identity_for_recovery(email: str, mobile: str):
    """Verify a User using the registered Email + Mobile pair only. No OTP/email is sent."""
    email = _safe_text(email).strip().lower()
    mobile = _safe_text(mobile).strip()
    if not email or not mobile:
        raise RuntimeError("Registered Email और Mobile Number दोनों आवश्यक हैं।")

    profile = _profile_by_identity(mobile, email)
    if not profile or profile.get("role") != "user" or not profile.get("is_active", True):
        raise RuntimeError("Email और Mobile Number का registered User record से मिलान नहीं हुआ।")

    user_id = _safe_text(profile.get("user_id")).strip()
    if not user_id:
        raise RuntimeError("इस User account का Supabase User ID उपलब्ध नहीं है।")

    st.session_state.recovery_email = email
    st.session_state.recovery_user_id = user_id
    st.session_state.recovery_profile = profile
    st.session_state.recovery_verified = True
    st.session_state.recovery_otp_sent = False
    return profile


def _user_password_reset_by_verified_identity(new_password: str):
    """Set User password using the trusted server-side Supabase Admin API."""
    user_id = _safe_text(st.session_state.get("recovery_user_id")).strip()
    profile = st.session_state.get("recovery_profile") or {}
    if not user_id or profile.get("role") != "user":
        raise RuntimeError("Verified User account उपलब्ध नहीं है।")
    service = _get_service_client()
    result = service.auth.admin.update_user_by_id(
        user_id,
        {"password": new_password},
    )
    if getattr(result, "user", None) is None:
        raise RuntimeError("Supabase Admin API ने password update की पुष्टि नहीं की।")


def user_recovery_screen():
    mode = st.session_state.get("recovery_mode") or "password"
    title = "Forgot User ID" if mode == "user_id" else "Forgot Password"
    _login_visual_header(title, "Registered Email + Mobile Number से User verification", "#8e44ad", "🔑")
    _processing_notice("User Recovery प्रक्रिया शुरू हो गई है।")
    left, right = st.columns([1.0, 1.05], gap="large")
    with left:
        st.markdown('<div class="auth-card"><h3>🔐 User Recovery</h3><p>User recovery में OTP या recovery email नहीं भेजा जाएगा।</p><p>Registered Email और Mobile Number का exact match होने पर recovery विकल्प खुलेगा।</p></div>', unsafe_allow_html=True)
    with right:
        with st.container(key="user_recovery_form"):
            email = st.text_input("Registered Email", key="user_recovery_identity_email")
            mobile = st.text_input("Registered Mobile Number", key="user_recovery_identity_mobile")
            if not st.session_state.get("recovery_verified"):
                with st.container(key="user_recovery_verify"):
                    if st.button("✅ Email + Mobile Verify करें", use_container_width=True, key="verify_user_identity_recovery"):
                        with st.spinner("🔄 User details verify हो रहे हैं… कृपया प्रतीक्षा करें।"):
                            try:
                                profile = _verify_user_identity_for_recovery(email, mobile)
                                st.success("Email और Mobile Number verify हो गए हैं।")
                                if mode == "user_id": st.rerun()
                            except Exception as exc:
                                st.error(f"User Verification Error: {type(exc).__name__}: {exc}")
            if st.session_state.get("recovery_verified") and st.session_state.get("recovery_profile"):
                profile = st.session_state.recovery_profile
                if mode == "user_id":
                    st.success(f"आपकी User Login ID: {profile.get('username', '')}")
                else:
                    st.markdown('<h3 style="color:#f4d03f !important;">🔑 नया User Password</h3>', unsafe_allow_html=True)
                    new_password = st.text_input("नया Password", type="password", key="direct_user_recovery_new_password")
                    confirm_password = st.text_input("नया Password पुनः दर्ज करें", type="password", key="direct_user_recovery_confirm_password")
                    with st.container(key="auth_action"):
                        if st.button("🔄 User Password Reset करें", use_container_width=True, key="direct_user_password_reset_button"):
                            if len(new_password) < 6: st.error("Password कम से कम 6 characters का होना चाहिए।")
                            elif new_password != confirm_password: st.error("दोनों Password समान नहीं हैं।")
                            else:
                                with st.spinner("🔄 User Password update हो रहा है… कृपया प्रतीक्षा करें।"):
                                    try:
                                        _user_password_reset_by_verified_identity(new_password)
                                        st.session_state.recovery_verified=False; st.session_state.recovery_otp_sent=False; st.session_state.recovery_profile=None; st.session_state.recovery_user_id=None; st.session_state.recovery_email=None; st.session_state.show_user_recovery=False
                                        st.success("User Password सफलतापूर्वक बदल दिया गया है। अब नए Password से Login करें।"); st.rerun()
                                    except Exception as exc: st.error(f"User Password Reset Error: {type(exc).__name__}: {exc}")
            with st.container(key="back_login_btn"):
                if st.button("↩️ User Login पर वापस जाएँ", key="back_from_user_recovery"):
                    st.session_state.show_user_recovery=False; st.session_state.recovery_verified=False; st.session_state.recovery_otp_sent=False; st.session_state.recovery_profile=None; st.session_state.recovery_user_id=None; st.session_state.recovery_email=None; st.rerun()


# ============================================================
# ADMIN LOGIN
# ============================================================
# ============================================================
def admin_login_screen():
    _login_visual_header("Administrator Login","केवल अधिकृत Administrator के लिए सुरक्षित प्रवेश","#f4d03f","👑")
    _processing_notice("Admin Login प्रक्रिया शुरू हो गई है।")
    left,right=st.columns([1.0,1.05],gap="large")
    with left:
        st.markdown('<div class="auth-card"><h3>👑 Administrator Control</h3><p>सभी users की profile, visitor sessions और module activity केवल Admin को दिखाई देती है।</p><p>एक बार Admin Login के बाद सभी modules उसी session में उपलब्ध रहते हैं।</p><p>Admin User ID और Password recovery में Registered Email + Mobile verification / Password Reset Link का उपयोग होता है।</p></div>',unsafe_allow_html=True)
    with right:
        with st.container(key="admin_login_form"):
            admins=[p for p in _all_profiles() if p.get("role")=="admin" and p.get("is_active",True)]
            if not admins and not _legacy_admin_exists(): st.error("Administrator Account उपलब्ध नहीं है।")
            else:
                username=st.text_input("Admin Login ID",key="admin_login_username"); password=st.text_input("Admin Password",type="password",key="admin_login_password")
                with st.container(key="admin_login_submit"):
                    if st.button("👑 Admin Login करें",use_container_width=True,key="admin_login_button"):
                        with st.spinner("🔄 Admin Login हो रहा है… कृपया प्रतीक्षा करें।"):
                            try:
                                username=username.strip().lower(); profile=_profile_by_username(username)
                                if not profile: profile=_migrate_legacy_user_to_supabase(username,password)
                                if not profile or profile.get("role")!="admin" or not profile.get("is_active",True): raise RuntimeError()
                                auth_user=_supabase_password_login(profile,password); _set_authenticated(profile,auth_user); _record_activity("ADMIN_LOGIN","Authentication","Successful Administrator login"); st.rerun()
                            except Exception: st.error("Admin Login ID या Password गलत है।")
                st.markdown('<hr style="border-color:#2e86c1;">',unsafe_allow_html=True)
                c1,c2=st.columns(2)
                with c1:
                    with st.container(key="admin_id_recovery_btn"):
                        if st.button("🔑 Forgot Admin User ID",use_container_width=True,key="open_admin_id_recovery"):
                            _set_processing_notice("Forgot Admin User ID screen खोला जा रहा है…")
                            st.session_state.show_admin_recovery=True; st.session_state.recovery_mode="user_id"; st.session_state.recovery_otp_sent=False; st.session_state.recovery_verified=False; st.session_state.recovery_profile=None; st.rerun()
                with c2:
                    with st.container(key="admin_password_recovery_btn"):
                        if st.button("🔐 Forgot Admin Password",use_container_width=True,key="open_admin_password_recovery"):
                            _set_processing_notice("Forgot Admin Password screen खोला जा रहा है…")
                            st.session_state.show_admin_recovery=True; st.session_state.recovery_mode="password"; st.session_state.recovery_otp_sent=False; st.session_state.recovery_verified=False; st.session_state.recovery_profile=None; st.rerun()
            with st.container(key="back_login_btn"):
                if st.button("↩️ User Login पर वापस जाएँ",use_container_width=True,key="back_to_user_login"):
                    st.session_state.show_admin_login=False; st.session_state.show_admin_recovery=False; st.rerun()



def _verify_admin_identity_for_recovery(email: str, mobile: str):
    """Verify Admin identity by exact registered Email + Mobile match; no OTP."""
    email = _safe_text(email).strip().lower()
    mobile = _safe_text(mobile).strip()
    if not email or not mobile:
        raise RuntimeError("Registered Admin Email और Mobile Number दोनों आवश्यक हैं।")
    profile = _profile_by_identity(mobile, email)
    if not profile or profile.get("role") != "admin" or not profile.get("is_active", True):
        raise RuntimeError("Email और Mobile Number का registered Admin record से मिलान नहीं हुआ।")
    st.session_state.recovery_email = email
    st.session_state.recovery_profile = profile
    st.session_state.recovery_user_id = _safe_text(profile.get("user_id")).strip()
    st.session_state.recovery_verified = True
    st.session_state.recovery_otp_sent = False
    return profile

def admin_recovery_screen():
    if st.session_state.get("password_recovery_active") and st.session_state.get("recovery_verified"):
        _admin_password_reset_screen(); return
    callback_error = st.session_state.get("recovery_callback_error")
    mode = st.session_state.get("recovery_mode") or "password"
    _login_visual_header("Forgot Admin User ID" if mode == "user_id" else "Forgot Admin Password", "Registered Admin Email से recovery", "#d35400", "👑")
    _processing_notice("Admin Recovery प्रक्रिया शुरू हो गई है।")
    left, right = st.columns([1.0, 1.05], gap="large")
    with left:
        st.markdown('<div class="auth-card"><h3>🔐 Administrator Recovery</h3><p>Admin User ID के लिए Registered Email + Mobile का exact match किया जाएगा। OTP नहीं भेजा जाएगा।</p><p>Admin Password के लिए Supabase Password Reset Email link इस्तेमाल होगा।</p></div>', unsafe_allow_html=True)
    with right:
        with st.container(key="admin_recovery_form"):
            email = st.text_input("Registered Admin Email", key="admin_recovery_email_input")
            mobile = st.text_input("Registered Admin Mobile Number", key="admin_recovery_mobile_input")
            profile = _profile_by_email(email) if email.strip() else None
            if callback_error:
                st.error(f"Password Recovery Error: {callback_error}")
                st.session_state.recovery_callback_error = None
            if mode == "password":
                with st.container(key="admin_password_recovery_btn"):
                    if st.button("📨 Password Reset Email भेजें", use_container_width=True, key="send_admin_password_reset_email"):
                        with st.spinner("🔄 Admin Password Reset Email भेजा जा रहा है… कृपया प्रतीक्षा करें।"):
                            try:
                                if not profile or profile.get("role") != "admin": raise RuntimeError("यह registered Admin Email नहीं है।")
                                _send_admin_password_reset(email)
                                st.session_state.recovery_email = email.strip().lower(); st.session_state.recovery_profile = profile
                                st.success("Password Reset Email भेज दिया गया है। Email खोलकर Reset Password link पर क्लिक करें।")
                            except Exception as exc: st.error(f"Password Reset Email Error: {type(exc).__name__}: {exc}")
            else:
                with st.container(key="admin_recovery_verify"):
                    if st.button("✅ Email + Mobile Verify करके Admin User ID दिखाएँ", use_container_width=True, key="verify_admin_identity_recovery"):
                        with st.spinner("🔄 Admin details verify हो रहे हैं… कृपया प्रतीक्षा करें।"):
                            try:
                                profile = _verify_admin_identity_for_recovery(email, mobile)
                                st.success("Admin Email और Mobile Number verify हो गए हैं।")
                            except Exception as exc: st.error(f"Admin Verification Error: {type(exc).__name__}: {exc}")
                if st.session_state.get("recovery_verified") and st.session_state.get("recovery_profile"):
                    profile = st.session_state.recovery_profile
                    st.success(f"Admin Login ID: {profile.get('username', '')}")
            with st.container(key="back_login_btn"):
                if st.button("↩️ Admin Login पर वापस जाएँ", key="back_from_admin_recovery"):
                    st.session_state.show_admin_recovery=False; st.session_state.recovery_verified=False; st.session_state.recovery_otp_sent=False; st.session_state.recovery_profile=None; st.session_state.recovery_user_id=None; st.session_state.password_recovery_active=False; st.session_state.recovery_callback_error=None; st.rerun()


# ============================================================
# NATIVE ADMIN PASSWORD RECOVERY CALLBACK
# ============================================================
_handle_admin_password_recovery_callback()

# ============================================================
# AUTHENTICATION GATE
# ============================================================
if not st.session_state.authenticated:
    if st.session_state.show_admin_recovery:
        admin_recovery_screen()
    elif st.session_state.show_admin_login:
        admin_login_screen()
    elif st.session_state.show_user_recovery:
        user_recovery_screen()
    elif st.session_state.show_registration:
        registration_screen()
        st.markdown("---")
        if st.button("↩️ User Login पर वापस जाएँ", key="persistent_back_login"):
            st.session_state.show_registration = False
            st.rerun()
    else:
        user_login_screen()
    st.stop()

# ============================================================
# LOGGED-IN USER BAR
# ============================================================
# Refresh profile from Supabase when possible, but NEVER destroy an already
# authenticated Streamlit session merely because a transient Supabase read
# fails during a tab/page switch. The cached profile is authoritative for the
# current session until explicit Logout.
logged_profile = None
try:
    logged_profile = _profile_by_username(st.session_state.get("logged_username"))
except Exception:
    logged_profile = None

if logged_profile:
    st.session_state.logged_profile = dict(logged_profile)
else:
    logged_profile = st.session_state.get("logged_profile")

if not logged_profile:
    _clear_auth_state()
    st.error("User profile उपलब्ध नहीं है। कृपया पुनः Login करें।")
    st.stop()

if logged_profile.get("role") == "admin":
    auth_col1, auth_col2, auth_col3, auth_col4 = st.columns([5, 2, 1.8, 1.2])
    with auth_col1:
        st.caption(
            f"👤 **{logged_profile.get('full_name','')}** "
            f"({logged_profile.get('username','')})"
        )
    with auth_col2:
        st.caption("👑 Administrator")
    with auth_col3:
        if st.button("📊 Visitor Analytics", key="open_visitor_analytics", use_container_width=True):
            st.query_params["visitor_analytics"] = "1"
            st.rerun()
    with auth_col4:
        if st.button("🚪 Logout", key="persistent_logout_admin", use_container_width=True):
            _record_activity("LOGOUT", "Authentication", "Admin logout")
            _clear_auth_state()
            st.rerun()
else:
    auth_col1, auth_col2, auth_col3 = st.columns([6, 2, 1.2])
    with auth_col1:
        st.caption(
            f"👤 **{logged_profile.get('full_name','')}** "
            f"({logged_profile.get('username','')})"
        )
    with auth_col2:
        st.caption("👤 User")
    with auth_col3:
        if st.button("🚪 Logout", key="persistent_logout_user", use_container_width=True):
            _record_activity("LOGOUT", "Authentication", "User logout")
            _clear_auth_state()
            st.rerun()

# User-specific paths must be resolved AFTER successful authentication.
CURRENT_USER_DATA_DIR = get_current_user_data_dir()
PL_DATA_FILE = os.path.join(CURRENT_USER_DATA_DIR, "pl_data.json")
INC_DATA_FILE = os.path.join(CURRENT_USER_DATA_DIR, "increment_data.json")
SAN_DATA_FILE = os.path.join(CURRENT_USER_DATA_DIR, "sanchalan_data.json")
ARREAR_DATA_FILE = os.path.join(CURRENT_USER_DATA_DIR, "arrear_data.json")

# ============================================================
# ADMIN VISITOR ANALYTICS
# ============================================================
def _admin_visitor_analytics_page():
    # Keep the Analytics page on the same dark theme as the main application.
    st.markdown("""
    <style>
      .stApp { background:linear-gradient(135deg,#06162b,#0b2b4a 55%,#123e68) !important; }
      [data-testid="stDataFrame"] { border:1px solid #2e86c1 !important; border-radius:10px !important; overflow:hidden !important; }
      [data-testid="stMetric"] { background:rgba(9,30,53,.92) !important; border:1px solid #2e86c1 !important; border-radius:10px !important; padding:8px !important; }
      [data-testid="stMetricLabel"] p, [data-testid="stMetricValue"] { color:#ffffff !important; }
      [data-baseweb="tab-list"] { background:#0e2338 !important; border-radius:8px !important; }
      [data-baseweb="tab"] { color:#f4d03f !important; }
      [data-testid="stMarkdownContainer"] h1, [data-testid="stMarkdownContainer"] h2,
      [data-testid="stMarkdownContainer"] h3, [data-testid="stMarkdownContainer"] h4,
      [data-testid="stMarkdownContainer"] h5, [data-testid="stMarkdownContainer"] h6,
      [data-testid="stSubheader"] h3 { color:#f4d03f !important; text-shadow:0 1px 0 rgba(0,0,0,.5) !important; }
      [data-testid="stMarkdownContainer"] p, [data-testid="stMarkdownContainer"] li,
      [data-testid="stCaptionContainer"] { color:#eaf2f8 !important; }
      div[data-testid="stDownloadButton"] > button, div[data-testid="stButton"] > button { background:#2980b9 !important; color:#ffffff !important; border:2px solid #3498db !important; box-shadow:0 4px 0 #1b4f72 !important; font-weight:800 !important; }
      div[data-testid="stButton"]:has(button[aria-label="⬅️ मुख्य Dashboard पर वापस जाएँ"]) { order:-999 !important; }
      div[class*="st-key-close_visitor_analytics_top"] button { background:#d35400 !important; color:#fff !important; border:2px solid #e67e22 !important; box-shadow:0 4px 0 #a04000 !important; font-weight:900 !important; }
      div[class*="st-key-close_visitor_analytics_top"] button:hover { background:#e67e22 !important; }
    </style>
    """, unsafe_allow_html=True)
    if st.button("⬅️ मुख्य Dashboard पर वापस जाएँ", key="close_visitor_analytics_top"):
        st.query_params.pop("visitor_analytics", None)
        st.rerun()

    st.markdown("""
    <div style="background:linear-gradient(135deg,#154360,#1f618d);
    padding:18px;border-radius:12px;margin-bottom:18px;text-align:center;">
        <h2 style="color:#f4d03f !important;margin:0;">📊 Visitor Analytics & User Activity</h2>
        <p style="color:#eaf2f8 !important;margin:5px 0 0 0;">
        Registered Users, Visits और Module Activity
        </p>
    </div>
    """, unsafe_allow_html=True)

    profiles = _all_profiles()
    activity_records = _read_events("__activity__")
    visitor_records = _read_events("__visitor__")

    activities = []
    for row in activity_records:
        item = row.get("data") or {}
        activities.append(item)

    visitor_rows = []
    for row in visitor_records:
        item = row.get("data") or {}
        visitor_rows.append(item)

    module_counts = {}
    for item in activities:
        if item.get("activity") == "MODULE_OPEN":
            module = item.get("module") or "-"
            module_counts[module] = module_counts.get(module, 0) + 1

    today = datetime.now().strftime("%d-%m-%Y")
    total_users = len(profiles)
    total_logins = sum(
        1 for a in activities
        if a.get("activity") in ("LOGIN", "ADMIN_LOGIN")
    )
    today_visits = sum(1 for r in visitor_rows if r.get("Date") == today)
    unique_sessions = len({
        r.get("Session ID") for r in visitor_rows if r.get("Session ID")
    })
    active_users = sum(1 for p in profiles if p.get("is_active", True))
    total_module_opens = sum(module_counts.values())

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("👥 Registered Users", total_users)
    c2.metric("🔐 Total Logins", total_logins)
    c3.metric("📅 आज की Visits", today_visits)
    c4.metric("🔵 Unique Sessions", unique_sessions)
    c5.metric("🟢 Active Users", active_users)
    c6.metric("🧩 Module Opens", total_module_opens)

    st.markdown("---")
    tab1, tab2, tab3 = st.tabs(["👥 Users", "🧩 Module Activity", "🕒 Activity History"])

    with tab1:
        user_rows = [{
            "नाम": p.get("full_name", ""),
            "पता": p.get("address", ""),
            "मोबाइल": p.get("mobile", ""),
            "Email": p.get("email", ""),
            "Login ID": p.get("username", ""),
            "Role": "Administrator" if p.get("role") == "admin" else "User",
            "Status": "Active" if p.get("is_active", True) else "Inactive",
        } for p in profiles]
        if user_rows:
            st.dataframe(user_rows, use_container_width=True, hide_index=True)
        else:
            st.info("अभी कोई registered user नहीं है।")

    with tab2:
        module_rows = [
            {"Module": k, "कुल बार खोला गया": v}
            for k, v in sorted(
                module_counts.items(), key=lambda x: x[1], reverse=True
            )
        ]
        if module_rows:
            st.dataframe(module_rows, use_container_width=True, hide_index=True)
        else:
            st.info("अभी module activity उपलब्ध नहीं है।")

    with tab3:
        activity_rows = [{
            "Login ID": a.get("username", ""),
            "Activity": a.get("activity", ""),
            "Module": a.get("module") or "-",
            "समय": a.get("activity_time", ""),
            "Session ID": a.get("session_id", ""),
            "विवरण": a.get("details") or "",
        } for a in activities]
        if activity_rows:
            st.dataframe(activity_rows, use_container_width=True, hide_index=True)
        else:
            st.info("अभी activity history उपलब्ध नहीं है।")

    st.markdown("---")
    st.subheader("📋 Visitor Session Records")
    if visitor_rows:
        st.dataframe(visitor_rows, use_container_width=True, hide_index=True)
        csv_text = ""
        try:
            import csv
            import io
            output = io.StringIO()
            fields = [
                "Visitor ID", "Date", "Time", "Module",
                "Session ID", "Username"
            ]
            writer = csv.DictWriter(output, fieldnames=fields)
            writer.writeheader()
            writer.writerows(visitor_rows)
            csv_text = output.getvalue()
        except Exception:
            pass
        if csv_text:
            st.download_button(
                "⬇️ Visitor CSV डाउनलोड करें",
                data=csv_text.encode("utf-8-sig"),
                file_name="visitor_report.csv",
                mime="text/csv",
                key="download_admin_visitor_report",
            )
    else:
        st.info("अभी visitor session record उपलब्ध नहीं है।")

if st.query_params.get("visitor_analytics") == "1":
    if st.session_state.get("logged_role") == "admin":
        _admin_visitor_analytics_page()
    else:
        st.error("⛔ यह पृष्ठ केवल Administrator के लिए है।")
    st.stop()

# ============================================================
# MODULE ACTIVITY TRACKING
# ============================================================
params = st.query_params
active_page = params.get("page", "dashboard")

if st.session_state.get("authenticated") and st.session_state.get("logged_username"):
    _module_names = {
        "dashboard": "Main Dashboard",
        "pl_surrender": "PL Surrender",
        "increment_order": "Annual Increment",
        "sanchalan_portal": "Sanchalan Portal",
        "salary_arrear": "Salary Arrear",
    }
    _module_name = _module_names.get(str(active_page), str(active_page))
    if st.session_state.get("last_tracked_module") != _module_name:
        _record_activity(
            "MODULE_OPEN",
            _module_name,
            f"page={active_page}",
        )
        st.session_state["last_tracked_module"] = _module_name
        _visitor_record_visit(_module_name)

# ============================================================
# END INTEGRATED AUTH/SUPABASE LAYER
# ============================================================


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
    return _shared_image_base64()[0]

img_b64,img_mime=_shared_image_base64()

def generate_sun_rays_svg():
    return _shared_sun_rays_svg("spinning-rays")

rays_svg_html=generate_sun_rays_svg()

st.markdown("""
<style>
    /* During a Streamlit rerun, hide the previous Login render instead of
       keeping it visible. The dark app background prevents a white flash. */
    [data-stale="true"] {
        opacity:0 !important;
        visibility:hidden !important;
        pointer-events:none !important;
        transition:none !important;
        filter:none !important;
    }
    [data-testid="stAppViewBlockContainer"],
    [data-testid="stMainBlockContainer"] { transition:none !important; }
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
        overflow: visible;
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

    /* Dashboard-only navigation colors. The selectors are scoped to the
       exact module button text so buttons INSIDE the original modules keep
       their original appearance. */
    div[data-testid="stButton"]:has(button[aria-label^="1. उपार्जित अवकाश समर्पण"]) > button {
        background-color: #1f618d !important; border: 2px solid #2980b9 !important;
        box-shadow: 0 4px 0 #154360 !important; border-radius: 8px !important;
    }
    div[data-testid="stButton"]:has(button[aria-label^="1. उपार्जित अवकाश समर्पण"]) > button:hover { background-color: #2980b9 !important; }

    div[data-testid="stButton"]:has(button[aria-label^="2. वार्षिक सामयिक वेतन वृद्धि"]) > button {
        background-color: #27ae60 !important; border: 2px solid #2ecc71 !important;
        box-shadow: 0 4px 0 #1e8449 !important; border-radius: 8px !important;
    }
    div[data-testid="stButton"]:has(button[aria-label^="2. वार्षिक सामयिक वेतन वृद्धि"]) > button:hover { background-color: #2ecc71 !important; }

    div[data-testid="stButton"]:has(button[aria-label^="3. संचालन पोर्टल भुगतान स्वीकृति"]) > button {
        background-color: #8e44ad !important; border: 2px solid #9b59b6 !important;
        box-shadow: 0 4px 0 #512e5f !important; border-radius: 8px !important;
    }
    div[data-testid="stButton"]:has(button[aria-label^="3. संचालन पोर्टल भुगतान स्वीकृति"]) > button:hover { background-color: #9b59b6 !important; }

    div[data-testid="stButton"]:has(button[aria-label^="4. वेतन एरियर"]) > button {
        background-color: #d35400 !important; border: 2px solid #e67e22 !important;
        box-shadow: 0 4px 0 #a04000 !important; border-radius: 8px !important;
    }
    div[data-testid="stButton"]:has(button[aria-label^="4. वेतन एरियर"]) > button:hover { background-color: #e67e22 !important; }

    div[data-testid="stButton"]:has(button[aria-label="⬅ मुख्य डैशबोर्ड पर वापस जाएँ"]) > button {
        background-color: #c0392b !important; border: 1px solid #e74c3c !important;
        box-shadow: none !important; border-radius: 6px !important;
    }
    div[data-testid="stButton"]:has(button[aria-label="⬅ मुख्य डैशबोर्ड पर वापस जाएँ"]) > button:hover { background-color: #e74c3c !important; }

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

    /* FINAL dashboard module colors: key-scoped selectors are placed after
       the generic Streamlit button rule so the generic blue cannot override them. */
    div[class*="st-key-module_nav_pl"] button { background:#1f618d !important; border:2px solid #2980b9 !important; box-shadow:0 4px 0 #154360 !important; color:#fff !important; text-align:left !important; justify-content:flex-start !important; }
    div[class*="st-key-module_nav_inc"] button { background:#27ae60 !important; border:2px solid #2ecc71 !important; box-shadow:0 4px 0 #1e8449 !important; color:#fff !important; text-align:left !important; justify-content:flex-start !important; }
    div[class*="st-key-module_nav_sna"] button { background:#8e44ad !important; border:2px solid #9b59b6 !important; box-shadow:0 4px 0 #6c3483 !important; color:#fff !important; text-align:left !important; justify-content:flex-start !important; }
    div[class*="st-key-module_nav_arr"] button { background:#d35400 !important; border:2px solid #e67e22 !important; box-shadow:0 4px 0 #a04000 !important; color:#fff !important; text-align:left !important; justify-content:flex-start !important; }
    div[class*="st-key-module_nav_pl"] button:hover { background:#2980b9 !important; }
    div[class*="st-key-module_nav_inc"] button:hover { background:#2ecc71 !important; }
    div[class*="st-key-module_nav_sna"] button:hover { background:#9b59b6 !important; }
    div[class*="st-key-module_nav_arr"] button:hover { background:#e67e22 !important; }
    /* Streamlit button content is flex-based; align the inner content, not only the button box. */
    div[class*="st-key-module_nav_pl"] button > div,
    div[class*="st-key-module_nav_inc"] button > div,
    div[class*="st-key-module_nav_sna"] button > div,
    div[class*="st-key-module_nav_arr"] button > div { width:100% !important; justify-content:flex-start !important; text-align:left !important; }
    div[class*="st-key-module_nav_pl"] button p,
    div[class*="st-key-module_nav_inc"] button p,
    div[class*="st-key-module_nav_sna"] button p,
    div[class*="st-key-module_nav_arr"] button p { width:100% !important; text-align:left !important; margin:0 !important; }


    /* Every module's Main Dashboard button uses the requested orange-red. */
    div[class*="st-key-back_dashboard_pl"] button,
    div[class*="st-key-back_dashboard_increment"] button,
    div[class*="st-key-back_dashboard_sanchalan"] button,
    div[class*="st-key-back_dashboard_arrear"] button {
        background:#d35400 !important; border:2px solid #e67e22 !important;
        box-shadow:0 4px 0 #a04000 !important; color:#fff !important;
        font-weight:900 !important; border-radius:8px !important;
    }
    div[class*="st-key-back_dashboard_pl"] button:hover,
    div[class*="st-key-back_dashboard_increment"] button:hover,
    div[class*="st-key-back_dashboard_sanchalan"] button:hover,
    div[class*="st-key-back_dashboard_arrear"] button:hover { background:#e67e22 !important; }

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

# Record which module the logged-in user is currently using.
# This does not change any module logic; it only writes an activity row.
if st.session_state.get("authenticated") and st.session_state.get("logged_username"):
    _module_names = {
        "dashboard": "Main Dashboard",
        "pl_surrender": "PL Surrender",
        "increment_order": "Annual Increment",
        "sanchalan_portal": "Sanchalan Portal",
        "salary_arrear": "Salary Arrear",
    }
    _module_name = _module_names.get(str(active_page), str(active_page))
    if st.session_state.get("last_tracked_module") != _module_name:
        save_activity(
            st.session_state["logged_username"],
            "MODULE_OPEN",
            _module_name,
            f"page={active_page}",
        )
        st.session_state["last_tracked_module"] = _module_name
        _visitor_record_visit(_module_name)

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


def _build_arrear_excel_workbook(emp: dict, office_data: dict):
    from io import BytesIO
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Border, Side, Alignment, Protection
    from openpyxl.utils import get_column_letter
    from openpyxl.worksheet.page import PageMargins

    rows=emp.get("monthly_rows",[]) or []
    wb=Workbook(); inp=wb.active; inp.title="MASTER_INPUT"; calc=wb.create_sheet("CALCULATION"); stmt=wb.create_sheet("ARREAR_STATEMENT"); ref=wb.create_sheet("FORMULA_REFERENCE")
    thin=Side(style="thin",color="000000"); med=Side(style="medium",color="000000"); border=Border(left=thin,right=thin,top=thin,bottom=thin)
    fills={"dark":PatternFill("solid",fgColor="34495E"),"blue":PatternFill("solid",fgColor="2471A3"),"purple":PatternFill("solid",fgColor="7D3C98"),"orange":PatternFill("solid",fgColor="B9770E"),"red":PatternFill("solid",fgColor="884C3C"),"green":PatternFill("solid",fgColor="1E8449"),"light":PatternFill("solid",fgColor="EAF2F8"),"total":PatternFill("solid",fgColor="F4F6F7"),"net":PatternFill("solid",fgColor="E8F8F0"),"white":PatternFill("solid",fgColor="FFFFFF")}
    # Input sheet
    headers=["माह एवं वर्ष","कार्य दिवस","माह के दिन","देय DA %","आहरित DA %","HRA %","देय मूल वेतन ₹","आहरित मूल वेतन ₹","देय GPF ₹","आहरित GPF ₹","देय RGHS ₹","आहरित RGHS ₹","देय SI ₹","आहरित SI ₹","GPF में जमा DA एरियर ₹","आयकर ₹","अन्य कटौतियाँ ₹"]
    inp.merge_cells("A1:Q1"); inp["A1"]="MASTER INPUT — केवल यहाँ input values बदलें"; inp["A1"].fill=fills["dark"]; inp["A1"].font=Font(color="FFFFFF",bold=True,size=14); inp["A1"].alignment=Alignment(horizontal="center")
    inp["A2"]="Editable input sheet. CALCULATION और ARREAR_STATEMENT की formulas protected हैं."; inp["A2"].font=Font(color="C0392B",italic=True)
    for c,h in enumerate(headers,1):
        x=inp.cell(3,c,h); x.fill=fills["dark"]; x.font=Font(color="FFFFFF",bold=True); x.alignment=Alignment(horizontal="center",vertical="center",wrap_text=True); x.border=border
    for i,r in enumerate(rows,4):
        vals=[r.get("month_year",""),r.get("worked_days",0),r.get("days_in_month",0),r.get("da_pct",0),r.get("cash_da_pct",r.get("da_pct",0)),r.get("hra_pct",0),r.get("due_basic",0),r.get("drawn_basic",0),r.get("due_gpf",0),max(0,float(r.get("due_gpf",0) or 0)-float(r.get("diff_gpf",0) or 0)),r.get("due_rghs",0),max(0,float(r.get("due_rghs",0) or 0)-float(r.get("diff_rghs",0) or 0)),r.get("due_si",0),max(0,float(r.get("due_si",0) or 0)-float(r.get("diff_si",0) or 0)),r.get("gpf_deposit",0),r.get("income_tax",0),r.get("other_ded",0)]
        for c,v in enumerate(vals,1):
            x=inp.cell(i,c,v); x.fill=fills["white"]; x.border=border; x.alignment=Alignment(horizontal="center",vertical="center",wrap_text=True); x.protection=Protection(locked=False); x.number_format='0.00' if c in (4,5) else '#,##0'
    for c,w in enumerate([18,11,11,9,10,9,16,16,14,15,14,15,12,14,18,12,15],1): inp.column_dimensions[get_column_letter(c)].width=w
    inp.freeze_panes="A4"; inp.sheet_view.showGridLines=False

    # Calculation sheet: all formulas.
    ch=["क्र.","माह एवं वर्ष","DA %","HRA %","देय मूल वेतन","देय DA","देय HRA","देय कुल","आहरित मूल वेतन","आहरित DA","आहरित HRA","आहरित कुल","मूल वेतन अंतर","DA अंतर","HRA अंतर","कुल अंतर","GPF अंतर","RGHS अंतर","SI अंतर","GPF में जमा DA एरियर","आयकर","अन्य कटौतियाँ","कटौतियों का कुल योग","शुद्ध देय राशि"]
    for c,h in enumerate(ch,1):
        x=calc.cell(1,c,h); x.fill=fills["dark"]; x.font=Font(color="FFFFFF",bold=True); x.alignment=Alignment(horizontal="center",wrap_text=True); x.border=border
    for i in range(len(rows)):
        rr=i+2; ir=i+4
        fs=[i+1,f"=MASTER_INPUT!A{ir}",f"=MASTER_INPUT!D{ir}",f"=MASTER_INPUT!F{ir}",f"=MASTER_INPUT!G{ir}",f"=E{rr}*C{rr}/100",f"=E{rr}*D{rr}/100",f"=SUM(E{rr}:G{rr})",f"=MASTER_INPUT!H{ir}",f"=I{rr}*MASTER_INPUT!E{ir}/100",f"=I{rr}*D{rr}/100",f"=SUM(I{rr}:K{rr})",f"=MAX(0,E{rr}-I{rr})",f"=MAX(0,F{rr}-J{rr})",f"=MAX(0,G{rr}-K{rr})",f"=SUM(M{rr}:O{rr})",f"=MAX(0,MASTER_INPUT!I{ir}-MASTER_INPUT!J{ir})",f"=MAX(0,MASTER_INPUT!K{ir}-MASTER_INPUT!L{ir})",f"=MAX(0,MASTER_INPUT!M{ir}-MASTER_INPUT!N{ir})",f"=MASTER_INPUT!O{ir}",f"=MASTER_INPUT!P{ir}",f"=MASTER_INPUT!Q{ir}",f"=SUM(Q{rr}:V{rr})",f"=MAX(0,P{rr}-W{rr})"]
        for c,v in enumerate(fs,1):
            x=calc.cell(rr,c,v); x.border=border; x.alignment=Alignment(horizontal="center",vertical="center",wrap_text=True); x.protection=Protection(locked=True); x.number_format='0.00' if c in (3,4) else '#,##0'
    total=len(rows)+2; calc.cell(total,2,"कुल योग").font=Font(bold=True)
    for c in range(5,25):
        col=get_column_letter(c); x=calc.cell(total,c,f"=SUM({col}2:{col}{total-1})"); x.fill=fills["total"]; x.font=Font(bold=True); x.border=border; x.number_format='#,##0'
    for c in range(1,25): calc.column_dimensions[get_column_letter(c)].width=13
    calc.sheet_view.showGridLines=False; calc.freeze_panes="A2"; calc.protection.sheet=True; calc.protection.set_password("ARREAR_FORMULA_LOCK")

    # Statement sheet: 22 columns, white printable layout matching PDF.
    stmt.sheet_view.showGridLines=False
    stmt.merge_cells("A1:V1"); stmt["A1"]=f"कार्यालय {office_data.get('office_name','')}"; stmt["A1"].font=Font(size=16,bold=True); stmt["A1"].alignment=Alignment(horizontal="center"); stmt["A1"].fill=fills["white"]
    stmt.merge_cells("A2:V2"); stmt["A2"]="अंतर विवरण प्रपत्र — वेतन एरियर (SALARY ARREAR STATEMENT)"; stmt["A2"].font=Font(size=11,bold=True); stmt["A2"].alignment=Alignment(horizontal="center"); stmt["A2"].fill=fills["white"]
    info=[("A3:F3",f"कर्मचारी का नाम: {emp.get('emp_name','')}"),("G3:J3",f"Employee ID: {emp.get('employee_id','')}"),("K3:P3",f"पद: {emp.get('designation','')}"),("Q3:V3",f"PAN: {emp.get('pan','')}"),("A4:F4",f"खाता संख्या: {emp.get('account','')} ({emp.get('bank','')})"),("G4:J4",f"एरियर अवधि: {emp.get('start_date','')} से {emp.get('end_date','')}"),("K4:P4",f"कारण: {emp.get('reason','')}"),("Q4:V4",f"Pay Level: {emp.get('old_pay_level','-')} → {emp.get('new_pay_level','-')}")]
    for rng,val in info: stmt.merge_cells(rng); x=stmt[rng.split(':')[0]]; x.value=val; x.font=Font(size=8,bold=True); x.alignment=Alignment(wrap_text=True,vertical="center"); x.fill=fills["white"]
    stmt.merge_cells("A6:A8"); stmt["A6"]="क्र.\nसं."; stmt.merge_cells("B6:B8"); stmt["B6"]="माह एवं वर्ष\nDA % | HRA % | दिन"; stmt.merge_cells("C6:N6"); stmt["C6"]="आय"; stmt.merge_cells("C7:F7"); stmt["C7"]="देय वेतन"; stmt.merge_cells("G7:J7"); stmt["G7"]="आहरित वेतन"; stmt.merge_cells("K7:N7"); stmt["K7"]="अंतर"; stmt.merge_cells("O6:U6"); stmt["O6"]="कटौतियाँ"; stmt.merge_cells("V6:V8"); stmt["V6"]="शुद्ध देय राशि"
    for cell,fill in [("A6","dark"),("B6","dark"),("C6","blue"),("C7","purple"),("G7","blue"),("K7","orange"),("O6","red"),("V6","green")]: stmt[cell].fill=fills[fill]; stmt[cell].font=Font(color="FFFFFF",bold=True); stmt[cell].alignment=Alignment(horizontal="center",vertical="center",wrap_text=True)
    subs=["मूल वेतन","महंगाई भत्ता","मकान किराया भत्ता","कुल योग","मूल वेतन","महंगाई भत्ता","मकान किराया भत्ता","कुल योग","मूल वेतन का अंतर","महंगाई भत्ते का अंतर","मकान किराये का अंतर","कुल योग का अंतर","GPF अंतर","RGHS अंतर","SI अंतर","GPF में जमा DA एरियर","आयकर","अन्य कटौतियाँ","कटौतियों का कुल योग"]
    for c,h in enumerate(subs,3): stmt.cell(8,c,h).fill=fills["light"]; stmt.cell(8,c).font=Font(bold=True,size=7); stmt.cell(8,c).alignment=Alignment(horizontal="center",vertical="center",wrap_text=True); stmt.cell(8,c).border=border
    for i in range(len(rows)):
        sr=9+i; cr=2+i; stmt.cell(sr,1,f"=CALCULATION!A{cr}"); stmt.cell(sr,2,f'=CALCULATION!B{cr}&CHAR(10)&"DA "&TEXT(CALCULATION!C{cr},"0")&"% | HRA "&TEXT(CALCULATION!D{cr},"0")&"% | "&MASTER_INPUT!B{i+4}&"/"&MASTER_INPUT!C{i+4}&" दिन"')
        for c,src in enumerate(range(5,25),3): stmt.cell(sr,c,f"=CALCULATION!{get_column_letter(src)}{cr}")
        for c in range(1,23): stmt.cell(sr,c).border=border; stmt.cell(sr,c).alignment=Alignment(horizontal="center",vertical="center",wrap_text=True); stmt.cell(sr,c).number_format='#,##0'; stmt.cell(sr,c).protection=Protection(locked=True)
    tr=9+len(rows); stmt.cell(tr,2,"कुल योग").font=Font(bold=True)
    for c in range(3,23):
        src=get_column_letter(c+2); x=stmt.cell(tr,c,f"=SUM(CALCULATION!{src}2:{src}{total-1})"); x.fill=fills["total"]; x.font=Font(bold=True); x.border=border; x.number_format='#,##0'
    sr=tr+2; stmt.merge_cells(start_row=sr,start_column=1,end_row=sr,end_column=22); stmt.cell(sr,1,"सारांश").fill=fills["light"]; stmt.cell(sr,1).font=Font(bold=True,size=10)
    summary=[("ग्रॉस देय राशि",f"=SUM(CALCULATION!P2:P{total-1})"),("ग्रॉस रिडक्शन / कुल कटौती",f"=SUM(CALCULATION!W2:W{total-1})"),("शुद्ध देय राशि",f"=SUM(CALCULATION!X2:X{total-1})")]
    for rr,(label,formula) in enumerate(summary,sr+1):
        stmt.merge_cells(start_row=rr,start_column=1,end_row=rr,end_column=17); stmt.cell(rr,1,label).font=Font(bold=True); stmt.merge_cells(start_row=rr,start_column=18,end_row=rr,end_column=22); stmt.cell(rr,18,formula).font=Font(bold=True,size=9); stmt.cell(rr,18).number_format='₹ #,##0';
        for c in range(1,23): stmt.cell(rr,c).border=border
        if label=="शुद्ध देय राशि":
            for c in range(1,23): stmt.cell(rr,c).fill=fills["net"]
    aw=sr+5; stmt.merge_cells(start_row=aw,start_column=1,end_row=aw,end_column=22); stmt.cell(aw,1,"शुद्ध देय राशि शब्दों में: कृपया राशि बदलने पर इस पंक्ति को आवश्यकतानुसार अपडेट करें।").alignment=Alignment(wrap_text=True)
    cert=aw+2; stmt.merge_cells(start_row=cert,start_column=1,end_row=cert,end_column=22); stmt.cell(cert,1,"प्रमाणीकरण: प्रमाणित किया जाता है कि उपर्युक्त एरियर राशि का भुगतान पहले किसी अन्य बिल के साथ नहीं किया गया है। यदि भविष्य में यह पाया जाता है कि उक्त राशि का भुगतान पहले किया जा चुका है, तो उक्त राशि की रिकवरी नियमानुसार की जाए।").alignment=Alignment(wrap_text=True,vertical="top"); stmt.cell(cert,1).font=Font(size=8)
    sig=cert+3
    for startcol,endcol,text in [(1,7,"कर्मचारी के हस्ताक्षर\n\nनाम: ____________________"),(8,14,"लिपिक के हस्ताक्षर\n\nनाम: ____________________"),(15,22,"संस्था प्रधान के हस्ताक्षर\n\nनाम/मुहर: ____________________")]:
        stmt.merge_cells(start_row=sig,start_column=startcol,end_row=sig+2,end_column=endcol); stmt.cell(sig,startcol,text).alignment=Alignment(horizontal="center",vertical="center",wrap_text=True); stmt.cell(sig,startcol).border=border
    foot=sig+4; stmt.merge_cells(start_row=foot,start_column=1,end_row=foot,end_column=22); stmt.cell(foot,1,"सॉफ्टवेयर डेवलपर: आलोक कुमार सिंह, वरिष्ठ अध्यापक, राजकीय उच्च माध्यमिक विद्यालय, रोजड़ी | ईमेल: alokjobner@gmail.com").font=Font(size=7,italic=True,color="333333")
    for c,w in enumerate([5,16]+[9]*20,1): stmt.column_dimensions[get_column_letter(c)].width=w
    for r in range(1,foot+1):
        for c in range(1,23):
            if stmt.cell(r,c).fill.fill_type is None: stmt.cell(r,c).fill=fills["white"]
            if r>=6: stmt.cell(r,c).border=border
    for r in (6,7,8): stmt.row_dimensions[r].height=30
    stmt.freeze_panes="C9"; stmt.page_setup.orientation="landscape"; stmt.page_setup.paperSize=stmt.PAPERSIZE_A4; stmt.page_setup.fitToWidth=1; stmt.page_setup.fitToHeight=0; stmt.sheet_properties.pageSetUpPr.fitToPage=True; stmt.page_margins=PageMargins(left=.2,right=.2,top=.3,bottom=.3,header=.1,footer=.1); stmt.print_title_rows="1:8"; stmt.print_area=f"A1:V{foot}"; stmt.oddFooter.center.text="Page &P of &N"; stmt.protection.sheet=True; stmt.protection.set_password("ARREAR_STATEMENT_LOCK")

    ref.append(["Sheet","Purpose"]); ref.append(["MASTER_INPUT","केवल input values बदलें"]); ref.append(["CALCULATION","सभी calculation formulas protected"]); ref.append(["ARREAR_STATEMENT","PDF जैसा white printable statement; formulas protected"])
    for row in ref.iter_rows():
        for x in row: x.border=border; x.alignment=Alignment(wrap_text=True,vertical="top")
    ref.column_dimensions["A"].width=25; ref.column_dimensions["B"].width=80; ref.sheet_view.showGridLines=False
    bio=BytesIO(); wb.save(bio); bio.seek(0); return bio.getvalue()


def _show_module_cloud_status(module_key):
    if not st.session_state.get("authenticated"): return
    saved=st.session_state.get(f"supabase_saved_{module_key}")
    if saved is True: st.caption(f"☁️ Supabase: {module_key} data सुरक्षित रूप से saved | {st.session_state.get(f'supabase_saved_at_{module_key}','')}")
    elif saved is False: st.warning(f"⚠️ Supabase: {module_key} data का पिछला save असफल रहा था।")

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
                <div class="profile-center-img" style="background-image: url('data:{img_mime};base64,{img_b64}');"></div>
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

        # IMPORTANT: Do not use full-page HTML href navigation here.
        # A full href (/?page=...) can create a new Streamlit browser session,
        # which resets st.session_state and appears as an unexpected logout.
        # Streamlit buttons keep the same WebSocket/session while changing the
        # query parameter, so one login remains valid across all modules.
        with st.container(key="module_nav_pl"):
            if st.button("1. उपार्जित अवकाश समर्पण (PL Surrender) आदेश जनरेटर ▶", key="nav_pl_surrender", use_container_width=True):
                st.query_params["page"] = "pl_surrender"; st.rerun()
        with st.container(key="module_nav_inc"):
            if st.button("2. वार्षिक सामयिक वेतन वृद्धि (Annual Increment) आदेश जनरेटर ▶", key="nav_increment_order", use_container_width=True):
                st.query_params["page"] = "increment_order"; st.rerun()
        with st.container(key="module_nav_sna"):
            if st.button("3. संचालन पोर्टल भुगतान स्वीकृति आदेश (SNA Sanction Order) जनरेटर ▶", key="nav_sanchalan_portal", use_container_width=True):
                st.query_params["page"] = "sanchalan_portal"; st.rerun()
        with st.container(key="module_nav_arr"):
            if st.button("4. वेतन एरियर (Salary Arrear) अंतर विवरण प्रपत्र एवं गणना (7th CPC Landscape) ▶", key="nav_salary_arrear", use_container_width=True):
                st.query_params["page"] = "salary_arrear"; st.rerun()
        st.markdown('<div class="menu-btn-rel">5. कार्यमुक्ति / कार्यग्रहण (Relieving / Joining) आदेश [शीघ्र उपलब्ध]</div>', unsafe_allow_html=True)

# =============================================================================
# पृष्ठ 2: उपार्जित अवकाश समर्पण (PL Surrender) विंडो
# =============================================================================
elif active_page == "pl_surrender":
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
    _show_module_cloud_status("sanchalan_portal")
    if st.button("⬅ मुख्य डैशबोर्ड पर वापस जाएँ", key="back_dashboard_sanchalan", use_container_width=False):
        st.query_params["page"] = "dashboard"
        st.rerun()

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

        try:
            excel_bytes = _build_arrear_excel_workbook(emp, st.session_state.arr_office or {})
            st.download_button(
                label="📊 Salary Arrear Statement — PDF जैसा Formula Excel डाउनलोड करें",
                data=excel_bytes,
                file_name=f"Arrear_Statement_Formula_{emp.get('emp_name','employee').replace(' ','_')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="download_arrear_formula_excel",
            )
        except Exception as exc:
            st.error(f"Excel workbook बनाने में त्रुटि: {type(exc).__name__}: {exc}")

