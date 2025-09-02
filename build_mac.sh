#!/bin/bash

# File2LongImage macOS App 构建脚本
# 自动化打包流程，处理依赖和签名

set -e  # 遇到错误立即退出

echo "========================================="
echo "File2LongImage macOS App Builder"
echo "========================================="

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查运行环境
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo -e "${RED}错误: 此脚本仅支持 macOS${NC}"
    exit 1
fi

# 检查 Python 版本
PYTHON_VERSION=$(python3 --version 2>&1 | grep -oE '[0-9]+\.[0-9]+')
REQUIRED_VERSION="3.8"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    echo -e "${RED}错误: 需要 Python $REQUIRED_VERSION 或更高版本${NC}"
    echo "当前版本: $PYTHON_VERSION"
    exit 1
fi

echo -e "${GREEN}✓ Python 版本检查通过${NC}"

# 检查和安装依赖
echo ""
echo "检查系统依赖..."

# 检查 Homebrew
if ! command -v brew &> /dev/null; then
    echo -e "${YELLOW}Homebrew 未安装，正在安装...${NC}"
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
fi

# 检查 Poppler
if ! command -v pdftoppm &> /dev/null; then
    echo -e "${YELLOW}安装 Poppler...${NC}"
    brew install poppler
else
    echo -e "${GREEN}✓ Poppler 已安装${NC}"
fi

# 检查 LibreOffice（可选）
if [ ! -d "/Applications/LibreOffice.app" ]; then
    echo -e "${YELLOW}提示: LibreOffice 未安装${NC}"
    echo "如需支持 Word/Excel/PPT 转换，请运行:"
    echo "  brew install --cask libreoffice"
else
    echo -e "${GREEN}✓ LibreOffice 已安装${NC}"
fi

# 创建虚拟环境
echo ""
echo "设置 Python 环境..."

if [ ! -d "venv" ]; then
    echo "创建虚拟环境..."
    python3 -m venv venv
fi

# 激活虚拟环境
source venv/bin/activate

# 升级 pip
pip install --upgrade pip

# 安装 Python 依赖
echo "安装 Python 依赖..."
pip install -r requirements.txt
pip install py2app
pip install tkinterdnd2

# 创建应用图标（如果不存在）
if [ ! -f "assets/icon.icns" ]; then
    echo ""
    echo "创建应用图标..."
    
    # 创建临时 PNG（如果不存在）
    if [ ! -f "assets/icon.png" ]; then
        # 使用 Python 创建一个默认图标
        python3 << EOF
from PIL import Image, ImageDraw, ImageFont
import os

os.makedirs('assets', exist_ok=True)

# 创建图标
img = Image.new('RGBA', (512, 512), (255, 255, 255, 0))
draw = ImageDraw.Draw(img)

# 背景
draw.rounded_rectangle([20, 20, 492, 492], radius=60, fill=(52, 120, 246))

# 文字
try:
    font = ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc', 200)
except:
    font = ImageFont.load_default()

text = "F2L"
bbox = draw.textbbox((0, 0), text, font=font)
text_width = bbox[2] - bbox[0]
text_height = bbox[3] - bbox[1]
x = (512 - text_width) // 2
y = (512 - text_height) // 2 - 20

draw.text((x, y), text, fill='white', font=font)

# 保存
img.save('assets/icon.png')
print("默认图标已创建")
EOF
    fi
    
    # 转换 PNG 到 ICNS
    if [ -f "assets/icon.png" ]; then
        # 创建 iconset
        mkdir -p assets/icon.iconset
        
        # 生成不同尺寸
        sips -z 16 16     assets/icon.png --out assets/icon.iconset/icon_16x16.png
        sips -z 32 32     assets/icon.png --out assets/icon.iconset/icon_16x16@2x.png
        sips -z 32 32     assets/icon.png --out assets/icon.iconset/icon_32x32.png
        sips -z 64 64     assets/icon.png --out assets/icon.iconset/icon_32x32@2x.png
        sips -z 128 128   assets/icon.png --out assets/icon.iconset/icon_128x128.png
        sips -z 256 256   assets/icon.png --out assets/icon.iconset/icon_128x128@2x.png
        sips -z 256 256   assets/icon.png --out assets/icon.iconset/icon_256x256.png
        sips -z 512 512   assets/icon.png --out assets/icon.iconset/icon_256x256@2x.png
        sips -z 512 512   assets/icon.png --out assets/icon.iconset/icon_512x512.png
        sips -z 1024 1024 assets/icon.png --out assets/icon.iconset/icon_512x512@2x.png
        
        # 生成 icns
        iconutil -c icns assets/icon.iconset -o assets/icon.icns
        
        # 清理
        rm -rf assets/icon.iconset
        
        echo -e "${GREEN}✓ 应用图标已创建${NC}"
    fi
fi

# 清理旧的构建
echo ""
echo "清理旧的构建文件..."
rm -rf build dist

# 构建应用
echo ""
echo "开始构建应用..."
python setup.py py2app

