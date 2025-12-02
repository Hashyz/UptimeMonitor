import requests
import socket
import ssl
import subprocess
import time
from datetime import datetime, timedelta
from urllib.parse import urlparse
import OpenSSL
from models import Monitor, CheckResult, Incident

def check_http(monitor):
    url = monitor.get("url", "")
    method = monitor.get("http_method", "GET")
    timeout = monitor.get("timeout", 30)
    follow_redirects = monitor.get("follow_redirects", True)
    expected_codes = monitor.get("expected_status_codes", [200, 201, 301, 302])
    headers = monitor.get("headers", {})
    body = monitor.get("body", "")
    
    try:
        start_time = time.time()
        
        request_kwargs = {
            "method": method,
            "url": url,
            "timeout": timeout,
            "allow_redirects": follow_redirects,
            "headers": headers,
            "verify": True
        }
        
        if body and method in ["POST", "PUT", "PATCH"]:
            request_kwargs["data"] = body
            
        response = requests.request(**request_kwargs)
        response_time = round((time.time() - start_time) * 1000, 2)
        
        status = "up" if response.status_code in expected_codes else "down"
        
        return {
            "status": status,
            "response_time": response_time,
            "status_code": response.status_code,
            "error": None if status == "up" else f"Unexpected status code: {response.status_code}",
            "details": {
                "content_length": len(response.content),
                "headers": dict(response.headers)
            }
        }
        
    except requests.exceptions.Timeout:
        return {
            "status": "down",
            "response_time": timeout * 1000,
            "status_code": None,
            "error": "Request timeout",
            "details": {}
        }
    except requests.exceptions.ConnectionError as e:
        return {
            "status": "down",
            "response_time": None,
            "status_code": None,
            "error": f"Connection error: {str(e)}",
            "details": {}
        }
    except Exception as e:
        return {
            "status": "down",
            "response_time": None,
            "status_code": None,
            "error": str(e),
            "details": {}
        }

def check_keyword(monitor):
    result = check_http(monitor)
    
    if result["status"] == "down":
        return result
        
    keyword = monitor.get("keyword", "")
    keyword_type = monitor.get("keyword_type", "exists")
    
    if not keyword:
        return result
        
    try:
        url = monitor.get("url", "")
        response = requests.get(url, timeout=monitor.get("timeout", 30))
        content = response.text
        
        keyword_found = keyword.lower() in content.lower()
        
        if keyword_type == "exists" and keyword_found:
            result["status"] = "up"
            result["details"]["keyword_found"] = True
        elif keyword_type == "not_exists" and not keyword_found:
            result["status"] = "up"
            result["details"]["keyword_found"] = False
        else:
            result["status"] = "down"
            result["error"] = f"Keyword '{keyword}' {'not found' if keyword_type == 'exists' else 'found'}"
            result["details"]["keyword_found"] = keyword_found
            
    except Exception as e:
        result["status"] = "down"
        result["error"] = str(e)
        
    return result

def check_ping(monitor):
    url = monitor.get("url", "")
    timeout = monitor.get("timeout", 10)
    
    parsed = urlparse(url)
    host = parsed.hostname or url.replace("http://", "").replace("https://", "").split("/")[0]
    
    try:
        start_time = time.time()
        result = subprocess.run(
            ["ping", "-c", "1", "-W", str(timeout), host],
            capture_output=True,
            text=True,
            timeout=timeout + 5
        )
        response_time = round((time.time() - start_time) * 1000, 2)
        
        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                if 'time=' in line:
                    time_str = line.split('time=')[1].split()[0]
                    response_time = float(time_str.replace('ms', ''))
                    break
                    
            return {
                "status": "up",
                "response_time": response_time,
                "status_code": None,
                "error": None,
                "details": {"output": result.stdout}
            }
        else:
            return {
                "status": "down",
                "response_time": None,
                "status_code": None,
                "error": "Host unreachable",
                "details": {"output": result.stderr}
            }
            
    except subprocess.TimeoutExpired:
        return {
            "status": "down",
            "response_time": None,
            "status_code": None,
            "error": "Ping timeout",
            "details": {}
        }
    except Exception as e:
        return {
            "status": "down",
            "response_time": None,
            "status_code": None,
            "error": str(e),
            "details": {}
        }

def check_port(monitor):
    url = monitor.get("url", "")
    port = monitor.get("port", 80)
    timeout = monitor.get("timeout", 10)
    
    parsed = urlparse(url)
    host = parsed.hostname or url.replace("http://", "").replace("https://", "").split("/")[0]
    
    try:
        start_time = time.time()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        response_time = round((time.time() - start_time) * 1000, 2)
        sock.close()
        
        if result == 0:
            return {
                "status": "up",
                "response_time": response_time,
                "status_code": None,
                "error": None,
                "details": {"port": port}
            }
        else:
            return {
                "status": "down",
                "response_time": None,
                "status_code": None,
                "error": f"Port {port} is closed",
                "details": {"port": port}
            }
            
    except socket.timeout:
        return {
            "status": "down",
            "response_time": None,
            "status_code": None,
            "error": "Connection timeout",
            "details": {"port": port}
        }
    except Exception as e:
        return {
            "status": "down",
            "response_time": None,
            "status_code": None,
            "error": str(e),
            "details": {"port": port}
        }

