# 鸿蒙应用开发指南

## 项目说明

这是股票分析系统的鸿蒙原生应用，使用ArkTS开发。

## 环境要求

- DevEco Studio 4.0 或更高版本
- HarmonyOS SDK API 10 或更高版本
- Node.js 14.19.1 或更高版本

## 项目结构

```
harmony-app/
├── AppScope/              # 应用全局配置
│   └── app.json5         # 应用配置文件
├── entry/                 # 主模块
│   └── src/
│       └── main/
│           ├── ets/       # ArkTS源代码
│           │   ├── entryability/  # 应用入口
│           │   └── pages/         # 页面文件
│           └── resources/  # 资源文件
└── build-profile.json5    # 构建配置
```

## 开发步骤

### 1. 安装DevEco Studio

从华为开发者官网下载并安装DevEco Studio：
https://developer.harmonyos.com/cn/develop/deveco-studio

### 2. 打开项目

1. 启动DevEco Studio
2. 选择 "Open Project"
3. 选择 `harmony-app` 目录

### 3. 配置签名

1. 在DevEco Studio中，选择 "File > Project Structure"
2. 在 "Project" 页面配置签名信息
3. 或使用自动签名功能

### 4. 运行应用

#### 在模拟器上运行
1. 创建模拟器：Tools > Device Manager
2. 选择模拟器并运行

#### 在真机上运行
1. 连接鸿蒙设备
2. 开启开发者模式和USB调试
3. 点击运行按钮

## 功能模块

### 已实现功能
- ✅ 登录注册页面
- ✅ 主页面框架（底部导航）
- ✅ 四个主要功能模块：
  - 梯队分析
  - 自选股管理
  - 统计数据
  - 新闻资讯

### 待开发功能
- [ ] API接口集成
- [ ] 数据展示优化
- [ ] K线图组件
- [ ] 实时行情推送
- [ ] 本地数据缓存

## API配置

在 `ets/common/HttpUtil.ets` 中配置后端API地址：

```typescript
const BASE_URL = 'http://your-server-ip:5001/api'
```

## 打包发布

### 生成HAP包

1. 选择 Build > Build Hap(s)/APP(s) > Build Hap(s)
2. 生成的HAP包位于：`entry/build/default/outputs/default/`

### 生成APP包（用于发布）

1. 选择 Build > Build Hap(s)/APP(s) > Build APP(s)
2. 生成的APP包位于：`entry/build/default/outputs/default/`

## 注意事项

1. **网络权限**：已在 `module.json5` 中配置网络权限
2. **调试模式**：开发时建议开启调试模式
3. **真机调试**：需要在设备上安装证书
4. **API地址**：真机调试时需要使用实际的服务器IP地址

## 开发资源

- [鸿蒙开发文档](https://developer.harmonyos.com/cn/docs/documentation/doc-guides/document-outline-0000001064588498)
- [ArkTS语言指南](https://developer.harmonyos.com/cn/docs/documentation/doc-guides/arkts-getting-started-0000001504769321)
- [DevEco Studio使用指南](https://developer.harmonyos.com/cn/docs/documentation/doc-guides/ohos-deveco-studio-overview-0000001053582387)

## 常见问题

### 1. 编译错误
- 检查SDK版本是否匹配
- 清理项目：Build > Clean Project

### 2. 运行失败
- 检查设备连接
- 检查签名配置
- 查看日志：Log > HiLog

### 3. 网络请求失败
- 检查网络权限配置
- 确认API地址正确
- 检查服务器是否可访问
