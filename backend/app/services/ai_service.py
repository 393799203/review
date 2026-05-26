#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from typing import Optional, Dict, Tuple
from datetime import datetime, date
import json
from app.services.base_service import BaseService
from app.repositories.ai_repository import AIRepository
from core.limit_up_analyzer import LimitUpReasonAnalyzer
from core.data_fetcher import DataFetcher


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
                            'cached': True
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
                        'cached': True
                    }
                except:
                    pass
            
            quote_data = self.data_fetcher.get_realtime_quote(stock_code)
            
            stock_status = self._build_stock_status(quote_data)
            
            analysis_result = self.analyzer.analyze_with_llm(
                limit_up_reason=f"自选股投资分析:{stock_name}{stock_status}",
                stock_code=stock_code,
                stock_name=stock_name,
                limit_up_price=quote_data.get('price') if quote_data else None,
                continuous_days=None,
                limit_up_time=None,
                seal_amount=None,
                turnover_rate=None
            )
            
            self.ai_repository.save_watchlist_analysis(
                stock_code, stock_name, today, analysis_result
            )
            
            return True, '分析成功', {'data': analysis_result, 'cached': False}
            
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
            return ""
        
        price = quote_data.get('price', 0)
        open_price = quote_data.get('open', 0)
        high = quote_data.get('high', 0)
        low = quote_data.get('low', 0)
        change_percent = quote_data.get('change_percent', 0)
        volume = quote_data.get('volume', 0)
        amount = quote_data.get('amount', 0)
        
        status_parts = []
        if change_percent > 0:
            status_parts.append(f"涨幅{change_percent:.2f}%")
        elif change_percent < 0:
            status_parts.append(f"跌幅{abs(change_percent):.2f}%")
        else:
            status_parts.append("平盘")
        
        if price and open_price:
            status_parts.append(f"今开{open_price:.2f}元")
        if high and low:
            status_parts.append(f"最高{high:.2f}元")
            status_parts.append(f"最低{low:.2f}元")
        if volume:
            status_parts.append(f"成交量{(volume/10000):.0f}万手")
        if amount:
            status_parts.append(f"成交额{(amount/100000000):.2f}亿")
        
        return f" 现价{price:.2f}元 {', '.join(status_parts)}"
    
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
            
            api_key = "sk-rjknkdqxefbxebrbfawaokciapqzjejqzqfvlehyhohiknys"
            api_url = "https://api.siliconflow.cn/v1/chat/completions"
            
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": "deepseek-ai/DeepSeek-V4-Flash",
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.7,
                "max_tokens": 500
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
