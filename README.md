<div align="center">
  
# KGiit (v1.0.0)

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/release/python-3100/)
[![License: MIT](https://img.shields.io/badge/License-MIT-purple.svg)](https://opensource.org/licenses/MIT)
[![Build Status](https://img.shields.io/badge/build-passing-brightgreen)]()

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

## 🚀 Overview

**KGiit** is a powerful, dual-engine Command Line Interface designed for modern developers and students. It acts as both a safe offline learning sandbox and a real-world repository analyzer. 

Built with a cyberpunk-inspired dynamic TUI (Terminal User Interface), KGiit seamlessly blends high-performance backend logic with an incredible user experience.

- **Door 1: Analyze (`kgiit analyze`)**: Connect directly to live GitHub repositories to pull, analyze, and diagnose real-world issues.
- **Door 2: Learn (`kgiit learn`)**: Step into a 100% offline, safe sandbox to practice Git commands without fear of breaking production.

## 🧠 Machine Learning Engine

KGiit is not just a standard CLI; it is powered by **custom-trained Machine Learning models**. 
- **Typo Correction & Command Classification**: If a student mistypes a Git command in the sandbox, KGiit's ML engine kicks in, predicting what they meant to type and providing intelligent, context-aware hints.
- **Issue Triage**: The analyzer uses NLP to categorize and prioritize GitHub issues automatically.

---

## 🛠️ Quickstart Guide

### Installation
Ensure you have Python 3.10+ installed.

```bash
git clone https://github.com/ShauryaVaid/kgiit.git
cd kgiit
pip install -e .
```

### Usage
Start the interactive, full-screen cyberpunk menu simply by typing:

```bash
kgiit
```

From here, you can select:
1. **Analyze Mode**: Requires internet and an optional `GITHUB_TOKEN`.
2. **Learn Mode**: Fully offline. Launch the GUI or terminal practice environment.
3. **Demo Mode**: Watch an automated hands-free walkthrough.

To exit the application, simply type `/bye` or `q`.

---

## 📁 Project Structure

```text
KGiit/
├── kgiit/                  # Core Python Package
│   ├── cli.py              # Main Application Entrypoint & Cyberpunk UI
│   ├── analyze/            # Real-world GitHub Triage Engine
│   ├── learn/              # Offline Git Sandbox & Server
│   └── skills/             # Agentic ML Skills & Instructions
├── gui/                    # Electron-based Visual Interface
│   ├── main.js             # Electron Application Bootstrapper
│   └── styles.css          # Core Styling & Theme tokens
├── tests/                  # Pytest Validation Suite (90+ Passing Tests)
├── ARCHITECTURE.md         # Deep-dive into internal logic
├── CONTRIBUTING.md         # How to contribute to KGiit
└── setup.py                # Package installation definitions
```

---

## 📚 Documentation

Dive deeper into how KGiit works and how you can get involved:

- [**Architecture Guide**](ARCHITECTURE.md): Learn about the system design, ML integration, and how the CLI talks to the Electron GUI.
- [**Contributing Guidelines**](CONTRIBUTING.md): Want to add a feature? Read this first to set up your dev environment and run the test suite.

---

<div align="center">
  <b>Authored by Shaurya Vaid</b> <br/>
  <i>Empowering students to master Git.</i>
</div>