def check_ssl(monitor):
    url = monitor.get("url", "")
    threshold = monitor.get("ssl_expiry_threshold", 30)
    
    parsed = urlparse(url)
    host = parsed.hostname or url.replace("https://", "").replace("http://", "").split("/")[0]
    port = parsed.port or 443
    
    try:
        start_time = time.time()
        
        context = ssl.create_default_context()
        conn = context.wrap_socket(
            socket.socket(socket.AF_INET),
            server_hostname=host
        )
        conn.settimeout(10)
        conn.connect((host, port))
        
        cert_bin = conn.getpeercert(binary_form=True)
        x509 = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_ASN1, cert_bin)
        
        response_time = round((time.time() - start_time) * 1000, 2)
        
        expiry_date_str = x509.get_notAfter().decode('utf-8')
        expiry_date = datetime.strptime(expiry_date_str, '%Y%m%d%H%M%SZ')
        days_until_expiry = (expiry_date - datetime.utcnow()).days
        
        issuer = dict(x509.get_issuer().get_components())
        subject = dict(x509.get_subject().get_components())
        
        conn.close()
        
        status = "up" if days_until_expiry > threshold else "down"
        
        return {
            "status": status,
            "response_time": response_time,
            "status_code": None,
            "error": None if status == "up" else f"SSL expires in {days_until_expiry} days",
            "details": {
                "expiry_date": expiry_date.isoformat(),
                "days_until_expiry": days_until_expiry,
                "issuer": {k.decode(): v.decode() for k, v in issuer.items()},
                "subject": {k.decode(): v.decode() for k, v in subject.items()}
            }
        }
        
    except ssl.SSLError as e:
        return {
            "status": "down",
            "response_time": None,
            "status_code": None,
            "error": f"SSL Error: {str(e)}",
            "details": {}
        }
    except Exception as e:
        return {
            "status": "down",
            "response_time": None,
            "status_code": None,
            "error": str(e),
            "details": {}
        }

def check_domain(monitor):
    url = monitor.get("url", "")
    threshold = monitor.get("domain_expiry_threshold", 30)
    
    parsed = urlparse(url)
    domain = parsed.hostname or url.replace("http://", "").replace("https://", "").split("/")[0]
    
    try:
        import subprocess
        start_time = time.time()
        
        result = subprocess.run(
            ["whois", domain],
            capture_output=True,
            text=True,
            timeout=30
        )
        response_time = round((time.time() - start_time) * 1000, 2)
        
        output = result.stdout.lower()
        expiry_date = None
        
        expiry_patterns = [
            "expiry date:", "expiration date:", "registry expiry date:",
            "registrar registration expiration date:", "expires on:", "expire date:"
        ]
        
        for line in output.split('\n'):
            for pattern in expiry_patterns:
                if pattern in line.lower():
                    date_str = line.split(':', 1)[1].strip()
                    try:
                        from dateutil import parser
                        expiry_date = parser.parse(date_str)
                        break
                    except:
                        pass
            if expiry_date:
                break
                
        if expiry_date:
            days_until_expiry = (expiry_date - datetime.now()).days
            status = "up" if days_until_expiry > threshold else "down"
            
            return {
                "status": status,
                "response_time": response_time,
                "status_code": None,
                "error": None if status == "up" else f"Domain expires in {days_until_expiry} days",
                "details": {
                    "expiry_date": expiry_date.isoformat(),
                    "days_until_expiry": days_until_expiry,
                    "domain": domain
                }
            }
        else:
            return {
                "status": "up",
                "response_time": response_time,
                "status_code": None,
                "error": None,
                "details": {
                    "message": "Could not parse expiry date",
                    "domain": domain
                }
            }
            
    except Exception as e:
        return {
            "status": "down",
            "response_time": None,
            "status_code": None,
            "error": str(e),
            "details": {}
        }

def run_check(monitor):
    monitor_type = monitor.get("type", "http")
    
    check_functions = {
        "http": check_http,
        "keyword": check_keyword,
        "ping": check_ping,
        "port": check_port,
        "ssl": check_ssl,
        "domain": check_domain
    }
    
    check_func = check_functions.get(monitor_type, check_http)
    result = check_func(monitor)
    
    monitor_id = str(monitor["_id"])
    CheckResult.create(
        monitor_id=monitor_id,
        status=result["status"],
        response_time=result.get("response_time"),
        status_code=result.get("status_code"),
        error=result.get("error"),
        details=result.get("details", {})
    )
    
    previous_status = monitor.get("status", "pending")
    user_id = monitor.get("user_id")
    
    if result["status"] == "down" and previous_status != "down":
        Incident.create(
            monitor_id=monitor_id,
            monitor_name=monitor.get("name", "Unknown"),
            incident_type="down",
            details={"error": result.get("error")},
            user_id=user_id
        )
    elif result["status"] == "up" and previous_status == "down":
        ongoing = Incident.get_ongoing(user_id=user_id)
        for incident in ongoing:
            if incident["monitor_id"] == monitor_id:
                Incident.resolve(str(incident["_id"]), user_id=user_id)
    
    uptime = CheckResult.calculate_uptime(monitor_id)
    Monitor.update(monitor_id, {
        "status": result["status"],
        "last_check": datetime.utcnow(),
        "last_response_time": result.get("response_time"),
        "uptime_percentage": uptime
    })
    
    return result

def run_all_checks():
    monitors = Monitor.get_active_monitors()
    results = []
    
    for monitor in monitors:
        result = run_check(monitor)
        results.append({
            "monitor": monitor["name"],
            "result": result
        })
        
    return results
