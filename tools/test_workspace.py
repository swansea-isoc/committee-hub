"""UI tests use a mocked authenticated API. They do NOT claim live OAuth/mail/storage verification."""
from pathlib import Path
from functools import partial
import http.server, threading, json, copy, uuid, shutil
from datetime import datetime, timedelta, timezone
from playwright.sync_api import sync_playwright, expect
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'checks';OUT.mkdir(exist_ok=True)
class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*a):pass
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),partial(Quiet,directory=str(ROOT/'site')))
threading.Thread(target=server.serve_forever,daemon=True).start()
URL=f'http://127.0.0.1:{server.server_port}/'
A='11111111-1111-4111-8111-111111111111';B='22222222-2222-4222-8222-222222222222';C='44444444-4444-4444-8444-444444444444'
now=datetime.now(timezone.utc)
def stamp(n):return (now+timedelta(days=n)).isoformat()
people=[dict(id=A,name='Abubakr Majid',title='Brothers’ General Secretary',role='admin',finance=True,media=False,president=False,team='Exec',about='Minutes, inbox coordination and brothers’ reimbursements.'),dict(id=B,name='Fadumo',title='Sisters’ General Secretary',role='exec',finance=True,media=False,president=False,team='Exec',about='Room bookings, committee actions and sisters’ reimbursements.'),dict(id=C,name='Media member',title='Media subcommittee',role='member',finance=False,media=True,president=False,team='Media',about='Posters, event publicity and media requests.')]
def task(title,days,status='To do',owner=A):return dict(id=str(uuid.uuid4()),title=title,description='Agree the details and share a brief update with the team.',team='Exec' if owner==A else 'Media',owner=owner,creator=B,due=stamp(days),status=status,priority='Normal',revision=1,blocker='')
seed_tasks=[task('Share the committee communication plan',-1,'Blocked'),task('Prepare the next meeting agenda',3,'In progress'),task('Confirm the room-booking process',5,'For review'),task('Organise next month’s catch-up',12,'In progress'),task('Publish the previous meeting minutes',-3,'Done'),task('Create the next event poster',2,'To do',C)]
checks=[];errors=[]
def attach(page, persona='admin',denied=False):
    tasks=copy.deepcopy(seed_tasks);requests=[];reminders=[];files=[];claims=[];calls=[]
    user=copy.deepcopy(people[0] if persona in ['admin','exec'] else people[2]);
    if persona=='exec':user.update(role='exec',finance=False,president=False)
    def respond(route):
        if route.request.method=='OPTIONS':
            route.fulfill(status=204,headers={'Access-Control-Allow-Origin':'*','Access-Control-Allow-Headers':'authorization,apikey,content-type','Access-Control-Allow-Methods':'POST,OPTIONS'})
            return
        p=route.request.post_data_json or {};a=p.get('action');calls.append(p)
        response={};status=200
        if denied:
            route.fulfill(status=403,content_type='application/json',body=json.dumps({'error':'This account is not approved.','code':'MEMBERSHIP_DENIED'}));return
        if a=='bootstrap':response=dict(user=user,people=people,tasks=tasks if user['role']!='member' else [t for t in tasks if t['owner']==user['id']],media=requests,claims=claims,resources=[{'key':'media-form','url':'https://docs.google.com/forms/d/e/example/viewform'}],notifications=[],services={'email':False,'files':True,'finance':True,'mediaImport':False})
        elif a=='taskDetail':
            t=next(t for t in tasks if t['id']==p['id']);response={'task':t,'comments':[],'reminders':[r for r in reminders if r['task_id']==t['id']]}
        elif a=='taskUpdate':
            t=next(t for t in tasks if t['id']==p['id']);t.update({k:v for k,v in p['update'].items() if k!='comment'});t['revision']+=1;response={'task':t}
        elif a=='taskCreate':
            t=p['task'];t.update(id=str(uuid.uuid4()),creator=user['id'],status='To do',revision=1,blocker='');tasks.append(t);response={'task':t}
        elif a=='reminderSave':
            reminders.append(dict(id=str(uuid.uuid4()),task_id=p['task_id'],kind=p['kind'],offset_hours=(p.get('offset_days') or 0)*24,next_at=p.get('start') or stamp(2)));response={'success':True}
        elif a=='reminderDelete':reminders[:]=[r for r in reminders if r['id']!=p['id']];response={'success':True}
        elif a=='mediaCreate':
            r=p['request'];r.update(id=str(uuid.uuid4()),requester_id=user['id'],requester_name=user['name'],status='New',revision=1);requests.append(r);response={'id':r['id']}
        elif a=='mediaUpdate':next(r for r in requests if r['id']==p['id']).update(status=p['status']);response={'success':True}
        elif a=='fileList':response={'files':[f for f in files if f.get('parent')==p.get('parent') and f.get('scope','shared')=='shared']}
        elif a=='folderCreate':files.append(dict(id=str(uuid.uuid4()),parent=p.get('parent'),name=p['name'],kind='folder',created_at=stamp(0),owner_id=user['id'],size=0));response={'success':True}
        elif a=='filePrepare':
            fid=str(uuid.uuid4());files.append(dict(id=fid,parent=p.get('parent'),name=p['name'],kind='file',created_at=stamp(0),owner_id=user['id'],size=p['size'],mime=p['mime'],scope=p['scope']));response={'id':fid,'upload_url':'https://unit.supabase.co/upload','mime':p['mime']}
        elif a=='fileFinish':response={'success':True}
        elif a=='claimCreate':
            c=p['claim'];c.update(id=str(uuid.uuid4()),requester_id=user['id'],status='Awaiting review',revision=1);claims.append(c);response={'id':c['id']}
        elif a=='feedbackSend':response={'success':True,'email_enabled':False}
        elif a=='feedbackList':response={'messages':[]}
        elif a=='notificationsRead':response={'success':True}
        elif a=='memberList':response={'members':[{**u,'email':'test@example.test','active':True} for u in people]}
        elif a=='approveMember' or a=='resourceSave':response={'success':True}
        else:response={'error':'unmocked action '+str(a)};status=400
        route.fulfill(status=status,content_type='application/json',headers={'Access-Control-Allow-Origin':'*'},body=json.dumps(response))
    page.route('**/config.js*',lambda r:r.fulfill(content_type='application/javascript',body="window.HUB_CONFIG={supabaseUrl:'https://unit.supabase.co',supabasePublishableKey:'test',apiFunction:'committee-api',edition:'2026 / 27'};"))
    page.route('https://cdn.jsdelivr.net/**',lambda r:r.fulfill(content_type='application/javascript',body="window.supabase={createClient:()=>({auth:{getSession:async()=>({data:{session:{access_token:'test-token'}}}),onAuthStateChange:()=>{},signOut:async()=>{},signInWithOAuth:async()=>({})}})};"))
    page.route('https://unit.supabase.co/functions/**',respond)
    page.route('https://unit.supabase.co/upload',lambda r:r.fulfill(status=204 if r.request.method=='OPTIONS' else 200,headers={'Access-Control-Allow-Origin':'*','Access-Control-Allow-Headers':'content-type,x-upsert','Access-Control-Allow-Methods':'PUT,POST,OPTIONS'},content_type='application/json',body='' if r.request.method=='OPTIONS' else '{}'))
    page.route('https://docs.google.com/**',lambda r:r.fulfill(content_type='text/html',body='<p>External form isolated during browser tests.</p>'))
    page.on('pageerror',lambda e:errors.append(str(e)))
    return calls
