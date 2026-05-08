"""
涨停原因智能分析模块
从涨停原因中挖掘炒作逻辑、关联板块和买入推荐指数
"""

import re
import requests
import json
import logging
import time
from typing import Dict, List, Optional, Tuple
from collections import defaultdict

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class LimitUpReasonAnalyzer:
    """涨停原因智能分析器"""
    
    def __init__(self, api_key: str = None):
        """
        初始化分析器
        
        Args:
            api_key: 硅基流动API密钥
        """
        self.api_key = api_key or "sk-rjknkdqxefbxebrbfawaokciapqzjejqzqfvlehyhohiknys"
        self.api_url = "https://api.siliconflow.cn/v1/chat/completions"
        
        # 模型降级策略：优先使用V4-Flash，失败后降级到V3.2
        self.models = [
            "deepseek-ai/DeepSeek-V4-Flash",
            "Pro/deepseek-ai/DeepSeek-V3.2"
        ]
        self.current_model_index = 0
        
    
    def analyze_with_llm(self, limit_up_reason: str, stock_code: str = None, stock_name: str = None, limit_up_price: float = None, continuous_days: int = None, limit_up_time = None, seal_amount: float = None, turnover_rate: float = None) -> Dict:
        """
        使用大模型分析涨停原因
        
        Args:
            limit_up_reason: 涨停原因
            stock_code: 股票代码
            stock_name: 股票名称
            limit_up_price: 涨停价格
            continuous_days: 连板数
            limit_up_time: 涨停时间
            seal_amount: 封单金额
            turnover_rate: 换手率
            
        Returns:
            分析结果字典
        """
        logger.info(f"========== 开始分析股票 {stock_name}({stock_code}) ==========")
        logger.info(f"输入参数: limit_up_reason={limit_up_reason}, limit_up_price={limit_up_price}, continuous_days={continuous_days}")
        
        if not limit_up_reason:
            logger.warning(f"涨停原因为空,返回默认结果")
            return {
                'sectors': [],
                'speculation_logic': [],
                'stock_attribute': None,
                'market_heat': 0,
                'recommendation_score': 0,
                'recommendation_reason': '无涨停原因',
                'analysis_summary': '无涨停原因',
                'trading_advice': None,
                'keywords': []
            }
        
        try:
            # 构造提示词
            limit_up_price_float = float(limit_up_price) if limit_up_price else None
            
            # 构造股票状态
            status_parts = []
            if continuous_days and continuous_days > 1:
                status_parts.append(f"{continuous_days}连板")
            else:
                status_parts.append("首板")
            if limit_up_time:
                status_parts.append(f"涨停{limit_up_time}")
            if seal_amount:
                status_parts.append(f"封单{seal_amount/100000000:.1f}亿")
            if turnover_rate:
                status_parts.append(f"换手{turnover_rate:.1f}%")
            
            prompt = f"""分析涨停股票并给出交易建议。

股票: {stock_name}({stock_code}) 涨停价{limit_up_price_float}元 {', '.join(status_parts)}
原因: {limit_up_reason}

返回JSON:
{{
  "sectors": [{{"name":"板块","score":0.9}}],
  "speculation_logic": [{{"keyword":"关键词","logic":"逻辑"}}],
  "stock_attribute": {{"type":"类型","market_cap":"市值","investor_type":"资金","trading_style":"风格"}},
  "market_heat": 5,
  "recommendation_score": 4,
  "recommendation_reason": "推荐原因",
  "analysis_summary": "一句话总结",
  "trading_advice": {{
    "buy_strategy": "策略",
    "buy_price_range": "价位",
    "stop_loss_price": "止损",
    "take_profit_price": "止盈",
    "position_ratio": "仓位",
    "risk_level": "风险",
    "holding_period": "周期",
    "key_points": ["要点"]
  }},
  "holding_advice": {{
    "holding_strategy": "持有策略",
    "target_price": "目标价位",
    "stop_loss_price": "止损价位",
    "take_profit_price": "止盈价位",
    "holding_period": "持有周期",
    "risk_warning": "风险提示",
    "key_points": ["关注要点"]
  }}
}}

要求:
1. 板块最多3个,逻辑最多3个
2. 推荐指数: 首板4-5星,2连板3-4星,3连板以上2-3星
3. 连板越多风险越高,仓位越小
4. 价格基于涨停价计算
5. recommendation_reason说明推荐理由
6. market_heat市场热度评分0-10分,综合考虑板块热度、题材热度、资金关注度,7分以上高热度,4-7分中等,4分以下低热度
7. trading_advice针对未持有该股票的买入建议
8. holding_advice针对已持有该股票的持有建议,包括目标价位、止损止盈、持有周期等
9. 直接返回JSON"""

            logger.info(f"构造的Prompt长度: {len(prompt)} 字符")
            logger.info(f"开始调用大模型API: {self.api_url}")
            
            # 尝试使用不同的模型
            last_error = None
            for model_index in range(len(self.models)):
                current_model = self.models[model_index]
                logger.info(f"尝试使用模型: {current_model} (第{model_index + 1}个模型)")
                
                # 调用大模型API
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
                
                data = {
                    "model": current_model,
                    "messages": [
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.7,
                    "max_tokens": 1000
                }
                
                start_time = time.time()
                logger.info(f"API调用开始时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
                
                # 重试机制
                max_retries = 3
                for retry in range(max_retries):
                    try:
                        if retry > 0:
                            # 重试前等待
                            wait_time = 5 * retry  # 递增等待时间
                            logger.info(f"等待 {wait_time} 秒后重试...")
                            time.sleep(wait_time)
                        
                        response = requests.post(self.api_url, headers=headers, json=data, timeout=120)
                        
                        elapsed_time = time.time() - start_time
                        logger.info(f"API调用耗时: {elapsed_time:.2f}秒")
                        logger.info(f"API响应状态码: {response.status_code}")
                        
                        if response.status_code == 503:
                            logger.warning(f"API返回503错误，系统繁忙 (重试 {retry + 1}/{max_retries})")
                            if retry < max_retries - 1:
                                continue  # 继续重试
                            else:
                                # 最后一次重试也失败了，尝试下一个模型
                                logger.warning(f"模型 {current_model} 所有重试都失败，尝试下一个模型")
                                last_error = f"模型 {current_model} 系统繁忙"
                                break
                        
                        # 成功或其他错误，跳出重试循环
                        break
                        
                    except requests.exceptions.Timeout as e:
                        logger.error(f"API调用超时 (重试 {retry + 1}/{max_retries}): {e}")
                        if retry < max_retries - 1:
                            continue
                        else:
                            logger.warning(f"模型 {current_model} 超时，尝试下一个模型")
                            last_error = f"模型 {current_model} 超时"
                            break
                    except Exception as e:
                        logger.error(f"API调用异常: {e}")
                        last_error = f"模型 {current_model} 异常: {str(e)}"
                        break
                
                # 检查是否成功
                if response.status_code == 200:
                    result = response.json()
                    content = result['choices'][0]['message']['content']
                    
                    logger.info(f"API返回内容长度: {len(content)} 字符")
                    logger.info(f"API返回原始内容:\n{content[:500]}...")  # 只显示前500个字符
                    
                    # 解析JSON结果
                    try:
                        # 提取JSON部分
                        json_match = re.search(r'\{.*\}', content, re.DOTALL)
                        if json_match:
                            json_str = json_match.group()
                            logger.info(f"提取的JSON字符串长度: {len(json_str)} 字符")
                            
                            analysis = json.loads(json_str)
                            logger.info(f"解析JSON成功")
                            
                            # 确保所有必需字段都存在
                            if 'recommendation_score' not in analysis:
                                analysis['recommendation_score'] = 3
                            if 'recommendation_reason' not in analysis:
                                analysis['recommendation_reason'] = '综合分析推荐'
                            if 'analysis_summary' not in analysis:
                                analysis['analysis_summary'] = '涨停原因分析完成'
                            if 'trading_advice' not in analysis:
                                analysis['trading_advice'] = None
                            if 'stock_attribute' not in analysis:
                                analysis['stock_attribute'] = None
                            if 'holding_advice' not in analysis:
                                analysis['holding_advice'] = None
                            
                            analysis['keywords'] = limit_up_reason.split('+')
                            
                            logger.info(f"========== 分析完成 {stock_name}({stock_code}) ==========")
                            
                            return analysis
                        else:
                            logger.error(f"无法从返回内容中提取JSON")
                            logger.error(f"原始内容: {content}")
                            # 尝试下一个模型
                            last_error = f"模型 {current_model} 返回格式错误"
                            continue
                    except json.JSONDecodeError as e:
                        logger.error(f"解析大模型返回的JSON失败: {e}")
                        logger.error(f"原始内容: {content}")
                        # 尝试下一个模型
                        last_error = f"模型 {current_model} JSON解析失败"
                        continue
                else:
                    logger.error(f"调用大模型API失败: {response.status_code}")
                    logger.error(f"错误响应: {response.text}")
                    # 尝试下一个模型
                    last_error = f"模型 {current_model} API调用失败: {response.status_code}"
                    continue
            
            # 所有模型都失败了
            logger.error(f"所有模型都失败: {last_error}")
            return {
                'sectors': [],
                'speculation_logic': [],
                'stock_attribute': None,
                'market_heat': 0,
                'recommendation_score': 0,
                'recommendation_reason': f'所有模型都失败: {last_error}',
                'analysis_summary': '分析失败',
                'trading_advice': None,
                'holding_advice': None,
                'keywords': limit_up_reason.split('+')
            }
                
        except requests.exceptions.Timeout as e:
            logger.error(f"大模型API超时: {e}")
            logger.error(f"超时时间: 120秒")
            logger.error(f"股票: {stock_name}({stock_code})")
            return {
                'sectors': [],
                'speculation_logic': [],
                'stock_attribute': None,
                'market_heat': 0,
                'recommendation_score': 0,
                'recommendation_reason': '大模型API超时，请稍后重试',
                'analysis_summary': '分析超时',
                'trading_advice': None,
                'holding_advice': None,
                'keywords': limit_up_reason.split('+')
            }
        except Exception as e:
            logger.error(f"大模型分析失败: {e}", exc_info=True)
            logger.error(f"股票: {stock_name}({stock_code})")
            return {
                'sectors': [],
                'speculation_logic': [],
                'stock_attribute': None,
                'market_heat': 0,
                'recommendation_score': 0,
                'recommendation_reason': f'分析失败: {str(e)}',
                'analysis_summary': '分析失败',
                'trading_advice': None,
                'holding_advice': None,
                'keywords': limit_up_reason.split('+')
            }
    
