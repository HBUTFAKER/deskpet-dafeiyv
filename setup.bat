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
    echo [错误] 没找到 Python。请安装 WorkBuddy 或 Python 3.12+。
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

REM 3) 装依赖（默认源在本机代理下会卡住，走清华镜像）
echo 安装依赖 ...
python -m pip install --upgrade pip -q
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple --timeout 20 --retries 1
if errorlevel 1 (
    echo [错误] 依赖安装失败，检查网络后重试。
    pause
    exit /b 1
)

REM 4) 独立桌宠：dsh-pet standalone（不依赖已下线的 dsh web 宿主）
set "ND="
for /d %%d in ("%USERPROFILE%\.workbuddy\binaries\node\versions\*") do set "ND=%%d"
if defined ND (
    if not exist "%ND%\dsh-pet-standalone.cmd" (
        echo 安装独立桌宠 dsh-pet ...
        call "%ND%\npm.cmd" install -g dsh-pet@0.4.7 --registry=https://registry.npmmirror.com
    )
) else (
    echo [警告] 没找到 WorkBuddy 自带 Node，桌宠窗口需自行安装 dsh-pet。
)

REM 5) 语音识别模型（本地没有就从镜像直连拉，约 460MB）
if not exist "models\whisper-small\model.bin" (
    echo 下载 whisper-small ...
    if not exist "models\whisper-small" mkdir "models\whisper-small"
    for %%f in (config.json model.bin tokenizer.json vocabulary.txt) do (
        curl -sSL --max-time 600 -o "models\whisper-small\%%f" "https://hf-mirror.com/Systran/faster-whisper-small/resolve/main/%%f"
    )
) else (
    echo 语音识别模型已存在，跳过
)

REM 6) 桌面图标
echo 生成桌面快捷方式 ...
python _make_lnk.py

echo.
echo ============================================================
echo   安装完成
echo   · 双击桌面「蓝色大肥鱼」启动
echo   · 首次运行前把 config.local.json 的 api_key 填上自己的 DeepSeek Key
echo     （或设环境变量 DEEPSEEK_API_KEY）
echo   · 退出：运行 quit.py；切语言：说「说日语 / 说中文」
echo ============================================================
pause
