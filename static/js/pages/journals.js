/* ═══════════════════════════════════════════════════════════════
   journals.js — Journal Detail, Record Form, Lesson Form
   ═══════════════════════════════════════════════════════════════ */

/* ── Toast ───────────────────────────────────────────────────── */
function showToast(msg, type) {
  const t = document.getElementById('toast');
  if (!t) return;
  t.textContent = msg;
  t.className = `toast toast-${type} show`;
  setTimeout(() => t.classList.remove('show'), 2800);
}

/* ── Lesson accordion ────────────────────────────────────────── */
function toggleLesson(pk) {
  document.getElementById('lesson-' + pk).classList.toggle('open');
}

/* ── Join date editor ────────────────────────────────────────── */
function openJoinEdit(pk, d) {
  document.getElementById('jd-form-' + pk).classList.add('visible');
  document.getElementById('jd-input-' + pk).value = d;
}
function closeJoinEdit(pk) {
  document.getElementById('jd-form-' + pk).classList.remove('visible');
}
function saveJoinDate(pk) {
  const cfg  = JSON.parse(document.getElementById('journals-config').textContent);
  const d    = document.getElementById('jd-input-' + pk).value;
  if (!d) { showToast(cfg.i18n.selectDate, 'error'); return; }

  fetch(cfg.membershipUrl.replace('0', pk), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': cfg.csrfToken },
    body: JSON.stringify({ joined_at: d }),
  })
  .then(r => r.json())
  .then(data => {
    if (data.success) {
      const f = new Date(d + 'T00:00:00');
      document.getElementById('jd-display-' + pk).textContent =
        f.toLocaleDateString('en-GB', { day:'2-digit', month:'short', year:'numeric' }).toUpperCase();
      closeJoinEdit(pk);
      showToast(cfg.i18n.saved, 'success');
    } else {
      showToast(data.error || cfg.i18n.error, 'error');
    }
  })
  .catch(() => showToast(cfg.i18n.networkError, 'error'));
}

/* ── Grade buttons (record_form) ─────────────────────────────── */
function setGrade(pk, grade, btn) {
  btn.closest('.grade-row').querySelectorAll('.grade-btn').forEach(b => b.classList.remove('selected'));
  btn.classList.add('selected');
  document.getElementById('grade-hidden-' + pk).value = grade;
}

/* ── Lesson form: auto-fill today's date ─────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  const dateInput = document.querySelector('input[type="date"]');
  if (dateInput && !dateInput.value) {
    dateInput.value = new Date().toISOString().split('T')[0];
  }
});