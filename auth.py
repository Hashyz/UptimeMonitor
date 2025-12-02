import bcrypt
from datetime import datetime
from bson import ObjectId
from database import get_users_collection

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
    except Exception:
        return False

def sanitize_user(user: dict) -> dict:
    if user is None:
        return None
    return {
        "_id": user.get("_id"),
        "email": user.get("email"),
        "name": user.get("name"),
        "created_at": user.get("created_at")
    }

def create_user(email: str, password: str, name: str) -> dict:
    users = get_users_collection()
    if users is None:
        return {"success": False, "error": "Database connection failed"}
    
    existing = users.find_one({"email": email.lower()})
    if existing:
        return {"success": False, "error": "An account with this email already exists"}
    
    user = {
        "email": email.lower(),
        "password_hash": hash_password(password),
        "name": name,
        "created_at": datetime.utcnow()
    }
    
    try:
        result = users.insert_one(user)
        user["_id"] = result.inserted_id
        return {"success": True, "user": sanitize_user(user)}
    except Exception as e:
        if "duplicate key" in str(e).lower():
            return {"success": False, "error": "An account with this email already exists"}
        return {"success": False, "error": f"Registration failed: {str(e)}"}

def authenticate_user(email: str, password: str) -> dict:
    users = get_users_collection()
    if users is None:
        return {"success": False, "error": "Database connection failed"}
    
    user = users.find_one({"email": email.lower()})
    if not user:
        return {"success": False, "error": "Invalid email or password"}
    
    if not verify_password(password, user["password_hash"]):
        return {"success": False, "error": "Invalid email or password"}
    
    return {"success": True, "user": sanitize_user(user)}

def get_user_by_email(email: str) -> dict:
    users = get_users_collection()
    if users is None:
        return None
    return users.find_one({"email": email.lower()})

def get_user_by_id(user_id: str) -> dict:
    users = get_users_collection()
    if users is None:
        return None
    try:
        return users.find_one({"_id": ObjectId(user_id)})
    except Exception:
        return None
