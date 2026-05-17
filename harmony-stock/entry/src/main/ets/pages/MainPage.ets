import router from '@ohos.router';
import promptAction from '@ohos.promptAction';
import { LadderPage } from '../components/LadderPage';
import { NewsPage } from '../components/NewsPage';
import { WatchlistPage } from '../components/WatchlistPage';
import { StatisticsPage } from '../components/StatisticsPage';
import { GlobalContext } from '../common/GlobalContext';
import { StockApi } from '../common/HttpUtil';
import { DatePickerDialog } from '../components/DatePickerDialog';

interface AdjacentTradingDaysData {
  prev: string;
  next: string;
  trading_days: string[];
}

@Entry
@Component
struct MainPage {
  @State currentIndex: number = 0;
  @StorageLink('token') token: string = '';
  @StorageLink('user') userStr: string = '';
  @StorageLink('currentDate') currentDate: string = '';
  @StorageLink('latestDate') latestDate: string = '';
  @StorageLink('tradingDays') tradingDays: string[] = [];
  @StorageLink('loading') loading: boolean = false;
  @StorageLink('autoRefresh') autoRefresh: boolean = false;
  @StorageLink('refreshInterval') refreshInterval: number = 30;
  @StorageLink('smartMode') smartMode: boolean = true;
  @StorageLink('showFirstBoard') showFirstBoard: boolean = true;
  @StorageLink('showAllNews') showAllNews: boolean = false;
  
  @State showSettingsDialog: boolean = false;
  @State showDatePicker: boolean = false;
  @State prevDate: string = '';
  @State nextDate: string = '';
  
  private tabsController: TabsController = new TabsController();
  private refreshIntervalId: number = -1;

  aboutToAppear() {
    let savedToken = AppStorage.Get<string>('token') || '';
    console.log('MainPage aboutToAppear, token:', savedToken);
    
    if (!savedToken) {
      console.log('没有token，跳转到登录页');
      router.replaceUrl({ url: 'pages/LoginPage' });
    } else {
      console.log('有token，初始化MainPage');
      GlobalContext.init();
      GlobalContext.loadUserSettings();
      this.loadLatestDate();
      this.startAutoRefresh();
    }
  }

  aboutToDisappear() {
    this.stopAutoRefresh();
  }

  async loadLatestDate() {
    try {
      let result = await StockApi.getLatestDate();
      if (result.success && result.latest_date) {
        this.latestDate = result.latest_date;
        this.currentDate = result.latest_date;
        await this.loadAdjacentTradingDays();
      }
    } catch (error) {
      console.error('加载最新日期失败:', error);
    }
  }

  async loadAdjacentTradingDays() {
    if (!this.currentDate) return;
    
    try {
      let result = await StockApi.getAdjacentTradingDays(this.currentDate);
      if (result.success && result.data) {
        let data = result.data as AdjacentTradingDaysData;
        this.prevDate = data.prev || '';
        this.nextDate = data.next || '';
        this.tradingDays = data.trading_days || [];
      }
    } catch (error) {
      console.error('加载相邻交易日失败:', error);
    }
  }

  async handlePrevDay() {
    if (!this.prevDate) {
      promptAction.showToast({ message: '没有更早的交易日了' });
      return;
    }
    this.currentDate = this.prevDate;
    await this.loadAdjacentTradingDays();
  }

  async handleNextDay() {
    if (!this.nextDate) {
      promptAction.showToast({ message: '已经是最新的交易日了' });
      return;
    }
    this.currentDate = this.nextDate;
    await this.loadAdjacentTradingDays();
  }

  handleDateSelect(date: string) {
    this.currentDate = date;
    this.showDatePicker = false;
    this.loadAdjacentTradingDays();
  }

  handleRefresh() {
    if (this.currentIndex === 0) {
      AppStorage.SetOrCreate('refreshKey', Date.now());
    } else if (this.currentIndex === 1) {
      AppStorage.SetOrCreate('newsRefreshKey', Date.now());
    } else if (this.currentIndex === 2) {
      AppStorage.SetOrCreate('watchlistRefreshKey', Date.now());
    } else if (this.currentIndex === 3) {
      AppStorage.SetOrCreate('statisticsRefreshKey', Date.now());
    }
    
    promptAction.showToast({ message: '刷新中...' });
  }

  startAutoRefresh() {
    this.stopAutoRefresh();
    
    if (!this.autoRefresh) return;
    
    let shouldRefresh = this.smartMode ? GlobalContext.isInTradingTime() : true;
    if (!shouldRefresh) return;
    
    this.refreshIntervalId = setInterval(() => {
      let stillInTime = this.smartMode ? GlobalContext.isInTradingTime() : true;
      if (stillInTime) {
        this.handleRefresh();
      }
    }, this.refreshInterval * 1000);
  }

