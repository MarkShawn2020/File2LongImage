#!/bin/bash
# 快速测试所有构建的应用

echo "========================================="
echo "File2LongImage 应用测试"
echo "========================================="

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo ""
echo "可用的应用版本："
echo "-----------------------------------------"

# 测试 PyInstaller 版本
if [ -d "File2LongImage_PyInstaller.app" ]; then
    echo -e "${GREEN}✓${NC} File2LongImage_PyInstaller.app (PyInstaller构建)"
    echo "  位置: ./File2LongImage_PyInstaller.app"
    echo "  大小: $(du -sh File2LongImage_PyInstaller.app | cut -f1)"
else
    echo -e "${RED}✗${NC} File2LongImage_PyInstaller.app 未找到"
fi

# 测试轻量级版本
if [ -d "File2LongImage.app" ]; then
    echo -e "${GREEN}✓${NC} File2LongImage.app (轻量级包装)"
    echo "  位置: ./File2LongImage.app"
    echo "  大小: $(du -sh File2LongImage.app | cut -f1)"
else
    echo -e "${RED}✗${NC} File2LongImage.app 未找到"
fi

# 测试命令行脚本
if [ -f "run_parallel_app.command" ]; then
    echo -e "${GREEN}✓${NC} run_parallel_app.command (命令行脚本)"
    echo "  位置: ./run_parallel_app.command"
else
    echo -e "${RED}✗${NC} run_parallel_app.command 未找到"
fi

# 测试 Python 脚本
if [ -f "mac_app_parallel.py" ]; then
    echo -e "${GREEN}✓${NC} mac_app_parallel.py (源代码)"
    echo "  位置: ./mac_app_parallel.py"
else
    echo -e "${RED}✗${NC} mac_app_parallel.py 未找到"
fi

echo ""
echo "========================================="
echo "依赖检查"
echo "========================================="

# Python
if command -v python3 &> /dev/null; then
    echo -e "${GREEN}✓${NC} Python: $(python3 --version 2>&1)"
else
    echo -e "${RED}✗${NC} Python 未安装"
fi

# Poppler
if command -v pdftoppm &> /dev/null; then
    echo -e "${GREEN}✓${NC} Poppler: $(pdftoppm -v 2>&1 | head -1)"
elif [ -f "/opt/homebrew/bin/pdftoppm" ]; then
    echo -e "${GREEN}✓${NC} Poppler: 已安装 (Homebrew)"
else
    echo -e "${YELLOW}⚠${NC} Poppler: 未找到 (PDF转换可能失败)"
fi

# LibreOffice
if [ -d "/Applications/LibreOffice.app" ]; then
    echo -e "${GREEN}✓${NC} LibreOffice: 已安装"
else
    echo -e "${YELLOW}⚠${NC} LibreOffice: 未安装 (Office文件转换将失败)"
fi

# Python 包
echo ""
echo "Python 包："
for pkg in PIL pdf2image psutil; do
    if python3 -c "import $pkg" 2>/dev/null; then
        echo -e "  ${GREEN}✓${NC} $pkg"
    else
        echo -e "  ${RED}✗${NC} $pkg"
    fi
done

echo ""
echo "========================================="
echo "推荐运行方式"
echo "========================================="
echo ""
echo "1. 最稳定（PyInstaller）："
echo "   ${GREEN}open File2LongImage_PyInstaller.app${NC}"
echo ""
echo "2. 最轻量（需要Python）："
echo "   ${GREEN}open File2LongImage.app${NC}"
echo ""
echo "3. 开发调试："
echo "   ${GREEN}python3 mac_app_parallel.py${NC}"
echo ""
echo "========================================="