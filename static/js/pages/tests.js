/* ═══════════════════════════════════════════════════════════════
   tests.js — Question Manager, Test Join, Monitor, Results
   ═══════════════════════════════════════════════════════════════ */

/* ══════════════════════════════════════════════════════════════
   SHARED HELPERS
   ══════════════════════════════════════════════════════════════ */

function escHtml(str) {
  return String(str || '')
    .replace(/&/g,'&amp;').replace(/</g,'&lt;')
    .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

let _toastTimer = null;
function _toast(msg, type) {
  const el = document.getElementById('toast-el');
  if (!el) return;
  el.textContent = msg;
  el.className   = `toast-msg toast-${type} show`;
  clearTimeout(_toastTimer);
  _toastTimer = setTimeout(() => el.classList.remove('show'), 3000);
}

/* ══════════════════════════════════════════════════════════════
   QUESTION MANAGER  (question_manage.html)
   ══════════════════════════════════════════════════════════════ */

let questions = [];

function initQuestionManager() {
  const cfgEl = document.getElementById('question-manager-config');
  if (!cfgEl) return;
  const cfg = JSON.parse(cfgEl.textContent);

  try {
    const data = JSON.parse(document.getElementById('existing-data').textContent);
    questions = data.length > 0
      ? data.map(q => ({ text: q.text, choices: q.choices.map(c => ({ ...c })) }))
      : [];
  } catch(e) { questions = []; }

  if (questions.length === 0) addQuestion(cfg);
  else render(cfg);
}

function addQuestion(cfg) {
  questions.push({
    text: '',
    choices: [
      { label: 'A', text: '', is_correct: false },
      { label: 'B', text: '', is_correct: false },
      { label: 'C', text: '', is_correct: false },
      { label: 'D', text: '', is_correct: false },
    ]
  });
  const cfg2 = cfg || JSON.parse(document.getElementById('question-manager-config').textContent);
  render(cfg2);
  document.getElementById('q-count').textContent = questions.length;
  setTimeout(() => {
    const inputs = document.querySelectorAll('.q-text-input');
    inputs[inputs.length - 1]?.focus();
  }, 50);
}

function removeQuestion(idx) {
  if (questions.length === 1) return;
  questions.splice(idx, 1);
  const cfg = JSON.parse(document.getElementById('question-manager-config').textContent);
  render(cfg);
  document.getElementById('q-count').textContent = questions.length;
}

function setCorrect(qIdx, cIdx) {
  questions[qIdx].choices.forEach((c, i) => c.is_correct = i === cIdx);
  const cfg = JSON.parse(document.getElementById('question-manager-config').textContent);
  render(cfg);
}

function render(cfg) {
  const wrap = document.getElementById('questions-wrap');
  wrap.innerHTML = questions.map((q, qi) => `
    <div class="q-card">
      <div class="q-header">
        <div class="q-num">${qi + 1}</div>
        <span style="flex:1;font-weight:600;font-size:.88rem;">${cfg.i18n.question} ${qi + 1}</span>
        ${questions.length > 1
          ? `<button onclick="removeQuestion(${qi})" style="background:none;border:none;color:var(--danger);cursor:pointer;font-size:.82rem;padding:4px 8px;">✕ ${cfg.i18n.remove}</button>`
          : ''}
      </div>
      <div class="q-body">
        <textarea class="q-input q-text-input" placeholder="${cfg.i18n.questionPlaceholder}" rows="2"
          oninput="questions[${qi}].text=this.value">${escHtml(q.text)}</textarea>
        <div style="margin-top:12px;">
          ${q.choices.map((c, ci) => `
            <div class="choice-row">
              <div class="choice-label ${c.is_correct ? 'correct' : ''}">${c.label}</div>
              <input class="q-input" type="text" placeholder="${c.label} ${cfg.i18n.choicePlaceholder}" value="${escHtml(c.text)}"
                oninput="questions[${qi}].choices[${ci}].text=this.value">
              <button class="choice-correct-btn ${c.is_correct ? 'active' : ''}"
                onclick="setCorrect(${qi}, ${ci})">
                ${c.is_correct ? `✓ ${cfg.i18n.correct}` : cfg.i18n.markCorrect}
              </button>
            </div>
          `).join('')}
        </div>
      </div>
    </div>
  `).join('');
}

async function saveAll() {
  const cfg = JSON.parse(document.getElementById('question-manager-config').textContent);
  const btn = document.getElementById('save-btn');

  for (let i = 0; i < questions.length; i++) {
    if (!questions[i].text.trim()) {
      alert(`${cfg.i18n.question} ${i + 1}: ${cfg.i18n.emptyText}`); return;
    }
    if (!questions[i].choices.some(c => c.is_correct)) {
      alert(`${cfg.i18n.question} ${i + 1}: ${cfg.i18n.noCorrect}`); return;
    }
  }

  btn.textContent = `💾 ${cfg.i18n.saving}...`;
  btn.disabled    = true;

  try {
    const res = await fetch(cfg.saveUrl, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': cfg.csrfToken },
      body:    JSON.stringify({ questions }),
    });
    const d = await res.json();
    if (d.success) {
      btn.textContent      = `✅ ${cfg.i18n.saved}!`;
      btn.style.background = 'var(--success)';
      document.getElementById('q-count').textContent = questions.length;
      setTimeout(() => {
        btn.textContent      = `💾 ${cfg.i18n.save}`;
        btn.disabled         = false;
        btn.style.background = '';
      }, 2000);
    }
  } catch(e) {
    btn.textContent = `❌ ${cfg.i18n.error}!`;
    btn.disabled    = false;
  }
}

