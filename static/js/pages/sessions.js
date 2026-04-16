/* ═══════════════════════════════════════════════════════════════
   sessions.js — Session Form, Quiz Join, Monitor, Results, Leaderboard, Algorithmic Join
   ═══════════════════════════════════════════════════════════════ */

/* ══════════════════════════════════════════════════════════════
   SHARED
   ══════════════════════════════════════════════════════════════ */

let _toastTimer = null;
function _toast(msg, type) {
  const el = document.getElementById('toast-el');
  if (!el) return;
  el.textContent = msg;
  el.className   = `toast-msg toast-${type} show`;
  clearTimeout(_toastTimer);
  _toastTimer = setTimeout(() => el.classList.remove('show'), 3000);
}

function esc(s) {
  return String(s || '')
    .replace(/&/g,'&amp;').replace(/</g,'&lt;')
    .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

/* ══════════════════════════════════════════════════════════════
   SESSION FORM  (session_form.html)
   ══════════════════════════════════════════════════════════════ */

function switchType(type) {
  const taskSection     = document.getElementById('section-task');
  const testpackSection = document.getElementById('section-testpack');
  if (!taskSection || !testpackSection) return;
  if (type === 'algorithmic') {
    taskSection.classList.remove('section-hidden');
    testpackSection.classList.add('section-hidden');
  } else {
    taskSection.classList.add('section-hidden');
    testpackSection.classList.remove('section-hidden');
  }
}

/* ══════════════════════════════════════════════════════════════
   QUIZ JOIN  (session_join_quiz.html)
   ══════════════════════════════════════════════════════════════ */

function initQuizJoin() {
  const pdEl = document.getElementById('page-data');
  if (!pdEl) return;
  const PD = JSON.parse(pdEl.textContent);
  if (PD.page !== 'quiz_join') return;

  const TOTAL        = PD.total;
  const DURATION_SECS = PD.duration_secs * 60;
  const ACTIVATED_AT = PD.activated_at;
  const CSRF         = PD.csrfToken;
  const URL_ANSWER   = PD.urlAnswer;
  const URL_FINISH   = PD.urlFinish;
  const URL_RESULTS  = PD.urlResults;
  const i18n         = PD.i18n;

  let answeredIds = new Set(PD.answered_ids);
  let timeExpired = false;
  let finishing   = false;

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
    document.getElementById(`qcard-${questionId}`).classList.add('answered');
    try {
      await fetch(URL_ANSWER, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF },
        body: JSON.stringify({ question_id: questionId, choice_id: choiceId }),
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
    document.getElementById('finish-btn').disabled = true;
    try {
      const res = await fetch(URL_FINISH, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF },
        body: '{}',
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
          try { await fetch(URL_FINISH, { method:'POST', headers:{'Content-Type':'application/json','X-CSRFToken':CSRF}, body:'{}' }); } catch(e) {}
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
    const ws = new WebSocket(`${proto}://${location.host}/ws/session/${PD.session_pk}/`);
    ws.onclose = () => setTimeout(connectWS, 3000);
    ws.onmessage = e => {
      const msg = JSON.parse(e.data);
      if (msg.event === 'session_ended') {
        _toast(i18n.sessionClosed, 'w');
        timeExpired = true;
        document.getElementById('time-up-overlay').classList.add('show');
        setTimeout(() => window.location.href = URL_RESULTS, 2000);
      }
    };
  })();
}

/* ══════════════════════════════════════════════════════════════
   ALGORITHMIC JOIN  (session_join.html)
   ══════════════════════════════════════════════════════════════ */

function initAlgorithmicJoin() {
  const pdEl = document.getElementById('page-data');
  if (!pdEl) return;
  const PD = JSON.parse(pdEl.textContent);
  if (PD.page !== 'algo_join') return;

  const TASK_ID       = PD.task_id;
  const SESSION_ID    = PD.session_id;
  const CSRF          = PD.csrfToken;
  const DURATION_SECS = PD.duration_secs * 60;
  const ACTIVATED_AT  = PD.activated_at;
  const ALREADY_PASSED = PD.already_passed;
  const URL_RUN       = PD.urlRun;
  const URL_SUBMIT    = PD.urlSubmit;
  const i18n          = PD.i18n;

  const LANG_CONFIG = {
    python:     { filename:'solution.py',  mode:'python',        starter:'# Write your Python solution here\n# Input:  input()  or  int(input())\n# Output: print(...)\n\n' },
    javascript: { filename:'solution.js',  mode:'javascript',    starter:'// JavaScript solution\n// Input: const lines = require("fs").readFileSync("/dev/stdin","utf8").trim().split("\\n");\n\n' },
    cpp:        { filename:'solution.cpp', mode:'text/x-c++src', starter:'#include <bits/stdc++.h>\nusing namespace std;\nint main() {\n    \n    return 0;\n}\n' },
    c:          { filename:'solution.c',   mode:'text/x-csrc',   starter:'#include <stdio.h>\nint main() {\n    \n    return 0;\n}\n' },
  };
  let currentLang = 'python';
  let timeExpired = ALREADY_PASSED ? false : false;

  /* CodeMirror */
  const editor = CodeMirror.fromTextArea(document.getElementById('code-editor'), {
    mode: 'python', theme: 'nord', lineNumbers: true,
    autoCloseBrackets: true, matchBrackets: true,
    indentUnit: 4, tabSize: 4, indentWithTabs: false,
    extraKeys: { Tab: cm => cm.execCommand('indentMore') },
  });

  window.switchLang = function(btn) {
    const lang = btn.dataset.lang; const cfg = LANG_CONFIG[lang]; if (!cfg) return;
    document.querySelectorAll('.lang-pill').forEach(p => p.classList.remove('active'));
    btn.classList.add('active');
    editor.setOption('mode', cfg.mode);
    document.getElementById('editor-filename').textContent = cfg.filename;
    const val = editor.getValue().trim();
    const isStarter = Object.values(LANG_CONFIG).some(c => val === c.starter.trim() || val === '');
    if (isStarter) { editor.setValue(cfg.starter); setTimeout(() => editor.refresh(), 50); }
    currentLang = lang;
  };

  window.clearEditor = function() {
    if (confirm(i18n.clearConfirm)) editor.setValue(LANG_CONFIG[currentLang].starter);
  };

  window.toggleProblem = function() {
    const b = document.getElementById('prob-body'); const a = document.getElementById('prob-arrow');
    const show = b.style.display === 'none'; b.style.display = show ? 'block' : 'none';
    a.textContent = show ? `▼ ${i18n.hide}` : `▶ ${i18n.show}`;
  };

  window.switchTab = function(t) {
    document.getElementById('panel-r').style.display = t === 'r' ? 'block' : 'none';
    document.getElementById('panel-h').style.display = t === 'h' ? 'block' : 'none';
    document.getElementById('tab-r').className = 'tab-btn' + (t === 'r' ? ' active' : '');
    document.getElementById('tab-h').className = 'tab-btn' + (t === 'h' ? ' active' : '');
  };

  /* Countdown */
  if (DURATION_SECS && ACTIVATED_AT) {
    function updateCountdown() {
      const elapsed   = (Date.now() - new Date(ACTIVATED_AT).getTime()) / 1000;
      const remaining = Math.max(0, DURATION_SECS - elapsed);
      const m = Math.floor(remaining / 60), s = Math.floor(remaining % 60);
      const el   = document.getElementById('countdown');
      const wrap = document.getElementById('cd-wrap');
      if (el)   el.textContent = `${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`;
      if (wrap) wrap.className = 'cd-wrap ' + (remaining > 120 ? 'cd-ok' : remaining > 30 ? 'cd-warn' : 'cd-crit');
      if (remaining <= 0 && !timeExpired) { timeExpired = true; lockEditor(); }
    }
    updateCountdown(); setInterval(updateCountdown, 500);
  }

  function lockEditor() {
    editor.setOption('readOnly', 'nocursor');
    document.getElementById('editor-card').style.opacity = '.55';
    document.getElementById('btn-submit').disabled = true;
    document.getElementById('btn-run').disabled    = true;
    document.getElementById('time-up-banner').style.display = 'block';
    _toast(`⏰ ${i18n.timeUp}`, 'w');
  }

  function setRunLoading(on) {
    document.getElementById('btn-run').disabled          = on || timeExpired;
    document.getElementById('run-label').textContent     = on ? i18n.running : i18n.runCode;
  }
  function setSubLoading(on) {
    document.getElementById('btn-submit').disabled       = on || timeExpired || ALREADY_PASSED;
    document.getElementById('sub-label').textContent     = on ? i18n.evaluating : (ALREADY_PASSED ? i18n.alreadyPassed : i18n.submit);
  }

  function renderLoading(msg) {
    switchTab('r');
    document.getElementById('results-body').innerHTML = `<div style="text-align:center;padding:48px;color:var(--text-muted);"><div style="width:36px;height:36px;border:3px solid var(--border2);border-top-color:var(--accent);border-radius:50%;animation:spin .7s linear infinite;margin:0 auto 14px;"></div><p style="font-weight:600;">${msg}</p></div>`;
  }
  function renderError(msg) {
    switchTab('r');
    document.getElementById('results-body').innerHTML = `<div style="background:var(--danger-bg);border:2px solid var(--danger-brd);border-radius:var(--radius);padding:16px;color:var(--danger);font-size:.875rem;font-weight:500;">❌ ${esc(msg)}</div>`;
  }

  function renderResults(results, title, isSubmit) {
    switchTab('r');
    let html = title ? `<p style="font-weight:700;color:var(--text);margin-bottom:12px;font-size:.9rem;">${title}</p>` : '';
    results.forEach((r, i) => {
      const cls = r.passed ? 'pass' : (r.error ? 'warn' : 'fail');
      const icon = r.passed ? '✅' : (r.error ? '⚠️' : '❌');
      html += `<div class="ri ${cls}"><div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;"><span style="font-weight:700;font-size:.85rem;">${icon} ${i18n.testLabel} ${i + 1}</span><span style="font-size:.72rem;color:var(--text-muted);font-family:var(--font-mono);">${r.time_used || ''}s</span></div>`;
      if (r.input && r.input !== '(hidden)') html += `<p style="font-size:.75rem;margin-bottom:2px;"><span style="color:var(--text-muted);">${i18n.inputLabel}</span> <code style="font-family:var(--font-mono);color:var(--accent);">${esc(r.input.trim())}</code></p>`;
      if (!r.passed && r.expected && r.expected !== '(hidden)') html += `<p style="font-size:.75rem;margin-bottom:2px;"><span style="color:var(--text-muted);">${i18n.expectedLabel}</span> <code style="font-family:var(--font-mono);color:var(--success);">${esc(r.expected.trim())}</code></p>`;
      if (r.stdout) html += `<p style="font-size:.75rem;margin-bottom:2px;"><span style="color:var(--text-muted);">${i18n.gotLabel}</span> <code style="font-family:var(--font-mono);color:${r.passed ? 'var(--success)' : 'var(--danger)'};">${esc(r.stdout.trim())}</code></p>`;
      if (r.stderr) html += `<pre class="err">${esc(r.stderr)}</pre>`;
      html += `</div>`;
    });
    if (isSubmit) {
      const passed = results.filter(x => x.passed).length;
      const total  = results.length;
      if (passed === total) {
        html += `<div style="background:var(--success-bg);border:2px solid var(--success-brd);border-radius:var(--radius-lg);padding:20px;text-align:center;margin-top:8px;"><p style="font-size:2rem;margin-bottom:6px;">🎉</p><p style="font-weight:700;color:var(--success);font-size:1rem;">${i18n.allPassed}</p></div>`;
        document.getElementById('btn-submit').disabled = true;
        document.getElementById('sub-label').textContent = `✓ ${i18n.passed}`;
      } else {
        html += `<div style="background:var(--warning-bg);border:2px solid var(--warning-brd);border-radius:var(--radius-lg);padding:16px;text-align:center;margin-top:8px;"><p style="font-weight:700;color:var(--warning);">${passed}/${total} ${i18n.testsPassed}</p></div>`;
      }
    }
    document.getElementById('results-body').innerHTML = html;
  }

  window.runCode = async function() {
    if (timeExpired) return;
    setRunLoading(true); renderLoading(i18n.runningTests);
    try {
      const res = await fetch(URL_RUN, { method:'POST', headers:{'Content-Type':'application/json','X-CSRFToken':CSRF}, body:JSON.stringify({task_id:TASK_ID,session_id:SESSION_ID,code:editor.getValue(),language:currentLang}) });
      const d   = await res.json();
      if (!res.ok) { renderError(d.error || i18n.serverError); return; }
      renderResults(d.results, i18n.exampleResults, false);
    } catch(e) { renderError(`${i18n.networkError} ${e.message}`); }
    finally { setRunLoading(false); }
  };

  window.submitCode = async function() {
    if (timeExpired || ALREADY_PASSED) return;
    setSubLoading(true); renderLoading(i18n.evaluatingTests);
    try {
      const res = await fetch(URL_SUBMIT, { method:'POST', headers:{'Content-Type':'application/json','X-CSRFToken':CSRF}, body:JSON.stringify({task_id:TASK_ID,session_id:SESSION_ID,code:editor.getValue(),language:currentLang}) });
      const d   = await res.json();
      if (!res.ok) { renderError(d.error || i18n.serverError); return; }
      renderResults(d.results, i18n.submitResults, true);
      _toast(d.is_correct ? `🎉 ${i18n.allPassed}` : `${d.passed_count}/${d.total_count} ${i18n.testsPassed}`, d.is_correct ? 's' : 'w');
    } catch(e) { renderError(`${i18n.networkError} ${e.message}`); }
    finally { setSubLoading(false); }
  };

  /* WebSocket */
  function connectWS() {
    const proto = location.protocol === 'https:' ? 'wss' : 'ws';
    const ws = new WebSocket(`${proto}://${location.host}/ws/session/${SESSION_ID}/`);
    ws.onclose = () => setTimeout(connectWS, 3000);
    ws.onmessage = e => {
      const msg = JSON.parse(e.data);
      if (msg.event === 'session_ended') {
        _toast(i18n.sessionClosed, 'w');
        lockEditor();
        setTimeout(() => location.href = '/sessions/', 3000);
      }
    };
  }
  connectWS();
}

/* ══════════════════════════════════════════════════════════════
   MONITOR  (session_monitor.html)
   ══════════════════════════════════════════════════════════════ */

function initSessionMonitor() {
  const pdEl = document.getElementById('page-data');
  if (!pdEl) return;
  const PD = JSON.parse(pdEl.textContent);
  if (PD.page !== 'monitor') return;

  const SESSION_PK    = PD.session_pk;
  const IS_QUIZ       = PD.is_quiz;
  const TOTAL_S       = PD.total_students;
  const TOTAL_Q       = PD.total_questions;
  const DURATION_SECS = PD.duration_secs * 60;
  const ACTIVATED_AT  = PD.activated_at;

  let nPassed = 0, nActive = 0;

  function updateStats() {
    document.getElementById('s-passed').textContent = nPassed;
    document.getElementById('s-active').textContent = nActive;
    document.getElementById('s-idle').textContent   = Math.max(0, TOTAL_S - nPassed - nActive);
  }

  function setWS(ok) {
    const dot = document.getElementById('ws-dot');
    const lbl = document.getElementById('ws-label');
    const ind = document.getElementById('ws-indicator');
    if (ok) {
      dot.style.background = 'var(--success)'; lbl.textContent = 'Live'; lbl.style.color = 'var(--success)';
      ind.style.background = 'var(--success-bg)'; ind.style.borderColor = 'var(--success-brd)';
    } else {
      dot.style.background = 'var(--text-muted)'; lbl.textContent = 'Connecting'; lbl.style.color = 'var(--text-muted)';
      ind.style.background = 'var(--bg2)'; ind.style.borderColor = 'var(--border)';
    }
  }

  function nowStr() { return new Date().toTimeString().slice(0, 8); }

  function flashRow(sid, color) {
    const row = document.getElementById(`row-${sid}`);
    if (row) { row.style.transition = 'background .15s'; row.style.background = color; setTimeout(() => row.style.background = '', 1500); }
  }

  function updateDot(sid, order) {
    const dot = document.getElementById(`dot-${sid}-${order}`);
    if (dot) {
      dot.classList.remove('current'); dot.classList.add('answered');
      const next = document.getElementById(`dot-${sid}-${order + 1}`);
      if (next && !next.classList.contains('answered')) next.classList.add('current');
    }
  }

  function updateProgress(sid, answered) {
    const countEl = document.getElementById(`ans-count-${sid}`);
    const fillEl  = document.getElementById(`prog-fill-${sid}`);
    if (countEl) countEl.textContent = answered;
    if (fillEl && TOTAL_Q) fillEl.style.width = ((answered / TOTAL_Q) * 100) + '%';
  }

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
    updateCD(); setInterval(updateCD, 500);
  }

  function connectWS() {
    const proto = location.protocol === 'https:' ? 'wss' : 'ws';
    const ws = new WebSocket(`${proto}://${location.host}/ws/session/${SESSION_PK}/`);
    ws.onopen  = () => setWS(true);
    ws.onclose = () => { setWS(false); setTimeout(connectWS, 3000); };

    ws.onmessage = e => {
      const msg = JSON.parse(e.data), d = msg.data, sid = d.student_id;

      if (msg.event === 'student_joined') {
        const status = document.getElementById(`status-${sid}`);
        const joined = document.getElementById(`joined-${sid}`);
        if (status) status.innerHTML = `<span class="badge badge-active">▶ In Progress</span>`;
        if (joined) joined.textContent = nowStr();
        if (IS_QUIZ) {
          const first = document.getElementById(`dot-${sid}-1`);
          if (first) first.classList.add('current');
        }
        nActive++; updateStats();
        flashRow(sid, 'rgba(13,148,136,.07)');
        _toast(`${d.full_name} joined`, 's');

      } else if (msg.event === 'question_answered') {
        updateProgress(sid, d.answered_count);
        if (d.question_order) updateDot(sid, d.question_order);
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
        nActive = Math.max(0, nActive - 1); nPassed++; updateStats();
        flashRow(sid, 'rgba(5,150,105,.08)');
        _toast(`🎉 ${d.username} finished! ${d.score}/${d.total}`, 's');

      } else if (msg.event === 'ran_example' || msg.event === 'submitted') {
        const status = document.getElementById(`status-${sid}`);
        if (status && !IS_QUIZ) status.innerHTML = `<span class="badge badge-pending">⏳ Checking</span>`;
        if (!nActive) { nActive++; updateStats(); }

      } else if (msg.event === 'submission_result') {
        const status = document.getElementById(`status-${sid}`);
        const score  = document.getElementById(`score-${sid}`);
        const time   = document.getElementById(`time-${sid}`);
        if (!IS_QUIZ) {
          const badge = d.is_correct
            ? `<span class="badge badge-passed">✓ Passed</span>`
            : `<span class="badge badge-failed">✗ Failed</span>`;
          if (status) status.innerHTML = badge;
          if (score)  score.textContent = `${d.passed_count}/${d.total_count}`;
          if (time)   time.textContent  = nowStr();
          if (d.is_correct) { nActive = Math.max(0, nActive - 1); nPassed++; updateStats(); _toast(`✓ ${d.username} passed!`, 's'); }
          flashRow(sid, d.is_correct ? 'rgba(5,150,105,.07)' : 'rgba(220,38,38,.05)');
        }
      }
    };
  }
  connectWS();
}

