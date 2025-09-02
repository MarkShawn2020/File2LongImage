#!/bin/bash

# File2LongImage 仓库清理脚本
# 清理所有应该被忽略的文件和目录

echo "========================================="
echo "File2LongImage 仓库清理工具"
echo "========================================="

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 确认操作
echo -e "${YELLOW}警告：此操作将删除所有构建产物和临时文件！${NC}"
echo "将要删除："
echo "  - 所有 .app 文件"
echo "  - build/ 和 dist/ 目录"
echo "  - venv/ 虚拟环境"
echo "  - __pycache__ 目录"
echo "  - .spec 文件"
echo "  - .eggs 目录"
echo ""
read -p "确定要继续吗？(y/N) " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "操作已取消"
    exit 0
fi

echo ""
echo "开始清理..."

# 删除构建产物
echo -n "清理构建目录... "
rm -rf build/ dist/ .eggs/
echo -e "${GREEN}✓${NC}"

# 删除应用包
echo -n "清理应用包... "
rm -rf *.app
echo -e "${GREEN}✓${NC}"

# 删除 spec 文件
echo -n "清理 spec 文件... "
rm -f *.spec
echo -e "${GREEN}✓${NC}"

# 删除 Python 缓存
echo -n "清理 Python 缓存... "
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find . -type f -name "*.pyc" -delete 2>/dev/null
find . -type f -name "*.pyo" -delete 2>/dev/null
find . -type f -name "*.pyd" -delete 2>/dev/null
echo -e "${GREEN}✓${NC}"

# 删除虚拟环境（可选）
if [ -d "venv" ]; then
    echo -e "${YELLOW}发现虚拟环境 venv/${NC}"
    read -p "是否删除虚拟环境？(y/N) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo -n "删除虚拟环境... "
        rm -rf venv/ venv_*/
        echo -e "${GREEN}✓${NC}"
    fi
fi

# 清理输出目录（保留目录结构）
if [ -d "output" ]; then
    echo -n "清理输出目录... "
    rm -rf output/*
    echo -e "${GREEN}✓${NC}"
fi

# 清理日志目录（保留目录结构）
if [ -d "logs" ]; then
    echo -n "清理日志目录... "
    rm -rf logs/*
    echo -e "${GREEN}✓${NC}"
fi

# 清理中间文件目录
if [ -d ".intermediate" ]; then
    echo -n "清理中间文件... "
    rm -rf .intermediate/*
    echo -e "${GREEN}✓${NC}"
fi

# 删除 macOS 系统文件
echo -n "清理系统文件... "
find . -name ".DS_Store" -delete 2>/dev/null
find . -name "._*" -delete 2>/dev/null
echo -e "${GREEN}✓${NC}"

# 删除备份文件
echo -n "清理备份文件... "
find . -name "*.bak" -delete 2>/dev/null
find . -name "*.backup" -delete 2>/dev/null
find . -name "*.old" -delete 2>/dev/null
find . -name "*.orig" -delete 2>/dev/null
find . -name "*~" -delete 2>/dev/null
echo -e "${GREEN}✓${NC}"

# Git 相关操作
echo ""
echo "Git 操作："
echo "-----------"

# 更新 .gitignore
if [ -f ".gitignore" ]; then
    echo -e "${GREEN}✓${NC} .gitignore 已更新"
fi

# 从 Git 缓存中移除已忽略的文件
echo -n "更新 Git 索引... "
git rm -r --cached . >/dev/null 2>&1
git add . >/dev/null 2>&1
echo -e "${GREEN}✓${NC}"

# 显示清理结果
echo ""
echo "========================================="
echo -e "${GREEN}清理完成！${NC}"
echo "========================================="
echo ""
echo "Git 状态："
git status --short

echo ""
echo "建议后续操作："
echo "1. 检查 git status 确认更改"
echo "2. 提交更改: git commit -m \"chore: 更新 .gitignore 并清理仓库\""
echo "3. 如需重新安装依赖: pip install -r requirements.txt"