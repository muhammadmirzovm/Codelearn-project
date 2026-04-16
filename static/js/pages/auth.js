/* ═══════════════════════════════════════════════════════════════
   auth.js — Login, Register, Select Role
   ═══════════════════════════════════════════════════════════════ */

/**
 * Toggle password visibility.
 * Works for both login (SVG eye icons) and profile (bi icons).
 * @param {string} inputId  - id of the <input type="password">
 * @param {HTMLElement} btn - the toggle button element
 */
function togglePw(inputId, btn) {
  const input   = document.getElementById(inputId);
  const showing = input.type === 'text';
  input.type    = showing ? 'password' : 'text';

  /* SVG variant (login / register pages) */
  const eyeOpen   = btn.querySelector('.eye-open');
  const eyeClosed = btn.querySelector('.eye-closed');
  if (eyeOpen && eyeClosed) {
    eyeOpen.style.display   = showing ? 'block' : 'none';
    eyeClosed.style.display = showing ? 'none'  : 'block';
  }

  /* Bootstrap-icon variant (profile page) */
  const icon = btn.querySelector('i');
  if (icon) {
    icon.className = showing ? 'bi bi-eye-slash' : 'bi bi-eye';
  }

  /* Update title from data attributes set in the template */
  const showLabel = btn.dataset.showLabel || 'Show password';
  const hideLabel = btn.dataset.hideLabel || 'Hide password';
  btn.title = showing ? showLabel : hideLabel;

  input.focus();
}

/**
 * Select role card on the select_role page.
 * Highlights the chosen card and enables the submit button.
 * @param {string}      role - 'teacher' | 'student'
 * @param {HTMLElement} el   - the clicked label element
 */
function selectRole(role, el) {
  document.querySelectorAll('.role-card').forEach(l => l.classList.remove('selected'));
  el.classList.add('selected');
  el.querySelector('input').checked = true;

  const btn = document.getElementById('submit-btn');
  if (btn) {
    btn.disabled       = false;
    btn.style.opacity  = '1';
    btn.style.cursor   = 'pointer';
  }
}