/* ══════════════════════════════════════════════════════════════
   LEADERBOARD  (leaderboard.html)
   ══════════════════════════════════════════════════════════════ */

function initLeaderboard() {
  const pdEl = document.getElementById('page-data');
  if (!pdEl) return;
  const PD = JSON.parse(pdEl.textContent);
  if (PD.page !== 'leaderboard') return;

  const { session_pk, is_active, is_quiz, lang, my_username, i18n } = PD;
  const medals  = ['🥇','🥈','🥉'];
  const mColors = ['#d97706','#64748b','#b45309'];

  async function refreshLeaderboard() {
    try {
      const r = await fetch(`${lang}/api/leaderboard/${session_pk}/`);
      if (!r.ok) return;
      const d = await r.json();
      document.getElementById('lb-body').innerHTML = d.board.map((e, i) => {
        const rank    = (i < 3 && e.passed) ? medals[i] : (i + 1);
        const mColor  = (i < 3 && e.passed) ? mColors[i] : 'var(--text-muted)';
        const cls     = ['lb-row', e.passed ? 'passed' : '', e.username === my_username ? 'me' : ''].join(' ').trim();
        const me      = e.username === my_username ? ` <span style="color:var(--accent);font-size:.72rem;">(${i18n.you})</span>` : '';
        const badge   = e.passed
          ? `<span class="badge badge-passed">✓ ${i18n.passed}</span>`
          : e.attempts ? `<span class="badge badge-running">${i18n.working}</span>`
          : `<span class="badge badge-notstarted">${i18n.notStarted}</span>`;
        const time    = e.submitted_at ? new Date(e.submitted_at).toTimeString().slice(0, 8) : '—';
        const scoreCol = is_quiz
          ? `<td class="hide-sm" style="color:var(--text-muted);font-family:var(--font-mono);">${e.score !== undefined ? e.score+'/'+e.total : '—'}</td>`
          : `<td class="hide-sm" style="color:var(--text-muted);font-family:var(--font-mono);">${e.attempts}</td>`;
        return `<tr class="${cls}">
          <td style="text-align:center;font-weight:700;color:${mColor};font-family:var(--font-mono);">${rank}</td>
          <td><div style="display:flex;align-items:center;gap:8px;">
            <div style="width:30px;height:30px;border-radius:50%;background:var(--accent);display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:700;color:#fff;font-family:var(--font-mono);flex-shrink:0;">${e.username[0].toUpperCase()}</div>
            <span style="font-weight:600;">${esc(e.username)}${me}</span>
          </div></td>
          <td>${badge}</td>
          ${scoreCol}
          <td class="hide-sm" style="font-size:.8rem;color:var(--text-muted);font-family:var(--font-mono);">${time}</td>
        </tr>`;
      }).join('');
    } catch(e) { console.warn('Leaderboard refresh error:', e); }
  }

  function connectWS() {
    const proto = location.protocol === 'https:' ? 'wss' : 'ws';
    const ws = new WebSocket(`${proto}://${location.host}/ws/session/${session_pk}/`);
    ws.onclose = () => setTimeout(connectWS, 3000);
    ws.onmessage = e => {
      const msg = JSON.parse(e.data);
      const triggers = ['submission_result','student_finished','submitted','ran_example','question_answered'];
      if (triggers.includes(msg.event)) {
        refreshLeaderboard();
        if (msg.event === 'student_finished' || msg.event === 'submission_result') {
          const name = msg.data?.username || '';
          if (name) _toast(`✓ ${name} ${i18n.finished}!`, 's');
        }
      }
      if (msg.event === 'session_ended') {
        _toast(i18n.sessionEnded, 'w');
        setTimeout(refreshLeaderboard, 800);
        setTimeout(() => location.reload(), 3000);
      }
    };
  }

  if (is_active) {
    connectWS();
    setInterval(refreshLeaderboard, 10000);
  } else {
    refreshLeaderboard();
  }
}

