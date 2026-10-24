/** Install on the ISOC Google account. Secrets belong in Script Properties, not source.
 * Required: HUB_API_URL, EMAIL_AGENT_SECRET. Media import also needs MEDIA_IMPORT_SECRET,
 * MEDIA_FORM_ID, and MEDIA_DEADLINE_QUESTION (exact title of the existing deadline question).
 * No emails are sent until installEmailAgent is run and EMAIL_ENABLED is enabled on the backend.
 */
function hubRequest_(action, payload, secretName) {
  const p = PropertiesService.getScriptProperties();
  const endpoint = p.getProperty('HUB_API_URL');
  const secret = p.getProperty(secretName);
  if (!endpoint || !/^https:\/\/[a-z0-9-]+\.supabase\.co\/functions\/v1\/committee-api$/.test(endpoint) || !secret || secret.length < 32) throw new Error('Configure the hub URL and private agent secret first.');
  const response = UrlFetchApp.fetch(endpoint, {method:'post', contentType:'application/json', headers:{[secretName === 'EMAIL_AGENT_SECRET' ? 'x-email-secret' : 'x-media-secret']:secret}, payload:JSON.stringify(Object.assign({action:action},payload)), muteHttpExceptions:true});
  if (response.getResponseCode() !== 200) throw new Error('Hub agent request failed: HTTP ' + response.getResponseCode());
  return JSON.parse(response.getContentText());
}
function installEmailAgent() {
  // Review this function, set properties, and authorise as the ISOC sender account once.
  const p=PropertiesService.getScriptProperties();
  if(!p.getProperty('HUB_API_URL')||!p.getProperty('EMAIL_AGENT_SECRET'))throw new Error('Set the Script Properties first.');
  ScriptApp.getProjectTriggers().filter(t=>t.getHandlerFunction()==='dispatchCommitteeMail').forEach(t=>ScriptApp.deleteTrigger(t));
  ScriptApp.newTrigger('dispatchCommitteeMail').timeBased().everyMinutes(5).create();
  MailApp.getRemainingDailyQuota();
  console.log('Email worker installed. Enable EMAIL_ENABLED only after the owner-only test.');
}
function dispatchCommitteeMail() {
  const lock=LockService.getScriptLock();if(!lock.tryLock(1000))return;
  try {
    const capacity=Math.min(10,MailApp.getRemainingDailyQuota());if(capacity<1)return;
    const result=hubRequest_('mailClaim',{limit:capacity},'EMAIL_AGENT_SECRET');
    for(const job of result.jobs||[]) {
      let sent=false;
      try {MailApp.sendEmail({to:job.to,subject:job.subject,body:job.body,name:'Swansea ISOC'});sent=true;}
      catch(e){console.error('Mail send needs review for job '+job.id);}
      // Do not resend when acknowledgement fails. A sent-but-unacknowledged job needs manual review.
      let acknowledged=false;
      for(let attempt=0;attempt<3&&!acknowledged;attempt++){
        try {acknowledged=hubRequest_('mailAck',{id:job.id,lease:job.lease,sent:sent},'EMAIL_AGENT_SECRET').acknowledged;}
        catch(e){if(attempt<2)Utilities.sleep(500);}
      }
      if(!acknowledged)console.error('Check the sender mailbox before retrying job '+job.id);
    }
  } finally {lock.releaseLock();}
}
function installMediaImport() {
  const p=PropertiesService.getScriptProperties(),fid=p.getProperty('MEDIA_FORM_ID');
  if(!fid||!p.getProperty('MEDIA_IMPORT_SECRET')||!p.getProperty('MEDIA_DEADLINE_QUESTION'))throw new Error('Set MEDIA_FORM_ID, MEDIA_IMPORT_SECRET and MEDIA_DEADLINE_QUESTION first.');
  const form=FormApp.openById(fid); // Do not recreate or change the original form or its spreadsheet.
  ScriptApp.getProjectTriggers().filter(t=>t.getHandlerFunction()==='importMediaResponse').forEach(t=>ScriptApp.deleteTrigger(t));
  ScriptApp.newTrigger('importMediaResponse').forForm(form).onFormSubmit().create();
}
function importMediaResponse(e) {
  if(!e||!e.response)throw new Error('Run from the form submission trigger, not manually.');
  const p=PropertiesService.getScriptProperties(),values={};
  e.response.getItemResponses().forEach(r=>values[r.getItem().getTitle()]=r.getResponse());
  const value=t=>Array.isArray(values[t])?values[t].join(', '):String(values[t]||'');
  const deadline=values[p.getProperty('MEDIA_DEADLINE_QUESTION')];
  // Apps Script date-item responses can be Date objects or locale-formatted strings. Require an
  // ISO yyyy-MM-dd string or Date; never guess UK dates as US dates or silently invent a deadline.
  let due;
  if(deadline instanceof Date && !isNaN(deadline.getTime()))due=deadline;
  else if(/^\d{4}-\d{2}-\d{2}$/.test(String(deadline)))due=Utilities.parseDate(String(deadline)+' 17:00','Europe/London','yyyy-MM-dd HH:mm');
  else throw new Error('Deadline is not an unambiguous Date/ISO value. Configure the exact deadline mapping before enabling import.');
  const titleKey=p.getProperty('MEDIA_TITLE_QUESTION')||'Event / project name';
  const nameKey=p.getProperty('MEDIA_NAME_QUESTION')||'Requested by (name + role)';
  const teamKey=p.getProperty('MEDIA_TEAM_QUESTION')||'Subcommittee';
  const formatKey=p.getProperty('MEDIA_FORMAT_QUESTION')||'Type of media needed';
  const brief=e.response.getItemResponses().map(r=>r.getItem().getTitle()+': '+(Array.isArray(r.getResponse())?r.getResponse().join(', '):String(r.getResponse()))).join('\n\n');
  return hubRequest_('mediaImport',{request:{source_id:e.response.getId(),requester_name:value(nameKey),title:value(titleKey),team:value(teamKey),format:value(formatKey),brief:brief.slice(0,6000),needed_by:due.toISOString()}},'MEDIA_IMPORT_SECRET');
}
