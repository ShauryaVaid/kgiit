const API_BASE = 'http://localhost:8000/api';

// Simple state
let sessionId = null;
let currentLessonIndex = 0;
let totalLessons = 1;
let trackId = window.api ? window.api.getTrackId() : 'git-basics';
const authToken = window.api ? window.api.getAuthToken() : '';

if (authToken) {
  axios.defaults.headers.common['X-Auth-Token'] = authToken;
}

const elements = {
  trackTitle: document.getElementById('track-title'),
  lessonTitle: document.getElementById('lesson-title'),
  lessonPrompt: document.getElementById('lesson-prompt'),
  scrollback: document.getElementById('scrollback'),
  cmdInput: document.getElementById('cmd-input'),
  statusBranch: document.getElementById('status-branch'),
  statusStaged: document.getElementById('status-staged'),
  statusUnstaged: document.getElementById('status-unstaged'),
  statusUntracked: document.getElementById('status-untracked'),
  statusCommit: document.getElementById('status-commit'),
  btnNext: document.getElementById('btn-next'),
  btnSkip: document.getElementById('btn-skip'),
  btnReset: document.getElementById('btn-reset'),
  btnQuit: document.getElementById('btn-quit'),
  progressBar: document.getElementById('progress-bar'),
  trackModal: document.getElementById('track-modal'),
  trackList: document.getElementById('track-list'),
  btnCloseModal: document.getElementById('btn-close-modal'),
  btnGitLog: document.getElementById('btn-git-log'),
  gitLogModal: document.getElementById('git-log-modal'),
  btnSelectRepo: document.getElementById('btn-select-repo'),
  gitLogPath: document.getElementById('git-log-path'),
  gitLogLoading: document.getElementById('git-log-loading'),
  gitLogError: document.getElementById('git-log-error'),
  gitLogEmpty: document.getElementById('git-log-empty'),
  gitLogTable: document.getElementById('git-log-table'),
  gitLogTbody: document.getElementById('git-log-tbody'),
  btnLoadMore: document.getElementById('btn-load-more'),
  btnCloseLogModal: document.getElementById('btn-close-log-modal'),
};

let currentLogRepo = '';
let currentLogSkip = 0;

function appendToScrollback(html) {
  const div = document.createElement('div');
  div.innerHTML = html;
  elements.scrollback.appendChild(div);
  elements.scrollback.scrollTop = elements.scrollback.scrollHeight;
}

function updateProgress() {
  if (totalLessons > 0) {
    const percent = Math.min(100, Math.round((currentLessonIndex / totalLessons) * 100));
    elements.progressBar.style.width = `${percent}%`;
  }
}

function appendCommand(cmd) {
  appendToScrollback(`
    <div class="cmd-line">
      <span class="cmd-prompt">~/sandbox $</span>
      <span class="cmd-text">${cmd}</span>
    </div>
  `);
}

function appendOutput(text, isError = false) {
  if (!text.trim()) return;
  // Escape html
  const escaped = text.replace(/</g, "&lt;").replace(/>/g, "&gt;");
  const cls = isError ? 'cmd-output cmd-error' : 'cmd-output';
  appendToScrollback(`<div class="${cls}">${escaped}</div>`);
}

function appendHint(hintText) {
  appendToScrollback(`<div class="cmd-hint">💡 Hint: ${hintText}</div>`);
}

function appendSuccess(msg) {
  appendToScrollback(`<div class="lesson-success">✅ [SUCCESS] ${msg}</div>`);
}

async function updateStatus() {
  if (!sessionId) return;
  try {
    const res = await axios.get(`${API_BASE}/session/${sessionId}/status`);
    const state = res.data;
    elements.statusBranch.textContent = state.branch || 'N/A';
    elements.statusStaged.textContent = state.staged?.length ?? 0;
    elements.statusUnstaged.textContent = state.unstaged?.length ?? 0;
    elements.statusUntracked.textContent = state.untracked?.length ?? 0;
    elements.statusCommit.textContent = state.last_commit || 'None';
  } catch (e) {
    console.error('Status update failed', e);
  }
}

