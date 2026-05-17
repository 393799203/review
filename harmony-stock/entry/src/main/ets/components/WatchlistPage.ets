import { StockApi } from '../common/HttpUtil';
import { GlobalContext } from '../common/GlobalContext';

interface WatchlistItem {
  stock_code?: string;
  stock_name?: string;
  ladder?: string;
  change_pct?: number;
  volume_ratio?: number;
  current_price?: number;
  change_rate?: number;
  buy_price?: number;
  buy_quantity?: number;
  is_holding?: boolean;
}

@Component
export struct WatchlistPage {
  @State watchlist: WatchlistItem[] = [];
  @State isLoading: boolean = false;
  @StorageLink('watchlistRefreshKey') @Watch('onRefreshKeyChange') watchlistRefreshKey: number = 0;

  aboutToAppear() {
    GlobalContext.loadPageSettings('watchlist');
    this.loadWatchlist();
  }

  onRefreshKeyChange() {
    if (this.watchlistRefreshKey > 0) {
      this.updatePrices();
    }
  }

  async loadWatchlist() {
    this.isLoading = true;
    try {
      let result = await StockApi.getWatchlist();
      if (result.success) {
        this.watchlist = result.data as WatchlistItem[] || [];
      }
    } catch (error) {
      console.error('加载自选股失败:', error);
    } finally {
      this.isLoading = false;
    }
  }

  async updatePrices() {
    try {
      let result = await StockApi.updateWatchlistPrices();
      if (result.success) {
        await this.loadWatchlist();
      }
    } catch (error) {
      console.error('更新价格失败:', error);
    }
  }

  calculateProfit(stock: WatchlistItem): number {
    return ((stock.current_price || 0) - (stock.buy_price || 0)) * (stock.buy_quantity || 0);
  }

  @Builder
  StockCard(stock: WatchlistItem) {
    Column() {
      Row() {
        Column() {
          Text(stock.stock_name || '')
            .fontSize(16)
            .fontWeight(FontWeight.Bold)
            .fontColor('#262626')

          Text(stock.stock_code || '')
            .fontSize(12)
            .fontColor('#8c8c8c')
            .margin({ top: 4 })
        }
        .alignItems(HorizontalAlign.Start)
        .layoutWeight(1)

        Column() {
          Text((stock.current_price || 0).toFixed(2))
            .fontSize(18)
            .fontWeight(FontWeight.Bold)
            .fontColor('#262626')

          Text(((stock.change_rate || 0) >= 0 ? '+' : '') + ((stock.change_rate || 0) * 100).toFixed(2) + '%')
            .fontSize(14)
            .fontWeight(FontWeight.Bold)
            .fontColor((stock.change_rate || 0) >= 0 ? '#FF4D4F' : '#52C41A')
            .margin({ top: 4 })
        }
        .alignItems(HorizontalAlign.End)
      }
      .width('100%')
      .padding(16)

      if (stock.is_holding && stock.buy_price && stock.buy_quantity) {
        Divider()
          .margin({ left: 16, right: 16 })

        Row() {
          Column() {
            Text('买入价')
              .fontSize(12)
              .fontColor('#8c8c8c')
            Text((stock.buy_price || 0).toFixed(2))
              .fontSize(14)
              .fontColor('#666666')
              .margin({ top: 2 })
          }
          .margin({ right: 24 })

          Column() {
            Text('持仓')
              .fontSize(12)
              .fontColor('#8c8c8c')
            Text((stock.buy_quantity || 0).toString() + '股')
              .fontSize(14)
              .fontColor('#666666')
              .margin({ top: 2 })
          }

          Blank()

          Column() {
            Text('盈亏')
              .fontSize(12)
              .fontColor('#8c8c8c')
            Text((this.calculateProfit(stock) >= 0 ? '+' : '') + this.calculateProfit(stock).toFixed(2))
              .fontSize(14)
              .fontWeight(FontWeight.Bold)
              .fontColor(this.calculateProfit(stock) >= 0 ? '#FF4D4F' : '#52C41A')
              .margin({ top: 2 })
          }
        }
        .width('100%')
        .padding({ left: 16, right: 16, bottom: 16 })
      }
    }
    .width('100%')
    .backgroundColor(Color.White)
    .borderRadius(8)
    .margin({ bottom: 12 })
  }

  build() {
    Column() {
      if (this.isLoading && this.watchlist.length === 0) {
        Column() {
          LoadingProgress()
            .width(50)
            .height(50)
        }
        .width('100%')
        .layoutWeight(1)
        .justifyContent(FlexAlign.Center)
      } else if (this.watchlist.length === 0) {
        Column() {
          Text('暂无自选股')
            .fontSize(16)
            .fontColor('#999999')
        }
        .width('100%')
        .layoutWeight(1)
        .justifyContent(FlexAlign.Center)
      } else {
        Scroll() {
          Column() {
            ForEach(this.watchlist, (stock: WatchlistItem) => {
              this.StockCard(stock)
            })
          }
          .width('100%')
          .padding(12)
        }
        .layoutWeight(1)
        .backgroundColor('#F5F5F5')
      }
    }
    .width('100%')
    .height('100%')
    .backgroundColor('#F5F5F5')
  }
}
