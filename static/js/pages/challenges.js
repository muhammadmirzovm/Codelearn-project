/* ═══════════════════════════════════════════════════════════════
   challenges.js — Challenge Detail (run & submit)
   ═══════════════════════════════════════════════════════════════ */

document.addEventListener('DOMContentLoaded', () => {
  const cfgEl = document.getElementById('challenge-config');
  if (!cfgEl) return;
  const cfg = JSON.parse(cfgEl.textContent);

  /* ── CodeMirror ──────────────────────────────────────────────── */
  const modeMap = {
    python:     'python',
    javascript: 'javascript',
    cpp:        'text/x-c++src',
    c:          'text/x-csrc',
  };

  const editor = CodeMirror.fromTextArea(document.getElementById('code-editor'), {
    theme:             'nord',
    lineNumbers:       true,
    autoCloseBrackets: true,
    matchBrackets:     true,
    mode:              'python',
    indentUnit:        4,
    tabSize:           4,
    indentWithTabs:    false,
  });

  document.getElementById('lang-select').addEventListener('change', function() {
    editor.setOption('mode', modeMap[this.value] || 'python');
  });

  /* ── DOM refs ────────────────────────────────────────────────── */
  const btnRun    = document.getElementById('btn-run');
  const btnSubmit = document.getElementById('btn-submit');
  const panel     = document.getElementById('results-panel');
  const body      = document.getElementById('results-body');
  const titleEl   = document.getElementById('results-title');

  /* ── Helpers ─────────────────────────────────────────────────── */
  function setLoading(loading) {
    btnRun.disabled    = loading;
    btnSubmit.disabled = loading;
  }

  function showPanel(html, titleHtml) {
    panel.style.display = 'block';
    body.innerHTML      = html;
    if (titleHtml) titleEl.innerHTML = titleHtml;
    panel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  function escHtml(s) {
    return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  }

  function renderResults(results) {
    if (!results || !results.length) {
      return `<p style="color:var(--text-muted);font-size:.85rem;">${cfg.i18n.noResults}</p>`;
    }
    return results.map((r, i) => `
      <div class="result-row">
        <span class="result-status ${r.passed ? 'result-pass' : 'result-fail'}">
          ${r.passed ? '✓' : '✗'}
        </span>
        <div class="result-data">
          <span><strong>${cfg.i18n.test} ${i + 1}</strong>
            ${r.time_used != null ? `<span style="color:var(--text-sub);margin-left:8px;">${r.time_used}s</span>` : ''}
            ${r.error ? `<span style="color:#ef4444;margin-left:6px;">${escHtml(r.error)}</span>` : ''}
          </span>
          ${r.input && r.input !== '(hidden)' ? `<span>${cfg.i18n.input}: <code>${escHtml(r.input)}</code></span>` : ''}
          ${r.expected && r.expected !== '(hidden)' ? `<span>${cfg.i18n.expected}: <code>${escHtml(r.expected)}</code></span>` : ''}
          ${r.stdout ? `<span>${cfg.i18n.output}: <code>${escHtml(r.stdout.slice(0, 200))}</code></span>` : ''}
          ${r.stderr ? `<span style="color:#ef4444;">${cfg.i18n.error}: <code>${escHtml(r.stderr.slice(0, 200))}</code></span>` : ''}
        </div>
      </div>
    `).join('');
  }

  /* ── Run ─────────────────────────────────────────────────────── */
  btnRun.addEventListener('click', async () => {
    const code     = editor.getValue();
    const language = document.getElementById('lang-select').value;
    if (!code.trim()) { _toast(cfg.i18n.writeCodeFirst, 'w'); return; }

    setLoading(true);
    btnRun.innerHTML = `<span class="spinner"></span> ${cfg.i18n.running}`;

    try {
      const fd = new FormData();
      fd.append('code', code);
      fd.append('language', language);

      const res  = await fetch(cfg.runUrl, { method:'POST', headers:{'X-CSRFToken': cfg.csrfToken}, body: fd });
      const data = await res.json();

      if (data.error) { _toast(data.error, 'e'); return; }

      const all    = data.results || [];
      const passed = all.filter(r => r.passed).length;
      const html   = `
        <div class="verdict-banner ${passed === all.length ? 'verdict-pass' : 'verdict-fail'}">
          ${passed === all.length ? '✅' : '❌'}
          ${cfg.i18n.exampleCases}: ${passed}/${all.length} ${cfg.i18n.passed}
        </div>
        ${renderResults(all)}
      `;
      showPanel(html, `<i class="bi bi-play-circle"></i> ${cfg.i18n.runResults}`);

    } catch(e) {
      _toast(cfg.i18n.networkError, 'e');
    } finally {
      setLoading(false);
      btnRun.innerHTML = `<i class="bi bi-play"></i> ${cfg.i18n.run}`;
    }
  });

  /* ── Submit ──────────────────────────────────────────────────── */
  btnSubmit.addEventListener('click', async () => {
    const code     = editor.getValue();
    const language = document.getElementById('lang-select').value;
    if (!code.trim()) { _toast(cfg.i18n.writeCodeFirst, 'w'); return; }

    setLoading(true);
    btnSubmit.innerHTML = `<span class="spinner"></span> ${cfg.i18n.evaluating}`;

    showPanel(
      `<div style="text-align:center;padding:24px;color:var(--text-muted);">
         <span class="spinner" style="border-color:rgba(0,0,0,.2);border-top-color:var(--accent);width:22px;height:22px;border-width:3px;"></span>
         <p style="margin-top:12px;font-size:.85rem;">${cfg.i18n.runningAllTests}</p>
       </div>`,
      `<i class="bi bi-send"></i> ${cfg.i18n.submission}`
    );

    try {
      const fd = new FormData();
      fd.append('code', code);
      fd.append('language', language);

      const res  = await fetch(cfg.submitUrl, { method:'POST', headers:{'X-CSRFToken': cfg.csrfToken}, body: fd });
      const data = await res.json();

      if (data.error) {
        _toast(data.error, 'e');
        showPanel(`<p style="color:var(--danger);padding:14px;">${escHtml(data.error)}</p>`);
        return;
      }

      const passed = data.passed ?? 0;
      const total  = data.total  ?? 0;
      let verdict  = '';

      if (data.is_correct) {
        const coinMsg = data.coins_earned
          ? `<span style="font-size:.85rem;font-weight:400;"> — 🪙 +${data.coins_earned} ${cfg.i18n.coinsEarned}</span>`
          : '';
        verdict = `<div class="verdict-banner verdict-pass">✅ ${cfg.i18n.accepted} (${passed}/${total})${coinMsg}</div>`;
        if (data.coins_earned) _toast(`🪙 +${data.coins_earned} ${cfg.i18n.coinsEarned}`, 's');
      } else {
        verdict = `<div class="verdict-banner verdict-fail">❌ ${cfg.i18n.wrongAnswer} — ${passed}/${total} ${cfg.i18n.testCasesPassed}</div>`;
      }

      showPanel(
        verdict + renderResults(data.results || []),
        `<i class="bi bi-check2-circle"></i> ${cfg.i18n.submissionResult}`
      );

    } catch(e) {
      _toast(cfg.i18n.networkError, 'e');
    } finally {
      setLoading(false);
      btnSubmit.innerHTML = `<i class="bi bi-send"></i> ${cfg.i18n.submit}`;
    }
  });
});