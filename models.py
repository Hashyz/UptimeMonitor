from datetime import datetime
from bson import ObjectId
from database import (
    get_monitors_collection, 
    get_check_results_collection, 
    get_incidents_collection,
    get_notifications_collection,
    get_status_pages_collection,
    get_settings_collection,
    get_users_collection
)


class User:
    @staticmethod
    def create(email, password_hash, name):
        users = get_users_collection()
        if users is None:
            return None
            
        user = {
            "email": email.lower(),
            "password_hash": password_hash,
            "name": name,
            "created_at": datetime.utcnow()
        }
        
        try:
            result = users.insert_one(user)
            user["_id"] = result.inserted_id
            return user
        except Exception:
            return None
    
    @staticmethod
    def get_by_email(email):
        users = get_users_collection()
        if users is None:
            return None
        return users.find_one({"email": email.lower()})
    
    @staticmethod
    def get_by_id(user_id):
        users = get_users_collection()
        if users is None:
            return None
        try:
            return users.find_one({"_id": ObjectId(user_id)})
        except Exception:
            return None

class Monitor:
    @staticmethod
    def create(name, monitor_type, url, interval=300, user_id=None, **kwargs):
        monitors = get_monitors_collection()
        if monitors is None:
            return None
            
        monitor = {
            "name": name,
            "type": monitor_type,
            "url": url,
            "interval": interval,
            "user_id": str(user_id) if user_id else None,
            "status": "pending",
            "last_check": None,
            "last_response_time": None,
            "uptime_percentage": 100.0,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "is_paused": False,
            "timeout": kwargs.get("timeout", 30),
            "http_method": kwargs.get("http_method", "GET"),
            "expected_status_codes": kwargs.get("expected_status_codes", [200, 201, 301, 302]),
            "keyword": kwargs.get("keyword", ""),
            "keyword_type": kwargs.get("keyword_type", "exists"),
            "port": kwargs.get("port", 80),
            "headers": kwargs.get("headers", {}),
            "body": kwargs.get("body", ""),
            "follow_redirects": kwargs.get("follow_redirects", True),
            "ssl_check": kwargs.get("ssl_check", False),
            "ssl_expiry_threshold": kwargs.get("ssl_expiry_threshold", 30),
            "domain_expiry_threshold": kwargs.get("domain_expiry_threshold", 30),
            "notification_settings": kwargs.get("notification_settings", {
                "enabled": True,
                "on_down": True,
                "on_up": True,
                "delay": 0,
                "repeat": False
            }),
            "tags": kwargs.get("tags", []),
            "group": kwargs.get("group", "default"),
            "notes": kwargs.get("notes", "")
        }
        
        result = monitors.insert_one(monitor)
        monitor["_id"] = result.inserted_id
        return monitor
    
    @staticmethod
    def get_all(user_id=None):
        monitors = get_monitors_collection()
        if monitors is None:
            return []
        query = {}
        if user_id:
            query["user_id"] = str(user_id)
        return list(monitors.find(query).sort("created_at", -1))
    
    @staticmethod
    def get_by_id(monitor_id, user_id=None):
        monitors = get_monitors_collection()
        if monitors is None:
            return None
        query = {"_id": ObjectId(monitor_id)}
        if user_id:
            query["user_id"] = str(user_id)
        return monitors.find_one(query)
    
    @staticmethod
    def update(monitor_id, updates, user_id=None):
        monitors = get_monitors_collection()
        if monitors is None:
            return False
        updates["updated_at"] = datetime.utcnow()
        query = {"_id": ObjectId(monitor_id)}
        if user_id:
            query["user_id"] = str(user_id)
        result = monitors.update_one(
            query,
            {"$set": updates}
        )
        return result.modified_count > 0
    
    @staticmethod
    def delete(monitor_id, user_id=None):
        monitors = get_monitors_collection()
        check_results = get_check_results_collection()
        incidents = get_incidents_collection()
        
        query = {"_id": ObjectId(monitor_id)}
        if user_id:
            query["user_id"] = str(user_id)
        
        if monitors is not None:
            result = monitors.delete_one(query)
            if result.deleted_count == 0:
                return False
        if check_results is not None:
            check_results.delete_many({"monitor_id": str(monitor_id)})
        if incidents is not None:
            incidents.delete_many({"monitor_id": str(monitor_id)})
        return True
    
    @staticmethod
    def get_active_monitors(user_id=None):
        monitors = get_monitors_collection()
        if monitors is None:
            return []
        query = {"is_paused": False}
        if user_id:
            query["user_id"] = str(user_id)
        return list(monitors.find(query))
    
    @staticmethod
    def get_by_group(group, user_id=None):
        monitors = get_monitors_collection()
        if monitors is None:
            return []
        query = {"group": group}
        if user_id:
            query["user_id"] = str(user_id)
        return list(monitors.find(query))
    
    @staticmethod
    def get_groups(user_id=None):
        monitors = get_monitors_collection()
        if monitors is None:
            return ["default"]
        query = {}
        if user_id:
            query["user_id"] = str(user_id)
        groups = monitors.distinct("group", query)
        return groups if groups else ["default"]

