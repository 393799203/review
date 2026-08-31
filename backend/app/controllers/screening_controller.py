#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from app.controllers.base_controller import BaseController
from app.core.tdx_db import TdxNotConfiguredError
from app.services.screening_service import ScreeningService


class ScreeningController(BaseController):
    """量化筛选控制器类"""

    def __init__(self):
        super().__init__(ScreeningService())
        self.screening_service = self.service

    def get_available_dates(self):
        """获取最近有数据的交易日列表（约半年，130 个交易日）"""
        try:
            success, message, data = self.screening_service.get_available_dates(130)
            if success:
                return self.success(data)
            else:
                return self.error(message, 500)
        except TdxNotConfiguredError as e:
            return self.error(str(e), 503)
        except Exception as e:
            return self.error(str(e), 500)

    def run_screening(self):
        """执行量化筛选"""
        try:
            payload = self.get_json_data()
            success, message, data = self.screening_service.run_screening(payload)
            if success:
                return self.success(data)
            else:
                return self.error(message, 400)
        except TdxNotConfiguredError as e:
            return self.error(str(e), 503)
        except Exception as e:
            return self.error(str(e), 500)


screening_controller = ScreeningController()