/* ══════════════════════════════════════════════════════════════
   TEST FORM  (test_form.html)
   ══════════════════════════════════════════════════════════════ */

function switchMode(mode) {
  const globalFields = document.getElementById('global-fields');
  if (!globalFields) return;
  if (mode === 'global') {
    globalFields.classList.remove('hidden');
  } else {
    globalFields.classList.add('hidden');
    const dur  = document.getElementById('id_duration_minutes');
    const coin = document.getElementById('id_coin_reward');
    if (dur)  dur.value  = '0';
    if (coin) coin.value = '0';
  }
}

/* ══════════════════════════════════════════════════════════════
   TEST JOIN (test_detail / take test)
   ══════════════════════════════════════════════════════════════ */

function initTestJoin() {
  const pdEl = document.getElementById('page-data');
  if (!pdEl) return;
  const PD = JSON.parse(pdEl.textContent);

  const TOTAL        = PD.total;
  const DURATION_SECS = PD.duration_secs * 60;
  const ACTIVATED_AT = PD.activated_at;
  const CSRF         = PD.csrfToken;
  const URL_ANSWER   = PD.urlAnswer;
  const URL_FINISH   = PD.urlFinish;
  const URL_RESULTS  = PD.urlResults;
  const i18n         = PD.i18n;

  let answeredIds  = new Set(PD.answered_ids);
  let timeExpired  = false;
  let finishing    = false;

  function updateProgress() {
    const pct = TOTAL > 0 ? (answeredIds.size / TOTAL) * 100 : 0;
    document.getElementById('progress-fill').style.width = pct + '%';
    document.getElementById('answered-count').textContent = answeredIds.size;
  }
  updateProgress();

  window.selectAnswer = async function(questionId, choiceId, btn) {
    if (timeExpired) return;
    document.querySelectorAll(`[id^="choice-${questionId}-"]`).forEach(b => b.classList.remove('selected'));
    btn.classList.add('selected');
    const card = document.getElementById(`qcard-${questionId}`);
    card.classList.add('answered');
    card.classList.remove('active');
    try {
      await fetch(URL_ANSWER, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF },
        body:    JSON.stringify({ question_id: questionId, choice_id: choiceId }),
      });
      if (!answeredIds.has(questionId)) { answeredIds.add(questionId); updateProgress(); }
    } catch(e) { _toast(i18n.connectionError, 'w'); }
  };

  window.finishTest = async function() {
    if (finishing) return;
    if (answeredIds.size < TOTAL) {
      const ok = confirm(`${TOTAL - answeredIds.size} ${i18n.unanswered}`);
      if (!ok) return;
    }
    finishing = true;
    document.querySelectorAll('#finish-btn, #finish-btn-bottom').forEach(b => b.disabled = true);
    try {
      const res = await fetch(URL_FINISH, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF },
        body:    '{}',
      });
      const d = await res.json();
      if (d.success || d.already_finished) window.location.href = URL_RESULTS;
    } catch(e) { _toast(i18n.error, 'w'); finishing = false; }
  };

  /* Countdown */
  if (DURATION_SECS && ACTIVATED_AT) {
    let expired = false;
    function updateCountdown() {
      const elapsed = (Date.now() - new Date(ACTIVATED_AT).getTime()) / 1000;
      const rem     = Math.max(0, DURATION_SECS - elapsed);
      const m = Math.floor(rem / 60), s = Math.floor(rem % 60);
      const el   = document.getElementById('countdown');
      const wrap = document.getElementById('cd-wrap');
      if (el)   el.textContent = `${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`;
      if (wrap) wrap.className = 'cd-wrap ' + (rem > 120 ? 'cd-ok' : rem > 30 ? 'cd-warn' : 'cd-crit');
      if (rem <= 0 && !expired) {
        expired = true; timeExpired = true;
        document.getElementById('time-up-overlay').classList.add('show');
        setTimeout(async () => {
          try {
            await fetch(URL_FINISH, { method:'POST', headers:{'Content-Type':'application/json','X-CSRFToken':CSRF}, body:'{}' });
          } catch(e) {}
          window.location.href = URL_RESULTS;
        }, 2000);
      }
    }
    updateCountdown();
    setInterval(updateCountdown, 500);
  }

  /* WebSocket */
  (function connectWS() {
    const proto = location.protocol === 'https:' ? 'wss' : 'ws';
    const ws = new WebSocket(`${proto}://${location.host}/ws/test/${PD.test_pk}/`);
    ws.onclose  = () => setTimeout(connectWS, 3000);
    ws.onmessage = e => {
      const msg = JSON.parse(e.data);
      if (msg.event === 'test_ended') {
        _toast(i18n.testEndedByTeacher, 'w');
        setTimeout(() => window.location.href = '/tests/', 2000);
      }
    };
  })();
}

