import os
import json
import hashlib

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
        return False, "Yeh User ID pehle se mojood hai. Kripya dusra Username chunein."
    
    users[username] = {
        "password": hash_password(password),
        "full_name": full_name,
        "email": email
    }
    save_users(users)
    return True, "Registration safal raha! Ab aap login kar sakte hain."

def verify_user(username, password):
    users = load_users()
    if username in users:
        if users[username]["password"] == hash_password(password):
            return True, "Login safal!"
    return False, "Galat User ID ya Password!"

def recover_username(full_name, email):
    users = load_users()
    for uname, details in users.items():
        if details.get("full_name", "").strip().lower() == full_name.strip().lower() and details.get("email", "").strip().lower() == email.strip().lower():
            return True, f"Aapka User ID hai: {uname}"
    return False, "Diye gaye विवरण (Details) se koi User ID nahi mila."

def reset_password(username, email, new_password):
    users = load_users()
    if username in users:
        if users[username].get("email", "").strip().lower() == email.strip().lower():
            users[username]["password"] = hash_password(new_password)
            save_users(users)
            return True, "Password सफलतापूर्वक badal diya gaya hai!"
        else:
            username_match = any(details.get("email", "").strip().lower() == email.strip().lower() for details in users.values())
            if not username_match:
                return False, "Yeh Email ID hamare database mein registered nahi hai."
            return False, "User ID aur Email ID aapas mein match nahi ho rahe hain."
    return False, "Yeh User ID system mein mojood nahi hai."