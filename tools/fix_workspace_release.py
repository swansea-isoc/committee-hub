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

p = Path('tools/test_workspace.py')
s = p.read_text()
s = s.replace("page.locator('#f-title').fill('Test media request')", "page.locator('#media-create #f-title').fill('Test media request')")
s = s.replace("checks.append('Executive action assignment')", "expect(page.locator('#drawer')).not_to_be_visible();expect(page.locator('#drawer-body')).to_be_empty();checks.append('Executive action assignment and synchronous removal of closed forms')")
p.write_text(s)
print('Dialog cleanup and regression checks applied.')
