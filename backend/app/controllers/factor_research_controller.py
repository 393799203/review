#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from app.controllers.base_controller import BaseController
from app.core.tdx_db import TdxNotConfiguredError
from app.services.factor_research_service import FactorResearchService


class FactorResearchController(BaseController):
    """因子研究控制器类"""

    def __init__(self):
        super().__init__(FactorResearchService())
        self.factor_research_service = self.service

    def get_meta(self):
        """评估元信息（持有期、因子列表、最近评估时间）"""
        try:
            success, message, data = self.factor_research_service.get_meta()
            if success:
                return self.success(data)
            return self.error(message, 500)
        except TdxNotConfiguredError as e:
            return self.error(str(e), 503)
        except Exception as e:
            return self.error(str(e), 500)

    def get_summary(self):
        """某持有期的因子 IC/IR 汇总（可指定样本 universe 与口径 method）"""
        try:
            success, message, data = self.factor_research_service.get_summary(
                self.get_query_param('horizon'),
                self.get_query_param('universe'),
                self.get_query_param('method'),
            )
            if success:
                return self.success(data)
            return self.error(message, 400)
        except TdxNotConfiguredError as e:
            return self.error(str(e), 503)
        except Exception as e:
            return self.error(str(e), 500)

    def get_ic_series(self):
        """某因子的逐日 IC 时间序列（可指定样本 universe 与口径 method）"""
        try:
            success, message, data = self.factor_research_service.get_ic_series(
                self.get_query_param('factor'),
                self.get_query_param('horizon'),
                self.get_query_param('universe'),
                self.get_query_param('method'),
            )
            if success:
                return self.success(data)
            return self.error(message, 404)
        except TdxNotConfiguredError as e:
            return self.error(str(e), 503)
        except Exception as e:
            return self.error(str(e), 500)


factor_research_controller = FactorResearchController()
