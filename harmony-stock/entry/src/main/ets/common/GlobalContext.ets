import { StockApi } from './HttpUtil';

export interface UserSettings {
  ladder?: PageSettings;
  watchlist?: PageSettings;
  statistics?: PageSettings;
  news?: NewsPageSettings;
}

export interface PageSettings {
  autoRefresh?: boolean;
  refreshInterval?: number;
  smartMode?: boolean;
}

export interface NewsPageSettings extends PageSettings {
  showAllNews?: boolean;
}

const DEFAULT_SETTINGS: UserSettings = {
  ladder: { autoRefresh: false, refreshInterval: 30, smartMode: true },
  watchlist: { autoRefresh: false, refreshInterval: 30, smartMode: true },
  statistics: { autoRefresh: false, refreshInterval: 30, smartMode: true },
  news: { autoRefresh: false, refreshInterval: 300, smartMode: true, showAllNews: false },
};

export class GlobalContext {
  static init() {
    AppStorage.SetOrCreate('currentDate', '');
    AppStorage.SetOrCreate('latestDate', '');
    AppStorage.SetOrCreate('tradingDays', []);
    AppStorage.SetOrCreate('loading', false);
    AppStorage.SetOrCreate('autoRefresh', false);
    AppStorage.SetOrCreate('refreshInterval', 30);
    AppStorage.SetOrCreate('smartMode', true);
    AppStorage.SetOrCreate('showFirstBoard', true);
    AppStorage.SetOrCreate('showAllNews', false);
    AppStorage.SetOrCreate('userSettings', DEFAULT_SETTINGS);
    AppStorage.SetOrCreate('refreshKey', 0);
    AppStorage.SetOrCreate('newsRefreshKey', 0);
    AppStorage.SetOrCreate('watchlistRefreshKey', 0);
    AppStorage.SetOrCreate('statisticsRefreshKey', 0);
  }

  static async loadUserSettings(): Promise<void> {
    try {
      let result = await StockApi.getCurrentUser();
      if (result.success && result.data) {
        let userData = result.data as Record<string, Object>;
        let settings = userData['settings'] as UserSettings || DEFAULT_SETTINGS;
        AppStorage.SetOrCreate('userSettings', settings);
      }
    } catch (error) {
      console.error('加载用户设置失败:', error);
    }
  }

  static async updateUserSettings(page: string, newPageSettings: PageSettings): Promise<void> {
    let currentSettings = AppStorage.Get<UserSettings>('userSettings') || DEFAULT_SETTINGS;
    let updatedSettings: UserSettings = {
      ladder: currentSettings.ladder,
      watchlist: currentSettings.watchlist,
      statistics: currentSettings.statistics,
      news: currentSettings.news
    };

    if (page === 'ladder') {
      updatedSettings.ladder = newPageSettings as PageSettings;
    } else if (page === 'watchlist') {
      updatedSettings.watchlist = newPageSettings as PageSettings;
    } else if (page === 'statistics') {
      updatedSettings.statistics = newPageSettings as PageSettings;
    } else if (page === 'news') {
      updatedSettings.news = newPageSettings as NewsPageSettings;
    }

    AppStorage.SetOrCreate('userSettings', updatedSettings);

    try {
      await StockApi.updateSettings(updatedSettings);
    } catch (error) {
      console.error('更新用户设置失败:', error);
    }
  }

  static setAutoRefresh(value: boolean, page: string): void {
    AppStorage.SetOrCreate('autoRefresh', value);
    GlobalContext.updateUserSettings(page, { autoRefresh: value });
  }

  static setRefreshInterval(value: number, page: string): void {
    AppStorage.SetOrCreate('refreshInterval', value);
    GlobalContext.updateUserSettings(page, { refreshInterval: value });
  }

  static setSmartMode(value: boolean, page: string): void {
    AppStorage.SetOrCreate('smartMode', value);
    GlobalContext.updateUserSettings(page, { smartMode: value });
  }

  static setShowFirstBoard(value: boolean): void {
    AppStorage.SetOrCreate('showFirstBoard', value);
    let settings = AppStorage.Get<UserSettings>('userSettings') || DEFAULT_SETTINGS;
    let ladderSettings: PageSettings = {
      autoRefresh: settings.ladder?.autoRefresh || false,
      refreshInterval: settings.ladder?.refreshInterval || 30,
      smartMode: settings.ladder?.smartMode !== false
    };
    GlobalContext.updateUserSettings('ladder', ladderSettings);
  }

  static setShowAllNews(value: boolean): void {
    AppStorage.SetOrCreate('showAllNews', value);
    let settings = AppStorage.Get<UserSettings>('userSettings') || DEFAULT_SETTINGS;
    let newsSettings: NewsPageSettings = {
      autoRefresh: settings.news?.autoRefresh || false,
      refreshInterval: settings.news?.refreshInterval || 300,
      smartMode: settings.news?.smartMode !== false,
      showAllNews: value
    };
    GlobalContext.updateUserSettings('news', newsSettings);
  }

  static loadPageSettings(page: string): void {
    let settings = AppStorage.Get<UserSettings>('userSettings') || DEFAULT_SETTINGS;
    let pageSettings: PageSettings | undefined;

    if (page === 'ladder') {
      pageSettings = settings.ladder;
    } else if (page === 'watchlist') {
      pageSettings = settings.watchlist;
    } else if (page === 'statistics') {
      pageSettings = settings.statistics;
    } else if (page === 'news') {
      pageSettings = settings.news;
    }

    if (!pageSettings) {
      if (page === 'ladder') {
        pageSettings = DEFAULT_SETTINGS.ladder;
      } else if (page === 'watchlist') {
        pageSettings = DEFAULT_SETTINGS.watchlist;
      } else if (page === 'statistics') {
        pageSettings = DEFAULT_SETTINGS.statistics;
      } else if (page === 'news') {
        pageSettings = DEFAULT_SETTINGS.news;
      }
    }

    AppStorage.SetOrCreate('autoRefresh', pageSettings?.autoRefresh || false);
    AppStorage.SetOrCreate('refreshInterval', pageSettings?.refreshInterval || 30);
    AppStorage.SetOrCreate('smartMode', pageSettings?.smartMode !== false);

    if (page === 'ladder') {
      let ladderSettings = pageSettings as PageSettings;
      AppStorage.SetOrCreate('showFirstBoard', ladderSettings?.smartMode !== false);
    }
    if (page === 'news') {
      let newsSettings = pageSettings as NewsPageSettings;
      AppStorage.SetOrCreate('showAllNews', newsSettings?.showAllNews || false);
    }
  }

  static isInTradingTime(): boolean {
    let now = new Date();
    let hours = now.getHours();
    let minutes = now.getMinutes();
    let currentTime = hours * 60 + minutes;

    let morningStart = 9 * 60 + 15;
    let morningEnd = 11 * 60 + 30;
    let afternoonStart = 13 * 60;
    let afternoonEnd = 15 * 60;

    return (currentTime >= morningStart && currentTime <= morningEnd) ||
           (currentTime >= afternoonStart && currentTime <= afternoonEnd);
  }
}
