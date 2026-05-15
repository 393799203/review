# 移动端应用快速启动指南

## 项目概览

本项目包含两个独立的移动应用：
1. **React Native应用** - 支持Android和iOS平台
2. **鸿蒙原生应用** - 支持HarmonyOS平台

## 快速开始

### React Native应用

#### 1. 环境准备

确保已安装以下工具：
- Node.js >= 18
- React Native CLI
- Android Studio (Android开发)
- Xcode (iOS开发，仅macOS)

#### 2. 安装依赖

```bash
cd mobile/rn-app
npm install
```

#### 3. 配置API地址

编辑 `src/services/api.js`，修改 `BASE_URL`：

```javascript
const BASE_URL = 'http://你的服务器IP:5001/api';
```

#### 4. 运行应用

**Android:**
```bash
npm run android
```

**iOS:**
```bash
npm run ios
```

### 鸿蒙应用

#### 1. 环境准备

- 安装 [DevEco Studio](https://developer.harmonyos.com/cn/develop/deveco-studio)
- 配置HarmonyOS SDK

#### 2. 打开项目

1. 启动DevEco Studio
2. 选择 "Open Project"
3. 打开 `mobile/harmony-app` 目录

#### 3. 配置API地址

编辑 `entry/src/main/ets/common/HttpUtil.ets`：

```typescript
const BASE_URL = 'http://你的服务器IP:5001/api';
```

#### 4. 运行应用

- 在模拟器上运行：Tools > Device Manager > 创建模拟器 > 运行
- 在真机上运行：连接设备 > 开启开发者模式 > 运行

## 功能特性

### 已实现功能

✅ 用户登录注册  
✅ 梯队分析  
✅ 自选股管理  
✅ 统计数据  
✅ 新闻资讯  
✅ 实时行情更新  

### 待开发功能

⬜ K线图展示  
⬜ 股票详细分析  
⬜ 消息推送  
⬜ 离线缓存  
⬜ 深色模式  

## 项目结构

```
mobile/
├── rn-app/                    # React Native应用
│   ├── src/
│   │   ├── screens/          # 页面组件
│   │   │   ├── LoginScreen.js
│   │   │   ├── LadderScreen.js
│   │   │   ├── WatchlistScreen.js
│   │   │   ├── StatisticsScreen.js
│   │   │   └── NewsScreen.js
│   │   ├── services/         # API服务
│   │   │   └── api.js
│   │   └── store/            # 状态管理
│   │       ├── authStore.js
│   │       └── globalStore.js
│   ├── App.js                # 应用入口
│   └── package.json          # 依赖配置
│
└── harmony-app/              # 鸿蒙原生应用
    ├── entry/
    │   └── src/main/
    │       ├── ets/          # ArkTS源代码
    │       │   ├── entryability/
    │       │   ├── pages/
    │       │   └── common/
    │       └── resources/    # 资源文件
    └── AppScope/             # 应用配置
```

## 开发建议

### React Native开发

1. **调试工具**: 使用 React Native Debugger
2. **热重载**: 修改代码后自动刷新
3. **性能优化**: 使用 FlatList 代替 ScrollView
4. **样式**: 使用 StyleSheet.create 优化性能

### 鸿蒙开发

1. **调试工具**: 使用 DevEco Studio 内置调试器
2. **预览器**: 使用 Previewer 快速预览UI
3. **日志**: 使用 HiLog 查看日志
4. **性能**: 使用 Profiler 分析性能

## 常见问题

### React Native

**Q: 运行Android报错 "Unable to load script"**  
A: 确保手机和电脑在同一网络，或使用 `adb reverse tcp:8081 tcp:8081`

**Q: iOS编译失败**  
A: 运行 `cd ios && pod install`

**Q: 网络请求失败**  
A: 检查API地址是否正确，Android需要配置网络权限

### 鸿蒙应用

**Q: 编译错误**  
A: 检查SDK版本，清理项目后重新编译

**Q: 真机无法安装**  
A: 检查签名配置，确保设备已开启开发者模式

**Q: 网络请求失败**  
A: 检查网络权限配置，确认API地址可访问

## 打包发布

### React Native打包

**Android APK:**
```bash
cd rn-app/android
./gradlew assembleRelease
```

**iOS IPA:**
使用Xcode进行Archive并导出

### 鸿蒙应用打包

**HAP包:**
Build > Build Hap(s)/APP(s) > Build Hap(s)

**APP包:**
Build > Build Hap(s)/APP(s) > Build APP(s)

## 技术支持

- React Native文档: https://reactnative.dev/
- 鸿蒙开发文档: https://developer.harmonyos.com/
- 项目问题: 请在项目仓库提交Issue

## 下一步

1. 根据实际需求完善页面功能
2. 添加更多图表组件（K线图、分时图等）
3. 实现消息推送功能
4. 优化UI/UX设计
5. 添加单元测试和集成测试
