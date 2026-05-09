@echo off
cd /d "C:\Users\BIT\Desktop\Youtube-Agent"
:loop
"C:\Users\BIT\AppData\Local\Programs\Python\Python311\python.exe" scheduler.py >> logs\scheduler_boot.log 2>&1
echo Restarting in 60 seconds... >> logs\scheduler_boot.log
timeout /t 60 /nobreak
goto loop
