from datetime import datetime
from bson import ObjectId
from database import (
    get_monitors_collection, 
    get_check_results_collection, 
    get_incidents_collection,
    get_notifications_collection,
    get_status_pages_collection,
    get_settings_collection
)

class Monitor:
    @staticmethod
    def create(name, monitor_type, url, interval=300, **kwargs):
        monitors = get_monitors_collection()
        if monitors is None:
            return None
            
        monitor = {
            "name": name,
            "type": monitor_type,
            "url": url,
            "interval": interval,
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
    def get_all():
        monitors = get_monitors_collection()
        if monitors is None:
            return []
        return list(monitors.find().sort("created_at", -1))
    
    @staticmethod
    def get_by_id(monitor_id):
        monitors = get_monitors_collection()
        if monitors is None:
            return None
        return monitors.find_one({"_id": ObjectId(monitor_id)})
    
    @staticmethod
    def update(monitor_id, updates):
        monitors = get_monitors_collection()
        if monitors is None:
            return False
        updates["updated_at"] = datetime.utcnow()
        result = monitors.update_one(
            {"_id": ObjectId(monitor_id)},
            {"$set": updates}
        )
        return result.modified_count > 0
    
    @staticmethod
    def delete(monitor_id):
        monitors = get_monitors_collection()
        check_results = get_check_results_collection()
        incidents = get_incidents_collection()
        
        if monitors is not None:
            monitors.delete_one({"_id": ObjectId(monitor_id)})
        if check_results is not None:
            check_results.delete_many({"monitor_id": str(monitor_id)})
        if incidents is not None:
            incidents.delete_many({"monitor_id": str(monitor_id)})
        return True
    
    @staticmethod
    def get_active_monitors():
        monitors = get_monitors_collection()
        if monitors is None:
            return []
        return list(monitors.find({"is_paused": False}))
    
    @staticmethod
    def get_by_group(group):
        monitors = get_monitors_collection()
        if monitors is None:
            return []
        return list(monitors.find({"group": group}))
    
    @staticmethod
    def get_groups():
        monitors = get_monitors_collection()
        if monitors is None:
            return ["default"]
        groups = monitors.distinct("group")
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
    def create(monitor_id, monitor_name, incident_type="down", details=None):
        incidents = get_incidents_collection()
        if incidents is None:
            return None
            
        incident = {
            "monitor_id": str(monitor_id),
            "monitor_name": monitor_name,
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
    def resolve(incident_id):
        incidents = get_incidents_collection()
        if incidents is None:
            return False
            
        incident = incidents.find_one({"_id": ObjectId(incident_id)})
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
    def get_ongoing():
        incidents = get_incidents_collection()
        if incidents is None:
            return []
        return list(incidents.find({"status": "ongoing"}).sort("created_at", -1))
    
    @staticmethod
    def get_by_monitor(monitor_id, limit=50):
        incidents = get_incidents_collection()
        if incidents is None:
            return []
        return list(incidents.find(
            {"monitor_id": str(monitor_id)}
        ).sort("created_at", -1).limit(limit))
    
    @staticmethod
    def get_recent(limit=50):
        incidents = get_incidents_collection()
        if incidents is None:
            return []
        return list(incidents.find().sort("created_at", -1).limit(limit))

class Notification:
    @staticmethod
    def create(name, notification_type, config):
        notifications = get_notifications_collection()
        if notifications is None:
            return None
            
        notification = {
            "name": name,
            "type": notification_type,
            "config": config,
            "enabled": True,
            "created_at": datetime.utcnow()
        }
        
        result = notifications.insert_one(notification)
        return result.inserted_id
    
    @staticmethod
    def get_all():
        notifications = get_notifications_collection()
        if notifications is None:
            return []
        return list(notifications.find())
    
    @staticmethod
    def delete(notification_id):
        notifications = get_notifications_collection()
        if notifications is None:
            return False
        notifications.delete_one({"_id": ObjectId(notification_id)})
        return True

class StatusPage:
    @staticmethod
    def create(name, slug, monitors, custom_domain=None, **kwargs):
        pages = get_status_pages_collection()
        if pages is None:
            return None
            
        page = {
            "name": name,
            "slug": slug,
            "monitors": monitors,
            "custom_domain": custom_domain,
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
    def get_all():
        pages = get_status_pages_collection()
        if pages is None:
            return []
        return list(pages.find())
    
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
