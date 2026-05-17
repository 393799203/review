import { StockApi } from '../common/HttpUtil';
import { GlobalContext } from '../common/GlobalContext';
import promptAction from '@ohos.promptAction';

interface BlockInfo {
  change_rate?: number;
  limit_up_num?: number;
  continuous_num?: number;
  high?: string;
  list_days?: number;
  high_stock_name?: string;
}

interface StockItem {
  code?: string;
  name?: string;
  reason?: string;
  limit_up_time?: string;
  limit_up_price?: number;
  limit_up_type?: string;
  high_days?: string;
  block_name?: string;
  detail_reason?: string;
  seal_amount?: number;
  seal_amount_wan?: number;
  continuous_days?: number;
  sector?: string;
  change_percent?: number;
  turnover_rate?: number;
  is_high_stock?: number;
  block_info?: BlockInfo;
}

interface LadderLevel {
  level?: number;
  label?: string;
  stocks?: StockItem[];
}

interface Statistics {
  total_count?: number;
  first_board?: number;
  second_board?: number;
  third_board?: number;
  fourth_board?: number;
  fifth_plus_board?: number;
}

interface LadderData {
  ladder?: LadderLevel[];
  statistics?: Statistics;
  next_day_blocks?: object[];
  yesterday?: object;
}

@Component
export struct LadderPage {
  @State ladderData: LadderData | null = null;
  @State selectedDate: string = '';
  @State latestDate: string = '';
  @State tradingDays: string[] = [];
  @State isLoading: boolean = false;
  @StorageLink('showFirstBoard') showFirstBoard: boolean = true;
  @StorageLink('currentDate') @Watch('onCurrentDateChange') currentDate: string = '';
  @StorageLink('refreshKey') @Watch('onRefreshKeyChange') refreshKey: number = 0;
  
  @State selectedBlocks: string[] = [];
  @State allBlocks: string[] = [];
  @State enableBlur: boolean = false;

  aboutToAppear() {
    GlobalContext.loadPageSettings('ladder');
    if (this.currentDate) {
      this.selectedDate = this.currentDate;
      this.loadLadderData();
    }
  }

  onCurrentDateChange() {
    if (this.currentDate) {
      this.selectedDate = this.currentDate;
      this.loadLadderData();
    }
  }

  onRefreshKeyChange() {
    if (this.refreshKey > 0) {
      this.loadLadderData();
    }
  }

  async loadLadderData() {
    let dateToLoad = this.currentDate || this.selectedDate;
    if (!dateToLoad) return;

    this.isLoading = true;
    try {
      let result = await StockApi.getDataByDate(dateToLoad);
      if (result.success) {
        this.ladderData = result.data as LadderData;
        
        let blockSet = new Set<string>();
        this.ladderData?.ladder?.forEach((level: LadderLevel) => {
          level.stocks?.forEach((stock: StockItem) => {
            if (stock.block_name) {
              blockSet.add(stock.block_name);
            }
          });
        });
        this.allBlocks = Array.from(blockSet);
      }
    } catch (error) {
      console.error('加载梯队数据失败:', error);
      promptAction.showToast({ message: '加载数据失败', bottom: -100 });
    } finally {
      this.isLoading = false;
    }
  }

  toggleBlock(blockName: string) {
    let index = this.selectedBlocks.indexOf(blockName);
    if (index > -1) {
      this.selectedBlocks.splice(index, 1);
    } else {
      this.selectedBlocks.push(blockName);
    }
  }

  selectAllBlocks() {
    if (this.selectedBlocks.length === this.allBlocks.length) {
      this.selectedBlocks = [];
    } else {
      this.selectedBlocks = [...this.allBlocks];
    }
  }

  getFilteredStocks(stocks: StockItem[]): StockItem[] {
    if (this.selectedBlocks.length === 0) {
      return stocks;
    }
    return stocks.filter((stock: StockItem) => 
      this.selectedBlocks.includes(stock.block_name || '')
    );
  }

  shouldShowLevel(level: LadderLevel): boolean {
    if (!this.showFirstBoard && level.level === 1) {
      return false;
    }
    let filteredStocks = this.getFilteredStocks(level.stocks || []);
    return filteredStocks.length > 0;
  }

