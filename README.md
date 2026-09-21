# Team Calendar App

This is a simple calendar and task management web app for a small team of system administrators. It supports user registration, login, and task creation with due dates and reminders.

## Features

- User login and registration
- Task creation with title, description, date, reminder, and priority
- Per-user task list
- SQLite database for persistent storage
- Runs on Windows and is easy to move to a Raspberry Pi 5

## Prerequisites

- Python 3.12 or newer
- Windows 10/11 or a Raspberry Pi OS environment

## Run on Windows

1. Open a terminal in this folder.
2. Install dependencies:
   ```powershell
   python -m pip install -r requirements.txt
   ```
3. Start the app:
   ```powershell
   python app.py
   ```
4. Open http://localhost:5000 in a browser.

## Run on Raspberry Pi 5

1. Install Python 3 on the Raspberry Pi.
2. Clone or copy this project to the Pi.
3. Install dependencies:
   ```bash
   python3 -m pip install -r requirements.txt
   ```
4. Start the app:
   ```bash
   python3 app.py
   ```
5. Access the app from the local network using the Pi IP address and port 5000.

## Notes

- The app stores data in a local SQLite file named `calendar.db`.
- For a production deployment, use a WSGI server like Gunicorn and serve behind nginx or a reverse proxy.
- For a real team environment, the next step would be shared calendars, recurring tasks, admin roles, and notifications.
