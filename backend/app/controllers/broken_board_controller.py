#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from app.controllers.base_controller import BaseController
from app.services.broken_board_service import BrokenBoardService


class BrokenBoardController(BaseController):
    """断板强势股追踪控制器"""

    def __init__(self, data_fetcher=None):
        super().__init__(BrokenBoardService(data_fetcher=data_fetcher))
        self.broken_board_service = self.service

    def get_strong_stocks(self, date_str: str):
        """获取断板后走势强势的3连板及以上股票"""
        try:
            success, message, data = self.broken_board_service.get_strong_stocks(date_str)

            if success:
                from flask import jsonify
                return jsonify({
                    'success': True,
                    'data': data
                })
            else:
                return self.error(message, 400)

        except Exception as e:
            return self.error(str(e), 500)


broken_board_controller = None


def init_broken_board_controller(data_fetcher):
    """初始化断板强势股控制器"""
    global broken_board_controller
    broken_board_controller = BrokenBoardController(data_fetcher)
    return broken_board_controller
