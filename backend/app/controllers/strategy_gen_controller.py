#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from app.controllers.base_controller import BaseController
from app.services.strategy_gen_service import StrategyGenService


class StrategyGenController(BaseController):
    """策略代码生成控制器类"""

    def __init__(self):
        super().__init__(StrategyGenService())
        self.strategy_gen_service = self.service

    def generate(self):
        """根据自然语言条件生成策略代码"""
        try:
            data = self.get_json_data()
            requirement = data.get('requirement', '')
            with_backtest = bool(data.get('with_backtest', False))

            success, message, result = self.strategy_gen_service.generate_strategy(
                requirement, with_backtest
            )
            if success:
                return self.success(result)
            else:
                return self.error(message, 400)
        except ValueError as e:
            # LLM 未配置（缺 DEEPSEEK_API_KEY）
            return self.error(str(e), 503)
        except Exception as e:
            return self.error(str(e), 500)


strategy_gen_controller = StrategyGenController()
