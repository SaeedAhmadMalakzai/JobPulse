@echo off
REM Build JobPulse for Windows. Run from project root with venv active.
REM Output: dist\JobPulse\ folder and JobPulse-win64.zip

echo Building JobPulse for Windows...
pip install pyinstaller -q
pyinstaller --noconfirm jobpulse.spec
if errorlevel 1 exit /b 1

echo Creating JobPulse-win64.zip...
cd dist
powershell -Command "Compress-Archive -Path JobPulse -DestinationPath JobPulse-win64.zip -Force"
cd ..
echo Done. Run: dist\JobPulse\JobPulse.exe
echo Zip: dist\JobPulse-win64.zip