# 检查构建结果
if [ -d "dist/File2LongImage.app" ]; then
    echo -e "${GREEN}✓ 应用构建成功！${NC}"
    
    # 复制 Poppler 二进制文件到应用包
    echo ""
    echo "嵌入 Poppler 二进制文件..."
    
    APP_RESOURCES="dist/File2LongImage.app/Contents/Resources"
    mkdir -p "$APP_RESOURCES/poppler"
    
    # 复制必要的 Poppler 工具
    for tool in pdftoppm pdfinfo pdftocairo pdftotext; do
        if [ -f "/opt/homebrew/bin/$tool" ]; then
            cp "/opt/homebrew/bin/$tool" "$APP_RESOURCES/poppler/"
            echo "  复制 $tool"
        elif [ -f "/usr/local/bin/$tool" ]; then
            cp "/usr/local/bin/$tool" "$APP_RESOURCES/poppler/"
            echo "  复制 $tool"
        fi
    done
    
    # 复制 Poppler 依赖库
    echo "处理依赖库..."
    
    # 创建修复脚本
    cat > fix_libs.py << 'EOF'
import os
import subprocess
import shutil

app_path = "dist/File2LongImage.app"
poppler_dir = f"{app_path}/Contents/Resources/poppler"
frameworks_dir = f"{app_path}/Contents/Frameworks"

os.makedirs(frameworks_dir, exist_ok=True)

# 获取并复制依赖库
for tool in os.listdir(poppler_dir):
    tool_path = os.path.join(poppler_dir, tool)
    if os.path.isfile(tool_path):
        # 获取依赖
        result = subprocess.run(['otool', '-L', tool_path], capture_output=True, text=True)
        for line in result.stdout.split('\n'):
            if '/opt/homebrew' in line or '/usr/local' in line:
                lib_path = line.strip().split()[0]
                if os.path.exists(lib_path):
                    lib_name = os.path.basename(lib_path)
                    dest_path = os.path.join(frameworks_dir, lib_name)
                    if not os.path.exists(dest_path):
                        shutil.copy2(lib_path, dest_path)
                        print(f"  复制库: {lib_name}")

print("依赖库处理完成")
EOF
    
    python fix_libs.py
    rm fix_libs.py
    
    # 代码签名（如果有开发者证书）
    echo ""
    echo "尝试代码签名..."
    
    # 检查是否有有效的开发者证书
    if security find-identity -v -p codesigning | grep -q "Developer ID Application"; then
        IDENTITY=$(security find-identity -v -p codesigning | grep "Developer ID Application" | head -1 | awk '{print $2}')
        echo "使用证书: $IDENTITY"
        
        # 签名应用
        codesign --deep --force --verify --verbose --sign "$IDENTITY" \
                 --options runtime \
                 --entitlements - \
                 "dist/File2LongImage.app" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>com.apple.security.cs.allow-unsigned-executable-memory</key>
    <true/>
    <key>com.apple.security.cs.disable-library-validation</key>
    <true/>
    <key>com.apple.security.automation.apple-events</key>
    <true/>
</dict>
</plist>
EOF
        
        echo -e "${GREEN}✓ 代码签名完成${NC}"
    else
        echo -e "${YELLOW}跳过代码签名（未找到开发者证书）${NC}"
    fi
    
    # 创建 DMG 安装包
    echo ""
    echo "创建 DMG 安装包..."
    
    # 创建临时目录
    mkdir -p dist/dmg
    cp -r "dist/File2LongImage.app" dist/dmg/
    
    # 创建应用程序文件夹的符号链接
    ln -s /Applications dist/dmg/Applications
    
    # 创建 DMG
    hdiutil create -volname "File2LongImage" \
                   -srcfolder dist/dmg \
                   -ov -format UDZO \
                   "dist/File2LongImage.dmg"
    
    # 清理临时文件
    rm -rf dist/dmg
    
    echo -e "${GREEN}✓ DMG 安装包创建成功${NC}"
    
    # 输出结果
    echo ""
    echo "========================================="
    echo -e "${GREEN}构建完成！${NC}"
    echo "========================================="
    echo ""
    echo "应用位置: dist/File2LongImage.app"
    echo "安装包: dist/File2LongImage.dmg"
    echo ""
    echo "测试运行:"
    echo "  open dist/File2LongImage.app"
    echo ""
    echo "安装到应用程序:"
    echo "  cp -r dist/File2LongImage.app /Applications/"
    echo ""
    
    # 计算文件大小
    APP_SIZE=$(du -sh dist/File2LongImage.app | cut -f1)
    DMG_SIZE=$(du -sh dist/File2LongImage.dmg | cut -f1)
    echo "应用大小: $APP_SIZE"
    echo "DMG 大小: $DMG_SIZE"
    
else
    echo -e "${RED}构建失败！${NC}"
    echo "请检查错误信息并重试"
    exit 1
fi

# 退出虚拟环境
deactivate