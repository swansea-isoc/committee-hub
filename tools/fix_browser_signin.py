"""Narrow, repeatable source patch. Does not change backend or discount sites."""
from pathlib import Path
import hashlib

root = Path(__file__).resolve().parents[1]
p = root / 'site/workspace.js'
s = p.read_text()
if '// Sign-in recovery 2026-10-25' in s:
    print('Sign-in recovery is already applied.')
    raise SystemExit(0)
raw = p.read_bytes()
assert hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() == '704854c844e90738a14e8e314f55c78fb774f91f', 'Review changed workspace before applying this patch'
s = s.replace("const cfg=window.HUB_CONFIG||{}, $=id=>document.getElementById(id);", "const cfg=window.HUB_CONFIG||{}, $=id=>document.getElementById(id);\n// Sign-in recovery 2026-10-25\nlet authReady=false,signingIn=false;")
lines = s.splitlines()
for i, line in enumerate(lines):
    if line.startswith('function authScreen('):
        line = line.replace("${!configured?'disabled':''}", "${(!configured||!authReady||signingIn)?'disabled':''}")
        line = line.replace('Continue with Google</button>', "${signingIn?'Opening Google…':configured&&!authReady?'Checking sign-in…':'Continue with Google'}</button>")
        line = line.replace('<div class="lock-note">', '${configured&&authReady?`<details class="section-gap"><summary>Trouble signing in?</summary><p class="small">Restart this hub’s saved sign-in on this browser. This does not clear your Google cookies, affect other websites, or delete committee records.</p><button type="button" class="button secondary" data-cmd="reset-login" ${signingIn?\'disabled\':\'\'}>Restart sign-in</button></details>`:\'\'}<div class="lock-note">')
        lines[i] = line
    if line.startswith('async function login('):
        lines[i] = r'''function clearAuthLocation(){
 const u=new URL(location.href);
 for(const k of ['code','error','error_code','error_description','error_uri'])u.searchParams.delete(k);
 const h=new URLSearchParams(u.hash.slice(1));
 if(['error','error_description','access_token','refresh_token'].some(k=>h.has(k)))u.hash='';
 history.replaceState(history.state,'',u.pathname+u.search+u.hash);
}
function callbackError(){
 const q=new URLSearchParams(location.search),h=new URLSearchParams(location.hash.slice(1));
 return q.get('error_code')||q.get('error')||h.get('error_code')||h.get('error')||'';
}
function signinMessage(e){
 const code=String(e?.code||e||'');
 if(code==='access_denied')return 'Google sign-in was cancelled or not permitted. Choose your approved account and try again.';
 return 'Sign-in did not finish. Use Restart sign-in below, then choose your approved Google account. Keep the sign-in in this browser tab.';
}
async function login(){
 if(!client||!authReady||signingIn)return;
 signingIn=true;authScreen();
 try{
  // PKCE must survive the round trip in this browser; do not silently use memory-only storage.
  try{localStorage.setItem('__isoc_hub_storage_probe__','1');localStorage.removeItem('__isoc_hub_storage_probe__');}
  catch{throw new Error('Allow this site to save browser data before signing in.');}
  clearAuthLocation();
  const redirectTo=cfg.redirectUrl||new URL('./',location.href).href;
  const {data:result,error}=await client.auth.signInWithOAuth({provider:'google',options:{redirectTo,queryParams:{prompt:'select_account'},skipBrowserRedirect:true}});
  if(error)throw error;
  const target=new URL(result?.url||'');
  if(target.origin!==new URL(cfg.supabaseUrl).origin||target.pathname!=='/auth/v1/authorize')throw new Error('The sign-in service returned an unexpected address.');
  // SDK generates a new PKCE verifier; Supabase generates/validates OAuth state. Never forge either.
  location.assign(target.href);
 }catch(e){signingIn=false;authScreen(e?.message==='Allow this site to save browser data before signing in.'?e.message:'Google sign-in could not start. Please try again.');}
}
async function resetLogin(){
 if(!client||!authReady||signingIn)return;
 signingIn=true;authScreen();
 let timer;
 try{
  // Revoke only this browser's session, not a successful phone/incognito session.
  await Promise.race([client.auth.signOut({scope:'local'}),new Promise(resolve=>{timer=setTimeout(resolve,8000);})]);
 }catch{/* Local recovery must still work if a stale session cannot reach the server. */}
 finally{clearTimeout(timer);}
 try{
  const prefix='sb-'+new URL(cfg.supabaseUrl).hostname.split('.')[0]+'-auth-token';
  for(const store of [localStorage,sessionStorage])for(const suffix of ['','-code-verifier','-user'])store.removeItem(prefix+suffix);
 }catch{signingIn=false;authScreen('Allow this site to save browser data, then try again.');return;}
 // Discard stale in-memory auth too. Only the canonical hub page is reopened.
 location.replace(cfg.redirectUrl||new URL('./',location.href).href);
}'''
    if line.startswith('async function start('):
        lines[i] = r'''async function start(){
 page=location.hash.slice(1)||'space';const problem=callbackError();authScreen();
 if(!cfg.supabaseUrl||!cfg.supabasePublishableKey)return;
 try{
  const u=new URL(cfg.supabaseUrl);if(u.protocol!=='https:'||!u.hostname.endsWith('.supabase.co'))throw new Error('The private backend address is invalid.');
  await new Promise((resolve,reject)=>{const s=document.createElement('script');s.src='https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2.57.4/dist/umd/supabase.js';s.onload=resolve;s.onerror=()=>reject(new Error('Google sign-in could not load. Please refresh the page.'));document.head.append(s);});
  client=window.supabase.createClient(cfg.supabaseUrl,cfg.supabasePublishableKey,{auth:{flowType:'pkce',persistSession:true,autoRefreshToken:true,detectSessionInUrl:true}});
  client.auth.onAuthStateChange((event)=>{
   if(event==='SIGNED_OUT'){close(true);me=null;data={tasks:[],people:[],media:[],claims:[],notifications:[],resources:[]};files=[];authScreen();}
   if(event==='SIGNED_IN'&&!me)setTimeout(()=>{authReady=true;clearAuthLocation();refresh();},0);
  });
  const {data:s,error}=await client.auth.getSession();authReady=true;
  if(error){clearAuthLocation();authScreen(signinMessage(error));return;}
  if(s.session){clearAuthLocation();await refresh();}
  else{if(problem)clearAuthLocation();authScreen(problem?signinMessage(problem):'');}
 }catch(e){authReady=!!client;if(client)clearAuthLocation();authScreen(client?signinMessage(e):e.message);}
}
// Browser Back can restore a disabled button from the back/forward cache.
window.addEventListener('pageshow',e=>{if(e.persisted&&!me){signingIn=false;authScreen();}});'''
s='\n'.join(lines)+'\n'
s=s.replace("if(c==='google')return login();", "if(c==='google')return login();if(c==='reset-login')return resetLogin();")
s=s.replace('client.auth.signOut()',"client.auth.signOut({scope:'local'})")
assert "prompt:'select_account'" in s and "data-cmd=\"reset-login\"" in s
p.write_text(s)
index=root/'site/index.html'
text=index.read_text()
assert 'workspace.js?v=3' in text
index.write_text(text.replace('workspace.js?v=3','workspace.js?v=20261025-auth1'))
print('Explicit Google account selection, scoped sign-in recovery and single-flight login applied.')
