#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
from flask_mail import Message
from database import mail


def send_welcome_email_to_user(email, username):
    """发送欢迎邮件给用户"""
    try:
        mail_password = os.environ.get('MAIL_PASSWORD')
        if not mail_password:
            print(f"✗ 邮件服务未配置:缺少 MAIL_PASSWORD 环境变量")
            return False
        
        subject = '感谢您注册使用云雀AI涨停复盘智能体'
        
        html_content = f'''
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <h2 style="color: #1890ff; text-align: center;">欢迎您,{username}!</h2>
            
            <p style="font-size: 16px; line-height: 1.6; color: #333;">
                感谢您注册使用云雀AI涨停复盘智能体!我们很高兴为您提供专业的股票分析工具。
            </p>
            
            <div style="background-color: #f5f5f5; padding: 20px; border-radius: 8px; margin: 20px 0;">
                <h3 style="color: #1890ff; margin-top: 0;">🎯 产品主要能力</h3>
                <ul style="line-height: 1.8; color: #555;">
                    <li><strong>🤖 AI智能体分析</strong>:全链路AI智能分析,从数据采集到决策建议,智能体全程辅助</li>
                    <li><strong>涨停复盘</strong>:实时追踪涨停股票,深度分析涨停原因和板块联动</li>
                    <li><strong>连板天梯</strong>:可视化展示连板股票,把握市场情绪和热点</li>
                    <li><strong>板块强度</strong>:智能分析板块热度,识别强势板块和龙头股</li>
                    <li><strong>自选股管理</strong>:个性化自选股池,实时监控股票动态</li>
                    <li><strong>智能问答助手</strong>:基于AI技术的股票分析和投资问答助手</li>
                    <li><strong>数据统计</strong>:全面的市场数据统计和历史回溯</li>
                </ul>
            </div>
            
            <div style="background-color: #e6f7ff; padding: 20px; border-radius: 8px; margin: 20px 0;">
                <h3 style="color: #1890ff; margin-top: 0;">🤖 AI智能体特色功能</h3>
                <ul style="line-height: 1.8; color: #555;">
                    <li><strong>全链路AI分析</strong>:从行情监控、数据分析到投资建议,AI智能体全程参与</li>
                    <li><strong>智能体问答</strong>:随时向AI智能体咨询股票相关问题,获得专业解答</li>
                    <li><strong>自动化监控</strong>:AI智能体7x24小时监控市场动态,及时发现投资机会</li>
                    <li><strong>个性化推荐</strong>:基于您的投资偏好,智能体提供定制化建议</li>
                </ul>
            </div>
            
            <div style="background-color: #fff7e6; padding: 20px; border-radius: 8px; margin: 20px 0;">
                <h3 style="color: #1890ff; margin-top: 0;">👥 适用客户</h3>
                <ul style="line-height: 1.8; color: #555;">
                    <li><strong>短线交易者</strong>:需要实时捕捉涨停板机会的投资者</li>
                    <li><strong>板块轮动投资者</strong>:关注板块联动和市场热点的交易者</li>
                    <li><strong>量化交易者</strong>:需要数据支持和统计分析的专业人士</li>
                    <li><strong>股票分析师</strong>:需要深度分析工具的研究人员</li>
                    <li><strong>个人投资者</strong>:希望提升投资决策水平的散户朋友</li>
                </ul>
            </div>
            
            <div style="text-align: center; margin: 30px 0;">
                <a href="http://yunqueai.cloud/news" style="background-color: #1890ff; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; font-size: 16px;">立即开始使用</a>
            </div>
            
            <p style="font-size: 14px; color: #999; text-align: center; margin-top: 30px;">
                如有任何问题或需求建议,请随时联系我们:yunque.ai@qq.com
            </p>
            
            <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
            
            <p style="font-size: 12px; color: #999; text-align: center;">
                此邮件由系统自动发送,如有建议或想法,您可直接回复
            </p>
        </div>
        '''
        
        msg = Message(
            subject=subject,
            recipients=[email],
            html=html_content
        )
        
        with mail.connect() as conn:
            conn.send(msg)
        
        print(f"✓ 已向用户 {username} ({email}) 发送欢迎邮件")
        return True
        
    except Exception as e:
        print(f"✗ 发送欢迎邮件失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
