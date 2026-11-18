import sqlite3
import pytest
from app import create_app

ORIGIN = {'Origin': 'https://task.supurazako.com'}

@pytest.fixture
def settings(tmp_path):
    path = tmp_path / 'todo.db'
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE todo_items(todo_id INTEGER PRIMARY KEY AUTOINCREMENT, task TEXT NOT NULL, status TEXT DEFAULT 'open' CHECK(status IN ('open','completed')), created_at TEXT DEFAULT CURRENT_TIMESTAMP, completed_at TEXT)")
    return dict(TESTING=True, SECRET_KEY='test-session', OWNER_KEY='owner-key', VIEWER_KEY='viewer-key', DATABASE=str(path))

@pytest.fixture
def client(settings):
    return create_app(settings).test_client()

def login(client, key='owner-key'):
    return client.post('/api/login', json={'key':key}, headers=ORIGIN)

def test_anonymous(client):
    assert client.get('/').status_code == 200
    assert client.get('/api/todos').status_code == 401
    assert client.post('/api/todos', json={'task':'x'}, headers=ORIGIN).status_code == 401

def test_owner_crud_and_persistence(client, settings):
    assert login(client).status_code == 200
    added = client.post('/api/todos', json={'task':'<script>alert(1)</script>'}, headers=ORIGIN)
    assert added.status_code == 201
    ident = added.json['id']
    assert client.patch(f'/api/todos/{ident}', json={'task':'changed','status':'completed'}, headers=ORIGIN).status_code == 200
    fresh = create_app(settings).test_client(); login(fresh)
    row = fresh.get('/api/todos').json['todos'][0]
    assert row['task'] == 'changed' and row['completed_at']
    # Same query used by the reminder, without a second copy or synchronization.
    with sqlite3.connect(settings['DATABASE']) as db:
        assert db.execute("SELECT task FROM todo_items WHERE status='open'").fetchall() == []
    assert fresh.patch(f'/api/todos/{ident}', json={'status':'open'}, headers=ORIGIN).status_code == 200
    assert fresh.delete(f'/api/todos/{ident}', json={}, headers=ORIGIN).status_code == 200
    assert fresh.get('/api/todos').json['todos'] == []

@pytest.mark.parametrize('method,path,payload', [('post','/api/todos',{'task':'x'}),('patch','/api/todos/1',{'status':'completed'}),('delete','/api/todos/1',{})])
def test_viewer_cannot_write(client, method, path, payload):
    login(client, 'viewer-key')
    assert client.get('/api/todos').json['role'] == 'viewer'
    assert getattr(client,method)(path,json=payload,headers=ORIGIN).status_code == 403

def test_origin_and_validation(client):
    assert client.post('/api/login',json={'key':'owner-key'}).status_code == 403
    login(client)
    assert client.post('/api/todos',json={'task':'x'},headers={'Origin':'https://evil.example'}).status_code == 403
    for value in ['', ' '*3, 'x'*501, 5, None]:
        assert client.post('/api/todos',json={'task':value},headers=ORIGIN).status_code == 400
    assert client.patch('/api/todos/1',json={'status':'bad'},headers=ORIGIN).status_code == 400
    assert client.post('/api/todos',json=[],headers=ORIGIN).status_code == 400

def test_cookie_logout_rotation(client, settings):
    response = login(client)
    cookie = response.headers['Set-Cookie']
    for attr in ['Secure','HttpOnly','SameSite=Strict']:
        assert attr in cookie
    old_cookie = client.get_cookie('session').value
    changed = create_app({**settings,'VIEWER_KEY':'rotated'}).test_client()
    changed.set_cookie('session',old_cookie)
    assert changed.get('/api/todos').status_code == 401
    client.post('/api/logout',json={},headers=ORIGIN)
    assert client.get('/api/todos').status_code == 401

def test_rate_limit(client):
    for _ in range(30):
        assert login(client,'wrong').status_code == 401
    assert login(client,'wrong').status_code == 429

def test_fail_closed(settings):
    with pytest.raises(ValueError): create_app({**settings,'DATABASE':'/nonexistent/todo.db'})
    with pytest.raises(ValueError): create_app({**settings,'VIEWER_KEY':'owner-key'})

def test_security_headers(client):
    r=client.get('/')
    assert r.headers['Cache-Control']=='no-store'
    assert "frame-ancestors 'none'" in r.headers['Content-Security-Policy']
