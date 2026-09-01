#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
每日自动筛选任务：每天 19:00 执行抄底放量策略，结果加入启用用户的自选股。

- 轻量线程循环（每 30 秒检查一次，精确到分钟触发，每天去重）
- 开关：auto_screening_config.enabled（用户级）
- 参数：auto_screening_config.params（JSON，前端保存的表单参数）
- 结果：加入各自选股（跳过已存在），写入 auto_screening_logs
"""

import json
import threading
import time
from datetime import date, datetime

RUN_HOUR = 19
RUN_MINUTE = 0
CHECK_INTERVAL = 30  # 秒

_done_dates = set()
_lock = threading.Lock()


def _save_log(session, user_id, run_date, added=0, skipped=0, error=None):
    from models import AutoScreeningLog
    session.add(AutoScreeningLog(
        user_id=user_id,
        run_date=run_date,
        added_count=added,
        skipped_count=skipped,
        error_message=error,
    ))
    session.commit()


def _run_for_user(cfg, session):
    """对单个启用用户执行：筛选 → 加入自选 → 记日志"""
    from app.services.screening_service import ScreeningService
    from app.services.watchlist_service import WatchlistService

    user_id = cfg.user_id
    run_date = date.today()

    params = {}
    try:
        params = json.loads(cfg.params) if cfg.params else {}
    except (ValueError, TypeError):
        params = {}
    params['date'] = run_date.strftime('%Y%m%d')
    params['strategy'] = cfg.strategy or 'bottom'

    ok, msg, data = ScreeningService().run_screening(params)
    if not ok or not data:
        _save_log(session, user_id, run_date, error=msg or '筛选无结果')
        return

    wsvc = WatchlistService()
    added = 0
    skipped = 0
    for row in data:
        code = str(row.get('code', ''))
        if not code:
            continue
        # 已在自选则跳过
        if wsvc.watchlist_repository.exists_in_watchlist(user_id, code):
            skipped += 1
            continue

        blocks = row.get('concept_blocks') or []
        category = '/'.join(
            b.get('block_name', '') for b in blocks[:3] if b.get('block_name')
        )
        # 预警价：放量日最低 × 1.02（与筛选页一致：bottom 用 signal_low）
        vol_day_low = row.get('signal_low')
        if vol_day_low is None:
            vol_day_low = row.get('low')
        alert_price = round(float(vol_day_low) * 1.02, 2) if vol_day_low else None

        signal_date = row.get('signal_date')
        if signal_date:
            try:
                from datetime import datetime as _dt
                signal_date = _dt.strptime(str(signal_date), '%Y-%m-%d').date()
            except Exception:
                signal_date = None

        try:
            success, message = wsvc.add_to_watchlist(
                user_id=user_id,
                stock_code=code,
                stock_name=row.get('name') or code,
                add_date=run_date,
                add_price=row.get('close'),
                add_reason='抄底放量',
                source='screening',
                add_type='strategy',
                limit_up_reason_category=category,
                alert_price=alert_price,
                signal_date=signal_date,
            )
            if success:
                added += 1
            else:
                skipped += 1
        except Exception:
            skipped += 1

    _save_log(session, user_id, run_date, added=added, skipped=skipped)
    print(f"🤖 自动筛选完成 user={user_id} 新增{added} 跳过{skipped}")


def _cleanup_expired():
    """清理超过 1 个月的策略筛选自选股（add_type='strategy'），手动添加的不受影响"""
    from datetime import timedelta
    from database import get_db_session
    from models import WatchlistStock

    cutoff = date.today() - timedelta(days=30)
    session = get_db_session()
    try:
        deleted = session.query(WatchlistStock).filter(
            WatchlistStock.add_type == 'strategy',
            WatchlistStock.add_date < cutoff,
        ).delete(synchronize_session=False)
        session.commit()
        if deleted:
            print(f"🧹 已清理超过 1 个月的策略自选股 {deleted} 条（截止 {cutoff}）")
    except Exception as e:
        print(f"✗ 清理过期策略自选股失败: {e}")
    finally:
        session.close()


def _execute_once():
    """19:00 窗口触发：先清理过期策略自选股，再对所有启用用户执行筛选"""
    from database import get_db_session
    from models import AutoScreeningConfig

    # 1. 清理超过 1 个月的策略筛选结果（独立于开关，始终执行）
    _cleanup_expired()

    # 2. 执行每日筛选
    session = get_db_session()
    try:
        configs = session.query(AutoScreeningConfig).filter(
            AutoScreeningConfig.enabled == 1
        ).all()
        if not configs:
            print("🤖 自动筛选：无启用用户")
            return
        for cfg in configs:
            try:
                _run_for_user(cfg, session)
            except Exception as e:
                print(f"✗ 自动筛选失败 user={cfg.user_id}: {e}")
                try:
                    _save_log(session, cfg.user_id, date.today(), error=str(e)[:500])
                except Exception:
                    pass
    finally:
        session.close()


def _check_loop():
    while True:
        try:
            now = datetime.now()
            with _lock:
                is_time = (now.hour == RUN_HOUR and now.minute == RUN_MINUTE
                           and now.date() not in _done_dates)
                if is_time:
                    _done_dates.add(now.date())
            if is_time:
                print(f"🤖 自动筛选任务触发：{now.strftime('%Y-%m-%d %H:%M:%S')}")
                _execute_once()
        except Exception as e:
            print(f"✗ 自动筛选调度异常: {e}")
        time.sleep(CHECK_INTERVAL)


def start_scheduler():
    """启动自动筛选定时线程（随 Flask 启动，daemon 线程）"""
    t = threading.Thread(target=_check_loop, name='auto-screening', daemon=True)
    t.start()
    print(f"🤖 每日自动筛选调度已启动（每天 {RUN_HOUR}:{RUN_MINUTE:02d}）")
