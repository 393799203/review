#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
找对标功能控制器
提供AI对标分析接口
"""

from flask import request, jsonify
from app.controllers.base_controller import BaseController
from app.services.ai_service import AIService
from app.core.hotspot_fetcher import HotspotFetcher
from database import get_db_session
from models import UserStrategy
import json


class ComparableController(BaseController):
    """找对标控制器类"""
    
    def __init__(self):
        super().__init__(None)
        self.ai_service = AIService()
        self.hotspot_fetcher = HotspotFetcher()
    
    def analyze_comparable(self):
        """
        找对标分析接口
        
        Request JSON:
        {
            "stock_code": "股票代码",
            "stock_name": "股票名称",
            "block": "所属板块",
            "limit_up_reason": "涨停原因",
            "date": "日期",
            "strategy": "用户输入的策略条件"
        }
        """
        try:
            data = request.json
            stock_code = data.get('stock_code')
            stock_name = data.get('stock_name')
            block = data.get('block', '')
            limit_up_reason = data.get('limit_up_reason', '')
            date_str = data.get('date')
            strategy = data.get('strategy', '')
            
            if not stock_code or not strategy:
                return jsonify({
                    'success': False,
                    'message': '缺少必要参数'
                }), 400
            
            # 调用AI服务进行分析（Service层返回原始AI结果）
            success, message, result = self.ai_service.analyze_comparable_stock(
                stock_code, stock_name, block, limit_up_reason, date_str, strategy
            )
            
            if success:
                # Controller层负责解析AI返回的JSON数据
                import json
                
                raw_analysis = result.get('raw_analysis', '')
                processed_strategy = result.get('processed_strategy', '')
                
                try:
                    # 直接解析AI返回的结果（提示词已要求纯JSON格式）
                    print(f"[DEBUG] Raw analysis length: {len(raw_analysis)}")
                    print(f"[DEBUG] Raw analysis first 200 chars: {raw_analysis[:200]}")
                    
                    analysis_data = json.loads(raw_analysis.strip())
                    
                    print(f"[DEBUG] JSON parsed successfully")
                    print(f"[DEBUG] analysis_data type: {type(analysis_data)}")
                    print(f"[DEBUG] analysis_data keys: {analysis_data.keys() if isinstance(analysis_data, dict) else 'N/A'}")
                    
                    # 验证JSON结构
                    if isinstance(analysis_data, dict):
                        return jsonify({
                            'success': True,
                            'data': {
                                'analysis': analysis_data,
                                'raw_analysis': raw_analysis,
                                'processed_strategy': processed_strategy,
                                'structured': True
                            }
                        })
                except json.JSONDecodeError as e:
                    print(f"[ERROR] JSON解析失败: {e}")
                    print(f"[ERROR] Failed to parse: {raw_analysis[:500]}")
                    # 解析失败，fallback返回原始文本（前端用Markdown显示）
                    return jsonify({
                        'success': True,
                        'data': {
                            'analysis': raw_analysis,
                            'processed_strategy': processed_strategy,
                            'structured': False
                        }
                    })
            else:
                return jsonify({
                    'success': False,
                    'message': message
                }), 500
                
        except Exception as e:
            return jsonify({
                'success': False,
                'message': str(e)
            }), 500
    
    def get_first_limit_up_date(self, stock_code):
        """
        获取股票首次涨停日期
        
        Args:
            stock_code: 股票代码
            
        Returns:
            首次涨停日期信息
        """
        try:
            result = self.hotspot_fetcher.get_first_limit_up_date(stock_code)
            
            if result:
                return jsonify({
                    'success': True,
                    'data': result
                })
            else:
                return jsonify({
                    'success': True,
                    'data': {
                        'first_date': None,
                        'message': '未找到涨停记录'
                    }
                })
                
        except Exception as e:
            return jsonify({
                'success': False,
                'message': str(e)
            }), 500
    
    def get_strategies(self):
        """获取用户的找对标策略列表"""
        try:
            uid = request.headers.get('X-User-Uid')
            if not uid:
                return jsonify({
                    'success': False,
                    'message': '未登录'
                }), 401
            
            session = get_db_session()
            strategies = session.query(UserStrategy).filter_by(
                user_id=uid,
                strategy_type='comparable'  # 区分找对标策略
            ).order_by(UserStrategy.created_at.desc()).all()
            
            result = []
            for s in strategies:
                result.append({
                    'id': s.id,
                    'strategy_name': s.strategy_name,
                    'strategy': s.query_template,
                    'description': s.description,
                    'is_default': s.is_default,
                    'created_at': s.created_at.strftime('%Y-%m-%d %H:%M:%S') if s.created_at else None
                })
            
            session.close()
            return jsonify({
                'success': True,
                'data': result
            })
            
        except Exception as e:
            return jsonify({
                'success': False,
                'message': str(e)
            }), 500
    
    def create_strategy(self):
        """创建新的找对标策略"""
        try:
            uid = request.headers.get('X-User-Uid')
            if not uid:
                return jsonify({
                    'success': False,
                    'message': '未登录'
                }), 401
            
            data = request.json
            name = data.get('name')
            strategy = data.get('strategy')
            is_default = data.get('is_default', False)
            
            if not name or not strategy:
                return jsonify({
                    'success': False,
                    'message': '缺少必要参数'
                }), 400
            
            session = get_db_session()
            new_strategy = UserStrategy(
                user_id=uid,
                strategy_name=name,
                query_template=strategy,
                strategy_type='comparable',  # 标记为找对标策略
                description=data.get('description', ''),
                is_default=1 if is_default else 0
            )
            session.add(new_strategy)
            session.commit()
            
            result = {
                'id': new_strategy.id,
                'strategy_name': new_strategy.strategy_name,
                'strategy': new_strategy.query_template,
                'description': new_strategy.description,
                'is_default': new_strategy.is_default,
                'created_at': new_strategy.created_at.strftime('%Y-%m-%d %H:%M:%S')
            }
            
            session.close()
            return jsonify({
                'success': True,
                'data': result
            })
            
        except Exception as e:
            return jsonify({
                'success': False,
                'message': str(e)
            }), 500
    
    def update_strategy(self, strategy_id):
        """更新找对标策略"""
        try:
            uid = request.headers.get('X-User-Uid')
            if not uid:
                return jsonify({
                    'success': False,
                    'message': '未登录'
                }), 401
            
            data = request.json
            name = data.get('name')
            strategy = data.get('strategy')
            is_default = data.get('is_default', False)
            
            session = get_db_session()
            existing = session.query(UserStrategy).filter_by(
                id=strategy_id,
                user_id=uid,
                strategy_type='comparable'
            ).first()
            
            if not existing:
                session.close()
                return jsonify({
                    'success': False,
                    'message': '策略不存在'
                }), 404
            
            if name:
                existing.strategy_name = name
            if strategy:
                existing.query_template = strategy
            if 'description' in data:
                existing.description = data.get('description', '')
            existing.is_default = 1 if is_default else 0
            
            session.commit()
            
            result = {
                'id': existing.id,
                'strategy_name': existing.strategy_name,
                'strategy': existing.query_template,
                'description': existing.description,
                'is_default': existing.is_default,
                'created_at': existing.created_at.strftime('%Y-%m-%d %H:%M:%S')
            }
            
            session.close()
            return jsonify({
                'success': True,
                'data': result
            })
            
        except Exception as e:
            return jsonify({
                'success': False,
                'message': str(e)
            }), 500
    
    def delete_strategy(self, strategy_id):
        """删除找对标策略"""
        try:
            uid = request.headers.get('X-User-Uid')
            if not uid:
                return jsonify({
                    'success': False,
                    'message': '未登录'
                }), 401
            
            session = get_db_session()
            existing = session.query(UserStrategy).filter_by(
                id=strategy_id,
                user_id=uid,
                strategy_type='comparable'
            ).first()
            
            if not existing:
                session.close()
                return jsonify({
                    'success': False,
                    'message': '策略不存在'
                }), 404
            
            session.delete(existing)
            session.commit()
            session.close()
            
            return jsonify({
                'success': True,
                'message': '删除成功'
            })
            
        except Exception as e:
            return jsonify({
                'success': False,
                'message': str(e)
            }), 500


comparable_controller = ComparableController()