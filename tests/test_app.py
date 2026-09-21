from datetime import date

import pytest

import app as app_module


@pytest.fixture
def client(tmp_path):
    db_path = tmp_path / 'calendar.db'
    app_module.DB_PATH = db_path
    app_module.init_db()
    app_module.ensure_default_admin()
    app_module.app.config['TESTING'] = True
    app_module.app.config['WTF_CSRF_ENABLED'] = False
    with app_module.app.test_client() as client:
        yield client


def test_home_redirects_to_login(client):
    response = client.get('/')
    assert response.status_code == 302
    assert '/login' in response.headers['Location']


def test_default_admin_login(client):
    response = client.post('/login', data={
        'username': 'admin',
        'password': 'Admin123!'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b'Login successful.' in response.data


def test_dashboard_month_view_renders(client):
    client.post('/login', data={'username': 'admin', 'password': 'Admin123!'}, follow_redirects=True)
    client.post('/tasks', data={
        'title': 'Patch firewall',
        'description': 'Update perimeter rules',
        'date': '2026-09-30',
        'reminder': '2026-09-29T09:00',
        'priority': 'High'
    }, follow_redirects=True)

    response = client.get('/dashboard?month=2026-09')
    assert response.status_code == 200
    assert b'September 2026' in response.data
    assert b'Patch firewall' in response.data


def test_dashboard_weekday_order_matches_month_grid(client):
    client.post('/login', data={'username': 'admin', 'password': 'Admin123!'}, follow_redirects=True)

    response = client.get('/dashboard?month=2026-09')
    assert response.status_code == 200
    assert response.data.index(b'Sun') < response.data.index(b'Mon')
    assert response.data.index(b'Sat') > response.data.index(b'Fri')


def test_build_forecast_groups_aligns_to_calendar_week():
    weather_forecast = [
        {'date_key': '2026-09-10', 'weekday': 'Thu', 'is_daytime': True, 'shortForecast': 'Cloudy', 'temperature': 72, 'temperatureUnit': 'F'},
        {'date_key': '2026-09-10', 'weekday': 'Thu', 'is_daytime': False, 'shortForecast': 'Clear', 'temperature': 60, 'temperatureUnit': 'F'},
        {'date_key': '2026-09-11', 'weekday': 'Fri', 'is_daytime': True, 'shortForecast': 'Sunny', 'temperature': 74, 'temperatureUnit': 'F'},
        {'date_key': '2026-09-11', 'weekday': 'Fri', 'is_daytime': False, 'shortForecast': 'Mostly clear', 'temperature': 62, 'temperatureUnit': 'F'},
        {'date_key': '2026-09-06', 'weekday': 'Sun', 'is_daytime': True, 'shortForecast': 'Rain', 'temperature': 68, 'temperatureUnit': 'F'},
        {'date_key': '2026-09-06', 'weekday': 'Sun', 'is_daytime': False, 'shortForecast': 'Showers', 'temperature': 57, 'temperatureUnit': 'F'},
        {'date_key': '2026-09-07', 'weekday': 'Mon', 'is_daytime': True, 'shortForecast': 'Cloudy', 'temperature': 70, 'temperatureUnit': 'F'},
        {'date_key': '2026-09-07', 'weekday': 'Mon', 'is_daytime': False, 'shortForecast': 'Partly cloudy', 'temperature': 58, 'temperatureUnit': 'F'},
        {'date_key': '2026-09-08', 'weekday': 'Tue', 'is_daytime': True, 'shortForecast': 'Sunny', 'temperature': 76, 'temperatureUnit': 'F'},
        {'date_key': '2026-09-08', 'weekday': 'Tue', 'is_daytime': False, 'shortForecast': 'Clear', 'temperature': 63, 'temperatureUnit': 'F'},
        {'date_key': '2026-09-09', 'weekday': 'Wed', 'is_daytime': True, 'shortForecast': 'Sunny', 'temperature': 80, 'temperatureUnit': 'F'},
        {'date_key': '2026-09-09', 'weekday': 'Wed', 'is_daytime': False, 'shortForecast': 'Clear', 'temperature': 65, 'temperatureUnit': 'F'},
    ]
    week_dates = [
        date(2026, 9, 6), date(2026, 9, 7), date(2026, 9, 8),
        date(2026, 9, 9), date(2026, 9, 10), date(2026, 9, 11), date(2026, 9, 12),
    ]

    groups = app_module.build_forecast_groups(weather_forecast, week_dates)

    assert [group['label'] for group in groups[:7]] == ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
    assert len(groups) == 7
    assert groups[0]['day_period'] is not None
    assert groups[0]['night_period'] is not None


def test_dashboard_shows_weather_forecast_strip(client):
    client.post('/login', data={'username': 'admin', 'password': 'Admin123!'}, follow_redirects=True)

    response = client.get('/dashboard?month=2026-09')
    assert response.status_code == 200
    assert b'weather-strip' in response.data
    assert b'23337' in response.data
    assert b'Thi' not in response.data
    assert b'Ton' not in response.data


def test_completed_tasks_show_complete_badge_on_calendar(client):
    client.post('/login', data={'username': 'admin', 'password': 'Admin123!'}, follow_redirects=True)
    client.post('/tasks', data={
        'title': 'Patch firewall',
        'date': '2026-09-30',
        'priority': 'High',
        'subtasks': '✔ Check firewall rules\n✔ Confirm cutover window'
    }, follow_redirects=True)

    response = client.get('/dashboard?month=2026-09')
    assert response.status_code == 200
    assert b'Complete' in response.data
    assert b'task-complete' in response.data


def test_task_can_be_dragged_to_a_new_day(client):
    client.post('/login', data={'username': 'admin', 'password': 'Admin123!'}, follow_redirects=True)
    client.post('/tasks', data={
        'title': 'Patch firewall',
        'date': '2026-09-30',
        'priority': 'High'
    }, follow_redirects=True)

    response = client.post('/tasks/1/move', data={'date': '2026-09-15'})
    assert response.status_code == 200
    dashboard = client.get('/dashboard?month=2026-09')
    assert b'2026-09-15' in dashboard.data


def test_calendar_modal_and_task_details(client):
    client.post('/login', data={'username': 'admin', 'password': 'Admin123!'}, follow_redirects=True)
    client.post('/tasks', data={
        'title': 'Patch firewall',
        'description': 'Update perimeter rules',
        'date': '2026-09-30',
        'reminder': '2026-09-29T09:00',
        'priority': 'High',
        'notes': 'Verify failover',
        'subtasks': 'Check firewall rules\nConfirm cutover window'
    }, follow_redirects=True)

    response = client.get('/dashboard?month=2026-09')
    assert response.status_code == 200
    assert b'calendar-modal' in response.data
    assert b'Add Task' in response.data
    assert b'Check firewall rules' in response.data

    detail_response = client.get('/tasks/1/details')
    assert detail_response.status_code == 200
    assert b'Check firewall rules' in detail_response.data

    update_response = client.post('/tasks/1/update', data={
        'title': 'Patch firewall',
        'description': 'Update perimeter rules',
        'date': '2026-09-30',
        'reminder': '2026-09-29T09:00',
        'priority': 'High',
        'notes': 'Verified failover',
        'subtasks': 'Check firewall rules\nConfirm cutover window\nNotify team'
    }, follow_redirects=True)
    assert update_response.status_code == 200
    assert b'Verified failover' in update_response.data

    delete_response = client.post('/tasks/1/delete', follow_redirects=True)
    assert delete_response.status_code == 200
    assert b'Task deleted.' in delete_response.data
