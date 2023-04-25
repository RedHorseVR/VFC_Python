prompt :
echo off

cd

copy %1 %1_

SET mypath=%~dp0PythonParser.pl
echo %mypath%

perl %mypath%  %1

pause