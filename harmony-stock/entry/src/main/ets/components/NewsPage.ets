import { StockApi } from '../common/HttpUtil';
import { GlobalContext } from '../common/GlobalContext';
import promptAction from '@ohos.promptAction';

interface NewsItem {
  id?: string;
  title?: string;
  content?: string;
  ctime?: string;
  is_important?: boolean;
  has_stocks?: boolean;
  confirmed?: boolean;
  reading_num?: number;
  stock_list?: StockInfo[];
}

interface StockInfo {
  code?: string;
  name?: string;
}

interface AnalysisResult {
  analysis?: string;
  related_sectors?: RelatedSector[];
  related_stocks?: RelatedStock[];
  market_impact?: string;
  investment_suggestion?: string;
}

interface RelatedSector {
  name?: string;
  relevance?: number;
}

interface RelatedStock {
  code?: string;
  name?: string;
  reason?: string;
}

@Component
export struct NewsPage {
  @State newsList: NewsItem[] = [];
  @State isLoading: boolean = false;
  @State isLoadingMore: boolean = false;
  @State hasMore: boolean = true;
  @State isFirstLoad: boolean = true;
  @StorageLink('showAllNews') showAllNews: boolean = false;
  @StorageLink('newsRefreshKey') @Watch('onRefreshKeyChange') newsRefreshKey: number = 0;
  
  @State analyzingId: string = '';
  @State analysisCache: Map<string, AnalysisResult> = new Map();
  @State expandedIds: Set<string> = new Set();

  aboutToAppear() {
    GlobalContext.loadPageSettings('news');
    this.loadNews(true);
  }

  onRefreshKeyChange() {
    if (this.newsRefreshKey > 0) {
      this.loadNews(true);
    }
  }

  async loadNews(force: boolean = false) {
    if (this.isLoading) return;

    try {
      this.isLoading = true;
      let result = await StockApi.getClsTelegraph(force);

      if (result.success) {
        let newData = result.data as NewsItem[] || [];
        
        if (this.isFirstLoad) {
          this.newsList = newData;
          this.hasMore = result.has_more !== false;
          this.isFirstLoad = false;
        } else {
          let existingIds = new Set(this.newsList.map(n => n.id));
          let newItems = newData.filter(n => !existingIds.has(n.id));
          
          if (newItems.length > 0) {
            this.newsList = [...newItems, ...this.newsList];
            let importantCount = newItems.filter(n => n.is_important).length;
            promptAction.showToast({ message: `新增 ${newItems.length} 条资讯，其中 ${importantCount} 条加红`, bottom: -100 });
          }
        }
      }
    } catch (error) {
      console.error('加载资讯失败:', error);
      promptAction.showToast({ message: '加载资讯失败', bottom: -100 });
    } finally {
      this.isLoading = false;
    }
  }

  async loadMoreNews() {
    if (this.isLoadingMore || !this.hasMore || this.newsList.length === 0) return;

    try {
      this.isLoadingMore = true;
      let lastNews = this.newsList[this.newsList.length - 1];
      let lastCtime = lastNews.ctime || '';

      let result = await StockApi.getClsTelegraph(false, lastCtime, 50);

      if (result.success) {
        let newData = result.data as NewsItem[] || [];
        
        if (newData.length > 0) {
          let existingIds = new Set(this.newsList.map(n => n.id));
          let uniqueNewData = newData.filter(n => !existingIds.has(n.id));
          
          if (uniqueNewData.length > 0) {
            this.newsList = [...this.newsList, ...uniqueNewData];
          }
          this.hasMore = result.has_more !== false;
        } else {
          this.hasMore = false;
        }
      }
    } catch (error) {
      console.error('加载更多资讯失败:', error);
      promptAction.showToast({ message: '加载更多资讯失败', bottom: -100 });
    } finally {
      this.isLoadingMore = false;
    }
  }

  async analyzeNews(newsId: string) {
    if (this.analyzingId === newsId) return;
    
    // 检查缓存
    if (this.analysisCache.has(newsId)) {
      this.expandedIds.add(newsId);
      return;
    }
    
    this.analyzingId = newsId;
    try {
      let result = await StockApi.analyzeNews(newsId);
      if (result.success && result.data) {
        this.analysisCache.set(newsId, result.data as AnalysisResult);
        this.expandedIds.add(newsId);
      } else {
        promptAction.showToast({ message: result.error || '分析失败', bottom: -100 });
      }
    } catch (error) {
      console.error('分析资讯失败:', error);
      promptAction.showToast({ message: '分析资讯失败', bottom: -100 });
    } finally {
      this.analyzingId = '';
    }
  }