async function startSession() {
  try {
    // No remote require in context isolation
    const res = await axios.post(`${API_BASE}/session/start`, { track_id: trackId });
    sessionId = res.data.session_id;
    totalLessons = res.data.total_lessons || 1;
    currentLessonIndex = res.data.current_index || 0;
    
    elements.trackTitle.textContent = res.data.track_title;
    elements.lessonTitle.textContent = res.data.lesson_title;
    elements.lessonPrompt.innerHTML = res.data.lesson_prompt.replace(/\n/g, '<br>');
    updateProgress();
    await updateStatus();
  } catch (e) {
    console.error('Failed to start session', e);
    elements.lessonTitle.textContent = 'Error: Could not connect to backend';
  }
}

async function setupLesson(index) {
  if (!sessionId) return;
  try {
    const args = await axios.get(`${API_BASE}/session/${sessionId}/status`); // Just checking if session alive
    const res = await axios.post(`${API_BASE}/session/${sessionId}/lesson/${index}/setup`, { track_id: trackId }).catch(e => e.response);
    
    if (res && res.status === 400 && res.data.detail === "Invalid track or lesson") {
      // Track complete
      currentLessonIndex = totalLessons;
      updateProgress();
      elements.lessonTitle.textContent = "Track Complete!";
      elements.lessonPrompt.innerHTML = `
        <div style="color:var(--success); font-size:1.1em; margin-bottom:15px;">🏆 TRACK COMPLETION CERTIFICATE 🏆</div>
        <div>Status: PASSED</div><br>
        <div style="color:var(--accent);">Ready to use your new skills on a real GitHub repository?</div>
        <div>Exit this sandbox and select <b>Door 1</b> from the main menu, or run:</div>
        <div><code style="color:var(--warning);">kgiit analyze --repo &lt;owner/name&gt;</code></div>
      `;
      elements.btnNext.disabled = true;
      elements.btnSkip.disabled = true;
      elements.cmdInput.disabled = true;
      appendToScrollback(`<hr style="border-color:#333; margin: 15px 0;">`);
      appendSuccess("Track Complete! You can close this window now.");
      return;
    }
    
    currentLessonIndex = res.data.current_index !== undefined ? res.data.current_index : index;
    totalLessons = res.data.total_lessons || totalLessons;
    
    elements.lessonTitle.textContent = res.data.lesson_title;
    elements.lessonPrompt.innerHTML = res.data.lesson_prompt.replace(/\n/g, '<br>');
    elements.btnNext.disabled = true;
    updateProgress();
    appendToScrollback(`<hr style="border-color:#333; margin: 15px 0;">`);
    await updateStatus();
  } catch (e) {
    console.error('Lesson setup failed', e);
  }
}

async function handleCommand(cmd) {
  if (!cmd.trim() || !sessionId) return;
  
  elements.cmdInput.disabled = true;
  appendCommand(cmd);
  
  try {
    // 1. Execute
    const execRes = await axios.post(`${API_BASE}/session/${sessionId}/execute`, { command: cmd });
    const { exit_code, stdout, stderr } = execRes.data;
    
    if (stdout) appendOutput(stdout);
    if (stderr) appendOutput(stderr, true);
    
    // 2. Verify
    const verifyRes = await axios.post(`${API_BASE}/session/${sessionId}/verify`, {
      track_id: trackId,
      lesson_index: currentLessonIndex,
      last_command: cmd,
      exit_code,
      stdout,
      stderr
    });
    
    if (verifyRes.data.passed) {
      appendSuccess(verifyRes.data.message);
      elements.btnNext.disabled = false;
      elements.btnNext.focus();
    } else {
      if (verifyRes.data.hint) {
        appendHint(verifyRes.data.hint);
      } else if (exit_code === 0 && cmd.startsWith('git ')) {
         appendHint(`That command succeeded, but didn't satisfy the lesson goal. Expected: ${verifyRes.data.expected_command}`);
      }
    }
    
    await updateStatus();
    
  } catch (e) {
    console.error('Command failed', e);
    appendOutput('Error communicating with backend API', true);
  } finally {
    elements.cmdInput.disabled = false;
    elements.cmdInput.value = '';
    elements.cmdInput.focus();
  }
}

// Event Listeners
elements.cmdInput.addEventListener('keydown', (e) => {
  if (e.key === 'Enter') {
    handleCommand(e.target.value);
  }
});

elements.btnNext.addEventListener('click', () => {
  setupLesson(currentLessonIndex + 1);
});

