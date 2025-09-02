# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

File2LongImage 是一个文件转换工具，将多种格式文档（PDF、Word、Excel、PPT等）转换为高质量长图。项目提供 Web 界面（Streamlit）和桌面版（Tkinter）两种实现。

## Core Architecture

### 主要组件

1. **main.py** - Streamlit Web 应用主程序
   - 处理文件上传和参数设置
   - 实现图像合并和文件转换核心逻辑
   - 包含缓存机制避免重复处理

2. **TKGUI.py** - Tkinter 桌面版程序
   - 独立的桌面应用实现
   - Windows 优化（使用 os.startfile）

3. **mac_app.py** / **mac_app_simple.py** - macOS 原生应用
   - 完整版支持拖放功能（需要 tkinterdnd2）
   - 简化版无需额外依赖
   - macOS 菜单栏集成和快捷键支持

4. **config.py** - 系统配置管理
   - 自动检测操作系统并配置路径
   - Poppler 和 LibreOffice 路径管理

### 转换流程

1. 非 PDF 文件先通过 LibreOffice 转换为 PDF
2. PDF 通过 pdf2image（使用 Poppler）转换为图片序列
3. 使用 Pillow 将多张图片合并为长图
4. 支持 JPG/PNG 输出，可调节 DPI 和质量

## System Dependencies

### macOS
- Poppler: `/opt/homebrew/bin` (Apple Silicon) 或 `/usr/local/bin` (Intel)
- LibreOffice: `/Applications/LibreOffice.app/Contents/MacOS/soffice`

### Windows
- Poppler: `./poppler/poppler-24.07.0/Library/bin`
- LibreOffice: `./libreoffice/App/libreoffice/program/soffice.exe`

## Common Commands

```bash
# 运行 Web 应用
streamlit run main.py
# 或
python run_app.py

# 运行桌面版
python TKGUI.py

# 运行 macOS 原生应用（开发版）
python mac_app.py          # 完整版（支持拖放）
python mac_app_simple.py   # 简化版（无需 tkinterdnd2）

# 构建 macOS 应用
chmod +x build_mac.sh
./build_mac.sh

# 手动打包 macOS 应用
python setup.py py2app

# 安装依赖
pip install -r requirements.txt
pip install -r requirements_gui.txt  # GUI 额外依赖

# macOS 安装系统依赖
brew install poppler
brew install --cask libreoffice
```

## Key Implementation Details

### 文件缓存机制
- 使用 MD5 哈希识别文件，避免重复处理
- 缓存键包含：文件哈希 + DPI + 格式 + 质量

### 图像处理限制
- PIL 最大像素限制设为 5亿像素，防止内存溢出
- JPG 保存失败时自动降级为 PNG

### 进度反馈
- Web 版使用 st.progress() 和 st.empty() 实时更新
- 桌面版使用 ttk.Progressbar 和 update_idletasks()

### 错误处理
- LibreOffice 未安装时提供详细安装指引
- JPEG 编码失败时自动尝试不同参数或切换格式

## Performance Optimization Solutions

`solutions/` 目录包含多个性能优化方案：
- **multi_level_preview.py** - 多级预览系统
- **virtual_scroll_viewer.py** - 虚拟滚动查看器
- **adaptive_quality_streaming.py** - 自适应质量流式加载
- **smart_preview_panel.py** - 智能预览面板
- **integrated_solution.py** - 集成解决方案

## File Structure Conventions

- 输出文件保存在 `output/` 目录
- 临时文件存储在 `.intermediate/` 目录
- 文件命名：`{原文件名}.{png|jpg}`

## Testing Approach

项目目前无自动化测试框架。测试时应：
1. 验证各种文档格式转换（PDF、Word、Excel、PPT）
2. 测试不同 DPI 设置（72-600）
3. 验证 JPG/PNG 输出格式切换
4. 检查大文件处理和内存管理