/* ══════════════════════════════════════════════════════════════
   RESULTS  (session_quiz_results.html)
   ══════════════════════════════════════════════════════════════ */

function initQuizResults() {
  const rankEl = document.getElementById('result-rank');
  if (!rankEl) return;
  const rank = parseInt(rankEl.dataset.rank);

  setTimeout(() => {
    document.querySelectorAll('.score-bar-fill').forEach(el => {
      const w = el.style.width; el.style.width = '0%';
      setTimeout(() => el.style.width = w, 100);
    });
  }, 300);

  if (rank > 3) return;
  const colors = ['#FAC775','#EF9F27','#7F77DD','#1D9E75','#D85A30','#378ADD','#D4537E'];
  const wrap   = document.getElementById('confetti-wrap');
  setTimeout(() => {
    for (let i = 0; i < 80; i++) {
      setTimeout(() => {
        const el = document.createElement('div');
        el.className = 'confetti-piece';
        el.style.cssText = [`left:${Math.random()*100}vw`,`background:${colors[Math.floor(Math.random()*colors.length)]}`,`width:${6+Math.random()*8}px`,`height:${6+Math.random()*8}px`,`border-radius:${Math.random()>.5?'50%':'2px'}`,`animation-duration:${2+Math.random()*2}s`,`animation-delay:${Math.random()*.5}s`].join(';');
        wrap.appendChild(el);
        setTimeout(() => el.remove(), 4000);
      }, i * 30);
    }
  }, 400);
}

/* ══════════════════════════════════════════════════════════════
   BOOTSTRAP
   ══════════════════════════════════════════════════════════════ */
document.addEventListener('DOMContentLoaded', () => {
  /* Session form */
  const checked = document.querySelector('input[name="session_type"]:checked');
  if (checked) switchType(checked.value);

  const dtInput = document.querySelector('input[type="datetime-local"]');
  if (dtInput && !dtInput.value) {
    const now = new Date();
    now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
    dtInput.value = now.toISOString().slice(0, 16);
  }

  initQuizJoin();
  initAlgorithmicJoin();
  initSessionMonitor();
  initLeaderboard();
  initQuizResults();
});