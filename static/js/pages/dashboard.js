/* ═══════════════════════════════════════════════════════════════
   dashboard.js — Student & Teacher Dashboard
   ═══════════════════════════════════════════════════════════════ */

/* ── Unread chat badges (shared by both dashboards) ──────────── */
document.addEventListener('DOMContentLoaded', () => {
  const unreadEl = document.getElementById('unread-counts-data');
  if (!unreadEl) return;

  try {
    const unreadCounts = JSON.parse(unreadEl.textContent);
    document.querySelectorAll('.chat-unread-badge[data-group]').forEach(el => {
      const cnt = unreadCounts[parseInt(el.dataset.group)];
      if (cnt) { el.textContent = cnt; el.style.display = 'inline-flex'; }
    });
  } catch (_) {}
});

/* ══════════════════════════════════════════════════════════════
   STUDENT DASHBOARD ONLY
   (functions below are no-ops on teacher dashboard)
   ══════════════════════════════════════════════════════════════ */

/* ── Toast helper ────────────────────────────────────────────── */
let _toastTimer = null;
function showToast(msg, type) {
  const el = document.getElementById('toast-el');
  if (!el) return;
  el.textContent = msg;
  el.className   = `toast-msg toast-${type} show`;
  clearTimeout(_toastTimer);
  _toastTimer = setTimeout(() => el.classList.remove('show'), 4000);
}

/* ── Session grid helpers ────────────────────────────────────── */
function getGrid() { return document.getElementById('sessions-grid'); }

/**
 * If the "no active sessions" card is shown, replace it with
 * the active sessions banner and an empty grid.
 */
function ensureActiveBanner(i18n) {
  const noCard = document.getElementById('no-sessions-card');
  if (!noCard) return;

  document.getElementById('active-sessions-wrap').innerHTML = `
    <div id="active-sessions-inner" class="active-sessions-banner">
      <div class="active-sessions-header">
        <span class="live-dot pulse"></span>
        <span class="active-sessions-title">${i18n.activeSessions}</span>
      </div>
      <div id="sessions-grid" class="sessions-grid"></div>
    </div>`;
}

/**
 * Build and append a session card to the grid.
 */
function addSessionCard(data, i18n) {
  ensureActiveBanner(i18n);
  const grid = getGrid();
  if (!grid || document.getElementById(`session-card-${data.session_pk}`)) return;

  const card      = document.createElement('div');
  card.id         = `session-card-${data.session_pk}`;
  card.className  = 'session-card session-card-enter';
  card.dataset.sessionPk = data.session_pk;

  if (data.duration_minutes && data.activated_at) {
    const endMs = new Date(data.activated_at).getTime() + data.duration_minutes * 60000;
    card.dataset.sessionEnd = new Date(endMs).toISOString();
  }

  const typeLabel = data.session_type === 'quiz' ? '🧪 Quiz' : '⚡ Algorithmic';
  const duration  = data.duration_minutes
    ? `<span class="session-card-duration">⏱ ${data.duration_minutes} min</span>`
    : '';

  card.innerHTML = `
    <div class="session-card-top">
      <span class="session-card-type">${typeLabel}</span>
      ${duration}
    </div>
    <p class="session-card-title">${data.title}</p>
    <p class="session-card-group">${data.group_name}</p>
    <div class="session-card-actions">
      <a href="${data.join_url}" class="btn btn-success btn-sm" style="flex:1;justify-content:center;">▶ ${i18n.enter}</a>
      <a href="${data.leaderboard_url}" class="btn btn-ghost btn-sm">🏆</a>
    </div>`;

  grid.appendChild(card);
}

/**
 * Fade out and remove a session card.
 * If grid becomes empty, show the "no sessions" placeholder.
 */
function removeSessionCard(sessionPk, i18n) {
  const card = document.getElementById(`session-card-${sessionPk}`);
  if (!card) return;

  card.style.transition = 'opacity .3s, transform .3s';
  card.style.opacity    = '0';
  card.style.transform  = 'scale(.95)';

  setTimeout(() => {
    card.remove();
    const grid = getGrid();
    if (grid && grid.children.length === 0) {
      document.getElementById('active-sessions-wrap').innerHTML = `
        <div id="no-sessions-card" class="card card-p no-sessions-card">
          <p class="no-sessions-emoji">😴</p>
          <p class="no-sessions-title">${i18n.noSessions}</p>
          <p class="no-sessions-sub">${i18n.noSessionsSub}</p>
        </div>`;
    }
  }, 300);
}

/* ── Session timer checker (runs every 5 s) ──────────────────── */
function checkSessionTimers(i18n) {
  document.querySelectorAll('[data-session-end]').forEach(card => {
    if (Date.now() >= new Date(card.dataset.sessionEnd).getTime()) {
      removeSessionCard(parseInt(card.dataset.sessionPk), i18n);
    }
  });
}

/* ── WebSocket per group ─────────────────────────────────────── */
function connectGroupWS(groupPk, i18n) {
  const proto = location.protocol === 'https:' ? 'wss' : 'ws';
  const ws    = new WebSocket(`${proto}://${location.host}/ws/group/${groupPk}/session/`);

  ws.onclose = () => setTimeout(() => connectGroupWS(groupPk, i18n), 3000);
  ws.onerror = e  => console.warn(`[WS group ${groupPk}]`, e);

  ws.onmessage = e => {
    const msg = JSON.parse(e.data);
    if (msg.event === 'session_started') {
      addSessionCard(msg.data, i18n);
      showToast(`🚀 ${i18n.newSession} ${msg.data.title}`, 's');
    } else if (msg.event === 'session_ended') {
      removeSessionCard(msg.data.session_pk, i18n);
      showToast(i18n.sessionEnded, 'w');
    }
  };
}

/* ── Bootstrap student dashboard ─────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  const configEl = document.getElementById('dashboard-config');
  if (!configEl) return;  /* not student dashboard, stop here */

  const config   = JSON.parse(configEl.textContent);
  const { groupPks, i18n } = config;

  /* Start session timer polling */
  setInterval(() => checkSessionTimers(i18n), 5000);

  /* Connect a WebSocket for each group */
  groupPks.forEach(pk => connectGroupWS(pk, i18n));
});