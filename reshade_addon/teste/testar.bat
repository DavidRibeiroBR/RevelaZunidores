@echo off
call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat" >nul 2>nul
cd /d "%~dp0"
cl /nologo /std:c++17 /EHsc /utf-8 /W3 /DUNICODE /D_UNICODE /DWIN32_LEAN_AND_MEAN /I ..\sdk\include /I ..\sdk\imgui teste.cpp /Fe:teste.exe /link user32.lib || exit /b 1
teste.exe
