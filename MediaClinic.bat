@echo off
:: Starts MediaClinic from this folder without a console window (needs Python 3.10+)
cd /d "%~dp0"
start "" pythonw mediaclinic.py
