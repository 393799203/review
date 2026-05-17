import router from '@ohos.router';
import { StockApi } from '../common/HttpUtil';
import promptAction from '@ohos.promptAction';

@Entry
@Component
struct LoginPage {
  @State username: string = '';
  @State password: string = '';
  @State email: string = '';
  @State confirmPassword: string = '';
  @State nickname: string = '';
  @State isLogin: boolean = true;
  @State isLoading: boolean = false;
  @State usernameError: string = '';
  @State passwordError: string = '';
  @State emailError: string = '';
  @State confirmPasswordError: string = '';
  @State activeTab: number = 0;
  private tabsController: TabsController = new TabsController();

  build() {
    Stack({ alignContent: Alignment.Start }) {
      Column() {
        Column() {
          Row() {
            Column() {
              Text('📈')
                .fontSize(40)
            }
            .width(80)
            .height(80)
            .backgroundColor('rgba(255, 255, 255, 0.2)')
            .borderRadius(20)
            .justifyContent(FlexAlign.Center)
          }
          .margin({ top: 40 })

          Text('节节高')
            .fontSize(32)
            .fontWeight(FontWeight.Bold)
            .fontColor('#FFFFFF')
            .letterSpacing(4)
            .margin({ top: 24, bottom: 8 })

          Text('A股涨停复盘系统')
            .fontSize(14)
            .fontColor('rgba(255, 255, 255, 0.8)')
            .letterSpacing(2)
        }
        .width('100%')
        .alignItems(HorizontalAlign.Center)

        Column() {
          Column() {
            Tabs({ controller: this.tabsController }) {
              TabContent() {
                this.LoginForm()
              }
              .tabBar(this.TabBarBuilder(0, '登录'))

              TabContent() {
                this.RegisterForm()
              }
              .tabBar(this.TabBarBuilder(1, '注册'))
            }
            .barHeight(44)
            .margin({ bottom: 16 })
            .onChange((index: number) => {
              this.activeTab = index;
              this.isLogin = (index === 0);
              this.clearErrors();
            })

            Divider()
              .margin({ top: 16, bottom: 16 })

            Row() {
              Text('登录即表示同意')
                .fontSize(12)
                .fontColor('#8c8c8c')

              Text('用户协议')
                .fontSize(12)
                .fontColor('#1890ff')
                .margin({ left: 4, right: 4 })

              Text('和')
                .fontSize(12)
                .fontColor('#8c8c8c')

              Text('隐私政策')
                .fontSize(12)
                .fontColor('#1890ff')
                .margin({ left: 4 })
            }
            .width('100%')
            .justifyContent(FlexAlign.Center)
          }
          .width('100%')
          .padding({ left: 20, right: 20, top: 24, bottom: 24 })
          .backgroundColor(Color.White)
          .borderRadius(16)
          .shadow({
            radius: 24,
            color: 'rgba(0, 0, 0, 0.15)',
            offsetX: 0,
            offsetY: 8
          })
        }
        .width('100%')
        .layoutWeight(1)
        .justifyContent(FlexAlign.Center)
        .padding({ left: 20, right: 20 })

        Text('© 2024 节节高 All Rights Reserved')
          .fontSize(12)
          .fontColor('rgba(255, 255, 255, 0.5)')
          .margin({ bottom: 40 })
      }
      .width('100%')
      .height('100%')
      .linearGradient({
        angle: 180,
        colors: [['#001529', 0.0], ['#1890ff', 1.0]]
      })
    }
    .width('100%')
    .height('100%')
  }

  @Builder
  TabBarBuilder(index: number, title: string) {
    Column() {
      Text(title)
        .fontSize(16)
        .fontColor(index === this.activeTab ? '#1890ff' : '#8c8c8c')
        .fontWeight(index === this.activeTab ? FontWeight.Bold : FontWeight.Normal)

      Divider()
        .color('#1890ff')
        .strokeWidth(2)
        .width(40)
        .margin({ top: 8 })
        .opacity(index === this.activeTab ? 1 : 0)
    }
    .width('50%')
    .height(44)
    .justifyContent(FlexAlign.Center)
  }

