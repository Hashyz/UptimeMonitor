# Uptime Monitor

A full-featured uptime monitoring application similar to UptimeRobot, built with Streamlit and MongoDB. Monitor your websites, APIs, and services with enterprise-level features.

## Features

- **Multiple Monitor Types**
  - HTTP/HTTPS - Website and API endpoint monitoring
  - Keyword - Check for presence/absence of text in response
  - Ping - ICMP ping monitoring for hosts
  - Port - TCP port availability monitoring
  - SSL Certificate - SSL certificate expiry monitoring
  - Domain Expiry - Domain registration expiry monitoring

- **Flexible Check Intervals** - From 30 seconds to 1 hour

- **Real-time Dashboard** - Overview of all monitors with uptime statistics

- **Incident Management** - Automatic incident creation and resolution tracking

- **Public Status Pages** - Create shareable status pages for your services

- **Multi-Channel Notifications**
  - Email (SMTP)
  - Webhook
  - Slack
  - Telegram

- **User Authentication** - Secure login with bcrypt password hashing

- **Unlimited Monitors** - No restrictions on the number of monitors

## Tech Stack

- **Frontend**: Streamlit
- **Database**: MongoDB
- **Scheduler**: APScheduler
- **Authentication**: bcrypt

## Getting Started

### Prerequisites

- Python 3.11+
- MongoDB database

### Environment Variables

Set the following environment variable:

```
MONGODB_URI=your_mongodb_connection_string
```

### Installation

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the application:
   ```bash
   streamlit run main.py --server.port 5000
   ```

## Usage

1. **Register** - Create an account with your email and password
2. **Add Monitors** - Set up monitoring for your websites and services
3. **Configure Notifications** - Set up alerts for when services go down
4. **Create Status Pages** - Share your service status publicly
5. **Track Incidents** - Monitor and resolve downtime events

## Screenshots

The application features a clean, dark-themed interface with:
- Dashboard with monitor statistics
- Monitor management interface
- Incident tracking
- Status page builder
- Notification configuration

## License

MIT License

---

<details>
<summary>.</summary>

Developed by [Hashyz](https://github.com/Hashyz)

</details>
