#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Flask后端API - 重构版本
采用分层架构: Controller -> Service -> Repository
"""

from flask import Flask, jsonify, render_template, request
from flask_cors import CORS
from flask_mail import Mail, Message
from datetime import datetime, timedelta
from dotenv import load_dotenv
import sys
import os
import threading
import json
import requests
from mootdx.quotes import Quotes

load_dotenv()

# Windows 控制台默认 GBK 编码，print ✓/✗ 等字符会导致 UnicodeEncodeError 崩溃
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(errors='replace')
    except Exception:
        pass

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from models import DatabaseConfig, LimitUpStock, LadderStats, init_database, Block, WatchlistStock, TradeRecord, AIAnalysisResult, User, ClsNews, UserStrategy, WatchlistAnalysisResult, ResearchReportAnalysisResult
from app.core.data_fetcher import DataFetcher
from app.core.statistics_api import register_statistics_routes
from app.core.limit_up_analyzer import LimitUpReasonAnalyzer
from database import get_db_session, init_mail

from app.controllers.auth_controller import auth_controller
from app.controllers.ladder_controller import init_ladder_controller
from app.controllers.watchlist_controller import init_watchlist_controller
from app.controllers.trade_controller import trade_controller
from app.controllers.wencai_controller import wencai_controller
from app.controllers.news_controller import news_controller
from app.controllers.ai_controller import ai_controller
from app.controllers.report_controller import report_controller
from app.controllers.stock_data_controller import stock_data_controller
from app.controllers.misc_controller import misc_controller
from app.controllers.base_routes_controller import base_routes_controller
from app.controllers.admin_controller import admin_controller
from app.controllers.weixin_controller import weixin_controller
from app.controllers.comparable_controller import comparable_controller
from app.controllers.strategy_controller import strategy_controller
app = Flask(__name__)
CORS(app)

app.config['MAIL_SERVER'] = 'smtp.qq.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_USERNAME'] = 'yunque.ai@qq.com'
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', '')
app.config['MAIL_DEFAULT_SENDER'] = 'yunque.ai@qq.com'

init_mail(app)

data_fetcher = DataFetcher()

ladder_controller = init_ladder_controller(data_fetcher)
watchlist_controller = init_watchlist_controller(data_fetcher)


@app.before_request
def update_user_activity():
    """更新用户最后活动时间"""
    try:
        uid = request.headers.get('X-User-Uid')
        if uid and request.path.startswith('/api/') and not request.path.startswith('/api/health'):
            auth_controller.update_activity(uid)
    except:
        pass


def init_ths_session():
    """初始化同花顺会话并启动心跳"""
    print("初始化同花顺会话...")
    if data_fetcher.init_session():
        data_fetcher.start_heartbeat(interval=60)
        print("✓ 同花顺会话初始化完成")
    else:
        print("✗ 同花顺会话初始化失败，将在请求时重试")


register_statistics_routes(app, get_db_session)


# ==================== 认证路由 ====================

@app.route('/api/auth/register', methods=['POST'])
def register():
    """用户注册"""
    return auth_controller.register()


@app.route('/api/auth/login', methods=['POST'])
def login():
    """用户登录"""
    return auth_controller.login()


@app.route('/api/auth/guest', methods=['POST'])
def guest_login():
    """访客登录"""
    return auth_controller.guest_login()


@app.route('/api/auth/me', methods=['GET'])
def get_current_user():
    """获取当前登录用户信息"""
    return auth_controller.get_current_user()


@app.route('/api/auth/logout', methods=['POST'])
def logout():
    """用户登出"""
    return auth_controller.logout()


@app.route('/api/auth/settings', methods=['PUT'])
def update_auth_settings():
    """更新用户设置"""
    return auth_controller.update_settings()


@app.route('/api/user/settings', methods=['GET', 'POST'])
def handle_user_settings():
    """获取或更新用户设置"""
    if request.method == 'GET':
        return auth_controller.get_settings()
    else:
        return auth_controller.update_settings()


@app.route('/api/admin/user-stats', methods=['GET'])
def get_user_stats():
    """获取用户统计信息（管理员接口）"""
    return auth_controller.get_user_stats()


# ==================== 涨停股票相关路由 ====================

@app.route('/api/dates', methods=['GET'])
def get_available_dates():
    """获取所有可用日期"""
    return ladder_controller.get_available_dates()


@app.route('/api/data/<date_str>', methods=['GET'])
def get_data_by_date(date_str):
    """获取指定日期的完整数据"""
    return ladder_controller.get_data_by_date(date_str)


@app.route('/api/latest', methods=['GET'])
def get_latest_date():
    """获取最近一个交易日"""
    return ladder_controller.get_latest_date()


@app.route('/api/adjacent-trading-days/<date_str>', methods=['GET'])
def get_adjacent_trading_days(date_str):
    """获取指定日期前后一个月的交易日列表"""
    return ladder_controller.get_adjacent_trading_days(date_str)


@app.route('/api/statistics/<date_str>', methods=['GET'])
def get_statistics_by_date(date_str):
    """获取指定日期的统计数据"""
    return ladder_controller.get_statistics_by_date(date_str)


@app.route('/api/refresh', methods=['POST'])
def refresh_data():
    """刷新数据"""
    data = request.json
    date_str = data.get('date')
    return ladder_controller.refresh_data(date_str)


@app.route('/api/block-strength/<date_str>', methods=['GET'])
def get_block_strength(date_str):
    """获取板块强度"""
    return ladder_controller.get_block_strength_by_date(date_str)


@app.route('/api/block-strength/continuous', methods=['GET'])
def get_continuous_blocks():
    """获取连续板块"""
    return ladder_controller.get_continuous_blocks()


@app.route('/api/stock/block', methods=['PUT'])
def update_stock_block():
    """更新股票板块"""
    return ladder_controller.update_stock_block()


@app.route('/api/keyword-analysis/<date_str>', methods=['GET'])
def get_keyword_analysis(date_str):
    """获取关键词 AI 分析缓存"""
    return ladder_controller.get_keyword_analysis(date_str)


@app.route('/api/keyword-analysis', methods=['POST'])
def analyze_keywords():
    """AI 处理涨停关键词"""
    return ladder_controller.analyze_keywords()


# ==================== 自选股相关路由 ====================

@app.route('/api/watchlist', methods=['GET'])
def get_watchlist():
    """获取自选股列表"""
    return watchlist_controller.get_watchlist()


@app.route('/api/watchlist', methods=['POST'])
def add_to_watchlist():
    """添加股票到自选"""
    return watchlist_controller.add_to_watchlist()


@app.route('/api/watchlist/<stock_code>', methods=['DELETE'])
def remove_from_watchlist(stock_code):
    """从自选中删除股票"""
    return watchlist_controller.remove_from_watchlist(stock_code)


@app.route('/api/watchlist/update-prices', methods=['POST'])
def update_watchlist_prices():
    """更新自选股价格"""
    return watchlist_controller.update_prices()


@app.route('/api/stock/search', methods=['GET'])
def search_stock():
    """搜索股票"""
    return watchlist_controller.search_stock()


@app.route('/api/stock/quote/<stock_code>', methods=['GET'])
def get_stock_quote(stock_code):
    """获取单只股票的实时行情"""
    return watchlist_controller.get_stock_quote(stock_code)


# ==================== 交易记录相关路由 ====================

@app.route('/api/watchlist/buy', methods=['POST'])
def buy_stock():
    """买入股票"""
    return trade_controller.buy_stock()


@app.route('/api/watchlist/sell', methods=['POST'])
def sell_stock():
    """卖出股票"""
    return trade_controller.sell_stock()


@app.route('/api/trade-records', methods=['GET'])
def get_trade_records():
    """获取交易记录"""
    return trade_controller.get_trade_records()


# ==================== 问财策略相关路由 ====================

@app.route('/api/wencai/breakout/<date_str>', methods=['GET'])
def wencai_breakout(date_str):
    """问财查询：断板日突破120日高点的股票"""
    return wencai_controller.get_breakout_stocks(date_str)


@app.route('/api/wencai/query', methods=['POST'])
def wencai_query():
    """问财自定义查询"""
    return wencai_controller.query_wencai()


@app.route('/api/wencai/strategies', methods=['GET'])
def get_wencai_strategies():
    """获取用户的问财策略列表"""
    return wencai_controller.get_strategies()


@app.route('/api/wencai/strategies', methods=['POST'])
def create_wencai_strategy():
    """创建新的问财策略"""
    return wencai_controller.create_strategy()


@app.route('/api/wencai/strategies/<int:strategy_id>', methods=['PUT'])
def update_wencai_strategy(strategy_id):
    """更新问财策略"""
    return wencai_controller.update_strategy(strategy_id)


@app.route('/api/wencai/strategies/<int:strategy_id>', methods=['DELETE'])
def delete_wencai_strategy(strategy_id):
    """删除问财策略"""
    return wencai_controller.delete_strategy(strategy_id)


# ==================== 统一策略管理路由 ====================

@app.route('/api/strategies', methods=['GET'])
def get_strategies():
    """获取用户策略列表（支持通过 strategy_type 参数区分）"""
    return strategy_controller.get_strategies()

@app.route('/api/strategies', methods=['POST'])
def create_strategy():
    """创建新策略"""
    return strategy_controller.create_strategy()

@app.route('/api/strategies/<int:strategy_id>', methods=['PUT'])
def update_strategy(strategy_id):
    """更新策略"""
    return strategy_controller.update_strategy(strategy_id)

@app.route('/api/strategies/<int:strategy_id>', methods=['DELETE'])
def delete_strategy(strategy_id):
    """删除策略"""
    return strategy_controller.delete_strategy(strategy_id)


# ==================== 找对标相关路由 ====================

@app.route('/api/comparable/analyze', methods=['POST'])
def analyze_comparable():
    """找对标分析"""
    return comparable_controller.analyze_comparable()

@app.route('/api/comparable/strategies', methods=['GET'])
def get_comparable_strategies():
    """获取用户的找对标策略列表"""
    return comparable_controller.get_strategies()

@app.route('/api/comparable/strategies', methods=['POST'])
def create_comparable_strategy():
    """创建新的找对标策略"""
    return comparable_controller.create_strategy()

@app.route('/api/comparable/strategies/<int:strategy_id>', methods=['PUT'])
def update_comparable_strategy(strategy_id):
    """更新找对标策略"""
    return comparable_controller.update_strategy(strategy_id)

@app.route('/api/comparable/strategies/<int:strategy_id>', methods=['DELETE'])
def delete_comparable_strategy(strategy_id):
    """删除找对标策略"""
    return comparable_controller.delete_strategy(strategy_id)

@app.route('/api/hotspot/first-date/<stock_code>', methods=['GET'])
def get_first_limit_up_date(stock_code):
    """获取股票首次涨停日期"""
    return comparable_controller.get_first_limit_up_date(stock_code)


# ==================== 新闻相关路由 ====================

@app.route('/api/news/cls-telegraph', methods=['GET'])
def get_cls_telegraph():
    """获取财联社电报数据"""
    return news_controller.get_cls_telegraph()


# ==================== AI分析相关路由 ====================

@app.route('/api/stock/analyze/<stock_code>', methods=['GET'])
def analyze_limit_up_stock(stock_code):
    """分析涨停股票"""
    return ai_controller.analyze_limit_up_stock(stock_code)

@app.route('/api/news/analyze', methods=['POST'])
def analyze_news():
    """分析新闻"""
    return ai_controller.analyze_news()

@app.route('/api/stock/analyze', methods=['POST'])
def analyze_stock():
    """分析自选股"""
    return ai_controller.analyze_watchlist_stock()

@app.route('/api/reports/analyze', methods=['POST'])
def analyze_report():
    """分析研报"""
    return ai_controller.analyze_report()

@app.route('/api/hot-topic/analyze', methods=['POST'])
def analyze_hot_topic():
    """分析热门话题"""
    return ai_controller.analyze_hot_topic()

@app.route('/api/stock/comfort', methods=['POST'])
def comfort_stock():
    """AI安慰分析持仓股票"""
    return ai_controller.comfort_stock()


@app.route('/api/stock/report/<stock_code>', methods=['POST'])
def send_stock_report(stock_code):
    """生成个股分析报告并发送到用户邮箱"""
    return ai_controller.send_stock_report(stock_code)


# ==================== 研报相关路由 ====================

@app.route('/api/reports', methods=['GET'])
def get_reports():
    """获取研报列表"""
    return report_controller.get_reports()


# ==================== 股票数据相关路由 ====================

@app.route('/api/stock/kline/<stock_code>', methods=['GET'])
def get_stock_kline(stock_code):
    """获取股票K线数据"""
    return stock_data_controller.get_kline_data(stock_code)

@app.route('/api/stock/intraday/<stock_code>', methods=['GET'])
def get_stock_intraday(stock_code):
    """获取股票当日分时数据和实时行情"""
    return stock_data_controller.get_intraday_data(stock_code)


# ==================== 其他辅助接口路由 ====================

@app.route('/api/ladder-comparison/<date_str>', methods=['GET'])
def get_ladder_comparison(date_str):
    """获取连板晋级对比数据"""
    return misc_controller.get_ladder_comparison(date_str)

@app.route('/api/premium-trend/<int:continuous_days>', methods=['GET'])
def get_premium_trend(continuous_days):
    """获取溢价率趋势"""
    return misc_controller.get_premium_trend(continuous_days)

@app.route('/api/auction-premium-trend/<int:continuous_days>', methods=['GET'])
def get_auction_premium_trend(continuous_days):
    """获取竞价溢价趋势"""
    return misc_controller.get_auction_premium_trend(continuous_days)

@app.route('/api/hot-stocks', methods=['GET'])
def get_hot_stocks():
    """获取同花顺热股数据"""
    return misc_controller.get_hot_stocks()


@app.route('/api/hot-topics', methods=['GET'])
def get_hot_topics():
    """获取热门话题数据"""
    return misc_controller.get_hot_topics()


@app.route('/api/market-alerts/latest', methods=['GET'])
def get_market_alerts():
    """获取市场动态消息"""
    return misc_controller.get_market_alerts()


@app.route('/api/market-alerts/save', methods=['POST'])
def save_market_alerts():
    """保存市场动态消息"""
    return misc_controller.save_market_alerts()


@app.route('/api/market-alerts/history', methods=['GET'])
def get_market_alerts_history():
    """获取历史市场动态消息"""
    return misc_controller.get_market_alerts_history()


# ==================== 基础路由 ====================

@app.route('/')
def index():
    """主页"""
    return base_routes_controller.index()

@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查"""
    return base_routes_controller.health_check()

@app.route('/api/ths-status', methods=['GET'])
def ths_status():
    """获取同花顺会话状态"""
    return base_routes_controller.ths_status()


# ==================== 管理员接口路由 ====================

@app.route('/api/admin/send-welcome-email', methods=['POST'])
def send_welcome_email():
    """发送欢迎邮件"""
    return admin_controller.send_welcome_email()

@app.route('/api/admin/send-email', methods=['POST'])
def send_custom_email():
    """发送自定义邮件"""
    return admin_controller.send_custom_email()


# ==================== 微信接口路由 ====================

@app.route('/api/weixin/signature', methods=['GET'])
def weixin_signature():
    """微信JS-SDK签名接口"""
    return weixin_controller.get_signature()



# ==================== 其他路由（待重构） ====================
# 这里会逐步添加其他模块的路由


if __name__ == '__main__':
    # 初始化同花顺会话
    init_ths_session()
    # 启动应用
    app.run(host='0.0.0.0', port=5001, debug=True, threaded=True)
