"""Isolated full browser CRUD test, never writes production data."""
import sqlite3
import tempfile
import threading
from pathlib import Path
from playwright.sync_api import sync_playwright
from werkzeug.serving import make_server
from app import create_app

with tempfile.TemporaryDirectory() as directory:
    db=Path(directory)/'test.db'
    with sqlite3.connect(db) as con:
        con.execute("CREATE TABLE todo_items(todo_id INTEGER PRIMARY KEY AUTOINCREMENT,task TEXT NOT NULL,status TEXT DEFAULT 'open',created_at TEXT DEFAULT CURRENT_TIMESTAMP,completed_at TEXT)")
    app=create_app(dict(TESTING=True,SECRET_KEY='browser-test',OWNER_KEY='test-owner',VIEWER_KEY='test-viewer',DATABASE=str(db),PUBLIC_ORIGIN='http://127.0.0.1:18786',SESSION_COOKIE_SECURE=False))
    server=make_server('127.0.0.1',18786,app,threaded=True)
    worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch()
            context=browser.new_context(viewport={'width':1440,'height':1000})
            page=context.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
            page.goto('http://127.0.0.1:18786')
            page.locator('#key').fill('test-owner');page.locator('#loginForm button').click()
            page.locator('#workspace').wait_for(state='visible')
            malicious='<img src=x onerror=alert(1)>'
            page.locator('#task').fill(malicious);page.locator('#addForm button').click()
            page.locator('#list li').wait_for()
            assert page.locator('#list img').count()==0
            assert page.locator('#list').inner_text().find(malicious)>=0
            page.locator('#list button',has_text='編集').click()
            page.locator('#editTask').fill('browser-test-task');page.locator('#taskEditForm button',has_text='保存').click()
            page.locator('#list .tasktext',has_text='browser-test-task').wait_for()
            page.locator('#list input').check();page.locator('#doneTab').click()
            page.locator('#list .completed').wait_for()
            page.locator('#financeNav').click()
            page.locator('#newEntry').click();page.locator('#occurred').fill('2026-11-18');page.locator('#entryTitle').fill('browser-test-expense');page.locator('#amount').fill('1250');page.locator('#saveEntry').click()
            page.locator('#entries li').wait_for();assert page.locator('#expense').inner_text()=='￥1,250'
            page.locator('#entries button',has_text='編集').click();page.locator('#amount').fill('2000');page.locator('#saveEntry').click()
            page.wait_for_function("document.getElementById('expense').textContent === '￥2,000'")
            page.reload();page.locator('#entries li').wait_for();assert page.locator('#expense').inner_text()=='￥2,000'
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            page.locator('#logout').click();page.locator('#login').wait_for(state='visible')
            page.locator('#key').fill('test-viewer');page.locator('#loginForm button').click();page.locator('#entries li').wait_for()
            assert page.locator('#newEntry').is_hidden();assert page.locator('#entries button').count()==0
            assert page.locator('#expense').inner_text()=='￥2,000'
            assert page.evaluate("async()=> (await fetch('/api/finance',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({})})).status")==403
            page.set_viewport_size({'width':390,'height':844});assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            page.locator('#menu').click();page.locator('#todoNav').click();page.locator('#openTab').click();page.locator('#doneTab').click();page.locator('#list li').wait_for();assert page.locator('#list button').count()==0
            assert not errors,errors
            # Owner deletion through UI, still isolated.
            page.locator('#menu').click();page.locator('#logout').click();page.locator('#key').fill('test-owner');page.locator('#loginForm button').click();page.locator('#workspace').wait_for(state='visible')
            page.on('dialog',lambda dialog:dialog.accept())
            page.locator('#list button',has_text='削除').click();page.locator('#empty').wait_for(state='visible')
            page.locator('#menu').click();page.locator('#financeNav').click();page.locator('#entries li').wait_for();page.locator('#entries button',has_text='削除').click();page.locator('#financeEmpty').wait_for(state='visible')
            browser.close()
            print('PASS: owner CRUD, persistence, literal XSS rendering, shared viewer read, forbidden writes, desktop/mobile layout, zero page errors')
    finally:
        server.shutdown();worker.join()
