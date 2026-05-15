import http from '@ohos.net.http';

const BASE_URL = 'http://localhost:5001/api';

export class HttpUtil {
  static async request(method: string, url: string, data?: any): Promise<any> {
    return new Promise((resolve, reject) => {
      const httpRequest = http.createHttp();
      
      const token = AppStorage.Get('token');
      const user = AppStorage.Get('user');
      
      const header: any = {
        'Content-Type': 'application/json'
      };
      
      if (token) {
        header['Authorization'] = `Bearer ${token}`;
      }
      
      if (user && user.uid) {
        header['X-User-Uid'] = user.uid;
      }
      
      httpRequest.request(
        BASE_URL + url,
        {
          method: method,
          header: header,
          extraData: data
        },
        (err, data) => {
          if (!err) {
            if (data.responseCode === 200) {
              resolve(JSON.parse(data.result.toString()));
            } else if (data.responseCode === 401) {
              AppStorage.Delete('token');
              AppStorage.Delete('user');
              reject(new Error('未授权，请重新登录'));
            } else {
              reject(new Error('请求失败'));
            }
          } else {
            reject(err);
          }
          httpRequest.destroy();
        }
      );
    });
  }

  static get(url: string): Promise<any> {
    return this.request(http.RequestMethod.GET, url);
  }

  static post(url: string, data?: any): Promise<any> {
    return this.request(http.RequestMethod.POST, url, data);
  }

  static put(url: string, data?: any): Promise<any> {
    return this.request(http.RequestMethod.PUT, url, data);
  }

  static delete(url: string): Promise<any> {
    return this.request(http.RequestMethod.DELETE, url);
  }
}

export class StockApi {
  static getLatestDate() {
    return HttpUtil.get('/latest');
  }

  static getDataByDate(dateStr: string) {
    return HttpUtil.get(`/data/${dateStr}`);
  }

  static getLadderByDate(dateStr: string) {
    return HttpUtil.get(`/ladder/${dateStr}`);
  }

  static getStatistics(dateStr: string) {
    return HttpUtil.get(`/statistics/${dateStr}`);
  }

  static getAvailableDates() {
    return HttpUtil.get('/dates');
  }

  static getWatchlist() {
    return HttpUtil.get('/watchlist');
  }

  static updateWatchlistPrices() {
    return HttpUtil.post('/watchlist/update-prices');
  }

  static buyStock(data: any) {
    return HttpUtil.post('/watchlist/buy', data);
  }

  static sellStock(data: any) {
    return HttpUtil.post('/watchlist/sell', data);
  }

  static login(username: string, password: string) {
    return HttpUtil.post('/auth/login', { username, password });
  }

  static register(username: string, email: string, password: string, nickname?: string) {
    return HttpUtil.post('/auth/register', { username, email, password, nickname });
  }

  static getCurrentUser() {
    return HttpUtil.get('/auth/me');
  }

  static logout() {
    return HttpUtil.post('/auth/logout');
  }
}
