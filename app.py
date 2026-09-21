import calendar
import json
import os
import sqlite3
from datetime import date, datetime
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

from flask import Flask, flash, redirect, render_template, request, url_for
from flask_login import LoginManager, UserMixin, current_user, login_required, login_user, logout_user
from flask_wtf import FlaskForm
from werkzeug.security import check_password_hash, generate_password_hash
from wtforms import DateField, DateTimeLocalField, PasswordField, SelectField, StringField, TextAreaField
from wtforms.validators import DataRequired, Length

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev-secret-key-change-me'
app.config['WTF_CSRF_ENABLED'] = False

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = Path(os.environ.get('CALENDAR_DB_PATH', BASE_DIR / 'calendar.db'))
WEATHER_ZIP_CODE = '23337'
WEATHER_LATITUDE = 36.8354
WEATHER_LONGITUDE = -76.0433

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


class User(UserMixin):
    def __init__(self, id, username, password_hash):
        self.id = str(id)
        self.username = username
        self.password_hash = password_hash


class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=50)])
    password = PasswordField('Password', validators=[DataRequired()])


class RegisterForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=50)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])


class TaskForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired(), Length(min=1, max=100)])
    description = TextAreaField('Description')
    due_date = DateField('Due date', format='%Y-%m-%d')
    reminder = DateTimeLocalField('Reminder', format='%Y-%m-%dT%H:%M')
    priority = SelectField('Priority', choices=['Low', 'Medium', 'High'], default='Medium')


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as conn:
        conn.execute(
            '''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL
            )
            '''
        )
        conn.execute(
            '''
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                due_date TEXT,
                reminder TEXT,
                priority TEXT DEFAULT 'Medium',
                notes TEXT,
                subtasks TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
            '''
        )


def migrate_db_schema():
    with get_db() as conn:
        columns = [row['name'] for row in conn.execute('PRAGMA table_info(tasks)').fetchall()]
        if 'notes' not in columns:
            conn.execute('ALTER TABLE tasks ADD COLUMN notes TEXT')
        if 'subtasks' not in columns:
            conn.execute('ALTER TABLE tasks ADD COLUMN subtasks TEXT')


def ensure_default_admin():
    with get_db() as conn:
        admin_exists = conn.execute(
            'SELECT 1 FROM users WHERE username = ?',
            ('admin',),
        ).fetchone()
        if not admin_exists:
            conn.execute(
                'INSERT INTO users (username, password_hash) VALUES (?, ?)',
                ('admin', generate_password_hash('Admin123!')),
            )


# initialize the app database on the active path used by the process
init_db()
migrate_db_schema()
ensure_default_admin()


@login_manager.user_loader
def load_user(user_id):
    with get_db() as conn:
        row = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    if row is None:
        return None
    return User(row['id'], row['username'], row['password_hash'])


@app.route('/')
def home():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


def shift_month(current_date, offset):
    month_index = (current_date.year * 12) + (current_date.month - 1) + offset
    year, month = divmod(month_index, 12)
    return date(year, month + 1, 1)


def task_is_complete(task):
    subtasks = task.get('subtasks') or ''
    values = [line.strip() for line in subtasks.splitlines() if line.strip()]
    if not values:
        return False
    return all(
        line.startswith('[x]') or line.startswith('[X]') or line.startswith('✔') or line.startswith('✓')
        for line in values
    )


def get_weather_forecast(zip_code='23337', latitude=WEATHER_LATITUDE, longitude=WEATHER_LONGITUDE):
    point_url = f'https://api.weather.gov/points/{latitude},{longitude}'
    point_request = Request(
        point_url,
        headers={
            'User-Agent': 'calendar-app/1.0 (dev@example.com)',
            'Accept': 'application/geo+json',
        },
    )
    try:
        with urlopen(point_request, timeout=10) as point_response:
            point_data = json.loads(point_response.read().decode('utf-8'))
    except (URLError, ValueError, TimeoutError):
        return []

    forecast_url = point_data.get('properties', {}).get('forecast')
    if not forecast_url:
        return []

    forecast_request = Request(
        forecast_url,
        headers={
            'User-Agent': 'calendar-app/1.0 (dev@example.com)',
            'Accept': 'application/geo+json',
        },
    )
    try:
        with urlopen(forecast_request, timeout=10) as forecast_response:
            payload = json.loads(forecast_response.read().decode('utf-8'))
    except (URLError, ValueError, TimeoutError):
        return []

    periods = payload.get('properties', {}).get('periods', [])
    forecast = []
    for period in periods:
        start_time = period.get('startTime')
        weekday_label = 'Today'
        date_key = None
        if start_time:
            try:
                parsed = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                weekday_label = parsed.strftime('%a')
                date_key = parsed.date().isoformat()
            except ValueError:
                weekday_label = period.get('name', 'Today')

        forecast.append({
            'name': period.get('name', 'Today'),
            'weekday': weekday_label,
            'date_key': date_key,
            'temperature': period.get('temperature'),
            'unit': period.get('temperatureUnit', 'F'),
            'shortForecast': period.get('shortForecast', 'Forecast unavailable'),
            'icon': period.get('icon', ''),
            'is_daytime': period.get('isDaytime', True),
        })
    return forecast


