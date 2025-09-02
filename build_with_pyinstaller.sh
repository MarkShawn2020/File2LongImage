#!/bin/bash

# File2LongImage PyInstaller 构建脚本
# 使用 PyInstaller 替代 py2app，解决库依赖问题

set -e  # 遇到错误立即退出

echo "==========================================="
echo "File2LongImage PyInstaller 构建器"
echo "==========================================="

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}✗ Python 3 未安装${NC}"
    echo "请访问 https://www.python.org/downloads/ 安装 Python"
    exit 1
fi
echo -e "${GREEN}✓ Python 已安装${NC}"

# 清理旧文件
echo ""
echo "清理旧的构建文件..."
rm -rf build dist *.spec
rm -rf File2LongImage_PyInstaller.app

# 创建 spec 文件
echo ""
echo "创建 PyInstaller 配置..."
cat > File2LongImage.spec << 'EOF'
# -*- mode: python ; coding: utf-8 -*-

import os
import sys
from pathlib import Path

# 获取项目根目录
project_root = Path(os.getcwd())

a = Analysis(
    ['mac_app_parallel.py'],
    pathex=[str(project_root)],
    binaries=[],
    datas=[
        ('config.py', '.'),
        ('error_logger.py', '.'),
        ('assets', 'assets'),
        ('output', 'output'),
        ('logs', 'logs'),
        ('.intermediate', '.intermediate'),
    ],
    hiddenimports=[
        'PIL',
        'PIL.Image',
        'PIL.ImageDraw',
        'PIL.ImageFont',
        'pdf2image',
        'psutil',
        'psutil._psutil_osx',
        'psutil._psutil_posix',
        'tkinter',
        'tkinter.ttk',
        'tkinter.messagebox',
        'tkinter.filedialog',
        'concurrent.futures',
        'dataclasses',
        'enum',
        'uuid',
        'queue',
        'threading',
        'subprocess',
        'hashlib',
        'pathlib',
        'time',
        'webbrowser',
        'traceback',
        'json',
        'platform',
        'shutil',
        'tempfile',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'numpy',
        'scipy',
        'pandas',
        'pytest',
        'IPython',
        'jupyter',
        'notebook',
        'setuptools',
        'pip',
        'wheel',
    ],
    noarchive=False,
    optimize=1,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='File2LongImage',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,  # 不显示控制台窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='File2LongImage',
)

app = BUNDLE(
    coll,
    name='File2LongImage.app',
    icon='assets/icon.icns' if os.path.exists('assets/icon.icns') else None,
    bundle_identifier='com.file2longimage.parallel',
    version='2.0.0',
    info_plist={
        'CFBundleName': 'File2LongImage',
        'CFBundleDisplayName': 'File2LongImage - 并行版',
        'CFBundleVersion': '2.0.0',
        'CFBundleShortVersionString': '2.0.0',
        'NSHighResolutionCapable': True,
        'LSMinimumSystemVersion': '10.14.0',
        'NSRequiresAquaSystemAppearance': False,
        'NSHumanReadableCopyright': '© 2024 File2LongImage',
        'NSAppleEventsUsageDescription': 'File2LongImage needs to control other applications.',
        'NSDesktopFolderUsageDescription': 'File2LongImage needs access to save files.',
        'NSDocumentsFolderUsageDescription': 'File2LongImage needs access to documents.',
        'NSDownloadsFolderUsageDescription': 'File2LongImage needs access to downloads.',
    },
)
EOF

# 确保必要的目录存在
mkdir -p output logs .intermediate assets

# 如果没有图标，创建一个占位符
if [ ! -f "assets/icon.icns" ]; then
    echo "创建默认图标..."
    touch assets/icon.icns
fi

# 运行 PyInstaller
echo ""
echo "开始构建应用..."
echo -e "${YELLOW}这可能需要几分钟...${NC}"

if pyinstaller File2LongImage.spec --clean --noconfirm; then
    echo -e "${GREEN}✓ 构建成功！${NC}"
    
    # 复制到根目录并重命名
    if [ -d "dist/File2LongImage.app" ]; then
        rm -rf File2LongImage_PyInstaller.app
        cp -r dist/File2LongImage.app File2LongImage_PyInstaller.app
        
        echo ""
        echo "==========================================="
        echo -e "${GREEN}✅ 应用构建完成！${NC}"
        echo "==========================================="
        echo ""
        echo "应用位置: File2LongImage_PyInstaller.app"
        echo ""
        echo "运行方式："
        echo "  1. 双击 File2LongImage_PyInstaller.app"
        echo "  2. 命令行: open File2LongImage_PyInstaller.app"
        echo ""
        echo "如果首次运行遇到安全警告："
        echo "  系统设置 → 安全性与隐私 → 仍要打开"
        echo ""
    else
        echo -e "${RED}✗ 构建产物未找到${NC}"
        exit 1
    fi
else
    echo -e "${RED}✗ 构建失败${NC}"
    echo ""
    echo "调试建议："
    echo "1. 检查错误信息"
    echo "2. 确保所有依赖已安装: pip install -r requirements.txt"
    echo "3. 尝试使用虚拟环境重新构建"
    exit 1
fi