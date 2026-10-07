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
header[data-testid="stHeader"] {
    background:#123e68 !important;
    border-bottom:1px solid rgba(93,173,226,.35) !important;
    opacity:1 !important; visibility:visible !important;
    z-index:999999 !important;
}
header[data-testid="stHeader"] [data-testid="stToolbar"],
header[data-testid="stHeader"] [data-testid="stToolbarActions"],
header[data-testid="stHeader"] [data-testid="stDecoration"],
[data-testid="stStatusWidget"] {
    opacity:1 !important; visibility:visible !important;
    pointer-events:auto !important;
}
header[data-testid="stHeader"] [data-testid="stToolbar"] button,
header[data-testid="stHeader"] [data-testid="stToolbarActions"] button,
[data-testid="stStatusWidget"] button {
    color:#ffffff !important;
    fill:#ffffff !important;
    opacity:1 !important; visibility:visible !important;
    background:#1f618d !important;
    border:1px solid #5dade2 !important;
    border-radius:7px !important;
}
header[data-testid="stHeader"] [data-testid="stToolbar"] button:hover,
header[data-testid="stHeader"] [data-testid="stToolbarActions"] button:hover,
[data-testid="stStatusWidget"] button:hover {
    background:#2980b9 !important; color:#ffffff !important;
}
[data-testid="stStatusWidget"] { background:#123e68 !important; color:#ffffff !important; }
[data-testid="stDecoration"] { background:#123e68 !important; }
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
    [data-testid="stStatusWidget"], [data-testid="stDecoration"] { background:#123e68 !important; opacity:1 !important; visibility:visible !important; }
    header[data-testid="stHeader"] { background:#123e68 !important; opacity:1 !important; visibility:visible !important; }

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
    /* Date picker styling is defined in the dashboard stylesheet below so it
       can target both Streamlit React-Aria (1.62+) and legacy BaseWeb pickers. */

    div[class*="st-key-module_nav_pl"] button { background:#1f618d !important; border:2px solid #2980b9 !important; box-shadow:0 4px 0 #154360 !important; color:#fff !important; }
    div[class*="st-key-module_nav_master"] button { background:#2980b9 !important; border:2px solid #3498db !important; box-shadow:0 4px 0 #21618c !important; color:#fff !important; }
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
        "master_data": "Master Data Management",
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
    'L-1': [17700, 18200, 18700, 19300, 19900, 20500, 21100, 21700, 22400, 23100, 23800, 24500, 25200, 26000, 26800, 27600, 28400, 29300, 30200, 31100, 32000, 33000, 34000, 35000, 36100, 37200, 38300, 39400, 40600, 41800, 43100, 44400, 45700, 47100, 48500, 50000, 51500, 53000, 54600, 56200],
    'L-2': [17900, 18400, 19000, 19600, 20200, 20800, 21400, 22000, 22700, 23400, 24100, 24800, 25500, 26300, 27100, 27900, 28700, 29600, 30500, 31400, 32300, 33300, 34300, 35300, 36400, 37500, 38600, 39800, 41000, 42200, 43500, 44800, 46100, 47500, 48900, 50400, 51900, 53500, 55100, 56800],
    'L-3': [18200, 18700, 19300, 19900, 20500, 21100, 21700, 22400, 23100, 23800, 24500, 25200, 26000, 26800, 27600, 28400, 29300, 30200, 31100, 32000, 33000, 34000, 35000, 36100, 37200, 38300, 39400, 40600, 41800, 43100, 44400, 45700, 47100, 48500, 50000, 51500, 53000, 54600, 56200, 57900],
    'L-4': [19200, 19800, 20400, 21000, 21600, 22200, 22900, 23600, 24300, 25000, 25800, 26600, 27400, 28200, 29000, 29900, 30800, 31700, 32700, 33700, 34700, 35700, 36800, 37900, 39000, 40200, 41400, 42600, 43900, 45200, 46600, 48000, 49400, 50900, 52400, 54000, 55600, 57300, 59000, 60800],
    'L-5': [20800, 21400, 22000, 22700, 23400, 24100, 24800, 25500, 26300, 27100, 27900, 28700, 29600, 30500, 31400, 32300, 33300, 34300, 35300, 36400, 37500, 38600, 39800, 41000, 42200, 43500, 44800, 46100, 47500, 48900, 50400, 51900, 53500, 55100, 56800, 58500, 60300, 62100, 64000, 65900],
    'L-6': [21500, 22100, 22800, 23500, 24200, 24900, 25600, 26400, 27200, 28000, 28800, 29700, 30600, 31500, 32400, 33400, 34400, 35400, 36500, 37600, 38700, 39900, 41100, 42300, 43600, 44900, 46200, 47600, 49000, 50500, 52000, 53600, 55200, 56900, 58600, 60400, 62200, 64100, 66000, 68000],
    'L-7': [22400, 23100, 23800, 24500, 25200, 26000, 26800, 27600, 28400, 29300, 30200, 31100, 32000, 33000, 34000, 35000, 36100, 37200, 38300, 39400, 40600, 41800, 43100, 44400, 45700, 47100, 48500, 50000, 51500, 53000, 54600, 56200, 57900, 59600, 61400, 63200, 65100, 67100, 69100, 71200],
    'L-8': [26300, 27100, 27900, 28700, 29600, 30500, 31400, 32300, 33300, 34300, 35300, 36400, 37500, 38600, 39800, 41000, 42200, 43500, 44800, 46100, 47500, 48900, 50400, 51900, 53500, 55100, 56800, 58500, 60300, 62100, 64000, 65900, 67900, 69900, 72000, 74200, 76400, 78700, 81100, 83500],
    'L-9': [28700, 29600, 30500, 31400, 32300, 33300, 34300, 35300, 36400, 37500, 38600, 39800, 41000, 42200, 43500, 44800, 46100, 47500, 48900, 50400, 51900, 53500, 55100, 56800, 58500, 60300, 62100, 64000, 65900, 67900, 69900, 72000, 74200, 76400, 78700, 81100, 83500, 86000, 88600, 91300],
    'L-10': [33800, 34800, 35800, 36900, 38000, 39100, 40300, 41500, 42700, 44000, 45300, 46700, 48100, 49500, 51000, 52500, 54100, 55700, 57400, 59100, 60900, 62700, 64600, 66500, 68500, 70600, 72700, 74900, 77100, 79400, 81800, 84300, 86800, 89400, 92100, 94900, 97700, 100600, 103600, 106700],
    'L-11': [37800, 38900, 40100, 41300, 42500, 43800, 45100, 46500, 47900, 49300, 50800, 52300, 53900, 55500, 57200, 58900, 60700, 62500, 64400, 66300, 68300, 70300, 72400, 74600, 76800, 79100, 81500, 83900, 86400, 89000, 91700, 94500, 97300, 100200, 103200, 106300, 109500, 112800, 116200, 119700],
    'L-12': [44300, 45600, 47000, 48400, 49900, 51400, 52900, 54500, 56100, 57800, 59500, 61300, 63100, 65000, 67000, 69000, 71100, 73200, 75400, 77700, 80000, 82400, 84900, 87400, 90000, 92700, 95500, 98400, 101400, 104400, 107500, 110700, 114000, 117400, 120900, 124500, 128200, 132000, 136000, 140100],
    'L-13': [53100, 54700, 56300, 58000, 59700, 61500, 63300, 65200, 67200, 69200, 71300, 73400, 75600, 77900, 80200, 82600, 85100, 87700, 90300, 93000, 95800, 98700, 101700, 104800, 107900, 111100, 114400, 117800, 121300, 124900, 128600, 132500, 136500, 140600, 144800, 149100, 153600, 158200, 162900, 167800],
    'L-14': [56100, 57800, 59500, 61300, 63100, 65000, 67000, 69000, 71100, 73200, 75400, 77700, 80000, 82400, 84900, 87400, 90000, 92700, 95500, 98400, 101400, 104400, 107500, 110700, 114000, 117400, 120900, 124500, 128200, 132000, 136000, 140100, 144300, 148600, 153100, 157700, 162400, 167300, 172300, 177500],
    'L-15': [60700, 62500, 64400, 66300, 68300, 70300, 72400, 74600, 76800, 79100, 81500, 83900, 86400, 89000, 91700, 94500, 97300, 100200, 103200, 106300, 109500, 112800, 116200, 119700, 123300, 127000, 130800, 134700, 138700, 142900, 147200, 151600, 156100, 160800, 165600, 170600, 175700, 181000, 186400, 192000],
    'L-16': [67300, 69300, 71400, 73500, 75700, 78000, 80300, 82700, 85200, 87800, 90400, 93100, 95900, 98800, 101800, 104900, 108000, 111200, 114500, 117900, 121400, 125000, 128800, 132700, 136700, 140800, 145000, 149400, 153900, 158500, 163300, 168200, 173200, 178400, 183800, 189300, 195000],
    'L-17': [71000, 73100, 75300, 77600, 79900, 82300, 84800, 87300, 89900, 92600, 95400, 98300, 101200, 104200, 107300, 110500, 113800, 117200, 120700, 124300, 128000, 131800, 135800, 139900, 144100, 148400, 152900, 157500, 162200, 167100, 172100, 177300, 182600, 188100, 193700, 199500],
    'L-18': [75300, 77600, 79900, 82300, 84800, 87300, 89900, 92600, 95400, 98300, 101200, 104200, 107300, 110500, 113800, 117200, 120700, 124300, 128000, 131800, 135800, 139900, 144100, 148400, 152900, 157500, 162200, 167100, 172100, 177300, 182600, 188100, 193700, 199500],
    'L-19': [79900, 82300, 84800, 87300, 89900, 92600, 95400, 98300, 101200, 104200, 107300, 110500, 113800, 117200, 120700, 124300, 128000, 131800, 135800, 139900, 144100, 148400, 152900, 157500, 162200, 167100, 172100, 177300, 182600, 188100, 193700, 199500],
    'L-20': [88900, 91600, 94300, 97100, 100000, 103000, 106100, 109300, 112600, 116000, 119500, 123100, 126800, 130600, 134500, 138500, 142700, 147000, 151400, 155900, 160600, 165400, 170400, 175500, 180800, 186200, 191800, 197600, 203500],
    'L-21': [123100, 126800, 130600, 134500, 138500, 142700, 147000, 151400, 155900, 160600, 165400, 170400, 175500, 180800, 186200, 191800, 197600, 203500],
    'L-22': [129700, 133600, 137600, 141700, 146000, 150400, 154900, 159500, 164300, 169200, 174300, 179500, 184900, 190400, 196100, 202000, 208100],
    'L-23': [145800, 150200, 154700, 159300, 164100, 169000, 174100, 179300, 184700, 190200, 195900, 201800, 207900, 214100],
    'L-24': [148800, 153300, 157900, 162600, 167500, 172500, 177700, 183000, 188500, 194200, 200000, 206000, 212200, 218600],
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

    /* DATE PICKER FIX (Streamlit 1.62+ / React Aria).
       Streamlit replaced the old BaseWeb DateInput implementation in 1.62.
       The calendar is now rendered under [data-testid="stDateInputCalendar"]
       and its day cells use React-Aria state attributes such as
       data-selected, data-outside-month, data-disabled and data-unavailable.
       The application has a dark global text rule, so normal current-month
       dates can otherwise inherit white text on the white calendar.
       IMPORTANT: only colors are changed here; no calendar geometry is touched. */
    div[data-testid="stDateInputCalendar"] {
        background: #ffffff !important;
        color: #1f2937 !important;
        border-radius: 8px !important;
    }
    div[data-testid="stDateInputCalendar"] [role="grid"],
    div[data-testid="stDateInputCalendar"] table {
        color: #1f2937 !important;
    }
    div[data-testid="stDateInputCalendar"] [role="gridcell"],
    div[data-testid="stDateInputCalendar"] [role="gridcell"] *,
    div[data-testid="stDateInputCalendar"] [data-outside-month],
    div[data-testid="stDateInputCalendar"] [data-outside-month] * {
        color: #1f2937 !important;
        -webkit-text-fill-color: #1f2937 !important;
    }
    div[data-testid="stDateInputCalendar"] [data-outside-month],
    div[data-testid="stDateInputCalendar"] [data-outside-month] * {
        color: #9ca3af !important;
        -webkit-text-fill-color: #9ca3af !important;
    }
    div[data-testid="stDateInputCalendar"] [data-disabled],
    div[data-testid="stDateInputCalendar"] [data-unavailable],
    div[data-testid="stDateInputCalendar"] [data-disabled] *,
    div[data-testid="stDateInputCalendar"] [data-unavailable] * {
        color: #9ca3af !important;
        -webkit-text-fill-color: #9ca3af !important;
    }
    div[data-testid="stDateInputCalendar"] [data-selected],
    div[data-testid="stDateInputCalendar"] [data-selected] * {
        background-color: #ff4757 !important;
        color: #ffffff !important;
        -webkit-text-fill-color: #ffffff !important;
        font-weight: 800 !important;
    }
    div[data-testid="stDateInputCalendar"] [role="columnheader"],
    div[data-testid="stDateInputCalendar"] [role="columnheader"] *,
    div[data-testid="stDateInputCalendar"] th,
    div[data-testid="stDateInputCalendar"] th * {
        color: #34495e !important;
        -webkit-text-fill-color: #34495e !important;
        font-weight: 700 !important;
    }
    div[data-testid="stDateInputCalendar"] [role="gridcell"]:hover,
    div[data-testid="stDateInputCalendar"] [data-hovered] {
        color: #102a45 !important;
        -webkit-text-fill-color: #102a45 !important;
    }

    /* Backward compatibility for older Streamlit releases that still use BaseWeb. */
    div[data-baseweb="calendar"] {
        background: #ffffff !important;
        color: #1f2937 !important;
        border-radius: 8px !important;
    }
    div[data-baseweb="calendar"] [role="gridcell"],
    div[data-baseweb="calendar"] [role="gridcell"] button,
    div[data-baseweb="calendar"] [role="gridcell"] button * {
        color: #1f2937 !important;
        -webkit-text-fill-color: #1f2937 !important;
    }
    div[data-baseweb="calendar"] [aria-disabled="true"],
    div[data-baseweb="calendar"] [aria-disabled="true"] * {
        color: #9ca3af !important;
        -webkit-text-fill-color: #9ca3af !important;
    }
    div[data-baseweb="calendar"] [aria-selected="true"],
    div[data-baseweb="calendar"] [aria-selected="true"] * {
        background: #ff4757 !important;
        color: #ffffff !important;
        -webkit-text-fill-color: #ffffff !important;
        font-weight: 800 !important;
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

    /* IMPORTANT: never style every <button> globally. Streamlit's date picker
       also uses button elements for its day cells. A global button color rule
       makes normal calendar dates inherit the dashboard's white text. */
    div.stButton > button, div[data-testid="stFormSubmitButton"] > button {
        background-color: #2980b9 !important;
        color: #ffffff !important;
        font-weight: bold !important;
        border: 2px solid #3498db !important;
        border-radius: 6px !important;
        box-shadow: 0 4px 0 #1b4f72 !important;
    }
    div.stButton > button *, div[data-testid="stFormSubmitButton"] > button * {
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
    div[class*="st-key-module_nav_master"] button { background:#2980b9 !important; border:2px solid #3498db !important; box-shadow:0 4px 0 #21618c !important; color:#fff !important; text-align:left !important; justify-content:flex-start !important; }
    div[class*="st-key-module_nav_pay_commission_admin"] button { background:#7d3c98 !important; border:2px solid #bb8fce !important; box-shadow:0 4px 0 #512e5f !important; color:#fff !important; text-align:left !important; justify-content:flex-start !important; font-weight:900 !important; }
    div[class*="st-key-module_nav_inc"] button { background:#27ae60 !important; border:2px solid #2ecc71 !important; box-shadow:0 4px 0 #1e8449 !important; color:#fff !important; text-align:left !important; justify-content:flex-start !important; }
    div[class*="st-key-module_nav_sna"] button { background:#8e44ad !important; border:2px solid #9b59b6 !important; box-shadow:0 4px 0 #6c3483 !important; color:#fff !important; text-align:left !important; justify-content:flex-start !important; }
    div[class*="st-key-module_nav_arr"] button { background:#d35400 !important; border:2px solid #e67e22 !important; box-shadow:0 4px 0 #a04000 !important; color:#fff !important; text-align:left !important; justify-content:flex-start !important; }
    div[class*="st-key-module_nav_master"] button:hover { background:#3498db !important; }
    div[class*="st-key-module_nav_pl"] button:hover { background:#2980b9 !important; }
    div[class*="st-key-module_nav_inc"] button:hover { background:#2ecc71 !important; }
    div[class*="st-key-module_nav_sna"] button:hover { background:#9b59b6 !important; }
    div[class*="st-key-module_nav_arr"] button:hover { background:#e67e22 !important; }
    /* Streamlit button content is flex-based; align the inner content, not only the button box. */
    div[class*="st-key-module_nav_master"] button > div,
    div[class*="st-key-module_nav_pl"] button > div,
    div[class*="st-key-module_nav_inc"] button > div,
    div[class*="st-key-module_nav_sna"] button > div,
    div[class*="st-key-module_nav_arr"] button > div { width:100% !important; justify-content:flex-start !important; text-align:left !important; }
    div[class*="st-key-module_nav_master"] button p,
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
        "master_data": "Master Data Management",
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














# User-supplied deduction slabs.






















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
        # Master Data is intentionally the first menu item.
        with st.container(key="module_nav_master"):
            if st.button("1. ⚙️ Master Data Management", key="nav_master_data", use_container_width=True):
                st.query_params["page"] = "master_data"; st.rerun()
        if st.session_state.get("logged_role") == "admin":
            with st.container(key="module_nav_pay_commission_admin"):
                if st.button("🔐 Pay Commission Master (Admin Only)", key="nav_pay_commission_admin", use_container_width=True):
                    st.query_params["page"] = "pay_commission_master_admin"; st.rerun()
        with st.container(key="module_nav_pl"):
            if st.button("2. उपार्जित अवकाश समर्पण (PL Surrender) आदेश जनरेटर ▶", key="nav_pl_surrender", use_container_width=True):
                st.query_params["page"] = "pl_surrender"; st.rerun()
        with st.container(key="module_nav_inc"):
            if st.button("3. वार्षिक सामयिक वेतन वृद्धि (Annual Increment) आदेश जनरेटर ▶", key="nav_increment_order", use_container_width=True):
                st.query_params["page"] = "increment_order"; st.rerun()
        with st.container(key="module_nav_sna"):
            if st.button("4. संचालन पोर्टल भुगतान स्वीकृति आदेश (SNA Sanction Order) जनरेटर ▶", key="nav_sanchalan_portal", use_container_width=True):
                st.query_params["page"] = "sanchalan_portal"; st.rerun()
        with st.container(key="module_nav_arr"):
            if st.button("5. वेतन एरियर (Salary Arrear) अंतर विवरण प्रपत्र एवं गणना (7th CPC Landscape) ▶", key="nav_salary_arrear", use_container_width=True):
                st.query_params["page"] = "salary_arrear"; st.rerun()
        st.markdown('<div class="menu-btn-rel">6. कार्यमुक्ति / कार्यग्रहण (Relieving / Joining) आदेश [शीघ्र उपलब्ध]</div>', unsafe_allow_html=True)

# =============================================================================
# पृष्ठ 2: उपार्जित अवकाश समर्पण (PL Surrender) विंडो
# =============================================================================
elif active_page == "pay_commission_master_admin":
    from modules.master_data_management import render_admin_pay_commission_page
    render_admin_pay_commission_page(globals())

# =============================================================================
# पृष्ठ 2: उपार्जित अवकाश (PL Surrender) विंडो
# =============================================================================
elif active_page == "pl_surrender":
    from modules.pl_surrender import render as _render_pl_surrender
    _render_pl_surrender(globals())

# =============================================================================
# पृष्ठ 3: सामयिक वार्षिक वेतन वृद्धि (Annual Increment) विंडो
# =============================================================================
elif active_page == "increment_order":
    from modules.increment_order import render as _render_increment_order
    _render_increment_order(globals())

# =============================================================================
# पृष्ठ 4: संचालन पोर्टल भुगतान स्वीकृति आदेश (Sanchalan Portal Sanction) विंडो
# =============================================================================
elif active_page == "master_data":
    from modules.master_data_management import render as _render_master_data
    _render_master_data(globals())

elif active_page == "sanchalan_portal":
    from modules.sanchalan_portal import render as _render_sanchalan_portal
    _render_sanchalan_portal(globals())

# =============================================================================
# पृष्ठ 5: वेतन एरियर (Salary Arrear) गणना एवं अंतर विवरण प्रपत्र मॉड्यूल (7th CPC Landscape Final Fixes)
# =============================================================================
elif active_page == "salary_arrear":
    from modules.salary_arrear import render as _render_salary_arrear
    _render_salary_arrear(globals())

