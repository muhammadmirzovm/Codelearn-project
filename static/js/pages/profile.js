/* ═══════════════════════════════════════════════════════════════
   profile.js — Chat (group_detail), Groups, Profile
   ═══════════════════════════════════════════════════════════════ */

/* ══════════════════════════════════════════════════════════════
   SHARED — unread chat badge update
   ══════════════════════════════════════════════════════════════ */
document.addEventListener('DOMContentLoaded', () => {
  const unreadEl = document.getElementById('unread-counts-data');
  if (unreadEl) {
    try {
      const counts = JSON.parse(unreadEl.textContent);
      document.querySelectorAll('.chat-unread-badge[data-group]').forEach(el => {
        const cnt = counts[parseInt(el.dataset.group)];
        if (cnt) { el.textContent = cnt; el.style.display = 'inline-flex'; }
      });
    } catch (_) {}
  }

  /* ── Bootstrap the chat page if config exists ── */
  const chatConfigEl = document.getElementById('chat-config');
  if (chatConfigEl) initChat(JSON.parse(chatConfigEl.textContent));
});

/* ══════════════════════════════════════════════════════════════
   CHAT PAGE
   ══════════════════════════════════════════════════════════════ */

function initChat(cfg) {
  const {
    groupId,
    currentUser,
    teacherUsername,
    allMembers,
    wsScheme,
    i18n,
    previousMessages,
  } = cfg;

  /* ── DOM refs ──────────────────────────────────────────────── */
  const msgsDiv       = document.getElementById('chat-messages');
  const input         = document.getElementById('chat-input');
  const sendBtn       = document.getElementById('send-btn');
  const connBadge     = document.getElementById('conn-badge');
  const connText      = document.getElementById('conn-text');
  const typingBar     = document.getElementById('typing-bar');
  const typingText    = document.getElementById('typing-text');
  const onlineList    = document.getElementById('online-list');
  const offlineList   = document.getElementById('offline-list');
  const onlineCount   = document.getElementById('online-count');
  const offlineCount  = document.getElementById('offline-count');
  const mOnlineList   = document.getElementById('m-online-list');
  const mOfflineList  = document.getElementById('m-offline-list');
  const mOnlineCount  = document.getElementById('m-online-count');
  const mOfflineCount = document.getElementById('m-offline-count');

  /* ── Helpers ───────────────────────────────────────────────── */
  const AC = ['ac-0','ac-1','ac-2','ac-3','ac-4','ac-5','ac-6','ac-7'];
  function ac(u) {
    let h = 0;
    for (const c of u) h = (h * 31 + c.charCodeAt(0)) & 0xffff;
    return AC[h % AC.length];
  }
  function esc(s) {
    return String(s)
      .replace(/&/g,'&amp;').replace(/</g,'&lt;')
      .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }
  function nowFull() {
    const d = new Date();
    const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
    return `${d.getDate()} ${months[d.getMonth()]} ${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}`;
  }
  function scrollBottom() { msgsDiv.scrollTop = msgsDiv.scrollHeight; }

  /* ── Connection state ──────────────────────────────────────── */
  function setConnected(state) {
    connBadge.className  = 'conn-badge ' + (state === 'on' ? 'connected' : 'disconnected');
    connText.textContent = state === 'on' ? i18n.connected : i18n.disconnected;
    input.disabled       = state !== 'on';
    sendBtn.disabled     = state !== 'on';
  }

  /* ── Member rendering ──────────────────────────────────────── */
  function buildMemberHTML(m, isOnline) {
    const color = ac(m.username);
    const isYou = m.username === currentUser;
    return `<div class="member-item">
      <div class="member-avatar ${color}">${esc(m.username[0].toUpperCase())}<div class="sdot ${isOnline ? 'online' : 'offline'}"></div></div>
      <div class="member-name ${isOnline ? 'online' : 'offline'}">${esc(m.displayName)}</div>
      ${isYou  ? `<span class="you-tag">${i18n.you}</span>`     : ''}
      ${m.isAdmin ? `<span class="admin-tag">${i18n.admin}</span>` : ''}
    </div>`;
  }

  function renderMembers(onlineUsers) {
    const s = new Set(onlineUsers);
    let onlineHTML = '', offlineHTML = '', o = 0, f = 0;
    allMembers.forEach(m => {
      if (s.has(m.username)) { onlineHTML  += buildMemberHTML(m, true);  o++; }
      else                   { offlineHTML += buildMemberHTML(m, false); f++; }
    });
    onlineList.innerHTML   = onlineHTML;
    offlineList.innerHTML  = offlineHTML;
    mOnlineList.innerHTML  = onlineHTML;
    mOfflineList.innerHTML = offlineHTML;
    onlineCount.textContent  = o; mOnlineCount.textContent  = o;
    offlineCount.textContent = f; mOfflineCount.textContent = f;
  }

  /* ── Message rendering ─────────────────────────────────────── */
  let lastSender = null;
  function appendMessage(sender, message, timeStr, isSelf) {
    const empty = msgsDiv.querySelector('.chat-empty');
    if (empty) empty.remove();

    const color   = ac(sender);
    const isFirst = sender !== lastSender;
    lastSender    = sender;

    const row = document.createElement('div');
    row.className = 'msg-row' + (isSelf ? ' self' : '');

    if (isSelf) {
      row.innerHTML = `
        <div class="bubble-wrap">
          <div class="bubble self">${esc(message)}</div>
          <div class="bubble-time">${esc(timeStr)}</div>
        </div>
        <div class="msg-avatar ${color} ${isFirst ? '' : 'hidden'}">${esc(sender[0].toUpperCase())}</div>`;
    } else {
      row.innerHTML = `
        <div class="msg-avatar ${color} ${isFirst ? '' : 'hidden'}">${esc(sender[0].toUpperCase())}</div>
        <div class="bubble-wrap">
          ${isFirst ? `<div class="sender-name">${esc(sender)}${sender === teacherUsername ? ` <span class="admin-tag">${i18n.admin}</span>` : ''}</div>` : ''}
          <div class="bubble other">${esc(message)}</div>
          <div class="bubble-time">${esc(timeStr)}</div>
        </div>`;
    }
    msgsDiv.appendChild(row);
    scrollBottom();
  }

  /* Render any existing messages passed from the template */
  if (Array.isArray(previousMessages)) {
    previousMessages.forEach(m => {
      appendMessage(m.sender, m.message, m.time, m.sender === currentUser);
    });
  }
  scrollBottom();

  /* ── Typing indicator ──────────────────────────────────────── */
  let typingTimer = null, isTyping = false;
  function sendTyping(state) {
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify({ type: 'typing', is_typing: state }));
    }
  }

  input.addEventListener('input', () => {
    autoResize();
    if (!isTyping) { isTyping = true; sendTyping(true); }
    clearTimeout(typingTimer);
    typingTimer = setTimeout(() => { isTyping = false; sendTyping(false); }, 1500);
  });

  function autoResize() {
    input.style.height = 'auto';
    input.style.height = Math.min(input.scrollHeight, 120) + 'px';
  }

  /* ── WebSocket ─────────────────────────────────────────────── */
  let socket;
  function connect() {
    setConnected('off');
    socket = new WebSocket(`${wsScheme}://${location.host}/ws/chat/${groupId}/`);

    socket.onopen = () => {
      setConnected('on');
      if (typeof window.updateChatBadge === 'function') {
        window.updateChatBadge(groupId, 0);
      }
    };

    socket.onclose = () => { setConnected('off'); renderMembers([]); setTimeout(connect, 3000); };
    socket.onerror = () => socket.close();

    socket.onmessage = e => {
      const data = JSON.parse(e.data);
      if (data.type === 'chat_message') {
        appendMessage(data.sender, data.message, data.time || nowFull(), data.sender === currentUser);
      }
      if (data.type === 'online_users') renderMembers(data.users);
      if (data.type === 'typing' && data.sender !== currentUser) {
        if (data.is_typing) {
          typingText.textContent = `${data.sender} ${i18n.isTyping}`;
          typingBar.style.display = 'flex';
        } else {
          typingBar.style.display = 'none';
        }
      }
    };
  }
  connect();

  /* ── Send message ──────────────────────────────────────────── */
  function sendMessage() {
    const msg = input.value.trim();
    if (!msg || !socket || socket.readyState !== WebSocket.OPEN) return;
    socket.send(JSON.stringify({ type: 'chat_message', message: msg }));
    input.value = '';
    input.style.height = 'auto';
    isTyping = false;
    clearTimeout(typingTimer);
    sendTyping(false);
  }

  sendBtn.addEventListener('click', sendMessage);
  input.addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
  });

  /* ── Mobile members drawer ─────────────────────────────────── */
  const membersBtn     = document.getElementById('members-btn');
  const membersDrawer  = document.getElementById('members-drawer');
  const membersOverlay = document.getElementById('members-overlay');
  const membersClose   = document.getElementById('members-drawer-close');

  function openMembers()  {
    membersDrawer?.classList.add('open');
    membersOverlay?.classList.add('open');
    document.body.style.overflow = 'hidden';
  }
  function closeMembers() {
    membersDrawer?.classList.remove('open');
    membersOverlay?.classList.remove('open');
    document.body.style.overflow = '';
  }

  membersBtn?.addEventListener('click',     openMembers);
  membersClose?.addEventListener('click',   closeMembers);
  membersOverlay?.addEventListener('click', closeMembers);
  document.addEventListener('keydown', e => { if (e.key === 'Escape') closeMembers(); });
}