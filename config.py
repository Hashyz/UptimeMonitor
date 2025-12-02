import os

MONGODB_URI = os.environ.get("MONGODB_URI", "mongodb+srv://mosel80708_db_user:WNhLu7aM4MxMkrEE@reverseauction.dkzr8ey.mongodb.net/?appName=reverseAuction")
DATABASE_NAME = "uptime_monitor"

MONITOR_TYPES = {
    "http": "HTTP/HTTPS",
    "keyword": "Keyword",
    "ping": "Ping",
    "port": "Port",
    "ssl": "SSL Certificate",
    "domain": "Domain Expiry"
}

MONITOR_INTERVALS = {
    30: "30 seconds",
    60: "1 minute",
    120: "2 minutes",
    180: "3 minutes",
    300: "5 minutes",
    600: "10 minutes",
    900: "15 minutes",
    1800: "30 minutes",
    3600: "1 hour"
}

HTTP_METHODS = ["GET", "HEAD", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"]

MONITOR_STATUS = {
    "up": "Up",
    "down": "Down",
    "paused": "Paused",
    "pending": "Pending"
}

NOTIFICATION_TYPES = {
    "email": "Email",
    "webhook": "Webhook",
    "slack": "Slack",
    "telegram": "Telegram"
}