try:
 with sync_playwright() as p:
    browser=p.chromium.launch(headless=True, executable_path=shutil.which("chromium") or None, args=["--no-sandbox"])
    page=browser.new_page(viewport={'width':1440,'height':1000})
    page.goto(URL,wait_until='networkidle');expect(page.get_by_role('button',name='Continue with Google')).to_be_disabled();assert page.locator('.task-row').count()==0
    page.screenshot(path=str(OUT/'login-desktop.png'),full_page=True)
    page.goto(URL+'?demo=1#space',wait_until='networkidle');expect(page.get_by_role('button',name='Continue with Google')).to_be_disabled()
    page.goto(URL+'demo.html',wait_until='networkidle');expect(page.get_by_role('button',name='Continue with Google')).to_be_disabled();checks.append('Unconfigured live entry fails closed; old demo redirects; no URL bypass')
    page.close()
    page=browser.new_page(viewport={'width':1440,'height':1000});calls=attach(page)
    page.goto(URL,wait_until='networkidle');expect(page.locator('h1')).to_contain_text('Assalamu alaikum');assert page.locator('[data-persona]').count()==0
    page.screenshot(path=str(OUT/'my-space-desktop.png'),full_page=True)
    for width in [320,390,768,1440]:
        page.set_viewport_size({'width':width,'height':900});assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),f'Overflow space {width}'
        if width==390:page.screenshot(path=str(OUT/'my-space-phone.png'),full_page=True)
    checks.append('Persistent-session entry, greeting, dark My Space, no demo/persona controls; 4 widths')
    page.set_viewport_size({'width':1440,'height':1000});page.goto(URL+'#actions',wait_until='networkidle');expect(page.locator('[data-cmd=new-task]')).to_be_visible()
    page.get_by_role('button',name='All committee',exact=True).click();page.get_by_role('button',name='Board view').click();page.screenshot(path=str(OUT/'actions-board.png'),full_page=True)
    page.get_by_role('button',name='List view').click();page.locator('#action-search').fill('agenda');expect(page.locator('.task-row')).to_have_count(1)
    page.locator('.task-row').click();expect(page.locator('#drawer')).to_be_visible();page.locator('#f-status').select_option('Done');page.locator('#f-update').fill('Ready for review.');page.get_by_role('button',name='Save progress').click();expect(page.locator('#toast')).to_contain_text('Progress saved')
    assert any(x['action']=='taskUpdate' and x['update']['status']=='Done' for x in calls)
    page.locator('#action-search').fill('catch-up');page.locator('.task-row').click();page.get_by_role('button',name='My reminders',exact=True).click();page.locator('#f-kind').select_option('weekly');expect(page.locator('#start-field')).to_be_visible();page.get_by_role('button',name='Save reminder',exact=True).click();expect(page.locator('#toast')).to_contain_text('Email delivery is not enabled')
    assert any(x['action']=='reminderSave' and x['kind']=='weekly' for x in calls)
    checks.append('Action search, board, task editing, completion, recurring reminder saves with truthful delivery state')
    page.get_by_role('button',name='Assign action',exact=True).click();page.locator('#f-title').fill('Test new action');page.locator('#f-description').fill('Test only');page.locator('#task-create [type=submit]').click();expect(page.locator('#toast')).to_contain_text('Action assigned')
    expect(page.locator('#drawer')).not_to_be_visible();expect(page.locator('#drawer-body')).to_be_empty();checks.append('Executive action assignment and synchronous removal of closed forms')
    page.goto(URL+'#media',wait_until='networkidle');page.locator('#media-create #f-title').fill('Test media request');page.locator('#f-brief').fill('Details for a committee poster');page.locator('#media-create [type=submit]').click();expect(page.locator('.task-title')).to_contain_text('Test media request');page.locator('.task-row').click();expect(page.get_by_role('link',name='Add to Google Calendar')).to_have_attribute('href',__import__('re').compile('^https://calendar.google.com/calendar/render\\?'));page.keyboard.press('Escape')
    page.get_by_role('button',name='Existing Google Form',exact=True).click();expect(page.locator('iframe')).to_have_attribute('src','https://docs.google.com/forms/d/e/example/viewform?embedded=true');checks.append('Native media requests, original form embed and explicit one-off Google Calendar link')
    page.goto(URL+'#files',wait_until='networkidle');page.get_by_role('button',name='New folder').click();page.locator('#f-name').fill('Meeting minutes');page.locator('#folder-form [type=submit]').click();expect(page.locator('.file-card strong')).to_have_text('Meeting minutes');page.locator('.file-card>button').click();page.locator('#file-picker').set_input_files({'name':'notes.txt','mimeType':'text/plain','buffer':b'Test committee notes'});expect(page.locator('.file-card strong')).to_have_text('notes.txt');assert any(x['action']=='fileFinish' for x in calls);page.screenshot(path=str(OUT/'files-desktop.png'),full_page=True);checks.append('Folder creation, breadcrumb navigation, upload then finalisation')
    page.goto(URL+'#finance',wait_until='networkidle');expect(page.get_by_role('button',name='Finance desk',exact=False)).to_be_visible();page.get_by_role('button',name='New claim').click();page.locator('#f-student_number').fill('TEST123');page.locator('#f-event').fill('Test event');page.locator('#f-amount').fill('5');page.locator('#f-items').fill('Printing');page.locator('#f-sort_code').fill('12-34-56');page.locator('#f-account_number').fill('12345678');page.locator('#f-receipt').set_input_files({'name':'test.pdf','mimeType':'application/pdf','buffer':b'%PDF-1.4 test'});page.locator('#claim-create [type=submit]').click();expect(page.locator('#toast')).to_contain_text('Claim submitted');assert '12345678' not in page.evaluate('JSON.stringify(localStorage)');checks.append('Native claim form, private receipt scope and no bank details in browser localStorage')
    page.goto(URL+'#wellbeing',wait_until='networkidle');page.locator('#f-recipient').select_option('exec');page.locator('#f-topic').fill('Support');page.locator('#f-message').fill('I need a little help with my workload.');page.locator('#feedback-send [type=submit]').click();expect(page.locator('#toast')).to_contain_text('Email alerts are not enabled');last=[x for x in calls if x['action']=='feedbackSend'][-1];assert set(last)=={'action','recipient','topic','message'};page.screenshot(path=str(OUT/'wellbeing-desktop.png'),full_page=True);checks.append('Feedback payload contains no sender details; acknowledgement does not falsely claim email sent')
    for route in ['actions','media','finance','files','people','wellbeing','settings']:
        for width in [320,390,768,1440]:
            page.set_viewport_size({'width':width,'height':900})
            page.evaluate('(name)=>{location.hash=name}', route)
            title = {'actions':'Action points','media':'Media','finance':'Reimbursements','files':'Shared files','people':'Who’s who','wellbeing':'Well-being','settings':'Settings'}[route]
            expect(page).to_have_title(title + ' · Swansea ISOC')
            expect(page.locator('#main')).to_be_visible()
            page.evaluate('() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))')
            if width == 320:
                page.screenshot(path=str(OUT / (route + '-320.png')), full_page=True)
            if not page.evaluate('document.documentElement.scrollWidth<=innerWidth'):
                offenders = page.locator('body *').evaluate_all('(els)=>els.filter(e=>{const r=e.getBoundingClientRect();return r.width>0&&r.right>innerWidth+1}).map(e=>({tag:e.tagName,cls:e.className,text:e.textContent.slice(0,80),right:e.getBoundingClientRect().right})).slice(0,12)')
                raise AssertionError(f'Overflow {route} {width}: {offenders}')
    checks.append('Every authenticated page fits 320/390/768/1440px without document overflow')
    page.close()
    for role in ['member','exec']:
        page=browser.new_page();attach(page,role);page.goto(URL+'#actions',wait_until='networkidle')
        if role=='member':expect(page.locator('[data-cmd=new-task]')).to_have_count(0);expect(page.locator('.task-row')).to_have_count(1)
        page.goto(URL+'#finance',wait_until='networkidle');expect(page.get_by_role('button',name='Finance desk')).to_have_count(0)
        page.goto(URL+'#settings',wait_until='networkidle');expect(page.locator('h1')).to_contain_text('Assalamu alaikum')
        page.close()
    checks.append('Normal committee cannot assign or see other tasks; ordinary executives do not get finance/admin views')
    page=browser.new_page();attach(page,denied=True);page.goto(URL,wait_until='networkidle');expect(page.locator('.auth-card')).to_contain_text('not approved');expect(page.locator('.task-row')).to_have_count(0);page.close();checks.append('Server membership denial does not expose workspace')
    assert not errors,errors
    browser.close()
 (OUT/'ui-results.json').write_text(json.dumps({'passed':True,'checks':checks,'javascriptErrors':errors,'testMode':'Mocked API and auth responses; not a live backend or email delivery test'},indent=2))
 print(json.dumps({'passed':True,'checks':len(checks),'javascriptErrors':errors},indent=2))
finally:server.shutdown()
