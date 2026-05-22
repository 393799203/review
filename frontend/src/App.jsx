import React, { useEffect } from 'react';
import AppRouter from './router';
import './index.css';

function App() {
  useEffect(() => {
    const initWeixin = async () => {
      if (typeof wx !== 'undefined') {
        try {
          const response = await fetch(`/api/weixin/signature?url=${encodeURIComponent(window.location.href)}`);
          const data = await response.json();
          
          if (data.success) {
            wx.config({
              debug: false,
              appId: data.appId,
              timestamp: data.timestamp,
              nonceStr: data.nonceStr,
              signature: data.signature,
              jsApiList: [
                'updateAppMessageShareData',
                'updateTimelineShareData',
                'onMenuShareAppMessage',
                'onMenuShareTimeline'
              ]
            });

            wx.ready(() => {
              const shareConfig = {
                title: '云雀AI-最感性的A股分析智能体',
                desc: '专业的A股涨停股复盘分析工具，提供涨停天梯、财联播报、研报解读、自选回溯等功能',
                link: window.location.origin,
                imgUrl: `${window.location.origin}/logo.png`,
              };

              wx.updateAppMessageShareData(shareConfig);
              wx.updateTimelineShareData(shareConfig);
            });
          }
        } catch (error) {
          console.log('微信分享配置失败:', error);
        }
      }
    };

    initWeixin();
  }, []);

  return <AppRouter />;
}

export default App;
