from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from config import MONGODB_URI, DATABASE_NAME
import streamlit as st

@st.cache_resource
def get_database():
    if not MONGODB_URI:
        return None
        
    try:
        client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
        client.admin.command('ping')
        db = client[DATABASE_NAME]
        
        if "monitors" not in db.list_collection_names():
            db.create_collection("monitors")
        if "check_results" not in db.list_collection_names():
            db.create_collection("check_results")
        if "incidents" not in db.list_collection_names():
            db.create_collection("incidents")
        if "notifications" not in db.list_collection_names():
            db.create_collection("notifications")
        if "status_pages" not in db.list_collection_names():
            db.create_collection("status_pages")
        if "settings" not in db.list_collection_names():
            db.create_collection("settings")
            
        db.check_results.create_index([("monitor_id", 1), ("timestamp", -1)])
        db.incidents.create_index([("monitor_id", 1), ("created_at", -1)])
        
        return db
    except ConnectionFailure as e:
        st.error(f"Failed to connect to MongoDB: {e}")
        return None
    except Exception as e:
        st.error(f"Database error: {e}")
        return None

def get_monitors_collection():
    db = get_database()
    return db.monitors if db is not None else None

def get_check_results_collection():
    db = get_database()
    return db.check_results if db is not None else None

def get_incidents_collection():
    db = get_database()
    return db.incidents if db is not None else None

def get_notifications_collection():
    db = get_database()
    return db.notifications if db is not None else None

def get_status_pages_collection():
    db = get_database()
    return db.status_pages if db is not None else None

def get_settings_collection():
    db = get_database()
    return db.settings if db is not None else None