  getLevelFilteredStocks(level: LadderLevel): StockItem[] {
    return this.getFilteredStocks(level.stocks || []);
  }

  @Builder
  StatsCard() {
    Column() {
      Row() {
        Column() {
          Text('总数')
            .fontSize(10)
            .fontColor('#8c8c8c')
          Text((this.ladderData?.statistics?.total_count || 0).toString())
            .fontSize(18)
            .fontWeight(FontWeight.Bold)
            .fontColor('#FF4D4F')
            .margin({ top: 2 })
        }
        .layoutWeight(1)
        .alignItems(HorizontalAlign.Center)

        Column() {
          Text('首板')
            .fontSize(10)
            .fontColor('#8c8c8c')
          Text((this.ladderData?.statistics?.first_board || 0).toString())
            .fontSize(18)
            .fontWeight(FontWeight.Bold)
            .fontColor('#FF4D4F')
            .margin({ top: 2 })
        }
        .layoutWeight(1)
        .alignItems(HorizontalAlign.Center)

        Column() {
          Text('2板')
            .fontSize(10)
            .fontColor('#8c8c8c')
          Text((this.ladderData?.statistics?.second_board || 0).toString())
            .fontSize(18)
            .fontWeight(FontWeight.Bold)
            .fontColor('#FF4D4F')
            .margin({ top: 2 })
        }
        .layoutWeight(1)
        .alignItems(HorizontalAlign.Center)

        Column() {
          Text('3板')
            .fontSize(10)
            .fontColor('#8c8c8c')
          Text((this.ladderData?.statistics?.third_board || 0).toString())
            .fontSize(18)
            .fontWeight(FontWeight.Bold)
            .fontColor('#FF4D4F')
            .margin({ top: 2 })
        }
        .layoutWeight(1)
        .alignItems(HorizontalAlign.Center)

        Column() {
          Text('4板')
            .fontSize(10)
            .fontColor('#8c8c8c')
          Text((this.ladderData?.statistics?.fourth_board || 0).toString())
            .fontSize(18)
            .fontWeight(FontWeight.Bold)
            .fontColor('#FF4D4F')
            .margin({ top: 2 })
        }
        .layoutWeight(1)
        .alignItems(HorizontalAlign.Center)

        Column() {
          Text('5板+')
            .fontSize(10)
            .fontColor('#8c8c8c')
          Text((this.ladderData?.statistics?.fifth_plus_board || 0).toString())
            .fontSize(18)
            .fontWeight(FontWeight.Bold)
            .fontColor('#FF4D4F')
            .margin({ top: 2 })
        }
        .layoutWeight(1)
        .alignItems(HorizontalAlign.Center)
      }
      .width('100%')
      .padding(8)
    }
    .width('100%')
    .backgroundColor(Color.White)
    .borderRadius(6)
    .margin({ bottom: 8 })
  }

  @Builder
  BlockFilter() {
    Column() {
      Row() {
        Text('板块筛选')
          .fontSize(12)
          .fontWeight(FontWeight.Bold)
          .fontColor('#262626')

        Blank()

        Button(this.selectedBlocks.length === this.allBlocks.length ? '取消' : '全选')
          .fontSize(10)
          .height(22)
          .padding({ left: 6, right: 6 })
          .onClick(() => this.selectAllBlocks())
      }
      .width('100%')
      .padding({ left: 8, right: 8, top: 8, bottom: 8 })

      Scroll() {
        Flex({ wrap: FlexWrap.Wrap }) {
          ForEach(this.allBlocks, (block: string) => {
            Text(block)
              .fontSize(10)
              .fontColor(this.selectedBlocks.includes(block) ? Color.White : '#666666')
              .backgroundColor(this.selectedBlocks.includes(block) ? '#1890ff' : '#F5F5F5')
              .padding({ left: 8, right: 8, top: 4, bottom: 4 })
              .borderRadius(12)
              .margin({ right: 6, bottom: 6 })
              .onClick(() => this.toggleBlock(block))
          })
        }
        .padding({ left: 8, right: 8, bottom: 8 })
      }
      .scrollable(ScrollDirection.Horizontal)
      .scrollBar(BarState.Off)
    }
    .width('100%')
    .backgroundColor(Color.White)
    .borderRadius(6)
    .margin({ bottom: 8 })
  }

