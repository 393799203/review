# Android APK打包指南

## 环境要求

在打包APK之前，请确保已安装以下环境：

### 1. Java JDK 17

**macOS:**
```bash
brew install openjdk@17
sudo ln -sfn /usr/local/opt/openjdk@17/libexec/openjdk.jdk /Library/Java/JavaVirtualMachines/openjdk-17.jdk
```

**Windows:**
下载并安装：https://adoptium.net/

**Linux:**
```bash
sudo apt install openjdk-17-jdk
```

### 2. Android Studio

1. 下载并安装 [Android Studio](https://developer.android.com/studio)
2. 打开Android Studio，安装以下组件：
   - Android SDK Platform 34
   - Android SDK Build-Tools 34.0.0
   - Android NDK (最新版本)
   - Android SDK Command-line Tools

### 3. 环境变量配置

**macOS/Linux (~/.bash_profile 或 ~/.zshrc):**
```bash
export ANDROID_HOME=$HOME/Library/Android/sdk
export PATH=$PATH:$ANDROID_HOME/emulator
export PATH=$PATH:$ANDROID_HOME/platform-tools
export PATH=$PATH:$ANDROID_HOME/cmdline-tools/latest/bin
```

**Windows (系统环境变量):**
```
ANDROID_HOME=C:\Users\你的用户名\AppData\Local\Android\Sdk
PATH添加: %ANDROID_HOME%\platform-tools
PATH添加: %ANDROID_HOME%\cmdline-tools\latest\bin
```

## 快速打包

### 方法一：使用自动化脚本（推荐）

```bash
cd mobile/rn-app
chmod +x build-apk.sh
./build-apk.sh
```

### 方法二：手动打包

1. **安装依赖**
```bash
cd mobile/rn-app
npm install
```

2. **生成签名密钥**
```bash
cd android/app
keytool -genkeypair -v -storetype PKCS12 \
    -keystore debug.keystore \
    -alias androiddebugkey \
    -storepass android \
    -keypass android \
    -keyalg RSA \
    -keysize 2048 \
    -validity 10000 \
    -dname "CN=Android Debug,O=Android,C=US"
cd ../..
```

3. **构建APK**
```bash
cd android
./gradlew assembleRelease
```

4. **获取APK**
构建完成后，APK文件位于：
```
android/app/build/outputs/apk/release/app-release.apk
```

## 常见问题

### 1. Java环境问题

**问题：** `Unable to locate a Java Runtime`

**解决：**
```bash
# 检查Java是否安装
java -version

# 如果未安装，请按照上面的步骤安装Java JDK 17
```

### 2. Android SDK问题

**问题：** `SDK location not found`

**解决：**
创建 `android/local.properties` 文件：
```properties
sdk.dir=/Users/你的用户名/Library/Android/sdk
```

### 3. Gradle构建失败

**问题：** `Could not resolve all files for configuration`

**解决：**
```bash
cd android
./gradlew clean
./gradlew assembleRelease
```

### 4. NDK问题

**问题：** `No version of NDK matched the requested version`

**解决：**
在Android Studio中安装NDK：
1. 打开 Android Studio
2. Preferences → Appearance & Behavior → System Settings → Android SDK
3. 选择 SDK Tools 标签
4. 勾选 "NDK (Side by side)"
5. 点击 Apply 安装

## APK安装

### 方法一：通过ADB安装

```bash
adb install android/app/build/outputs/apk/release/app-release.apk
```

### 方法二：直接传输

1. 将APK文件传输到Android设备
2. 在设备上打开文件管理器
3. 点击APK文件进行安装
4. 如果提示"未知来源"，请在设置中允许安装未知来源应用

## 发布版本打包

### 1. 生成正式签名密钥

```bash
keytool -genkeypair -v \
    -keystore stock-app-release.keystore \
    -alias stock-app \
    -keyalg RSA \
    -keysize 2048 \
    -validity 10000
```

### 2. 配置签名信息

在 `android/gradle.properties` 中添加：
```properties
MYAPP_RELEASE_STORE_FILE=stock-app-release.keystore
MYAPP_RELEASE_KEY_ALIAS=stock-app
MYAPP_RELEASE_STORE_PASSWORD=你的密钥库密码
MYAPP_RELEASE_KEY_PASSWORD=你的密钥密码
```

### 3. 构建发布版本

```bash
cd android
./gradlew assembleRelease
```

## 优化建议

### 减小APK体积

1. 启用ProGuard（已在build.gradle中配置）
2. 使用APK Analyzer分析体积
3. 移除未使用的资源

### 性能优化

1. 启用Hermes引擎（已默认启用）
2. 使用React Native性能工具
3. 优化图片资源

## 技术支持

如遇到其他问题，请查看：
- [React Native官方文档](https://reactnative.dev/docs/signed-apk-android)
- [Android开发者文档](https://developer.android.com/studio/build)
