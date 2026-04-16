/* ================================================================
   resources.js  —  shared logic for home / website_list / video_list
   ================================================================ */

/* ── Video helpers ── */
function extractYouTubeId(url) {
  if (!url) return '';
  let match;
  match = url.match(/youtube\.com\/embed\/([a-zA-Z0-9_-]{11})/);
  if (match) return match[1];
  match = url.match(/[?&]v=([a-zA-Z0-9_-]{11})/);
  if (match) return match[1];
  match = url.match(/youtu\.be\/([a-zA-Z0-9_-]{11})/);
  if (match) return match[1];
  match = url.match(/([a-zA-Z0-9_-]{11})(?:\?|&|$)/);
  if (match) return match[1];
  return '';
}

function getEmbedUrl(url) {
  const id = extractYouTubeId(url);
  return id ? `https://www.youtube.com/embed/${id}?autoplay=1&rel=0` : '';
}

function getThumbUrl(url) {
  const id = extractYouTubeId(url);
  return id ? `https://img.youtube.com/vi/${id}/hqdefault.jpg` : '';
}

function loadVideo(pk) {
  const card   = document.querySelector(`.vid-card[data-video-url] #thumb-${pk}`)?.closest('.vid-card');
  const thumb  = document.getElementById('thumb-' + pk);
  const player = document.getElementById('player-' + pk);
  if (!card || !thumb || !player) return;

  const embedUrl = getEmbedUrl(card.dataset.videoUrl || '');
  if (!embedUrl) { alert('Invalid YouTube URL'); return; }

  thumb.style.display  = 'none';
  player.style.display = 'block';
  player.innerHTML     = '';

  const iframe = document.createElement('iframe');
  iframe.src              = embedUrl;
  iframe.allowFullscreen  = true;
  iframe.allow            = 'accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture';
  iframe.referrerPolicy   = 'strict-origin-when-cross-origin';
  iframe.style.cssText    = 'position:absolute;top:0;left:0;width:100%;height:100%;border:none;';
  player.appendChild(iframe);
}

function initVideoThumbnails() {
  document.querySelectorAll('.vid-card[data-video-url]').forEach(card => {
    const videoUrl  = card.dataset.videoUrl || '';
    const thumbImg  = card.querySelector('img[id^="thumb-img-"]');
    const watchLink = card.querySelector('a[id^="watch-link-"]');
    const videoId   = extractYouTubeId(videoUrl);

    if (thumbImg)  thumbImg.src  = videoId ? getThumbUrl(videoUrl) : '';
    if (watchLink && videoId) watchLink.href = `https://www.youtube.com/watch?v=${videoId}`;
  });
}

/* ── Video form toggle ── */
function toggleVideoForm() {
  const wrap = document.getElementById('video-form-wrap');
  if (!wrap) return;
  const opening = wrap.style.display === 'none';
  wrap.style.display = opening ? 'block' : 'none';
  if (opening) wrap.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

/* ── Video search ── */
function initVideoSearch() {
  const input = document.getElementById('vid-search');
  if (!input) return;
  input.addEventListener('input', function () {
    const q = this.value.toLowerCase().trim();
    document.querySelectorAll('.vid-card').forEach(card => {
      const match = !q ||
        (card.dataset.title || '').includes(q) ||
        (card.dataset.desc  || '').includes(q);
      card.style.display = match ? '' : 'none';
    });
  });
}

/* ── Website search ── */
function initWebsiteSearch() {
  const input     = document.getElementById('res-search');
  const grid      = document.getElementById('res-grid');
  const countPill = document.getElementById('res-visible-count');
  if (!input || !grid) return;

  let emptyEl = null;

  input.addEventListener('input', function () {
    const q       = this.value.toLowerCase().trim();
    const cards   = grid.querySelectorAll('.res-card');
    let   visible = 0;

    cards.forEach(card => {
      const match = !q ||
        (card.dataset.name || '').includes(q) ||
        (card.dataset.desc || '').includes(q) ||
        (card.dataset.tags || '').includes(q);
      card.style.display = match ? '' : 'none';
      if (match) visible++;
    });

    if (countPill) countPill.textContent = visible;

    if (visible === 0 && !emptyEl) {
      emptyEl = document.createElement('div');
      emptyEl.className = 'res-empty';
      emptyEl.innerHTML =
        '<div class="res-empty-icon">🔍</div>' +
        '<h3>No results found</h3>' +
        '<p>Try a different search term.</p>';
      grid.appendChild(emptyEl);
    } else if (visible > 0 && emptyEl) {
      emptyEl.remove();
      emptyEl = null;
    }
  });
}

/* ── Suggest form toggle ── */
function toggleSuggestForm() {
  const wrap = document.getElementById('suggest-form-wrap');
  const btn  = document.getElementById('suggest-toggle-btn');
  if (!wrap) return;
  const opening = wrap.style.display === 'none';
  wrap.style.display = opening ? 'block' : 'none';
  if (btn) btn.innerHTML = opening
    ? '<i class="bi bi-x-lg"></i> Cancel'
    : '<i class="bi bi-plus-lg"></i> Suggest a website';
  if (opening) wrap.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

/* ── New-category toggle (suggest form) ── */
function toggleNewCategory(checkbox) {
  const wrap      = document.getElementById('new-cat-wrap');
  const catSelect = document.getElementById('id_category');
  const newInput  = document.getElementById('id_suggested_category');
  if (!wrap) return;
  if (checkbox.checked) {
    wrap.style.display  = 'block';
    if (catSelect) { catSelect.value = ''; catSelect.disabled = true; }
    if (newInput)  newInput.required = true;
  } else {
    wrap.style.display  = 'none';
    if (catSelect) catSelect.disabled = false;
    if (newInput)  { newInput.required = false; newInput.value = ''; }
  }
}

/* ── Boot ── */
document.addEventListener('DOMContentLoaded', function () {
  initVideoThumbnails();
  initVideoSearch();
  initWebsiteSearch();
});