  @Builder
  InputField(icon: string, placeholder: string, inputType: InputType, value: string, error: string, onChange: (value: string) => void, onBlur?: () => void) {
    Column() {
      Row() {
        Text(icon)
          .fontSize(18)
          .fontColor('#1890ff')
          .width(32)
          .height(44)
          .textAlign(TextAlign.Center)

        TextInput({ placeholder: placeholder, text: value })
          .layoutWeight(1)
          .height(44)
          .borderRadius(8)
          .backgroundColor('#FFFFFF')
          .type(inputType)
          .fontColor('#262626')
          .placeholderColor('#bfbfbf')
          .placeholderFont({ size: 14 })
          .borderWidth(error ? 1 : 0)
          .borderColor(error ? '#FF4D4F' : '#FFFFFF')
          .onChange(onChange)
          .onBlur(() => {
            if (onBlur) {
              onBlur();
            }
          })
      }
      .width('100%')
      .height(44)
      .borderRadius(8)
      .backgroundColor('#FFFFFF')
      .borderWidth(1)
      .borderColor(error ? '#FF4D4F' : '#d9d9d9')
      .padding({ left: 12, right: 12 })

      if (error) {
        Text(error)
          .fontSize(12)
          .fontColor('#FF4D4F')
          .width('100%')
          .margin({ top: 4 })
          .padding({ left: 12 })
      }
    }
    .width('100%')
    .margin({ bottom: 16 })
  }

  @Builder
  LoginForm() {
    Column() {
      this.InputField('👤', '用户名', InputType.Normal, this.username, this.usernameError, 
        (value: string) => {
          this.username = value;
          if (this.usernameError) {
            this.usernameError = '';
          }
        },
        () => {
          this.validateUsername();
        }
      )

      this.InputField('🔒', '密码', InputType.Password, this.password, this.passwordError,
        (value: string) => {
          this.password = value;
          if (this.passwordError) {
            this.passwordError = '';
          }
        },
        () => {
          this.validatePassword();
        }
      )

      Button(this.isLoading ? '登录中...' : '登录')
        .width('100%')
        .height(44)
        .borderRadius(8)
        .fontSize(16)
        .fontWeight(FontWeight.Bold)
        .linearGradient({
          angle: 135,
          colors: this.isLoading ? [['#a0d7ff', 0.0], ['#a0d7ff', 1.0]] : [['#1890ff', 0.0], ['#096dd9', 1.0]]
        })
        .enabled(!this.isLoading)
        .margin({ top: 8 })
        .onClick(() => {
          console.log('登录按钮被点击');
          if (this.validateLoginForm()) {
            console.log('验证通过，开始登录');
            this.handleLogin();
          } else {
            console.log('验证失败');
          }
        })
    }
    .width('100%')
  }

  @Builder
  RegisterForm() {
    Column() {
      this.InputField('👤', '用户名（至少3个字符）', InputType.Normal, this.username, this.usernameError,
        (value: string) => {
          this.username = value;
          if (this.usernameError) {
            this.usernameError = '';
          }
        },
        () => {
          this.validateUsername();
        }
      )

      this.InputField('📧', '邮箱', InputType.Email, this.email, this.emailError,
        (value: string) => {
          this.email = value;
          if (this.emailError) {
            this.emailError = '';
          }
        },
        () => {
          this.validateEmail();
        }
      )

      this.InputField('😊', '昵称（选填）', InputType.Normal, this.nickname, '',
        (value: string) => {
          this.nickname = value;
        }
      )

      this.InputField('🔒', '密码（至少6个字符）', InputType.Password, this.password, this.passwordError,
        (value: string) => {
          this.password = value;
          if (this.passwordError) {
            this.passwordError = '';
          }
        },
        () => {
          this.validatePassword();
        }
      )

      this.InputField('🔒', '确认密码', InputType.Password, this.confirmPassword, this.confirmPasswordError,
        (value: string) => {
          this.confirmPassword = value;
          if (this.confirmPasswordError) {
            this.confirmPasswordError = '';
          }
        },
        () => {
          this.validateConfirmPassword();
        }
      )

      Button(this.isLoading ? '注册中...' : '注册')
        .width('100%')
        .height(44)
        .borderRadius(8)
        .fontSize(16)
        .fontWeight(FontWeight.Bold)
        .linearGradient({
          angle: 135,
          colors: this.isLoading ? [['#a0d7ff', 0.0], ['#a0d7ff', 1.0]] : [['#1890ff', 0.0], ['#096dd9', 1.0]]
        })
        .enabled(!this.isLoading)
        .margin({ top: 8 })
        .onClick(() => {
          if (this.validateRegisterForm()) {
            this.handleRegister();
          }
        })
    }
    .width('100%')
  }

  validateUsername(): boolean {
    if (!this.username.trim()) {
      this.usernameError = '请输入用户名';
      return false;
    }
    if (!this.isLogin && this.username.length < 3) {
      this.usernameError = '用户名至少3个字符';
      return false;
    }
    this.usernameError = '';
    return true;
  }

