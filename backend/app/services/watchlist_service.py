#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Optional, List, Dict, Tuple
from datetime import date, datetime
from decimal import Decimal
from app.services.base_service import BaseService
from app.repositories.watchlist_repository import WatchlistRepository
from models import WatchlistStock, TradeRecord

# mootdx 客户端复用（沪/深各一个，避免每次请求新建连接）
_mootdx_clients = {}

# 向量搜索相似度阈值：入选原因与查询词的余弦相似度低于此值不算匹配
WATCHLIST_VEC_SIM_THRESHOLD = 0.5


def _get_mootdx_client(market: int):
    from mootdx.quotes import Quotes
    if market not in _mootdx_clients:
        _mootdx_clients[market] = Quotes.factory(market=market)
    return _mootdx_clients[market]


class WatchlistService(BaseService):
    """自选股服务类"""
    
    def __init__(self):
        super().__init__(WatchlistRepository())
        self.watchlist_repository = self.repository
    
    def get_watchlist_with_quotes(self, user_id: str) -> Tuple[bool, str, Optional[List[Dict]]]:
        """
        获取自选股列表(带实时行情)
        
        Args:
            user_id: 用户ID
            
        Returns:
            tuple: (success, message, data)
        """
        try:
            watchlist = self.watchlist_repository.get_by_user_id(user_id)
            
            stock_codes = [stock.stock_code.split('.')[0] for stock in watchlist]
            
            quotes_dict = self._fetch_realtime_quotes(stock_codes)
            
            # 批量查询盈亏与持仓（避免每只股票单独开 session）
            profits_map = self.watchlist_repository.get_total_profits_map(user_id, stock_codes)
            buy_map = self.watchlist_repository.get_buy_records_map(user_id, stock_codes)
            
            result = []
            for stock in watchlist:
                stock_data = self._build_stock_data(
                    stock, user_id, quotes_dict, profits_map, buy_map
                )
                result.append(stock_data)
            
            return True, '获取成功', result
            
        except Exception as e:
            return False, str(e), None
    
    def _fetch_realtime_quotes(self, stock_codes: List[str]) -> Dict:
        """获取实时行情（mootdx 客户端复用）"""
        from mootdx.quotes import Quotes

        quotes_dict = {}
        
        if not stock_codes:
            return quotes_dict
        
        sh_codes = [code for code in stock_codes if code.startswith('6')]
        sz_codes = [code for code in stock_codes if not code.startswith('6')]
        
        for market, codes in ((1, sh_codes), (0, sz_codes)):
            if not codes:
                continue
            try:
                client = _get_mootdx_client(market)
                quotes = client.quotes(symbol=codes)
                
                if quotes is not None and hasattr(quotes, 'empty') and not quotes.empty:
                    for idx, row in quotes.iterrows():
                        code = row['code']
                        quotes_dict[code] = {
                            'price': float(row.get('price', 0) or 0),
                            'high': float(row.get('high', 0) or 0),
                            'low': float(row.get('low', 0) or 0),
                            'prev_close': float(row.get('last_close', 0) or 0),
                        }
            except Exception as e:
                print(f"批量获取{'沪' if market == 1 else '深'}市实时行情失败: {e}")
        
        return quotes_dict
    
    def _build_stock_data(self, stock: WatchlistStock, user_id: str, quotes_dict: Dict,
                          profits_map: Dict = None, buy_map: Dict = None) -> Dict:
        """构建股票数据（批量 map 优先，缺失时回退单查）"""
        code = stock.stock_code.split('.')[0]
        if profits_map is not None:
            stock_total_profit = profits_map.get(stock.stock_code, 0.0)
        else:
            stock_total_profit = self.watchlist_repository.get_total_profit(user_id, stock.stock_code)

        if buy_map is not None:
            buy_records = buy_map.get(stock.stock_code, [])
        else:
            buy_records = self.watchlist_repository.get_buy_records(user_id, stock.stock_code)
        
        current_quantity = sum(r.remaining_quantity for r in buy_records)
        
        stock_code_num = stock.stock_code.split('.')[0]
        quote = quotes_dict.get(stock_code_num)
        current_price = quote['price'] if quote else None
        prev_close = quote['prev_close'] if quote else None
        day_low = quote.get('low') if quote else None
        
        if current_price and prev_close and prev_close > 0:
            day_change_pct = (current_price - prev_close) / prev_close * 100
        else:
            day_change_pct = None
        
        if current_quantity > 0:
            total_cost = sum(float(r.price) * r.remaining_quantity for r in buy_records)
            avg_buy_price = total_cost / current_quantity
            
            if current_price:
                position_profit = (current_price - avg_buy_price) * current_quantity
                position_profit_ratio = (current_price - avg_buy_price) / avg_buy_price
            else:
                position_profit = None
                position_profit_ratio = None
            
            position_status = '持仓'
            buy_date = min(r.operation_date for r in buy_records)
        else:
            position_profit = None
            position_profit_ratio = None
            position_status = '空仓'
            avg_buy_price = None
            buy_date = None
        
        return {
            'id': stock.id,
            'stock_code': stock.stock_code,
            'stock_name': stock.stock_name,
            'add_date': stock.add_date.strftime('%Y%m%d') if stock.add_date else '',
            'add_price': float(stock.add_price) if stock.add_price else None,
            'alert_price': float(stock.alert_price) if stock.alert_price else None,
            'signal_date': stock.signal_date.strftime('%Y%m%d') if stock.signal_date else None,
            'current_price': float(current_price) if current_price else None,
            'day_low': float(day_low) if day_low else None,
            'day_change_pct': float(day_change_pct) if day_change_pct is not None else None,
            'add_reason': stock.add_reason or '',
            'source': stock.source or '',
            'add_type': stock.add_type or 'manual',
            'limit_up_reason_category': stock.limit_up_reason_category or '',
            'position_status': position_status,
            'buy_price': float(avg_buy_price) if avg_buy_price else None,
            'buy_date': buy_date.strftime('%Y-%m-%d') if buy_date else None,
            'buy_quantity': current_quantity,
            'position_profit': float(position_profit) if position_profit is not None else None,
            'position_profit_ratio': float(position_profit_ratio) if position_profit_ratio is not None else None,
            'total_profit': float(stock_total_profit),
            'created_at': stock.created_at.strftime('%Y-%m-%d %H:%M:%S') if stock.created_at else ''
        }

    @staticmethod
    def _ensure_batch_reason_vecs(reasons: List[str]) -> bool:
        """批量补齐入选原因向量（复用 block_matcher 的跨请求 reason 缓存）"""
        from app.core.block_matcher import _reason_vec_cache
        from app.core.embedding import embed_texts

        missing = [r for r in reasons if r and r not in _reason_vec_cache]
        if not missing:
            return True
        vecs = embed_texts(missing)
        if vecs is None:
            return False
        for r, v in zip(missing, vecs):
            _reason_vec_cache[r] = v
        return True

    def vector_search(self, user_id: str, query: str) -> Tuple[bool, str, Optional[List[Dict]]]:
        """
        向量语义搜索自选股：查询词向量化后与每只自选股"入选原因"做余弦相似度，
        返回相似度 ≥ 阈值的股票（按相似度降序，含行情与持仓数据）。
        """
        try:
            query = (query or '').strip()
            if not query:
                return False, '请输入搜索关键词', None

            watchlist = self.watchlist_repository.get_by_user_id(user_id)
            if not watchlist:
                return True, '暂无自选股', []

            # 1. 查询词向量化
            from app.core.embedding import embed_texts
            q_vecs = embed_texts([query])
            if not q_vecs:
                return False, '向量服务不可用（embedding 模型未加载）', None
            q_vec = q_vecs[0]

            # 2. 入选原因批量向量化（仅保留有原因的股票）
            reason_items = [(s, (s.add_reason or '').strip()) for s in watchlist]
            reason_items = [(s, r) for s, r in reason_items if r]
            if not reason_items:
                return True, '自选股暂无入选原因，无法向量匹配', []

            if not self._ensure_batch_reason_vecs([r for _, r in reason_items]):
                return False, '向量服务不可用（embedding 模型未加载）', None

            import numpy as np
            from app.core.block_matcher import _reason_vec_cache

            mat = np.array(
                [_reason_vec_cache[r] for _, r in reason_items], dtype=np.float32
            )
            sims = mat @ np.array(q_vec, dtype=np.float32)  # (N,) 余弦

            # 3. 阈值过滤 + 相似度降序
            hits = [
                (stock, float(sim))
                for (stock, _), sim in zip(reason_items, sims)
                if sim >= WATCHLIST_VEC_SIM_THRESHOLD
            ]
            hits.sort(key=lambda x: x[1], reverse=True)

            if not hits:
                return True, '未匹配到相关自选股', []

            # 4. 行情与持仓数据组装（复用批量逻辑）
            hit_codes = [stock.stock_code.split('.')[0] for stock, _ in hits]
            quotes_dict = self._fetch_realtime_quotes(hit_codes)
            profits_map = self.watchlist_repository.get_total_profits_map(user_id, hit_codes)
            buy_map = self.watchlist_repository.get_buy_records_map(user_id, hit_codes)

            sim_map = {stock.stock_code: sim for stock, sim in hits}
            result = []
            for stock, _ in hits:
                data = self._build_stock_data(
                    stock, user_id, quotes_dict, profits_map, buy_map
                )
                data['vec_sim'] = round(sim_map.get(stock.stock_code, 0.0), 3)
                result.append(data)

            return True, f'匹配到 {len(result)} 只', result

        except Exception as e:
            return False, str(e), None
    
    def add_to_watchlist(self, user_id: str, stock_code: str, stock_name: str, 
                        add_date: date, add_price: float = None, add_reason: str = '',
                        source: str = 'wencai', add_type: str = 'manual',
                        limit_up_reason_category: str = '', alert_price: float = None,
                        signal_date: date = None) -> Tuple[bool, str]:
        """
        添加股票到自选
        
        Args:
            user_id: 用户ID
            stock_code: 股票代码
            stock_name: 股票名称
            add_date: 添加日期
            add_price: 添加价格
            add_reason: 添加原因
            source: 来源
            add_type: 添加类型
            limit_up_reason_category: 涨停原因分类
            alert_price: 预警价格（可为 None）
            signal_date: 放量首日（策略信号日，可为 None）
            
        Returns:
            tuple: (success, message)
        """
        if self.watchlist_repository.exists_in_watchlist(user_id, stock_code):
            return False, '该股票已在自选列表中'
        
        try:
            self.watchlist_repository.create(
                user_id=user_id,
                stock_code=stock_code,
                stock_name=stock_name,
                add_date=add_date,
                add_price=add_price,
                alert_price=alert_price,
                signal_date=signal_date,
                add_reason=add_reason,
                source=source,
                add_type=add_type,
                limit_up_reason_category=limit_up_reason_category
            )
            return True, '添加成功'
        except Exception as e:
            return False, str(e)
    
    def remove_from_watchlist(self, user_id: str, stock_code: str) -> Tuple[bool, str]:
        """
        从自选中删除股票
        
        Args:
            user_id: 用户ID
            stock_code: 股票代码
            
        Returns:
            tuple: (success, message)
        """
        stock = self.watchlist_repository.get_by_user_and_code(user_id, stock_code)
        
        if not stock:
            return False, '股票不在自选列表中'
        
        if self.watchlist_repository.has_position(user_id, stock_code):
            return False, '该股票正在持仓中，请先卖出后再删除'
        
        try:
            self.watchlist_repository.delete_by_user_and_code(user_id, stock_code)
            return True, '删除成功'
        except Exception as e:
            return False, str(e)

    def remove_many(self, user_id: str, stock_codes: list) -> Tuple[bool, str, int, list]:
        """
        批量删除自选股（持仓中的股票跳过不删，单 session 批量处理）
        
        Args:
            user_id: 用户ID
            stock_codes: 股票代码列表
            
        Returns:
            tuple: (success, message, deleted_count, skipped_codes)
        """
        if not stock_codes:
            return False, '请选择要删除的股票', 0, []

        session = self.watchlist_repository.create_session()
        try:
            # 一次查询所有目标自选股
            stocks = session.query(WatchlistStock).filter(
                WatchlistStock.user_id == user_id,
                WatchlistStock.stock_code.in_(stock_codes)
            ).all()
            targets = {s.stock_code: s for s in stocks}

            # 一次查询持仓中的股票（批量）
            held = set()
            if targets:
                held_rows = session.query(TradeRecord.stock_code).filter(
                    TradeRecord.user_id == user_id,
                    TradeRecord.stock_code.in_(list(targets.keys())),
                    TradeRecord.operation_type == '买入',
                    TradeRecord.remaining_quantity > 0
                ).distinct().all()
                held = {r[0] for r in held_rows}

            deleted = 0
            skipped = []
            for code in stock_codes:
                stock = targets.get(code)
                if not stock:
                    continue
                if code in held:
                    skipped.append(code)
                    continue
                session.delete(stock)
                deleted += 1
            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

        if deleted == 0 and skipped:
            return False, '所选股票均在持仓中，请先卖出后再删除', deleted, skipped
        msg = f'已删除 {deleted} 只'
        if skipped:
            msg += f'，{len(skipped)} 只持仓中已跳过'
        return True, msg, deleted, skipped

    def update_alert_price(self, user_id: str, stock_code: str, alert_price) -> Tuple[bool, str]:
        """
        更新自选股预警价格（alert_price 为 None 时清除）
        
        Args:
            user_id: 用户ID
            stock_code: 股票代码
            alert_price: 预警价格（float 或 None）
            
        Returns:
            tuple: (success, message)
        """
        if alert_price is not None:
            try:
                price = float(alert_price)
                if price <= 0:
                    return False, '预警价格必须大于 0'
            except (TypeError, ValueError):
                return False, '预警价格格式错误'
        else:
            price = None

        stock = self.watchlist_repository.get_by_user_and_code(user_id, stock_code)
        if not stock:
            return False, '股票不在自选列表中'

        try:
            self.watchlist_repository.update_alert_price(user_id, stock_code, price)
            if price is None:
                return True, '预警价格已清除'
            return True, '预警价格已更新'
        except Exception as e:
            return False, str(e)
    
    def search_stock(self, keyword: str) -> Tuple[bool, str, Optional[List[Dict]]]:
        """
        搜索股票
        
        Args:
            keyword: 搜索关键词
            
        Returns:
            tuple: (success, message, data)
        """
        if not keyword:
            return True, '获取成功', []
        
        try:
            import requests as req_module
            
            url = "https://searchapi.eastmoney.com/api/suggest/get"
            params = {
                "input": keyword,
                "type": "14",
                "token": "D43BF722C8E33BCE90EFB9D8653D9A5B",
                "count": 20,
                "cb": ""
            }
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://quote.eastmoney.com/",
                "Accept": "*/*",
                "Accept-Encoding": "gzip, deflate, br",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"
            }
            
            response = req_module.get(url, params=params, headers=headers, timeout=5)
            
            if response.status_code != 200:
                return False, f'搜索失败，状态码: {response.status_code}', None
            
            try:
                text = response.text.strip()
                if text.startswith('(') and text.endswith(')'):
                    text = text[1:-1]
                data = json.loads(text)
            except Exception as json_err:
                return False, '搜索接口返回数据格式错误', None
            
            stocks = []
            if data and 'QuotationCodeTable' in data:
                table_data = data['QuotationCodeTable']
                if table_data and 'Data' in table_data and isinstance(table_data['Data'], list):
                    for item in table_data['Data']:
                        code = item.get('Code', '')
                        name = item.get('Name', '')
                        market_code = item.get('MktNum', '')
                        
                        if code and name:
                            stocks.append({
                                'code': code,
                                'name': name,
                                'market_code': market_code,
                                'display': f"{code} {name}"
                            })
            
            return True, '获取成功', stocks
            
        except Exception as e:
            print(f"搜索股票异常: {str(e)}")
            import traceback
            traceback.print_exc()
            return False, str(e), None
    
    def get_stock_quote(self, stock_code: str, data_fetcher) -> Tuple[bool, str, Optional[Dict]]:
        """
        获取单只股票的实时行情
        
        Args:
            stock_code: 股票代码
            data_fetcher: 数据抓取器
            
        Returns:
            tuple: (success, message, data)
        """
        try:
            quote = data_fetcher.get_realtime_quote(stock_code)
            
            if quote:
                return True, '获取成功', quote
            else:
                return False, '未找到该股票', None
                
        except Exception as e:
            return False, str(e), None


import json