class CheckResult:
    @staticmethod
    def create(monitor_id, status, response_time=None, status_code=None, error=None, details=None):
        results = get_check_results_collection()
        if results is None:
            return None
            
        check = {
            "monitor_id": str(monitor_id),
            "status": status,
            "response_time": response_time,
            "status_code": status_code,
            "error": error,
            "details": details or {},
            "timestamp": datetime.utcnow()
        }
        
        result = results.insert_one(check)
        return result.inserted_id
    
    @staticmethod
    def get_by_monitor(monitor_id, limit=100):
        results = get_check_results_collection()
        if results is None:
            return []
        return list(results.find(
            {"monitor_id": str(monitor_id)}
        ).sort("timestamp", -1).limit(limit))
    
    @staticmethod
    def get_recent(limit=50):
        results = get_check_results_collection()
        if results is None:
            return []
        return list(results.find().sort("timestamp", -1).limit(limit))
    
    @staticmethod
    def calculate_uptime(monitor_id, hours=24):
        results = get_check_results_collection()
        if results is None:
            return 100.0
            
        from datetime import timedelta
        start_time = datetime.utcnow() - timedelta(hours=hours)
        
        checks = list(results.find({
            "monitor_id": str(monitor_id),
            "timestamp": {"$gte": start_time}
        }))
        
        if not checks:
            return 100.0
            
        up_count = sum(1 for c in checks if c["status"] == "up")
        return round((up_count / len(checks)) * 100, 2)

class Incident:
    @staticmethod
    def create(monitor_id, monitor_name, incident_type="down", details=None, user_id=None):
        incidents = get_incidents_collection()
        if incidents is None:
            return None
            
        incident = {
            "monitor_id": str(monitor_id),
            "monitor_name": monitor_name,
            "user_id": str(user_id) if user_id else None,
            "type": incident_type,
            "status": "ongoing",
            "details": details or {},
            "created_at": datetime.utcnow(),
            "resolved_at": None,
            "duration": None
        }
        
        result = incidents.insert_one(incident)
        return result.inserted_id
    
    @staticmethod
    def resolve(incident_id, user_id=None):
        incidents = get_incidents_collection()
        if incidents is None:
            return False
        
        query = {"_id": ObjectId(incident_id)}
        if user_id:
            query["user_id"] = str(user_id)
            
        incident = incidents.find_one(query)
        if incident and incident["status"] == "ongoing":
            resolved_at = datetime.utcnow()
            duration = (resolved_at - incident["created_at"]).total_seconds()
            
            incidents.update_one(
                {"_id": ObjectId(incident_id)},
                {"$set": {
                    "status": "resolved",
                    "resolved_at": resolved_at,
                    "duration": duration
                }}
            )
            return True
        return False
    
    @staticmethod
    def get_ongoing(user_id=None):
        incidents = get_incidents_collection()
        if incidents is None:
            return []
        query = {"status": "ongoing"}
        if user_id:
            query["user_id"] = str(user_id)
        return list(incidents.find(query).sort("created_at", -1))
    
    @staticmethod
    def get_by_monitor(monitor_id, limit=50, user_id=None):
        incidents = get_incidents_collection()
        if incidents is None:
            return []
        query = {"monitor_id": str(monitor_id)}
        if user_id:
            query["user_id"] = str(user_id)
        return list(incidents.find(query).sort("created_at", -1).limit(limit))
    
    @staticmethod
    def get_recent(limit=50, user_id=None):
        incidents = get_incidents_collection()
        if incidents is None:
            return []
        query = {}
        if user_id:
            query["user_id"] = str(user_id)
        return list(incidents.find(query).sort("created_at", -1).limit(limit))

class Notification:
    @staticmethod
    def create(name, notification_type, config, user_id=None):
        notifications = get_notifications_collection()
        if notifications is None:
            return None
            
        notification = {
            "name": name,
            "type": notification_type,
            "config": config,
            "user_id": str(user_id) if user_id else None,
            "enabled": True,
            "created_at": datetime.utcnow()
        }
        
        result = notifications.insert_one(notification)
        return result.inserted_id
    
    @staticmethod
    def get_all(user_id=None):
        notifications = get_notifications_collection()
        if notifications is None:
            return []
        query = {}
        if user_id:
            query["user_id"] = str(user_id)
        return list(notifications.find(query))
    
    @staticmethod
    def delete(notification_id, user_id=None):
        notifications = get_notifications_collection()
        if notifications is None:
            return False
        query = {"_id": ObjectId(notification_id)}
        if user_id:
            query["user_id"] = str(user_id)
        result = notifications.delete_one(query)
        return result.deleted_count > 0

class StatusPage:
    @staticmethod
    def create(name, slug, monitors, custom_domain=None, user_id=None, **kwargs):
        pages = get_status_pages_collection()
        if pages is None:
            return None
            
        page = {
            "name": name,
            "slug": slug,
            "monitors": monitors,
            "custom_domain": custom_domain,
            "user_id": str(user_id) if user_id else None,
            "is_public": kwargs.get("is_public", True),
            "password": kwargs.get("password", None),
            "custom_css": kwargs.get("custom_css", ""),
            "logo_url": kwargs.get("logo_url", ""),
            "description": kwargs.get("description", ""),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        result = pages.insert_one(page)
        return result.inserted_id
    
    @staticmethod
    def get_all(user_id=None):
        pages = get_status_pages_collection()
        if pages is None:
            return []
        query = {}
        if user_id:
            query["user_id"] = str(user_id)
        return list(pages.find(query))
    
    @staticmethod
    def get_by_slug(slug):
        pages = get_status_pages_collection()
        if pages is None:
            return None
        return pages.find_one({"slug": slug})
    
    @staticmethod
    def update(page_id, updates):
        pages = get_status_pages_collection()
        if pages is None:
            return False
        updates["updated_at"] = datetime.utcnow()
        result = pages.update_one(
            {"_id": ObjectId(page_id)},
            {"$set": updates}
        )
        return result.modified_count > 0
    
    @staticmethod
    def delete(page_id):
        pages = get_status_pages_collection()
        if pages is None:
            return False
        pages.delete_one({"_id": ObjectId(page_id)})
        return True
