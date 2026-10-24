"""Browser checks for the PUBLIC prototype, not live authentication or integrations."""
from pathlib import Path
from functools import partial
import http.server
import threading
import json
from playwright.sync_api import sync_playwright, expect

root = Path(__file__).resolve().parents[1]
site = root / 'site'
out = root / 'checks'
out.mkdir(exist_ok=True)
class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass
server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), partial(Quiet, directory=str(site)))
threading.Thread(target=server.serve_forever, daemon=True).start()
base = f'http://127.0.0.1:{server.server_port}'
checks = []
errors = []
try:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width': 1440, 'height': 1000})
        page.on('pageerror', lambda e: errors.append(str(e)))
        # No real Google forms, banking, files or task APIs may receive test traffic.
        page.route('https://**/*', lambda r: r.abort())
        page.goto(base + '/demo.html', wait_until='networkidle')
        expect(page.locator('h1')).to_contain_text('Assalamu alaikum,')
        expect(page.locator('.task-row')).to_have_count(3)
        expect(page.locator('#preview-persona')).to_be_visible()
        assert page.locator('input[type=password]').count() == 0
        assert 'not a live committee account' in page.locator('#preview-bar').inner_text()
        checks.append('My Space opens directly; clearly labelled sample preview')
        page.screenshot(path=str(out / 'desktop.png'), full_page=True)
        def nav(route):
            page.evaluate('(route) => {location.hash = route}', route)
            page.wait_for_timeout(80)
        def persona(value):
            page.locator('#preview-persona').select_option(value)
        nav('actions')
        page.locator('[data-scope=all]').click()
        expect(page.locator('.task-row')).to_have_count(10)
        page.locator('[data-view=board]').click()
        page.locator('[data-action=new-task]').click()
        page.locator('#new-title').fill('Example check: arrange a briefing')
        page.locator('#new-owner').select_option('member')
        page.locator('#new-team').select_option('Media')
        page.locator('#new-task-form [type=submit]').click()
        expect(page.locator('.task-card', has_text='arrange a briefing')).to_have_count(1)
        checks.append('Executive preview creates and assigns a sample action')
        persona('member')
        expect(page.locator('[data-scope=all]')).to_have_count(0)
        expect(page.locator('[data-action=new-task]')).to_have_count(0)
        expect(page.locator('[data-task=AP-101]')).to_have_count(0)
        page.locator('[data-task=AP-106]').click()
        for field in ['task-owner', 'task-title', 'task-due']:
            expect(page.locator('#' + field)).to_have_count(0)
        page.locator('#task-status').select_option('For review')
        page.locator('#task-note').fill('Example update <img src=x onerror=alert(1)>')
        page.locator('#task-form [type=submit]').click()
        page.locator('[data-task=AP-106]').click()
        expect(page.locator('.task-notes')).to_contain_text('<img src=x onerror=alert(1)>')
        assert page.locator('.task-notes img').count() == 0
        page.keyboard.press('Escape')
        checks.append('Member preview shows own actions only; progress updates escape HTML')
        nav('finance')
        for role in ['volunteer', 'exec', 'president']:
            persona(role)
            expect(page.locator('[data-finance=desk]')).to_have_count(0)
        for role in ['secretary', 'fadumo']:
            persona(role)
            page.locator('[data-finance=desk]').click()
            expect(page.locator('table')).to_have_count(1)
        checks.append('Finance preview is restricted to the two General Secretary personas')
        persona('volunteer')
        nav('media')
        expect(page.locator('[data-media=team]')).to_have_count(0)
        assert page.locator('iframe').count() == 0
        assert page.locator('#main form').count() == 0
        checks.append('Public demo has no live media form or private response-sheet links')
        nav('wellbeing')
        page.locator('#feedback').fill('Example concern addressed to the president only.')
        page.locator('#wellbeing-form [type=submit]').click()
        expect(page.locator('#toast')).to_contain_text('no message was sent')
        persona('exec')
        page.locator('[data-wellbeing=inbox]').click()
        expect(page.locator('.inbox-message')).to_have_count(0)
        persona('president')
        page.locator('[data-wellbeing=inbox]').click()
        expect(page.locator('.inbox-message')).to_have_count(1)
        assert 'Committee volunteer' not in page.locator('.inbox-message').inner_text()
        assert 'Example concern' not in page.evaluate('JSON.stringify(localStorage)')
        checks.append('Example feedback is transient, recipient-filtered and not emailed')
        persona('secretary')
        nav('files')
        page.locator('[data-folder=media]').click()
        page.locator('[data-file-view=grid]').click()
        expect(page.locator('.file-tile')).to_have_count(2)
        page.locator('[data-file=f3]').click()
        expect(page.locator('#dialog')).to_be_visible()
        page.keyboard.press('Escape')
        checks.append('Sample shared-file folders, gallery and previews work')
        for route in ['space', 'actions', 'media', 'finance', 'files', 'people', 'values', 'wellbeing']:
            nav(route)
            for width in [320, 390, 768, 1440]:
                page.set_viewport_size({'width': width, 'height': 900})
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), (route, width)
        checks.append('Eight pages checked at four widths without horizontal overflow')
        nav('space')
        page.set_viewport_size({'width': 390, 'height': 844})
        page.screenshot(path=str(out / 'mobile.png'), full_page=True)
        page.locator('[data-action=more]').click()
        expect(page.locator('.menu-list')).to_be_visible()
        page.keyboard.press('Escape')
        nav('people')
        page.locator('#people-search').fill('bookings')
        expect(page.locator('.person')).to_have_count(1)
        checks.append('Mobile More menu and role-responsibility search work')
        page.goto(base + '/demo.html#actions', wait_until='networkidle')
        assert 'arrange a briefing' in page.evaluate('JSON.stringify(localStorage)')
        checks.append('Sample task changes persist in this browser')
        gate = browser.new_page()
        gate.on('pageerror', lambda e: errors.append(str(e)))
        gate.goto(base + '/index.html?demo=1#space', wait_until='networkidle')
        expect(gate.locator('[data-action=google]')).to_be_disabled()
        assert gate.locator('.task-row').count() == 0
        assert gate.locator('#preview-persona').count() == 0
        assert 'not enabled yet' in gate.locator('.gate-note').inner_text()
        checks.append('Unconfigured private entry stays locked and ignores demo query parameters')
        broken = page.locator('img').evaluate_all('(images) => images.filter(i => !i.complete || !i.naturalWidth).map(i => i.src)')
        assert not broken, broken
        assert not errors, errors
        result = {'passed': True, 'checks': checks, 'javascriptErrors': errors, 'notConnected': ['Google sign-in', 'Server-side committee authorisation', 'ClickUp', 'Email notifications', 'OneDrive', 'Live media and finance tools']}
        (out / 'results.json').write_text(json.dumps(result, indent=2))
        print(json.dumps(result, indent=2))
        browser.close()
finally:
    server.shutdown()