def get_weather_theme(forecast):
    if not forecast:
        return 'neutral'

    value = (forecast[0].get('shortForecast') or '').lower()
    if any(token in value for token in ['thunderstorm', 'storm', 'showers', 'rain', 'drizzle', 'shower']):
        return 'stormy'
    if any(token in value for token in ['cloudy', 'overcast', 'clouds']):
        return 'cloudy'
    if any(token in value for token in ['sunny', 'clear', 'fair']):
        return 'sunny'
    return 'neutral'


def build_forecast_groups(weather_forecast, week_dates=None):
    grouped = {}
    ordered_keys = []
    for item in weather_forecast:
        date_key = item.get('date_key') or (item.get('weekday') or 'Today')
        if date_key not in grouped:
            grouped[date_key] = {
                'key': date_key,
                'label': (item.get('weekday') or 'Today')[:3],
                'day_period': None,
                'night_period': None,
            }
            ordered_keys.append(date_key)

        slot = 'day' if item.get('is_daytime', True) else 'night'
        if slot == 'day':
            grouped[date_key]['day_period'] = item
        else:
            grouped[date_key]['night_period'] = item

    if not ordered_keys:
        return []

    actual_dates = [date.fromisoformat(key) for key in ordered_keys if key]
    if actual_dates:
        calendar_slots = [None] * 7
        for date_key in ordered_keys:
            if not date_key:
                continue
            try:
                day = date.fromisoformat(date_key)
            except ValueError:
                continue
            slot_index = (day.weekday() + 1) % 7
            calendar_slots[slot_index] = grouped[date_key]
        for index in range(7):
            if calendar_slots[index] is None:
                calendar_slots[index] = {
                    'key': None,
                    'label': ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'][index],
                    'day_period': None,
                    'night_period': None,
                }
        return calendar_slots

    ordered = [grouped[key] for key in ordered_keys]
    return ordered[:7]


