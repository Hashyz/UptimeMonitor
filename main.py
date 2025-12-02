import streamlit as st
import streamlit.components.v1 as components
from datetime import datetime, timedelta
import time
import re
from streamlit_js_eval import streamlit_js_eval
from models import Monitor, CheckResult, Incident, Notification, StatusPage, User
from monitoring import run_check, run_all_checks
from config import MONITOR_TYPES, MONITOR_INTERVALS, HTTP_METHODS, MONITOR_STATUS, NOTIFICATION_TYPES
from database import get_database
from scheduler import sync_all_monitors, get_scheduler_status
from auth import create_user, authenticate_user, get_user_by_email, validate_session, delete_session

st.set_page_config(
    page_title="Uptime Monitor",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

def get_browser_token():
    try:
        token = streamlit_js_eval(js_expressions="localStorage.getItem('uptime_session_token')", key="get_token")
        return token
    except Exception:
        return None

def set_browser_token(token):
    if token:
        streamlit_js_eval(js_expressions=f"localStorage.setItem('uptime_session_token', '{token}')", key="set_token")

def clear_browser_token():
    streamlit_js_eval(js_expressions="localStorage.removeItem('uptime_session_token')", key="clear_token")

components.html("""
<script>
    // Inject meta tags into document head
    const metaTags = [
        {name: "description", content: "Enterprise-grade uptime monitoring solution. Monitor websites, APIs, and services with real-time alerts, incident tracking, and public status pages."},
        {name: "keywords", content: "uptime monitor, website monitoring, server monitoring, uptime tracking, status page, incident management, API monitoring"},
        {name: "author", content: "Hashyz"},
        {name: "robots", content: "index, follow"},
        {property: "og:type", content: "website"},
        {property: "og:title", content: "Uptime Monitor - Enterprise Website Monitoring"},
        {property: "og:description", content: "Monitor your websites and services with confidence. Real-time alerts, incident tracking, and public status pages."},
        {property: "og:site_name", content: "Uptime Monitor"},
        {name: "twitter:card", content: "summary_large_image"},
        {name: "twitter:title", content: "Uptime Monitor - Enterprise Website Monitoring"},
        {name: "twitter:description", content: "Monitor your websites and services with confidence. Real-time alerts, incident tracking, and public status pages."}
    ];
    
    metaTags.forEach(tag => {
        const meta = document.createElement('meta');
        if (tag.name) meta.setAttribute('name', tag.name);
        if (tag.property) meta.setAttribute('property', tag.property);
        meta.setAttribute('content', tag.content);
        document.head.appendChild(meta);
    });
</script>
""", height=0)

st.markdown("""
<style>
    .stApp {
        background-color: #0e1117;
    }
    .monitor-card {
        background-color: #1a1f2e;
        padding: 1rem;
        border-radius: 8px;
        margin-bottom: 1rem;
        border-left: 4px solid #4CAF50;
    }
    .monitor-card.down {
        border-left-color: #f44336;
    }
    .monitor-card.paused {
        border-left-color: #9e9e9e;
    }
    .status-up {
        color: #4CAF50;
        font-weight: bold;
    }
    .status-down {
        color: #f44336;
        font-weight: bold;
    }
    .status-paused {
        color: #9e9e9e;
        font-weight: bold;
    }
    .metric-card {
        background-color: #1a1f2e;
        padding: 1.5rem;
        border-radius: 8px;
        text-align: center;
    }
    .uptime-bar {
        display: flex;
        gap: 2px;
        margin-top: 0.5rem;
    }
    .uptime-segment {
        flex: 1;
        height: 20px;
        border-radius: 2px;
    }
    .uptime-up {
        background-color: #4CAF50;
    }
    .uptime-down {
        background-color: #f44336;
    }
    .uptime-unknown {
        background-color: #9e9e9e;
    }
</style>
""", unsafe_allow_html=True)

def init_session_state():
    if "page" not in st.session_state:
        st.session_state.page = "dashboard"
    if "selected_monitor" not in st.session_state:
        st.session_state.selected_monitor = None
    if "edit_mode" not in st.session_state:
        st.session_state.edit_mode = False
    if "user" not in st.session_state:
        st.session_state.user = None
    if "auth_mode" not in st.session_state:
        st.session_state.auth_mode = "login"
    if "scheduler_initialized" not in st.session_state:
        st.session_state.scheduler_initialized = False
    if "session_token" not in st.session_state:
        st.session_state.session_token = None

def restore_session_from_token():
    if st.session_state.user is not None:
        return
    
    try:
        token = get_browser_token()
        
        if token and token != "null" and token != "":
            user = validate_session(token)
            if user:
                st.session_state.user = user
                st.session_state.session_token = token
                return
    except Exception:
        pass

def init_scheduler():
    if not st.session_state.scheduler_initialized:
        try:
            count = sync_all_monitors()
            st.session_state.scheduler_initialized = True
            print(f"Scheduler initialized with {count} monitors")
        except Exception as e:
            print(f"Failed to initialize scheduler: {e}")

def is_authenticated():
    return st.session_state.user is not None

def get_current_user_id():
    if st.session_state.user:
        return str(st.session_state.user.get("_id", ""))
    return None

def logout():
    try:
        if st.session_state.session_token:
            delete_session(st.session_state.session_token)
        clear_browser_token()
    except Exception:
        pass
    
    st.session_state.user = None
    st.session_state.session_token = None
    st.session_state.page = "dashboard"
    st.rerun()

def validate_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def render_login_page():
    st.markdown("""
    <style>
        .auth-container {
            max-width: 400px;
            margin: 0 auto;
            padding: 2rem;
        }
        .auth-header {
            text-align: center;
            margin-bottom: 2rem;
        }
        .auth-header h1 {
            font-size: 2.5rem;
            margin-bottom: 0.5rem;
        }
        .auth-header p {
            color: #888;
        }
        .auth-form {
            background-color: #1a1f2e;
            padding: 2rem;
            border-radius: 10px;
            border: 1px solid #2d3748;
        }
        .auth-tabs {
            display: flex;
            margin-bottom: 1.5rem;
        }
        .auth-tab {
            flex: 1;
            padding: 0.75rem;
            text-align: center;
            cursor: pointer;
            border-bottom: 2px solid transparent;
            color: #888;
            transition: all 0.3s;
        }
        .auth-tab.active {
            border-bottom-color: #4CAF50;
            color: white;
        }
        .auth-tab:hover {
            color: white;
        }
    </style>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("<div class='auth-header'><h1>🔍 Uptime Monitor</h1><p>Monitor your services with confidence</p></div>", unsafe_allow_html=True)
        
        tab1, tab2 = st.tabs(["🔐 Login", "📝 Register"])
        
        with tab1:
            with st.form("login_form", clear_on_submit=False):
                st.subheader("Welcome Back")
                login_email = st.text_input("Email", placeholder="your@email.com", key="login_email")
                login_password = st.text_input("Password", type="password", placeholder="Enter your password", key="login_password")
                
                login_submitted = st.form_submit_button("Sign In", type="primary", use_container_width=True)
                
                if login_submitted:
                    if not login_email or not login_password:
                        st.error("Please fill in all fields")
                    elif not validate_email(login_email):
                        st.error("Please enter a valid email address")
                    else:
                        result = authenticate_user(login_email, login_password)
                        if result["success"]:
                            st.session_state.user = result["user"]
                            if result.get("token"):
                                st.session_state.session_token = result["token"]
                                set_browser_token(result["token"])
                            st.success("Login successful! Redirecting...")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error(result["error"])
        
        with tab2:
            with st.form("register_form", clear_on_submit=False):
                st.subheader("Create Account")
                reg_name = st.text_input("Full Name", placeholder="John Doe", key="reg_name")
                reg_email = st.text_input("Email", placeholder="your@email.com", key="reg_email")
                reg_password = st.text_input("Password", type="password", placeholder="Create a password (min 6 characters)", key="reg_password")
                reg_confirm = st.text_input("Confirm Password", type="password", placeholder="Confirm your password", key="reg_confirm")
                
                reg_submitted = st.form_submit_button("Create Account", type="primary", use_container_width=True)
                
                if reg_submitted:
                    if not reg_name or not reg_email or not reg_password or not reg_confirm:
                        st.error("Please fill in all fields")
                    elif not validate_email(reg_email):
                        st.error("Please enter a valid email address")
                    elif len(reg_password) < 6:
                        st.error("Password must be at least 6 characters long")
                    elif reg_password != reg_confirm:
                        st.error("Passwords do not match")
                    else:
                        result = create_user(reg_email, reg_password, reg_name)
                        if result["success"]:
                            st.session_state.user = result["user"]
                            if result.get("token"):
                                st.session_state.session_token = result["token"]
                                set_browser_token(result["token"])
                            st.success("Account created successfully! Redirecting...")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error(result["error"])
        
        st.markdown("---")
        st.markdown("<p style='text-align: center; color: #888;'>Enterprise-grade uptime monitoring solution</p>", unsafe_allow_html=True)

def render_sidebar():
    with st.sidebar:
        st.title("Uptime Monitor")
        st.markdown("---")
        
        if is_authenticated():
            user = st.session_state.user
            st.markdown(f"👤 **{user.get('name', 'User')}**")
            st.caption(user.get('email', ''))
            if st.button("🚪 Logout", use_container_width=True):
                logout()
            st.markdown("---")
        
        db = get_database()
        if db is not None:
            st.success("Database Connected")
        else:
            st.error("Database Error")
        
        st.markdown("### Navigation")
        
        if st.button("Dashboard", use_container_width=True, type="primary" if st.session_state.page == "dashboard" else "secondary"):
            st.session_state.page = "dashboard"
            st.rerun()
            
        if st.button("Monitors", use_container_width=True, type="primary" if st.session_state.page == "monitors" else "secondary"):
            st.session_state.page = "monitors"
            st.rerun()
            
        if st.button("Add Monitor", use_container_width=True, type="primary" if st.session_state.page == "add_monitor" else "secondary"):
            st.session_state.page = "add_monitor"
            st.rerun()
            
        if st.button("Incidents", use_container_width=True, type="primary" if st.session_state.page == "incidents" else "secondary"):
            st.session_state.page = "incidents"
            st.rerun()
            
        if st.button("Status Pages", use_container_width=True, type="primary" if st.session_state.page == "status_pages" else "secondary"):
            st.session_state.page = "status_pages"
            st.rerun()
            
        if st.button("Notifications", use_container_width=True, type="primary" if st.session_state.page == "notifications" else "secondary"):
            st.session_state.page = "notifications"
            st.rerun()
            
        if st.button("Settings", use_container_width=True, type="primary" if st.session_state.page == "settings" else "secondary"):
            st.session_state.page = "settings"
            st.rerun()
        
        st.markdown("---")
        st.markdown("### Quick Actions")
        
        if st.button("Run All Checks", use_container_width=True):
            with st.spinner("Running checks..."):
                results = run_all_checks()
                st.success(f"Completed {len(results)} checks")
                time.sleep(1)
                st.rerun()

def render_dashboard():
    st.title("Dashboard")
    
    user_id = get_current_user_id()
    monitors = Monitor.get_all(user_id=user_id)
    
    up_count = sum(1 for m in monitors if m.get("status") == "up")
    down_count = sum(1 for m in monitors if m.get("status") == "down")
    paused_count = sum(1 for m in monitors if m.get("is_paused", False))
    total_count = len(monitors)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Monitors", total_count)
    with col2:
        st.metric("Up", up_count, delta=None)
    with col3:
        st.metric("Down", down_count, delta=None)
    with col4:
        st.metric("Paused", paused_count)
    
    st.markdown("---")
    
    col_left, col_right = st.columns([2, 1])
    
    with col_left:
        st.subheader("Current Status")
        
        if not monitors:
            st.info("No monitors configured yet. Add your first monitor to get started!")
        else:
            for monitor in monitors:
                status = monitor.get("status", "pending")
                is_paused = monitor.get("is_paused", False)
                
                if is_paused:
                    status_class = "paused"
                    status_icon = "⏸️"
                elif status == "up":
                    status_class = "up"
                    status_icon = "🟢"
                elif status == "down":
                    status_class = "down"
                    status_icon = "🔴"
                else:
                    status_class = "paused"
                    status_icon = "⚪"
                
                with st.container():
                    col_a, col_b, col_c, col_d = st.columns([3, 1, 1, 1])
                    
                    with col_a:
                        st.markdown(f"**{status_icon} {monitor.get('name', 'Unknown')}**")
                        st.caption(f"{monitor.get('url', '')} • {MONITOR_TYPES.get(monitor.get('type', 'http'), 'HTTP')}")
                    
                    with col_b:
                        uptime = monitor.get("uptime_percentage", 100)
                        st.metric("Uptime", f"{uptime}%")
                    
                    with col_c:
                        response_time = monitor.get("last_response_time")
                        st.metric("Response", f"{response_time}ms" if response_time else "N/A")
                    
                    with col_d:
                        last_check = monitor.get("last_check")
                        if last_check:
                            diff = datetime.utcnow() - last_check
                            if diff.seconds < 60:
                                st.caption(f"{diff.seconds}s ago")
                            else:
                                st.caption(f"{diff.seconds // 60}m ago")
                        else:
                            st.caption("Never")
                    
                    st.markdown("---")
    
    with col_right:
        st.subheader("Last 24 Hours")
        
        if monitors:
            total_uptime = sum(m.get("uptime_percentage", 100) for m in monitors) / len(monitors) if monitors else 100
            st.metric("Overall Uptime", f"{total_uptime:.2f}%")
        
        st.markdown("---")
        st.subheader("Recent Incidents")
        
        incidents = Incident.get_recent(5, user_id=user_id)
        
        if incidents:
            for incident in incidents:
                status = incident.get("status", "ongoing")
                icon = "🔴" if status == "ongoing" else "✅"
                st.markdown(f"{icon} **{incident.get('monitor_name', 'Unknown')}**")
                st.caption(f"{incident.get('created_at', '').strftime('%Y-%m-%d %H:%M') if incident.get('created_at') else 'Unknown'}")
        else:
            st.success("No incidents in the last 24 hours!")

def render_monitors():
    st.title("Monitors")
    
    user_id = get_current_user_id()
    
    col1, col2 = st.columns([3, 1])
    with col1:
        search = st.text_input("Search monitors", placeholder="Search by name or URL...")
    with col2:
        filter_status = st.selectbox("Filter by status", ["All", "Up", "Down", "Paused"])
    
    monitors = Monitor.get_all(user_id=user_id)
    
    if search:
        monitors = [m for m in monitors if search.lower() in m.get("name", "").lower() or search.lower() in m.get("url", "").lower()]
    
    if filter_status != "All":
        if filter_status == "Paused":
            monitors = [m for m in monitors if m.get("is_paused", False)]
        else:
            monitors = [m for m in monitors if m.get("status", "").lower() == filter_status.lower() and not m.get("is_paused", False)]
    
    st.markdown("---")
    
    if not monitors:
        st.info("No monitors found. Add your first monitor to get started!")
        if st.button("Add Monitor"):
            st.session_state.page = "add_monitor"
            st.rerun()
    else:
        for monitor in monitors:
            status = monitor.get("status", "pending")
            is_paused = monitor.get("is_paused", False)
            
            if is_paused:
                status_icon = "⏸️"
            elif status == "up":
                status_icon = "🟢"
            elif status == "down":
                status_icon = "🔴"
            else:
                status_icon = "⚪"
            
            with st.expander(f"{status_icon} {monitor.get('name', 'Unknown')} - {monitor.get('url', '')}", expanded=False):
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.markdown("**Details**")
                    st.write(f"Type: {MONITOR_TYPES.get(monitor.get('type', 'http'), 'HTTP')}")
                    st.write(f"Interval: {MONITOR_INTERVALS.get(monitor.get('interval', 300), '5 minutes')}")
                    st.write(f"Timeout: {monitor.get('timeout', 30)}s")
                
                with col2:
                    st.markdown("**Statistics**")
                    st.write(f"Uptime: {monitor.get('uptime_percentage', 100)}%")
                    response_time = monitor.get("last_response_time")
                    st.write(f"Response Time: {response_time}ms" if response_time else "Response Time: N/A")
                    last_check = monitor.get("last_check")
                    if last_check:
                        st.write(f"Last Check: {last_check.strftime('%Y-%m-%d %H:%M:%S')}")
                    else:
                        st.write("Last Check: Never")
                
                with col3:
                    st.markdown("**Actions**")
                    
                    action_col1, action_col2 = st.columns(2)
                    
                    with action_col1:
                        if st.button("Check Now", key=f"check_{monitor['_id']}"):
                            with st.spinner("Running check..."):
                                result = run_check(monitor)
                                if result["status"] == "up":
                                    st.success("Monitor is UP!")
                                else:
                                    st.error(f"Monitor is DOWN: {result.get('error', 'Unknown error')}")
                                time.sleep(1)
                                st.rerun()
                        
                        if monitor.get("is_paused", False):
                            if st.button("Resume", key=f"resume_{monitor['_id']}"):
                                Monitor.update(str(monitor["_id"]), {"is_paused": False}, user_id=user_id)
                                st.success("Monitor resumed!")
                                time.sleep(0.5)
                                st.rerun()
                        else:
                            if st.button("Pause", key=f"pause_{monitor['_id']}"):
                                Monitor.update(str(monitor["_id"]), {"is_paused": True}, user_id=user_id)
                                st.success("Monitor paused!")
                                time.sleep(0.5)
                                st.rerun()
                    
                    with action_col2:
                        if st.button("Edit", key=f"edit_{monitor['_id']}"):
                            st.session_state.selected_monitor = str(monitor["_id"])
                            st.session_state.page = "edit_monitor"
                            st.rerun()
                        
                        if st.button("Delete", key=f"delete_{monitor['_id']}", type="secondary"):
                            Monitor.delete(str(monitor["_id"]), user_id=user_id)
                            st.success("Monitor deleted!")
                            time.sleep(0.5)
                            st.rerun()
                
                st.markdown("---")
                st.markdown("**Recent Checks**")
                
                checks = CheckResult.get_by_monitor(str(monitor["_id"]), limit=10)
                if checks:
                    check_cols = st.columns(10)
                    for i, check in enumerate(checks[:10]):
                        with check_cols[i]:
                            if check.get("status") == "up":
                                st.markdown("🟢")
                            else:
                                st.markdown("🔴")
                else:
                    st.caption("No check history yet")

def render_add_monitor():
    st.title("Add New Monitor")
    
    with st.form("add_monitor_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            name = st.text_input("Monitor Name", placeholder="My Website")
            url = st.text_input("URL / Host", placeholder="https://example.com")
            monitor_type = st.selectbox("Monitor Type", options=list(MONITOR_TYPES.keys()), format_func=lambda x: MONITOR_TYPES[x])
            interval = st.selectbox("Check Interval", options=list(MONITOR_INTERVALS.keys()), format_func=lambda x: MONITOR_INTERVALS[x], index=4)
        
        with col2:
            timeout = st.slider("Timeout (seconds)", min_value=5, max_value=60, value=30)
            group = st.text_input("Group", value="default")
            tags = st.text_input("Tags (comma-separated)", placeholder="production, api, critical")
            notes = st.text_area("Notes", placeholder="Additional notes about this monitor...")
        
        st.markdown("---")
        st.subheader("Type-Specific Settings")
        
        http_method = "GET"
        expected_status_codes = [200, 201, 301, 302]
        follow_redirects = True
        keyword = ""
        keyword_type = "exists"
        port = 80
        ssl_expiry_threshold = 30
        domain_expiry_threshold = 30
        headers = {}
        body = ""
        
        if monitor_type in ["http", "keyword"]:
            col1, col2 = st.columns(2)
            with col1:
                http_method = st.selectbox("HTTP Method", HTTP_METHODS)
                follow_redirects = st.checkbox("Follow Redirects", value=True)
            with col2:
                status_codes_str = st.text_input("Expected Status Codes", value="200, 201, 301, 302")
                expected_status_codes = [int(x.strip()) for x in status_codes_str.split(",") if x.strip().isdigit()]
            
            headers_str = st.text_area("Custom Headers (JSON format)", placeholder='{"Authorization": "Bearer token"}')
            if headers_str:
                try:
                    import json
                    headers = json.loads(headers_str)
                except:
                    st.warning("Invalid JSON format for headers")
            
            if http_method in ["POST", "PUT", "PATCH"]:
                body = st.text_area("Request Body", placeholder="Request body content...")
        
        if monitor_type == "keyword":
            col1, col2 = st.columns(2)
            with col1:
                keyword = st.text_input("Keyword to Search", placeholder="Enter keyword...")
            with col2:
                keyword_type = st.selectbox("Keyword Condition", ["exists", "not_exists"], format_func=lambda x: "Keyword exists" if x == "exists" else "Keyword does not exist")
        
        if monitor_type == "port":
            port = st.number_input("Port Number", min_value=1, max_value=65535, value=80)
        
        if monitor_type == "ssl":
            ssl_expiry_threshold = st.slider("SSL Expiry Alert (days before)", min_value=1, max_value=90, value=30)
        
        if monitor_type == "domain":
            domain_expiry_threshold = st.slider("Domain Expiry Alert (days before)", min_value=1, max_value=90, value=30)
        
        st.markdown("---")
        st.subheader("Notification Settings")
        
        col1, col2 = st.columns(2)
        with col1:
            notify_enabled = st.checkbox("Enable Notifications", value=True)
            notify_on_down = st.checkbox("Notify when Down", value=True)
        with col2:
            notify_on_up = st.checkbox("Notify when Back Up", value=True)
            notify_delay = st.number_input("Notification Delay (seconds)", min_value=0, value=0)
        
        submitted = st.form_submit_button("Create Monitor", type="primary", use_container_width=True)
        
        if submitted:
            if not name:
                st.error("Please enter a monitor name")
            elif not url:
                st.error("Please enter a URL or host")
            else:
                tags_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
                
                user_id = get_current_user_id()
                monitor = Monitor.create(
                    name=name,
                    monitor_type=monitor_type,
                    url=url,
                    interval=interval,
                    user_id=user_id,
                    timeout=timeout,
                    http_method=http_method,
                    expected_status_codes=expected_status_codes,
                    keyword=keyword,
                    keyword_type=keyword_type,
                    port=port,
                    headers=headers,
                    body=body,
                    follow_redirects=follow_redirects,
                    ssl_expiry_threshold=ssl_expiry_threshold,
                    domain_expiry_threshold=domain_expiry_threshold,
                    notification_settings={
                        "enabled": notify_enabled,
                        "on_down": notify_on_down,
                        "on_up": notify_on_up,
                        "delay": notify_delay
                    },
                    tags=tags_list,
                    group=group,
                    notes=notes
                )
                
                if monitor:
                    st.success("Monitor created successfully!")
                    with st.spinner("Running initial check..."):
                        run_check(monitor)
                    time.sleep(1)
                    st.session_state.page = "monitors"
                    st.rerun()
                else:
                    st.error("Failed to create monitor. Please check database connection.")

def render_edit_monitor():
    st.title("Edit Monitor")
    
    user_id = get_current_user_id()
    monitor_id = st.session_state.selected_monitor
    if not monitor_id:
        st.error("No monitor selected")
        if st.button("Back to Monitors"):
            st.session_state.page = "monitors"
            st.rerun()
        return
    
    monitor = Monitor.get_by_id(monitor_id, user_id=user_id)
    if not monitor:
        st.error("Monitor not found")
        if st.button("Back to Monitors"):
            st.session_state.page = "monitors"
            st.rerun()
        return
    
    with st.form("edit_monitor_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            name = st.text_input("Monitor Name", value=monitor.get("name", ""))
            url = st.text_input("URL / Host", value=monitor.get("url", ""))
            current_type_index = list(MONITOR_TYPES.keys()).index(monitor.get("type", "http")) if monitor.get("type") in MONITOR_TYPES else 0
            monitor_type = st.selectbox("Monitor Type", options=list(MONITOR_TYPES.keys()), format_func=lambda x: MONITOR_TYPES[x], index=current_type_index)
            
            interval_keys = list(MONITOR_INTERVALS.keys())
            current_interval = monitor.get("interval", 300)
            interval_index = interval_keys.index(current_interval) if current_interval in interval_keys else 4
            interval = st.selectbox("Check Interval", options=interval_keys, format_func=lambda x: MONITOR_INTERVALS[x], index=interval_index)
        
        with col2:
            timeout = st.slider("Timeout (seconds)", min_value=5, max_value=60, value=monitor.get("timeout", 30))
            group = st.text_input("Group", value=monitor.get("group", "default"))
            tags = st.text_input("Tags (comma-separated)", value=", ".join(monitor.get("tags", [])))
            notes = st.text_area("Notes", value=monitor.get("notes", ""))
        
        st.markdown("---")
        st.subheader("Type-Specific Settings")
        
        http_method = monitor.get("http_method", "GET")
        expected_status_codes = monitor.get("expected_status_codes", [200, 201, 301, 302])
        follow_redirects = monitor.get("follow_redirects", True)
        keyword = monitor.get("keyword", "")
        keyword_type = monitor.get("keyword_type", "exists")
        port = monitor.get("port", 80)
        ssl_expiry_threshold = monitor.get("ssl_expiry_threshold", 30)
        domain_expiry_threshold = monitor.get("domain_expiry_threshold", 30)
        headers = monitor.get("headers", {})
        body = monitor.get("body", "")
        
        if monitor_type in ["http", "keyword"]:
            col1, col2 = st.columns(2)
            with col1:
                method_index = HTTP_METHODS.index(http_method) if http_method in HTTP_METHODS else 0
                http_method = st.selectbox("HTTP Method", HTTP_METHODS, index=method_index)
                follow_redirects = st.checkbox("Follow Redirects", value=follow_redirects)
            with col2:
                status_codes_str = st.text_input("Expected Status Codes", value=", ".join(map(str, expected_status_codes)))
                expected_status_codes = [int(x.strip()) for x in status_codes_str.split(",") if x.strip().isdigit()]
            
            import json
            headers_str = st.text_area("Custom Headers (JSON format)", value=json.dumps(headers) if headers else "")
            if headers_str:
                try:
                    headers = json.loads(headers_str)
                except:
                    st.warning("Invalid JSON format for headers")
            
            if http_method in ["POST", "PUT", "PATCH"]:
                body = st.text_area("Request Body", value=body)
        
        if monitor_type == "keyword":
            col1, col2 = st.columns(2)
            with col1:
                keyword = st.text_input("Keyword to Search", value=keyword)
            with col2:
                kw_index = 0 if keyword_type == "exists" else 1
                keyword_type = st.selectbox("Keyword Condition", ["exists", "not_exists"], format_func=lambda x: "Keyword exists" if x == "exists" else "Keyword does not exist", index=kw_index)
        
        if monitor_type == "port":
            port = st.number_input("Port Number", min_value=1, max_value=65535, value=port)
        
        if monitor_type == "ssl":
            ssl_expiry_threshold = st.slider("SSL Expiry Alert (days before)", min_value=1, max_value=90, value=ssl_expiry_threshold)
        
        if monitor_type == "domain":
            domain_expiry_threshold = st.slider("Domain Expiry Alert (days before)", min_value=1, max_value=90, value=domain_expiry_threshold)
        
        st.markdown("---")
        st.subheader("Notification Settings")
        
        notify_settings = monitor.get("notification_settings", {})
        col1, col2 = st.columns(2)
        with col1:
            notify_enabled = st.checkbox("Enable Notifications", value=notify_settings.get("enabled", True))
            notify_on_down = st.checkbox("Notify when Down", value=notify_settings.get("on_down", True))
        with col2:
            notify_on_up = st.checkbox("Notify when Back Up", value=notify_settings.get("on_up", True))
            notify_delay = st.number_input("Notification Delay (seconds)", min_value=0, value=notify_settings.get("delay", 0))
        
        col1, col2 = st.columns(2)
        with col1:
            submitted = st.form_submit_button("Update Monitor", type="primary", use_container_width=True)
        with col2:
            cancelled = st.form_submit_button("Cancel", use_container_width=True)
        
        if submitted:
            if not name:
                st.error("Please enter a monitor name")
            elif not url:
                st.error("Please enter a URL or host")
            else:
                tags_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
                
                updates = {
                    "name": name,
                    "url": url,
                    "type": monitor_type,
                    "interval": interval,
                    "timeout": timeout,
                    "http_method": http_method,
                    "expected_status_codes": expected_status_codes,
                    "keyword": keyword,
                    "keyword_type": keyword_type,
                    "port": port,
                    "headers": headers,
                    "body": body,
                    "follow_redirects": follow_redirects,
                    "ssl_expiry_threshold": ssl_expiry_threshold,
                    "domain_expiry_threshold": domain_expiry_threshold,
                    "notification_settings": {
                        "enabled": notify_enabled,
                        "on_down": notify_on_down,
                        "on_up": notify_on_up,
                        "delay": notify_delay
                    },
                    "tags": tags_list,
                    "group": group,
                    "notes": notes
                }
                
                if Monitor.update(monitor_id, updates, user_id=user_id):
                    st.success("Monitor updated successfully!")
                    time.sleep(1)
                    st.session_state.page = "monitors"
                    st.rerun()
                else:
                    st.error("Failed to update monitor")
        
        if cancelled:
            st.session_state.page = "monitors"
            st.rerun()

def render_incidents():
    st.title("Incidents")
    
    user_id = get_current_user_id()
    
    tab1, tab2 = st.tabs(["Ongoing", "History"])
    
    with tab1:
        ongoing = Incident.get_ongoing(user_id=user_id)
        
        if not ongoing:
            st.success("No ongoing incidents! All systems operational.")
        else:
            for incident in ongoing:
                with st.container():
                    col1, col2, col3 = st.columns([3, 1, 1])
                    
                    with col1:
                        st.markdown(f"🔴 **{incident.get('monitor_name', 'Unknown')}**")
                        st.caption(f"Started: {incident.get('created_at', '').strftime('%Y-%m-%d %H:%M:%S') if incident.get('created_at') else 'Unknown'}")
                        if incident.get("details", {}).get("error"):
                            st.error(incident["details"]["error"])
                    
                    with col2:
                        if incident.get("created_at"):
                            duration = datetime.utcnow() - incident["created_at"]
                            st.metric("Duration", f"{duration.seconds // 60}m {duration.seconds % 60}s")
                    
                    with col3:
                        if st.button("Resolve", key=f"resolve_{incident['_id']}"):
                            Incident.resolve(str(incident["_id"]), user_id=user_id)
                            st.success("Incident resolved!")
                            time.sleep(0.5)
                            st.rerun()
                    
                    st.markdown("---")
    
    with tab2:
        st.subheader("Incident History")
        
        history = Incident.get_recent(50, user_id=user_id)
        resolved = [i for i in history if i.get("status") == "resolved"]
        
        if not resolved:
            st.info("No incident history yet.")
        else:
            for incident in resolved:
                with st.expander(f"✅ {incident.get('monitor_name', 'Unknown')} - {incident.get('created_at', '').strftime('%Y-%m-%d %H:%M') if incident.get('created_at') else 'Unknown'}"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write(f"**Started:** {incident.get('created_at', '').strftime('%Y-%m-%d %H:%M:%S') if incident.get('created_at') else 'Unknown'}")
                        st.write(f"**Resolved:** {incident.get('resolved_at', '').strftime('%Y-%m-%d %H:%M:%S') if incident.get('resolved_at') else 'Unknown'}")
                    
                    with col2:
                        duration = incident.get("duration", 0)
                        if duration:
                            minutes = int(duration // 60)
                            seconds = int(duration % 60)
                            st.write(f"**Duration:** {minutes}m {seconds}s")
                        
                        if incident.get("details", {}).get("error"):
                            st.write(f"**Error:** {incident['details']['error']}")

def render_status_pages():
    st.title("Status Pages")
    
    user_id = get_current_user_id()
    
    tab1, tab2 = st.tabs(["Existing Pages", "Create New"])
    
    with tab1:
        pages = StatusPage.get_all(user_id=user_id)
        
        if not pages:
            st.info("No status pages created yet. Create your first public status page!")
        else:
            for page in pages:
                with st.expander(f"📊 {page.get('name', 'Unnamed')} - /{page.get('slug', '')}"):
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        st.write(f"**Slug:** {page.get('slug', '')}")
                        st.write(f"**Public:** {'Yes' if page.get('is_public', True) else 'No'}")
                        st.write(f"**Monitors:** {len(page.get('monitors', []))}")
                        if page.get('description'):
                            st.write(f"**Description:** {page.get('description')}")
                    
                    with col2:
                        if st.button("View", key=f"view_page_{page['_id']}"):
                            st.session_state.page = "view_status_page"
                            st.session_state.status_page_slug = page.get("slug")
                            st.rerun()
                        
                        if st.button("Delete", key=f"delete_page_{page['_id']}", type="secondary"):
                            StatusPage.delete(str(page["_id"]))
                            st.success("Status page deleted!")
                            time.sleep(0.5)
                            st.rerun()
    
    with tab2:
        with st.form("create_status_page"):
            name = st.text_input("Page Name", placeholder="My Status Page")
            slug = st.text_input("Page Slug", placeholder="my-status-page")
            description = st.text_area("Description", placeholder="Service status for My Company")
            
            monitors = Monitor.get_all(user_id=user_id)
            monitor_options = {str(m["_id"]): m.get("name", "Unknown") for m in monitors}
            
            if monitor_options:
                selected_monitors = st.multiselect("Select Monitors to Display", options=list(monitor_options.keys()), format_func=lambda x: monitor_options.get(x, x))
            else:
                st.info("No monitors available. Create monitors first.")
                selected_monitors = []
            
            is_public = st.checkbox("Make page public", value=True)
            password = st.text_input("Password (optional)", type="password", placeholder="Leave empty for no password")
            
            logo_url = st.text_input("Logo URL (optional)", placeholder="https://example.com/logo.png")
            custom_css = st.text_area("Custom CSS (optional)", placeholder="Custom styling...")
            
            submitted = st.form_submit_button("Create Status Page", type="primary", use_container_width=True)
            
            if submitted:
                if not name:
                    st.error("Please enter a page name")
                elif not slug:
                    st.error("Please enter a page slug")
                elif not selected_monitors:
                    st.error("Please select at least one monitor")
                else:
                    existing = StatusPage.get_by_slug(slug)
                    if existing:
                        st.error("A page with this slug already exists")
                    else:
                        page_id = StatusPage.create(
                            name=name,
                            slug=slug,
                            monitors=selected_monitors,
                            user_id=user_id,
                            is_public=is_public,
                            password=password if password else None,
                            logo_url=logo_url,
                            description=description,
                            custom_css=custom_css
                        )
                        
                        if page_id:
                            st.success("Status page created successfully!")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("Failed to create status page")

def render_view_status_page():
    slug = st.session_state.get("status_page_slug")
    
    if not slug:
        st.error("No status page selected")
        if st.button("Back"):
            st.session_state.page = "status_pages"
            st.rerun()
        return
    
    page = StatusPage.get_by_slug(slug)
    
    if not page:
        st.error("Status page not found")
        if st.button("Back"):
            st.session_state.page = "status_pages"
            st.rerun()
        return
    
    if st.button("Back to Status Pages"):
        st.session_state.page = "status_pages"
        st.rerun()
    
    st.markdown("---")
    
    if page.get("logo_url"):
        st.image(page["logo_url"], width=200)
    
    st.title(page.get("name", "Status Page"))
    
    if page.get("description"):
        st.markdown(page["description"])
    
    st.markdown("---")
    
    monitor_ids = page.get("monitors", [])
    monitors = [Monitor.get_by_id(mid) for mid in monitor_ids]
    monitors = [m for m in monitors if m]
    
    all_up = all(m.get("status") == "up" for m in monitors)
    
    if all_up:
        st.success("All Systems Operational", icon="✅")
    else:
        down_count = sum(1 for m in monitors if m.get("status") == "down")
        st.error(f"{down_count} system(s) experiencing issues", icon="⚠️")
    
    st.markdown("---")
    
    for monitor in monitors:
        status = monitor.get("status", "pending")
        
        if status == "up":
            status_icon = "🟢"
            status_text = "Operational"
        elif status == "down":
            status_icon = "🔴"
            status_text = "Down"
        else:
            status_icon = "⚪"
            status_text = "Unknown"
        
        col1, col2, col3 = st.columns([3, 1, 1])
        
        with col1:
            st.markdown(f"**{monitor.get('name', 'Unknown')}**")
        with col2:
            st.markdown(f"{status_icon} {status_text}")
        with col3:
            st.markdown(f"{monitor.get('uptime_percentage', 100):.2f}% uptime")
        
        st.markdown("---")
    
    st.caption(f"Last updated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")

def render_notifications():
    st.title("Notification Channels")
    
    user_id = get_current_user_id()
    
    tab1, tab2 = st.tabs(["Configured Channels", "Add New"])
    
    with tab1:
        notifications = Notification.get_all(user_id=user_id)
        
        if not notifications:
            st.info("No notification channels configured yet.")
        else:
            for notif in notifications:
                with st.expander(f"{'🔔' if notif.get('enabled', True) else '🔕'} {notif.get('name', 'Unnamed')} - {NOTIFICATION_TYPES.get(notif.get('type', ''), notif.get('type', ''))}"):
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        st.write(f"**Type:** {NOTIFICATION_TYPES.get(notif.get('type', ''), notif.get('type', ''))}")
                        st.write(f"**Enabled:** {'Yes' if notif.get('enabled', True) else 'No'}")
                        
                        config = notif.get("config", {})
                        if notif.get("type") == "email":
                            st.write(f"**Recipient:** {config.get('recipient_email', 'Not set')}")
                        elif notif.get("type") == "webhook":
                            st.write(f"**URL:** {config.get('webhook_url', 'Not set')[:50]}...")
                        elif notif.get("type") == "slack":
                            st.write(f"**Webhook:** {config.get('webhook_url', 'Not set')[:50]}...")
                        elif notif.get("type") == "telegram":
                            st.write(f"**Chat ID:** {config.get('chat_id', 'Not set')}")
                    
                    with col2:
                        if st.button("Delete", key=f"delete_notif_{notif['_id']}", type="secondary"):
                            Notification.delete(str(notif["_id"]), user_id=user_id)
                            st.success("Notification channel deleted!")
                            time.sleep(0.5)
                            st.rerun()
    
    with tab2:
        with st.form("add_notification"):
            name = st.text_input("Channel Name", placeholder="My Email Alert")
            notif_type = st.selectbox("Notification Type", options=list(NOTIFICATION_TYPES.keys()), format_func=lambda x: NOTIFICATION_TYPES[x])
            
            config = {}
            
            if notif_type == "email":
                st.subheader("Email Configuration")
                config["smtp_server"] = st.text_input("SMTP Server", value="smtp.gmail.com")
                config["smtp_port"] = st.number_input("SMTP Port", value=587)
                config["sender_email"] = st.text_input("Sender Email")
                config["sender_password"] = st.text_input("Sender Password", type="password")
                config["recipient_email"] = st.text_input("Recipient Email")
            
            elif notif_type == "webhook":
                st.subheader("Webhook Configuration")
                config["webhook_url"] = st.text_input("Webhook URL", placeholder="https://your-webhook-endpoint.com")
                headers_str = st.text_area("Custom Headers (JSON)", placeholder='{"Authorization": "Bearer token"}')
                if headers_str:
                    try:
                        import json
                        config["headers"] = json.loads(headers_str)
                    except:
                        st.warning("Invalid JSON format")
            
            elif notif_type == "slack":
                st.subheader("Slack Configuration")
                config["webhook_url"] = st.text_input("Slack Webhook URL", placeholder="https://hooks.slack.com/services/...")
            
            elif notif_type == "telegram":
                st.subheader("Telegram Configuration")
                config["bot_token"] = st.text_input("Bot Token", placeholder="Your Telegram bot token")
                config["chat_id"] = st.text_input("Chat ID", placeholder="Your chat or group ID")
            
            submitted = st.form_submit_button("Add Notification Channel", type="primary", use_container_width=True)
            
            if submitted:
                if not name:
                    st.error("Please enter a channel name")
                else:
                    notif_id = Notification.create(name, notif_type, config, user_id=user_id)
                    if notif_id:
                        st.success("Notification channel added successfully!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("Failed to add notification channel")

def render_settings():
    st.title("Settings")
    
    user_id = get_current_user_id()
    
    st.subheader("Background Scheduler")
    
    scheduler_status = get_scheduler_status()
    col1, col2 = st.columns(2)
    with col1:
        if scheduler_status["running"]:
            st.success("Scheduler Running")
        else:
            st.warning("Scheduler Stopped")
        st.metric("Active Jobs", scheduler_status["job_count"])
    
    with col2:
        if st.button("Sync All Monitors", use_container_width=True):
            count = sync_all_monitors()
            st.success(f"Synced {count} monitors to scheduler")
            time.sleep(1)
            st.rerun()
    
    st.markdown("---")
    
    st.subheader("Database Connection")
    db = get_database()
    if db is not None:
        st.success("Connected to MongoDB")
        st.write(f"Database: {db.name}")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Monitors", len(Monitor.get_all(user_id=user_id)))
        with col2:
            st.metric("Check Results", db.check_results.count_documents({}))
        with col3:
            st.metric("Incidents", db.incidents.count_documents({}))
    else:
        st.error("Not connected to database")
    
    st.markdown("---")
    
    st.subheader("Monitor Groups")
    groups = Monitor.get_groups(user_id=user_id)
    st.write("Current groups:", ", ".join(groups))
    
    st.markdown("---")
    
    st.subheader("Data Management")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Clear Old Check Results (>7 days)", type="secondary"):
            from datetime import timedelta
            cutoff = datetime.utcnow() - timedelta(days=7)
            db = get_database()
            if db is not None:
                result = db.check_results.delete_many({"timestamp": {"$lt": cutoff}})
                st.success(f"Deleted {result.deleted_count} old check results")
    
    with col2:
        if st.button("Clear Resolved Incidents (>30 days)", type="secondary"):
            from datetime import timedelta
            cutoff = datetime.utcnow() - timedelta(days=30)
            db = get_database()
            if db is not None:
                result = db.incidents.delete_many({
                    "status": "resolved",
                    "resolved_at": {"$lt": cutoff}
                })
                st.success(f"Deleted {result.deleted_count} old incidents")
    
    st.markdown("---")
    
    st.subheader("About")
    st.write("**Uptime Monitor** - Enterprise-grade uptime monitoring solution")
    st.write("Features:")
    st.write("- HTTP/HTTPS, Ping, Port, Keyword monitoring")
    st.write("- SSL certificate and domain expiry monitoring")
    st.write("- Configurable check intervals (30s - 1h)")
    st.write("- Multiple notification channels")
    st.write("- Public status pages")
    st.write("- Incident tracking and history")

def main():
    init_session_state()
    restore_session_from_token()
    
    if not is_authenticated():
        render_login_page()
        return
    
    init_scheduler()
    
    render_sidebar()
    
    page = st.session_state.page
    
    if page == "dashboard":
        render_dashboard()
    elif page == "monitors":
        render_monitors()
    elif page == "add_monitor":
        render_add_monitor()
    elif page == "edit_monitor":
        render_edit_monitor()
    elif page == "incidents":
        render_incidents()
    elif page == "status_pages":
        render_status_pages()
    elif page == "view_status_page":
        render_view_status_page()
    elif page == "notifications":
        render_notifications()
    elif page == "settings":
        render_settings()

if __name__ == "__main__":
    main()
