#!/bin/bash

echo "========================================="
echo "环境检查工具"
echo "========================================="
echo ""

# 检查Node.js
echo "1. 检查Node.js..."
if command -v node &> /dev/null; then
    NODE_VERSION=$(node -v)
    echo "   ✅ Node.js已安装: $NODE_VERSION"
else
    echo "   ❌ Node.js未安装"
    echo "      请访问: https://nodejs.org/"
fi
echo ""

# 检查Java
echo "2. 检查Java JDK..."
if command -v java &> /dev/null; then
    JAVA_VERSION=$(java -version 2>&1 | head -n 1)
    echo "   ✅ Java已安装: $JAVA_VERSION"
else
    echo "   ❌ Java未安装"
    echo "      macOS: brew install openjdk@17"
    echo "      或下载: https://adoptium.net/"
fi
echo ""

# 检查Android SDK
echo "3. 检查Android SDK..."
if [ -n "$ANDROID_HOME" ]; then
    echo "   ✅ ANDROID_HOME已设置: $ANDROID_HOME"
    if [ -d "$ANDROID_HOME" ]; then
        echo "   ✅ Android SDK目录存在"
        
        # 检查build-tools
        if [ -d "$ANDROID_HOME/build-tools" ]; then
            BUILD_TOOLS=$(ls "$ANDROID_HOME/build-tools" | sort -V | tail -n 1)
            echo "   ✅ Build-Tools版本: $BUILD_TOOLS"
        else
            echo "   ❌ Build-Tools未安装"
        fi
        
        # 检查platforms
        if [ -d "$ANDROID_HOME/platforms" ]; then
            PLATFORMS=$(ls "$ANDROID_HOME/platforms" | grep -E "android-[0-9]+" | sort -V | tail -n 1)
            echo "   ✅ Platform版本: $PLATFORMS"
        else
            echo "   ❌ Platforms未安装"
        fi
    else
        echo "   ❌ Android SDK目录不存在"
    fi
else
    echo "   ❌ ANDROID_HOME未设置"
    echo "      请安装Android Studio并配置环境变量"
fi
echo ""

# 检查Gradle
echo "4. 检查Gradle..."
if [ -f "android/gradlew" ]; then
    echo "   ✅ Gradle Wrapper存在"
    cd android
    chmod +x gradlew
    GRADLE_VERSION=$(./gradlew --version 2>&1 | grep "Gradle" | head -n 1)
    echo "   $GRADLE_VERSION"
    cd ..
else
    echo "   ❌ Gradle Wrapper不存在"
fi
echo ""

# 检查项目依赖
echo "5. 检查项目依赖..."
if [ -d "node_modules" ]; then
    echo "   ✅ node_modules存在"
    PACKAGE_COUNT=$(ls -1 node_modules | wc -l | tr -d ' ')
    echo "   已安装 $PACKAGE_COUNT 个包"
else
    echo "   ❌ node_modules不存在"
    echo "      请运行: npm install"
fi
echo ""

# 检查签名密钥
echo "6. 检查签名密钥..."
if [ -f "android/app/debug.keystore" ]; then
    echo "   ✅ debug.keystore存在"
else
    echo "   ⚠️  debug.keystore不存在"
    echo "      将在打包时自动生成"
fi
echo ""

echo "========================================="
echo "环境检查完成"
echo "========================================="
