#!/bin/bash
# File2LongImage 并行版启动器

# 获取脚本所在目录
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo "错误: 未找到 Python3"
    echo "请安装 Python3: https://www.python.org/downloads/"
    read -p "按回车键退出..."
    exit 1
fi

# 检查依赖
echo "检查依赖..."
python3 -c "import PIL" 2>/dev/null || {
    echo "安装 Pillow..."
    pip3 install Pillow
}

python3 -c "import pdf2image" 2>/dev/null || {
    echo "安装 pdf2image..."
    pip3 install pdf2image
}

python3 -c "import psutil" 2>/dev/null || {
    echo "安装 psutil..."
    pip3 install psutil
}

# 启动应用
echo "启动 File2LongImage 并行版..."
python3 mac_app_parallel.py

# 如果应用崩溃，保持窗口打开
if [ $? -ne 0 ]; then
    echo ""
    echo "应用遇到错误。按回车键退出..."
    read
fi