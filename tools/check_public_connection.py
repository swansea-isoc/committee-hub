"""Read-only live checks. Uses only the browser publishable key; never logs private data."""
from pathlib import Path
import json
import re
import urllib.error
import urllib.request

root = Path(__file__).resolve().parents[1]
config = (root / 'site/config.js').read_text()
def setting(name):
    match = re.search(r'\b' + re.escape(name) + r"\s*:\s*'([^']*)'", config)
    return match.group(1) if match else ''
base = setting('supabaseUrl').rstrip('/')
key = setting('supabasePublishableKey')
if not base or not key:
    print('Public connection checks skipped: project not configured.')
    raise SystemExit(0)
assert base == 'https://pawgtcpbmgtxntvjugja.supabase.co', 'Unexpected backend target'
assert key.startswith('sb_publishable_'), 'Use a publishable browser key'
origin = 'https://swansea-isoc.github.io'
api = base + '/functions/v1/committee-api'
results = []

def request(url, method='GET', payload=None, extra=None):
    headers = {'apikey': key, 'Origin': origin, 'User-Agent': 'ISOC-Committee-Hub-Connection-Check'}
    if payload is not None:
        headers['Content-Type'] = 'application/json'
    headers.update(extra or {})
    req = urllib.request.Request(url, data=None if payload is None else json.dumps(payload).encode(), headers=headers, method=method)
    try:
        response = urllib.request.urlopen(req, timeout=25)
    except urllib.error.HTTPError as error:
        response = error
    with response:
        raw = response.read(16384)
        try:
            body = json.loads(raw)
        except (ValueError, UnicodeDecodeError):
            body = {}
        return response.code, response.headers, body

status, _, body = request(base + '/auth/v1/settings')
assert status == 200 and body.get('external', {}).get('google') is True, 'Google provider is not enabled'
results.append({'check': 'Google provider enabled', 'passed': True})
status, headers, _ = request(api, method='OPTIONS')
assert status == 204 and headers.get('Access-Control-Allow-Origin') == origin, 'Approved website preflight failed'
results.append({'check': 'Website origin permitted', 'passed': True})
status, headers, body = request(api, method='POST', payload={'action': 'bootstrap'})
assert status == 401 and body.get('error') == 'Sign in with Google first.', 'Anonymous workspace request was not rejected'
assert headers.get('Access-Control-Allow-Origin') == origin
results.append({'check': 'Anonymous workspace access denied', 'passed': True})
status, _, _ = request(api, method='POST', payload={'action': 'bootstrap'}, extra={'Authorization': 'Bearer deliberately-invalid-token'})
assert status == 401, 'Invalid token was not rejected'
results.append({'check': 'Invalid token access denied', 'passed': True})
status, _, _ = request(api, method='POST', payload={'action': 'mailClaim'})
assert status == 403, 'Email agent requires its own secret'
results.append({'check': 'Unauthorised email-agent access denied', 'passed': True})
status, _, _ = request(base + '/rest/v1/hub3_members?select=id&limit=1')
assert status in (401, 403), 'Anonymous direct member-table access was not denied'
results.append({'check': 'Direct member-table access denied', 'passed': True})
out = root / 'checks'
out.mkdir(exist_ok=True)
(out / 'public-connection.json').write_text(json.dumps({'passed': True, 'checks': results, 'limitations': 'No real Google login, file upload, finance submission or email sending was performed.'}, indent=2))
print(json.dumps({'passed': True, 'checks': results}, indent=2))