@app.route('/dashboard')
@login_required
def dashboard():
    month_value = request.args.get('month')
    if month_value:
        try:
            display_month = date.fromisoformat(f"{month_value}-01")
        except ValueError:
            display_month = date.today().replace(day=1)
    else:
        display_month = date.today().replace(day=1)

    with get_db() as conn:
        rows = conn.execute(
            '''
            SELECT * FROM tasks
            WHERE user_id = ?
            ORDER BY due_date IS NULL, due_date ASC, reminder IS NULL, reminder ASC
            ''',
            (current_user.id,),
        ).fetchall()

    tasks = [dict(row) for row in rows]
    for task in tasks:
        task['is_complete'] = task_is_complete(task)

    tasks_by_date = {}
    for task in tasks:
        if task.get('due_date'):
            tasks_by_date.setdefault(task['due_date'], []).append(task)

    month_days = calendar.Calendar(firstweekday=6).monthdatescalendar(display_month.year, display_month.month)
    prev_month = shift_month(display_month, -1)
    next_month = shift_month(display_month, 1)
    today = date.today()

    weather_forecast = get_weather_forecast(WEATHER_ZIP_CODE, WEATHER_LATITUDE, WEATHER_LONGITUDE)
    weather_theme = get_weather_theme(weather_forecast)

    calendar_week = month_days[0] if month_days else []
    forecast_groups = build_forecast_groups(weather_forecast, calendar_week)

    return render_template(
        'dashboard.html',
        tasks=tasks,
        tasks_by_date=tasks_by_date,
        month_days=month_days,
        display_month=display_month,
        prev_month=prev_month,
        next_month=next_month,
        weather_forecast=weather_forecast,
        forecast_groups=forecast_groups,
        weather_zip_code=WEATHER_ZIP_CODE,
        today=today,
        weather_theme=weather_theme,
    )


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if request.method == 'POST' and form.validate():
        username = form.username.data.strip()
        password = form.password.data
        with get_db() as conn:
            row = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        if row and check_password_hash(row['password_hash'], password):
            user = User(row['id'], row['username'], row['password_hash'])
            login_user(user)
            flash('Login successful.')
            return redirect(url_for('dashboard'))
        flash('Invalid username or password.')
    return render_template('login.html', form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.')
    return redirect(url_for('login'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if request.method == 'POST' and form.validate():
        username = form.username.data.strip()
        password = form.password.data
        with get_db() as conn:
            existing = conn.execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone()
            if existing:
                flash('Username already exists.')
                return render_template('register.html', form=form)
            conn.execute(
                'INSERT INTO users (username, password_hash) VALUES (?, ?)',
                (username, generate_password_hash(password)),
            )
        flash('Registration successful. Please log in.')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)


@app.route('/tasks', methods=['POST'])
@login_required
def add_task():
    title = request.form.get('title', '').strip()
    description = request.form.get('description', '').strip()
    due_date = request.form.get('date') or None
    reminder = request.form.get('reminder') or None
    priority = request.form.get('priority', 'Medium')
    notes = request.form.get('notes', '').strip()
    subtasks = request.form.get('subtasks', '').strip()

    if not title:
        flash('Task title is required.')
        return redirect(url_for('dashboard'))

    with get_db() as conn:
        conn.execute(
            '''
            INSERT INTO tasks (user_id, title, description, due_date, reminder, priority, notes, subtasks, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            ''',
            (current_user.id, title, description, due_date, reminder, priority, notes, subtasks),
        )
    flash('Task added successfully.')
    return redirect(url_for('dashboard'))


@app.route('/tasks/<int:task_id>/details')
@login_required
def task_details(task_id):
    with get_db() as conn:
        row = conn.execute(
            'SELECT * FROM tasks WHERE id = ? AND user_id = ?',
            (task_id, current_user.id),
        ).fetchone()
    if row is None:
        return {'error': 'Task not found'}, 404
    return dict(row)


@app.route('/tasks/<int:task_id>/update', methods=['POST'])
@login_required
def update_task(task_id):
    with get_db() as conn:
        existing = conn.execute(
            'SELECT * FROM tasks WHERE id = ? AND user_id = ?',
            (task_id, current_user.id),
        ).fetchone()
        if existing is None:
            flash('Task not found.')
            return redirect(url_for('dashboard'))

        title = request.form.get('title', existing['title']).strip()
        description = request.form.get('description', existing['description'] or '').strip()
        due_date = request.form.get('date') or existing['due_date']
        reminder = request.form.get('reminder') or existing['reminder']
        priority = request.form.get('priority', existing['priority'])
        notes = request.form.get('notes', existing['notes'] or '').strip()
        subtasks = request.form.get('subtasks', existing['subtasks'] or '').strip()

        conn.execute(
            '''
            UPDATE tasks
            SET title = ?, description = ?, due_date = ?, reminder = ?, priority = ?, notes = ?, subtasks = ?
            WHERE id = ? AND user_id = ?
            ''',
            (title, description, due_date, reminder, priority, notes, subtasks, task_id, current_user.id),
        )

    flash('Task updated successfully.')
    return redirect(url_for('dashboard'))


@app.route('/tasks/<int:task_id>/move', methods=['POST'])
@login_required
def move_task(task_id):
    new_date = request.form.get('date', '').strip()
    if not new_date:
        return {'error': 'A target date is required'}, 400

    with get_db() as conn:
        task = conn.execute(
            'SELECT id FROM tasks WHERE id = ? AND user_id = ?',
            (task_id, current_user.id),
        ).fetchone()
        if task is None:
            return {'error': 'Task not found'}, 404

        conn.execute(
            'UPDATE tasks SET due_date = ? WHERE id = ? AND user_id = ?',
            (new_date, task_id, current_user.id),
        )

    return {'status': 'ok', 'date': new_date}


@app.route('/tasks/<int:task_id>/delete', methods=['POST'])
@login_required
def delete_task(task_id):
    with get_db() as conn:
        deleted = conn.execute(
            'DELETE FROM tasks WHERE id = ? AND user_id = ?',
            (task_id, current_user.id),
        )
    if deleted.rowcount:
        flash('Task deleted.')
    else:
        flash('Task not found.')
    return redirect(url_for('dashboard'))


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
