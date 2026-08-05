/* Qari frontend: Mushaf rendering, live audio streaming, live highlighting. */

const socket = io();

const el = {
  mushaf: document.getElementById('mushaf'),
  pageHeader: document.getElementById('page-header'),
  pageFooter: document.getElementById('page-footer'),
  pageInput: document.getElementById('page-input'),
  pageTotal: document.getElementById('page-total'),
  btnMic: document.getElementById('btn-mic'),
  micLabel: document.getElementById('mic-label'),
  connDot: document.getElementById('conn-dot'),
  connText: document.getElementById('conn-text'),
  accuracy: document.getElementById('accuracy'),
  lastText: document.getElementById('last-text'),
};

let currentPage = 1;
let totalPages = 604;
let lineElements = [];       // {lineEl, wordEls, n: mushafLineNo}
let currentLineNo = null;    // mushaf line number of the active line
let lastContentNo = -1;      // highest mushaf line number with content
let recording = false;
let stream = null;
let completionShown = false;
let scoredLines = new Set();

// running accuracy for the page
let score = { correct: 0, total: 0 };

/* ---------------- socket events ---------------- */

socket.on('connect', () => {
  el.connDot.classList.add('online');
  el.connText.textContent = 'متصل';
});

socket.on('disconnect', () => {
  el.connDot.classList.remove('online');
  el.connText.textContent = 'غير متصل';
});

socket.on('page', (data) => {
  totalPages = data.total_pages;
  el.pageTotal.textContent = `/ ${totalPages}`;
  currentPage = data.page;
  el.pageInput.value = currentPage;
  renderPage(data);
  resetScore();
});

socket.on('feedback', (data) => {
  applyFeedback(data);
});

socket.on('error', (data) => {
  console.error('server error:', data);
});

/* ---------------- page rendering ---------------- */

function renderPage(data) {
  currentLineNo = null;
  lastContentNo = -1;
  completionShown = false;
  scoredLines = new Set();
  lineElements = [];
  el.mushaf.innerHTML = '';
  hideCompletion();
  score = { correct: 0, total: 0 };

  // surah header
  const surah = data.surahs && data.surahs[0];
  el.pageHeader.innerHTML = surah
    ? `<span class="surah-name">سُورَةُ ${surah.name}</span>`
    : '';
  el.pageFooter.innerHTML = `صفحة ${data.page} — مصحف المدينة (15 سطر)`;

  // 15 slots, place real lines at their mushaf line number
  for (let i = 1; i <= 15; i++) {
    const lineData = data.lines.find((l) => l.n === i);
    const lineEl = document.createElement('div');
    lineEl.className = 'line';
    const wordEls = [];
    if (lineData) {
      for (const w of lineData.words) {
        const span = document.createElement('span');
        if (w.m != null) {
          span.className = 'ayah-end';
          span.innerHTML = `<span class="sep">۝</span><span class="num">${w.t}</span>`;
          span.dataset.idx = w.idx;
        } else {
          span.className = 'word';
          span.textContent = w.t;
          span.dataset.idx = w.idx;
        }
        lineEl.appendChild(span);
        wordEls.push(span);
      }
      lineEl.dataset.lineIdx = lineData.n;
    } else {
      lineEl.classList.add('blank');
      lineEl.innerHTML = '&nbsp;';
    }
    el.mushaf.appendChild(lineEl);
    lineElements.push({ lineEl, wordEls, n: lineData ? lineData.n : null });
    if (lineData && lineData.n > lastContentNo) lastContentNo = lineData.n;
  }
}

/* ---------------- feedback application ---------------- */

function applyFeedback(data) {
  if (data.text) el.lastText.textContent = `… ${data.text}`;
  if (typeof data.accuracy === 'number' && data.accuracy !== null) {
    el.accuracy.textContent = `دقة: ${data.accuracy}٪`;
  }
  if (data.line == null) return;

  // update active line (matched by mushaf line number)
  if (currentLineNo !== null) {
    const prev = lineElements.find((l) => l.n === currentLineNo);
    if (prev) {
      prev.lineEl.classList.remove('active');
      prev.wordEls.forEach((s) => { if (s.classList.contains('word')) s.className = 'word'; });
    }
  }
  const li = lineElements.find((l) => l.n === data.line_no);
  if (li) {
    li.lineEl.classList.add('active');
    currentLineNo = data.line_no;
    li.lineEl.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
  }

  // update word statuses for the reported line
  if (Array.isArray(data.words)) {
    for (const w of data.words) {
      const target = li && li.wordEls.find((s) => s.dataset.idx === String(w.idx));
      if (!target) continue;
      if (w.marker != null) continue; // verse-end markers keep gold
      target.className = 'word ' + w.status;
    }
    // accumulate page score from non-marker words (count each line once)
    if (!scoredLines.has(data.line_no) && Array.isArray(data.words)) {
      scoredLines.add(data.line_no);
      data.words.forEach((w) => {
        if (w.marker != null) return;
        score.total += 1;
        if (w.status === 'correct') score.correct += 1;
      });
    }
    const pct = score.total ? Math.round((score.correct / score.total) * 100) : 0;
    el.accuracy.textContent = `دقة الصفحة: ${pct}٪`;

    // page completion: reached the last line with a good score
    if (data.line_no === lastContentNo && pct >= 85 && score.total > 0 && !completionShown) {
      completionShown = true;
      showCompletion(pct);
    }
  }
}

