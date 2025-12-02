# Uptime Monitor - Enterprise-Grade Monitoring Solution

## Overview
A full-featured uptime monitoring application similar to UptimeRobot, built with Streamlit and MongoDB. This application provides comprehensive website and service monitoring with enterprise-level features.

## Features
- **Multiple Monitor Types**: HTTP/HTTPS, Ping, Port, Keyword, SSL Certificate, Domain Expiry
- **Configurable Intervals**: From 30 seconds to 1 hour check intervals
- **Real-time Dashboard**: Overview of all monitors with uptime statistics
- **Incident Tracking**: Automatic incident creation and resolution tracking
- **Status Pages**: Create public status pages for your services
- **Notifications**: Email, Webhook, Slack, and Telegram integrations
- **Background Scheduler**: Automated checks using APScheduler

## Architecture
- **Frontend**: Streamlit (Python)
- **Database**: MongoDB Atlas
- **Scheduler**: APScheduler for background monitoring tasks
- **Notifications**: Pluggable notification system

## File Structure
- `main.py` - Main Streamlit application
- `config.py` - Configuration constants
- `database.py` - MongoDB connection and collections
- `models.py` - Data models (Monitor, CheckResult, Incident, etc.)
- `monitoring.py` - Monitor check implementations
- `scheduler.py` - Background job scheduler
- `notifications_service.py` - Notification channel implementations

## MongoDB Collections
- `monitors` - Monitor configurations
- `check_results` - Check history and results
- `incidents` - Incident records
- `notifications` - Notification channel configurations
- `status_pages` - Public status page configurations
- `settings` - Application settings

## Running the Application
The application runs on port 5000 using Streamlit.

## Environment Variables
- `MONGODB_URI` - MongoDB connection string (default configured)

## Recent Changes
- December 2, 2025: Initial implementation with full monitoring suite
