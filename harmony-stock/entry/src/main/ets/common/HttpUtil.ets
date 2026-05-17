import http from '@ohos.net.http';
import preference from '@ohos.data.preferences';

const BASE_URL = 'http://218.244.140.186:5001/api';

// 定义响应类型接口
export interface ApiResponse {
  success: boolean;
  error?: string;
  message?: string;
  status?: string;
  data?: object;
  token?: string;
  user?: object;
  dates?: string[];
  latest_date?: string;
  has_more?: boolean;
  total?: number;
  from_cache?: boolean;
  saved_count?: number;
}

// 定义用户信息接口
interface UserInfo {
  uid?: string;
}

// 定义登录请求参数接口
interface LoginParams {
  username: string;
  password: string;
}

// 定义注册请求参数接口
interface RegisterParams {
  username: string;
  email: string;
  password: string;
  nickname?: string;
}

// 定义设置更新参数接口
interface SettingsParams {
  settings: object;
}

// 定义买入股票参数接口
interface BuyStockParams {
  stock_code: string;
  buy_price: number;
  buy_quantity: number;
}

// 定义卖出股票参数接口
interface SellStockParams {
  stock_code: string;
  sell_quantity: number;
}

// 定义刷新数据参数接口
interface RefreshParams {
  date: string;
}

// 定义批量分析参数接口
interface BatchAnalyzeParams {
  stock_codes: string[];
}

export class HttpUtil {
  static async request(method: string, url: string, data?: object): Promise<ApiResponse> {
    let context = AppStorage.Get<Context>('context');

    return new Promise<ApiResponse>((resolve, reject) => {
      let httpRequest = http.createHttp();

      let token = AppStorage.Get<string>('token');
      let userStr = AppStorage.Get<string>('user');

      let header: Record<string, string> = {
        'Content-Type': 'application/json'
      };

      if (token) {
        header['Authorization'] = `Bearer ${token}`;
      }

      if (userStr) {
        try {
          let user: UserInfo = JSON.parse(userStr) as UserInfo;
          if (user.uid) {
            header['X-User-Uid'] = user.uid;
          }
        } catch (e) {
          console.error('解析用户数据失败:', e);
        }
      }

      let options: http.HttpRequestOptions = {
        method: method as http.RequestMethod,
        header: header,
        extraData: data,
        connectTimeout: 30000,
        readTimeout: 30000
      };

      httpRequest.request(BASE_URL + url, options, (err, result) => {
        if (err) {
          reject(err);
          httpRequest.destroy();
          return;
        }

        if (result.responseCode === 200) {
          try {
            let response: ApiResponse = JSON.parse(result.result as string) as ApiResponse;
            if (response.success || response.status === 'success') {
              resolve(response);
            } else {
              reject(new Error(response.error || '请求失败'));
            }
          } catch (e) {
            resolve({ success: true, data: result.result as object });
          }
        } else if (result.responseCode === 401) {
          AppStorage.SetOrCreate('token', '');
          AppStorage.SetOrCreate('user', '');
          reject(new Error('未授权，请重新登录'));
        } else {
          reject(new Error('请求失败'));
        }
        httpRequest.destroy();
      });
    });
  }

  static get(url: string): Promise<ApiResponse> {
    return HttpUtil.request(http.RequestMethod.GET, url);
  }

  static post(url: string, data?: object): Promise<ApiResponse> {
    return HttpUtil.request(http.RequestMethod.POST, url, data);
  }

  static put(url: string, data?: object): Promise<ApiResponse> {
    return HttpUtil.request(http.RequestMethod.PUT, url, data);
  }

  static delete(url: string): Promise<ApiResponse> {
    return HttpUtil.request(http.RequestMethod.DELETE, url);
  }
}

 export class StockApi {
  static getLatestDate(): Promise<ApiResponse> {
    return HttpUtil.get('/latest');
  }

  static getDataByDate(dateStr: string): Promise<ApiResponse> {
    return HttpUtil.get(`/data/${dateStr}`);
  }

  static getLadderByDate(dateStr: string): Promise<ApiResponse> {
    return HttpUtil.get(`/data/${dateStr}`);
  }

  static getStatistics(dateStr: string): Promise<ApiResponse> {
    return HttpUtil.get(`/statistics/${dateStr}`);
  }

  static getAvailableDates(): Promise<ApiResponse> {
    return HttpUtil.get('/dates');
  }

  static getAdjacentTradingDays(dateStr: string): Promise<ApiResponse> {
    return HttpUtil.get(`/adjacent-trading-days/${dateStr}`);
  }

  static refreshData(dateStr: string): Promise<ApiResponse> {
    let params: RefreshParams = { date: dateStr };
    return HttpUtil.post(`/refresh`, params);
  }

  static getWatchlist(): Promise<ApiResponse> {
    return HttpUtil.get('/watchlist');
  }

  static updateWatchlistPrices(): Promise<ApiResponse> {
    return HttpUtil.post('/watchlist/update-prices');
  }

  static buyStock(data: BuyStockParams): Promise<ApiResponse> {
    return HttpUtil.post('/watchlist/buy', data);
  }

  static sellStock(data: SellStockParams): Promise<ApiResponse> {
    return HttpUtil.post('/watchlist/sell', data);
  }

  static getStockKline(stockCode: string, days: number = 60): Promise<ApiResponse> {
    return HttpUtil.get(`/stock/kline/${stockCode}?days=${days}`);
  }

  static getStockIntraday(stockCode: string): Promise<ApiResponse> {
    return HttpUtil.get(`/stock/intraday/${stockCode}`);
  }

  static analyzeStock(stockCode: string, force: boolean = false): Promise<ApiResponse> {
    return HttpUtil.get(`/stock/analyze/${stockCode}?force=${force}`);
  }

  static batchAnalyzeStocks(stockCodes: string[]): Promise<ApiResponse> {
    let params: BatchAnalyzeParams = { stock_codes: stockCodes };
    return HttpUtil.post('/stocks/analyze', params);
  }

  static getClsTelegraph(force: boolean = false, lastCtime?: string, limit: number = 50, loadFromApi: boolean = false): Promise<ApiResponse> {
    let params: string[] = [];
    if (force) params.push('force=true');
    if (lastCtime) params.push(`last_ctime=${encodeURIComponent(lastCtime)}`);
    params.push(`limit=${limit}`);
    if (loadFromApi) params.push('load_from_api=true');
    
    let queryString = params.length > 0 ? `?${params.join('&')}` : '';
    return HttpUtil.get(`/news/cls-telegraph${queryString}`);
  }

  static analyzeNews(newsId: string, force: boolean = false): Promise<ApiResponse> {
    return HttpUtil.get(`/news/analyze/${newsId}?force=${force}`);
  }

  static login(username: string, password: string): Promise<ApiResponse> {
    let params: LoginParams = { username, password };
    return HttpUtil.post('/auth/login', params);
  }

  static register(username: string, email: string, password: string, nickname?: string): Promise<ApiResponse> {
    let params: RegisterParams = { username, email, password, nickname };
    return HttpUtil.post('/auth/register', params);
  }

  static getCurrentUser(): Promise<ApiResponse> {
    return HttpUtil.get('/auth/me');
  }

  static updateSettings(settings: object): Promise<ApiResponse> {
    let params: SettingsParams = { settings };
    return HttpUtil.put('/auth/settings', params);
  }

  static logout(): Promise<ApiResponse> {
    return HttpUtil.post('/auth/logout');
  }
}
