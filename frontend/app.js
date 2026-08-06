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
  btnNext: document.getElementById('btn-next'),
  btnPrev: document.getElementById('btn-prev'),
  connDot: document.getElementById('conn-dot'),
  connText: document.getElementById('conn-text'),
  accuracy: document.getElementById('accuracy'),
  micStatus: document.getElementById('mic-status'),
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
  el.connText.textContent = 'Connected';
});

socket.on('disconnect', () => {
  el.connDot.classList.remove('online');
  el.connText.textContent = 'Disconnected';
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
  el.pageFooter.innerHTML = `Page ${data.page} — Madani Mushaf (15 lines)`;

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
    el.accuracy.textContent = `Accuracy: ${data.accuracy}%`;
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
    el.accuracy.textContent = `Page accuracy: ${pct}%`;

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
        <div class="completion-title">Well done! 🎉</div>
        <div class="completion-score">Page accuracy: <span id="completion-pct"></span>%</div>
        <div class="completion-actions">
          <button id="btn-retry" class="done-btn">Try again</button>
          <button id="btn-next-page" class="done-btn primary">Next page →</button>
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
  el.accuracy.textContent = 'Page accuracy: —';
}

function resetScore() {
  score = { correct: 0, total: 0 };
  el.accuracy.textContent = 'Accuracy: —';
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
const SILENCE_RMS_THRESHOLD = 0.004; // drop near-silent chunks before they reach the ASR
let audioCtx = null;
let pcmBuf = [];
let pending = new Float32Array(0);

function resampleTo16k(samples, inputRate) {
  const OUT = 16000;
  if (inputRate === OUT) return samples;
  const ratio = inputRate / OUT;
  if (ratio < 1) {
    const out = new Float32Array(Math.floor(samples.length * ratio));
    for (let i = 0; i < out.length; i++) {
      const pos = i / ratio;
      const i0 = Math.floor(pos);
      const i1 = Math.min(i0 + 1, samples.length - 1);
      out[i] = samples[i0] + (samples[i1] - samples[i0]) * (pos - i0);
    }
    return out;
  }
  // decimate: low-pass (Hamming-windowed sinc) before downsampling to avoid aliasing
  const fc = 0.45 / ratio;
  const ntaps = Math.max(9, (Math.round(8 * ratio) | 1));
  const center = (ntaps - 1) / 2;
  const kernel = new Float32Array(ntaps);
  let sum = 0;
  for (let n = 0; n < ntaps; n++) {
    const x = n - center;
    let h = x === 0 ? 2 * fc : Math.sin(2 * Math.PI * fc * x) / (Math.PI * x);
    h *= 0.54 - 0.46 * Math.cos((2 * Math.PI * n) / (ntaps - 1));
    kernel[n] = h;
    sum += h;
  }
  for (let n = 0; n < ntaps; n++) kernel[n] /= sum;

  const outLen = Math.floor(samples.length / ratio);
  const padded = new Float32Array(samples.length + ntaps);
  padded.set(samples, Math.floor(center));
  const out = new Float32Array(outLen);
  for (let i = 0; i < outLen; i++) {
    const start = Math.floor(i * ratio);
    let acc = 0;
    for (let k = 0; k < ntaps; k++) acc += padded[start + k] * kernel[k];
    out[i] = acc;
  }
  return out;
}

function rms(samples) {
  let acc = 0;
  for (let i = 0; i < samples.length; i++) acc += samples[i] * samples[i];
  return Math.sqrt(acc / samples.length);
}

async function startRecording() {
  stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true } });
  audioCtx = new (window.AudioContext || window.webkitAudioContext)();
  const source = audioCtx.createMediaStreamSource(stream);
  const processor = audioCtx.createScriptProcessor(4096, 1, 1);
  processor.onaudioprocess = (e) => {
    const chunk = resampleTo16k(e.inputBuffer.getChannelData(0), audioCtx.sampleRate);
    // append to pending
    const merged = new Float32Array(pending.length + chunk.length);
    merged.set(pending);
    merged.set(chunk, pending.length);
    pending = merged;
    if (pending.length >= CHUNK_LEN) {
      const buf = pending.slice(0, CHUNK_LEN);
      pending = pending.slice(CHUNK_LEN);
      if (rms(buf) >= SILENCE_RMS_THRESHOLD) sendChunk(buf);
    }
  };
  source.connect(processor);
  processor.connect(audioCtx.destination); // keep alive
  recording = true;
  el.btnMic.classList.add('recording');
  el.micLabel.textContent = 'Stop';
  setMicStatus('');
}

function stopRecording() {
  if (audioCtx) { audioCtx.close(); audioCtx = null; }
  if (stream) { stream.getTracks().forEach((t) => t.stop()); stream = null; }
  pending = new Float32Array(0);
  recording = false;
  el.btnMic.classList.remove('recording');
  el.micLabel.textContent = 'Start';
  setMicStatus('');
}

function setMicStatus(msg, isError) {
  el.micStatus.textContent = msg;
  el.micStatus.classList.toggle('error', !!isError);
}

function sendChunk(f32) {
  // float32 [-1,1] -> 16-bit PCM LE (half the upload size over the tunnel)
  const i16 = new Int16Array(f32.length);
  for (let i = 0; i < f32.length; i++) {
    const s = f32[i];
    i16[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
  }
  const b64 = arrayBufferToBase64(i16.buffer);
  socket.emit('audio_chunk', { pcm: b64, sample_rate: TARGET_SR, format: 'i16' });
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
  setMicStatus('');
  try {
    await startRecording();
    setMicStatus('Listening…');
  } catch (err) {
    const n = err.name;
    let msg;
    if (n === 'NotAllowedError') {
      msg = 'Microphone blocked. Click the mic/padlock icon in the address bar and allow the microphone, then try again.';
    } else if (n === 'NotFoundError') {
      msg = 'No microphone found. Plug one in or check your input device, then refresh the page.';
    } else if (n === 'NotReadableError') {
      msg = 'Microphone is in use by another app. Close it, then try again.';
    } else if (!window.isSecureContext) {
      msg = 'Microphone needs a secure connection. Open https://localhost:5001 (not the LAN IP / http).';
    } else {
      msg = 'Could not access the microphone: ' + (err.message || n);
    }
    setMicStatus(msg, true);
  }
});
