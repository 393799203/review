# 🚀 快速开始

## 当前状态

✅ React Native项目已创建  
✅ 所有业务代码已完成  
✅ Android项目配置已完成  
✅ 项目依赖已安装  

## 立即打包APK

### 步骤1：安装必要环境

**安装Java JDK 17:**
```bash
# macOS
brew install openjdk@17

# 配置Java环境
sudo ln -sfn /usr/local/opt/openjdk@17/libexec/openjdk.jdk /Library/Java/JavaVirtualMachines/openjdk-17.jdk
```

**安装Android Studio:**
1. 下载：https://developer.android.com/studio
2. 安装后打开，安装SDK组件
3. 配置环境变量（添加到 ~/.bash_profile 或 ~/.zshrc）：
```bash
export ANDROID_HOME=$HOME/Library/Android/sdk
export PATH=$PATH:$ANDROID_HOME/emulator
export PATH=$PATH:$ANDROID_HOME/platform-tools
```

### 步骤2：检查环境

```bash
cd mobile/rn-app
./check-env.sh
```

### 步骤3：一键打包

```bash
./build-apk.sh
```

打包完成后，APK文件位于：
```
android/app/build/outputs/apk/release/app-release.apk
```

## 详细文档

- [完整打包指南](./BUILD_GUIDE.md)
- [项目说明](../README.md)
- [快速启动](../QUICKSTART.md)

## 常见问题

### Q: 没有Java环境怎么办？
A: 按照上面的步骤安装Java JDK 17

### Q: 没有Android Studio怎么办？
A: 必须安装Android Studio才能打包APK，它包含了必要的SDK和构建工具

### Q: 打包失败怎么办？
A: 运行 `./check-env.sh` 检查环境，根据提示安装缺失的组件

## 下一步

1. 完成环境安装
2. 运行打包脚本
3. 将生成的APK安装到手机测试
4. 根据需要修改API地址（在 `src/services/api.js` 中）

## 技术支持

如遇到问题，请查看 [BUILD_GUIDE.md](./BUILD_GUIDE.md) 获取详细帮助。
