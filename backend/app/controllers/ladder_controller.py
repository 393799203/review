#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re
import json
from app.core.fetch_data import LimitUpFetcher
from datetime import datetime, date
from flask import request
from app.controllers.base_controller import BaseController
from app.services.ladder_service import LadderService
from database import get_db_session
from models import Block, KeywordAnalysis, LimitUpStock


class LadderController(BaseController):
    """连板天梯控制器类"""
    
    def __init__(self, data_fetcher=None):
        super().__init__(LadderService())
        self.ladder_service = self.service
        self.data_fetcher = data_fetcher
    
    def get_available_dates(self):
        """获取所有可用日期"""
        try:
            dates = self.ladder_service.get_all_dates()
            from flask import jsonify
            return jsonify({
                'success': True,
                'data': dates
            })
        except Exception as e:
            return self.error(str(e), 500)
    
    def get_data_by_date(self, date_str: str):
        """获取指定日期的完整数据"""
        try:
            success, message, data = self.ladder_service.get_data_by_date(
                date_str, self.data_fetcher
            )
            
            if success:
                from flask import jsonify
                return jsonify({
                    'success': True,
                    'data': data,
                    'date': date_str
                })
            else:
                return self.error(message, 200)
                
        except Exception as e:
            return self.error(str(e), 400)
    
    def get_latest_date(self):
        """获取最近一个交易日"""
        try:
            from trade_calendar import trade_calendar
            
            trading_days = trade_calendar.get_recent_trading_days(1)
            
            if not trading_days:
                return self.error('无法获取交易日', 500)
            
            latest_date = trading_days[0]
            
            return self.success(latest_date)
            
        except Exception as e:
            return self.error(str(e), 500)
    
    def get_adjacent_trading_days(self, date_str: str):
        """获取指定日期前后一个月的交易日列表"""
        try:
            from trade_calendar import trade_calendar
            from datetime import timedelta
            
            target_date = datetime.strptime(date_str, '%Y%m%d').date()
            today = datetime.now().date()
            
            start_date = target_date - timedelta(days=31)
            end_date = min(target_date + timedelta(days=31), today)
            
            trading_days = trade_calendar.get_trading_days(start_date, end_date)
            
            prev_date = None
            next_date = None
            prev_days = []
            next_days = []
            
            current_idx = -1
            for i, d in enumerate(trading_days):
                if d == date_str:
                    current_idx = i
                    break
            
            if current_idx >= 0:
                if current_idx > 0:
                    prev_date = trading_days[current_idx - 1]
                    prev_days = trading_days[:current_idx]
                if current_idx < len(trading_days) - 1:
                    next_date = trading_days[current_idx + 1]
                    next_days = trading_days[current_idx + 1:]
            else:
                for i, d in enumerate(trading_days):
                    if d < date_str:
                        prev_days.append(d)
                    else:
                        next_days.append(d)
                
                if prev_days:
                    prev_date = prev_days[-1]
                if next_days:
                    next_date = next_days[0]
            
            is_trading_day = trade_calendar.is_trading_day(target_date)
            
            return self.success({
                'prev': prev_date,
                'next': next_date,
                'prev_days': prev_days,
                'next_days': next_days,
                'is_trading_day': is_trading_day
            })
            
        except Exception as e:
            return self.error(str(e), 500)
    
    def get_block_strength_by_date(self, date_str: str):
        """获取板块强度"""
        try:
            trade_date = datetime.strptime(date_str, '%Y%m%d').date()
            min_limit_up_num = int(self.get_query_param('min_limit_up_num', 1))
            
            blocks = self.ladder_service.get_block_strength_by_date(
                trade_date, min_limit_up_num
            )
            
            from flask import jsonify
            return jsonify({
                'success': True,
                'data': {
                    'date': date_str,
                    'blocks': blocks
                }
            })
            
        except Exception as e:
            return self.error(str(e), 400)
    
    def get_continuous_blocks(self):
        """获取连续板块"""
        try:
            date_str = self.get_query_param('date')
            
            from flask import jsonify
            from trade_calendar import trade_calendar
            
            session = get_db_session()
            
            try:
                if date_str:
                    try:
                        base_date = datetime.strptime(date_str, '%Y%m%d').date()
                    except ValueError:
                        return jsonify({
                            'success': False,
                            'error': '日期格式错误，请使用YYYYMMDD格式'
                        }), 400
                else:
                    latest_block = session.query(Block).order_by(Block.trade_date.desc()).first()
                    if not latest_block:
                        return jsonify({
                            'success': True,
                            'data': {}
                        })
                    base_date = latest_block.trade_date
                
                target_days = []
                
                yesterday = trade_calendar.get_prev_trading_day(base_date)
                if yesterday:
                    target_days.append(('yesterday', yesterday))
                
                target_days.append(('today', base_date))
                
                tomorrow = trade_calendar.get_next_trading_day(base_date)
                if tomorrow:
                    target_days.append(('tomorrow', tomorrow))
                
                result_data = {}
                
                for label, trade_date in target_days:
                    date_str = trade_date.strftime('%Y%m%d')
                    blocks = session.query(Block).filter(
                        Block.trade_date == trade_date
                    ).order_by(Block.limit_up_num.desc()).limit(20).all()
                    
                    block_list = []
                    for index, block in enumerate(blocks, 1):
                        import json as _json
                        try:
                            stock_codes = _json.loads(block.stock_codes) if block.stock_codes else []
                        except (ValueError, TypeError):
                            stock_codes = []
                        block_list.append({
                            'block_code': block.block_code,
                            'block_name': block.block_name,
                            'limit_up_num': block.limit_up_num,
                            'continuous_plate_num': block.continuous_plate_num,
                            'change_rate': float(block.change_rate) if block.change_rate else 0,
                            'high': block.high,
                            'high_num': block.high_num,
                            'rank': index,
                            'stock_codes': stock_codes,
                            'high_stock_code': block.high_stock_code,
                            'high_stock_name': block.high_stock_name,
                        })
                    
                    result_data[label] = {
                        'date': date_str,
                        'blocks': block_list
                    }
                
                return jsonify({
                    'success': True,
                    'data': result_data
                })
                
            finally:
                session.close()
            
        except Exception as e:
            return self.error(str(e), 500)
            
        except Exception as e:
            return self.error(str(e), 400)
    
    def update_stock_block(self):
        """更新股票板块"""
        try:
            data = self.get_json_data()
            stock_code = data.get('stock_code')
            trade_date_str = data.get('trade_date')
            block_name = data.get('block_name')
            block_id = data.get('block_id')
            
            if not all([stock_code, trade_date_str]) or (not block_name and not block_id):
                return self.error('缺少必要参数', 400)
            
            trade_date = datetime.strptime(trade_date_str, '%Y%m%d').date()
            
            success = self.ladder_service.update_stock_block(
                stock_code, trade_date, block_id, block_name
            )
            
            if success:
                return self.success(message='更新成功')
            else:
                return self.error('更新失败', 400)
                
        except Exception as e:
            return self.error(str(e), 400)
    
    def refresh_data(self, date_str: str):
        """刷新数据"""
        try:
            if not date_str:
                return self.error('日期参数不能为空', 400)
            
            # 验证日期格式
            try:
                from datetime import datetime
                datetime.strptime(date_str, '%Y%m%d')
            except ValueError:
                return self.error('日期格式错误，请使用 YYYYMMDD 格式', 400)
            
            if not self.data_fetcher:
                return self.error('数据抓取器未初始化', 500)

            fetcher: LimitUpFetcher = LimitUpFetcher(data_fetcher=self.data_fetcher)
            success = fetcher.fetch_and_save(date_str)
            
            if success:
                from flask import jsonify
                return jsonify({
                    'success': True,
                    'message': f'数据刷新成功：{date_str}',
                    'date': date_str
                })
            else:
                return self.error('数据刷新失败', 400)
                
        except Exception as e:
            return self.error(str(e), 500)
    
    def get_statistics_by_date(self, date_str: str):
        """获取指定日期的统计数据"""
        try:
            trade_date = datetime.strptime(date_str, '%Y%m%d').date()
            
            stats = self.ladder_service.get_statistics_by_date(trade_date)
            
            if stats:
                from flask import jsonify
                return jsonify({
                    'success': True,
                    'data': stats
                })
            else:
                return self.error('数据不存在', 404)
                
        except Exception as e:
            return self.error(str(e), 500)

    def analyze_keywords(self):
        """AI 处理涨停关键词"""
        try:
            data = self.get_json_data()
            date_str = data.get('date')
            keywords_data = data.get('keywords', [])
            force_refresh = data.get('force_refresh', False)

            if not date_str:
                return self.error('缺少日期参数', 400)

            trade_date = datetime.strptime(date_str, '%Y%m%d').date()

            # 如果已有缓存且不强制刷新，直接返回
            if not force_refresh:
                session = get_db_session()
                try:
                    existing = session.query(KeywordAnalysis).filter(
                        KeywordAnalysis.trade_date == trade_date
                    ).first()
                    if existing:
                        return self.success({
                            'raw_keywords': json.loads(existing.raw_keywords),
                            'merged_keywords': json.loads(existing.merged_keywords),
                            'analysis_text': existing.analysis_text,
                            'from_cache': True
                        })
                finally:
                    session.close()

            # 无缓存或强制刷新：调用 AI
            from core.llm_client import llm_client
            from core.trade_calendar import trade_calendar

            # 汇总今日及前两个交易日的涨停关键词，用于主线轮动分析
            def aggregate_keywords_by_date(day):
                session = get_db_session()
                try:
                    rows = session.query(LimitUpStock.limit_up_reason).filter(
                        LimitUpStock.trade_date == day,
                        LimitUpStock.current_status == 'close'
                    ).all()
                    stats = {}
                    for (reason,) in rows:
                        for kw in (reason or '').split('+'):
                            kw = kw.strip()
                            if kw:
                                stats[kw] = stats.get(kw, 0) + 1
                    return sorted(
                        [{'keyword': k, 'count': v} for k, v in stats.items()],
                        key=lambda x: -x['count']
                    )
                finally:
                    session.close()

            def format_keywords(items):
                if not items:
                    return '（无数据）'
                # 兼容两种输入：前端传入的字符串数组 ["人工智能","机器人"]
                # 或库内聚合的字典列表 [{"keyword":"人工智能","count":5}]
                lines = []
                for item in items:
                    if isinstance(item, dict):
                        kw = item.get('keyword') or ''
                        cnt = item.get('count', 1)
                        lines.append(f"- {kw}（出现{cnt}次）")
                    else:
                        lines.append(f"- {item}（出现1次）")
                return "\n".join(lines)

            # 近三个交易日（含当日，倒序：[当日, 前1日, 前2日]）
            recent_days = trade_calendar.get_recent_trading_days(3, end_date=trade_date)
            day_sections = []
            for i, day in enumerate(recent_days):
                label = '今日' if i == 0 else f'前{i}个交易日'
                # 当日关键词优先使用前端传入的（盘中可能未入库），其余从库里聚合
                if i == 0 and keywords_data:
                    day_keywords = keywords_data
                else:
                    day_date = datetime.strptime(day, '%Y%m%d').date()
                    day_keywords = aggregate_keywords_by_date(day_date)
                day_sections.append(f"【{label}（{day}）涨停关键词】\n{format_keywords(day_keywords)}")

            system_prompt = """你是一个A股涨停板主线题材分析专家，擅长从涨停数据识别市场主线和题材轮动。

我会提供【今日】及【前两个交易日】的涨停股票关键词及出现次数。

任务一：今日关键词语义归并
1. 将含义相近或属于同一大类的关键词合并（如"火电""电力""绿色电力"→统一为"电力"）
2. 归类后的名称应简洁、通用，能代表该类别的核心概念
3. 保留无法归类的重要独立关键词
4. 合并后的 count 为所有源关键词的 count 之和，按次数降序排列
5. 【重要】merged 只归并【今日】的关键词；前两日数据仅用于任务二的轮动对比，严禁混入 merged
6. 【重要】剔除过于宽泛、缺乏实质题材意义的泛概念关键词（如"华为概念""MSCI概念""融资融券""ST股"等），它们只说明股东或属性而非题材主线，不要进入 merged；若某泛概念确实为当日重要驱动，可在 analysis 中提及
7. 为每个归并后的关键词标注 trend 字段，对比前两日同题材关键词的出现次数（按语义匹配，如"电力"对比前两日的"火电""绿色电力"等），取值：
   - "增强"：今日次数显著多于前两日
   - "衰退"：前两日较多，今日明显减少
   - "新发"：前两日未出现，今日新出现
   - "平稳"：与前两日基本持平

任务二：主线轮动分析（重点，写入 analysis 字段）
结合最近三天的关键词及出现次数变化，分析：
1. 今日主线：今日最强的题材集群是什么
2. 持续性：哪些题材连续多日走强（真主线），哪些是今日新发酵，哪些正在退潮（次数逐日减少）
3. 轮动路径：资金在题材之间的切换方向
4. 只基于我提供的数据进行分析，不要编造数据

请以 JSON 格式返回结果，格式如下：
{
  "merged": [
    {"keyword": "电力", "count": 12, "source": ["火电", "电力", "绿色电力"], "trend": "增强"},
    ...
  ],
  "analysis": "主线轮动分析（Markdown格式，包含：今日主线、近三日题材持续/发酵/退潮判断、轮动路径）"
}"""

            user_prompt = f"""{chr(10).join(day_sections)}

请先完成任务一（今日关键词归并），再完成任务二（结合三天数据的主线轮动分析）。"""

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]

            result_text = llm_client._chat(messages, temperature=0.3, max_tokens=4096)

            # 解析 AI 返回的 JSON（括号配平提取，避免 analysis 文本中的花括号干扰）
            def extract_json(text):
                start = text.find('{')
                if start < 0:
                    return None
                depth = 0
                in_str = False
                escape = False
                for i in range(start, len(text)):
                    ch = text[i]
                    if in_str:
                        if escape:
                            escape = False
                        elif ch == '\\':
                            escape = True
                        elif ch == '"':
                            in_str = False
                        continue
                    if ch == '"':
                        in_str = True
                    elif ch == '{':
                        depth += 1
                    elif ch == '}':
                        depth -= 1
                        if depth == 0:
                            return text[start:i + 1]
                return None

            json_str = extract_json(result_text)
            if not json_str:
                return self.error('AI 返回格式解析失败', 500)

            try:
                result = json.loads(json_str)
            except json.JSONDecodeError as e:
                print(f"[ERROR] 关键词分析 JSON 解析失败: {e}, 原文: {result_text[:500]}")
                return self.error('AI 返回格式解析失败', 500)
            merged_keywords = result.get('merged', [])
            analysis_text = result.get('analysis', '')

            # 保存到数据库
            session = get_db_session()
            try:
                existing = session.query(KeywordAnalysis).filter(
                    KeywordAnalysis.trade_date == trade_date
                ).first()

                if existing:
                    existing.raw_keywords = json.dumps(keywords_data, ensure_ascii=False)
                    existing.merged_keywords = json.dumps(merged_keywords, ensure_ascii=False)
                    existing.analysis_text = analysis_text
                    existing.updated_at = datetime.now()
                else:
                    analysis_record = KeywordAnalysis(
                        trade_date=trade_date,
                        raw_keywords=json.dumps(keywords_data, ensure_ascii=False),
                        merged_keywords=json.dumps(merged_keywords, ensure_ascii=False),
                        analysis_text=analysis_text
                    )
                    session.add(analysis_record)
                session.commit()
            except Exception:
                session.rollback()
                raise
            finally:
                session.close()

            return self.success({
                'raw_keywords': keywords_data,
                'merged_keywords': merged_keywords,
                'analysis_text': analysis_text,
                'from_cache': False
            })

        except Exception as e:
            import traceback
            traceback.print_exc()
            return self.error(f'AI 分析失败: {str(e)}', 500)

    def get_keyword_analysis(self, date_str: str):
        """获取关键词 AI 分析缓存"""
        try:
            trade_date = datetime.strptime(date_str, '%Y%m%d').date()

            session = get_db_session()
            try:
                existing = session.query(KeywordAnalysis).filter(
                    KeywordAnalysis.trade_date == trade_date
                ).first()
                if existing:
                    return self.success({
                        'raw_keywords': json.loads(existing.raw_keywords),
                        'merged_keywords': json.loads(existing.merged_keywords),
                        'analysis_text': existing.analysis_text,
                        'from_cache': True
                    })
                return self.success(None)
            finally:
                session.close()
        except Exception as e:
            return self.error(str(e), 500)


ladder_controller = None

def init_ladder_controller(data_fetcher):
    """初始化连板天梯控制器"""
    global ladder_controller
    ladder_controller = LadderController(data_fetcher)
    return ladder_controller
