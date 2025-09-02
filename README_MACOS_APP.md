# File2LongImage macOS 应用程序

将 File2LongImage 打包成原生 macOS 应用程序，提供更好的用户体验。

## 🎯 特性

### 原生 macOS 体验
- ✅ 独立应用程序，无需 Python 环境
- ✅ 原生菜单栏集成
- ✅ 支持拖放文件（高级版）
- ✅ macOS 快捷键支持
- ✅ Retina 显示屏优化
- ✅ 暗色模式支持

### 核心功能
- 批量文件转换
- 实时进度显示
- 可调节 DPI（72-600）
- PNG/JPG 输出格式
- JPG 质量控制

## 🚀 快速构建

### 一键构建
```bash
# 赋予执行权限
chmod +x build_mac.sh

# 运行构建脚本
./build_mac.sh
```

构建脚本会自动：
1. 检查系统依赖
2. 安装必要的工具
3. 创建应用图标
4. 打包应用程序
5. 生成 DMG 安装包

### 手动构建

#### 1. 安装依赖
```bash
# 安装系统依赖
brew install poppler
brew install --cask libreoffice  # 可选

# 安装 Python 依赖
pip install -r requirements_gui.txt
pip install py2app
```

#### 2. 运行开发版本
```bash
# 带拖放支持（需要 tkinterdnd2）
python mac_app.py

# 简化版（无需额外依赖）
python mac_app_simple.py
```

#### 3. 打包应用
```bash
# 清理旧文件
rm -rf build dist

# 构建应用
python setup.py py2app

# 应用在 dist/File2LongImage.app
```

## 📦 安装和分发

### 安装到本地
```bash
# 复制到应用程序文件夹
cp -r dist/File2LongImage.app /Applications/
```

### 分发给其他用户

构建完成后会生成：
- `dist/File2LongImage.app` - 应用程序
- `dist/File2LongImage.dmg` - DMG 安装包

用户可以：
1. 下载 DMG 文件
2. 双击打开
3. 拖动应用到 Applications 文件夹

## 🎨 界面预览

### 主界面
- 文件列表管理
- 参数设置区域
- 实时进度显示
- 状态信息反馈

### 菜单栏
```
File2LongImage
├── 关于
├── 偏好设置 (Cmd+,)
└── 退出 (Cmd+Q)

文件
├── 打开文件 (Cmd+O)
├── 清空列表
└── 转换 (Cmd+R)

编辑
└── 删除选中 (Delete)

窗口
└── 最小化 (Cmd+M)

帮助
└── 使用指南
```

## ⌨️ 快捷键

| 快捷键 | 功能 |
|-------|------|
| Cmd+O | 打开文件 |
| Cmd+R | 开始转换 |
| Cmd+, | 偏好设置 |
| Cmd+Q | 退出程序 |
| Cmd+M | 最小化窗口 |
| Delete | 删除选中文件 |

## 🛠 自定义配置

### 修改应用信息

编辑 `setup.py` 中的 plist 配置：
```python
'plist': {
    'CFBundleName': '你的应用名',
    'CFBundleVersion': '版本号',
    # ...
}
```

### 自定义图标

1. 准备 512x512 PNG 图片
2. 保存为 `assets/icon.png`
3. 运行构建脚本会自动生成 icns

### 添加代码签名

如果有开发者证书：
```bash
# 查看证书
security find-identity -v -p codesigning

# 手动签名
codesign --deep --force --verify --verbose \
         --sign "Developer ID Application: Your Name" \
         dist/File2LongImage.app
```

## 🐛 故障排除

### 常见问题

**Q: 应用无法打开，提示"已损坏"**
```bash
# 清除隔离属性
xattr -cr /Applications/File2LongImage.app
```

**Q: 拖放功能不可用**
```bash
# 安装 tkinterdnd2
pip install tkinterdnd2

# 使用简化版
python mac_app_simple.py
```

**Q: Poppler 工具找不到**
```bash
# 确认 Poppler 安装
which pdftoppm

# 重新安装
brew reinstall poppler
```

**Q: 构建失败**
```bash
# 清理并重试
rm -rf build dist
pip install --upgrade py2app
python setup.py py2app
```

## 📝 版本选择

### mac_app.py（完整版）
- ✅ 拖放文件支持
- ✅ 更流畅的用户体验
- ⚠️ 需要 tkinterdnd2

### mac_app_simple.py（简化版）
- ✅ 无额外依赖
- ✅ 完整功能支持
- ❌ 无拖放功能

## 🔄 更新应用

1. 修改代码
2. 更新版本号（setup.py）
3. 重新运行构建脚本
4. 测试新版本
5. 分发更新

## 📄 许可

本项目基于 MIT License 开源。

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

---

**提示**：首次使用建议先运行开发版本测试，确认功能正常后再打包分发。