  validatePassword(): boolean {
    if (!this.password) {
      this.passwordError = '请输入密码';
      return false;
    }
    if (!this.isLogin && this.password.length < 6) {
      this.passwordError = '密码至少6个字符';
      return false;
    }
    this.passwordError = '';
    return true;
  }

  validateEmail(): boolean {
    if (!this.email.trim()) {
      this.emailError = '请输入邮箱';
      return false;
    }
    let emailRegex = /^[a-zA-Z0-9._-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,6}$/;
    if (!emailRegex.test(this.email)) {
      this.emailError = '请输入有效的邮箱地址';
      return false;
    }
    this.emailError = '';
    return true;
  }

  validateConfirmPassword(): boolean {
    if (!this.confirmPassword) {
      this.confirmPasswordError = '请确认密码';
      return false;
    }
    if (this.password !== this.confirmPassword) {
      this.confirmPasswordError = '两次输入的密码不一致';
      return false;
    }
    this.confirmPasswordError = '';
    return true;
  }

  validateLoginForm(): boolean {
    console.log('validateLoginForm 开始执行');
    let isValid = true;
    if (!this.validateUsername()) {
      console.log('用户名验证失败');
      isValid = false;
    }
    if (!this.validatePassword()) {
      console.log('密码验证失败');
      isValid = false;
    }
    console.log('验证结果:', isValid);
    return isValid;
  }

  validateRegisterForm(): boolean {
    let isValid = true;
    if (!this.validateUsername()) isValid = false;
    if (!this.validateEmail()) isValid = false;
    if (!this.validatePassword()) isValid = false;
    if (!this.validateConfirmPassword()) isValid = false;
    return isValid;
  }

  clearErrors() {
    this.usernameError = '';
    this.passwordError = '';
    this.emailError = '';
    this.confirmPasswordError = '';
  }

  async handleLogin() {
    console.log('handleLogin 开始执行');
    console.log('用户名:', this.username);
    console.log('密码长度:', this.password.length);
    
    this.isLoading = true;
    try {
      console.log('开始调用登录API');
      let result = await StockApi.login(this.username, this.password);
      console.log('登录结果:', JSON.stringify(result));
      
      if (result.success) {
        console.log('登录成功，保存token');
        // 兼容两种数据结构：result.data.token 和 result.token
        let token = (result.data as Record<string, Object>)?.token || result.token;
        let user = (result.data as Record<string, Object>)?.user || result.user;
        
        if (token) {
          AppStorage.SetOrCreate('token', token as string);
          if (user) {
            AppStorage.SetOrCreate('user', JSON.stringify(user));
          }
          
          // 验证token是否保存成功
          let savedToken = AppStorage.Get<string>('token');
          console.log('保存的token:', savedToken);
          
          promptAction.showToast({ message: '登录成功', bottom: -100 });
          
          console.log('准备跳转到MainPage');
          // 使用 setTimeout 确保 AppStorage 同步完成
          setTimeout(() => {
            console.log('执行跳转');
            router.replaceUrl({ url: 'pages/MainPage' })
              .then(() => {
                console.log('跳转成功');
              })
              .catch((err: Error) => {
                console.error('跳转失败:', err);
              });
          }, 100);
        } else {
          console.log('未获取到token');
          promptAction.showToast({ message: '登录失败：未获取到token', bottom: -100 });
        }
      } else {
        console.log('登录失败:', result.error || result.message);
        promptAction.showToast({ message: result.error || result.message || '登录失败', bottom: -100 });
      }
    } catch (error) {
      console.error('登录错误:', error);
      let errorMessage = '登录失败，请重试';
      if (error && error.message) {
        errorMessage = error.message;
      }
      promptAction.showToast({ message: errorMessage, bottom: -100 });
    } finally {
      this.isLoading = false;
    }
  }

  async handleRegister() {
    this.isLoading = true;
    try {
      let result = await StockApi.register(this.username, this.email, this.password, this.nickname);
      console.log('注册结果:', JSON.stringify(result));
      
      if (result.success) {
        promptAction.showToast({ message: '注册成功，请登录', bottom: -100 });
        this.activeTab = 0;
        this.isLogin = true;
        this.password = '';
        this.confirmPassword = '';
        this.tabsController.changeIndex(0);
      } else {
        promptAction.showToast({ message: result.error || result.message || '注册失败', bottom: -100 });
      }
    } catch (error) {
      console.error('注册错误:', error);
      let errorMessage = '注册失败，请重试';
      if (error && error.message) {
        errorMessage = error.message;
      }
      promptAction.showToast({ message: errorMessage, bottom: -100 });
    } finally {
      this.isLoading = false;
    }
  }
}
