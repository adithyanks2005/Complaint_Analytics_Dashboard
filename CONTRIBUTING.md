# Contributing Guide

Thank you for considering contributing to **Complaint Analytics Dashboard**! 🎉

## 🚀 Getting Started
1. **Fork** the repository and clone it locally.
   ```bash
   git clone https://github.com/your-username/Complaint_Analytics_Dashboard.git
   cd Complaint_Analytics_Dashboard
   ```
2. **Create a virtual environment** and install dependencies.
   ```bash
   python -m venv .venv
   # Windows
   .venv\\Scripts\\activate
   # macOS / Linux
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
3. **Run the app** to ensure everything works:
   ```bash
   streamlit run frontend/streamlit_app.py
   ```

## 🧪 Testing
- Run the test suite:
  ```bash
  pytest tests -q
  ```
- New tests should be placed under the `tests/` directory and follow the `test_*.py` naming convention.

## 🛠️ Code Style
- **Formatting**: The project uses `flake8` with the configuration in `setup.cfg`. Run:
  ```bash
  flake8 backend/ --max-line-length=120
  ```
- **Pre‑commit**: We recommend installing pre‑commit hooks:
  ```bash
  pip install pre-commit
  pre-commit install
  ```

## 📦 Docker
- Build the image locally:
  ```bash
  docker build -t complaint-dashboard .
  ```
- Run the container:
  ```bash
  docker run -d -p 8501:8501 complaint-dashboard
  ```

## 📚 Documentation
- Keep the `README.md` up‑to‑date with any new features.
- Add changelog entries under a `CHANGELOG.md` file for major releases.

## 🐞 Reporting Issues
- Open an issue with a clear description, steps to reproduce, and expected vs. actual behavior.
- Include screenshots or logs when helpful.

## 🎉 Pull Requests
- Ensure all checks (lint, tests, Docker build) pass.
- Provide a concise PR title and description.
- Reference related issues (e.g., `Closes #12`).

Happy coding! 🚀
