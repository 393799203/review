@Entry
@Component
struct LoginPage {
  @State username: string = ''
  @State password: string = ''
  @State isLogin: boolean = true
  @State isLoading: boolean = false

  build() {
    Column() {
      Text('股票分析系统')
        .fontSize(32)
        .fontWeight(FontWeight.Bold)
        .fontColor('#007AFF')
        .margin({ bottom: 10 })

      Text(this.isLogin ? '登录您的账户' : '创建新账户')
        .fontSize(18)
        .fontColor('#666666')
        .margin({ bottom: 40 })

      Column() {
        TextInput({ placeholder: '用户名' })
          .width('100%')
          .height(50)
          .margin({ bottom: 15 })
          .onChange((value: string) => {
            this.username = value
          })

        if (!this.isLogin) {
          TextInput({ placeholder: '邮箱' })
            .width('100%')
            .height(50)
            .margin({ bottom: 15 })
            .type(InputType.Email)
        }

        TextInput({ placeholder: '密码' })
          .width('100%')
          .height(50)
          .type(InputType.Password)
          .onChange((value: string) => {
            this.password = value
          })

        Button(this.isLoading ? '处理中...' : (this.isLogin ? '登录' : '注册'))
          .width('100%')
          .height(50)
          .backgroundColor('#007AFF')
          .margin({ top: 20 })
          .enabled(!this.isLoading)
          .onClick(() => {
            this.handleSubmit()
          })

        Button(this.isLogin ? '没有账户？立即注册' : '已有账户？立即登录')
          .width('100%')
          .height(50)
          .backgroundColor(Color.Transparent)
          .fontColor('#007AFF')
          .margin({ top: 10 })
          .onClick(() => {
            this.isLogin = !this.isLogin
          })
      }
      .width('85%')
      .padding(20)
      .backgroundColor(Color.White)
      .borderRadius(10)
      .shadow({ radius: 10, color: '#00000010', offsetX: 0, offsetY: 2 })
    }
    .width('100%')
    .height('100%')
    .backgroundColor('#F5F5F5')
    .justifyContent(FlexAlign.Center)
  }

  handleSubmit() {
    if (!this.username || !this.password) {
      console.info('请输入用户名和密码')
      return
    }

    this.isLoading = true
    setTimeout(() => {
      this.isLoading = false
      console.info(this.isLogin ? '登录成功' : '注册成功')
    }, 1000)
  }
}
