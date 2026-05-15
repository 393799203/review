# 股票分析移动端应用

基于React Native开发的股票分析移动端应用，支持Android和iOS平台。

## 项目结构

```
mobile/
├── rn-app/                 # React Native应用（Android & iOS）
│   ├── src/
│   │   ├── screens/       # 页面组件
│   │   ├── services/      # API服务
│   │   └── store/         # 状态管理
│   ├── App.js             # 应用入口
│   └── package.json       # 依赖配置
└── harmony-app/           # 鸿蒙原生应用
    └── entry/             # 鸿蒙应用入口
```

## React Native 应用

### 环境要求

- Node.js >= 18
- React Native CLI
- Android Studio (Android开发)
- Xcode (iOS开发，仅macOS)

### 安装依赖

```bash
cd rn-app
npm install
```

### 运行应用

#### Android
```bash
npm run android
```

#### iOS
```bash
npm run ios
```

### 功能特性

- ✅ 用户登录注册
- ✅ 梯队分析
- ✅ 自选股管理
- ✅ 统计数据
- ✅ 新闻资讯
- ✅ 实时行情更新

### 技术栈

- **框架**: React Native 0.74
- **导航**: React Navigation 6
- **状态管理**: Zustand
- **UI组件**: React Native核心组件
- **网络请求**: Axios
- **日期处理**: Day.js

## 鸿蒙应用

鸿蒙应用使用ArkTS开发，位于`harmony-app`目录。

### 环境要求

- DevEco Studio
- HarmonyOS SDK

### 开发指南

请参考鸿蒙应用目录下的README文档。

## API配置

应用默认连接到`http://localhost:5001/api`，请根据实际情况修改`src/services/api.js`中的`BASE_URL`。

## 打包发布

### Android打包

```bash
cd rn-app/android
./gradlew assembleRelease
```

生成的APK位于：`android/app/build/outputs/apk/release/`

### iOS打包

使用Xcode进行打包：
1. 打开`ios/StockApp.xcworkspace`
2. 选择Product > Archive
3. 导出IPA文件

## 注意事项

1. 首次运行前请确保后端服务已启动
2. Android模拟器需要配置网络访问权限
3. iOS需要在Xcode中配置开发者账号
4. 鸿蒙应用需要使用DevEco Studio打开项目

## 开发计划

- [ ] 添加K线图展示
- [ ] 实现股票分析功能
- [ ] 添加消息推送
- [ ] 优化UI/UX
- [ ] 添加离线缓存