  toggleExpand(newsId: string) {
    if (this.expandedIds.has(newsId)) {
      this.expandedIds.delete(newsId);
    } else {
      this.expandedIds.add(newsId);
    }
  }

  @Builder
  NewsCard(news: NewsItem) {
    Column() {
      // 头部：时间和标签
      Row() {
        Text(news.ctime ? news.ctime.split(' ')[1] : '')
          .fontSize(12)
          .fontColor('#8c8c8c')

        if (news.is_important) {
          Text('加红')
            .fontSize(12)
            .fontColor('#FF4D4F')
            .backgroundColor('#FFF1F0')
            .padding({ left: 6, right: 6, top: 2, bottom: 2 })
            .borderRadius(4)
            .margin({ left: 8 })
        }

        if (news.has_stocks) {
          Text('相关股')
            .fontSize(12)
            .fontColor('#1890ff')
            .backgroundColor('#E6F7FF')
            .padding({ left: 6, right: 6, top: 2, bottom: 2 })
            .borderRadius(4)
            .margin({ left: 8 })
        }

        Blank()

        Text(`阅读 ${news.reading_num || 0}`)
          .fontSize(12)
          .fontColor('#8c8c8c')
      }
      .width('100%')
      .margin({ bottom: 8 })

      // 标题
      if (news.title) {
        Text(news.title)
          .fontSize(16)
          .fontWeight(FontWeight.Bold)
          .fontColor(news.is_important ? '#FF4D4F' : '#262626')
          .maxLines(2)
          .textOverflow({ overflow: TextOverflow.Ellipsis })
          .width('100%')
          .margin({ bottom: 8 })
      }

      // 内容
      Text(news.content || '')
        .fontSize(14)
        .fontColor('#666666')
        .maxLines(this.expandedIds.has(news.id) ? 100 : 3)
        .textOverflow({ overflow: TextOverflow.Ellipsis })
        .width('100%')

      // 相关股票
      if (news.stock_list && news.stock_list.length > 0) {
        Row() {
          ForEach(news.stock_list.slice(0, 3), (stock: StockInfo) => {
            Text(stock.name || '')
              .fontSize(12)
              .fontColor('#1890ff')
              .backgroundColor('#E6F7FF')
              .padding({ left: 6, right: 6, top: 2, bottom: 2 })
              .borderRadius(4)
              .margin({ right: 8 })
          })
        }
        .width('100%')
        .margin({ top: 8 })
      }

      // AI分析结果
      if (news.id && this.expandedIds.has(news.id) && this.analysisCache.has(news.id)) {
        this.AnalysisSection(this.analysisCache.get(news.id)!)
      }

      // 底部按钮
      Row() {
        Button(this.expandedIds.has(news.id) ? '收起' : '展开全文')
          .fontSize(12)
          .height(28)
          .padding({ left: 12, right: 12 })
          .backgroundColor('#F5F5F5')
          .fontColor('#666666')
          .onClick(() => this.toggleExpand(news.id || ''))

        if (news.id && this.analysisCache.has(news.id)) {
          Button('再次分析')
            .fontSize(12)
            .height(28)
            .padding({ left: 12, right: 12 })
            .backgroundColor('#F5F5F5')
            .fontColor('#666666')
            .margin({ left: 8 })
            .onClick(() => this.analyzeNews(news.id || ''))
        } else {
          Button(this.analyzingId === news.id ? '分析中...' : 'AI分析')
            .fontSize(12)
            .height(28)
            .padding({ left: 12, right: 12 })
            .backgroundColor(this.analyzingId === news.id ? '#F5F5F5' : '#1890ff')
            .fontColor(this.analyzingId === news.id ? '#999999' : Color.White)
            .margin({ left: 8 })
            .enabled(this.analyzingId !== news.id)
            .onClick(() => this.analyzeNews(news.id || ''))
        }
      }
      .width('100%')
      .margin({ top: 12 })
    }
    .width('100%')
    .padding(16)
    .backgroundColor(Color.White)
    .borderRadius(8)
    .margin({ bottom: 12 })
  }

