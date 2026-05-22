@echo off
rem Change directory to the script location
cd /d "%~dp0"

rem Activate virtual environment if it exists
if exist .venv\Scripts\activate.bat (
    call .venv\Scripts\activate.bat
)

rem Ensure required packages are installed (optional)
rem pip install -r requirements.txt

rem Run the Streamlit application
streamlit run streamlit_app.py
