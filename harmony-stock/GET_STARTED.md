# 鸿蒙股票分析应用 - 快速开始指南

## ✅ 已完成功能

我已经为你实现了完整的股票分析应用，包含以下功能：

### 1. 用户认证
- ✅ 登录页面
- ✅ 注册页面
- ✅ Token管理
- ✅ 自动登录状态

### 2. 梯队分析页面
- ✅ 日期选择器
- ✅ 板块列表展示
- ✅ 股票列表展示
- ✅ 涨跌幅显示（红色上涨，绿色下跌）

### 3. 自选股页面
- ✅ 自选股列表
- ✅ 实时价格显示
- ✅ 涨跌幅展示
- ✅ 刷新功能

### 4. 统计页面
- ✅ 涨停/跌停数量
- ✅ 上涨/下跌家数
- ✅ 数据统计

### 5. 新闻资讯页面
- ✅ 新闻列表
- ✅ 来源和时间显示
- ✅ 内容预览

## 📂 项目文件结构

```
harmony-stock/
└── entry/src/main/ets/
    ├── common/
    │   ├── HttpUtil.ets          # HTTP工具类 + API服务
    │   └── PreferenceUtil.ets    # 本地存储工具类
    ├── entryability/
    │   └── EntryAbility.ets      # 应用入口
    └── pages/
        ├── LoginPage.ets         # 登录/注册页面
        └── MainPage.ets          # 主页面（含4个功能模块）
```

## 🚀 运行应用

### 1. 打开项目

使用DevEco Studio打开项目：
```
/Users/dingyuebo/projects/stock/review/harmony-stock
```

### 2. 配置签名

1. **File > Project Structure**
2. 选择 **Project > Signing Configs**
3. 登录华为开发者账号
4. 勾选 **Automatically generate signature**
5. **Apply** > **OK**

### 3. 修改API地址（重要）

打开 `entry/src/main/ets/common/HttpUtil.ets`，修改第3行：

```typescript
const BASE_URL = 'http://你的服务器IP:5001/api';
```

**获取电脑IP：**
```bash
ifconfig | grep "inet " | grep -v 127.0.0.1
```

### 4. 运行应用

1. 连接鸿蒙手机
2. 点击DevEco Studio运行按钮 ▶️
3. 应用会自动安装到手机

## 📱 应用使用流程

1. **首次打开**：显示登录页面
2. **注册账号**：如果没有账号，点击"立即注册"
3. **登录**：输入用户名和密码登录
4. **使用功能**：
   - 底部导航切换：梯队 / 自选 / 统计 / 资讯
   - 梯队页面：选择日期查看涨停梯队
   - 自选页面：查看自选股实时行情
   - 统计页面：查看市场统计数据
   - 资讯页面：查看最新新闻

## ⚠️ 重要提示

### API地址配置

- **本地测试**：使用电脑局域网IP（如 `192.168.1.100`）
- **不要使用** `localhost` 或 `127.0.0.1`
- **确保手机和服务器在同一网络**

### 网络权限

应用已配置网络权限，可以正常发送HTTP请求。

## 🔧 技术栈

- **框架**：ArkTS + HarmonyOS SDK
- **状态管理**：AppStorage
- **网络请求**：@ohos.net.http
- **页面路由**：@ohos.router
- **本地存储**：@ohos.data.preferences

## 📚 相关文档

- [HarmonyOS开发文档](https://developer.harmonyos.com/cn/docs/documentation/doc-guides/document-outline-0000001064588498)
- [ArkTS语言指南](https://developer.harmonyos.com/cn/docs/documentation/doc-guides/arkts-getting-started-0000001504769321)
- [DevEco Studio使用指南](https://developer.harmonyos.com/cn/docs/documentation/doc-guides/ohos-deveco-studio-overview-0000001053582387)

## 💡 提示

- 首次运行可能需要几分钟编译
- 确保手机已开启开发者模式
- 如果遇到问题，查看DevEco Studio的错误日志

---

**祝你使用愉快！** 🎉
