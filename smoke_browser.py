"""Public HTTPS verification without production data changes or disclosure."""
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

keys=dict(line.split('=',1) for line in Path('/home/sprzk/.config/chronos-todo/app.env').read_text().splitlines())
with sync_playwright() as p:
    browser=p.chromium.launch()
    for role in ['anonymous','owner']:
        context=browser.new_context(viewport={'width':390,'height':844})
        page=context.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
        response=page.goto('https://task.supurazako.com')
        assert response.status==200 and 'noindex' in response.headers['x-robots-tag']
        page.locator('#workspace').wait_for(state='visible')
        assert page.locator('#login').is_hidden() and page.locator('#addForm').is_hidden()
        if role=='owner':
            page.locator('#menu').click();page.locator('#ownerLogin').click()
            page.locator('#key').fill(keys['TODO_OWNER_KEY']);page.locator('#loginForm button').click()
            page.locator('#addForm').wait_for(state='visible')
        assert page.locator('#addForm').is_visible()==(role=='owner')
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        if role=='anonymous':
            for method,path in [('POST','/api/todos'),('PATCH','/api/todos/1'),('DELETE','/api/todos/1'),('POST','/api/finance'),('PUT','/api/finance/1'),('DELETE','/api/finance/1')]:
                status=page.evaluate("async ({method,path}) => (await fetch(path,{method,headers:{'Content-Type':'application/json'},body:JSON.stringify({})})).status",{'method':method,'path':path})
                assert status==401
        page.locator('#menu').click();page.locator('#financeNav').click()
        expect(page.locator('#income')).not_to_have_text('—')
        assert page.locator('#newEntry').is_visible()==(role=='owner')
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        page.set_viewport_size({'width':1440,'height':1000})
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        if role=='owner':
            page.locator('#logout').click();page.locator('#ownerLogin').wait_for(state='visible')
            assert page.locator('#login').is_hidden()
            expect(page.locator('#newEntry')).to_be_hidden()
        assert not errors,errors
        print(f'{role}: HTTPS public read, role controls, desktop/mobile layout, noindex PASS')
        context.close()
    browser.close()
