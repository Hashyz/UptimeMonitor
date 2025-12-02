import bcrypt
import secrets
import hashlib
from datetime import datetime, timedelta
from bson import ObjectId
from database import get_users_collection, get_database

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

def generate_session_token() -> str:
    return secrets.token_urlsafe(32)

def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()

def create_session(user_id: str, days_valid: int = 30) -> str:
    db = get_database()
    if db is None:
        return None
    
    token = generate_session_token()
    token_hash = hash_token(token)
    
    session = {
        "user_id": str(user_id),
        "token_hash": token_hash,
        "created_at": datetime.utcnow(),
        "expires_at": datetime.utcnow() + timedelta(days=days_valid)
    }
    
    try:
        sessions = db.sessions
        sessions.delete_many({"user_id": str(user_id)})
        sessions.insert_one(session)
        return token
    except Exception:
        return None

def validate_session(token: str) -> dict:
    if not token:
        return None
    
    db = get_database()
    if db is None:
        return None
    
    token_hash = hash_token(token)
    
    try:
        sessions = db.sessions
        session = sessions.find_one({
            "token_hash": token_hash,
            "expires_at": {"$gt": datetime.utcnow()}
        })
        
        if session:
            user = get_user_by_id(session["user_id"])
            if user:
                return sanitize_user(user)
        return None
    except Exception:
        return None

def delete_session(token: str) -> bool:
    if not token:
        return False
    
    db = get_database()
    if db is None:
        return False
    
    token_hash = hash_token(token)
    
    try:
        sessions = db.sessions
        sessions.delete_one({"token_hash": token_hash})
        return True
    except Exception:
        return False

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
        
        token = create_session(str(user["_id"]))
        
        return {"success": True, "user": sanitize_user(user), "token": token}
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
    
    token = create_session(str(user["_id"]))
    
    return {"success": True, "user": sanitize_user(user), "token": token}

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