/* ══════════════════════════════════════════════════════════════
   MONITOR  (test_monitor.html)
   ══════════════════════════════════════════════════════════════ */

function initMonitor() {
  const pdEl = document.getElementById('page-data');
  if (!pdEl) return;
  const PD = JSON.parse(pdEl.textContent);

  const TOTAL_Q       = PD.total_questions;
  const TOTAL_S       = PD.total_students;
  const DURATION_SECS = PD.duration_secs * 60;
  const ACTIVATED_AT  = PD.activated_at;

  let nFinished = 0, nActive = 0;

  function updateStats() {
    document.getElementById('s-finished').textContent = nFinished;
    document.getElementById('s-active').textContent   = nActive;
    document.getElementById('s-idle').textContent     = Math.max(0, TOTAL_S - nFinished - nActive);
  }

  function setWS(ok) {
    const dot = document.getElementById('ws-dot');
    const lbl = document.getElementById('ws-label');
    const ind = document.getElementById('ws-indicator');
    if (ok) {
      dot.style.background = 'var(--success)';
      lbl.textContent = 'Live'; lbl.style.color = 'var(--success)';
      ind.style.background = 'var(--success-bg)'; ind.style.borderColor = 'var(--success-brd)';
    } else {
      dot.style.background = 'var(--text-muted)';
      lbl.textContent = 'Connecting'; lbl.style.color = 'var(--text-muted)';
      ind.style.background = 'var(--bg2)'; ind.style.borderColor = 'var(--border)';
    }
  }

  function nowStr() { return new Date().toTimeString().slice(0, 8); }

  function flashRow(sid, color) {
    const row = document.getElementById(`row-${sid}`);
    if (row) {
      row.style.transition = 'background .15s';
      row.style.background = color;
      setTimeout(() => row.style.background = '', 1500);
    }
  }

  function updateDot(sid, order, answered) {
    const dot = document.getElementById(`dot-${sid}-${order}`);
    if (dot) {
      dot.classList.remove('current');
      if (answered) dot.classList.add('answered');
      const next = document.getElementById(`dot-${sid}-${order + 1}`);
      if (next && !next.classList.contains('answered')) next.classList.add('current');
    }
  }

  function updateProgress(sid, count) {
    const countEl = document.getElementById(`ans-count-${sid}`);
    const fillEl  = document.getElementById(`prog-fill-${sid}`);
    if (countEl) countEl.textContent = count;
    if (fillEl)  fillEl.style.width  = ((count / TOTAL_Q) * 100) + '%';
  }

  /* Countdown */
  if (DURATION_SECS && ACTIVATED_AT) {
    function updateCD() {
      const elapsed = (Date.now() - new Date(ACTIVATED_AT).getTime()) / 1000;
      const rem = Math.max(0, DURATION_SECS - elapsed);
      const m = Math.floor(rem / 60), s = Math.floor(rem % 60);
      const el   = document.getElementById('countdown');
      const wrap = document.getElementById('cd-wrap');
      if (el)   el.textContent = `${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`;
      if (wrap) wrap.className = 'cd-wrap ' + (rem > 120 ? 'cd-ok' : rem > 30 ? 'cd-warn' : 'cd-crit');
    }
    updateCD();
    setInterval(updateCD, 500);
  }

  /* WebSocket */
  function connectWS() {
    const proto = location.protocol === 'https:' ? 'wss' : 'ws';
    const ws = new WebSocket(`${proto}://${location.host}/ws/test/${PD.test_pk}/`);
    ws.onopen  = () => setWS(true);
    ws.onclose = () => { setWS(false); setTimeout(connectWS, 3000); };

    ws.onmessage = e => {
      const msg = JSON.parse(e.data);
      const d = msg.data, sid = d.student_id;

      if (msg.event === 'student_joined') {
        const status = document.getElementById(`status-${sid}`);
        const time   = document.getElementById(`time-${sid}`);
        if (status) status.innerHTML = `<span class="badge badge-active">▶ In Progress</span>`;
        if (time)   time.textContent = nowStr();
        const firstDot = document.getElementById(`dot-${sid}-1`);
        if (firstDot) firstDot.classList.add('current');
        nActive++; updateStats();
        flashRow(sid, 'rgba(13,148,136,.07)');
        _toast(`${d.full_name} joined the test`, 's');

      } else if (msg.event === 'question_answered') {
        updateProgress(sid, d.answered_count);
        if (d.question_order) updateDot(sid, d.question_order, true);
        flashRow(sid, 'rgba(13,148,136,.04)');

      } else if (msg.event === 'student_finished') {
        const status = document.getElementById(`status-${sid}`);
        const fill   = document.getElementById(`prog-fill-${sid}`);
        if (status) status.innerHTML = `<span class="badge badge-passed">✓ Finished — ${d.score}/${d.total}</span>`;
        if (fill)   { fill.style.width = '100%'; fill.classList.add('done'); }
        updateProgress(sid, d.total);
        for (let i = 1; i <= TOTAL_Q; i++) {
          const dot = document.getElementById(`dot-${sid}-${i}`);
          if (dot) { dot.classList.remove('current'); dot.classList.add('answered'); }
        }
        nActive = Math.max(0, nActive - 1); nFinished++; updateStats();
        flashRow(sid, 'rgba(5,150,105,.08)');
        _toast(`🎉 ${d.username} finished! ${d.score}/${d.total}`, 's');
      }
    };
  }
  connectWS();
}

