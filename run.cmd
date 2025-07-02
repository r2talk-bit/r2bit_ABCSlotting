@echo off
echo Starting ABC Slotting Analysis App...

:: Check if virtual environment exists, if not create it
if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
    call venv\Scripts\activate.bat
    echo Installing dependencies...
    pip install -r requirements.txt
) else (
    call venv\Scripts\activate.bat
)

:: Run the Streamlit app
echo Launching Streamlit app...
streamlit run streamlit_app.py

:: Keep the window open if there's an error
if %ERRORLEVEL% NEQ 0 (
    echo An error occurred while running the app.
    pause
)
