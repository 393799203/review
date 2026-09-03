#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Optional, Dict, Tuple
from datetime import datetime, date
import json
from app.services.base_service import BaseService
from app.repositories.ai_repository import AIRepository
from app.core.limit_up_analyzer import LimitUpReasonAnalyzer
from app.core.data_fetcher import DataFetcher


class AIService(BaseService):
    """AI分析服务类"""
    
    def __init__(self):
        super().__init__(AIRepository())
        self.ai_repository = self.repository
        self.analyzer = LimitUpReasonAnalyzer()
        self.data_fetcher = DataFetcher()
    
    def analyze_limit_up_stock(self, stock_code: str, force: bool = False,
                               date_str: str = None, check_only: bool = False) -> Tuple[bool, str, Optional[Dict]]:
        """
        分析涨停股票
        
        Args:
            stock_code: 股票代码
            force: 是否强制重新分析
            date_str: 指定日期
            check_only: 是否只检查缓存
            
        Returns:
            tuple: (success, message, data)
        """
        try:
            trade_date = None
            if date_str:
                try:
                    trade_date = datetime.strptime(date_str, '%Y%m%d').date()
                except:
                    return False, '日期格式错误,应为YYYYMMDD格式', None
            
            stock = self.ai_repository.get_limit_up_stock_by_code(stock_code, trade_date)
            
            if not stock:
                return False, '未找到该股票的涨停记录', None
            
            stock_data = {
                'stock_code': stock.stock_code,
                'stock_name': stock.stock_name,
                'trade_date': stock.trade_date,
                'limit_up_reason': stock.limit_up_reason,
                'limit_up_price': stock.limit_up_price,
                'continuous_days': stock.continuous_days,
                'limit_up_time': stock.limit_up_time,
                'seal_amount': stock.seal_amount,
                'turnover_rate': stock.turnover_rate
            }
            
            cached_result = self.ai_repository.get_ai_analysis_cache(
                stock_code, stock_data['trade_date']
            )
            
            if check_only:
                if cached_result:
                    analysis = json.loads(cached_result.analysis_result)
                    result = self._format_analysis_result(stock_data, analysis, True)
                    result['has_cache'] = True
                    return True, '有缓存', result
                else:
                    return True, '无缓存', {'has_cache': False}
            
            if cached_result and not force:
                analysis = json.loads(cached_result.analysis_result)
                return True, '获取成功', self._format_analysis_result(stock_data, analysis, True)
            
            analysis = self.analyzer.analyze_with_llm(
                stock_data['limit_up_reason'],
                stock_data['stock_code'],
                stock_data['stock_name'],
                stock_data['limit_up_price'],
                stock_data['continuous_days'],
                stock_data['limit_up_time'],
                stock_data['seal_amount'],
                stock_data['turnover_rate']
            )
            
            if analysis and analysis.get('recommendation_score', 0) > 0:
                self.ai_repository.save_ai_analysis(
                    stock_data['stock_code'],
                    stock_data['stock_name'],
                    stock_data['trade_date'],
                    analysis
                )
            
            return True, '分析成功', self._format_analysis_result(stock_data, analysis, False)
            
        except Exception as e:
            return False, str(e), None
    
    def analyze_news(self, news_id: str, title: str, content: str,
                    force: bool = False) -> Tuple[bool, str, Optional[Dict]]:
        """
        分析新闻
        
        Args:
            news_id: 新闻ID
            title: 新闻标题
            content: 新闻内容
            force: 是否强制重新分析
            
        Returns:
            tuple: (success, message, data)
        """
        try:
            if not title and not content:
                return False, '缺少标题和内容', None
            
            full_text = f"{title} {content}"
            
            if not force:
                news_record = self.ai_repository.get_news_by_id(news_id)
                if news_record and news_record.analysis_result:
                    try:
                        analysis_data = json.loads(news_record.analysis_result)
                        return True, '获取成功', {'data': analysis_data, 'cached': True}
                    except:
                        pass
            
            analysis_result = self.analyzer.analyze_news_impact(full_text)
            
            self.ai_repository.update_news_analysis(news_id, analysis_result)
            
            return True, '分析成功', {'data': analysis_result, 'cached': False}
            
        except Exception as e:
            return False, str(e), None
    
    def analyze_watchlist_stock(self, stock_code: str, stock_name: str,
                                force: bool = False, check_only: bool = False) -> Tuple[bool, str, Optional[Dict]]:
        """
        分析自选股
        
        Args:
            stock_code: 股票代码
            stock_name: 股票名称
            force: 是否强制重新分析
            check_only: 是否只检查缓存
            
        Returns:
            tuple: (success, message, data)
        """
        try:
            today = date.today()
            
            existing = self.ai_repository.get_watchlist_analysis_cache(stock_code, today)
            
            if check_only:
                if existing:
                    try:
                        analysis_data = json.loads(existing.analysis_result)
                        return True, '有缓存', {
                            'has_cache': True,
                            'data': analysis_data,
                            'cached': True,
                            'stock_name': stock_name or existing.stock_name or ''
                        }
                    except:
                        pass
                return True, '检查完成', {'has_cache': False}
            
            if existing and not force:
                try:
                    analysis_data = json.loads(existing.analysis_result)
                    return True, '获取成功', {
                        'has_cache': True,
                        'data': analysis_data,
                        'cached': True,
                        'stock_name': stock_name or existing.stock_name or ''
                    }
                except:
                    pass
            
            quote_data = self.data_fetcher.get_realtime_quote(stock_code)
            
            print(f"获取到的行情数据: {quote_data}")
            
            # 如果没有传入stock_name，尝试从行情数据中获取
            if not stock_name and quote_data and quote_data.get('name'):
                stock_name = quote_data.get('name')
                print(f"从行情数据获取到名称: {stock_name}")
            
            stock_status = self._build_stock_status(quote_data)
            
            print(f"构建的股票状态: {stock_status}")
            
            analysis_result = self.analyzer.analyze_with_llm(
                limit_up_reason=f"自选股投资分析：{stock_name}{stock_status}",
                stock_code=stock_code,
                stock_name=stock_name,
                limit_up_price=quote_data.get('price') if quote_data else None,
                continuous_days=None,
                limit_up_time=None,
                seal_amount=None,
                turnover_rate=quote_data.get('turnover') if quote_data else None
            )
            
            self.ai_repository.save_watchlist_analysis(
                stock_code, stock_name, today, analysis_result
            )
            
            return True, '分析成功', {
                'data': analysis_result,
                'cached': False,
                'stock_name': stock_name or ''
            }
            
        except Exception as e:
            return False, str(e), None
    
    def analyze_report(self, info_code: str, title: str, stock_name: str = '',
                      stock_code: str = '', rating: str = '', rating_change: str = '',
                      predict_eps: dict = None, predict_pe: dict = None,
                      force: bool = False) -> Tuple[bool, str, Optional[Dict]]:
        """
        分析研报
        
        Args:
            info_code: 研报ID
            title: 研报标题
            stock_name: 股票名称
            stock_code: 股票代码
            rating: 评级
            rating_change: 评级变化
            predict_eps: EPS预测
            predict_pe: PE预测
            force: 是否强制重新分析
            
        Returns:
            tuple: (success, message, data)
        """
        try:
            if not info_code:
                return False, '缺少研报ID', None
            
            if not title:
                return False, '缺少研报标题', None
            
            if not force:
                existing = self.ai_repository.get_report_analysis_cache(info_code)
                if existing:
                    try:
                        analysis_data = json.loads(existing.analysis_result)
                        return True, '获取成功', {'data': analysis_data, 'cached': True}
                    except:
                        pass
            
            prompt = self._build_report_prompt(
                title, stock_name, stock_code, rating, rating_change,
                predict_eps, predict_pe
            )
            
            analysis_result = self.analyzer.analyze_news_impact(prompt)
            
            self.ai_repository.save_report_analysis(
                info_code, stock_code, stock_name, title,
                rating, rating_change, date.today(), analysis_result
            )
            
            return True, '分析成功', {'data': analysis_result, 'cached': False}
            
        except Exception as e:
            return False, str(e), None
    
    def _format_analysis_result(self, stock_data: dict, analysis: dict, cached: bool) -> dict:
        """格式化分析结果"""
        return {
            'stock_code': stock_data['stock_code'],
            'stock_name': stock_data['stock_name'],
            'trade_date': stock_data['trade_date'].strftime('%Y-%m-%d'),
            'limit_up_reason': stock_data['limit_up_reason'],
            'continuous_days': stock_data['continuous_days'],
            'sectors': analysis.get('sectors', []),
            'speculation_logic': analysis.get('speculation_logic', []),
            'stock_attribute': analysis.get('stock_attribute', None),
            'market_heat': analysis.get('market_heat', 0),
            'recommendation_score': analysis.get('recommendation_score', 0),
            'recommendation_reason': analysis.get('recommendation_reason', ''),
            'analysis_summary': analysis.get('analysis_summary', ''),
            'keywords': analysis.get('keywords', []),
            'trading_advice': analysis.get('trading_advice', None),
            'holding_advice': analysis.get('holding_advice', None),
            'cached': cached
        }
    
    def _build_stock_status(self, quote_data: dict) -> str:
        """构建股票状态信息"""
        if not quote_data:
            return "无行情数据"
        
        price = quote_data.get('price', 0)
        open_price = quote_data.get('open', 0)
        high = quote_data.get('high', 0)
        low = quote_data.get('low', 0)
        change_percent = quote_data.get('change_percent', 0)
        volume = quote_data.get('volume', 0)
        amount = quote_data.get('amount', 0)
        turnover = quote_data.get('turnover')
        prev_close = quote_data.get('prev_close', 0)
        
        status_parts = []
        
        status_parts.append(f"现价{price:.2f}元")
        
        if change_percent > 0:
            status_parts.append(f"涨幅{change_percent:.2f}%")
        elif change_percent < 0:
            status_parts.append(f"跌幅{abs(change_percent):.2f}%")
        else:
            status_parts.append("平盘")
        
        if prev_close:
            status_parts.append(f"昨收{prev_close:.2f}元")
        if open_price:
            status_parts.append(f"今开{open_price:.2f}元")
        if high and low:
            status_parts.append(f"最高{high:.2f}元")
            status_parts.append(f"最低{low:.2f}元")
        if volume:
            status_parts.append(f"成交量{(volume/10000):.0f}万手")
        if amount:
            status_parts.append(f"成交额{(amount/100000000):.2f}亿")
        if turnover:
            status_parts.append(f"换手率{turnover:.2f}%")
        
        return ', '.join(status_parts)
    
    def _build_report_prompt(self, title: str, stock_name: str, stock_code: str,
                            rating: str, rating_change: str,
                            predict_eps: dict, predict_pe: dict) -> str:
        """构建研报分析提示"""
        eps_info = ""
        if predict_eps:
            eps_info = f"EPS预测:今年{predict_eps.get('this_year', '--')},明年{predict_eps.get('next_year', '--')},后年{predict_eps.get('next_two_year', '--')}"
        
        pe_info = ""
        if predict_pe:
            pe_info = f"PE预测:今年{predict_pe.get('this_year', '--')},明年{predict_pe.get('next_year', '--')},后年{predict_pe.get('next_two_year', '--')}"
        
        return f"""分析以下研报对股票的影响:

研报标题:{title}
股票名称:{stock_name}
股票代码:{stock_code}
机构评级:{rating or '无'}
评级变化:{rating_change or '无'}
{eps_info}
{pe_info}

返回JSON:
{{"analysis":"研报核心观点(100字内)","related_sectors":[{{"name":"相关板块","relevance":0.9}}],"related_stocks":[{{"code":"代码","name":"名称","reason":"原因"}}],"market_impact":"对股价的潜在影响(利好/利空/中性)","investment_suggestion":"投资建议和风险提示"}}

要求:最多3个板块,5只个股,直接返回JSON。"""
    
    def analyze_hot_topic(self, topic_title: str, themes: list, 
                         investment_direction: str = '',
                         force: bool = False) -> Tuple[bool, str, Optional[Dict]]:
        """
        分析热门话题
        
        Args:
            topic_title: 话题标题
            themes: 相关主题列表
            investment_direction: 投资方向
            force: 是否强制重新分析
            
        Returns:
            tuple: (success, message, data)
        """
        try:
            if not topic_title:
                return False, '缺少话题标题', None
            
            cached_result = self.ai_repository.get_hot_topic_analysis_cache(topic_title)
            if cached_result:
                try:
                    analysis_data = json.loads(cached_result.analysis_result)
                    return True, '获取成功', {'data': analysis_data, 'cached': True}
                except:
                    pass
            
            if not force:
                return True, '无缓存', {'data': None, 'cached': False}
            
            themes_str = '、'.join(themes) if themes else ''
            full_text = f"话题：{topic_title}"
            if themes_str:
                full_text += f"\n相关主题：{themes_str}"
            if investment_direction:
                full_text += f"\n投资方向：{investment_direction}"
            
            analysis_result = self.analyzer.analyze_news_impact(full_text)
            
            self.ai_repository.save_hot_topic_analysis(topic_title, analysis_result)
            
            return True, '分析成功', {'data': analysis_result, 'cached': False}
            
        except Exception as e:
            return False, str(e), None
    
    def comfort_stock(self, stock_code: str, stock_name: str, buy_price: float,
                     current_price: float, position_profit: float,
                     position_profit_ratio: float) -> Tuple[bool, str, Optional[Dict]]:
        """
        AI安慰分析持仓股票
        
        Args:
            stock_code: 股票代码
            stock_name: 股票名称
            buy_price: 买入价格
            current_price: 当前价格
            position_profit: 持仓盈亏
            position_profit_ratio: 持仓盈亏比例
            
        Returns:
            tuple: (success, message, data)
        """
        try:
            if not stock_code:
                return False, '缺少股票代码', None
            
            profit_status = ""
            if position_profit_ratio > 0:
                profit_status = f"盈利{position_profit:.2f}元（+{(position_profit_ratio * 100):.2f}%）"
            elif position_profit_ratio < 0:
                profit_status = f"亏损{abs(position_profit):.2f}元（{(position_profit_ratio * 100):.2f}%）"
            else:
                profit_status = "持平"
            
            prompt = f"""你是一位温暖专业的投资顾问,需要安慰和分析投资者的持仓。

股票: {stock_name}({stock_code})
买入价: {buy_price:.2f}元
现价: {current_price:.2f}元
持仓: {profit_status}

请返回JSON格式分析:
{{
  "emotion_comfort": "情感安慰(温暖话语,50-80字)",
  "rational_analysis": "理性分析(客观判断,50-80字)",
  "operation_advice": "操作建议(具体可行,30-50字)",
  "risk_warning": "风险提示(30-50字)",
  "future_outlook": "未来展望(客观判断,30-50字)",
  "overall_suggestion": "总体建议(持有/加仓/减仓/止损)"
}}

语气要温暖专业,避免过度乐观或悲观。只返回JSON,不要其他内容。"""
            
            import requests
            import os
            
            api_key = os.environ.get('DEEPSEEK_API_KEY')
            if not api_key:
                return False, '未配置DEEPSEEK_API_KEY环境变量', None
            
            api_url = os.environ.get('DEEPSEEK_API_URL', 'https://api.deepseek.com/v1/chat/completions')
            model = os.environ.get('DEEPSEEK_MODEL', 'deepseek-chat')
            temperature = float(os.environ.get('DEEPSEEK_TEMPERATURE', '0.7'))
            max_tokens = int(os.environ.get('DEEPSEEK_MAX_TOKENS_SHORT', '500'))
            
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": model,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": temperature,
                "max_tokens": max_tokens
            }
            
            response = requests.post(api_url, headers=headers, json=payload, timeout=60)
            
            if response.status_code == 200:
                result = response.json()
                content = result.get('choices', [{}])[0].get('message', {}).get('content', '')
                
                if content:
                    try:
                        analysis_data = json.loads(content)
                        return True, '分析成功', {'analysis': analysis_data}
                    except json.JSONDecodeError:
                        return True, '分析成功', {
                            'analysis': {
                                'emotion_comfort': content,
                                'rational_analysis': '',
                                'operation_advice': '',
                                'risk_warning': '',
                                'future_outlook': '',
                                'overall_suggestion': ''
                            }
                        }
                else:
                    return False, 'AI返回内容为空', None
            else:
                return False, f'AI请求失败: {response.status_code}', None
                
        except Exception as e:
            return False, str(e), None
    
    def call_llm_analysis(self, prompt: str) -> Tuple[bool, str, str]:
        """
        调用LLM进行分析（通用方法）
        
        Args:
            prompt: 分析提示词
            
        Returns:
            tuple: (success, message, result)
        """
        try:
            import requests
            import os
            
            api_key = os.environ.get('DEEPSEEK_API_KEY')
            if not api_key:
                return False, '未配置DEEPSEEK_API_KEY环境变量', ''
            
            api_url = os.environ.get('DEEPSEEK_API_URL', 'https://api.deepseek.com/v1/chat/completions')
            model = os.environ.get('DEEPSEEK_MODEL', 'deepseek-chat')
            temperature = float(os.environ.get('DEEPSEEK_TEMPERATURE', '0.7'))
            max_tokens = int(os.environ.get('DEEPSEEK_MAX_TOKENS_LONG', '4000'))
            
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": model,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": temperature,
                "max_tokens": max_tokens
            }
            
            response = requests.post(api_url, headers=headers, json=payload, timeout=60)
            
            if response.status_code == 200:
                result = response.json()
                content = result.get('choices', [{}])[0].get('message', {}).get('content', '')
                
                if content:
                    return True, '分析成功', content
                else:
                    return False, 'AI返回内容为空', ''
            else:
                return False, f'AI请求失败: {response.status_code}', ''
                
        except Exception as e:
            return False, str(e), ''
    
    def analyze_comparable_stock(self, stock_code: str, stock_name: str, 
                                block: str, limit_up_reason: str,
                                date_str: str, strategy: str) -> Tuple[bool, str, Optional[Dict]]:
        """
        找对标分析
        
        Args:
            stock_code: 股票代码
            stock_name: 股票名称
            block: 所属板块
            limit_up_reason: 涨停原因
            date_str: 日期
            strategy: 用户输入的策略条件
            
        Returns:
            tuple: (success, message, data)
        """
        try:
            if not stock_code or not strategy:
                return False, '缺少必要参数', None
            
            # 处理策略模板变量
            processed_strategy = self._process_strategy_template(
                strategy, stock_code, stock_name, block, date_str
            )

            # 抓取同花顺真实涨停热点数据（目标日期+前2个交易日），防止AI编造数据
            hot_data = {}
            if date_str:
                try:
                    from app.core.hotspot_fetcher import HotspotFetcher
                    fetcher = HotspotFetcher()
                    window_dates = [date_str] + fetcher.get_trading_days_before(date_str, 2)
                    hot_data = fetcher.get_multi_day_hot_data(window_dates)
                except Exception as e:
                    print(f"[WARNING] 获取热点数据失败，将不提供数据grounding: {e}")

            # 构建提示词
            prompt = self._build_comparable_prompt(
                stock_code, stock_name, block, limit_up_reason, date_str, processed_strategy, hot_data
            )
            
            # 调用LLM分析
            success, message, result = self.call_llm_analysis(prompt)
            
            if success:
                # Service层只返回原始AI结果,由Controller层负责解析
                return True, '分析成功', {
                    'raw_analysis': result,
                    'processed_strategy': processed_strategy
                }
            else:
                return False, message, None
                
        except Exception as e:
            return False, str(e), None
    
    def _process_strategy_template(self, strategy: str, stock_code: str, 
                                   stock_name: str, block: str, date_str: str) -> str:
        """
        处理策略模板中的变量替换
        
        Args:
            strategy: 策略模板
            stock_code: 股票代码
            stock_name: 股票名称
            block: 所属板块
            date_str: 日期
            
        Returns:
            处理后的策略
        """
        processed = strategy
        processed = processed.replace('{date}', date_str or '')
        processed = processed.replace('{code}', stock_code or '')
        processed = processed.replace('{name}', stock_name or '')
        processed = processed.replace('{block}', block or '')
        return processed
    
    def _build_comparable_prompt(self, stock_code: str, stock_name: str,
                                block: str, limit_up_reason: str,
                                date_str: str, processed_strategy: str,
                                hot_data: dict = None) -> str:
        """
        构建找对标分析的提示词

        Args:
            stock_code: 股票代码
            stock_name: 股票名称
            block: 所属板块
            limit_up_reason: 涨停原因
            date_str: 日期
            processed_strategy: 处理后的策略
            hot_data: 同花顺真实涨停热点数据 {date: [rows]}，用于防止AI编造

        Returns:
            构建好的提示词
        """
        # 添加涨停原因信息
        reason_info = ""
        if limit_up_reason:
            reason_info = f"- 涨停原因：{limit_up_reason}"

        # 热点数据段（截断保护，只保留最近几个交易日、每天最多200条）
        hot_data_section = ""
        grounding_rules = ""
        if hot_data:
            import json as _json
            data_to_use = hot_data
            hot_data_str = _json.dumps(data_to_use, ensure_ascii=False, indent=2)
            if len(hot_data_str) > 80000:
                truncated = {}
                for d in list(hot_data.keys())[:3]:
                    truncated[d] = hot_data[d][:200]
                hot_data_str = _json.dumps(truncated, ensure_ascii=False, indent=2)
                hot_data_str += "\n\n(数据已截断，只保留最近几个交易日)"

            hot_data_section = """
## 同花顺真实涨停数据（最近几个交易日）
数据中包含涨停股票的代码、名称、涨幅、题材标签(reason)等信息：

```json
""" + hot_data_str + """
```
"""
            grounding_rules = """0. 【最重要】推荐的对标股票必须来自上面提供的真实涨停数据，只使用我提供的数据，绝对不要编造任何股票或数据
1. 如果提供的数据中没有找到符合条件的对标股票，如实说明，不要虚构
"""
        else:
            grounding_rules = """0. 确保推荐股票真实存在（不要虚构股票）
"""

        prompt = """你是一位资深的A股股票分析师，擅长对标分析和股票推荐。请根据以下信息，找出与目标股票对标相似的股票，并进行多维度深度分析。

## 目标股票基本信息
- 股票名称：""" + stock_name + """
- 股票代码：""" + stock_code + """
- 所属板块：""" + block + """
""" + reason_info + """
- 涨停日期：""" + date_str + """

## 用户对标需求
""" + processed_strategy + """
""" + hot_data_section + """
## 分析要求

请按照以下框架进行全面对标分析，并返回结构化的JSON数据：

### 1. 对标股票筛选（至少推荐3-5只）
列出符合对标条件的股票，每只股票需包含：
- **股票代码/股票名称**：清晰标注
- **涨停日期**：具体涨停日期
- **细分标签**：如"连板股"、"首板股"、"突破板"等
- **题材标签**：主要题材概念（2-3个）

### 2. 多维度对标分析（每只对标股票）
对每只对标股票从以下维度与目标股票对比：

#### A. 基础面对比
- 市值对比：流通市值、总市值是否相近
- 估值对比：PE/PB估值水平是否相似
- 价格对比：股价位置、涨幅情况

#### B. 涨停特征对比
- 涨停时间：是否相近时段涨停（早盘/午盘/尾盘）
- 连板天数：是否相同连板级别（首板/2板/3板等）
- 封单强度：封单金额、封单占比
- 换手率：涨停当天换手率对比

#### C. 板块题材对比
- 板块归属：是否同板块或关联板块
- 题材相似度：题材概念重叠度分析
- 板块地位：板块内地位（龙头/跟风/补涨）

#### D. 历史表现对比
- 近期涨停：近期涨停次数对比
- 连板能力：历史连板表现对比
- 区间涨幅：近1月/近1年涨幅对比

#### E. 技术形态对比
- 成交量形态：量价关系是否相似
- 筹码分布：筹码集中度、套牢盘情况
- 均线形态：均线支撑/压力位
- 技术指标：MACD、KDJ等指标状态

### 3. 对标匹配度评分
为每只对标股票评分（满分10分）：
- 市值匹配度（2分）
- 涨停特征匹配度（3分）
- 板块题材匹配度（2分）
- 历史表现匹配度（2分）
- 技术形态匹配度（1分）

### 4. 投资建议
根据对标分析给出专业建议：
- **最直接对标**：最相似的股票（匹配度最高）
- **核心逻辑对标**：逻辑最相近的股票
- **其他相关对标**：其他值得关注的股票
- **操作建议**：如何利用对标信息进行操作
- **风险提示**：对标股票的风险点分析

### 5. 注意事项
- 只推荐提供的真实涨停数据中出现的股票
- 分析要有理有据，避免空洞描述
- 如找不到完全符合条件的对标股，请说明原因并推荐次优选择

## 返回格式要求【重要】

请直接返回纯JSON对象，不要使用markdown代码块包裹，不要包含任何其他文字说明。

返回的JSON格式如下：

{
  "summary": "对标分析总结（100字内）",
  "target_stock": {
    "code": "目标股票代码",
    "name": "目标股票名称",
    "block": "所属板块",
    "reason": "涨停原因",
    "date": "涨停日期"
  },
  "comparable_stocks": [
    {
      "code": "股票代码",
      "name": "股票名称",
      "block": "所属板块",
      "reason": "涨停原因",
      "date": "涨停日期",
      "tags": ["连板股", "首板股", "突破板"],
      "themes": ["题材1", "题材2"],
      "match_score": 8.5,
      "match_details": {
        "market_cap_match": 2.0,
        "limit_up_match": 3.0,
        "block_theme_match": 2.0,
        "history_match": 1.5,
        "tech_match": 1.0
      },
      "analysis": "详细分析说明（200字内）"
    }
  ],
  "recommendations": {
    "best_match": "最直接对标股票代码",
    "logic_match": "核心逻辑对标股票代码",
    "other_matches": ["其他对标股票代码1", "其他对标股票代码2"],
    "operation_advice": "操作建议（150字内）",
    "risk_warning": "风险提示（100字内）"
  }
}

严格要求：
""" + grounding_rules + """1. 直接返回JSON对象，第一个字符必须是左花括号，最后一个字符必须是右花括号
2. 不要使用代码块包裹（不要用反引号）
3. 不要在JSON前后添加任何说明文字
4. JSON格式必须正确，可直接被解析"""

        return prompt
