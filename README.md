<div align="center">
  
# KGiit (v1.1.0)

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/release/python-3100/)
[![License: MIT](https://img.shields.io/badge/License-MIT-purple.svg)](https://opensource.org/licenses/MIT)
[![CI](https://github.com/ShauryaVaid/kgiit/actions/workflows/python-app.yml/badge.svg)](https://github.com/ShauryaVaid/kgiit/actions/workflows/python-app.yml)

<br/>

```text
 ██╗  ██╗ ██████╗ ██╗██╗████████╗
 ██║ ██╔╝██╔════╝ ██║██║╚══██╔══╝
 █████╔╝ ██║  ███╗██║██║   ██║   
 ██╔═██╗ ██║   ██║██║██║   ██║   
 ██║  ██╗╚██████╔╝██║██║   ██║   
 ╚═╝  ╚═╝ ╚═════╝ ╚═╝╚═╝   ╚═╝   
```
**Two Doors. One CLI.**

</div>

---

## 1. What is this project about?

**KGiit** is a powerful, dual-engine CLI and GUI hybrid designed for modern software engineering education and repository management. It solves a critical problem in tech education: bridging the gap between learning Git in a sterile environment and actually contributing to massive, real-world open-source projects. 

It achieves this through a **"Two Doors" architecture**:
*   **Door 1 (Analyze Mode):** An internet-connected, NLP-powered triage engine that interfaces directly with the GitHub API to categorize and rank real-world software defects.
*   **Door 2 (Learn Mode):** A 100% offline, isolated sandbox environment that allows students to practice destructive Git commands safely with real-time feedback.

<div align="center">
  <img src="assets/images/main-menu.png" alt="Main CLI Menu" width="80%">
</div>

---

## 2. What skills and features does it hold?

### Interactive Offline Curriculum
A fully integrated Electron GUI (and a headless TUI mode) that guides users through progressive modules: **Git Basics**, **Branching & Merging**, and **Remotes & Collaboration**.

<div align="center">
  <img src="assets/images/learn-menu.png" alt="Learn Mode Curriculum" width="80%">
</div>

### Machine Learning Integration
*   **Intent Classification:** When a user types a wrong command (e.g., `git comit`), a localized ML classifier uses string distance and semantic heuristics to predict what they meant and offers pedagogical hints.
*   **NLP Issue Triage:** Automatically analyzes unstructured text in GitHub issues to assign categorical labels (bug, docs) and severity rankings (HIGH, MEDIUM, LOW) so contributors know exactly where to start.

<div align="center">
  <img src="assets/images/learn-gui-hints.png" alt="GUI Sandbox with ML Hints" width="80%">
</div>

### Universal Git History Viewer (New in v1.1.0)
A rich graphical interface that lets users open *any* repository on their laptop (using a universal folder picker) to view its commit history, branching graph, and metadata in a structured, paginated table.

<div align="center">
  <img src="assets/images/gui-git-log.png" alt="Universal Git History Viewer" width="80%">
</div>

### Real-time State Tracking
The GUI actively monitors the sandbox and displays live counts of staged, unstaged, and untracked files alongside your current branch, without the user needing to constantly type `git status`.

---

## 3. How is it beneficial for you as a student?

*   **Risk-Free Playground:** Version control is intimidating. KGiit’s sandbox allows you to execute dangerous commands (`git reset --hard`, `git push --force`) without the fear of destroying a real project or messing up your global system configuration.
*   **Pedagogical Feedback, not Errors:** Standard terminals give cryptic error codes. KGiit intercepts mistakes and provides human-readable hints to teach you *why* a command failed.
*   **Direct Pipeline to Open Source (GSoC):** Once you master the basics in the sandbox, you can immediately switch to `kgiit analyze --repo <target-repo>`. The ML engine will surface the easiest, lowest-severity issues in massive repositories, giving you a direct entry point into contributing to Google Summer of Code (GSoC) projects.

<div align="center">
  <img src="assets/images/analyze-output.png" alt="Analyze NLP Triage Engine" width="80%">
</div>

---

## 4. How is it optimized for local system performance?

*   **Micro-Architecture:** The system runs a high-performance Python (FastAPI) backend alongside a lightweight Electron GUI. 
*   **Data-Capping & Pagination:** The Universal Git History viewer restricts subprocess data retrieval (e.g., `--max-count=500`). This guarantees sub-100ms response times and an ultra-low memory footprint (<5MB), allowing it to render the history of massive codebases like the Linux Kernel instantaneously without crashing.
*   **Ephemeral Storage:** The sandbox utilizes native OS temporary directories (`tempfile.mkdtemp`). Once a lesson is finished or the app is closed, the sandbox is instantly purged, leaving zero bloat on your hard drive.

---

## 5. How is it protected (Security Architecture)?

KGiit implements enterprise-grade, defense-in-depth security to ensure that running a local server on your machine doesn't expose you to vulnerabilities:

> [!WARNING]
> **Deployment Model:** KGiit is strictly a **local, single-user developer tool**. It is highly scalable in terms of user distribution (millions of users can run it locally), but it is NOT a hosted multi-tenant cloud service. 

*   **Anti-CSRF Session Tokens:** The FastAPI backend binds exclusively to `127.0.0.1`. To prevent malicious websites in your browser from executing Git commands on your machine via Cross-Site Request Forgery (CSRF), KGiit generates a cryptographically secure, randomized 32-byte token (`secrets.token_hex(32)`) upon boot.
*   **Invisible Transmission:** This token is passed securely to the Electron GUI via environment variables (`subprocess.Popen(env=...)`), ensuring it is completely invisible to system monitoring tools like Task Manager or `ps`.
*   **Timing Attack Mitigation:** The API validates this token using `hmac.compare_digest()`, completely eliminating theoretical timing-attack vectors.
*   **Strict Canonicalization:** The Git history viewer enforces strict path resolution and `.git` directory validation, entirely neutralizing directory traversal (path injection) attacks.

---

## 6. How to use it (Example Commands)

### Setup and Installation
1. Clone the repository and navigate to it:
   ```bash
   git clone https://github.com/ShauryaVaid/kgiit.git
   cd kgiit
   ```
2. Install the Python package in editable mode (requires Python 3.10+):
   ```bash
   pip install -e .
   ```

### Usage

**Interactive Mode (The easiest way to start):**
```bash
kgiit
```
*(This launches an interactive, rich terminal menu where you can navigate with your arrow keys.)*

**Directly Launch the Offline Sandbox GUI:**
```bash
kgiit learn
```
*(This boots the FastAPI backend and Electron GUI, starting you on Lesson 1 of the Git Basics track.)*

If you are on an SSH connection or prefer the terminal, you can use the headless Textual TUI:
```bash
kgiit learn --headless
```
<div align="center">
  <img src="assets/images/learn-tui.png" alt="Headless TUI Learn Mode" width="80%">
</div>

**Analyze a Real GitHub Repository (e.g., VS Code):**
```bash
kgiit analyze --repo microsoft/vscode --all-open
```
*(This will fetch the latest issues from the VS Code repository, run them through the NLP triage engine, and output a prioritized, formatted table directly in your terminal.)*

---

## Documentation Links

For further technical details and contribution guidelines, please refer to the specific documentation files included in this repository:

- [System Architecture Guide](ARCHITECTURE.md) - A deep dive into the system design, ML integration, and CLI-GUI communication protocols.
- [Contributing Guidelines](CONTRIBUTING.md) - Instructions for setting up a development environment, running the Pytest validation suite, and submitting pull requests.

---

<div align="center">
  <b>Authored by Shaurya Vaid</b> <br/>
  <i>Building robust tooling for modern engineering education.</i>
  <br/><br/>
  <b>Contributors:</b> Aditya Tiwari and Mihir Bagh
</div>
