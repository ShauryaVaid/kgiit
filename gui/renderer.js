const API_BASE = 'http://localhost:8000/api';

// Simple state
let sessionId = null;
let currentLessonIndex = 0;
let totalLessons = 1;
let trackId = window.api ? window.api.getTrackId() : 'git-basics';

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
};

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
    elements.statusStaged.textContent = state.staged_files ? state.staged_files.length : 0;
    elements.statusUnstaged.textContent = state.unstaged_files ? state.unstaged_files.length : 0;
    elements.statusUntracked.textContent = state.untracked_files ? state.untracked_files.length : 0;
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

// Init
window.onload = startSession;
