#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
断板强势股追踪服务

规则（以用户选择的日期 D 为准）：
1. 在 D 前 7 个自然日（含 D）内，找出出现过 3 连板及以上的股票（current_status='close'）
2. 取该股票在窗口内最后一次涨停日 T（连板高度 = T 日 continuous_days）
3. T 之后第一个交易日 n1 必须已发生（n1 <= D），且 n1 当天未再封板 → 视为断板
4. 断板当天(n1)和后一天(n2)（以 D 内已存在的交易日为准），每日收盘价
   不得跌破 T 日收盘价（基准价）的 90%，即累计回撤不超过 10%

价格数据来源：优先 TDX 行情库（quantdb, tdx.raw_stocks_daily），
未配置时回退到 mootdx 在线 K 线（data_fetcher.get_stock_kline）。
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from app.services.base_service import BaseService
from app.repositories.stock_repository import StockRepository
from app.core.trade_calendar import trade_calendar
from models import LimitUpStock


class BrokenBoardService(BaseService):
    """断板强势股追踪服务"""

    MIN_CONTINUOUS_DAYS = 3   # 至少 3 连板
    WINDOW_DAYS = 7           # 回看窗口（自然日）
    MAX_DROP_PCT = 10.0       # 断板后允许最大回撤（%）
    CACHE_TTL = 120           # 结果缓存秒数（同日期重复请求直接秒回）

    # 结果缓存：{date_str: (timestamp, result)}
    _result_cache: Dict[str, Tuple[float, Tuple[bool, str, Optional[Dict]]]] = {}

    def __init__(self, data_fetcher=None):
        super().__init__(StockRepository())
        self.stock_repository = self.repository
        self.data_fetcher = data_fetcher

    # ---------- 对外入口 ----------

    def get_strong_stocks(self, date_str: str) -> Tuple[bool, str, Optional[Dict]]:
        import time
        now = time.time()
        hit = self._result_cache.get(date_str)
        if hit and now - hit[0] < self.CACHE_TTL:
            return hit[1]

        result = self._compute_strong_stocks(date_str)
        # 成功且非空的结果才缓存（失败的/空的可由下次重算快速补上，
        # 但 18:03 同步后同一天会重算拿到新数据）
        if result[0] and result[2] and result[2].get('items'):
            self._result_cache[date_str] = (time.time(), result)
        return result

    def _compute_strong_stocks(self, date_str: str) -> Tuple[bool, str, Optional[Dict]]:
        try:
            trade_date = datetime.strptime(date_str, '%Y%m%d').date()
        except ValueError:
            return False, '日期格式错误，请使用 YYYYMMDD', None

        try:
            # 1. 窗口内涨停记录
            window_start = trade_date - timedelta(days=self.WINDOW_DAYS - 1)
            records = self._get_limit_up_records(window_start, trade_date)
            if not records:
                return True, '获取成功', {'date': date_str, 'items': [], 'source': 'none'}

            # 2. 筛选候选：窗口内出现过 >=3 连板
            by_stock: Dict[str, Dict] = {}
            for r in records:
                by_stock.setdefault(r.stock_code, {'name': r.stock_name, 'days': {}})
                by_stock[r.stock_code]['days'][r.trade_date] = r

            candidates = []
            for code, info in by_stock.items():
                days_map = info['days']
                peak_record = max(
                    (r for r in days_map.values() if (r.continuous_days or 0) >= self.MIN_CONTINUOUS_DAYS),
                    key=lambda r: r.trade_date,
                    default=None,
                )
                if not peak_record:
                    continue
                # T = 窗口内最后一次涨停日
                last_date = max(days_map.keys())
                last_record = days_map[last_date]
                candidates.append({
                    'code': code,
                    'name': info['name'],
                    'last_date': last_date,                 # T
                    'peak_days': last_record.continuous_days or 0,
                    'limit_up_price': float(last_record.limit_up_price) if last_record.limit_up_price else None,
                })

            if not candidates:
                return True, '获取成功', {'date': date_str, 'items': [], 'source': 'none'}

            # 3. 确认断板 + 收集需要检查的交易日
            checked = []
            for c in candidates:
                n1 = trade_calendar.get_next_trading_day(datetime.combine(c['last_date'], datetime.min.time()))
                if not n1:
                    continue
                n1_date = n1.date() if hasattr(n1, 'date') else n1
                if n1_date > trade_date:
                    continue  # 断板还没发生
                # n1 当天不能再有封板记录（若有则说明窗口内 T 取错，理论上不会发生）
                if n1_date in by_stock[c['code']]['days']:
                    continue

                check_dates = [n1_date]
                # 观察断板日之后到所选日期 D 的每一个交易日（不只 n1/n2 两天），
                # 这样 D 日内后续交易日（如跌停）也会计入回撤统计
                n_iter = n1
                while True:
                    nxt = trade_calendar.get_next_trading_day(n_iter)
                    if not nxt:
                        break
                    nxt_date = nxt.date() if hasattr(nxt, 'date') else nxt
                    if nxt_date > trade_date:
                        break
                    check_dates.append(nxt_date)
                    n_iter = nxt

                c['break_date'] = n1_date
                c['check_dates'] = check_dates
                checked.append(c)

            if not checked:
                return True, '获取成功', {'date': date_str, 'items': [], 'source': 'none'}

            # 4. 获取价格（含 T 日基准价 + 断板后检查日）
            price_map, source = self._load_prices(checked, trade_date)

            # 5. 按规则判定
            items = []
            for c in checked:
                symbol = self._to_tdx_symbol(c['code'])
                base_price = None
                t_prices = price_map.get((symbol, c['last_date']))
                if t_prices and t_prices.get('close'):
                    base_price = t_prices['close']
                elif c['limit_up_price']:
                    base_price = c['limit_up_price']
                if not base_price:
                    continue

                threshold = base_price * (1 - self.MAX_DROP_PCT / 100)
                details = []
                ok = True
                for d in c['check_dates']:
                    p = price_map.get((symbol, d))
                    if not p or not p.get('close'):
                        ok = False
                        break
                    pct = (p['close'] - base_price) / base_price * 100
                    details.append({
                        'date': d.strftime('%Y-%m-%d'),
                        'close': round(p['close'], 2),
                        'pct': round(pct, 2),
                    })
                    if p['close'] < threshold:
                        ok = False
                        break

                if not ok or not details:
                    continue

                worst = min(d['pct'] for d in details)
                items.append({
                    'code': c['code'],
                    'name': c['name'],
                    'peak_days': c['peak_days'],
                    'last_limit_date': c['last_date'].strftime('%Y-%m-%d'),
                    'break_date': c['break_date'].strftime('%Y-%m-%d'),
                    'base_price': round(base_price, 2),
                    'days_checked': len(details),
                    'max_drawdown_pct': round(worst, 2),
                    'details': details,
                })

            # 按连板数从高到低降序；同板数时新断板的在前
            items.sort(key=lambda x: (x['peak_days'], x['break_date']), reverse=True)
            return True, '获取成功', {'date': date_str, 'items': items, 'source': source}

        except Exception as e:
            print(f"获取断板强势股失败: {e}")
            return False, str(e), None

    # ---------- 内部方法 ----------

    def _get_limit_up_records(self, start_date, end_date) -> List[LimitUpStock]:
        """窗口内所有封板（close）涨停记录"""
        session = self.stock_repository.create_session()
        try:
            return session.query(LimitUpStock).filter(
                LimitUpStock.trade_date >= start_date,
                LimitUpStock.trade_date <= end_date,
                LimitUpStock.current_status == 'close',
            ).all()
        finally:
            session.close()

    @staticmethod
    def _to_tdx_symbol(code: str) -> str:
        """600519 -> sh600519; 000001/300750 -> sz...; 8xxxxx/4xxxxx/920xxx -> bj..."""
        code = code.strip()
        if code.startswith('6'):
            return 'sh' + code
        if code[0] in ('0', '2', '3'):
            return 'sz' + code
        return 'bj' + code

    def _load_prices(self, candidates: List[Dict], end_date) -> Tuple[Dict, str]:
        """
        加载价格：{(symbol, date): {'close': x, 'low': y}}
        返回 (price_map, source)；source ∈ {'tdx', 'mootdx', 'none'}
        """
        need_dates = set()
        symbols = {}
        min_date = end_date
        for c in candidates:
            symbol = self._to_tdx_symbol(c['code'])
            symbols[c['code']] = symbol
            need_dates.add(c['last_date'])
            need_dates.update(c['check_dates'])
            if c['last_date'] < min_date:
                min_date = c['last_date']

        # 优先 TDX 行情库
        try:
            from app.core.tdx_db import get_tdx_engine
            engine = get_tdx_engine()
        except Exception:
            engine = None

        if engine is not None:
            try:
                from sqlalchemy import text, bindparam
                stmt = text(
                    "SELECT symbol, date, close, low FROM tdx.raw_stocks_daily "
                    "WHERE symbol IN :symbols AND date >= :start AND date <= :end"
                ).bindparams(bindparam('symbols', expanding=True))
                with engine.connect() as conn:
                    rows = conn.execute(stmt, {
                        'symbols': list(set(symbols.values())),
                        'start': min_date,
                        'end': end_date,
                    }).fetchall()
                price_map = {}
                for symbol, d, close, low in rows:
                    price_map[(symbol, d)] = {
                        'close': float(close) if close else None,
                        'low': float(low) if low else None,
                    }
                if not price_map:
                    raise ValueError('quantdb 无数据')

                # 关键：盘中 quantdb 通常缺"当天"（收盘后才同步）。检查断板校验
                # 所需的 check_dates 是否齐全；有缺的则用 mootdx 实时 K 线补充，
                # 避免因缺当日价格把当天断板/昨断板的股票整批剔除。
                missing_codes = set()
                tdx_has_check_date = False  # quantdb 是否已覆盖部分断板观察日
                for c in candidates:
                    symbol = symbols[c['code']]
                    for d in c['check_dates']:
                        p = price_map.get((symbol, d))
                        if p and p.get('close'):
                            tdx_has_check_date = True
                        else:
                            missing_codes.add(c['code'])

                # 仅当 quantdb 已覆盖部分观察日（即数据基本同步、只缺个别天，
                # 如盘中缺当天）时才做 mootdx 补充；quantdb 整体缺当日（如
                # 行情未同步）时盲补无意义且可能在通达信异常环境下拖慢接口。
                if missing_codes and self.data_fetcher is not None and tdx_has_check_date:
                    filled = 0
                    fail_streak = 0
                    for code in missing_codes:
                        try:
                            kline = self.data_fetcher.get_stock_kline(code, days=40)
                        except Exception as e:
                            print(f"mootdx 补充 {code} 价格失败: {e}")
                            fail_streak += 1
                            if fail_streak >= 3:
                                break  # 连续失败：环境不健康，整体放弃
                            continue
                        if not kline:
                            fail_streak += 1
                            if fail_streak >= 3:
                                break
                            continue
                        fail_streak = 0
                        symbol = symbols[code]
                        for bar in kline:
                            d = str(bar.get('date', ''))[:10]
                            try:
                                dt = datetime.strptime(d, '%Y-%m-%d').date()
                            except ValueError:
                                continue
                            if dt in need_dates:
                                price_map[(symbol, dt)] = {
                                    'close': float(bar.get('close')) if bar.get('close') else None,
                                    'low': float(bar.get('low')) if bar.get('low') else None,
                                }
                                filled += 1
                    if filled:
                        print(f"✓ mootdx 补充盘中价格 {filled} 条（quantdb 缺当日数据）")

                return price_map, 'tdx'
            except Exception as e:
                print(f"TDX 行情库查询失败，回退 mootdx: {e}")

        # 回退：mootdx 在线 K 线
        if self.data_fetcher is None:
            return {}, 'none'

        price_map = {}
        need_str = {d.strftime('%Y-%m-%d') for d in need_dates}
        for c in candidates:
            code = c['code']
            symbol = symbols[code]
            try:
                kline = self.data_fetcher.get_stock_kline(code, days=30)
            except Exception as e:
                print(f"获取 {code} K线失败: {e}")
                continue
            if not kline:
                continue
            for bar in kline:
                d = str(bar.get('date', ''))[:10]
                if d in need_str:
                    try:
                        dt = datetime.strptime(d, '%Y-%m-%d').date()
                    except ValueError:
                        continue
                    price_map[(symbol, dt)] = {
                        'close': float(bar['close']) if bar.get('close') else None,
                        'low': float(bar['low']) if bar.get('low') else None,
                    }
        return price_map, 'mootdx' if price_map else 'none'
