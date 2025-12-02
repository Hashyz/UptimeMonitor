import threading
import time
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from models import Monitor
from monitoring import run_check

scheduler = None
scheduler_lock = threading.Lock()

def get_scheduler():
    global scheduler
    with scheduler_lock:
        if scheduler is None:
            scheduler = BackgroundScheduler()
            scheduler.start()
    return scheduler

def schedule_monitor_check(monitor_id, interval_seconds):
    sched = get_scheduler()
    job_id = f"monitor_{monitor_id}"
    
    existing_job = sched.get_job(job_id)
    if existing_job:
        sched.remove_job(job_id)
    
    def check_job():
        try:
            monitor = Monitor.get_by_id(monitor_id)
            if monitor and not monitor.get("is_paused", False):
                run_check(monitor)
        except Exception as e:
            print(f"Error checking monitor {monitor_id}: {e}")
    
    sched.add_job(
        check_job,
        trigger=IntervalTrigger(seconds=interval_seconds),
        id=job_id,
        replace_existing=True,
        max_instances=1
    )
    
    return True

def remove_monitor_job(monitor_id):
    sched = get_scheduler()
    job_id = f"monitor_{monitor_id}"
    
    try:
        sched.remove_job(job_id)
        return True
    except:
        return False

def sync_all_monitors():
    sched = get_scheduler()
    
    for job in sched.get_jobs():
        if job.id.startswith("monitor_"):
            sched.remove_job(job.id)
    
    monitors = Monitor.get_active_monitors()
    
    for monitor in monitors:
        schedule_monitor_check(
            str(monitor["_id"]),
            monitor.get("interval", 300)
        )
    
    return len(monitors)

def get_scheduler_status():
    sched = get_scheduler()
    jobs = sched.get_jobs()
    
    return {
        "running": sched.running,
        "job_count": len(jobs),
        "jobs": [
            {
                "id": job.id,
                "next_run": job.next_run_time.isoformat() if job.next_run_time else None
            }
            for job in jobs
        ]
    }

def shutdown_scheduler():
    global scheduler
    with scheduler_lock:
        if scheduler:
            scheduler.shutdown(wait=False)
            scheduler = None
