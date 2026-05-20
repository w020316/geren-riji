@echo off
chcp 65001 >nul
echo ========================================
echo   心语日记 - 多智能体AI日记助手
echo ========================================
echo.

set PYTHON=D:\dev-tools\Python312\python.exe

echo [1/2] 检查环境...
%PYTHON% -c "import openai, chromadb, sentence_transformers, fastapi" 2>nul
if errorlevel 1 (
    echo 依赖缺失，正在安装...
    %PYTHON% -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
)

echo [2/2] 启动服务...
echo 请在浏览器中访问: http://localhost:8000
echo.
%PYTHON% main.py

pause
