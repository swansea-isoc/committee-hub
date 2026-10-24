import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import {readFileSync} from 'node:fs';
const source=readFileSync(new URL('../site/workspace.js',import.meta.url),'utf8');
const auth=source.slice(source.indexOf('function clearAuthLocation(){'),source.indexOf('function go(v)'));
assert.ok(auth.length>1000,'Run the sign-in patch before testing');
const base='https://unit.supabase.co';
const home='https://swansea-isoc.github.io/committee-hub/';
function store(){const data=new Map();return {setItem:(k,v)=>data.set(k,String(v)),getItem:k=>data.get(k)??null,removeItem:k=>data.delete(k)};}
function setup(overrides={}){
 const events=[],localStorage=store(),sessionStorage=store();
 const context={URL,URLSearchParams,setTimeout,clearTimeout,Promise,Error,authReady:true,signingIn:false,
  cfg:{supabaseUrl:base,redirectUrl:home},localStorage,sessionStorage,
  location:{href:home,search:'',hash:'',assign:v=>events.push(['navigate',v]),replace:v=>events.push(['replace',v])},
  history:{state:null,replaceState:(_,__,u)=>events.push(['clean-url',u])},
  authScreen:m=>events.push(['screen',m]),
  client:{auth:{signInWithOAuth:async p=>{events.push(['oauth',p]);return {data:{url:base+'/auth/v1/authorize?provider=google'},error:null};},signOut:async p=>{events.push(['signout',p]);return {error:null};}}},
  ...overrides};
 vm.createContext(context);vm.runInContext(auth,context);return {context,events,localStorage,sessionStorage};
}
test('New sign-in asks Google to select an account, uses canonical callback and keeps PKCE in the SDK',async()=>{
 const {context:c,events}=setup();await c.login();const options=events.find(x=>x[0]==='oauth')[1];
 assert.equal(options.provider,'google');assert.equal(options.options.queryParams.prompt,'select_account');
 assert.equal(options.options.redirectTo,home);assert.equal(options.options.skipBrowserRedirect,true);
 assert.equal('state' in options.options.queryParams,false);assert.equal(events.filter(x=>x[0]==='navigate').length,1);
});
test('Repeated taps start only one OAuth request',async()=>{
 const {context:c,events}=setup();let finish;
 c.client.auth.signInWithOAuth=p=>{events.push(['oauth',p]);return new Promise(resolve=>{finish=resolve;});};
 const first=c.login();await c.login();assert.equal(events.filter(x=>x[0]==='oauth').length,1);
 finish({data:{url:base+'/auth/v1/authorize'},error:null});await first;
});
test('Login waits for saved-session restoration rather than racing it',async()=>{
 const {context:c,events}=setup({authReady:false});await c.login();assert.equal(events.length,0);
});
test('An OAuth start error restores the login controls without leaking provider details',async()=>{
 const {context:c,events}=setup();c.client.auth.signInWithOAuth=async()=>({error:new Error('secret-like-detail')});await c.login();
 assert.equal(c.signingIn,false);assert.equal(events.some(x=>x[0]==='navigate'),false);
 assert.equal(events.at(-1)[1].includes('secret-like-detail'),false);
});
test('Untrusted navigation target is rejected',async()=>{
 const {context:c,events}=setup();c.client.auth.signInWithOAuth=async()=>({data:{url:'https://example.test/'}});await c.login();
 assert.equal(events.some(x=>x[0]==='navigate'),false);assert.equal(c.signingIn,false);
});
test('Restart clears only this hub session and verifier, preserving unrelated data',async()=>{
 const {context:c,events,localStorage:l,sessionStorage:s}=setup();
 for(const st of [l,s])for(const [k,v] of [['sb-unit-auth-token','old'],['sb-unit-auth-token-code-verifier','old'],['sb-unit-auth-token-user','old'],['other-site-setting','keep'],['sb-other-auth-token','keep']])st.setItem(k,v);
 await c.resetLogin();assert.equal(events.find(x=>x[0]==='signout')[1].scope,'local');
 for(const st of [l,s]){assert.equal(st.getItem('sb-unit-auth-token'),null);assert.equal(st.getItem('sb-unit-auth-token-code-verifier'),null);assert.equal(st.getItem('other-site-setting'),'keep');assert.equal(st.getItem('sb-other-auth-token'),'keep');}
 assert.equal(events.at(-1)[0],'replace');assert.equal(events.at(-1)[1],home);
});
test('Reset is not blocked by a stale session that fails to revoke',async()=>{
 const {context:c,events}=setup();c.client.auth.signOut=async()=>{throw new Error('stale session');};await c.resetLogin();
 assert.equal(events.at(-1)[0],'replace');
});
test('Blocked browser storage prevents an unrecoverable PKCE redirect',async()=>{
 const {context:c,events}=setup();c.localStorage.setItem=()=>{throw new Error('blocked');};await c.login();
 assert.equal(events.some(x=>x[0]==='oauth'),false);assert.equal(c.signingIn,false);
 assert.match(events.at(-1)[1],/Allow this site/);
});
test('OAuth URL cleanup preserves unrelated query parameters and workspace route',()=>{
 const {context:c,events}=setup();c.location.href=home+'?code=discard&error_description=discard&source=bookmark#actions';c.clearAuthLocation();
 assert.equal(events.at(-1)[1],'/committee-hub/?source=bookmark#actions');
});
test('Callback errors are understandable and never reflect arbitrary provider text',()=>{
 const {context:c}=setup();c.location.search='?error=access_denied&error_description=sensitive';
 assert.equal(c.callbackError(),'access_denied');assert.match(c.signinMessage(c.callbackError()),/cancelled/);
 assert.equal(c.signinMessage({code:'sensitive'}).includes('sensitive'),false);
});
test('Every application sign-out is local and remembered sessions remain enabled',()=>{
 assert.equal(source.includes('client.auth.signOut()'),false);
 assert.ok(source.includes("persistSession:true"));assert.ok(source.includes("autoRefreshToken:true"));assert.ok(source.includes("flowType:'pkce'"));
 assert.ok(source.includes("window.addEventListener('pageshow'"));
});
