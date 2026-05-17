import { useState, useEffect, useRef } from 'react';
import { Card, Row, Col, Tag, Spin, message, Button, Collapse, Badge, Tooltip, Empty, Switch, Slider, Select, Popover } from 'antd';
import { NotificationOutlined, RobotOutlined, ReloadOutlined, ThunderboltOutlined, FireOutlined, SoundOutlined, LoadingOutlined, SettingOutlined, PlayCircleOutlined } from '@ant-design/icons';
import axios from 'axios';
import { useGlobal } from '../contexts/GlobalContext';
import { useAuth } from '../contexts/AuthContext';

const { Panel } = Collapse;

let loadNewsRef = null;

export const refreshNewsData = (force = true) => {
  if (loadNewsRef) {
    loadNewsRef(force);
  }
};

const NewsPage = () => {
  const { showAllNews, settings, updateSettings } = useGlobal();
  const { user } = useAuth();
  const [newsList, setNewsList] = useState([]);
  const [analyzingId, setAnalyzingId] = useState(null);
  const [analysisCache, setAnalysisCache] = useState({});
  const [isMobile, setIsMobile] = useState(false);
  const [isFirstLoad, setIsFirstLoad] = useState(true);
  const [hasMore, setHasMore] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [loading, setLoading] = useState(true);
  const [latestNews, setLatestNews] = useState(null);
  const [highlightedIds, setHighlightedIds] = useState(new Set());
  const [countdown, setCountdown] = useState(0);
  const [isPaused, setIsPaused] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [isInitialLoad, setIsInitialLoad] = useState(true);
  const [speechSupported, setSpeechSupported] = useState(false);

  const getBrowserInfo = () => {
    const ua = navigator.userAgent;
    let browserName = 'unknown';
    
    if (ua.indexOf('Chrome') > -1 && ua.indexOf('Edg') === -1) {
      browserName = 'chrome';
    } else if (ua.indexOf('Safari') > -1 && ua.indexOf('Chrome') === -1) {
      browserName = 'safari';
    } else if (ua.indexOf('Firefox') > -1) {
      browserName = 'firefox';
    } else if (ua.indexOf('Edg') > -1) {
      browserName = 'edge';
    }
    
    return browserName;
  };
  
  // 从用户设置中获取语音设置
  const [speechEnabled, setSpeechEnabled] = useState(() => {
    return settings?.news?.speechEnabled ?? true;
  });
  
  const [speechSettings, setSpeechSettings] = useState(() => {
    const savedSettings = settings?.news?.speechSettings;
    
    if (!savedSettings) {
      return {
        voices: {},
        rate: 1.0,
        pitch: 1.0,
        volume: 1.0
      };
    }
    
    if (savedSettings.voice && !savedSettings.voices) {
      console.log('检测到旧的语音设置格式，正在迁移...');
      const browserName = getBrowserInfo();
      const migratedSettings = {
        voices: {
          [browserName]: savedSettings.voice
        },
        rate: savedSettings.rate || 1.0,
        pitch: savedSettings.pitch || 1.0,
        volume: savedSettings.volume || 1.0
      };
      console.log('语音设置迁移完成:', migratedSettings);
      return migratedSettings;
    }
    
    return {
      voices: savedSettings.voices || {},
      rate: savedSettings.rate || 1.0,
      pitch: savedSettings.pitch || 1.0,
      volume: savedSettings.volume || 1.0
    };
  });
  
  const [availableVoices, setAvailableVoices] = useState([]);
  const countdownRef = useRef(null);
  const speechRef = useRef(null);
  const lastSpeakTimeRef = useRef(0);
  const isPausedRef = useRef(false);

  // 同步isPaused状态到ref
  useEffect(() => {
    isPausedRef.current = isPaused;
  }, [isPaused]);

  // 预加载语音并检测支持情况
  useEffect(() => {
    if (!('speechSynthesis' in window)) {
      // 不支持Web Speech API
      setSpeechSupported(false);
      console.log('浏览器不支持Web Speech API');
      return;
    }

    let isMounted = true;
    let checkCount = 0;
    const maxChecks = 10; // 最多检查10次

    const checkVoices = () => {
      if (!isMounted) return;

      try {
        const voices = window.speechSynthesis.getVoices();
        checkCount++;

        console.log(`检查语音包 (第${checkCount}次):`, voices ? voices.length : 0);

        if (voices && voices.length > 0) {
          // 有可用的语音包
          const chineseVoices = voices.filter(voice => voice.lang.includes('zh'));
          if (isMounted) {
            setAvailableVoices(chineseVoices.length > 0 ? chineseVoices : voices);
            setSpeechSupported(true);
            console.log('✅ 检测到语音包支持，可用语音包数量:', voices.length);
          }
          return true;
        } else if (checkCount < maxChecks) {
          // 没有检测到语音包，但还有检查次数，延迟后继续检查
          setTimeout(checkVoices, 500);
        } else {
          // 达到最大检查次数，仍然没有语音包
          if (isMounted) {
            setSpeechSupported(false);
            console.log('❌ 未检测到可用的语音包');
          }
        }
      } catch (error) {
        console.error('检查语音包出错:', error);
        if (isMounted) {
          setSpeechSupported(false);
        }
      }

      return false;
    };

    // 立即尝试加载
    checkVoices();

    // 监听语音包加载事件
    const handleVoicesChanged = () => {
      console.log('voiceschanged事件触发');
      checkVoices();
    };

    window.speechSynthesis.onvoiceschanged = handleVoicesChanged;

    // 清理函数
    return () => {
      isMounted = false;
      if (window.speechSynthesis) {
        window.speechSynthesis.onvoiceschanged = null;
      }
    };
  }, []);

  // 开始倒计时
  const startCountdown = () => {
    // 清理之前的定时器
    if (countdownRef.current) {
      clearInterval(countdownRef.current);
      countdownRef.current = null;
    }
    
    setCountdown(5);
    
    countdownRef.current = setInterval(() => {
      if (!isPausedRef.current) {  // 使用ref而不是state
        setCountdown(prev => {
          if (prev <= 1) {
            closeNewsBroadcast();
            return 0;
          }
          return prev - 1;
        });
      }
    }, 1000);
  };

  // 语音朗读消息
  const speakNews = (news, isManual = false) => {
    // 检查浏览器是否支持语音合成
    if (!('speechSynthesis' in window)) {
      message.warning('您的浏览器不支持语音播报功能，建议使用Chrome、Safari等现代浏览器');
      return;
    }

    // 检查语音合成是否可用
    if (!window.speechSynthesis) {
      message.error('语音合成服务不可用');
      return;
    }

    // 如果播报被禁用且不是手动播报，直接返回
    if (!speechEnabled && !isManual) {
      return;
    }

    // 防抖：仅对自动播报生效，手动播报不需要防抖
    if (!isManual) {
      const now = Date.now();
      if (now - lastSpeakTimeRef.current < 5000) {
        console.log('播报防抖：5秒内不重复播报');
        return;
      }
      lastSpeakTimeRef.current = now;
    }

    try {
      // 停止之前的朗读
      if (speechRef.current) {
        window.speechSynthesis.cancel();
      }

      const text = news.title || news.content;
      
      // 检查文本是否为空
      if (!text || text.trim() === '') {
        message.warning('消息内容为空，无法播报');
        return;
      }

      const utterance = new SpeechSynthesisUtterance(text);
      
      const currentBrowser = getBrowserInfo();
      let selectedVoice = null;
      
      if (speechSettings.voices && speechSettings.voices[currentBrowser]) {
        selectedVoice = availableVoices.find(v => v.name === speechSettings.voices[currentBrowser]);
        if (selectedVoice) {
          console.log(`使用${currentBrowser}浏览器保存的语音包:`, selectedVoice.name);
        } else {
          console.log(`保存的${currentBrowser}语音包不可用，尝试智能匹配`);
        }
      }
      
      if (!selectedVoice) {
        selectedVoice = availableVoices.find(voice => voice.lang.includes('zh'));
        if (selectedVoice) {
          console.log('使用中文语音包:', selectedVoice.name);
        }
      }
      
      if (!selectedVoice && availableVoices.length > 0) {
        selectedVoice = availableVoices[0];
        console.log('使用第一个可用语音包:', selectedVoice.name);
      }
      
      if (selectedVoice) {
        utterance.voice = selectedVoice;
      }
      
      utterance.rate = speechSettings.rate;
      utterance.pitch = speechSettings.pitch;
      utterance.volume = speechSettings.volume;
      
      utterance.onstart = () => {
        setIsSpeaking(true);
        if (isManual) {
          message.success('开始播报');
        }
      };
      
      utterance.onend = () => {
        setIsSpeaking(false);
        // 语音播报完成后开始5秒倒计时（仅对自动播报）
        if (!isManual) {
          startCountdown();
        }
      };
      
      utterance.onerror = (event) => {
        console.error('语音播报错误:', event);
        setIsSpeaking(false);
        
        // 根据错误类型显示不同提示
        if (event.error === 'not-allowed') {
          message.error('语音播报被浏览器阻止，请检查浏览器权限设置');
        } else if (event.error === 'no-speech') {
          message.error('未检测到语音数据');
        } else if (event.error === 'network') {
          message.error('网络错误，无法加载语音数据');
        } else if (event.error === 'canceled') {
          message.info('播报已取消');
        } else {
          message.error(`播报失败: ${event.error || '未知错误'}`);
        }
        
        // 播报出错也启动倒计时（仅对自动播报）
        if (!isManual) {
          startCountdown();
        }
      };
      
      speechRef.current = utterance;
      
      // 尝试播放
      window.speechSynthesis.speak(utterance);
      
      // 检查是否真的开始播放（某些浏览器可能静默失败）
      setTimeout(() => {
        if (isSpeaking && !window.speechSynthesis.speaking) {
          message.warning('语音播报可能未正常启动，请检查浏览器设置');
        }
      }, 1000);
      
    } catch (error) {
      console.error('语音播报异常:', error);
      message.error(`播报异常: ${error.message || '未知错误'}`);
      setIsSpeaking(false);
    }
  };

  // 试听语音
  const testSpeech = () => {
    const testText = '这是一条测试消息，用于试听语音效果。';
    const utterance = new SpeechSynthesisUtterance(testText);
    
    const currentBrowser = getBrowserInfo();
    let selectedVoice = null;
    
    if (speechSettings.voices && speechSettings.voices[currentBrowser]) {
      selectedVoice = availableVoices.find(v => v.name === speechSettings.voices[currentBrowser]);
    }
    
    if (!selectedVoice) {
      selectedVoice = availableVoices.find(voice => voice.lang.includes('zh'));
    }
    
    if (!selectedVoice && availableVoices.length > 0) {
      selectedVoice = availableVoices[0];
    }
    
    if (selectedVoice) {
      utterance.voice = selectedVoice;
    }
    
    utterance.rate = speechSettings.rate;
    utterance.pitch = speechSettings.pitch;
    utterance.volume = speechSettings.volume;
    
    window.speechSynthesis.speak(utterance);
  };

  // 停止朗读
  const stopSpeaking = () => {
    if (window.speechSynthesis) {
      window.speechSynthesis.cancel();
      setIsSpeaking(false);
      // 停止朗读后开始倒计时
      startCountdown();
    }
  };

  // 关闭播报条
  const closeNewsBroadcast = () => {
    stopSpeaking();
    setLatestNews(null);
    setCountdown(0);  // 重置为0
    if (countdownRef.current) {
      clearInterval(countdownRef.current);
      countdownRef.current = null;
    }
  };

  // 滚动到指定消息
  const scrollToNews = (newsId) => {
    const element = document.getElementById(`news-${newsId}`);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth', block: 'center' });
      closeNewsBroadcast();
    }
  };

  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 768);
    };
    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  useEffect(() => {
    loadNews(true);
  }, []);

  // 预加载语音
  useEffect(() => {
    if ('speechSynthesis' in window) {
      const loadVoices = () => {
        const voices = window.speechSynthesis.getVoices();
        const chineseVoices = voices.filter(voice => voice.lang.includes('zh'));
        setAvailableVoices(chineseVoices.length > 0 ? chineseVoices : voices);
      };
      
      loadVoices();
      window.speechSynthesis.onvoiceschanged = loadVoices;
    }
  }, []);

  // 保存设置到用户设置
  useEffect(() => {
    if (user) {
      updateSettings({
        ...settings,
        news: {
          ...settings?.news,
          speechEnabled,
          speechSettings
        }
      });
    }
  }, [speechEnabled, speechSettings]);

  useEffect(() => {
    const handleScroll = () => {
      if (loadingMore || !hasMore || newsList.length === 0) return;
      
      const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
      const scrollHeight = document.documentElement.scrollHeight;
      const clientHeight = document.documentElement.clientHeight;
      
      if (scrollTop + clientHeight >= scrollHeight - 100) {
        loadMoreNews();
      }
    };

    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, [loadingMore, hasMore, newsList]);

  const loadNews = async (force = false) => {
    if (refreshing) return;
    
    try {
      setRefreshing(true);
      setLoading(true);
      const isDev = import.meta.env.DEV;
      const API_BASE = isDev ? 'http://localhost:5001/api' : '/api';
      const response = await axios.get(`${API_BASE}/news/cls-telegraph${force ? '?force=true' : ''}`);

      if (response.data.success) {
        const newData = response.data.data;
        const total = response.data.total || 0;
        
        if (isFirstLoad) {
          setNewsList(newData);
          setHasMore(response.data.has_more !== false);
          setIsFirstLoad(false);
          setIsInitialLoad(false);  // 初始加载完成
        } else {
          // 只有在非初始加载时才播报
          if (!isInitialLoad) {
            setNewsList(prevList => {
              const existingIds = new Set(prevList.map(n => n.id));
              const newItems = newData.filter(n => !existingIds.has(n.id));
              
              if (newItems.length > 0) {
                // 设置最新消息用于滚动播报
                setLatestNews(newItems[0]);
                
                // 语音朗读最新消息
                speakNews(newItems[0]);
                
                // 添加新消息ID到高亮集合
                setHighlightedIds(prev => {
                  const newSet = new Set(prev);
                  newItems.forEach(item => newSet.add(item.id));
                  return newSet;
                });
                
                // 5秒后移除高亮
                setTimeout(() => {
                  setHighlightedIds(prev => {
                    const newSet = new Set(prev);
                    newItems.forEach(item => newSet.delete(item.id));
                    return newSet;
                  });
                }, 5000);
                
                const mergedList = [...newItems, ...prevList];
                const newImportantCount = newItems.filter(n => n.is_important).length;
                message.success(`新增 ${newItems.length} 条资讯，其中 ${newImportantCount} 条加红`);
                return mergedList;
              }
              
              return prevList;
            });
          } else {
            // 初始加载时直接设置数据，不播报
            setNewsList(newData);
          }
        }
      } else {
        message.error(response.data.error || '加载资讯失败');
      }
    } catch (error) {
      console.error('加载资讯失败:', error);
      message.error('加载资讯失败，请稍后重试');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const loadMoreNews = async () => {
    if (loadingMore || !hasMore || newsList.length === 0) return;
    
    try {
      setLoadingMore(true);
      const isDev = import.meta.env.DEV;
      const API_BASE = isDev ? 'http://localhost:5001/api' : '/api';
      
      const lastNews = newsList[newsList.length - 1];
      const lastCtime = lastNews.ctime;
      
      const response = await axios.get(`${API_BASE}/news/cls-telegraph?last_ctime=${encodeURIComponent(lastCtime)}&limit=50`);

      if (response.data.success) {
        const newData = response.data.data;
        
        if (newData.length > 0) {
          setNewsList(prevList => {
            const existingIds = new Set(prevList.map(n => n.id));
            const uniqueNewData = newData.filter(n => !existingIds.has(n.id));
            
            if (uniqueNewData.length > 0) {
              return [...prevList, ...uniqueNewData];
            }
            return prevList;
          });
          setHasMore(response.data.has_more !== false);
        } else {
          setHasMore(false);
        }
      }
    } catch (error) {
      console.error('加载更多资讯失败:', error);
      message.error('加载更多资讯失败');
    } finally {
      setLoadingMore(false);
    }
  };

  loadNewsRef = loadNews;

  const analyzeNews = async (news, force = false) => {
    if (analysisCache[news.id] && !force) {
      return;
    }

    try {
      setAnalyzingId(news.id);
      const isDev = import.meta.env.DEV;
      const API_BASE = isDev ? 'http://localhost:5001/api' : '/api';
      const response = await axios.post(`${API_BASE}/news/analyze`, {
        news_id: news.id,
        title: news.title,
        content: news.content,
        force: force
      });

      if (response.data.success) {
        setAnalysisCache(prev => ({
          ...prev,
          [news.id]: response.data.data
        }));
        message.success('分析完成');
      } else {
        message.error(response.data.error || '分析失败');
      }
    } catch (error) {
      console.error('分析失败:', error);
      message.error('分析失败，请稍后重试');
    } finally {
      setAnalyzingId(null);
    }
  };

  const renderNewsItem = (news) => {
    const analysis = analysisCache[news.id];
    const isAnalyzing = analyzingId === news.id;
    const isHighlighted = highlightedIds.has(news.id);

    return (
      <Card
        key={news.id}
        id={`news-${news.id}`}
        size="small"
        style={{
          marginBottom: 12,
          borderLeft: news.is_important ? '4px solid #f5222d' : '3px solid #d9d9d9',
          background: news.is_important ? '#fff1f0' : '#fff',
          animation: isHighlighted ? 'highlight 5s ease-out' : 'none',
          transition: 'all 0.3s ease'
        }}
        styles={{ body: { padding: isMobile ? 12 : 16 } }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
          <div style={{ flex: 1 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6, flexWrap: 'wrap' }}>
              {news.is_important && (
                <Tag color="red" style={{ margin: 0, fontWeight: 'bold' }}>
                  <FireOutlined /> 加红
                </Tag>
              )}
              {news.has_stocks && (
                <Tag color="orange" style={{ margin: 0 }}>
                  关联个股
                </Tag>
              )}
              {news.confirmed && (
                <Tag color="green" style={{ margin: 0 }}>
                  已确认
                </Tag>
              )}
              <span style={{ fontSize: 12, color: '#999' }}>{news.ctime}</span>
              {news.reading_num > 10000 && (
                <span style={{ fontSize: 11, color: '#999' }}>阅读{(news.reading_num/10000).toFixed(1)}万</span>
              )}
            </div>
            {news.title && (
              <div style={{ fontSize: isMobile ? 14 : 16, fontWeight: news.is_important ? 'bold' : 'normal', marginBottom: 6, color: news.is_important ? '#f5222d' : '#333' }}>
                {news.title}
              </div>
            )}
            {news.content && (
              <div style={{ fontSize: 13, color: '#666', lineHeight: 1.6, whiteSpace: 'pre-wrap' }}>
                {news.content}
              </div>
            )}
            {news.has_stocks && news.stock_list && news.stock_list.length > 0 && (
              <div style={{ marginTop: 8, display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                {news.stock_list.map((stock, idx) => (
                  <Tag key={idx} color="blue" style={{ margin: 0 }}>
                    {stock.name} {stock.code}
                  </Tag>
                ))}
              </div>
            )}
          </div>
          <div style={{ marginLeft: 12, display: 'flex', flexDirection: 'column', gap: 8 }}>
            {speechSupported && (
              <Button
                type="default"
                icon={<SoundOutlined />}
                onClick={() => speakNews(news, true)}
                size="small"
              >
                {isMobile ? '' : '播报'}
              </Button>
            )}
            <Button
              type="primary"
              icon={<RobotOutlined />}
              onClick={() => analyzeNews(news, !!analysis)}
              loading={isAnalyzing}
              style={{
                background: analysis ? '#52c41a' : '#722ed1',
                borderColor: analysis ? '#52c41a' : '#722ed1'
              }}
              size="small"
            >
              {isMobile ? '' : (analysis ? '再次分析' : 'AI分析')}
            </Button>
          </div>
        </div>

        {analysis && (
          <div
            style={{
              marginTop: 12,
              padding: 12,
              background: '#f5f5f5',
              borderRadius: 6
            }}
          >
            <div style={{ marginBottom: 8 }}>
              <Tag color="blue" style={{ marginRight: 8 }}>
                <ThunderboltOutlined /> AI解读
              </Tag>
            </div>

            <div style={{ fontSize: 13, color: '#333', marginBottom: 12, lineHeight: 1.6 }}>
              {analysis.analysis}
            </div>

            {analysis.related_sectors && analysis.related_sectors.length > 0 && (
              <div style={{ marginBottom: 12 }}>
                <div style={{ fontSize: 12, color: '#666', marginBottom: 6 }}>相关板块:</div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                  {analysis.related_sectors.map((sector, idx) => (
                    <Tag key={idx} color="purple">
                      {sector.name} ({Math.round(sector.relevance * 100)}%)
                    </Tag>
                  ))}
                </div>
              </div>
            )}

            {analysis.related_stocks && analysis.related_stocks.length > 0 && (
              <div>
                <div style={{ fontSize: 12, color: '#666', marginBottom: 6 }}>相关个股:</div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                  {analysis.related_stocks.map((stock, idx) => (
                    <Tag key={idx} color="cyan">
                      {stock.name} {stock.code && `(${stock.code})`}
                    </Tag>
                  ))}
                </div>
                <div style={{ marginTop: 8, fontSize: 12, color: '#888' }}>
                  {analysis.related_stocks.map((stock, idx) => (
                    <div key={idx} style={{ marginBottom: 2 }}>
                      <span style={{ color: '#1890ff' }}>{stock.name}:</span> {stock.reason}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {analysis.market_impact && (
              <div style={{ marginTop: 12, paddingTop: 12, borderTop: '1px solid #e8e8e8' }}>
                <Tag color="orange">市场影响</Tag>
                <span style={{ fontSize: 12, color: '#666', marginLeft: 8 }}>
                  {analysis.market_impact}
                </span>
              </div>
            )}
          </div>
        )}
      </Card>
    );
  };

  const displayList = showAllNews ? newsList : newsList.filter(n => n.is_important);
  const importantCount = newsList.filter(n => n.is_important).length;

  return (
    <div>
      {isFirstLoad && loading ? (
        <div style={{ 
          display: 'flex', 
          justifyContent: 'center', 
          alignItems: 'center', 
          minHeight: '400px' 
        }}>
          <Spin size="large" description="加载中..." />
        </div>
      ) : (
        <>
      {/* 顶部滚动播报条 */}
      {latestNews && (
        <div 
          style={{
            position: 'fixed',
            top: '50%',
            left: '50%',
            transform: 'translate(-50%, -50%)',
            background: 'linear-gradient(90deg, #1890ff 0%, #722ed1 100%)',
            color: '#fff',
            padding: '20px 24px',
            borderRadius: 12,
            display: 'flex',
            alignItems: 'center',
            gap: 16,
            boxShadow: '0 8px 24px rgba(24, 144, 255, 0.4)',
            animation: 'fadeIn 0.3s ease-out',
            zIndex: 1000,
            maxWidth: '90vw',
            minWidth: 400
          }}
          onMouseEnter={() => setIsPaused(true)}
          onMouseLeave={() => setIsPaused(false)}
        >
          <SoundOutlined style={{ fontSize: 24, animation: 'pulse 1s infinite' }} />
          <div 
            style={{ flex: 1, cursor: 'pointer' }}
            onClick={() => scrollToNews(latestNews.id)}
            title="点击查看详情"
          >
            <div style={{ 
              fontSize: 16,
              fontWeight: 'bold',
              marginBottom: 8,
              display: 'flex',
              alignItems: 'center',
              gap: 8
            }}>
              <span>{latestNews.is_important ? '🔴 重要资讯' : '📢 最新资讯'}</span>
              {isSpeaking ? (
                <span style={{ 
                  fontSize: 12, 
                  opacity: 0.8,
                  background: 'rgba(255,255,255,0.2)',
                  padding: '2px 8px',
                  borderRadius: 10
                }}>
                  正在朗读...
                </span>
              ) : countdown > 0 && (
                <span style={{ 
                  fontSize: 12, 
                  opacity: 0.8,
                  background: 'rgba(255,255,255,0.2)',
                  padding: '2px 8px',
                  borderRadius: 10
                }}>
                  {countdown}秒后关闭
                </span>
              )}
            </div>
            <div style={{ 
              fontSize: 14,
              lineHeight: 1.5,
              overflow: 'hidden',
              display: '-webkit-box',
              WebkitLineClamp: 2,
              WebkitBoxOrient: 'vertical'
            }}>
              {latestNews.title || latestNews.content}
            </div>
            <div style={{ fontSize: 12, opacity: 0.7, marginTop: 8 }}>
              {latestNews.ctime}
            </div>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            <Button
              type="text"
              style={{ color: '#fff', fontSize: 16 }}
              onClick={() => {
                if (isSpeaking) {
                  stopSpeaking();
                } else {
                  speakNews(latestNews);
                }
              }}
              title={isSpeaking ? '停止朗读' : '朗读消息'}
            >
              {isSpeaking ? '⏸' : '🔊'}
            </Button>
            <Button
              type="text"
              style={{ color: '#fff', fontSize: 20 }}
              onClick={closeNewsBroadcast}
              title="关闭"
            >
              ✕
            </Button>
          </div>
        </div>
      )}

      <style>
        {`
          @keyframes fadeIn {
            from {
              opacity: 0;
              transform: translate(-50%, -50%) scale(0.9);
            }
            to {
              opacity: 1;
              transform: translate(-50%, -50%) scale(1);
            }
          }
          @keyframes pulse {
            0%, 100% {
              transform: scale(1);
            }
            50% {
              transform: scale(1.2);
            }
          }
          @keyframes highlight {
            0% {
              background-color: #fff5f5;
            }
            100% {
              background-color: transparent;
            }
          }
        `}
      </style>

      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
        <div style={{ fontSize: isMobile ? 14 : 16, fontWeight: 'bold', display: 'flex', alignItems: 'center' }}>
          <FireOutlined style={{ color: '#f5222d', marginRight: 8 }} />
          财联社电报
          {loading && !isFirstLoad && (
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              color: '#1890ff',
              fontSize: 12,
              marginLeft: 12
            }}>
              <LoadingOutlined spin />
              <span>数据同步中...</span>
            </div>
          )}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          {speechSupported && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ fontSize: 14, color: '#666' }}>语音播报</span>
              <Switch
                checked={speechEnabled}
                onChange={setSpeechEnabled}
                size="small"
              />
              <Popover
                content={
                  <div style={{ width: 300 }}>
                    <div style={{ marginBottom: 16 }}>
                      <div style={{ marginBottom: 8, fontWeight: 'bold' }}>语音设置</div>
                      <div style={{ marginBottom: 12 }}>
                        <div style={{ marginBottom: 4, fontSize: 12, color: '#666' }}>语音包</div>
                        <Select
                          style={{ width: '100%' }}
                          value={speechSettings.voices?.[getBrowserInfo()] || undefined}
                          onChange={(value) => {
                            const currentBrowser = getBrowserInfo();
                            setSpeechSettings({ 
                              ...speechSettings, 
                              voices: {
                                ...speechSettings.voices,
                                [currentBrowser]: value
                              }
                            });
                          }}
                          placeholder="选择语音包"
                        >
                          {availableVoices.map(voice => (
                            <Select.Option key={voice.name} value={voice.name}>
                              {voice.name} ({voice.lang})
                            </Select.Option>
                          ))}
                        </Select>
                      </div>
                      <div style={{ marginBottom: 12 }}>
                        <div style={{ marginBottom: 4, fontSize: 12, color: '#666' }}>语速: {speechSettings.rate.toFixed(1)}</div>
                        <Slider
                          min={0.5}
                          max={2}
                          step={0.1}
                          value={speechSettings.rate}
                          onChange={(value) => setSpeechSettings({ ...speechSettings, rate: value })}
                        />
                      </div>
                      <div style={{ marginBottom: 12 }}>
                        <div style={{ marginBottom: 4, fontSize: 12, color: '#666' }}>音调: {speechSettings.pitch.toFixed(1)}</div>
                        <Slider
                          min={0.5}
                          max={2}
                          step={0.1}
                          value={speechSettings.pitch}
                          onChange={(value) => setSpeechSettings({ ...speechSettings, pitch: value })}
                        />
                      </div>
                      <div style={{ marginBottom: 12 }}>
                        <div style={{ marginBottom: 4, fontSize: 12, color: '#666' }}>音量: {speechSettings.volume.toFixed(1)}</div>
                        <Slider
                          min={0}
                          max={1}
                          step={0.1}
                          value={speechSettings.volume}
                          onChange={(value) => setSpeechSettings({ ...speechSettings, volume: value })}
                        />
                      </div>
                      <Button
                        type="primary"
                        size="small"
                        icon={<PlayCircleOutlined />}
                        onClick={testSpeech}
                        block
                      >
                        试听效果
                      </Button>
                    </div>
                  </div>
                }
                title={null}
                trigger="click"
              >
                <Button
                  type="text"
                  icon={<SettingOutlined />}
                  size="small"
                  style={{ color: '#1890ff' }}
                />
              </Popover>
            </div>
          )}
        </div>
      </div>

      {displayList.length === 0 && !loading ? (
        <Empty description="暂无资讯" />
      ) : (
        <div>
          {displayList.map(news => renderNewsItem(news))}
          
          {loadingMore && (
            <div style={{ textAlign: 'center', padding: '20px 0' }}>
              <Spin />
              <div style={{ marginTop: 8, color: '#999' }}>加载更多资讯...</div>
            </div>
          )}
          
          {!hasMore && displayList.length > 0 && (
            <div style={{ textAlign: 'center', padding: '20px 0', color: '#999' }}>
              已经到底了
            </div>
          )}
        </div>
      )}
        </>
      )}
    </div>
  );
};

export default NewsPage;