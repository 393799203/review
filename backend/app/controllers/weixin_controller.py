#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import hashlib
import time
import random
import string
import requests
from app.controllers.base_controller import BaseController


class WeixinController(BaseController):
    """微信接口控制器类"""
    
    def __init__(self):
        super().__init__(None)
    
    def get_signature(self):
        """微信JS-SDK签名接口"""
        try:
            url = self.get_query_param('url', '')
            
            WEIXIN_APP_ID = os.environ.get('WEIXIN_APP_ID', '')
            WEIXIN_APP_SECRET = os.environ.get('WEIXIN_APP_SECRET', '')
            
            if not WEIXIN_APP_ID or not WEIXIN_APP_SECRET:
                return self.success(success=False, message='微信配置未设置')
            
            access_token_url = f'https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={WEIXIN_APP_ID}&secret={WEIXIN_APP_SECRET}'
            token_response = requests.get(access_token_url, timeout=5)
            token_data = token_response.json()
            
            if 'access_token' not in token_data:
                return self.success(success=False, message='获取access_token失败')
            
            access_token = token_data['access_token']
            
            jsapi_ticket_url = f'https://api.weixin.qq.com/cgi-bin/ticket/getticket?access_token={access_token}&type=jsapi'
            ticket_response = requests.get(jsapi_ticket_url, timeout=5)
            ticket_data = ticket_response.json()
            
            if ticket_data.get('errcode', 0) != 0:
                return self.success(success=False, message='获取jsapi_ticket失败')
            
            jsapi_ticket = ticket_data['ticket']
            
            noncestr = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
            timestamp = int(time.time())
            
            string1 = f'jsapi_ticket={jsapi_ticket}&noncestr={noncestr}&timestamp={timestamp}&url={url}'
            signature = hashlib.sha1(string1.encode('utf-8')).hexdigest()
            
            return self.success(
                appId=WEIXIN_APP_ID,
                timestamp=timestamp,
                nonceStr=noncestr,
                signature=signature
            )
                
        except Exception as e:
            return self.error(str(e), 500)


weixin_controller = WeixinController()
