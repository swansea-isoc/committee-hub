"""Apply narrowly scoped fixes to the staged V3 release; safe on repeated runs."""
from pathlib import Path

p = Path('site/workspace.js')
s = p.read_text()
old = "function close(force=false){if(dirty&&!force&&!confirm('Discard your unsaved changes?'))return;$('drawer').close();dirty=false;if(opener?.isConnected)opener.focus();}"
new = "function close(force=false){if(dirty&&!force&&!confirm('Discard your unsaved changes?'))return false;const returnTo=opener;$('drawer-body').replaceChildren();dirty=false;if($('drawer').open)$('drawer').close();if(returnTo?.isConnected)returnTo.focus();return true;}"
if old in s:
    s = s.replace(old, new)
elif new not in s:
    raise RuntimeError('Unexpected dialog close implementation')
s = s.replace("$('drawer').addEventListener('close',()=>{$('drawer-body').innerHTML='';dirty=false;});", "$('drawer').addEventListener('close',()=>{if(!$('drawer').open){$('drawer-body').replaceChildren();dirty=false;}});")
p.write_text(s)

p = Path('site/workspace.css')
s = p.read_text()
marker = '/* Compact phone layouts: wrap controls rather than hide overflowing content. */'
if marker not in s:
    s += '\n' + marker + '\n.page-title>div{min-width:0}.page-title h1{overflow-wrap:anywhere}.task-title,.task-detail,.comment p{overflow-wrap:anywhere}\n@media(max-width:720px){.page-title{flex-wrap:wrap;gap:12px}.page-title>div{flex:1 1 240px}.file-toolbar,.file-toolbar>div:last-child,.dropzone,.integration{flex-wrap:wrap}.file-toolbar>div{min-width:0}.breadcrumbs{flex-wrap:wrap;overflow-wrap:anywhere}.integration>div{min-width:0}.form-actions{flex-wrap:wrap}}\n'
p.write_text(s)

p = Path('tools/test_workspace.py')
s = p.read_text()
s = s.replace("page.locator('#f-title').fill('Test media request')", "page.locator('#media-create #f-title').fill('Test media request')")
s = s.replace("checks.append('Executive action assignment')", "expect(page.locator('#drawer')).not_to_be_visible();expect(page.locator('#drawer-body')).to_be_empty();checks.append('Executive action assignment and synchronous removal of closed forms')")
old_loop = "            page.set_viewport_size({'width':width,'height':900});page.goto(URL+'#'+route,wait_until='networkidle');assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),f'Overflow {route} {width}'"
new_loop = """            page.set_viewport_size({'width':width,'height':900})
            page.evaluate('(name)=>{location.hash=name}', route)
            title = {'actions':'Action points','media':'Media','finance':'Reimbursements','files':'Shared files','people':'Who’s who','wellbeing':'Well-being','settings':'Settings'}[route]
            expect(page).to_have_title(title + ' · Swansea ISOC')
            expect(page.locator('#main')).to_be_visible()
            page.evaluate('() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))')
            if width == 320:
                page.screenshot(path=str(OUT / (route + '-320.png')), full_page=True)
            if not page.evaluate('document.documentElement.scrollWidth<=innerWidth'):
                offenders = page.locator('body *').evaluate_all('(els)=>els.filter(e=>{const r=e.getBoundingClientRect();return r.width>0&&r.right>innerWidth+1}).map(e=>({tag:e.tagName,cls:e.className,text:e.textContent.slice(0,80),right:e.getBoundingClientRect().right})).slice(0,12)')
                raise AssertionError(f'Overflow {route} {width}: {offenders}')"""
if old_loop in s:
    s = s.replace(old_loop, new_loop)
else:
    start = s.find("            page.set_viewport_size({'width':width,'height':900})\n            page.evaluate('(name)=>{location.hash=name}', route)")
    end = s.find("    checks.append('Every authenticated page fits", start)
    if start < 0 or end < 0:
        raise RuntimeError('Unexpected viewport loop')
    s = s[:start] + new_loop + '\n' + s[end:]
p.write_text(s)
print('Dialog cleanup, compact layouts and deterministic navigation checks applied.')
