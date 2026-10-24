/* PUBLIC connection details only. Never add a password, email allowlist, service key or private record here.
   Set these once the dedicated private backend and Google provider have been configured. */
window.HUB_CONFIG = Object.freeze({
  supabaseUrl: '',
  supabasePublishableKey: '',
  apiFunction: 'committee-api',
  redirectUrl: 'https://swansea-isoc.github.io/committee-hub/',
  edition: '2026 / 27'
});
