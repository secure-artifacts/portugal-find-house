@echo off
chcp 65001 >nul
cd /d "%~dp0"

set CHROME=
if exist "C:\Program Files\Google\Chrome\Application\chrome.exe" set CHROME=C:\Program Files\Google\Chrome\Application\chrome.exe
if exist "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" set CHROME=C:\Program Files (x86)\Google\Chrome\Application\chrome.exe
if exist "C:\Program Files\Microsoft\Edge\Application\msedge.exe" if "%CHROME%"=="" set CHROME=C:\Program Files\Microsoft\Edge\Application\msedge.exe

if "%CHROME%"=="" (
    echo 找不到 Chrome 或 Edge。
    pause
    exit /b 1
)

set PROFILE=%~dp0browser_profile
echo.
echo 将用独立资料目录打开真实 Chrome，方便你先登录 Idealista / Google / Imovirtual。
echo 资料目录：%PROFILE%
echo 调试地址：http://127.0.0.1:9222
echo.
echo 请先关闭占用这个资料目录的旧 Chrome 窗口。
echo 打开后请手动登录账号，并完成验证码。然后回到采集界面：
echo   1. 勾选“使用真实 Chrome”
echo   2. CDP 填 http://127.0.0.1:9222
echo   3. 再点“开始自动采集”
echo.
start "" "%CHROME%" --remote-debugging-port=9222 --user-data-dir="%PROFILE%" --no-first-run --no-default-browser-check --lang=pt-PT
echo Chrome 已启动。
pause
