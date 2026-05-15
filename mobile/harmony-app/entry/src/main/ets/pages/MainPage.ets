@Entry
@Component
struct MainPage {
  @State currentIndex: number = 0

  private tabsController: TabsController = new TabsController()

  @Builder
  TabBuilder(index: number, name: string, icon: Resource) {
    Column() {
      Image(icon)
        .width(24)
        .height(24)
        .fillColor(this.currentIndex === index ? '#007AFF' : '#999999')
      
      Text(name)
        .fontSize(12)
        .margin({ top: 4 })
        .fontColor(this.currentIndex === index ? '#007AFF' : '#999999')
    }
    .width('100%')
    .height('100%')
    .justifyContent(FlexAlign.Center)
  }

  build() {
    Column() {
      Tabs({ barPosition: BarPosition.End, controller: this.tabsController }) {
        TabContent() {
          LadderPage()
        }
        .tabBar(this.TabBuilder(0, '梯队', $r('app.media.ic_trending')))

        TabContent() {
          WatchlistPage()
        }
        .tabBar(this.TabBuilder(1, '自选', $r('app.media.ic_star')))

        TabContent() {
          StatisticsPage()
        }
        .tabBar(this.TabBuilder(2, '统计', $r('app.media.ic_chart')))

        TabContent() {
          NewsPage()
        }
        .tabBar(this.TabBuilder(3, '资讯', $r('app.media.ic_news')))
      }
      .barHeight(56)
      .onChange((index: number) => {
        this.currentIndex = index
      })
    }
    .width('100%')
    .height('100%')
  }
}

@Component
struct LadderPage {
  build() {
    Column() {
      Text('梯队分析')
        .fontSize(20)
        .fontWeight(FontWeight.Bold)
        .margin({ top: 20, bottom: 20 })

      Text('梯队分析页面内容')
        .fontSize(16)
        .fontColor('#999999')
    }
    .width('100%')
    .height('100%')
    .backgroundColor('#F5F5F5')
  }
}

@Component
struct WatchlistPage {
  build() {
    Column() {
      Text('自选股')
        .fontSize(20)
        .fontWeight(FontWeight.Bold)
        .margin({ top: 20, bottom: 20 })

      Text('自选股页面内容')
        .fontSize(16)
        .fontColor('#999999')
    }
    .width('100%')
    .height('100%')
    .backgroundColor('#F5F5F5')
  }
}

@Component
struct StatisticsPage {
  build() {
    Column() {
      Text('统计数据')
        .fontSize(20)
        .fontWeight(FontWeight.Bold)
        .margin({ top: 20, bottom: 20 })

      Text('统计数据页面内容')
        .fontSize(16)
        .fontColor('#999999')
    }
    .width('100%')
    .height('100%')
    .backgroundColor('#F5F5F5')
  }
}

@Component
struct NewsPage {
  build() {
    Column() {
      Text('新闻资讯')
        .fontSize(20)
        .fontWeight(FontWeight.Bold)
        .margin({ top: 20, bottom: 20 })

      Text('新闻资讯页面内容')
        .fontSize(16)
        .fontColor('#999999')
    }
    .width('100%')
    .height('100%')
    .backgroundColor('#F5F5F5')
  }
}
