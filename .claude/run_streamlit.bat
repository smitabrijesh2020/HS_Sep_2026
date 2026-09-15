@echo off
cd /d "%~dp0.."
python -m streamlit run app/main.py --server.headless true --server.port 8501
