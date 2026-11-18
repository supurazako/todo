"""Public HTTPS read-only smoke test; never prints keys or private records."""
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

keys=dict(line.split('=',1) for line in Path('/home/sprzk/.config/chronos-todo/app.env').read_text().splitlines())
with sync_playwright() as p:
    browser=p.chromium.launch()
    for role,field in [('owner','TODO_OWNER_KEY'),('viewer','TODO_VIEWER_KEY')]:
        context=browser.new_context(viewport={'width':390,'height':844})
        page=context.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
        assert page.goto('https://task.supurazako.com').status==200
        page.locator('#key').fill(keys[field]);page.locator('#loginForm button').click()
        page.locator('#workspace').wait_for(state='visible')
        assert page.locator('#addForm').is_visible()==(role=='owner')
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        if role=='viewer':
            assert page.evaluate("async()=> (await fetch('/api/todos',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({task:'must not be added'})})).status")==403
        page.locator('#menu').click();page.locator('#financeNav').click()
        expect(page.locator('#income')).not_to_have_text('—')
        assert page.locator('#newEntry').is_visible()==(role=='owner')
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        if role=='viewer':
            assert page.locator('#entries button').count()==0
            assert page.evaluate("async()=> (await fetch('/api/finance',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({})})).status")==403
        page.set_viewport_size({'width':1440,'height':1000})
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        page.locator('#logout').click();page.locator('#login').wait_for(state='visible')
        assert not errors,errors
        print(f'{role}: public HTTPS login, TODO and finance access, mobile/desktop layout, permissions, logout PASS')
        context.close()
    browser.close()
