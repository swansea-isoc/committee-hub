/* Public settings only. Real committee data, emails and private URLs belong in the server database.
   live: fail-closed unless Google auth and the hub API are configured.
   demo.html: a separate sample-only interface, never a security gate. */
window.HUB_CONFIG = Object.freeze({
  mode: 'live',
  supabaseUrl: '',
  supabasePublishableKey: '',
  apiFunction: 'hub-api',
  redirectUrl: '',
  edition: '2026 / 27'
});
