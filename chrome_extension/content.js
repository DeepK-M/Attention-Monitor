// content.js — Runs inside Google Meet tab
// Captures student video tiles and sends to Flask server

const SERVER_URL = 'http://localhost:5000';
const INTERVAL_MS = 3000;

let studentData = {};
let isRunning   = false;
let intervalId  = null;

// ── Wait for Meet to load ──────────────────────────────────────
function waitForMeet() {
  console.log('[AttentionMonitor] Waiting for Google Meet...');
  const observer = new MutationObserver(() => {
    const videos = document.querySelectorAll('video');
    if (videos.length > 0) {
      observer.disconnect();
      console.log('[AttentionMonitor] Meet loaded! Starting monitor...');
      startMonitoring();
    }
  });
  observer.observe(document.body, { childList: true, subtree: true });
}

// ── Start/stop monitoring ──────────────────────────────────────
function startMonitoring() {
  if (isRunning) return;
  isRunning  = true;
  intervalId = setInterval(analyseAllStudents, INTERVAL_MS);
  console.log('[AttentionMonitor] Monitoring started!');
  injectOverlayStyles();
}

function stopMonitoring() {
  isRunning = false;
  if (intervalId) clearInterval(intervalId);
  console.log('[AttentionMonitor] Monitoring stopped!');
}

// ── Global name registry — scraped from entire page ───────────
// Maps video element → assigned name, persisted across cycles
const videoNameMap = new WeakMap();

function getAllNamesFromPage() {
  /**
   * Scrape every participant name visible anywhere on the page.
   * Sources checked (in priority order):
   *   1. "More options for NAME" aria/button text
   *   2. data-participant-id or data-ssrc attributes near videos
   *   3. ALL-CAPS name overlays on tiles  e.g. "GAURI DONGARE"
   *   4. Participants panel list items
   */
  const names = new Set();
  const skip  = new Set([
    'reframe','raising hand','gemini','others might see','backgrounds',
    'more options','leave call','share screen','raise hand','meeting details',
    'people','chat','host controls','call ends in','audio','video','turn off',
    'send','mute','unmute','pin','spotlight','remove','report','you',
    'present now','turn on','everyone','microphone','camera'
  ]);

  document.querySelectorAll('*').forEach(el => {
    // "More options for NAME"
    const aria = el.getAttribute('aria-label') || '';
    if (aria.startsWith('More options for ')) {
      names.add(aria.replace('More options for ', '').trim());
      return;
    }

    // Leaf text nodes only
    if (el.children.length > 0) return;
    const txt = el.textContent?.trim();
    if (!txt || txt.length < 2 || txt.length > 45) return;

    const lower = txt.toLowerCase();
    if ([...skip].some(s => lower.includes(s))) return;
    if (!/[A-Za-z]/.test(txt)) return;
    if (/^\d+$/.test(txt)) return;          // pure numbers
    if (txt.split(' ').length > 5) return;  // too many words

    names.add(txt);
  });

  return [...names];
}