  stopAutoRefresh() {
    if (this.refreshIntervalId !== -1) {
      clearInterval(this.refreshIntervalId);
      this.refreshIntervalId = -1;
    }
  }

  handleLogout() {
    AlertDialog.show({
      title: '确认登出',
      message: '确定要退出登录吗？',
      primaryButton: {
        value: '取消',
        action: () => {}
      },
      secondaryButton: {
        value: '确定',
        fontColor: '#FF4D4F',
        action: () => {
          this.stopAutoRefresh();
          AppStorage.SetOrCreate('token', '');
          AppStorage.SetOrCreate('user', '');
          router.replaceUrl({ url: 'pages/LoginPage' });
        }
      }
    });
  }

  @Builder
  HeaderBar() {
    Row() {
      if (this.currentIndex === 0) {
        Row() {
          Button('前')
            .fontSize(11)
            .height(24)
            .padding({ left: 6, right: 6 })
            .enabled(this.prevDate !== '')
            .onClick(() => this.handlePrevDay())
          
          Button(this.currentDate || '日期')
            .fontSize(11)
            .height(24)
            .padding({ left: 8, right: 8 })
            .backgroundColor('#F5F5F5')
            .fontColor('#262626')
            .margin({ left: 6, right: 6 })
            .onClick(() => {
              this.showDatePicker = true;
            })
          
          if (this.currentDate !== this.latestDate) {
            Button('后')
              .fontSize(11)
              .height(24)
              .padding({ left: 6, right: 6 })
              .enabled(this.nextDate !== '')
              .onClick(() => this.handleNextDay())
          }

          Toggle({ type: ToggleType.Switch, isOn: this.showFirstBoard })
            .width(32)
            .height(18)
            .selectedColor('#1890ff')
            .onChange((isOn: boolean) => {
              GlobalContext.setShowFirstBoard(isOn);
            })
        }
        .layoutWeight(1)
      } else if (this.currentIndex === 1) {
        Row() {
          Toggle({ type: ToggleType.Switch, isOn: this.showAllNews })
            .width(32)
            .height(18)
            .selectedColor('#1890ff')
            .onChange((isOn: boolean) => {
              GlobalContext.setShowAllNews(isOn);
            })
        }
        .layoutWeight(1)
        .justifyContent(FlexAlign.End)
      } else {
        Blank()
          .layoutWeight(1)
      }

      Row() {
        Button({ type: ButtonType.Circle }) {
          Text('🔄')
            .fontSize(14)
        }
        .width(28)
        .height(28)
        .backgroundColor('#F5F5F5')
        .onClick(() => this.handleRefresh())

        Toggle({ type: ToggleType.Switch, isOn: this.autoRefresh })
          .width(32)
          .height(18)
          .selectedColor('#1890ff')
          .margin({ left: 8 })
          .onChange((isOn: boolean) => {
            let pages = ['ladder', 'news', 'watchlist', 'statistics'];
            GlobalContext.setAutoRefresh(isOn, pages[this.currentIndex]);
            
            if (isOn) {
              this.startAutoRefresh();
              this.showSettingsDialog = true;
            } else {
              this.stopAutoRefresh();
            }
          })
      }
    }
    .width('100%')
    .height(48)
    .padding({ left: 12, right: 12 })
    .backgroundColor(Color.White)
    .border({ width: { bottom: 1 }, color: '#F0F0F0' })
  }

  @Builder
  TabBar() {
    Row() {
      this.TabBarItem(0, '📈', '天梯')
      this.TabBarItem(1, '📰', '资讯')
      this.TabBarItem(2, '⭐', '自选')
      this.TabBarItem(3, '📊', '统计')
    }
    .width('100%')
    .height(48)
    .backgroundColor(Color.White)
    .border({ width: { top: 1 }, color: '#F0F0F0' })
  }

  @Builder
  TabBarItem(index: number, icon: string, name: string) {
    Column() {
      Text(icon)
        .fontSize(18)
        .opacity(index === this.currentIndex ? 1.0 : 0.6)

      Text(name)
        .fontSize(10)
        .fontColor(index === this.currentIndex ? '#1890ff' : '#999999')
        .fontWeight(index === this.currentIndex ? FontWeight.Bold : FontWeight.Normal)
        .margin({ top: 2 })
    }
    .layoutWeight(1)
    .height('100%')
    .justifyContent(FlexAlign.Center)
    .onClick(() => {
      this.currentIndex = index;
      this.tabsController.changeIndex(index);
      
      let pages = ['ladder', 'news', 'watchlist', 'statistics'];
      GlobalContext.loadPageSettings(pages[index]);
      
      if (this.autoRefresh) {
        this.startAutoRefresh();
      }
    })
  }

