@echo off
title ͨ�ýű�����
call activate py312
cd ...
cls
pyinstaller --onefile --hidden-import=pynput.keyboard --add-data "favicon.ico;favicon.ico" --icon=favicon.ico --noconsole main.py

xcopy /Y dist\*.exe .
echo ������ɣ���������˳�. . .
pause>nulq