elements.btnSkip.addEventListener('click', () => {
  setupLesson(currentLessonIndex + 1);
});

elements.btnReset.addEventListener('click', () => {
  setupLesson(currentLessonIndex);
});

if (elements.btnQuit) {
  elements.btnQuit.addEventListener('click', async () => {
    try {
      const res = await axios.get(`${API_BASE}/tracks`);
      const tracks = res.data;
      elements.trackList.innerHTML = '';
      
      tracks.forEach(track => {
        const div = document.createElement('div');
        div.className = 'track-item';
        div.innerHTML = `
          <div class="track-title">${track.title}</div>
          <div class="track-desc">${track.description} (${track.lessons_count} lessons)</div>
        `;
        div.addEventListener('click', () => {
          trackId = track.id;
          elements.trackModal.style.display = 'none';
          elements.scrollback.innerHTML = '';
          startSession();
        });
        elements.trackList.appendChild(div);
      });
      
      elements.trackModal.style.display = 'block';
    } catch (e) {
      console.error('Failed to load tracks', e);
      appendError('Failed to load available tracks from server.');
    }
  });
}

if (elements.btnCloseModal) {
  elements.btnCloseModal.addEventListener('click', () => {
    elements.trackModal.style.display = 'none';
  });
}

// Git Log Logic
if (elements.btnGitLog) {
  elements.btnGitLog.addEventListener('click', () => {
    elements.gitLogModal.style.display = 'flex';
  });
}

if (elements.btnCloseLogModal) {
  elements.btnCloseLogModal.addEventListener('click', () => {
    elements.gitLogModal.style.display = 'none';
  });
}

if (elements.btnSelectRepo) {
  elements.btnSelectRepo.addEventListener('click', async () => {
    const dir = await window.api.selectDirectory();
    if (dir) {
      currentLogRepo = dir;
      currentLogSkip = 0;
      elements.gitLogTbody.innerHTML = '';
      fetchGitLog();
    }
  });
}

if (elements.btnLoadMore) {
  elements.btnLoadMore.addEventListener('click', () => {
    currentLogSkip += 500;
    fetchGitLog(true);
  });
}

async function fetchGitLog(append = false) {
  if (!currentLogRepo) return;
  
  elements.gitLogPath.textContent = `Viewing: ${currentLogRepo}`;
  elements.gitLogLoading.style.display = 'block';
  elements.gitLogError.style.display = 'none';
  if (!append) {
    elements.gitLogTable.style.display = 'none';
    elements.gitLogEmpty.style.display = 'none';
  }
  elements.btnLoadMore.style.display = 'none';

  try {
    const res = await axios.get(`${API_BASE}/git/log`, {
      params: { repo_path: currentLogRepo, skip: currentLogSkip }
    });
    
    elements.gitLogLoading.style.display = 'none';
    const commits = res.data.commits;

    if (!append && commits.length === 0) {
      elements.gitLogEmpty.style.display = 'block';
      return;
    }

    elements.gitLogTable.style.display = 'table';
    
    commits.forEach(c => {
      const tr = document.createElement('tr');
      tr.style.borderBottom = '1px solid #30363d';
      
      let refHtml = '';
      if (c.refs) {
        refHtml = `<span style="background: #1f6feb; color: white; padding: 2px 6px; border-radius: 10px; font-size: 0.8em; margin-right: 5px;">${c.refs}</span>`;
      }

      tr.innerHTML = `
        <td style="padding: 8px; color: #8b949e; font-family: monospace;">${c.hash.substring(0, 7)}</td>
        <td style="padding: 8px;">${refHtml}</td>
        <td style="padding: 8px;">${c.message}</td>
        <td style="padding: 8px; color: #8b949e;">${c.author}</td>
        <td style="padding: 8px; color: #8b949e;">${new Date(c.date).toLocaleString()}</td>
      `;
      elements.gitLogTbody.appendChild(tr);
    });

    if (commits.length === 500) {
      elements.btnLoadMore.style.display = 'block';
    }

  } catch (err) {
    elements.gitLogLoading.style.display = 'none';
    elements.gitLogError.style.display = 'block';
    const detail = err.response?.data?.detail || err.message;
    elements.gitLogError.textContent = `Error: ${detail}`;
  }
}

// Init
window.onload = startSession;
