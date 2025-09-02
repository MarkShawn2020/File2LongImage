# .gitignore 整理指南

## 📋 概述

本项目的 `.gitignore` 文件已经过全面重构，采用了专业的分类组织方式，确保：
- ✅ 所有临时文件和构建产物被正确忽略
- ✅ 敏感信息不会被意外提交
- ✅ 保持仓库整洁和高效
- ✅ 跨平台兼容性

## 🏗️ 结构说明

### 1. Python 相关
```
__pycache__/       # Python 字节码缓存
*.py[cod]          # 编译的 Python 文件
build/, dist/      # 打包产物
*.egg-info/        # 包信息
venv/, .venv/      # 虚拟环境
```

### 2. macOS 系统文件
```
.DS_Store          # Finder 元数据
._*                # 资源分支文件
*.app              # 应用包（构建产物）
```

### 3. 项目特定
```
output/            # 转换输出目录
logs/              # 日志文件
.intermediate/     # 临时处理文件
*.spec             # PyInstaller 配置
```

### 4. IDE 配置
```
.vscode/           # VS Code
.idea/             # PyCharm/IntelliJ
*.sublime-*        # Sublime Text
```

### 5. 安全相关
```
*.pem, *.key       # 私钥文件
*.p12, *.p8        # 证书文件
.env*              # 环境变量
credentials.json   # 凭证文件
```

## 🛠️ 使用方法

### 清理现有仓库
```bash
# 运行清理脚本
chmod +x clean_repo.sh
./clean_repo.sh

# 或手动清理
git rm -r --cached .
git add .
git commit -m "chore: 应用新的 .gitignore 规则"
```

### 检查忽略状态
```bash
# 查看哪些文件被忽略
git status --ignored

# 检查特定文件是否被忽略
git check-ignore -v <filename>

# 列出所有被忽略的文件
git ls-files --others --ignored --exclude-standard
```

## 📝 .gitattributes 配置

同时配置了 `.gitattributes` 文件来解决跨平台问题：

### 行尾符规范化
- **脚本文件** (`.sh`, `.command`): 强制使用 LF
- **Python 文件** (`.py`): 强制使用 LF
- **配置文件** (`.json`, `.yml`): 强制使用 LF
- **二进制文件**: 不进行转换

### 应用配置
```bash
# 重新规范化现有文件
git add --renormalize .
git commit -m "chore: 规范化行尾符"
```

## 🎯 最佳实践

### 1. 添加新的忽略规则
```bash
# 编辑 .gitignore
echo "新规则" >> .gitignore

# 立即应用
git rm --cached <要忽略的文件>
git add .gitignore
git commit -m "chore: 更新 .gitignore"
```

### 2. 临时跟踪被忽略的文件
```bash
# 强制添加
git add -f <被忽略的文件>

# 或在 .gitignore 中添加例外
echo "!重要文件.pdf" >> .gitignore
```

### 3. 全局忽略规则
```bash
# 设置全局 .gitignore
git config --global core.excludesfile ~/.gitignore_global

# 添加个人偏好（不影响项目）
echo ".DS_Store" >> ~/.gitignore_global
echo ".vscode/" >> ~/.gitignore_global
```

## 🔍 调试技巧

### 查看忽略规则来源
```bash
git check-ignore -v <文件名>
# 输出：.gitignore:10:*.log	debug.log
```

### 测试忽略规则
```bash
# 干运行，查看会添加哪些文件
git add --dry-run .
```

### 清理已跟踪但应忽略的文件
```bash
# 保留本地文件，但从仓库移除
git rm --cached <文件名>

# 批量操作
git rm -r --cached <目录名>
```

## ⚠️ 注意事项

### 不要忽略的文件
- `requirements.txt` - 依赖清单
- `README.md` - 项目文档
- `LICENSE` - 许可证
- `.gitignore` - 忽略规则本身
- `.gitattributes` - Git 属性配置

### 特殊处理
- **测试文件**: 保留特定的测试文件（如 `test_enhanced_error.py`）
- **资源文件**: 保留 `assets/` 中的图标文件
- **示例配置**: 提供 `.example` 后缀的示例配置文件

## 📊 效果对比

### 整理前
```
仓库大小: ~500MB
文件数量: 10000+
包含: 虚拟环境、构建产物、缓存文件
```

### 整理后
```
仓库大小: ~10MB
文件数量: <100
仅包含: 源代码、文档、必要资源
```

## 🔄 维护建议

1. **定期检查**: 每月检查 `.gitignore` 是否需要更新
2. **版本升级**: 升级工具链时更新相应的忽略规则
3. **团队同步**: 确保团队成员了解忽略规则的变更
4. **文档更新**: 在此文档中记录特殊的忽略需求

## 📚 参考资源

- [GitHub .gitignore 模板](https://github.com/github/gitignore)
- [gitignore.io](https://www.toptal.com/developers/gitignore)
- [Git 官方文档](https://git-scm.com/docs/gitignore)

---

最后更新: 2024-09-02
维护者: File2LongImage Team