@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

echo ============================================================
echo   大肥鱼桌宠 · 一键安装
echo ============================================================
echo.

REM 1) 找 Python：优先 WorkBuddy 自带的，其次系统 PATH 里的
set "PW="
for /d %%d in ("%USERPROFILE%\.workbuddy\binaries\python\versions\*") do set "PW=%%d\python.exe"
if not defined PW (
    where python >nul 2>nul && set "PW=python.exe"
)
if not defined PW (
    echo [错误] 没找到 Python。请先安装 WorkBuddy（会自带 Python），或自行安装 Python 3.11+。
    pause
    exit /b 1
)
echo 使用 Python：%PW%

REM 2) 建虚拟环境（已有则跳过）
if not exist ".venv\Scripts\python.exe" (
    echo 创建虚拟环境 .venv ...
    "%PW%" -m venv .venv
) else (
    echo 虚拟环境已存在，跳过
)
call .venv\Scripts\activate.bat

REM 3) 装依赖
echo 安装依赖（可能要一两分钟）...
python -m pip install --upgrade pip >nul
pip install -r requirements.txt
if errorlevel 1 (
    echo [错误] 依赖安装失败，检查网络后重试。
    pause
    exit /b 1
)

REM 4) 生成桌面图标
echo 生成桌面快捷方式「蓝色大肥鱼」...
python _make_lnk.py

REM 5) 给 dsh-pet 打补丁（右键退出 / 语言切换 / 聊天框语言跟随）
echo.
echo 正在给 dsh-pet 打补丁（若还没装 dsh-pet 会失败，可稍后手动跑 patch_all.py）...
python patch_all.py || echo [提示] 补丁未应用，确认已安装 dsh-pet 插件后重新运行 patch_all.py 即可。

echo.
echo ============================================================
echo   安装完成！
echo   · 双击桌面「蓝色大肥鱼」启动
echo   · 右键屏幕上的鱼本体 -> 退出大肥鱼
echo   · 右键鱼本体 -> 切换语言（中 / 日）
echo   · 首次运行请把 config.example.json 复制为 config.local.json
echo     填上你自己的 DeepSeek API Key（或设置环境变量 DEEPSEEK_API_KEY）
echo ============================================================
pause
