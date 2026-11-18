"""Single-owner TODO web application; shares Chronos' SQLite table."""
import hashlib
import hmac
import os
import re
import sqlite3
import time
from contextlib import contextmanager
from datetime import date, timedelta
from functools import wraps
from pathlib import Path

from flask import Flask, abort, jsonify, request, session


def create_app(config=None):
    app = Flask(__name__, static_folder='static', static_url_path='/static')
    app.config.update(SECRET_KEY=os.environ.get('TODO_SESSION_SECRET'),
        OWNER_KEY=os.environ.get('TODO_OWNER_KEY'), VIEWER_KEY=os.environ.get('TODO_VIEWER_KEY'),
        DATABASE=os.environ.get('TODO_DATABASE'), PUBLIC_ORIGIN='https://task.supurazako.com',
        SESSION_COOKIE_SECURE=True, SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Strict',
        PERMANENT_SESSION_LIFETIME=timedelta(days=7), MAX_CONTENT_LENGTH=8192)
    if config:
        app.config.update(config)
    for name in ('SECRET_KEY', 'OWNER_KEY', 'VIEWER_KEY', 'DATABASE'):
        if not app.config.get(name):
            raise ValueError(f'{name} is required')
    if app.config['OWNER_KEY'] == app.config['VIEWER_KEY']:
        raise ValueError('Owner and viewer keys must differ')
    # Key changes invalidate all previous sessions without storing the actual keys in cookies.
    generation = hmac.new(str(app.config['SECRET_KEY']).encode(),
        (app.config['OWNER_KEY'] + '\0' + app.config['VIEWER_KEY']).encode(), hashlib.sha256).hexdigest()
    failures = []

    @contextmanager
    def db():
        con = sqlite3.connect(app.config['DATABASE'], timeout=15)
        con.row_factory = sqlite3.Row
        try:
            with con:
                yield con
        finally:
            con.close()

    # Do not create an empty replacement if the configured shared store is missing.
    if not Path(app.config['DATABASE']).is_file():
        raise ValueError('Existing TODO database is required')
    with db() as con:
        con.execute('SELECT todo_id, task, status, created_at, completed_at FROM todo_items LIMIT 0')
        con.execute('''CREATE TABLE IF NOT EXISTS finance_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kind TEXT NOT NULL CHECK(kind IN ('income','expense')),
            title TEXT NOT NULL,
            amount INTEGER NOT NULL CHECK(amount > 0 AND amount <= 1000000000),
            occurred_on TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )''')
        con.execute('CREATE INDEX IF NOT EXISTS finance_by_date ON finance_entries(occurred_on, id)')

    @app.before_request
    def guard():
        if request.method not in ('GET', 'HEAD', 'OPTIONS'):
            if request.headers.get('Origin') != app.config['PUBLIC_ORIGIN']:
                abort(403)
            if not request.is_json:
                abort(415)

    @app.after_request
    def headers(response):
        response.headers['Cache-Control'] = 'no-store'
        response.headers['X-Robots-Tag'] = 'noindex, nofollow, noarchive'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'no-referrer'
        response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'"
        response.headers['Strict-Transport-Security'] = 'max-age=31536000'
        return response

    def auth(owner=False):
        def decorate(fn):
            @wraps(fn)
            def wrapped(*args, **kwargs):
                if not owner:
                    return fn(*args, **kwargs)
                if session.get('generation') != generation or session.get('role') not in ('owner', 'viewer'):
                    abort(401)
                if owner and session['role'] != 'owner':
                    abort(403)
                return fn(*args, **kwargs)
            return wrapped
        return decorate

    def body():
        value = request.get_json()
        if not isinstance(value, dict):
            abort(400)
        return value

    def task_text(value):
        if not isinstance(value, str) or not value.strip() or len(value.strip()) > 500:
            abort(400)
        return value.strip()

    @app.get('/')
    def index():
        return app.send_static_file('index.html')

    @app.post('/api/login')
    def login():
        now = time.monotonic()
        failures[:] = [t for t in failures if now - t < 60]
        if len(failures) >= 30:
            abort(429)
        key = body().get('key')
        if not isinstance(key, str) or len(key) > 1024:
            abort(400)
        role = None
        for candidate, field in [('owner', 'OWNER_KEY'), ('viewer', 'VIEWER_KEY')]:
            if hmac.compare_digest(key.encode(), app.config[field].encode()):
                role = candidate
        if not role:
            failures.append(now)
            abort(401)
        session.clear()
        session.update(role=role, generation=generation)
        session.permanent = True
        return jsonify(role=role)

    @app.post('/api/logout')
    def logout():
        session.clear()
        return jsonify(ok=True)

    @app.get('/api/todos')
    @auth()
    def listing():
        with db() as con:
            rows = con.execute("SELECT todo_id AS id, task, status, created_at, completed_at FROM todo_items ORDER BY CASE status WHEN 'open' THEN 0 ELSE 1 END, todo_id").fetchall()
        role = session.get('role') if session.get('generation') == generation else 'viewer'
        return jsonify(role=role or 'viewer', todos=[dict(r) for r in rows])

    @app.post('/api/todos')
    @auth(True)
    def add():
        task = task_text(body().get('task'))
        with db() as con:
            cursor = con.execute('INSERT INTO todo_items(task) VALUES (?)', (task,))
            ident = cursor.lastrowid
        return jsonify(id=ident), 201

    @app.patch('/api/todos/<int:ident>')
    @auth(True)
    def update(ident):
        data = body()
        if not data or set(data) - {'task', 'status'}:
            abort(400)
        values, fields = [], []
        if 'task' in data:
            fields.append('task = ?')
            values.append(task_text(data['task']))
        if 'status' in data:
            if data['status'] not in ('open', 'completed'):
                abort(400)
            fields.extend(['status = ?', "completed_at = CASE WHEN ? = 'completed' THEN COALESCE(completed_at, CURRENT_TIMESTAMP) ELSE NULL END"])
            values.extend([data['status'], data['status']])
        with db() as con:
            cur = con.execute('UPDATE todo_items SET ' + ', '.join(fields) + ' WHERE todo_id = ?', [*values, ident])
            if not cur.rowcount:
                abort(404)
        return jsonify(ok=True)

    @app.delete('/api/todos/<int:ident>')
    @auth(True)
    def delete(ident):
        with db() as con:
            cur = con.execute('DELETE FROM todo_items WHERE todo_id = ?', (ident,))
            if not cur.rowcount:
                abort(404)
        return jsonify(ok=True)

    def finance_values(data):
        if set(data) != {'kind', 'title', 'amount', 'occurred_on'}:
            abort(400)
        kind, amount, occurred = data['kind'], data['amount'], data['occurred_on']
        if kind not in ('income', 'expense'):
            abort(400)
        if type(amount) is not int or not 1 <= amount <= 1_000_000_000:
            abort(400)
        if not isinstance(occurred, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', occurred):
            abort(400)
        try:
            date.fromisoformat(occurred)
        except ValueError:
            abort(400)
        return kind, task_text(data['title']), amount, occurred

    @app.get('/api/finance')
    @auth()
    def finance_list():
        month = request.args.get('month', '')
        if not re.fullmatch(r'\d{4}-(0[1-9]|1[0-2])', month):
            abort(400)
        try:
            date.fromisoformat(month + '-01')
        except ValueError:
            abort(400)
        with db() as con:
            rows = [dict(r) for r in con.execute(
                'SELECT id, kind, title, amount, occurred_on FROM finance_entries '
                'WHERE occurred_on >= ? AND occurred_on <= ? ORDER BY occurred_on DESC, id DESC',
                (month + '-01', month + '-31')).fetchall()]
        income = sum(r['amount'] for r in rows if r['kind'] == 'income')
        expense = sum(r['amount'] for r in rows if r['kind'] == 'expense')
        return jsonify(entries=rows, month=month, currency='JPY',
                       summary={'income': income, 'expense': expense, 'net': income - expense})

    @app.post('/api/finance')
    @auth(True)
    def finance_add():
        values = finance_values(body())
        with db() as con:
            cur = con.execute('INSERT INTO finance_entries(kind,title,amount,occurred_on) VALUES (?,?,?,?)', values)
            ident = cur.lastrowid
        return jsonify(id=ident), 201

    @app.put('/api/finance/<int:ident>')
    @auth(True)
    def finance_update(ident):
        values = finance_values(body())
        with db() as con:
            cur = con.execute('UPDATE finance_entries SET kind=?, title=?, amount=?, occurred_on=? WHERE id=?', (*values, ident))
            if not cur.rowcount:
                abort(404)
        return jsonify(ok=True)

    @app.delete('/api/finance/<int:ident>')
    @auth(True)
    def finance_delete(ident):
        with db() as con:
            cur = con.execute('DELETE FROM finance_entries WHERE id=?', (ident,))
            if not cur.rowcount:
                abort(404)
        return jsonify(ok=True)

    return app


if __name__ == '__main__':
    from waitress import serve
    serve(create_app(), host='127.0.0.1', port=int(os.environ.get('TODO_PORT', '8786')), threads=4)
