#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from app.controllers.base_controller import BaseController


class ComparableController(BaseController):

    def __init__(self):
        super().__init__(None)

    def analyze(self):
        try:
            data = self.get_json_data()
            query = data.get('query', '')
            context = data.get('context', {})
            window_days = int(data.get('window_days', 2))

            if not query:
                return self.error('请输入查询语句', 400)

            base_date = data.get('base_date', None)
            if not base_date:
                from datetime import datetime
                base_date = datetime.now().strftime('%Y%m%d')

            from core.hotspot_fetcher import hotspot_fetcher
            from core.llm_client import llm_client

            window_dates = hotspot_fetcher.get_trading_days_before(base_date, window_days)
            all_dates = [base_date] + window_dates

            hot_data = hotspot_fetcher.get_multi_day_hot_data(all_dates)

            if not hot_data:
                return self.error('未能获取热点数据，请稍后重试', 500)

            for d, rows in list(hot_data.items()):
                found = [r for r in rows if r.get('code') == context.get('stock_code', '') and r.get('reason')]
                if found:
                    context['reason'] = found[0].get('reason', context.get('reason', ''))

            result = llm_client.find_comparable_stocks(query, hot_data, context, window_dates)

            has_date = data.get('has_date', True)
            if has_date:
                import re
                valid_dates = set()
                range_match = re.search(r'(\d{8})\s*到\s*(\d{8})', query)
                if range_match:
                    from datetime import datetime, timedelta
                    start = datetime.strptime(range_match.group(1), '%Y%m%d')
                    end = datetime.strptime(range_match.group(2), '%Y%m%d')
                    d = start
                    while d <= end:
                        valid_dates.add(d.strftime('%Y%m%d'))
                        d += timedelta(days=1)
                else:
                    valid_dates = set(m.group(1) for m in re.finditer(r'\d{8}', query))

                raw_stocks = result.get('stocks', [])
                if raw_stocks and valid_dates:
                    filtered = []
                    for s in raw_stocks:
                        stock_date = (s.get('date', '') or '').replace('-', '')
                        if not stock_date or stock_date in valid_dates:
                            filtered.append(s)
                    if len(filtered) < len(raw_stocks):
                        result['analysis'] += f'\n\n> 注：已自动过滤 {len(raw_stocks) - len(filtered)} 只不符合日期范围的股票。'
                    result['stocks'] = filtered

            return self.success(result)

        except ValueError as e:
            return self.error(str(e), 400)
        except RuntimeError as e:
            return self.error(str(e), 500)
        except Exception as e:
            import traceback
            traceback.print_exc()
            return self.error(f'分析失败: {str(e)}', 500)


comparable_controller = ComparableController()
