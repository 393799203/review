#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from app.controllers.base_controller import BaseController
from app.core.tdx_db import TdxNotConfiguredError
from app.services.backtest_service import BacktestService


class BacktestController(BaseController):
    """组合回测控制器类"""

    def __init__(self):
        super().__init__(BacktestService())
        self.backtest_service = self.service

    def run(self):
        """执行组合回测（多因子打分 → top N% → T+1 开盘 → 再平衡）"""
        try:
            data = self.get_json_data()
            ok, message, result = self.backtest_service.run_via_payload(data)
            if ok:
                return self.success(result)
            return self.error(message, 400)
        except TdxNotConfiguredError as e:
            return self.error(str(e), 503)
        except Exception as e:
            return self.error(str(e), 500)


backtest_controller = BacktestController()