/* ══════════════════════════════════════════════════════════════
   RESULTS  (test_results.html)
   ══════════════════════════════════════════════════════════════ */

function initResults() {
  const rankEl = document.getElementById('result-rank');
  if (!rankEl) return;
  const rank = parseInt(rankEl.dataset.rank);

  /* Animate score bars */
  setTimeout(() => {
    document.querySelectorAll('.score-bar-fill').forEach(el => {
      const w = el.style.width;
      el.style.width = '0%';
      setTimeout(() => el.style.width = w, 100);
    });
  }, 300);

  /* Confetti for top 3 */
  if (rank > 3) return;
  const colors = ['#FAC775','#EF9F27','#7F77DD','#1D9E75','#D85A30','#378ADD','#D4537E'];
  const wrap   = document.getElementById('confetti-wrap');
  setTimeout(() => {
    for (let i = 0; i < 80; i++) {
      setTimeout(() => {
        const el = document.createElement('div');
        el.className = 'confetti-piece';
        el.style.cssText = [
          `left:${Math.random()*100}vw`,
          `background:${colors[Math.floor(Math.random()*colors.length)]}`,
          `width:${6+Math.random()*8}px`,
          `height:${6+Math.random()*8}px`,
          `border-radius:${Math.random()>.5?'50%':'2px'}`,
          `animation-duration:${2+Math.random()*2}s`,
          `animation-delay:${Math.random()*.5}s`,
        ].join(';');
        wrap.appendChild(el);
        setTimeout(() => el.remove(), 4000);
      }, i * 30);
    }
  }, 400);
}

/* ══════════════════════════════════════════════════════════════
   BOOTSTRAP — run the right function based on page
   ══════════════════════════════════════════════════════════════ */
document.addEventListener('DOMContentLoaded', () => {
  initQuestionManager();

  /* Test form mode switcher */
  const checked = document.querySelector('input[name="mode"]:checked');
  if (checked) switchMode(checked.value);

  initTestJoin();
  initMonitor();
  initResults();
});