# Contributing to JARVIS AI

Thanks for your interest in contributing! This project is maintained by
**ZAID BILAL** and welcomes pull requests.

## Getting started

1. Fork the repo and clone your fork.
2. Create a virtual environment and install dependencies:
   ```bash
   python -m venv venv
   source venv/bin/activate  # or venv\Scripts\activate on Windows
   pip install -r requirements.txt
   ```
3. Run the test suite before making changes, to confirm your environment
   is set up correctly:
   ```bash
   pytest tests/ -v
   ```

## Adding a new voice command

Most new features are a two-step addition:

1. Implement the action in `assistant/commands.py` (or `automation.py`/
   `system.py` if it's low-level device control). Return a short,
   natural-language string describing what happened.
2. Add an `Intent(name, pattern, handler)` entry to
   `Brain._build_intents()` in `assistant/brain.py` that matches the
   phrasing you want to support and calls your new function.
3. Add a unit test in `tests/test_brain.py` exercising the new phrase.

## Code style

- Type hints on public functions.
- Docstrings explaining *why*, not just *what*, especially for anything
  with a graceful-degradation fallback.
- Optional/heavy dependencies (GUI, audio, automation libraries) must be
  imported in a `try/except` so the module still imports cleanly without
  them, matching the existing pattern in `automation.py`/`speech.py`/etc.
- Run `pytest tests/ -v` before opening a PR; add tests for new behavior.

## Reporting bugs

Please include your OS, Python version, and the relevant section of
`jarvis.log` when filing an issue.

## Code of conduct

Be respectful and constructive. This is a hobby/open-source project run
in maintainers' spare time.
