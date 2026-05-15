#!/bin/bash

echo "========================================="
echo "股票分析Android应用打包脚本"
echo "========================================="
echo ""

# 检查Java环境
if ! command -v java &> /dev/null; then
    echo "❌ 错误：未检测到Java环境"
    echo ""
    echo "请先安装Java JDK 17："
    echo "  macOS: brew install openjdk@17"
    echo "  或下载: https://adoptium.net/"
    echo ""
    exit 1
fi

echo "✅ Java环境检测通过"
java -version
echo ""

# 检查Android SDK
if [ -z "$ANDROID_HOME" ]; then
    echo "❌ 错误：未设置ANDROID_HOME环境变量"
    echo ""
    echo "请先安装Android Studio并配置环境变量："
    echo "  export ANDROID_HOME=\$HOME/Library/Android/sdk"
    echo "  export PATH=\$PATH:\$ANDROID_HOME/emulator"
    echo "  export PATH=\$PATH:\$ANDROID_HOME/platform-tools"
    echo ""
    exit 1
fi

echo "✅ Android SDK检测通过"
echo "ANDROID_HOME: $ANDROID_HOME"
echo ""

# 进入项目目录
cd "$(dirname "$0")"

# 安装依赖
echo "📦 安装项目依赖..."
npm install
if [ $? -ne 0 ]; then
    echo "❌ 依赖安装失败"
    exit 1
fi
echo "✅ 依赖安装完成"
echo ""

# 生成debug keystore
echo "🔑 生成签名密钥..."
cd android/app
if [ ! -f debug.keystore ]; then
    keytool -genkeypair -v -storetype PKCS12 \
        -keystore debug.keystore \
        -alias androiddebugkey \
        -storepass android \
        -keypass android \
        -keyalg RSA \
        -keysize 2048 \
        -validity 10000 \
        -dname "CN=Android Debug,O=Android,C=US"
    if [ $? -ne 0 ]; then
        echo "❌ 密钥生成失败"
        exit 1
    fi
    echo "✅ 签名密钥生成完成"
else
    echo "✅ 签名密钥已存在"
fi
cd ../..
echo ""

# 清理旧的构建文件
echo "🧹 清理旧的构建文件..."
cd android
./gradlew clean
if [ $? -ne 0 ]; then
    echo "⚠️  清理失败，继续构建..."
fi
cd ..
echo ""

# 构建APK
echo "🏗️  开始构建APK..."
cd android
./gradlew assembleRelease
if [ $? -ne 0 ]; then
    echo "❌ APK构建失败"
    echo ""
    echo "常见问题："
    echo "1. 确保已安装Android SDK Build-Tools 34.0.0"
    echo "2. 确保已安装Android SDK Platform 34"
    echo "3. 确保已安装Android NDK"
    echo ""
    exit 1
fi
cd ..
echo ""

# 检查APK是否生成
APK_PATH="android/app/build/outputs/apk/release/app-release.apk"
if [ -f "$APK_PATH" ]; then
    echo "✅ APK构建成功！"
    echo ""
    echo "📱 APK文件位置："
    echo "  $(pwd)/$APK_PATH"
    echo ""
    echo "📊 APK文件大小："
    ls -lh "$APK_PATH" | awk '{print "  " $5}'
    echo ""
    echo "🎉 打包完成！您可以将APK安装到Android设备上使用。"
    echo ""
else
    echo "❌ APK文件未找到"
    exit 1
fi