function assignNamesToVideos(videos) {
  /**
   * Strategy:
   * 1. Check if video already has a confirmed name stored
   * 2. Try to find name inside the tile's own DOM subtree
   * 3. Fall back to page-wide name list, assign unmatched names by tile size
   *    (largest tile = main participant = other person, smallest = self-view)
   */

  // Step 1 — collect names already confirmed for each video
  const confirmed = new Map(); // video → name
  for (const video of videos) {
    if (videoNameMap.has(video)) {
      confirmed.set(video, videoNameMap.get(video));
    }
  }

  // Step 2 — try per-tile DOM search for unconfirmed videos
  for (const video of videos) {
    if (confirmed.has(video)) continue;

    // Search up to 12 levels up for "More options for NAME"
    let p = video.parentElement;
    for (let d = 0; d < 12; d++) {
      if (!p) break;
      const allEls = p.querySelectorAll('*');
      for (const el of allEls) {
        const aria = el.getAttribute('aria-label') || '';
        if (aria.startsWith('More options for ')) {
          const name = aria.replace('More options for ', '').trim();
          confirmed.set(video, name);
          videoNameMap.set(video, name);
          break;
        }
        const txt = el.textContent?.trim();
        if (txt?.startsWith('More options for ')) {
          const name = txt.replace('More options for ', '').trim();
          confirmed.set(video, name);
          videoNameMap.set(video, name);
          break;
        }
      }
      if (confirmed.has(video)) break;
      p = p.parentElement;
    }
  }

  // Step 3 — for still-unconfirmed tiles, use page-wide name list
  const unconfirmed = videos.filter(v => !confirmed.has(v));
  if (unconfirmed.length > 0) {
    const pageNames   = getAllNamesFromPage();
    const usedNames   = new Set([...confirmed.values()]);
    const unusedNames = pageNames.filter(n => !usedNames.has(n));

    const sorted = [...unconfirmed].sort((a, b) =>
      (b.videoWidth * b.videoHeight) - (a.videoWidth * a.videoHeight)
    );

    sorted.forEach((video, i) => {
      const name = unusedNames[i] || `Student_${i + 1}`;
      confirmed.set(video, name);
      videoNameMap.set(video, name);
      console.log(`[AttentionMonitor] Assigned "${name}" to ${video.videoWidth}x${video.videoHeight} via page scan`);
    });
  }

  // Step 4 — deduplicate: if two tiles have same name, the LARGER tile
  // is the remote participant — rename it "Participant_2" etc.
  const nameToVideos = {};
  for (const [video, name] of confirmed) {
    if (!nameToVideos[name]) nameToVideos[name] = [];
    nameToVideos[name].push(video);
  }

  for (const [name, vids] of Object.entries(nameToVideos)) {
    if (vids.length < 2) continue;
    // Keep smallest tile (self-view) with original name, rename larger ones
    vids.sort((a, b) => (a.videoWidth * a.videoHeight) - (b.videoWidth * b.videoHeight));
    for (let i = 1; i < vids.length; i++) {
      const newName = `Participant_${i + 1}`;
      confirmed.set(vids[i], newName);
      videoNameMap.set(vids[i], newName);
      console.log(`[AttentionMonitor] Deduplicated "${name}" to "${newName}" for ${vids[i].videoWidth}x${vids[i].videoHeight}`);
    }
  }

  return confirmed;
}

// Keep for backward compat (used in text input handler)
function getStudentName(video, index) {
  if (videoNameMap.has(video)) return videoNameMap.get(video);
  return `Student_${index + 1}`;
}

// ── Analyse all visible video tiles ───────────────────────────
async function analyseAllStudents() {
  const allVideos = document.querySelectorAll('video');
  if (allVideos.length === 0) return;

  // Filter to only active video tiles
  const videos = [...allVideos].filter(v =>
    v.readyState >= 2 &&
    v.videoWidth > 0 &&
    v.videoHeight > 0 &&
    !v.paused &&
    !v.ended
  );

  if (videos.length === 0) return;
  console.log(`[AttentionMonitor] Analysing ${videos.length} video tiles...`);

  // ✅ Assign real names to all tiles at once using page-wide scan
  const nameMap = assignNamesToVideos(videos);

  for (let i = 0; i < videos.length; i++) {
    const video     = videos[i];
    const studentId = nameMap.get(video) || `Student_${i + 1}`;

    try {
      const frames = captureFrames(video);
      const text   = await getStudentTextAsync(studentId);

      console.log(`[AttentionMonitor] Tile ${i} → id="${studentId}" size=${video.videoWidth}x${video.videoHeight}`);

      const result = await sendToServer(frames, text, studentId);

      if (result && !result.error) {
        studentData[studentId] = result;
        updateOverlay(video, result, studentId);
        notifyDashboard(studentData);
        console.log(`[AttentionMonitor] ${studentId} → ${result.final_label} (${result.attention_score})`);
      } else {
        console.log(`[AttentionMonitor] ${studentId} error:`, result?.error);
      }

    } catch (err) {
      console.log(`[AttentionMonitor] Error on tile ${i}:`, err.message);
    }
  }
}

