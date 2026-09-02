# -*- coding: utf-8 -*-
"""断板强势股判定逻辑自测（stub 数据库与行情源）"""
import sys
import types
from datetime import date, timedelta
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, '.')

# stub：避免 app.core.__init__ 拉起 mootdx 等重依赖；chinese_calendar 同理（测试中会被 patch）
cc = types.ModuleType('chinese_calendar')
cc.is_workday = lambda *a, **k: True
cc.is_holiday = lambda *a, **k: False
sys.modules['chinese_calendar'] = cc
core_pkg = types.ModuleType('app.core')
core_pkg.__path__ = ['app/core']
sys.modules['app.core'] = core_pkg

from app.services.broken_board_service import BrokenBoardService


def rec(code, name, d, days, price):
    return SimpleNamespace(
        stock_code=code, stock_name=name, trade_date=d,
        continuous_days=days, limit_up_price=price, current_status='close',
    )


def fake_calendar_next(dt, max_days=31):
    # 简化：周一~周五为交易日
    d = dt
    for _ in range(max_days):
        d = d + timedelta(days=1)
        if d.weekday() < 5:
            return d
    return None


# 场景：选择日 D = 2026-08-28（周五）
# 股票A 600001：8/24(一)8/25(二)8/26(三) 3连板到10元，8/27断板收9.5，8/28收9.2 → 强（未破9.0）✅
# 股票B 600002：8/25~8/27 3连板到20元，8/28断板收17.5 → 破10%（18.0）❌
# 股票C 600003：8/26~8/28 3连板（未断板）→ 排除 ❌
# 股票D 600004：8/24~8/25 2连板 → 不足3板 ❌
D = date(2026, 8, 28)
records = [
    rec('600001', '股票A', date(2026, 8, 24), 1, 8.26),
    rec('600001', '股票A', date(2026, 8, 25), 2, 9.09),
    rec('600001', '股票A', date(2026, 8, 26), 3, 10.00),
    rec('600002', '股票B', date(2026, 8, 25), 1, 16.53),
    rec('600002', '股票B', date(2026, 8, 26), 2, 18.18),
    rec('600002', '股票B', date(2026, 8, 27), 3, 20.00),
    rec('600003', '股票C', date(2026, 8, 26), 1, 5.0),
    rec('600003', '股票C', date(2026, 8, 27), 2, 5.5),
    rec('600003', '股票C', date(2026, 8, 28), 3, 6.05),
    rec('600004', '股票D', date(2026, 8, 24), 1, 3.0),
    rec('600004', '股票D', date(2026, 8, 25), 2, 3.3),
]

prices = {
    ('sh600001', date(2026, 8, 26)): {'close': 10.00, 'low': 9.8},
    ('sh600001', date(2026, 8, 27)): {'close': 9.50, 'low': 9.4},
    ('sh600001', date(2026, 8, 28)): {'close': 9.20, 'low': 9.1},
    ('sh600002', date(2026, 8, 27)): {'close': 20.00, 'low': 19.5},
    ('sh600002', date(2026, 8, 28)): {'close': 17.50, 'low': 17.2},
    ('sh600003', date(2026, 8, 28)): {'close': 6.05, 'low': 6.0},
    ('sh600004', date(2026, 8, 25)): {'close': 3.3, 'low': 3.2},
}

svc = BrokenBoardService(data_fetcher=None)
with patch.object(svc, '_get_limit_up_records', return_value=records), \
     patch.object(svc, '_load_prices', return_value=(prices, 'fake')), \
     patch('app.services.broken_board_service.trade_calendar') as tc:
    tc.get_next_trading_day.side_effect = fake_calendar_next
    ok, msg, data = svc.get_strong_stocks('20260828')

assert ok, msg
items = data['items']
codes = [i['code'] for i in items]
print('入选股票:', codes)
for i in items:
    print(f"  {i['name']} {i['peak_days']}板 断板日{i['break_date']} 基准{i['base_price']} 最大回撤{i['max_drawdown_pct']}% 明细{i['details']}")

assert codes == ['600001'], f'应只入选股票A，实际: {codes}'
assert items[0]['peak_days'] == 3
assert items[0]['days_checked'] == 2
print('\n✅ 逻辑自测通过：强势股入选、破10%剔除、未断板剔除、不足3板剔除')
