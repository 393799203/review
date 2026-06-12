#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import logging
import threading
from datetime import datetime
from app.controllers.base_controller import BaseController
from app.services.ai_service import AIService
from app.repositories.user_repository import UserRepository

logger = logging.getLogger(__name__)


class AIController(BaseController):
    """AI分析控制器类"""
    
    def __init__(self):
        super().__init__(AIService())
        self.ai_service = self.service
    
    def analyze_limit_up_stock(self, stock_code: str):
        """分析涨停股票"""
        try:
            force = self.get_query_param('force', 'false').lower() == 'true'
            date_str = self.get_query_param('date')
            check_only = self.get_query_param('check_only', 'false').lower() == 'true'
            
            success, message, data = self.ai_service.analyze_limit_up_stock(
                stock_code, force, date_str, check_only
            )
            
            if success:
                if check_only:
                    return self.success(**data)
                else:
                    cached = data.pop('cached', False)
                    return self.success(data=data, cached=cached)
            else:
                return self.error(message, 404 if '未找到' in message else 500)
                
        except Exception as e:
            return self.error(str(e), 500)
    
    def analyze_news(self):
        """分析新闻"""
        try:
            data = self.get_json_data()
            news_id = data.get('news_id')
            title = data.get('title', '')
            content = data.get('content', '')
            force = data.get('force', False)
            
            success, message, data = self.ai_service.analyze_news(
                news_id, title, content, force
            )
            
            if success:
                return self.success(**data)
            else:
                return self.error(message, 400 if '缺少' in message else 500)
                
        except Exception as e:
            return self.error(str(e), 500)
    
    def analyze_watchlist_stock(self):
        """分析自选股"""
        try:
            data = self.get_json_data()
            stock_code = data.get('stock_code', '')
            stock_name = data.get('stock_name', '')
            force = data.get('force', False)
            check_only = data.get('check_only', False)
            
            if not stock_code:
                return self.error('缺少股票代码', 400)
            
            success, message, data = self.ai_service.analyze_watchlist_stock(
                stock_code, stock_name, force, check_only
            )
            
            if success:
                return self.success(**data)
            else:
                return self.error(message, 500)
                
        except Exception as e:
            return self.error(str(e), 500)
    
    def analyze_report(self):
        """分析研报"""
        try:
            data = self.get_json_data()
            info_code = data.get('info_code')
            title = data.get('title', '')
            stock_name = data.get('stock_name', '')
            stock_code = data.get('stock_code', '')
            rating = data.get('rating', '')
            rating_change = data.get('rating_change', '')
            force = data.get('force', False)
            
            predict_eps = {
                'this_year': data.get('predict_this_year_eps', ''),
                'next_year': data.get('predict_next_year_eps', ''),
                'next_two_year': data.get('predict_next_two_year_eps', '')
            }
            
            predict_pe = {
                'this_year': data.get('predict_this_year_pe', ''),
                'next_year': data.get('predict_next_year_pe', ''),
                'next_two_year': data.get('predict_next_two_year_pe', '')
            }
            
            success, message, data = self.ai_service.analyze_report(
                info_code, title, stock_name, stock_code,
                rating, rating_change, predict_eps, predict_pe, force
            )
            
            if success:
                return self.success(**data)
            else:
                return self.error(message, 400 if '缺少' in message else 500)
                
        except Exception as e:
            return self.error(str(e), 500)

    def analyze_hot_topic(self):
        """分析热门话题"""
        try:
            data = self.get_json_data()
            topic_title = data.get('topic_title', '')
            themes = data.get('themes', [])
            investment_direction = data.get('investment_direction', '')
            force = data.get('force', False)
            
            if not topic_title:
                return self.error('缺少话题标题', 400)
            
            success, message, data = self.ai_service.analyze_hot_topic(
                topic_title, themes, investment_direction, force
            )
            
            if success:
                return self.success(**data)
            else:
                return self.error(message, 500)
                
        except Exception as e:
            return self.error(str(e), 500)

    def comfort_stock(self):
        """AI安慰分析持仓股票"""
        try:
            data = self.get_json_data()
            stock_code = data.get('stock_code', '')
            stock_name = data.get('stock_name', '')
            buy_price = float(data.get('buy_price', 0))
            current_price = float(data.get('current_price', 0))
            position_profit = float(data.get('position_profit', 0))
            position_profit_ratio = float(data.get('position_profit_ratio', 0))
            
            success, message, data = self.ai_service.comfort_stock(
                stock_code, stock_name, buy_price, current_price,
                position_profit, position_profit_ratio
            )
            
            if success:
                from flask import jsonify
                return jsonify({
                    'success': True,
                    'data': data
                })
            else:
                return self.error(message, 400 if '缺少' in message else 500)
                
        except Exception as e:
            return self.error(str(e), 500)

    def send_stock_report(self, stock_code: str):
        """生成个股分析报告并发送到用户邮箱"""
        try:
            uid = self.get_current_user_uid()
            if not uid:
                return self.error('请先登录', 401)

            user_repo = UserRepository()
            user = user_repo.get_by_uid(uid)
            if not user:
                return self.error('用户不存在', 404)

            email = user.email
            if not email:
                return self.error('您尚未设置邮箱，请先在设置中绑定邮箱', 400)

            data = self.get_json_data() or {}
            date_str = data.get('date')

            marketing_api = os.environ.get(
                'MARKETING_TOOL_API',
                'http://marketing-tool:8100'
            )

            from flask import current_app

            app = current_app._get_current_object()

            def _run_and_send():
                try:
                    import requests as http_requests

                    logger.info(f"开始生成个股报告: stock_code={stock_code}, date={date_str}")

                    gen_resp = http_requests.post(
                        f'{marketing_api}/api/generate',
                        json={
                            'type': 'stock',
                            'code': stock_code,
                            'date': date_str,
                            'report_only': True
                        },
                        timeout=10
                    )

                    gen_data = gen_resp.json()
                    if gen_resp.status_code != 200 or not gen_data.get('success'):
                        logger.error(f"报告生成请求失败: {gen_resp.text}")
                        return

                    if gen_data.get('cached'):
                        report_data = gen_data
                        logger.info(f"使用已有报告（缓存命中）")
                    else:
                        import time
                        max_wait = 300
                        interval = 10
                        waited = 0
                        report_data = None

                        while waited < max_wait:
                            time.sleep(interval)
                            waited += interval

                            try:
                                report_resp = http_requests.get(
                                    f'{marketing_api}/api/report/latest',
                                    params={'code': stock_code, 'date': date_str or ''},
                                    timeout=10
                                )
                                if report_resp.status_code == 200:
                                    report_data = report_resp.json()
                                    if report_data.get('success'):
                                        break
                            except Exception:
                                pass

                        if not report_data or not report_data.get('success'):
                            logger.error("报告生成超时或未找到报告文件")
                            return

                    article_html = report_data['html']
                    meta = report_data.get('meta', {})
                    stock_name = meta.get('stock_name', stock_code)

                    import smtplib
                    from email.mime.text import MIMEText
                    from email.utils import formataddr

                    subject = f'云雀AI个股深度分析报告 - {stock_name}({stock_code}) - {datetime.now().strftime("%Y-%m-%d")}'

                    mail_username = app.config.get('MAIL_USERNAME', 'yunque.ai@qq.com')
                    mail_password = app.config.get('MAIL_PASSWORD', '')
                    mail_server = app.config.get('MAIL_SERVER', 'smtp.qq.com')
                    mail_port = app.config.get('MAIL_PORT', 465)

                    mime_msg = MIMEText(article_html, 'html', 'utf-8')
                    mime_msg['Subject'] = subject
                    mime_msg['From'] = formataddr(('云雀AI', mail_username))
                    mime_msg['To'] = email

                    smtp = smtplib.SMTP_SSL(mail_server, mail_port, timeout=30)
                    smtp.ehlo()
                    smtp.login(mail_username, mail_password)
                    smtp.sendmail(mail_username, [email], mime_msg.as_bytes())
                    smtp.quit()

                    logger.info(f"报告已发送至 {email}")

                except Exception as e:
                    logger.error(f"报告生成/发送异常: {str(e)}", exc_info=True)

            thread = threading.Thread(target=_run_and_send, daemon=True)
            thread.start()

            return self.success(
                message=f'报告正在生成中，完成后将发送到 {email}',
                data={'email': email}
            )

        except Exception as e:
            return self.error(f'发送报告失败: {str(e)}', 500)


ai_controller = AIController()