/* ---------------- page completion banner ---------------- */

function showCompletion(pct) {
  let banner = document.getElementById('completion');
  if (!banner) {
    banner = document.createElement('div');
    banner.id = 'completion';
    banner.className = 'completion hidden';
    banner.innerHTML = `
      <div class="completion-card">
        <div class="completion-title">أحسنت! 🎉</div>
        <div class="completion-score">دقة الصفحة: <span id="completion-pct"></span>٪</div>
        <div class="completion-actions">
          <button id="btn-retry" class="done-btn">أعد المحاولة</button>
          <button id="btn-next-page" class="done-btn primary">الصفحة التالية ←</button>
        </div>
      </div>`;
    document.body.appendChild(banner);
    document.getElementById('btn-retry').addEventListener('click', () => {
      resetWordStatuses();
      completionShown = false;
      hideCompletion();
    });
    document.getElementById('btn-next-page').addEventListener('click', () => {
      hideCompletion();
      goToPage(currentPage + 1);
    });
  }
  document.getElementById('completion-pct').textContent = pct;
  banner.classList.remove('hidden');
}

function hideCompletion() {
  const banner = document.getElementById('completion');
  if (banner) banner.classList.add('hidden');
}

function resetWordStatuses() {
  lineElements.forEach((l) => l.wordEls.forEach((s) => {
    if (s.classList.contains('word')) s.className = 'word';
  }));
  score = { correct: 0, total: 0 };
  scoredLines = new Set();
  el.accuracy.textContent = 'دقة الصفحة: —';
}

function resetScore() {
  score = { correct: 0, total: 0 };
  el.accuracy.textContent = 'دقة: —';
  el.lastText.textContent = '';
}

/* ---------------- page navigation ---------------- */

function goToPage(n) {
  if (n < 1) n = 1;
  if (n > totalPages) n = totalPages;
  socket.emit('select_page', { page: n });
}

el.btnNext.addEventListener('click', () => goToPage(currentPage + 1));
el.btnPrev.addEventListener('click', () => goToPage(currentPage - 1));
el.pageInput.addEventListener('change', () => goToPage(parseInt(el.pageInput.value, 10) || 1));

/* ---------------- audio capture (raw PCM over socket) ---------------- */

const TARGET_SR = 16000;
const CHUNK_SECONDS = 2.5;
const CHUNK_LEN = Math.floor(TARGET_SR * CHUNK_SECONDS);
let audioCtx = null;
let pcmBuf = [];
let pending = new Float32Array(0);

function downsampleTo16k(samples, inputRate) {
  if (inputRate === TARGET_SR) return samples;
  const step = inputRate / TARGET_SR;
  const out = new Float32Array(Math.floor(samples.length / step));
  for (let i = 0; i < out.length; i++) {
    out[i] = samples[Math.floor(i * step)];
  }
  return out;
}

async function startRecording() {
  stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true } });
  audioCtx = new (window.AudioContext || window.webkitAudioContext)();
  const source = audioCtx.createMediaStreamSource(stream);
  const processor = audioCtx.createScriptProcessor(4096, 1, 1);
  processor.onaudioprocess = (e) => {
    const chunk = downsampleTo16k(e.inputBuffer.getChannelData(0), audioCtx.sampleRate);
    // append to pending
    const merged = new Float32Array(pending.length + chunk.length);
    merged.set(pending);
    merged.set(chunk, pending.length);
    pending = merged;
    if (pending.length >= CHUNK_LEN) {
      sendChunk(pending.slice(0, CHUNK_LEN));
      pending = pending.slice(CHUNK_LEN);
    }
  };
  source.connect(processor);
  processor.connect(audioCtx.destination); // keep alive
  recording = true;
  el.btnMic.classList.add('recording');
  el.micLabel.textContent = 'أوقف';
}

function stopRecording() {
  if (audioCtx) { audioCtx.close(); audioCtx = null; }
  if (stream) { stream.getTracks().forEach((t) => t.stop()); stream = null; }
  pending = new Float32Array(0);
  recording = false;
  el.btnMic.classList.remove('recording');
  el.micLabel.textContent = 'ابدأ';
}

function sendChunk(f32) {
  const buf = new ArrayBuffer(f32.length * 4);
  new Float32Array(buf).set(f32);
  const b64 = arrayBufferToBase64(buf);
  socket.emit('audio_chunk', { pcm: b64, sample_rate: TARGET_SR });
}

function arrayBufferToBase64(buffer) {
  const bytes = new Uint8Array(buffer);
  let bin = '';
  const CHUNK = 0x8000;
  for (let i = 0; i < bytes.length; i += CHUNK) {
    bin += String.fromCharCode.apply(null, bytes.subarray(i, i + CHUNK));
  }
  return btoa(bin);
}

el.btnMic.addEventListener('click', async () => {
  if (recording) { stopRecording(); return; }
  try {
    await startRecording();
  } catch (err) {
    alert('تعذر الوصول إلى الميكروفون: ' + err.message);
  }
});
