import { StockApi } from '../common/HttpUtil';
import { GlobalContext } from '../common/GlobalContext';

interface StatisticsData {
  limit_up_count?: number;
  limit_down_count?: number;
  up_count?: number;
  down_count?: number;
}

@Component
export struct StatisticsPage {
  @State statistics: StatisticsData | null = null;
  @State isLoading: boolean = false;
  @StorageLink('statisticsRefreshKey') @Watch('onRefreshKeyChange') statisticsRefreshKey: number = 0;

  aboutToAppear() {
    GlobalContext.loadPageSettings('statistics');
    this.loadStatistics();
  }

  onRefreshKeyChange() {
    if (this.statisticsRefreshKey > 0) {
      this.loadStatistics();
    }
  }

  async loadStatistics() {
    this.isLoading = true;
    try {
      let latestResult = await StockApi.getLatestDate();
      if (latestResult.success && latestResult.latest_date) {
        let statsResult = await StockApi.getStatistics(latestResult.latest_date);
        if (statsResult.success) {
          this.statistics = statsResult.data as StatisticsData;
        }
      }
    } catch (error) {
      console.error('加载统计数据失败:', error);
    } finally {
      this.isLoading = false;
    }
  }

  build() {
    Column() {
      if (this.isLoading && !this.statistics) {
        Column() {
          LoadingProgress()
            .width(50)
            .height(50)
        }
        .width('100%')
        .layoutWeight(1)
        .justifyContent(FlexAlign.Center)
      } else if (this.statistics) {
        Scroll() {
          Column() {
            Column() {
              Text('市场概况')
                .fontSize(16)
                .fontWeight(FontWeight.Bold)
                .fontColor('#262626')
                .width('100%')
                .padding(16)

              Divider()
                .margin({ left: 16, right: 16 })

              Row() {
                Column() {
                  Text('涨停')
                    .fontSize(14)
                    .fontColor('#8c8c8c')
                  Text((this.statistics.limit_up_count || 0).toString())
                    .fontSize(28)
                    .fontWeight(FontWeight.Bold)
                    .fontColor('#FF4D4F')
                    .margin({ top: 4 })
                }
                .layoutWeight(1)
                .alignItems(HorizontalAlign.Center)

                Column() {
                  Text('跌停')
                    .fontSize(14)
                    .fontColor('#8c8c8c')
                  Text((this.statistics.limit_down_count || 0).toString())
                    .fontSize(28)
                    .fontWeight(FontWeight.Bold)
                    .fontColor('#52C41A')
                    .margin({ top: 4 })
                }
                .layoutWeight(1)
                .alignItems(HorizontalAlign.Center)
              }
              .width('100%')
              .padding({ left: 16, right: 16, bottom: 16 })

              Divider()
                .margin({ left: 16, right: 16 })

              Row() {
                Column() {
                  Text('上涨')
                    .fontSize(14)
                    .fontColor('#8c8c8c')
                  Text((this.statistics.up_count || 0).toString())
                    .fontSize(28)
                    .fontWeight(FontWeight.Bold)
                    .fontColor('#FF4D4F')
                    .margin({ top: 4 })
                }
                .layoutWeight(1)
                .alignItems(HorizontalAlign.Center)

                Column() {
                  Text('下跌')
                    .fontSize(14)
                    .fontColor('#8c8c8c')
                  Text((this.statistics.down_count || 0).toString())
                    .fontSize(28)
                    .fontWeight(FontWeight.Bold)
                    .fontColor('#52C41A')
                    .margin({ top: 4 })
                }
                .layoutWeight(1)
                .alignItems(HorizontalAlign.Center)
              }
              .width('100%')
              .padding(16)
            }
            .width('100%')
            .backgroundColor(Color.White)
            .borderRadius(8)
            .margin({ bottom: 12 })
          }
          .width('100%')
          .padding(12)
        }
        .layoutWeight(1)
        .backgroundColor('#F5F5F5')
      } else {
        Column() {
          Text('暂无统计数据')
            .fontSize(16)
            .fontColor('#999999')
        }
        .width('100%')
        .layoutWeight(1)
        .justifyContent(FlexAlign.Center)
      }
    }
    .width('100%')
    .height('100%')
    .backgroundColor('#F5F5F5')
  }
}
