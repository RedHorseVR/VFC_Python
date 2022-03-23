prompt :
echo off

cd

SET mypath=%~dp0PythonParser.pl
echo %mypath%

perl %mypath%  %1

pause