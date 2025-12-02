# Uptime Monitor - Enterprise-Grade Monitoring Solution

## Overview
A full-featured uptime monitoring application similar to UptimeRobot, built with Streamlit and MongoDB. This application provides comprehensive website and service monitoring with enterprise-level features. You have full access and control over all features with no restrictions.

## Features
- **Multiple Monitor Types**: HTTP/HTTPS, Ping, Port, Keyword, SSL Certificate, Domain Expiry
- **Configurable Intervals**: From 30 seconds to 1 hour check intervals
- **Real-time Dashboard**: Overview of all monitors with uptime statistics
- **Incident Tracking**: Automatic incident creation and resolution tracking
- **Status Pages**: Create public status pages for your services
- **Notifications**: Email, Webhook, Slack, and Telegram integrations
- **Background Scheduler**: Automated checks using APScheduler
- **Unlimited Monitors**: No restrictions on number of monitors
- **Full API Access**: All features available through the UI

## Architecture
- **Frontend**: Streamlit (Python)
- **Database**: MongoDB Atlas
- **Scheduler**: APScheduler for background monitoring tasks
- **Notifications**: Pluggable notification system

## File Structure
- `main.py` - Main Streamlit application with all pages
- `config.py` - Configuration constants and monitor types
- `database.py` - MongoDB connection and collection management
- `models.py` - Data models (Monitor, CheckResult, Incident, Notification, StatusPage)
- `monitoring.py` - Monitor check implementations (HTTP, Ping, Port, SSL, Domain)
- `scheduler.py` - Background job scheduler for automated checks
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
- `MONGODB_URI` - MongoDB connection string (required, stored as secret)

## Monitor Types Supported
1. **HTTP/HTTPS** - Website and API endpoint monitoring
2. **Keyword** - Check for presence/absence of text in response
3. **Ping** - ICMP ping monitoring for hosts
4. **Port** - TCP port availability monitoring
5. **SSL Certificate** - SSL certificate expiry monitoring
6. **Domain Expiry** - Domain registration expiry monitoring

## Notification Channels
1. **Email** - SMTP-based email notifications
2. **Webhook** - Custom HTTP webhook notifications
3. **Slack** - Slack incoming webhook notifications
4. **Telegram** - Telegram bot notifications

## Recent Changes
- December 2, 2025: Initial implementation with full monitoring suite
- December 2, 2025: Moved MongoDB URI to environment variables for security
