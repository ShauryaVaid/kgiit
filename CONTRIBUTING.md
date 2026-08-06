# Contributing to KGiit

Welcome to **KGiit**! We're thrilled that you'd like to contribute. Whether it's fixing bugs, improving the ML models, or adding new terminal interfaces, your help is appreciated.

## Getting Started

### Prerequisites
- Python 3.10+
- Git
- Node.js & npm (for Electron GUI development)

### Local Setup
1. Fork the repository on GitHub.
2. Clone your fork locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/kgiit.git
   cd kgiit
   ```
3. Create a virtual environment and install dependencies:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows use: .venv\Scripts\activate
   pip install -e ".[dev]"
   ```
4. Install GUI dependencies (optional, only if editing Electron UI):
   ```bash
   cd gui
   npm install
   cd ..
   ```

## Running Tests
Before submitting any pull request, please ensure all tests pass. We enforce strict test coverage.

```bash
pytest
```

## Pull Request Process
1. Create a new branch from `main` (`git checkout -b feature/amazing-feature`).
2. Make your changes and write tests if applicable.
3. Ensure the test suite passes locally.
4. Commit your changes logically with descriptive commit messages.
5. Push to your fork and submit a Pull Request to the `main` branch of `ShauryaVaid/kgiit`.

Thank you for helping empower students to master Git!
