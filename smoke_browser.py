"""Public HTTPS browser smoke test. Uses local keys without printing them."""
from pathlib import Path
from playwright.sync_api import sync_playwright

secrets = dict(line.split('=',1) for line in Path('/home/sprzk/.config/chronos-todo/app.env').read_text().splitlines())
with sync_playwright() as p:
    browser = p.chromium.launch()
    for role, field in [('owner','TODO_OWNER_KEY'),('viewer','TODO_VIEWER_KEY')]:
        context = browser.new_context(viewport={'width':390,'height':844})
        page = context.new_page()
        response = page.goto('https://task.supurazako.com')
        assert response.status == 200
        page.locator('#key').fill(secrets[field])
        page.locator('#loginForm button').click()
        page.locator('#workspace').wait_for(state='visible')
        assert page.locator('#addForm').is_visible() == (role == 'owner')
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        if role == 'viewer':
            status = page.evaluate("""async () => (await fetch('/api/todos', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({task:'must not be added'})})).status""")
            assert status == 403
        page.screenshot(path=f'/home/sprzk/.hermes/profiles/calendar-owner/cache/scratch/todo-{role}.png',full_page=True)
        page.locator('#logout').click()
        page.locator('#login').wait_for(state='visible')
        print(f'{role}: HTTPS login, mobile layout, role controls, logout PASS')
        context.close()
    browser.close()