  build() {
    Column() {
      this.HeaderBar()

      Tabs({
        barPosition: BarPosition.End,
        controller: this.tabsController
      }) {
        TabContent() {
          LadderPage()
        }

        TabContent() {
          NewsPage()
        }

        TabContent() {
          WatchlistPage()
        }

        TabContent() {
          StatisticsPage()
        }
      }
      .barHeight(0)
      .layoutWeight(1)

      this.TabBar()
    }
    .width('100%')
    .height('100%')
    .backgroundColor('#F5F5F5')
    .bindSheet($$this.showSettingsDialog, this.SettingsSheet(), {
      height: 280,
      backgroundColor: Color.White,
      dragBar: true
    })
    .bindSheet($$this.showDatePicker, this.DatePickerSheet(), {
      height: 380,
      backgroundColor: Color.White,
      dragBar: true
    })
  }

  @Builder
  DatePickerSheet() {
    DatePickerDialog({
      selectedDate: $currentDate,
      tradingDays: $tradingDays,
      currentDate: this.currentDate,
      onConfirm: (date: string) => {
        this.handleDateSelect(date);
      },
      onCancel: () => {
        this.showDatePicker = false;
      }
    })
  }

  @Builder
  SettingsSheet() {
    Column() {
      Text('自动刷新设置')
        .fontSize(16)
        .fontWeight(FontWeight.Bold)
        .fontColor('#262626')
        .width('100%')
        .padding(12)

      Divider()

      Column() {
        Row() {
          Text('刷新时段')
            .fontSize(14)
            .fontColor('#262626')
            .layoutWeight(1)

          Row() {
            Button('交易时段')
              .fontSize(12)
              .height(28)
              .type(this.smartMode ? ButtonType.Capsule : ButtonType.Normal)
              .backgroundColor(this.smartMode ? '#1890ff' : '#F5F5F5')
              .fontColor(this.smartMode ? Color.White : '#666666')
              .onClick(() => {
                GlobalContext.setSmartMode(true, ['ladder', 'news', 'watchlist', 'statistics'][this.currentIndex]);
                if (this.autoRefresh) {
                  this.startAutoRefresh();
                }
              })

            Button('全天')
              .fontSize(12)
              .height(28)
              .type(!this.smartMode ? ButtonType.Capsule : ButtonType.Normal)
              .backgroundColor(!this.smartMode ? '#1890ff' : '#F5F5F5')
              .fontColor(!this.smartMode ? Color.White : '#666666')
              .margin({ left: 6 })
              .onClick(() => {
                GlobalContext.setSmartMode(false, ['ladder', 'news', 'watchlist', 'statistics'][this.currentIndex]);
                if (this.autoRefresh) {
                  this.startAutoRefresh();
                }
              })
          }
        }
        .width('100%')
        .padding({ left: 12, right: 12, top: 12, bottom: 12 })

        Divider()
          .margin({ left: 12, right: 12 })

        Row() {
          Text('刷新频率')
            .fontSize(14)
            .fontColor('#262626')
            .layoutWeight(1)

          Row() {
            ForEach([10, 30, 60, 300], (interval: number) => {
              Button(interval < 60 ? `${interval}秒` : '5分')
                .fontSize(12)
                .height(28)
                .type(this.refreshInterval === interval ? ButtonType.Capsule : ButtonType.Normal)
                .backgroundColor(this.refreshInterval === interval ? '#1890ff' : '#F5F5F5')
                .fontColor(this.refreshInterval === interval ? Color.White : '#666666')
                .margin({ left: 6 })
                .onClick(() => {
                  GlobalContext.setRefreshInterval(interval, ['ladder', 'news', 'watchlist', 'statistics'][this.currentIndex]);
                  if (this.autoRefresh) {
                    this.startAutoRefresh();
                  }
                })
            })
          }
        }
        .width('100%')
        .padding({ left: 12, right: 12, top: 12, bottom: 12 })
      }

      Blank()

      Button('关闭')
        .width('90%')
        .height(36)
        .backgroundColor('#1890ff')
        .margin({ bottom: 12 })
        .onClick(() => {
          this.showSettingsDialog = false;
        })
    }
    .width('100%')
    .height('100%')
  }
}
