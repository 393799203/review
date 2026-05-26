#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from flask import render_template
from app.controllers.base_controller import BaseController
from core.data_fetcher import DataFetcher


class BaseRoutesController(BaseController):
    """基础路由控制器类"""
    
    def __init__(self):
        super().__init__(None)
        self.data_fetcher = DataFetcher()
    
    def index(self):
        """主页"""
        return render_template('index.html')
    
    def health_check(self):
        """健康检查"""
        from flask import jsonify
        return jsonify({
            'status': 'ok',
            'message': '服务正常运行',
            'ths_session_ready': self.data_fetcher.is_ready()
        })
    
    def ths_status(self):
        """获取同花顺会话状态"""
        from flask import jsonify
        return jsonify({
            'success': True,
            'data': {
                'session_ready': self.data_fetcher.is_ready(),
                'heartbeat_running': self.data_fetcher._heartbeat_running
            }
        })


base_routes_controller = BaseRoutesController()