  @Builder
  @Builder
  AnalysisSection(analysis: AnalysisResult) {
    Column() {
      Divider()
        .margin({ bottom: 12 })

      Text('AI分析')
        .fontSize(14)
        .fontWeight(FontWeight.Bold)
        .fontColor('#262626')
        .width('100%')
        .margin({ bottom: 8 })

      if (analysis?.analysis) {
        Text(analysis.analysis)
          .fontSize(13)
          .fontColor('#666666')
          .width('100%')
          .margin({ bottom: 12 })
      }

      if (analysis?.related_sectors && analysis.related_sectors.length > 0) {
        Text('相关板块：')
          .fontSize(13)
          .fontWeight(FontWeight.Bold)
          .fontColor('#262626')
          .width('100%')
          .margin({ bottom: 4 })

        Flex({ wrap: FlexWrap.Wrap }) {
          ForEach(analysis.related_sectors, (sector: RelatedSector) => {
            Text(sector.name || '')
              .fontSize(12)
              .fontColor('#1890ff')
              .backgroundColor('#E6F7FF')
              .padding({ left: 8, right: 8, top: 4, bottom: 4 })
              .borderRadius(4)
              .margin({ right: 8, bottom: 8 })
          })
        }
        .width('100%')
        .margin({ bottom: 12 })
      }

      if (analysis?.related_stocks && analysis.related_stocks.length > 0) {
        Text('相关个股：')
          .fontSize(13)
          .fontWeight(FontWeight.Bold)
          .fontColor('#262626')
          .width('100%')
          .margin({ bottom: 4 })

        ForEach(analysis.related_stocks.slice(0, 3), (stock: RelatedStock) => {
          Row() {
            Text(stock.name || '')
              .fontSize(12)
              .fontColor('#1890ff')

            Text(stock.reason || '')
              .fontSize(12)
              .fontColor('#8c8c8c')
              .margin({ left: 8 })
              .layoutWeight(1)
          }
          .width('100%')
          .margin({ bottom: 4 })
        })
      }

      if (analysis?.market_impact) {
        Text('市场影响：')
          .fontSize(13)
          .fontWeight(FontWeight.Bold)
          .fontColor('#262626')
          .width('100%')
          .margin({ top: 12, bottom: 4 })

        Text(analysis.market_impact)
          .fontSize(12)
          .fontColor('#666666')
          .width('100%')
      }

      if (analysis?.investment_suggestion) {
        Text('投资建议：')
          .fontSize(13)
          .fontWeight(FontWeight.Bold)
          .fontColor('#262626')
          .width('100%')
          .margin({ top: 12, bottom: 4 })

        Text(analysis.investment_suggestion)
          .fontSize(12)
          .fontColor('#666666')
          .width('100%')
      }
    }
    .width('100%')
    .margin({ top: 12 })
  }

  build() {
    Column() {
      if (this.isLoading && this.newsList.length === 0) {
        Column() {
          LoadingProgress()
            .width(50)
            .height(50)
        }
        .width('100%')
        .layoutWeight(1)
        .justifyContent(FlexAlign.Center)
      } else if (this.newsList.length === 0) {
        Column() {
          Text('暂无资讯')
            .fontSize(16)
            .fontColor('#999999')
        }
        .width('100%')
        .layoutWeight(1)
        .justifyContent(FlexAlign.Center)
      } else {
        List() {
          ForEach(this.newsList, (news: NewsItem) => {
            ListItem() {
              this.NewsCard(news)
            }
          })

          if (this.isLoadingMore) {
            ListItem() {
              Row() {
                LoadingProgress()
                  .width(24)
                  .height(24)
                Text('加载更多...')
                  .fontSize(14)
                  .fontColor('#8c8c8c')
                  .margin({ left: 8 })
              }
              .width('100%')
              .justifyContent(FlexAlign.Center)
              .padding(16)
            }
          }

          if (!this.hasMore && this.newsList.length > 0) {
            ListItem() {
              Text('已经到底了')
                .fontSize(14)
                .fontColor('#999999')
                .width('100%')
                .textAlign(TextAlign.Center)
                .padding(16)
            }
          }
        }
        .width('100%')
        .layoutWeight(1)
        .backgroundColor('#F5F5F5')
        .padding(12)
        .onReachEnd(() => {
          this.loadMoreNews();
        })
      }
    }
    .width('100%')
    .height('100%')
    .backgroundColor('#F5F5F5')
  }
}