// ── Capture frames from a video element ───────────────────────
function captureFrames(video, count = 20) {
  // ✅ FIX: Scale DOWN to max 640px on longest side (not MAX which kept 1280px)
  const vw    = video.videoWidth;
  const vh    = video.videoHeight;
  const scale = Math.min(1.0, 640 / Math.max(vw, vh));
  const cw    = Math.round(vw * scale);
  const ch    = Math.round(vh * scale);

  console.log(`[AttentionMonitor] Canvas size: ${cw}x${ch} (video: ${vw}x${vh})`);

  const canvas  = document.createElement('canvas');
  canvas.width  = cw;
  canvas.height = ch;
  const ctx     = canvas.getContext('2d');
  const frames  = [];

  for (let i = 0; i < count; i++) {
    ctx.drawImage(video, 0, 0, cw, ch);
    frames.push(canvas.toDataURL('image/jpeg', 0.85));
  }
  return frames;
}

// ── Send frames to Flask server ────────────────────────────────
async function sendToServer(frames, text, studentId) {
  try {
    const response = await fetch(`${SERVER_URL}/predict`, {
      method : 'POST',
      headers: { 'Content-Type': 'application/json' },
      body   : JSON.stringify({ frames, text, student_id: studentId })
    });
    const data = await response.json();
    if (!response.ok) {
      console.log(`[AttentionMonitor] Server error ${response.status}:`, data);
      return null;
    }
    return data;
  } catch (err) {
    console.log('[AttentionMonitor] Fetch error:', err.message);
    return null;
  }
}

// ── Get text typed by student ──────────────────────────────────
async function getStudentTextAsync(studentId) {
  return new Promise(resolve => {
    try {
      if (typeof chrome === 'undefined' || !chrome.storage?.local) {
        resolve(''); return;
      }
      chrome.storage.local.get([`text_${studentId}`], result => {
        resolve(result[`text_${studentId}`] || '');
      });
    } catch(e) { resolve(''); }
  });
}

// ── Inject CSS for overlays ────────────────────────────────────
function injectOverlayStyles() {
  if (document.getElementById('am-styles')) return;
  const style = document.createElement('style');
  style.id = 'am-styles';
  style.textContent = `
    .am-overlay-badge {
      position: absolute;
      top: 10px; left: 10px;
      padding: 5px 12px;
      border-radius: 20px;
      font-size: 13px; font-weight: 700;
      font-family: Arial, sans-serif;
      z-index: 99999; pointer-events: none;
      backdrop-filter: blur(6px);
      box-shadow: 0 2px 8px rgba(0,0,0,0.3);
    }
    .am-score-bar {
      position: absolute; bottom: 0; left: 0;
      height: 4px; border-radius: 0 2px 0 0;
      transition: width 0.5s ease;
      z-index: 99999; pointer-events: none;
    }
  `;
  document.head.appendChild(style);
}

// ── Update overlay badge on video tile ────────────────────────
function updateOverlay(video, result, studentId) {
  const label = result.final_label;
  const score = result.attention_score;

  const emojis = {
    'Attentive'   : '✅ Attentive',
    'Bored'       : '😴 Bored',
    'Confused'    : '🤔 Confused',
    'Frustrated'  : '😤 Frustrated',
    'Camera Away' : '📷 Camera Away'
  };
  const colors = {
    'Attentive'   : '#00E5A0',
    'Bored'       : '#FFB830',
    'Confused'    : '#38BDF8',
    'Frustrated'  : '#FF5F7E',
    'Camera Away' : '#6B7280'
  };

  const color = colors[label] || '#FFFFFF';

  let container = video.parentElement;
  for (let i = 0; i < 8; i++) {
    if (!container) break;
    const rect = container.getBoundingClientRect();
    if (rect.width > 100 && rect.height > 100) break;
    container = container.parentElement;
  }
  if (!container) return;
  container.style.position = 'relative';

  // Remove old overlays
  container.querySelectorAll('.am-overlay-badge, .am-score-bar').forEach(el => el.remove());

  // Badge
  const badge = document.createElement('div');
  badge.className = 'am-overlay-badge';
  badge.style.cssText = `background:${color}33; color:${color}; border:1px solid ${color}88;`;
  badge.textContent = emojis[label] || label;
  container.appendChild(badge);

  // Score bar
  const bar = document.createElement('div');
  bar.className = 'am-score-bar';
  bar.style.cssText = `width:${score}%; background:${color};`;
  container.appendChild(bar);
}

