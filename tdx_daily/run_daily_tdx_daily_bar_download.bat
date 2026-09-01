@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
REM TDX_daily 目录内：官网日线下载 -> 解压 -> datatool -> 导入 raw_stocks_daily
cd /d "%~dp0"
if not defined PYTHON set PYTHON=python
set LOGDIR=%~dp0logs
if not exist "%LOGDIR%" mkdir "%LOGDIR%"
for /f %%i in ('C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe -NoProfile -Command "Get-Date -Format yyyyMMdd"') do set LOGDATE=%%i
set LOGFILE=%LOGDIR%\run_daily_tdx_daily_bar_%LOGDATE%.log
set PAUSE_AFTER=0

if /I "%~1"=="--pause" set PAUSE_AFTER=1
if /I "%~1"=="--no-pause" set PAUSE_AFTER=0

if "%~1"=="" (
    for /f %%p in ('powershell -NoProfile -Command "$me=Get-CimInstance Win32_Process -Filter ('ProcessId=' + $PID); $parent=Get-CimInstance Win32_Process -Filter ('ProcessId=' + $me.ParentProcessId); if($parent.Name -ieq 'cmd.exe'){ $pp=Get-CimInstance Win32_Process -Filter ('ProcessId=' + $parent.ParentProcessId); if($pp){$pp.Name}else{''} } else { $parent.Name }"') do set RUNNER=%%p
    if /I "!RUNNER!"=="explorer.exe" set PAUSE_AFTER=1
)

echo ========================================
echo TDX Daily Bar Download Task (TDX_daily)
echo ========================================
echo [1/3] Preparing runtime environment...
echo Log file: %LOGFILE%
echo.
echo [2/3] Running downloader ^(this may take a while^)...

powershell -NoProfile -ExecutionPolicy Bypass -Command "$OutputEncoding=[Console]::OutputEncoding=[System.Text.Encoding]::UTF8; Set-Location -LiteralPath '%CD%'; $log='%LOGFILE%'; $now=(Get-Date -Format 'yyyy-MM-dd HH:mm:ss'); $today=(Get-Date -Format 'yyyy-MM-dd'); $h='========================================'; Write-Host $h; Write-Host 'TDX Daily Bar Download Task'; Write-Host $h; Write-Host \"Start: $now  Target: $today\"; Add-Content -Path $log -Value \"`n$h`nTDX Daily Bar Download Task`n$h`nStart: $now Target: $today\" -Encoding UTF8; Write-Host '[Stage] Python task started...'; Add-Content -Path $log -Value '[Stage] Python task started...' -Encoding UTF8; $env:PYTHONIOENCODING='utf-8'; $py = if ($null -ne $env:PYTHON -and $env:PYTHON -ne '') { $env:PYTHON } else { 'python' }; $job = Join-Path (Get-Location) 'tdx_daily_bar_job.py'; & $py -u $job --trade-date $today --table-name tdx.daily_bar 2>&1 | ForEach-Object { Write-Host $_; Add-Content -Path $log -Value $_ -Encoding UTF8 }; $e=$LASTEXITCODE; Write-Host '[Stage] Python task finished.'; Add-Content -Path $log -Value '[Stage] Python task finished.' -Encoding UTF8; Write-Host ''; Write-Host \"End. Exit code: $e   Log: $log\"; Add-Content -Path $log -Value \"`nEnd. Exit code: $e\" -Encoding UTF8; exit $e"

set FINAL_EXIT=!ERRORLEVEL!
echo.
echo [3/3] Finished. Exit code: !FINAL_EXIT!
echo Log file: %LOGFILE%

if "!PAUSE_AFTER!"=="1" (
    echo.
    echo Press any key to close...
    pause >nul
)

endlocal
exit /b !FINAL_EXIT!
