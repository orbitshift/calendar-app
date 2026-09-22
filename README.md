# Team Calendar App

This is a simple calendar and task management web app for a small team of system administrators. It supports user registration, login, and task creation with due dates and reminders.

## Features

- User login and registration
- Task creation with title, description, date, reminder, and priority
- Per-user task list
- SQLite database for persistent storage
- Runs on Windows and is easy to move to a Raspberry Pi 5

## Recommended team setup

This project is designed to keep the application code in GitHub while keeping the live task database in one shared location.

- GitHub stores the app code and templates
- a shared SQLite database stores the live task data
- each Pi or workstation points to the same database path via the `CALENDAR_DB_PATH` environment variable

This is the safer workflow for a shared team calendar because the database is not treated as a regular code file that gets overwritten by local copies.

## Prerequisites

- Python 3.12 or newer
- Windows 10/11 or a Raspberry Pi OS environment

## Run on Windows

1. Open a terminal in this folder.
2. Install dependencies:
   ```powershell
   python -m pip install -r requirements.txt
   ```
3. Start the app with a shared database path:
   ```powershell
   $env:CALENDAR_DB_PATH = "C:\\calendar-data\\calendar.db"
   python app.py
   ```
4. Open http://localhost:5000 in a browser.

## Run on Raspberry Pi 5

1. Install Python 3 on the Raspberry Pi.
2. Clone or copy this project to the Pi.
3. Create a shared database directory:
   ```bash
   mkdir -p /home/pi/calendar-data
   ```
4. Install dependencies:
   ```bash
   python3 -m pip install -r requirements.txt
   ```
5. Start the app with the shared database path:
   ```bash
   export CALENDAR_DB_PATH=/home/pi/calendar-data/calendar.db
   python3 app.py
   ```
6. Access the app from the local network using the Pi IP address and port 5000.

## Persistent environment setup on the Pi

To keep the shared database path active for future sessions:

```bash
echo 'export CALENDAR_DB_PATH=/home/pi/calendar-data/calendar.db' >> ~/.bashrc
source ~/.bashrc
```

## Notes

- The app will create the parent folder for the database path automatically if needed.
- The code is meant to live in GitHub; the live user data should live in a shared SQLite file instead of a local repo copy.
- For a production deployment, use a WSGI server like Gunicorn and serve behind nginx or a reverse proxy.
- For a real team environment, the next step would be shared calendars, recurring tasks, admin roles, and notifications.