  @Builder
  LevelCard(level: LadderLevel) {
    Column() {
      Row() {
        Text(level.label || '')
          .fontSize(13)
          .fontWeight(FontWeight.Bold)
          .fontColor('#262626')

        Blank()

        Text(`${this.getLevelFilteredStocks(level).length}只`)
          .fontSize(10)
          .fontColor('#8c8c8c')
      }
      .width('100%')
      .padding(8)

      Divider()
        .margin({ left: 8, right: 8 })

      ForEach(this.getLevelFilteredStocks(level), (stock: StockItem) => {
        this.StockCard(stock)
      })
    }
    .width('100%')
    .backgroundColor(Color.White)
    .borderRadius(6)
    .margin({ bottom: 8 })
  }

  @Builder
  StockCard(stock: StockItem) {
    Column() {
      Row() {
        Column() {
          Row() {
            Text(this.enableBlur ? '***' : (stock.name || ''))
              .fontSize(13)
              .fontWeight(FontWeight.Bold)
              .fontColor('#262626')

            Text(stock.code || '')
              .fontSize(10)
              .fontColor('#1890ff')
              .margin({ left: 4 })
          }

          Text(this.enableBlur ? '******' : (stock.code || ''))
            .fontSize(10)
            .fontColor('#8c8c8c')
            .margin({ top: 2 })
        }
        .alignItems(HorizontalAlign.Start)
        .layoutWeight(1)

        Column() {
          Text((stock.limit_up_price || 0).toFixed(2))
            .fontSize(14)
            .fontWeight(FontWeight.Bold)
            .fontColor('#262626')

          Text(((stock.change_percent || 0) >= 0 ? '+' : '') + (stock.change_percent || 0).toFixed(2) + '%')
            .fontSize(11)
            .fontWeight(FontWeight.Bold)
            .fontColor((stock.change_percent || 0) >= 0 ? '#FF4D4F' : '#52C41A')
            .margin({ top: 2 })
        }
        .alignItems(HorizontalAlign.End)
      }
      .width('100%')
      .padding(8)

      Divider()
        .margin({ left: 8, right: 8 })

      Row() {
        Text(`涨停: ${stock.limit_up_time || '-'}`)
          .fontSize(10)
          .fontColor('#8c8c8c')

        Blank()

        Text(`封单: ${((stock.seal_amount_wan || 0) / 10000).toFixed(2)}亿`)
          .fontSize(10)
          .fontColor('#8c8c8c')
      }
      .width('100%')
      .padding({ left: 8, right: 8, top: 6, bottom: 6 })

      if (stock.block_name) {
        Row() {
          Text(stock.block_name)
            .fontSize(10)
            .fontColor('#1890ff')
            .backgroundColor('#E6F7FF')
            .padding({ left: 6, right: 6, top: 2, bottom: 2 })
            .borderRadius(4)
        }
        .width('100%')
        .padding({ left: 8, right: 8, bottom: 8 })
      }
    }
    .width('100%')
    .backgroundColor(Color.White)
    .borderRadius(6)
    .margin({ bottom: 8 })
  }

  build() {
    Column() {
      if (this.isLoading && !this.ladderData) {
        Column() {
          LoadingProgress()
            .width(40)
            .height(40)
        }
        .width('100%')
        .layoutWeight(1)
        .justifyContent(FlexAlign.Center)
      } else if (this.ladderData) {
        Scroll() {
          Column() {
            this.StatsCard()
            
            if (this.allBlocks.length > 0) {
              this.BlockFilter()
            }

            ForEach(this.ladderData?.ladder || [], (level: LadderLevel) => {
              if (this.shouldShowLevel(level)) {
                this.LevelCard(level)
              }
            })
          }
          .width('100%')
          .padding(8)
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
