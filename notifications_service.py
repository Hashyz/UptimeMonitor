import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from models import Notification

def send_email(config, subject, message):
    try:
        smtp_server = config.get("smtp_server", "smtp.gmail.com")
        smtp_port = config.get("smtp_port", 587)
        sender_email = config.get("sender_email", "")
        sender_password = config.get("sender_password", "")
        recipient_email = config.get("recipient_email", "")
        
        if not all([sender_email, sender_password, recipient_email]):
            return {"success": False, "error": "Missing email configuration"}
        
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = recipient_email
        msg['Subject'] = subject
        
        msg.attach(MIMEText(message, 'html'))
        
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()
        
        return {"success": True}
        
    except Exception as e:
        return {"success": False, "error": str(e)}

def send_webhook(config, data):
    try:
        webhook_url = config.get("webhook_url", "")
        
        if not webhook_url:
            return {"success": False, "error": "Missing webhook URL"}
        
        headers = config.get("headers", {"Content-Type": "application/json"})
        
        response = requests.post(
            webhook_url,
            json=data,
            headers=headers,
            timeout=30
        )
        
        if response.status_code in [200, 201, 202, 204]:
            return {"success": True}
        else:
            return {"success": False, "error": f"Webhook returned status {response.status_code}"}
            
    except Exception as e:
        return {"success": False, "error": str(e)}

def send_slack(config, message):
    try:
        webhook_url = config.get("webhook_url", "")
        
        if not webhook_url:
            return {"success": False, "error": "Missing Slack webhook URL"}
        
        response = requests.post(
            webhook_url,
            json={"text": message},
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        if response.status_code == 200:
            return {"success": True}
        else:
            return {"success": False, "error": f"Slack returned status {response.status_code}"}
            
    except Exception as e:
        return {"success": False, "error": str(e)}

def send_telegram(config, message):
    try:
        bot_token = config.get("bot_token", "")
        chat_id = config.get("chat_id", "")
        
        if not all([bot_token, chat_id]):
            return {"success": False, "error": "Missing Telegram configuration"}
        
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        
        response = requests.post(
            url,
            json={
                "chat_id": chat_id,
                "text": message,
                "parse_mode": "HTML"
            },
            timeout=30
        )
        
        if response.status_code == 200:
            return {"success": True}
        else:
            return {"success": False, "error": f"Telegram returned status {response.status_code}"}
            
    except Exception as e:
        return {"success": False, "error": str(e)}

def send_notification(notification_type, config, monitor_name, status, details=""):
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    
    subject = f"Monitor Alert: {monitor_name} is {status.upper()}"
    
    message = f"""
    <h2>Monitor Alert</h2>
    <p><strong>Monitor:</strong> {monitor_name}</p>
    <p><strong>Status:</strong> {status.upper()}</p>
    <p><strong>Time:</strong> {timestamp}</p>
    <p><strong>Details:</strong> {details}</p>
    """
    
    plain_message = f"""
Monitor Alert
Monitor: {monitor_name}
Status: {status.upper()}
Time: {timestamp}
Details: {details}
    """
    
    webhook_data = {
        "monitor_name": monitor_name,
        "status": status,
        "timestamp": timestamp,
        "details": details
    }
    
    if notification_type == "email":
        return send_email(config, subject, message)
    elif notification_type == "webhook":
        return send_webhook(config, webhook_data)
    elif notification_type == "slack":
        return send_slack(config, plain_message)
    elif notification_type == "telegram":
        return send_telegram(config, plain_message)
    else:
        return {"success": False, "error": "Unknown notification type"}

def broadcast_alert(monitor_name, status, details=""):
    notifications = Notification.get_all()
    results = []
    
    for notification in notifications:
        if notification.get("enabled", True):
            result = send_notification(
                notification["type"],
                notification["config"],
                monitor_name,
                status,
                details
            )
            results.append({
                "notification": notification["name"],
                "result": result
            })
            
    return results
