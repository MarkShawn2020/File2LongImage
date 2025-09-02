# File2LongImage - 文件转长图工具

一个强大的文件转换工具，可将 PDF、Word、Excel、PPT 等多种格式文件转换为高质量长图。

## 🎬 演示

<p align="center">
  <img src="assets/demo.png" alt="File2LongImage 演示" width="800"/>
</p>

## ✨ 功能特点

- 📄 **多格式支持**：PDF、Word、Excel、PPT、TXT、RTF 等
- 🖼️ **智能合并**：自动将多页文档合并为一张长图
- ⚡ **高性能**：支持批量处理和大文件转换
- 🎨 **质量可调**：自定义 DPI 设置，平衡质量与文件大小
- 🌐 **Web 界面**：基于 Streamlit 的现代化操作界面
- 🖥️ **桌面版本**：提供 Tkinter 版本，便于打包分发

## 🚀 快速开始

### 系统要求

- Python 3.8+
- macOS / Windows / Linux

### 安装步骤

#### 1. 克隆项目

```bash
git clone https://github.com/你的用户名/File2LongImage.git
cd File2LongImage
```

#### 2. 安装系统依赖

<details>
<summary><b>📱 macOS</b></summary>

```bash
# 安装 Homebrew（如未安装）
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 安装 Poppler（PDF 处理）
brew install poppler

# 安装 LibreOffice（可选，用于 Office 文件转换）
brew install --cask libreoffice
```

**注意**：
- Poppler 会自动安装到 `/opt/homebrew/bin`（Apple Silicon）或 `/usr/local/bin`（Intel）
- LibreOffice 会安装到 `/Applications/LibreOffice.app`
- 配置文件已自动适配 macOS 路径，无需手动修改

</details>

<details>
<summary><b>🪟 Windows</b></summary>

1. **安装 Poppler**
   - 下载 [Poppler for Windows](http://blog.alivate.com.au/poppler-windows/)
   - 解压到项目目录下的 `poppler` 文件夹
   - 或添加到系统环境变量 PATH

2. **安装 LibreOffice**（可选）
   - 下载 [LibreOffice](https://www.libreoffice.org/download/download/)
   - 安装到默认位置或自定义路径

</details>

<details>
<summary><b>🐧 Linux</b></summary>

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install poppler-utils
sudo apt-get install libreoffice  # 可选

# CentOS/RHEL/Fedora
sudo yum install poppler-utils
sudo yum install libreoffice  # 可选
```

</details>

#### 3. 安装 Python 依赖

```bash
pip install -r requirements.txt
```

## 📖 使用方法

### Web 界面版本

```bash
# 启动应用
streamlit run main.py

# 或使用便捷脚本
python run_app.py
```

浏览器将自动打开 `http://localhost:8501`

### 桌面界面版本

```bash
python TKGUI.py
```

### macOS 原生应用 🆕

```bash
# 一键构建 macOS 应用
chmod +x build_mac.sh
./build_mac.sh

# 或直接运行开发版
python mac_app.py
```

详见 [macOS 应用文档](README_MACOS_APP.md)

### 使用流程

1. 选择要转换的文件
2. 设置 DPI（默认 200，范围 72-600）
3. 选择输出格式（PNG/JPG）
4. 点击转换，等待处理完成
5. 在 `output` 文件夹查看结果

## ⚙️ 配置说明

配置文件 `config.py` 已针对不同系统自动适配：

- **macOS**：自动检测 Homebrew 安装路径
- **Windows**：支持本地 poppler 文件夹或环境变量
- **Linux**：使用系统标准路径

通常无需手动修改配置文件。

## 📁 项目结构

```
File2LongImage/
├── main.py           # Streamlit Web 应用主程序
├── TKGUI.py         # Tkinter 桌面版程序
├── config.py        # 自动适配的配置文件
├── run_app.py       # 快捷启动脚本
├── requirements.txt # Python 依赖列表
├── output/          # 转换结果输出目录
└── README.md        # 项目说明文档
```

## 🔧 故障排除

### macOS 常见问题

**Q: 提示找不到 Poppler**
```bash
# 验证安装
brew list poppler
# 重新安装
brew reinstall poppler
```

**Q: LibreOffice 无法转换文件**
```bash
# 检查是否已安装
ls /Applications/LibreOffice.app
# 如未安装
brew install --cask libreoffice
```

**Q: 权限问题**
```bash
# 首次运行 LibreOffice 可能需要授权
open /Applications/LibreOffice.app
# 在系统设置中允许运行
```

### Windows 常见问题

**Q: PDF 转换失败**
- 确保 `poppler/poppler-24.07.0/Library/bin` 存在
- 或将 Poppler bin 目录添加到系统 PATH

### 通用问题

**Q: 依赖安装失败**
```bash
# 使用国内镜像
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

## 💡 使用建议

- **DPI 设置**：
  - 屏幕查看：150-200 DPI
  - 打印质量：300 DPI
  - 高清输出：400-600 DPI

- **格式选择**：
  - PNG：无损压缩，适合文字内容
  - JPG：有损压缩，文件更小，适合图片内容

- **性能优化**：
  - 大文件建议分批处理
  - 降低 DPI 可加快处理速度

## 📦 预编译版本

不熟悉命令行？可下载预编译版本：

- [夸克网盘](https://pan.quark.cn/s/a5d0e37115a8)
- [百度网盘](https://pan.baidu.com/s/1p6reebYtEnxt0od-BxIxyQ?pwd=69hi) 提取码：69hi

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

本项目基于 [MIT License](LICENSE) 开源。

## 🙏 致谢

- [Streamlit](https://streamlit.io/) - Web 应用框架
- [pdf2image](https://github.com/Belval/pdf2image) - PDF 转图片
- [Pillow](https://python-pillow.org/) - 图像处理
- [Poppler](https://poppler.freedesktop.org/) - PDF 渲染引擎

---

<p align="center">
  如有问题或建议，请提交 <a href="https://github.com/你的用户名/File2LongImage/issues">Issue</a>
</p>