// ── Notify dashboard popup ────────────────────────────────────
function notifyDashboard(data) {
  try {
    if (typeof chrome === 'undefined' || !chrome.storage?.local) return;
    chrome.storage.local.set({ studentData: data });
  } catch(e) {
    console.log('[AttentionMonitor] Storage error — stopping');
    stopMonitoring();
  }
}

// ── Listen for messages from dashboard ───────────────────────
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.action === 'getStatus')
    sendResponse({ isRunning, studentCount: Object.keys(studentData).length });
  if (msg.action === 'stop') { stopMonitoring(); sendResponse({ ok: true }); }
  if (msg.action === 'start') { startMonitoring(); sendResponse({ ok: true }); }
  if (msg.action === 'getData') sendResponse({ studentData });
});

// ── Inject floating text input box ───────────────────────────
function injectTextInput() {
  if (document.getElementById('am-text-box')) return;

  const box = document.createElement('div');
  box.id = 'am-text-box';
  box.style.cssText = `
    position: fixed; bottom: 80px; right: 20px;
    z-index: 99999; background: #1C2035;
    border: 1px solid rgba(0,229,160,0.3);
    border-radius: 12px; padding: 10px 12px;
    width: 280px; box-shadow: 0 4px 20px rgba(0,0,0,0.4);
    font-family: Arial, sans-serif;
  `;
  box.innerHTML = `
    <div style="font-size:11px;color:#6B7280;margin-bottom:6px;
                display:flex;justify-content:space-between;align-items:center;">
      <span>🎓 How are you feeling?</span>
      <span id="am-close" style="cursor:pointer;color:#6B7280;font-size:14px;">×</span>
    </div>
    <div style="display:flex;gap:6px;">
      <input id="am-text-input" type="text" placeholder="e.g. I don't understand..."
        style="flex:1;background:#0D0F1A;border:1px solid rgba(255,255,255,0.1);
               border-radius:8px;padding:7px 10px;color:white;font-size:12px;
               outline:none;font-family:Arial,sans-serif;" />
      <button id="am-send-btn" style="background:#00E5A0;color:#0D0F1A;border:none;
        border-radius:8px;padding:7px 12px;font-size:12px;font-weight:700;
        cursor:pointer;font-family:Arial,sans-serif;">Send</button>
    </div>
    <div id="am-text-result" style="margin-top:6px;font-size:11px;color:#6B7280;min-height:16px;"></div>
  `;
  document.body.appendChild(box);

  document.getElementById('am-send-btn').addEventListener('click', async () => {
    const input  = document.getElementById('am-text-input');
    const result = document.getElementById('am-text-result');
    const text   = input.value.trim();
    if (!text) return;

    result.textContent = '⏳ Analysing...';
    result.style.color = '#6B7280';

    try {
      const res  = await fetch('http://localhost:5000/predict_text', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text })
      });
      const data = await res.json();

      const colors = { Attentive:'#00E5A0', Bored:'#FFB830', Confused:'#38BDF8', Frustrated:'#FF5F7E' };
      const emojis = { Attentive:'✅', Bored:'😴', Confused:'🤔', Frustrated:'😤' };

      result.textContent = `${emojis[data.label]} ${data.label} (${(data.confidence*100).toFixed(0)}%)`;
      result.style.color = colors[data.label];

      // ✅ Save text keyed per student tile (not hardcoded student_0)
      if (chrome?.storage?.local) {
        const videos = document.querySelectorAll('video');
        videos.forEach((v, i) => {
          const name = getStudentName(v, i);
          chrome.storage.local.set({ [`text_${name}`]: text });
          setTimeout(() => chrome.storage.local.remove([`text_${name}`]), 30000);
        });
      }

      input.value = '';
    } catch (err) {
      result.textContent = '❌ Server offline';
      result.style.color = '#FF5F7E';
    }
  });

  document.getElementById('am-text-input').addEventListener('keypress', e => {
    if (e.key === 'Enter') document.getElementById('am-send-btn').click();
  });

  document.getElementById('am-close').addEventListener('click', () => {
    box.style.display = 'none';
  });
}

// ── Start ─────────────────────────────────────────────────────
waitForMeet();

const textBoxInterval = setInterval(() => {
  if (!document.getElementById('am-text-box')) injectTextInput();
  else clearInterval(textBoxInterval);
}, 2000);