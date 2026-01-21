const BASE = '';
let chatVisible = false;

async function postJSON(path, body){
  try{
    const sid = localStorage.getItem('greenie-session') || ('sid-'+Math.random().toString(36).slice(2,10));
    localStorage.setItem('greenie-session', sid);
    if(typeof body === 'object') body.session_id = sid;
    if(typeof body === 'object') body.conversation_mode = true;
    if(typeof body === 'object') body.fast = true;
  }catch(e){}
  const res = await fetch(path, {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body)});
  return res.json();
}

function appendMsg(role, text){
  const log = document.getElementById('chat-log');
  if(!log) return;
  const div = document.createElement('div');
  div.className = `msg ${role}`;
  div.textContent = text;
  log.appendChild(div);
  log.scrollTop = log.scrollHeight;
}

function showChat(){
  const c = document.getElementById('chat-container');
  if(c){ c.style.display = 'flex'; chatVisible = true; }
  const inp = document.getElementById('chat-input');
  if(inp) inp.focus();
}

function hideChat(){
  const c = document.getElementById('chat-container');
  if(c){ c.style.display = 'none'; chatVisible = false; }
}

async function sendMessage(){
  const inp = document.getElementById('chat-input');
  if(!inp) return;
  const msg = inp.value.trim();
  if(!msg) return;
  inp.value = '';
  appendMsg('user', msg);
  try{
    const res = await postJSON('/chat', { message: msg, save: false, include_knowledge: true });
    if(res && res.reply){
      appendMsg('assistant', res.reply);
      // Log uncertainty if reply is vague
      if(/not sure|don't know|unclear|uncertain/i.test(res.reply)){
        await fetch('/log_uncertainty', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({user_message: msg, reply: res.reply, ts: Date.now()})}).catch(()=>{});
      }
    } else if(res && res.error){
      appendMsg('assistant', res.message || 'Hmm, ran into a hiccup.');
    }
  }catch(e){
    appendMsg('assistant', 'Connection issue. Is the server running?');
  }
}

function toggleSettings(){
  const s = document.getElementById('settings-panel');
  if(!s) return;
  s.hidden = !s.hidden;
}

function applyPosition(pos){
  const agent = document.getElementById('agent');
  const chat = document.getElementById('chat-container');
  if(!agent) return;
  agent.style.removeProperty('top'); agent.style.removeProperty('bottom'); agent.style.removeProperty('left'); agent.style.removeProperty('right');
  if(chat){ chat.style.removeProperty('top'); chat.style.removeProperty('bottom'); chat.style.removeProperty('left'); chat.style.removeProperty('right'); }
  if(pos === 'bottom-right'){
    agent.style.bottom = '8px'; agent.style.right = '8px';
    if(chat){ chat.style.bottom = '160px'; chat.style.right = '8px'; }
  } else if(pos === 'bottom-left'){
    agent.style.bottom = '8px'; agent.style.left = '8px';
    if(chat){ chat.style.bottom = '160px'; chat.style.left = '8px'; }
  } else if(pos === 'top-right'){
    agent.style.top = '8px'; agent.style.right = '8px';
    if(chat){ chat.style.top = '160px'; chat.style.right = '8px'; }
  } else if(pos === 'top-left'){
    agent.style.top = '8px'; agent.style.left = '8px';
    if(chat){ chat.style.top = '160px'; chat.style.left = '8px'; }
  }
  try{ localStorage.setItem('greenie-position', pos); }catch(e){}
}

function wireControls(){
  const agent = document.getElementById('agent');
  if(agent){ agent.addEventListener('click', ()=>{ if(!chatVisible) showChat(); }); }
  const sendBtn = document.getElementById('send-btn');
  if(sendBtn){ sendBtn.addEventListener('click', sendMessage); }
  const chatInput = document.getElementById('chat-input');
  if(chatInput){ chatInput.addEventListener('keypress', (e)=>{ if(e.key === 'Enter') sendMessage(); }); }
  const closeChat = document.getElementById('close-chat');
  if(closeChat){ closeChat.addEventListener('click', hideChat); }
  const settingsBtn = document.getElementById('settings-btn');
  if(settingsBtn){ settingsBtn.addEventListener('click', toggleSettings); }
  const closeSettings = document.getElementById('close-settings');
  if(closeSettings){ closeSettings.addEventListener('click', ()=>{ const s = document.getElementById('settings-panel'); if(s) s.hidden = true; }); }
  const hideBtn = document.getElementById('hide-btn');
  if(hideBtn){ hideBtn.addEventListener('click', ()=>{ if(window.pywebview) window.pywebview.api.hide_window(); }); }
  const posSelect = document.getElementById('position-select');
  if(posSelect){
    const saved = localStorage.getItem('greenie-position') || 'bottom-right';
    posSelect.value = saved;
    applyPosition(saved);
    posSelect.addEventListener('change', (e)=>{ applyPosition(e.target.value); });
  }
}

async function welcome(){
  try{
    const r = await fetch('/welcome');
    const j = await r.json();
    if(j && j.message){ appendMsg('assistant', j.message); }
  }catch(e){ /* ignore */ }
}

window.addEventListener('load', ()=>{
  wireControls();
  welcome();
});
