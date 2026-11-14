@echo off
rem Compila RevelaZunidores.addon64 (precisa do Visual Studio 2022 Build Tools com C++)
call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat" >nul || exit /b 1
cd /d "%~dp0"
if not exist build mkdir build
cl /nologo /std:c++17 /O2 /EHsc /MT /W3 /utf-8 /DUNICODE /D_UNICODE /DWIN32_LEAN_AND_MEAN /I sdk\include /I sdk\imgui RevelaZunidores.cpp /LD /Fobuild\ /Febuild\RevelaZunidores.dll /link /NOLOGO user32.lib kernel32.lib || exit /b 1
copy /y build\RevelaZunidores.dll RevelaZunidores.addon64 >nul
echo OK: RevelaZunidores.addon64
