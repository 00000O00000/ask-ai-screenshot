@echo off
title 通用脚本编译
call activate py312
cd ...
cls
pyinstaller --onefile --hidden-import=pynput.keyboard --add-data "favicon.ico;favicon.ico" --icon=favicon.ico --noconsole main.py

xcopy /Y dist\*.exe .
echo 编译完成，按任意键退出. . .
pause>nulq