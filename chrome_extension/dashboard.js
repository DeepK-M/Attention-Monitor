// dashboard.js — Teacher dashboard logic

const COLORS = {
  Attentive : '#00E5A0',
  Bored     : '#FFB830',
  Confused  : '#38BDF8',
  Frustrated: '#FF5F7E'
};

const EMOJIS = {
  Attentive : '✅',
  Bored     : '😴',
  Confused  : '🤔',
  Frustrated: '😤'
};

const ICONS = [
  '👨‍💻','👩‍💻','🧑‍💻','👨‍🎓','👩‍🎓',
  '🧑‍🎓','👦','👧','🧒','👤'
];

let isPaused    = false;
let sessionData = {};

// ── Check server health ───────────────────────────────────────
async function checkServer() {
  try {
    const res = await fetch('http://localhost:5000/health');
    if (res.ok) {
      document.getElementById('offlineMsg').style.display   = 'none';
      document.getElementById('statusBadge').className      = 'status-badge';
      document.getElementById('statusBadge').textContent    = '● LIVE';
    }
  } catch {
    document.getElementById('offlineMsg').style.display     = 'block';
    document.getElementById('statusBadge').className        = 'status-badge offline';
    document.getElementById('statusBadge').textContent      = '● OFFLINE';
  }
}

// ── Load data from storage ────────────────────────────────────
function loadData() {
  chrome.storage.local.get(['studentData'], (result) => {
    if (result.studentData) {
      sessionData = result.studentData;
      updateDashboard(sessionData);
    }
  });
}

// ── Update entire dashboard ───────────────────────────────────
function updateDashboard(data) {
  const students = Object.values(data);
  if (students.length === 0) return;

  // ── Stats ──
  const avgScore = Math.round(
    students.reduce((s, r) => s + r.attention_score, 0) / students.length
  );

  const counts = { Attentive:0, Bored:0, Confused:0, Frustrated:0 };
  students.forEach(s => counts[s.final_label]++);

  const alerts = students.filter(
    s => s.final_label === 'Frustrated' || s.final_label === 'Confused'
  );

  document.getElementById('avgScore').textContent      = avgScore;
  document.getElementById('totalStudents').textContent = students.length;
  document.getElementById('alertCount').textContent    = alerts.length;
  document.getElementById('attentiveCount').textContent= counts.Attentive;

  // ── Distribution bar ──
  const total = students.length;
  document.getElementById('barAttentive').style.width =
    `${(counts.Attentive  / total * 100).toFixed(0)}%`;
  document.getElementById('barConfused').style.width  =
    `${(counts.Confused   / total * 100).toFixed(0)}%`;
  document.getElementById('barBored').style.width     =
    `${(counts.Bored      / total * 100).toFixed(0)}%`;
  document.getElementById('barFrustrated').style.width=
    `${(counts.Frustrated / total * 100).toFixed(0)}%`;

  // ── Student list ──
  const listEl = document.getElementById('studentList');
  listEl.innerHTML = '';

  // Sort by score ascending (struggling students first)
  const sorted = [...students].sort((a,b) =>
    a.attention_score - b.attention_score
  );

  sorted.forEach((student, i) => {
    const label = student.final_label;
    const score = student.attention_score;
    const color = COLORS[label];
    const emoji = EMOJIS[label];
    const icon  = ICONS[i % ICONS.length];

    const item = document.createElement('div');
    item.className = 'student-item';
    item.innerHTML = `
      <div class="student-icon">${icon}</div>
      <div class="student-info">
        <div class="student-name">${student.student_id || 'Student ' + (i+1)}</div>
        <div class="student-state">
          ${emoji} ${label} ·
          Vision: ${student.vision_label} ·
          NLP: ${student.nlp_label}
        </div>
      </div>
      <div class="student-score" style="color:${color}">${score}</div>
    `;
    listEl.appendChild(item);
  });

  // ── Alerts ──
  const alertsSection = document.getElementById('alertsSection');
  const alertsList    = document.getElementById('alertsList');
  alertsList.innerHTML = '';

  if (alerts.length > 0) {
    alertsSection.style.display = 'block';
    alerts.forEach((student, i) => {
      const isFrust = student.final_label === 'Frustrated';
      const div     = document.createElement('div');
      div.className = `alert alert-${isFrust ? 'frustrated' : 'confused'}`;
      div.innerHTML = `
        <span>${isFrust ? '🚨' : '💡'}</span>
        <span>
          <strong>${student.student_id || 'Student'}</strong>
          is ${student.final_label.toLowerCase()} —
          score: ${student.attention_score}/100
        </span>
      `;
      alertsList.appendChild(div);
    });
  } else {
    alertsSection.style.display = 'none';
  }
}

// ── Export session data ───────────────────────────────────────
function exportData() {
  const students = Object.values(sessionData);
  if (students.length === 0) {
    alert('No data to export yet!');
    return;
  }

  const rows = ['Student ID,Label,Score,Vision,NLP,Confidence'];
  students.forEach(s => {
    rows.push([
      s.student_id,
      s.final_label,
      s.attention_score,
      s.vision_label,
      s.nlp_label,
      s.confidence
    ].join(','));
  });

  const csv  = rows.join('\n');
  const blob = new Blob([csv], { type: 'text/csv' });
  const url  = URL.createObjectURL(blob);
  const a    = document.createElement('a');
  a.href     = url;
  a.download = `attention_report_${Date.now()}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

// ── Button handlers ───────────────────────────────────────────
document.getElementById('btnStop').addEventListener('click', () => {
  isPaused = !isPaused;

  // Send message to content.js
  chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
    if (tabs[0]) {
      chrome.tabs.sendMessage(tabs[0].id, {
        action: isPaused ? 'stop' : 'start'
      });
    }
  });

  const btn = document.getElementById('btnStop');
  btn.textContent = isPaused ? '▶ Resume' : '⏸ Pause';
  btn.style.background = isPaused ? '#FF5F7E' : '';
  btn.style.color      = isPaused ? '#0D0F1A' : '';
});

document.getElementById('btnExport').addEventListener('click', exportData);

// ── Auto refresh every 3 seconds ─────────────────────────────
checkServer();
loadData();

setInterval(() => {
  if (!isPaused) loadData();
}, 3000);

setInterval(checkServer, 10000);