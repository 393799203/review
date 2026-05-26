import { useState, useEffect, useRef } from 'react';
import { Card, Tag, Spin, message, Button, Collapse, Empty, Input } from 'antd';
import { RobotOutlined, ThunderboltOutlined, FireOutlined, SoundOutlined, LoadingOutlined, UpOutlined, SearchOutlined } from '@ant-design/icons';
import api from '../services/api';
import { useGlobal } from '../contexts/GlobalContext';
import StockKlineModal from '../components/StockKlineModal';

const { Search } = Input;

let loadNewsRef = null;

export const refreshNewsData = (force = true) => {
  if (loadNewsRef) {
    loadNewsRef(force);
  }
};

const NewsPage = () => {
  const { 
    showAllNews, 
    speechEnabled,
    speechSettings,
    setSpeechSettings,
    availableVoices,
    speechSupported,
    getBrowserInfo
  } = useGlobal();
  const [newsList, setNewsList] = useState([]);
  const [analyzingIds, setAnalyzingIds] = useState(new Set());
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
  const [showBackTop, setShowBackTop] = useState(false);
  const [isInitialLoad, setIsInitialLoad] = useState(true);
  const [klineVisible, setKlineVisible] = useState(false);
  const [selectedStock, setSelectedStock] = useState(null);
  const [searchKeyword, setSearchKeyword] = useState('');
  const [searching, setSearching] = useState(false);
  const [searchResults, setSearchResults] = useState([]);
  const [searchHasMore, setSearchHasMore] = useState(false);
  const [isSearchMode, setIsSearchMode] = useState(false);
  
  const countdownRef = useRef(null);
  const speechRef = useRef(null);
  const lastSpeakTimeRef = useRef(0);
  const isPausedRef = useRef(false);
  const speechErrorRef = useRef(false);

  // 同步isPaused状态到ref
  useEffect(() => {
    isPausedRef.current = isPaused;
  }, [isPaused]);

  // 开始倒计时
  const startCountdown = (seconds = 5) => {
    // 清理之前的定时器
    if (countdownRef.current) {
      clearInterval(countdownRef.current);
      countdownRef.current = null;
    }
    
    setCountdown(seconds);
    
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
          console.log(`保存的${currentBrowser}语音包不可用，自动选择本地第一个语音包`);
        }
      }
      
      // 如果保存的语音包不可用，自动选择本地第一个可用的语音包
      if (!selectedVoice && availableVoices.length > 0) {
        selectedVoice = availableVoices[0];
        console.log('自动选择本地第一个可用语音包:', selectedVoice.name);
        
        // 自动更新用户设置为这个语音包
        const newVoices = { ...speechSettings.voices, [currentBrowser]: selectedVoice.name };
        setSpeechSettings({ ...speechSettings, voices: newVoices });
      }
      
      // 如果还没有选中，尝试智能匹配中文语音包（备用方案）
      if (!selectedVoice) {
        selectedVoice = availableVoices.find(voice => voice.lang.includes('zh'));
        if (selectedVoice) {
          console.log('使用中文语音包:', selectedVoice.name);
        }
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
        if (!isManual && !speechErrorRef.current) {
          startCountdown();
        }
        speechErrorRef.current = false;
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
        
        // 标记发生了错误，防止onend再次触发倒计时
        speechErrorRef.current = true;
        
        // 播报出错启动10秒倒计时（仅对自动播报）
        if (!isManual) {
          startCountdown(10);
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
    const handleScroll = () => {
      const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
      setShowBackTop(scrollTop > 300);
    };
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const scrollToTop = () => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  useEffect(() => {
    loadNews(true);
  }, []);

  useEffect(() => {
    const handleScroll = () => {
      // 如果在搜索模式，不触发加载更多
      if (isSearchMode) return;
      
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
  }, [loadingMore, hasMore, newsList, isSearchMode]);

  const handleSearch = async (keyword) => {
    if (!keyword || keyword.trim() === '') {
      setSearchKeyword('');
      setSearchResults([]);
      setSearchHasMore(false);
      setIsSearchMode(false);
      return;
    }
    
    setSearching(true);
    setSearchKeyword(keyword);
    setIsSearchMode(true);
    
    try {
      const response = await axios.get('/api/news/cls-telegraph', {
        params: { keyword: keyword.trim() }
      });
      
      if (response.data.success) {
        setSearchResults(response.data.data || []);
        setSearchHasMore(response.data.has_more !== false);
        if (response.data.data.length === 0) {
          message.info('未找到相关资讯');
        }
      } else {
        message.error('搜索失败：' + response.data.error);
      }
    } catch (error) {
      message.error('搜索失败：' + (error.response?.data?.error || error.message));
    } finally {
      setSearching(false);
    }
  };

  const clearSearch = () => {
    setSearchKeyword('');
    setSearchResults([]);
    setSearchHasMore(false);
    setIsSearchMode(false);
  };

  const loadNews = async (force = false) => {
    if (refreshing) return;
    
    try {
      setRefreshing(true);
      setLoading(true);
      const response = await api.get(`/news/cls-telegraph${force ? '?force=true' : ''}`);

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
      
      const lastNews = newsList[newsList.length - 1];
      const lastCtime = lastNews.ctime;
      
      const response = await api.get(`/news/cls-telegraph?last_ctime=${encodeURIComponent(lastCtime)}&limit=50`);

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
      setAnalyzingIds(prev => new Set([...prev, news.id]));
      const response = await api.post('/news/analyze', {
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
      setAnalyzingIds(prev => {
        const newSet = new Set(prev);
        newSet.delete(news.id);
        return newSet;
      });
    }
  };

  const highlightKeyword = (text, keyword) => {
    if (!text || !keyword) return text;
    
    const regex = new RegExp(`(${keyword.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
    const parts = text.split(regex);
    
    return parts.map((part, index) => {
      if (part.toLowerCase() === keyword.toLowerCase()) {
        return <span key={index} style={{ backgroundColor: '#ffe58f', padding: '0 2px' }}>{part}</span>;
      }
      return part;
    });
  };

  const renderNewsItem = (news) => {
    const analysis = analysisCache[news.id];
    const isAnalyzing = analyzingIds.has(news.id);
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
                {isSearchMode && searchKeyword ? highlightKeyword(news.title, searchKeyword) : news.title}
              </div>
            )}
            {news.content && (
              <div style={{ fontSize: 13, color: '#666', lineHeight: 1.6, whiteSpace: 'pre-wrap' }}>
                {isSearchMode && searchKeyword ? highlightKeyword(news.content, searchKeyword) : news.content}
              </div>
            )}
            {news.has_stocks && news.stock_list && news.stock_list.length > 0 && (
              <div style={{ marginTop: 8, display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                {news.stock_list.map((stock, idx) => {
                  const cleanCode = stock.code.replace(/^(SH|SZ|BJ)/i, '');
                  return (
                    <Tag 
                      key={idx} 
                      color="blue" 
                      style={{ margin: 0, cursor: 'pointer' }}
                      onClick={() => {
                        setSelectedStock({ code: cleanCode, name: stock.name });
                        setKlineVisible(true);
                      }}
                    >
                      {stock.name} {stock.code}
                    </Tag>
                  );
                })}
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
                borderColor: analysis ? '#52c41a' : '#722ed1',
                borderRadius: 3
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
                    <Tag 
                      key={idx} 
                      color="cyan"
                      style={{ cursor: 'pointer' }}
                      onClick={() => {
                        if (stock.code) {
                          setSelectedStock({ code: stock.code, name: stock.name });
                          setKlineVisible(true);
                        }
                      }}
                    >
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

  const displayList = isSearchMode ? searchResults : (showAllNews ? newsList : newsList.filter(n => n.is_important));
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
          <Input
            placeholder="搜索资讯..."
            allowClear
            style={{ width: isMobile ? 150 : 250 }}
            onChange={(e) => {
              setSearchKeyword(e.target.value);
              if (!e.target.value) {
                clearSearch();
              }
            }}
            onPressEnter={() => handleSearch(searchKeyword)}
            suffix={
              <SearchOutlined 
                style={{ color: '#bfbfbf', cursor: 'pointer' }} 
                onClick={() => handleSearch(searchKeyword)}
              />
            }
            value={searchKeyword}
          />
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
          
          {!loadingMore && !hasMore && displayList.length > 0 && !isSearchMode && (
            <div style={{ textAlign: 'center', padding: '20px 0', color: '#999' }}>
              已经到底了
            </div>
          )}
          
          {!loadingMore && !searchHasMore && isSearchMode && searchResults.length > 0 && (
            <div style={{ textAlign: 'center', padding: '20px 0', color: '#999' }}>
              已加载全部搜索结果
            </div>
          )}
        </div>
      )}
        </>
      )}
      
      <StockKlineModal
        visible={klineVisible}
        stockCode={selectedStock?.code}
        stockName={selectedStock?.name}
        onClose={() => setKlineVisible(false)}
      />

      {isMobile && showBackTop && (
        <div
          onClick={scrollToTop}
          style={{
            position: 'fixed',
            right: 16,
            bottom: 70,
            width: 36,
            height: 36,
            borderRadius: 8,
            background: '#1890ff',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 2px 8px rgba(24, 144, 255, 0.4)',
            cursor: 'pointer',
            zIndex: 100,
            transition: 'all 0.3s'
          }}
        >
          <UpOutlined style={{ color: '#fff', fontSize: 14 }} />
        </div>
      )}
    </div>
  );
};

export default NewsPage;