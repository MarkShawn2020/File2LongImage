# macOS 代码签名配置指南

## 概述
macOS 代码签名用于验证应用的来源和完整性，防止应用被篡改，并允许应用通过 Gatekeeper 安全检查。

## 证书类型

### 1. 开发证书 (Development)
- **文件格式**: `.p12` (包含私钥) 或 `.cer` (仅证书)
- **用途**: 本地开发和测试
- **名称**: "Mac Developer: Your Name (XXXXXXXXXX)"

### 2. 分发证书 (Distribution)
- **Developer ID Application**
  - **文件格式**: `.p12` (必须包含私钥)
  - **用途**: 在 Mac App Store 外分发应用
  - **名称**: "Developer ID Application: Your Name (XXXXXXXXXX)"
  - **特点**: 允许应用在任何 Mac 上运行

- **Mac App Store**
  - **文件格式**: `.p12`
  - **用途**: 提交到 Mac App Store
  - **名称**: "3rd Party Mac Developer Application: Your Name (XXXXXXXXXX)"

### 3. API 密钥 (用于自动化)
- **文件格式**: `.p8`
- **用途**: App Store Connect API，用于自动化上传和公证
- **不是代码签名证书**，而是用于 API 认证

## 获取证书

### 方法一：通过 Xcode（推荐）
```bash
1. 打开 Xcode
2. 菜单栏：Xcode → Settings → Accounts
3. 添加 Apple ID
4. 点击 "Manage Certificates"
5. 点击 "+" 创建 "Developer ID Application" 证书
```

### 方法二：通过 Apple Developer 网站
```bash
1. 访问 https://developer.apple.com/account
2. 进入 Certificates, Identifiers & Profiles
3. 点击 Certificates → "+"
4. 选择 "Developer ID Application"
5. 按照向导生成证书
6. 下载 .cer 文件
7. 双击安装到钥匙串
```

## 安装证书

### 1. 安装 .p12 文件
```bash
# 方法一：双击文件
# 系统会提示输入密码

# 方法二：命令行
security import certificate.p12 -P "密码" -A

# 查看已安装的证书
security find-identity -v -p codesigning
```

### 2. 导出证书为 .p12
```bash
# 如果只有 .cer 文件，需要先安装到钥匙串，然后导出
1. 双击 .cer 文件安装
2. 打开"钥匙串访问"应用
3. 找到证书，右键 → 导出
4. 选择 .p12 格式
5. 设置密码
```

## 配置 build_mac.sh 使用证书

### 自动检测（当前实现）
脚本会自动检测系统中的 Developer ID Application 证书：
```bash
security find-identity -v -p codesigning | grep "Developer ID Application"
```

### 手动指定证书
如需手动指定，修改 `build_mac.sh`：
```bash
# 使用证书名称
IDENTITY="Developer ID Application: Your Name (XXXXXXXXXX)"

# 或使用证书 SHA-1 哈希
IDENTITY="1234567890ABCDEF1234567890ABCDEF12345678"
```

## 代码签名命令

### 基本签名
```bash
codesign --sign "Developer ID Application: Your Name" File2LongImage.app
```

### 深度签名（推荐）
```bash
codesign --deep --force --verify --verbose \
         --sign "Developer ID Application: Your Name" \
         --options runtime \
         File2LongImage.app
```

### 验证签名
```bash
# 检查签名
codesign --verify --verbose File2LongImage.app

# 检查是否会通过 Gatekeeper
spctl -a -t exec -vv File2LongImage.app
```

## 公证 (Notarization)

从 macOS 10.15 开始，分发的应用需要公证：

### 1. 创建 App 专用密码
```bash
1. 访问 https://appleid.apple.com
2. 登录 → 安全 → App 专用密码
3. 生成密码并保存
```

### 2. 保存凭证到钥匙串
```bash
xcrun notarytool store-credentials "notary-profile" \
    --apple-id "your@email.com" \
    --team-id "XXXXXXXXXX" \
    --password "app-specific-password"
```

### 3. 提交公证
```bash
# 创建 zip 文件
ditto -c -k --keepParent File2LongImage.app File2LongImage.zip

# 提交公证
xcrun notarytool submit File2LongImage.zip \
    --keychain-profile "notary-profile" \
    --wait

# 装订票据
xcrun stapler staple File2LongImage.app
```

## 故障排除

### 问题：找不到证书
```bash
# 列出所有代码签名证书
security find-identity -v -p codesigning

# 如果为空，需要先安装证书
```

### 问题：证书不受信任
```bash
# 检查证书状态
security verify-cert -c "certificate.cer"

# 可能需要安装 Apple 中间证书
# 从 https://www.apple.com/certificateauthority/ 下载
```

### 问题：签名后应用无法运行
```bash
# 检查签名详情
codesign -dv --verbose=4 File2LongImage.app

# 检查 entitlements
codesign -d --entitlements - File2LongImage.app
```

## 自动化脚本示例

```bash
#!/bin/bash
# 完整的签名和公证流程

APP_PATH="dist/File2LongImage.app"
IDENTITY="Developer ID Application: Your Name (XXXXXXXXXX)"
PROFILE="notary-profile"

# 1. 签名
echo "签名应用..."
codesign --deep --force --verify --verbose \
         --sign "$IDENTITY" \
         --options runtime \
         --entitlements entitlements.plist \
         "$APP_PATH"

# 2. 验证签名
echo "验证签名..."
codesign --verify --verbose "$APP_PATH"

# 3. 创建 DMG
echo "创建 DMG..."
hdiutil create -volname "File2LongImage" \
               -srcfolder "$APP_PATH" \
               -ov -format UDZO \
               "File2LongImage.dmg"

# 4. 签名 DMG
echo "签名 DMG..."
codesign --sign "$IDENTITY" "File2LongImage.dmg"

# 5. 公证
echo "提交公证..."
xcrun notarytool submit "File2LongImage.dmg" \
                 --keychain-profile "$PROFILE" \
                 --wait

# 6. 装订
echo "装订票据..."
xcrun stapler staple "File2LongImage.dmg"

echo "✅ 完成！"
```

## 总结

- **开发测试**: 不需要证书，但会有安全警告
- **内部分发**: 使用 Developer ID Application 证书 (.p12)
- **公开分发**: 需要证书 + 公证
- **App Store**: 需要特定的分发证书

File2LongImage 的 `build_mac.sh` 已配置为自动检测和使用 Developer ID Application 证书。如果没有证书，应用仍可构建，但用户首次运行时需要在系统设置中允许。