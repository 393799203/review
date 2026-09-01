import React, { useState, useEffect, useLayoutEffect, useRef, useMemo, useCallback, memo } from 'react';
import { Card, Row, Col, Tag, Spin, message, Tooltip, Button, Modal, Badge, Select, Table, Space, Statistic, Empty } from 'antd';
import { DiffOutlined, RobotOutlined, LoadingOutlined, ArrowUpOutlined, ArrowDownOutlined, MinusOutlined, StockOutlined, RiseOutlined, FallOutlined, ArrowRightOutlined, MailOutlined, AimOutlined, ReloadOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';
import api, { stockApi } from '../services/api';
import { useGlobal } from '../contexts/GlobalContext';
import WencaiAssistant from '../components/WencaiAssistant';
import BlockStrengthModal from '../components/BlockStrengthModal';
import StockKlineModal from '../components/StockKlineModal';
import StockAnalysisModal from '../components/StockAnalysisModal';
import PremiumTrendModal from '../components/PremiumTrendModal';
import MarketAlertBar from '../components/MarketAlertBar';
import ComparableStockModal from '../components/ComparableStockModal';

// AI 归并关键词趋势颜色：增强=红，新发=蓝，衰退=绿，平稳=灰
const TREND_TAG_COLORS = { '增强': 'red', '新发': 'blue', '衰退': 'green', '平稳': 'default' };
const TREND_BADGE_COLORS = { '增强': '#cf1322', '新发': '#1890ff', '衰退': '#389e0d', '平稳': '#8c8c8c' };

const LadderPage = () => {
  const { currentDate, loading: globalLoading, setLoading: setGlobalLoading, refreshKey, autoRefresh, showFirstBoard, ladderMode, marketAlerts, setMarketAlerts } = useGlobal();
  const mode = ladderMode || 'ladder';
  const showFirstBoardProp = showFirstBoard;
  const [ladderData, setLadderData] = useState([]);
  const [statistics, setStatistics] = useState({});
  const [yesterdayData, setYesterdayData] = useState(null);
  const [selectedKeyword, setSelectedKeyword] = useState('');
  const [aiKeywordExpanded, setAiKeywordExpanded] = useState(false);
  const [aiKeywordModalVisible, setAiKeywordModalVisible] = useState(false);
  const [aiKeywordLoading, setAiKeywordLoading] = useState(false);
  const [aiKeywordResult, setAiKeywordResult] = useState(null);
  const [selectedBlocks, setSelectedBlocks] = useState([]);
  const [previousSelectedBlocks, setPreviousSelectedBlocks] = useState([]);
  const [isMobile, setIsMobile] = useState(false);
  const [wencaiVisible, setWencaiVisible] = useState(false);
  const [blockStrengthVisible, setBlockStrengthVisible] = useState(false);
  const [klineVisible, setKlineVisible] = useState(false);
  const [selectedStock, setSelectedStock] = useState(null);

  const [analysisVisible, setAnalysisVisible] = useState(false);
  const [analysisStock, setAnalysisStock] = useState(null);
  const [analysisDate, setAnalysisDate] = useState(null);
  const [analyzingStocks, setAnalyzingStocks] = useState(new Set());
  const [completedAnalysis, setCompletedAnalysis] = useState(new Map());

  const [blockFilterDay, setBlockFilterDay] = useState('today');
  
  const [comparisonData, setComparisonData] = useState(null);
  const [comparisonLoading, setComparisonLoading] = useState(false);
  const [comparisonResult, setComparisonResult] = useState({
    promoted: [],
    maintained: [],
    broken: []
  });
  
  const [premiumTrendVisible, setPremiumTrendVisible] = useState(false);
  const [selectedContinuousDays, setSelectedContinuousDays] = useState(null);
  const [premiumTrendType, setPremiumTrendType] = useState('premium');
  
  const [comparableVisible, setComparableVisible] = useState(false);
  const [comparableStock, setComparableStock] = useState(null);
  const [comparableDate, setComparableDate] = useState(null);
  
  const [blockStrengthData, setBlockStrengthData] = useState({ today: { blocks: [] }, tomorrow: { blocks: [] } });
  const [isFirstLoad, setIsFirstLoad] = useState(true);
  const [loading, setLoading] = useState(false);
  const [enableBlur, setEnableBlur] = useState(false);
  
  const [showAnnouncement, setShowAnnouncement] = useState(() => {
    // 检查本地存储，如果用户之前点过"知道了"就不再显示
    return !localStorage.getItem('announcement_dismissed');
  });

  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 768);
    };
    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  useEffect(() => {
    if (currentDate) {
      if (mode === 'comparison') {
        loadComparisonData();
      } else {
        loadData(currentDate);
      }
    }
  }, [currentDate, refreshKey, mode]);

  // 切换模式（天梯/晋级对比）时清空市场动态，避免数据源切换触发误提示
  useEffect(() => {
    setMarketAlerts([]);
  }, [mode, setMarketAlerts]);

  useEffect(() => {
    const tomorrowBlocks = blockStrengthData.tomorrow?.blocks || [];
    if (tomorrowBlocks.length === 0 && blockFilterDay === 'tomorrow') {
      setBlockFilterDay('today');
    }
  }, [blockStrengthData, blockFilterDay]);

  const sortByLimitUpTime = (stocks) => {
    return [...stocks].sort((a, b) => {
      if (!a.limit_up_time && !b.limit_up_time) return 0;
      if (!a.limit_up_time) return 1;
      if (!b.limit_up_time) return -1;
      return a.limit_up_time.localeCompare(b.limit_up_time);
    });
  };

  const keywordStats = useMemo(() => {
    const stats = {};
    ladderData.forEach(item => {
      if (!showFirstBoardProp && (item.level === 0 || item.label === '首板')) return;
      item.stocks.forEach(stock => {
        if (stock.current_status !== 'close') return;
        const reasons = stock.reason ? stock.reason.split('+').filter(r => r.trim()) : ['未分类'];
        reasons.forEach(reason => {
          const trimmed = reason.trim();
          stats[trimmed] = (stats[trimmed] || 0) + 1;
        });
      });
    });
    return Object.entries(stats)
      .map(([keyword, count]) => ({ keyword, count }))
      .sort((a, b) => b.count - a.count);
  }, [ladderData, showFirstBoardProp]);

  // AI合并关键词的source到合并词的映射（如 "火电"->"电力"）
  const mergedKeywordMap = useMemo(() => {
    const map = {};
    if (aiKeywordResult?.merged_keywords) {
      aiKeywordResult.merged_keywords.forEach(item => {
        if (item.source) {
          item.source.forEach(src => { map[src.trim()] = item.keyword; });
        }
        map[item.keyword] = item.keyword;
      });
    }
    return map;
  }, [aiKeywordResult]);

  const isStockKeywordMatched = useCallback((stock) => {
    if (!selectedKeyword) return false;
    const reasons = stock.reason ? stock.reason.split('+').filter(r => r.trim()) : ['未分类'];
    return reasons.some(reason => {
      const r = reason.trim();
      return r === selectedKeyword || mergedKeywordMap[r] === selectedKeyword;
    });
  }, [selectedKeyword, mergedKeywordMap]);

  const handleAnalysisClick = async (stock, tradeDate) => {
    const analysisKey = `${stock.code}_${tradeDate}`;
    
    if (completedAnalysis.has(analysisKey)) {
      setAnalysisStock({ code: stock.code, name: stock.name });
      setAnalysisDate(tradeDate);
      setAnalysisVisible(true);
      return;
    }
    
    if (analyzingStocks.has(analysisKey)) {
      message.info('该股票正在分析中，请稍后...');
      return;
    }
    
    try {
      const checkResponse = await stockApi.analyzeStock(stock.code, false, tradeDate, true);
      
      if (checkResponse.data.success && checkResponse.data.has_cache) {
        setCompletedAnalysis(prev => new Map(prev).set(analysisKey, checkResponse.data.data));
        setAnalysisStock({ code: stock.code, name: stock.name });
        setAnalysisDate(tradeDate);
        setAnalysisVisible(true);
        return;
      }
    } catch (error) {
      console.error('检查缓存失败:', error);
    }
    
    setAnalyzingStocks(prev => new Set(prev).add(analysisKey));
    message.info(`开始分析 ${stock.name}，分析时间可能较长，请稍后...`);
    
    try {
      const response = await stockApi.analyzeStock(stock.code, false, tradeDate);
      
      if (response.data.success) {
        setCompletedAnalysis(prev => new Map(prev).set(analysisKey, response.data.data));
        message.success(`${stock.name} 分析完成，点击图标查看结果`);
      }
    } catch (error) {
      console.error('分析失败:', error);
      message.error('分析失败，请稍后重试');
    } finally {
      setAnalyzingStocks(prev => {
        const newSet = new Set(prev);
        newSet.delete(analysisKey);
        return newSet;
      });
    }
  };
  
  const handleComparableClick = (stock, tradeDate) => {
    setComparableStock({
      code: stock.code,
      name: stock.name,
      block: stock.block,
      limit_up_reason: stock.limit_up_reason || stock.reason || ''
    });
    setComparableDate(tradeDate);
    setComparableVisible(true);
  };

  const loadBlockStrengthData = async () => {
    try {
      const response = await api.get(`/block-strength/continuous?date=${currentDate}`);
      if (response.data.success) {
        setBlockStrengthData(response.data.data);
        setSelectedBlocks([]);
      }
    } catch (error) {
      console.error('加载板块强度数据失败:', error);
    }
  };

  const loadComparisonData = async () => {
    if (mode !== 'comparison') return;

    setComparisonLoading(true);
    try {
      const dateStr = currentDate.replace(/-/g, '');
      const response = await api.get(`/ladder-comparison/${dateStr}`);

      if (response.data.success) {
        setComparisonData(response.data);
        processComparisonData(response.data);

        const todayStocks = response.data.today?.stocks || [];
        const newAlerts = extractAlertsFromStocks(todayStocks, marketAlerts || []);
        setMarketAlerts(newAlerts);
      }
    } catch (error) {
      console.error('加载连板晋级对比数据失败:', error);
      message.error('加载连板晋级对比数据失败');
    } finally {
      setComparisonLoading(false);
    }
  };

  const processComparisonData = (data) => {
    if (!data) return;

    const todayDict = {};
    data.today.stocks.forEach(stock => {
      todayDict[stock.code] = stock;
    });

    const yesterdayDict = {};
    data.yesterday.stocks.forEach(stock => {
      yesterdayDict[stock.code] = stock;
    });

    const promoted = [];
    const maintained = [];
    const broken = [];

    Object.values(yesterdayDict).forEach(yesterdayStock => {
      const todayStock = todayDict[yesterdayStock.code];

      if (todayStock) {
        if (todayStock.continuous_days > yesterdayStock.continuous_days) {
          promoted.push({
            ...todayStock,
            yesterday_height: yesterdayStock.continuous_days,
            status: 'promoted'
          });
        } else {
          maintained.push({
            ...todayStock,
            yesterday_height: yesterdayStock.continuous_days,
            status: 'maintained'
          });
        }
      } else {
        broken.push({
          ...yesterdayStock,
          today_height: 0,
          status: 'broken'
        });
      }
    });

    promoted.sort((a, b) => b.continuous_days - a.continuous_days);
    maintained.sort((a, b) => b.continuous_days - a.continuous_days);
    broken.sort((a, b) => b.yesterday_height - a.yesterday_height);

    setComparisonResult({ promoted, maintained, broken });
  };

  const extractAlertsFromStocks = (stocks, prevAlerts = []) => {
    return stocks.map(stock => {
      const prevAlert = prevAlerts.find(p => p.code === stock.code);
      return {
        code: stock.code,
        name: stock.name,
        continuous_days: stock.continuous_days || stock.level,
        time: stock.limit_up_time || stock.limitUpTime,
        status: stock.current_status,
        hasShownFirstTime: prevAlert ? true : false
      };
    });
  };

  const lastBlockDateRef = useRef('');

  useEffect(() => {
    if (currentDate && mode === 'ladder' && lastBlockDateRef.current !== currentDate) {
      loadBlockStrengthData();
      lastBlockDateRef.current = currentDate;
    }
  }, [currentDate, mode]);

  const loadData = async (dateStr) => {
    try {
      setLoading(true);
      const response = await stockApi.getDataByDate(dateStr);

      if (response.data.success) {
        const data = response.data.data;

        if (response.data.message) {
          message.info(response.data.message);
        }

        const currentStocks = [];
        data.ladder.forEach(item => {
          item.stocks.forEach(stock => {
            currentStocks.push({
              code: stock.code,
              name: stock.name,
              level: item.level,
              limit_up_time: stock.limit_up_time,
              current_status: stock.current_status
            });
          });
        });

        // 合并开板股票（用于市场动态对比出开板提示）
        (data.opened || []).forEach(stock => {
          currentStocks.push({
            code: stock.code,
            name: stock.name,
            level: stock.continuous_days,
            limit_up_time: stock.limit_up_time,
            current_status: 'open'
          });
        });

        setLadderData(data.ladder);
        setStatistics(data.statistics);
        setYesterdayData(data.yesterday);

        const newAlerts = extractAlertsFromStocks(currentStocks, marketAlerts || []);
        setMarketAlerts(newAlerts);

        setLoading(false);
        if (isFirstLoad) {
          setIsFirstLoad(false);
        }
      } else {
        const errorMsg = response.data.error || '加载数据失败';
        message.error(errorMsg);
        setLadderData([]);
        setStatistics({});
        setYesterdayData(null);
        setLoading(false);
      }
    } catch (error) {
      const errorMsg = error.response?.data?.error || error.message || '加载数据失败';
      message.error(errorMsg);
      setLadderData([]);
      setStatistics({});
      setYesterdayData(null);
      setLoading(false);
    }
  };

  const renderStatistics = () => {
    const cardStyle = {
      background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
      borderRadius: 8,
      boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
      transition: 'transform 0.2s, box-shadow 0.2s',
      cursor: 'default'
    };

    if (isMobile) {
      return (
        <div style={{ marginBottom: 12 }}>
          <Row gutter={[8, 8]}>
            <Col span={8}>
              <Card size="small" styles={{ body: { padding: '10px 6px' } }} style={{...cardStyle, background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'}}>
                <div style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.9)' }}>涨停总数</div>
                  <div style={{ fontSize: 18, fontWeight: 'bold', color: '#fff' }}>
                    {statistics.total_count || 0}
                  </div>
                </div>
              </Card>
            </Col>
            <Col span={8}>
              <Card size="small" styles={{ body: { padding: '10px 6px' } }} style={{...cardStyle, background: 'linear-gradient(135deg, #11998e 0%, #38ef7d 100%)'}}>
                <div style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.9)' }}>首板</div>
                  <div style={{ fontSize: 18, fontWeight: 'bold', color: '#fff' }}>
                    {statistics.first_board || 0}
                  </div>
                </div>
              </Card>
            </Col>
            <Col span={8}>
              <Card size="small" styles={{ body: { padding: '10px 6px' } }} style={{...cardStyle, background: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)'}}>
                <div style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.9)' }}>2连板</div>
                  <div style={{ fontSize: 18, fontWeight: 'bold', color: '#fff' }}>
                    {statistics.second_board || 0}
                  </div>
                </div>
              </Card>
            </Col>
            <Col span={8}>
              <Card size="small" styles={{ body: { padding: '10px 6px' } }} style={{...cardStyle, background: 'linear-gradient(135deg, #fa709a 0%, #fee140 100%)'}}>
                <div style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.9)' }}>3连板</div>
                  <div style={{ fontSize: 18, fontWeight: 'bold', color: '#fff' }}>
                    {statistics.third_board || 0}
                  </div>
                </div>
              </Card>
            </Col>
            <Col span={8}>
              <Card size="small" styles={{ body: { padding: '10px 6px' } }} style={{...cardStyle, background: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)'}}>
                <div style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.9)' }}>4连板</div>
                  <div style={{ fontSize: 18, fontWeight: 'bold', color: '#fff' }}>
                    {statistics.fourth_board || 0}
                  </div>
                </div>
              </Card>
            </Col>
            <Col span={8}>
              <Card size="small" styles={{ body: { padding: '10px 6px' } }} style={{...cardStyle, background: 'linear-gradient(135deg, #ff0844 0%, #ffb199 100%)'}}>
                <div style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.9)' }}>5连板+</div>
                  <div style={{ fontSize: 18, fontWeight: 'bold', color: '#fff' }}>
                    {statistics.fifth_plus_board || 0}
                  </div>
                </div>
              </Card>
            </Col>
          </Row>
        </div>
      );
    }

    return (
      <div>
        <Row gutter={12} style={{ marginBottom: 12 }}>
          <Col span={4}>
            <Card size="small" styles={{ body: { padding: '12px 8px' } }} style={{...cardStyle, background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'}}>
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.9)', fontWeight: 500 }}>涨停总数</div>
                <div style={{ fontSize: 24, fontWeight: 'bold', color: '#fff', marginTop: 4 }}>
                  {statistics.total_count || 0}
                </div>
              </div>
            </Card>
          </Col>
          <Col span={4}>
            <Card size="small" styles={{ body: { padding: '12px 8px' } }} style={{...cardStyle, background: 'linear-gradient(135deg, #11998e 0%, #38ef7d 100%)'}}>
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.9)', fontWeight: 500 }}>首板</div>
                <div style={{ fontSize: 24, fontWeight: 'bold', color: '#fff', marginTop: 4 }}>
                  {statistics.first_board || 0}
                </div>
              </div>
            </Card>
          </Col>
          <Col span={4}>
            <Card size="small" styles={{ body: { padding: '12px 8px' } }} style={{...cardStyle, background: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)'}}>
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.9)', fontWeight: 500 }}>2连板</div>
                <div style={{ fontSize: 24, fontWeight: 'bold', color: '#fff', marginTop: 4 }}>
                  {statistics.second_board || 0}
                </div>
              </div>
            </Card>
          </Col>
          <Col span={4}>
            <Card size="small" styles={{ body: { padding: '12px 8px' } }} style={{...cardStyle, background: 'linear-gradient(135deg, #fa709a 0%, #fee140 100%)'}}>
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.9)', fontWeight: 500 }}>3连板</div>
                <div style={{ fontSize: 24, fontWeight: 'bold', color: '#fff', marginTop: 4 }}>
                  {statistics.third_board || 0}
                </div>
              </div>
            </Card>
          </Col>
          <Col span={4}>
            <Card size="small" styles={{ body: { padding: '12px 8px' } }} style={{...cardStyle, background: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)'}}>
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.9)', fontWeight: 500 }}>4连板</div>
                <div style={{ fontSize: 24, fontWeight: 'bold', color: '#fff', marginTop: 4 }}>
                  {statistics.fourth_board || 0}
                </div>
              </div>
            </Card>
          </Col>
          <Col span={4}>
            <Card size="small" styles={{ body: { padding: '12px 8px' } }} style={{...cardStyle, background: 'linear-gradient(135deg, #ff0844 0%, #ffb199 100%)'}}>
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.9)', fontWeight: 500 }}>5连板+</div>
                <div style={{ fontSize: 24, fontWeight: 'bold', color: '#fff', marginTop: 4 }}>
                  {statistics.fifth_plus_board || 0}
                </div>
              </div>
            </Card>
          </Col>
        </Row>
        
      </div>
    );
  };

  const getLimitUpTypeColor = (type) => {
    const colorMap = {
      '一字板': 'red',
      'T字板': 'orange',
      '换手板': 'blue',
      '反包板': 'purple',
    };
    return colorMap[type] || 'default';
  };

  const parseHighDays = (highDays) => {
    if (!highDays || highDays === '首板') return 0;
    const match = highDays.match(/(\d+)天(\d+)板/);
    if (match) {
      return parseInt(match[2]);
    }
    return 0;
  };

  const getHighDaysColor = (highDays) => {
    const days = parseHighDays(highDays);
    if (days >= 5) return 'red';
    if (days === 4) return 'orange';
    if (days === 3) return 'blue';
    if (days === 2) return 'green';
    return 'default';
  };

  const getBlockRankColor = (blockName) => {
    if (selectedBlocks.length === 0) return null;

    if (!blockName || !blockStrengthData[blockFilterDay]?.blocks || blockStrengthData[blockFilterDay].blocks.length === 0) return null;

    const blockRank = blockStrengthData[blockFilterDay].blocks.find(b => b.block_name === blockName);
    if (!blockRank) return null;

    const colorMap = {
      1: '#f5222d',
      2: '#fa8c16',
      3: '#faad14',
      4: '#52c41a',
      5: '#1890ff',
    };

    return colorMap[blockRank.rank] || '#b37feb';
  };

  const renderStockCard = (stock, level) => {
    const blockRankColor = getBlockRankColor(stock.block_name);
    const isKeywordHighlighted = isStockKeywordMatched(stock);
    
    const reasons = stock.reason ? stock.reason.split('+').filter(r => r.trim()) : ['未分类'];
    
    const hasDetailReason = stock.detail_reason && stock.detail_reason.trim();
    
    const filterDisclaimer = (text) => {
      if (!text) return '';
      return text.replace(/（免责声明：[^）]+）/g, '').trim();
    };
    
    // 判断是否是10点前涨停的股票（排除首板）
    const isBefore10AM = stock.limit_up_time && stock.limit_up_time < '10:00:00' && level !== 1;

    if (isMobile) {
      return (
        <Col span={24} key={stock.code}>
          <Card
          size="small"
          style={{
            borderLeft: `3px solid ${blockRankColor || '#8c8c8c'}`,
            background: blockRankColor ? `${blockRankColor}10` : '#f5f5f5',
            position: 'relative',
            overflow: 'hidden',
            cursor: 'pointer',
            ...(isKeywordHighlighted ? { border: '2px solid #f5222d' } : {}),
          }}
          styles={{ body: { padding: '8px 10px' } }}
          onClick={() => {
            setSelectedStock({ code: stock.code, name: stock.name });
            setKlineVisible(true);
          }}
        >
          {stock.is_high_stock === 1 && (
            <div style={{
              position: 'absolute',
              top: 0,
              right: 0,
              background: 'linear-gradient(135deg, #faad14 0%, #fa8c16 100%)',
              color: '#fff',
              fontSize: 10,
              padding: '2px 8px',
              borderRadius: '0 0 0 8px',
              fontWeight: 'bold',
              boxShadow: '-2px 2px 4px rgba(0,0,0,0.1)',
            }}>
              龙头
            </div>
          )}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', overflow: 'visible' }}>
            <div style={{ flex: 1, minWidth: 0, overflow: 'visible' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 4, marginBottom: 2, flexWrap: 'nowrap', overflow: 'visible' }}>
                <span
                  style={{
                    fontWeight: 'bold',
                    fontSize: 14,
                    color: '#1890ff',
                    cursor: 'pointer',
                    filter: enableBlur ? 'blur(5px)' : 'none',
                    userSelect: enableBlur ? 'none' : 'auto',
                    whiteSpace: 'nowrap'
                  }}
                  onClick={() => {
                    setSelectedStock({ code: stock.code, name: stock.name });
                    setKlineVisible(true);
                  }}
                >
                  {stock.code}
                </span>
                <span
                  style={{
                    fontWeight: 'bold',
                    fontSize: 14,
                    color: '#262626',
                    cursor: 'pointer',
                    filter: enableBlur ? 'blur(5px)' : 'none',
                    userSelect: enableBlur ? 'none' : 'auto',
                    whiteSpace: 'nowrap'
                  }}
                  onClick={() => {
                    setSelectedStock({ code: stock.code, name: stock.name });
                    setKlineVisible(true);
                  }}
                >
                  {stock.name}
                </span>
                  {stock.limit_up_type && (
                    <Tag color={getLimitUpTypeColor(stock.limit_up_type)} style={{ fontSize: 10, margin: 0, padding: '0 4px', flexShrink: 0 }}>{stock.limit_up_type}</Tag>
                  )}
                  {stock.high_days && stock.high_days !== '首板' && (
                    <Tag color={getHighDaysColor(stock.high_days)} style={{ fontSize: 10, margin: 0, padding: '0 4px', flexShrink: 0 }}>{stock.high_days}</Tag>
                  )}
                  <div
                    id={`ai-analysis-btn-${stock.code}`}
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      width: 20,
                      height: 20,
                      borderRadius: 3,
                      background: completedAnalysis.has(`${stock.code}_${currentDate.replace(/-/g, '')}`) ? '#52c41a' :
                                  analyzingStocks.has(`${stock.code}_${currentDate.replace(/-/g, '')}`) ? '#fa8c16' : '#722ed1',
                      cursor: 'pointer',
                      marginLeft: 4,
                      flexShrink: 0
                    }}
                    onClick={(e) => {
                      e.stopPropagation();
                      handleAnalysisClick(stock, currentDate.replace(/-/g, ''));
                    }}
                  >
                    <RobotOutlined style={{ fontSize: 11, color: '#fff' }} />
                  </div>

                  {/* 找对标按钮 - 只对10点前涨停的股票显示 */}
                  {isBefore10AM && (
                    <div
                      style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        width: 20,
                        height: 20,
                        borderRadius: 3,
                        background: '#1890ff',
                        cursor: 'pointer',
                        marginLeft: 4,
                        flexShrink: 0
                      }}
                      onClick={(e) => {
                        e.stopPropagation();
                        handleComparableClick(stock, currentDate.replace(/-/g, ''));
                      }}
                    >
                      <AimOutlined style={{ fontSize: 11, color: '#fff' }} />
                    </div>
                  )}
              </div>
            </div>
            <div style={{ textAlign: 'right', marginLeft: 8 }}>
              <div style={{ fontSize: 13, fontWeight: 'bold', color: '#f5222d' }}>¥{stock.limit_up_price.toFixed(2)}</div>
            </div>
          </div>
          <div style={{ fontSize: 11, color: '#666', marginBottom: 4, marginTop: 4 }}>
                涨停: {stock.limit_up_time || '-'} | 封单: {(stock.seal_amount_wan / 10000).toFixed(2)}亿 | 换手: {stock.turnover_rate?.toFixed(2) || '-'}%
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, marginBottom: 4, alignItems: 'center' }}>
            {reasons.map((reason, index) => {
              const trimmedReason = reason.trim();
              const isReasonSelected = selectedKeyword === trimmedReason || mergedKeywordMap[trimmedReason] === selectedKeyword;
              // 移动端不用 Tooltip(触碰即弹,干扰筛选);详细原因仅桌面端悬停查看
              return (
                <Tag
                  key={index}
                  color={isReasonSelected ? 'red' : 'blue'}
                  style={{
                    fontSize: 10,
                    margin: 0,
                    cursor: 'pointer',
                    fontWeight: isReasonSelected ? 'bold' : 'normal'
                  }}
                  onClick={(e) => {
                    e.stopPropagation();
                    setSelectedKeyword(isReasonSelected ? '' : trimmedReason);
                  }}
                >
                  {trimmedReason}
                </Tag>
              );
            })}
            {stock.trend_block && (
              <Tooltip
                title={
                  stock.trend_block_info ? (
                    <div>
                      <div style={{ fontWeight: 600, marginBottom: 4 }}>{stock.trend_block}</div>
                      <div>板块涨跌幅: {stock.trend_block_info.change_rate.toFixed(1)}%</div>
                      <div>涨停: {stock.trend_block_info.limit_up_num} 家</div>
                      <div>连板: {stock.trend_block_info.continuous_plate_num} 家</div>
                      {stock.trend_block_info.matched_tag && (
                        <div>匹配依据: {stock.trend_block_info.matched_tag}</div>
                      )}
                    </div>
                  ) : null
                }
                placement="left"
              >
                <Tag
                  color="#722ed1"
                  style={{
                    fontSize: 10,
                    margin: 0,
                    marginLeft: 'auto',
                    cursor: 'default',
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: 4
                  }}
                >
                  {stock.trend_block}
                </Tag>
              </Tooltip>
            )}
          </div>
          </Card>
        </Col>
      );
    }
    
    return (
      <Col span={6} key={stock.code}>
        <Card
          size="small"
          style={{
            borderLeft: `3px solid ${blockRankColor || '#8c8c8c'}`,
            background: blockRankColor ? `${blockRankColor}10` : '#f5f5f5',
            position: 'relative',
            overflow: 'hidden',
            ...(isKeywordHighlighted ? { border: '2px solid #f5222d' } : {}),
          }}
        >
          {stock.is_high_stock === 1 && (
            <div style={{
              position: 'absolute',
              top: 0,
              right: 0,
              background: 'linear-gradient(135deg, #faad14 0%, #fa8c16 100%)',
              color: '#fff',
              fontSize: 10,
              padding: '2px 8px',
              borderRadius: '0 0 0 8px',
              fontWeight: 'bold',
              boxShadow: '-2px 2px 4px rgba(0,0,0,0.1)',
            }}>
              龙头
            </div>
          )}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 6 }}>
            <div style={{ minWidth: 0 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4, flexWrap: 'nowrap', flexShrink: 0 }}>
                <span 
                  style={{ 
                    fontWeight: 'bold', 
                    fontSize: 14, 
                    color: '#1890ff', 
                    cursor: 'pointer',
                    filter: enableBlur ? 'blur(5px)' : 'none',
                    userSelect: enableBlur ? 'none' : 'auto',
                    whiteSpace: 'nowrap'
                  }}
                  onClick={() => {
                    setSelectedStock({ code: stock.code, name: stock.name });
                    setKlineVisible(true);
                  }}
                >
                  {stock.code}
                </span>
                {stock.limit_up_type && (
                  <Tag color={getLimitUpTypeColor(stock.limit_up_type)} style={{ fontSize: 10, margin: 0, padding: '0 4px' }}>{stock.limit_up_type}</Tag>
                )}
                {stock.high_days && stock.high_days !== '首板' && (
                  <Tag color={getHighDaysColor(stock.high_days)} style={{ fontSize: 10, margin: 0, padding: '0 4px' }}>{stock.high_days}</Tag>
                )}
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap', marginBottom: 8 }}>
                <span 
                  style={{
                    fontWeight: 'bold',
                    fontSize: 15,
                    color: '#262626',
                    filter: enableBlur ? 'blur(5px)' : 'none',
                    userSelect: enableBlur ? 'none' : 'auto',
                    whiteSpace: 'nowrap'
                  }}
                  onClick={() => {
                    setSelectedStock({ code: stock.code, name: stock.name });
                    setKlineVisible(true);
                  }}
                >
                  {stock.name}
                </span>
                <div 
                  id={`ai-analysis-btn-${stock.code}`}
                  style={{ 
                    display: 'inline-flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    width: 20,
                    height: 20,
                    borderRadius: 3,
                    background: completedAnalysis.has(`${stock.code}_${currentDate.replace(/-/g, '')}`) ? '#52c41a' : 
                                analyzingStocks.has(`${stock.code}_${currentDate.replace(/-/g, '')}`) ? '#fa8c16' : '#722ed1',
                    cursor: 'pointer',
                    flexShrink: 0
                  }}
                  onClick={(e) => {
                    e.stopPropagation();
                    handleAnalysisClick(stock, currentDate.replace(/-/g, ''));
                  }}
                >
                  <RobotOutlined style={{ fontSize: 11, color: '#fff' }} />
                </div>
                
                {/* 找对标按钮 - 只对10点前涨停的股票显示 */}
                {isBefore10AM && (
                  <div
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      width: 20,
                      height: 20,
                      borderRadius: 3,
                      background: '#1890ff',
                      cursor: 'pointer',
                      flexShrink: 0
                    }}
                    onClick={(e) => {
                      e.stopPropagation();
                      handleComparableClick(stock, currentDate.replace(/-/g, ''));
                    }}
                  >
                    <AimOutlined style={{ fontSize: 11, color: '#fff' }} />
                  </div>
                )}
              </div>
              <div style={{ fontSize: 11, color: '#666', whiteSpace: 'nowrap' }}>
                <strong>涨停:</strong> {stock.limit_up_time || '-'} | <strong>封单:</strong> {(stock.seal_amount_wan / 10000).toFixed(2)}亿 | <strong>换手:</strong> {stock.turnover_rate?.toFixed(2) || '-'}%
              </div>
            </div>
            <div style={{ textAlign: 'right' }}>
              <div style={{ fontSize: 14, fontWeight: 'bold', color: '#f5222d', marginBottom: 4 }}>
                +{stock.change_percent.toFixed(2)}%
              </div>
              {stock.limit_up_price > 0 && (
                <div style={{ fontSize: 15, fontWeight: 'bold', color: '#f5222d', marginBottom: 4 }}>¥{stock.limit_up_price.toFixed(2)}</div>
              )}
              {stock.trend_block && (
                <Tooltip
                  title={
                    stock.trend_block_info ? (
                      <div>
                        <div style={{ fontWeight: 600, marginBottom: 4 }}>{stock.trend_block}</div>
                        <div>板块涨跌幅: {stock.trend_block_info.change_rate.toFixed(1)}%</div>
                        <div>涨停: {stock.trend_block_info.limit_up_num} 家</div>
                        <div>连板: {stock.trend_block_info.continuous_plate_num} 家</div>
                        {stock.trend_block_info.matched_tag && (
                          <div>匹配依据: {stock.trend_block_info.matched_tag}</div>
                        )}
                      </div>
                    ) : null
                  }
                  placement="left"
                >
                  <Tag
                    color="#722ed1"
                    style={{
                      fontSize: 10,
                      margin: 0,
                      cursor: 'default',
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: 4
                    }}
                  >
                    {stock.trend_block}
                  </Tag>
                </Tooltip>
              )}
            </div>
          </div>
          <div style={{ marginTop: 8 }}>
            {reasons.map((reason, index) => {
              const trimmedReason = reason.trim();
              const isReasonSelected = selectedKeyword === trimmedReason || mergedKeywordMap[trimmedReason] === selectedKeyword;
              return (
                <Tooltip 
                  key={index} 
                  title={
                    hasDetailReason ? (
                      <div style={{ whiteSpace: 'pre-wrap' }}>
                        {filterDisclaimer(stock.detail_reason)}
                      </div>
                    ) : null
                  } 
                  placement="top"
                  styles={{ root: { maxWidth: '500px' } }}
                >
                  <Tag 
                    color={isReasonSelected ? 'red' : 'blue'}
                    style={{ 
                      marginBottom: 4, 
                      fontSize: 11, 
                      cursor: 'pointer',
                      fontWeight: isReasonSelected ? 'bold' : 'normal'
                    }}
                    onClick={(e) => {
                      e.stopPropagation();
                      setSelectedKeyword(isReasonSelected ? '' : trimmedReason);
                    }}
                  >
                    {trimmedReason}
                  </Tag>
                </Tooltip>
              );
            })}
          </div>
        </Card>
      </Col>
    );
  };

  const renderLadder = () => {
    if (!ladderData || ladderData.length === 0) return null;

    const displayLadder = ladderData;

    return displayLadder.map(item => {
      // 根据showFirstBoard过滤首板
      if (!showFirstBoardProp && (item.level === 0 || item.label === '首板')) {
        return null;
      }

      // 根据选中的板块过滤股票：优先用同花顺板块成分股代码（stock_codes），
      // 与强势板块弹窗的涨停数口径一致；接口无 stock_codes 时回退到板块名匹配
      const selectedBlockCodes = new Set();
      if (selectedBlocks.length > 0) {
        const dayBlocks = blockStrengthData[blockFilterDay]?.blocks || [];
        selectedBlocks.forEach((blockName) => {
          const blk = dayBlocks.find((b) => b.block_name === blockName);
          (blk?.stock_codes || []).forEach((c) => selectedBlockCodes.add(String(c)));
        });
      }

      const isStockInSelectedBlock = (stock) => {
        if (selectedBlocks.length === 0) return true;
        if (selectedBlockCodes.size > 0) return selectedBlockCodes.has(String(stock.code));
        return selectedBlocks.includes(stock.block_name);
      };

      // 根据选中的板块过滤股票
      const filteredStocks = item.stocks.filter(stock =>
        isStockInSelectedBlock(stock) && stock.current_status === 'close'
      );
      
      const displayStocks = filteredStocks;
      
      const sortedStocks = sortByLimitUpTime(displayStocks);
      
      // 如果没有符合条件的股票，不显示这个梯队
      if (sortedStocks.length === 0) return null;
      
      return (
        <Card
          key={item.level}
          title={
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: isMobile ? 14 : 16, fontWeight: 'bold' }}>{item.label}</span>
              <Tag color="red">共 {sortedStocks.length} 只</Tag>
            </div>
          }
          style={{ marginBottom: isMobile ? 12 : 16 }}
          size={isMobile ? 'small' : 'medium'}
        >
          <Row gutter={[isMobile ? 8 : 12, isMobile ? 8 : 12]}>
            {sortedStocks.map(stock => renderStockCard(stock, item.level))}
          </Row>
        </Card>
      );
    }).filter(Boolean); // 过滤掉null值
  };

  const isBrokenBoard = () => {
    if (!yesterdayData || !ladderData || ladderData.length === 0) return false;
    
    const todayMaxLevel = Math.max(...ladderData.map(item => item.level));
    const expectedLevel = yesterdayData.max_level + 1;
    
    return todayMaxLevel !== expectedLevel;
  };

  const renderLadderTitle = () => {
    const broken = isBrokenBoard();

    return (
      <div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: isMobile ? 8 : 12 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <h2 style={{ margin: 0, fontSize: isMobile ? 14 : 16 }}>🎯 涨停梯队</h2>
            {loading && !isFirstLoad && (
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                color: '#1890ff',
                fontSize: 12
              }}>
                <LoadingOutlined spin />
                <span>数据同步中...</span>
              </div>
            )}
            {!loading && broken && (
              <Tag color="red" style={{ margin: 0 }}>断板日</Tag>
            )}
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <Button
              type={enableBlur ? "primary" : "default"}
              size="small"
              onClick={() => setEnableBlur(!enableBlur)}
              style={{ fontSize: isMobile ? 12 : 14 }}
            >
              {enableBlur ? '清晰' : '模糊'}
            </Button>
            <Button
              type="primary"
              size="small"
              onClick={() => setWencaiVisible(true)}
              style={{ fontSize: isMobile ? 12 : 14, background: '#722ed1', borderColor: '#722ed1' }}
            >
              问财选股
            </Button>
            <Button
              type="primary"
              size="small"
              onClick={() => setBlockStrengthVisible(true)}
              style={{ fontSize: isMobile ? 12 : 14 }}
            >
              强势板块
            </Button>
          </div>
        </div>

        <div style={{ marginBottom: isMobile ? 8 : 12, display: 'flex', alignItems: 'flex-start', gap: 8 }}>
          <span style={{ fontSize: isMobile ? 12 : 13, color: '#666', minWidth: 70, lineHeight: '24px' }}>板块日期：</span>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
            {['yesterday', 'today', ...((blockStrengthData.tomorrow?.blocks || []).length > 0 ? ['tomorrow'] : [])].map((day) => {
              const dayLabel = { yesterday: '前日', today: '当日', tomorrow: '次日' };
              const dayColor = { yesterday: '#722ed1', today: '#1890ff', tomorrow: '#52c41a' };
              return (
                <Tag
                  key={day}
                  color={blockFilterDay === day ? dayColor[day] : 'default'}
                  style={{ cursor: 'pointer', margin: 0, fontWeight: blockFilterDay === day ? 'bold' : 'normal' }}
                  onClick={() => setBlockFilterDay(day)}
                >
                  {dayLabel[day]}
                </Tag>
              );
            })}
          </div>
        </div>
        <div style={{ marginBottom: isMobile ? 8 : 12, display: 'flex', alignItems: 'flex-start', gap: 8 }}>
          <span style={{ fontSize: isMobile ? 12 : 13, color: '#666', minWidth: 70, lineHeight: '24px' }}>强势板块：</span>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
            <Tag
              color={selectedBlocks.length === (blockStrengthData[blockFilterDay]?.blocks || []).length && (blockStrengthData[blockFilterDay]?.blocks || []).length > 0 ? 'blue' : 'default'}
              style={{ cursor: 'pointer', margin: 0 }}
              onClick={() => {
                const allBlocks = (blockStrengthData[blockFilterDay]?.blocks || []).map(b => b.block_name);
                if (allBlocks.length === 0) return;
                if (selectedBlocks.length === allBlocks.length) {
                  if (previousSelectedBlocks.length > 0) {
                    setSelectedBlocks(previousSelectedBlocks);
                    setPreviousSelectedBlocks([]);
                  } else {
                    setSelectedBlocks([]);
                  }
                } else {
                  setPreviousSelectedBlocks(selectedBlocks);
                  setSelectedBlocks(allBlocks);
                }
              }}
            >
              全部
            </Tag>
            {(isMobile ? (blockStrengthData[blockFilterDay]?.blocks || []).slice(0, 5) : (blockStrengthData[blockFilterDay]?.blocks || [])).map((block) => {
                const colorMap = {
                  1: '#f5222d',
                  2: '#fa8c16',
                  3: '#faad14',
                  4: '#52c41a',
                  5: '#1890ff',
                };

                const isSelected = selectedBlocks.includes(block.block_name);
                const tagColor = isSelected ? (colorMap[block.rank] || '#b37feb') : 'default';

                return (
                  <Tag
                    key={block.block_name}
                    color={tagColor}
                    style={{ cursor: 'pointer', margin: 0 }}
                    onClick={() => {
                      if (isSelected) {
                        setSelectedBlocks(selectedBlocks.filter(b => b !== block.block_name));
                      } else {
                        setSelectedBlocks([...selectedBlocks, block.block_name]);
                      }
                    }}
                  >
                    {block.block_name}
                  </Tag>
                );
              })}
            {isMobile && (blockStrengthData[blockFilterDay]?.blocks || []).length > 5 && (
              <Tag
                color={selectedBlocks.some(b => {
                  const otherBlocks = (blockStrengthData[blockFilterDay]?.blocks || []).slice(5);
                  return otherBlocks.some(ob => ob.block_name === b);
                }) ? '#b37feb' : 'default'}
                style={{ cursor: 'pointer', margin: 0 }}
                onClick={() => {
                  const otherBlocks = (blockStrengthData[blockFilterDay]?.blocks || []).slice(5);
                  const otherBlockNames = otherBlocks.map(b => b.block_name);
                  const hasOtherSelected = selectedBlocks.some(b => otherBlockNames.includes(b));

                  if (hasOtherSelected) {
                    setSelectedBlocks(selectedBlocks.filter(b => !otherBlockNames.includes(b)));
                  } else {
                    setSelectedBlocks([...selectedBlocks, ...otherBlockNames]);
                  }
                }}
              >
                其他板块
              </Tag>
            )}
          </div>
        </div>

        <div style={{ marginBottom: isMobile ? 8 : 12, display: 'flex', alignItems: 'flex-start', gap: 8, flexWrap: 'wrap' }}>
          <span style={{ fontSize: isMobile ? 12 : 13, color: '#666', minWidth: isMobile ? 50 : 84, lineHeight: '24px', flexShrink: 0 }}>{isMobile ? 'AI归并：' : '关键词AI归并：'}</span>
          {/* 控制组：分析按钮 + 展开/收起，固定同一行靠右 */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexShrink: 0, height: 24, marginLeft: 'auto', order: isMobile ? 2 : 3 }}>
            <Button
              type="link"
              size="small"
              icon={<RobotOutlined />}
              onClick={() => setAiKeywordModalVisible(true)}
              style={{ fontSize: 12, padding: 0, color: '#13c2c2' }}
            >
              {aiKeywordResult?.merged_keywords?.length > 0 ? '重新分析' : '点击进行 AI 分析'}
            </Button>
            {aiKeywordResult?.merged_keywords?.length > (isMobile ? 12 : 20) && (
              <Tag
                style={{
                  cursor: 'pointer',
                  margin: 0,
                  flexShrink: 0,
                  color: '#1890ff',
                  borderColor: '#1890ff'
                }}
                onClick={() => setAiKeywordExpanded(!aiKeywordExpanded)}
              >
                {aiKeywordExpanded ? '收起' : `展开(${aiKeywordResult.merged_keywords.length})`}
              </Tag>
            )}
          </div>
          {(
            aiKeywordLoading ? (
              <span style={{ color: '#999', fontSize: 12, lineHeight: '24px', order: isMobile ? 3 : 2 }}>加载中...</span>
            ) : aiKeywordResult?.merged_keywords?.length > 0 ? (
              <div
                style={{
                  display: 'inline-flex',
                  flexWrap: 'wrap',
                  alignItems: 'center',
                  gap: 8,
                  flex: 1,
                  minWidth: isMobile ? '100%' : 200,
                  order: isMobile ? 3 : 2,
                }}
              >
                {(aiKeywordExpanded
                  ? aiKeywordResult.merged_keywords
                  : aiKeywordResult.merged_keywords.slice(0, isMobile ? 12 : 20)
                ).map((item, idx) => {
                  const isSelected = selectedKeyword === item.keyword;
                  return (
                    <Tooltip
                      key={item.keyword}
                      title={item.source ? `合并自：${item.source.join('、')}` : ''}
                    >
                      <Tag
                        color={isSelected ? 'red' : (TREND_TAG_COLORS[item.trend] || (idx < 3 ? 'red' : idx < 6 ? 'orange' : 'blue'))}
                        style={{
                          fontSize: isMobile ? 12 : 13,
                          padding: isMobile ? '1px 6px' : '2px 8px',
                          margin: 0,
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: 6,
                          cursor: 'pointer',
                          fontWeight: isSelected ? 'bold' : 'normal',
                          borderWidth: isSelected ? 2 : 1,
                          borderColor: isSelected ? '#f5222d' : undefined
                        }}
                        onClick={() => {
                          setSelectedKeyword(isSelected ? '' : item.keyword);
                        }}
                      >
                        {item.keyword}
                        <Badge
                          count={item.count}
                          size={isMobile ? 'small' : 'default'}
                          style={{ backgroundColor: TREND_BADGE_COLORS[item.trend] || (idx < 3 ? '#cf1322' : idx < 6 ? '#d46b08' : '#1890ff') }}
                          overflowCount={999}
                        />
                      </Tag>
                    </Tooltip>
                  );
                })}
              </div>
            ) : null
          )}
        </div>
      </div>
    );
  };

  const renderComparisonContent = () => {
    if (comparisonLoading && !comparisonData) {
      return (
        <div style={{ textAlign: 'center', padding: '100px 0' }}>
          <Spin size="large" />
        </div>
      );
    }

    if (!comparisonData) {
      return <Empty description="暂无数据" />;
    }

    const yesterdayStocks = comparisonData.yesterday.stocks || [];
    const todayStocks = comparisonData.today.stocks || [];
    const displayTodayStocks = todayStocks.filter(stock => stock.current_status === 'close');

    const yesterdayLadder = {};
    yesterdayStocks.forEach(stock => {
      const height = stock.continuous_days || 1;
      if (!yesterdayLadder[height]) {
        yesterdayLadder[height] = [];
      }
      yesterdayLadder[height].push(stock);
    });

    Object.keys(yesterdayLadder).forEach(height => {
      yesterdayLadder[height] = sortByLimitUpTime(yesterdayLadder[height]);
    });

    const todayLadder = {};
    displayTodayStocks.forEach(stock => {
      const height = stock.continuous_days || 1;
      if (!todayLadder[height]) {
        todayLadder[height] = [];
      }
      todayLadder[height].push(stock);
    });

    Object.keys(todayLadder).forEach(height => {
      todayLadder[height] = sortByLimitUpTime(todayLadder[height]);
    });

    const promotedLadder = {};
    Object.keys(yesterdayLadder).forEach(height => {
      const nextHeight = parseInt(height) + 1;
      const stocks = yesterdayLadder[height];
      const promotedStocks = [];
      
      stocks.forEach(stock => {
        const todayStock = displayTodayStocks.find(s => s.code === stock.code);
        if (todayStock && todayStock.continuous_days === nextHeight) {
          promotedStocks.push({
            ...todayStock,
            yesterday_height: parseInt(height)
          });
        }
      });
      
      promotedLadder[nextHeight] = promotedStocks;
    });

    Object.keys(promotedLadder).forEach(height => {
      promotedLadder[height] = sortByLimitUpTime(promotedLadder[height]);
    });

    const firstBoardStocks = displayTodayStocks.filter(stock => stock.continuous_days === 1);

    const renderStockCard = (stock, showYesterdayHeight = false, isRightColumn = false, tradeDate = null, height = null) => {
      const isPromoted = !isRightColumn && promotedHeights.some(height => {
        const stocks = promotedLadder[height] || [];
        return stocks.some(s => s.code === stock.code);
      });
      
      // 判断是否是10点前涨停的股票（排除首板）
      const isBefore10AM = stock.limit_up_time && stock.limit_up_time < '10:00:00' && height !== 1;
      
      return (
        <div
          key={stock.code}
          style={{
            padding: isMobile ? '3px 4px' : '8px 12px',
            background: isPromoted ? '#fff1f0' : '#fafafa',
            borderRadius: 4,
            border: isPromoted ? '1px solid #ffa39e' : '1px solid #e8e8e8',
            width: '100%'
          }}
        >
          <div style={{ display: 'flex', flexDirection: 'column', gap: isMobile ? 1 : 4 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: isMobile ? 2 : 4, justifyContent: 'center' }}>
              <span 
                style={{ 
                  fontWeight: 'bold', 
                  fontSize: isMobile ? 10 : 13,
                  cursor: 'pointer',
                  color: '#1890ff'
                }}
                onClick={() => {
                  setSelectedStock(stock);
                  setKlineVisible(true);
                }}
              >
                {stock.name}
              </span>
              <span style={{ color: '#999', fontSize: isMobile ? 8 : 11 }}>{stock.code}</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: isMobile ? 2 : 4 }}>
              {stock.change_percent !== null && stock.change_percent !== undefined && (
                <div style={{ 
                  fontSize: isMobile ? 10 : 12, 
                  fontWeight: 'bold',
                  color: stock.change_percent >= 0 ? '#f5222d' : '#52c41a'
                }}>
                  {stock.change_percent >= 0 ? '+' : ''}{stock.change_percent.toFixed(2)}%
                </div>
              )}
              <div
                {...(isRightColumn ? { id: `ai-analysis-btn-${stock.code}` } : {})}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  width: isMobile ? 16 : 20,
                  height: isMobile ? 16 : 20,
                  borderRadius: 3,
                  background: completedAnalysis.has(`${stock.code}_${tradeDate}`) ? '#52c41a' :
                              analyzingStocks.has(`${stock.code}_${tradeDate}`) ? '#fa8c16' : '#722ed1',
                  cursor: 'pointer'
                }}
                onClick={(e) => {
                  e.stopPropagation();
                  handleAnalysisClick(stock, tradeDate);
                }}
              >
                <RobotOutlined style={{ fontSize: isMobile ? 9 : 11, color: '#fff' }} />
              </div>
              
              {/* 找对标按钮 - 只对10点前涨停的股票显示 */}
              {isBefore10AM && (
                <div
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    width: isMobile ? 16 : 20,
                    height: isMobile ? 16 : 20,
                    borderRadius: 3,
                    background: '#1890ff',
                    cursor: 'pointer'
                  }}
                  onClick={(e) => {
                    e.stopPropagation();
                    handleComparableClick(stock, tradeDate);
                  }}
                >
                  <AimOutlined style={{ fontSize: isMobile ? 9 : 11, color: '#fff' }} />
                </div>
              )}
            </div>
          </div>
        </div>
      );
    };

    const renderLadderColumn = (title, ladderData, showYesterdayHeight = false, heights = null, isRightColumn = false) => {
      const displayHeights = heights || Object.keys(ladderData).map(Number).sort((a, b) => b - a);
      
      return (
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ 
            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            color: '#fff',
            padding: isMobile ? '10px 12px' : '12px 16px',
            borderRadius: '8px 8px 0 0',
            fontWeight: 'bold',
            fontSize: isMobile ? 13 : 14,
            marginBottom: 12
          }}>
            {title}
          </div>
          {displayHeights.map(height => {
            const stocks = ladderData[height] || [];
            return (
              <div key={height} style={{ marginBottom: isMobile ? 8 : 16, minHeight: isMobile ? 60 : 100 }}>
                <div style={{ 
                  background: '#e6f7ff',
                  padding: isMobile ? '3px 8px' : '6px 12px',
                  borderRadius: 4,
                  marginBottom: isMobile ? 4 : 8,
                  fontWeight: 'bold',
                  fontSize: isMobile ? 11 : 13,
                  color: '#1890ff',
                  minHeight: isMobile ? 22 : 28,
                  display: 'flex',
                  alignItems: 'center'
                }}>
                  {height}连板 ({stocks.length}只)
                </div>
                {stocks.length > 0 ? (
                  <div style={{ display: 'grid', gridTemplateColumns: isMobile ? 'repeat(2, 1fr)' : 'repeat(3, 1fr)', gap: isMobile ? 4 : 8 }}>
                    {stocks.map(stock => renderStockCard(stock, showYesterdayHeight, isRightColumn, null, height))}
                  </div>
                ) : (
                  <div style={{ 
                    padding: isMobile ? '6px' : '10px', 
                    textAlign: 'center', 
                    color: '#999',
                    fontSize: isMobile ? 10 : 12,
                    background: '#f5f5f5',
                    borderRadius: 4
                  }}>
                    暂无股票
                  </div>
                )}
              </div>
            );
          })}
        </div>
      );
    };

    const yesterdayHeights = Object.keys(yesterdayLadder).map(Number).sort((a, b) => b - a);
    const promotedHeights = yesterdayHeights.map(h => h + 1);
    
    const promotedCount = Object.values(promotedLadder).reduce((sum, stocks) => sum + stocks.length, 0);

    return (
      <div style={{ minHeight: '100vh' }}>
        <div style={{ marginBottom: isMobile ? 12 : 24}}>
          <Row gutter={isMobile ? [8, 8] : [16, 16]}>
            <Col span={6}>
              <div style={{ 
                background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                borderRadius: 8,
                padding: isMobile ? '8px' : '16px',
                color: '#fff'
              }}>
                <div style={{ fontSize: isMobile ? 10 : 14, opacity: 0.9, marginBottom: 4 }}>今日涨停</div>
                <div style={{ fontSize: isMobile ? 16 : 24, fontWeight: 'bold' }}>{displayTodayStocks.length}<span style={{ fontSize: isMobile ? 10 : 14, marginLeft: 2 }}>只</span></div>
              </div>
            </Col>
            <Col span={6}>
              <div style={{ 
                background: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
                borderRadius: 8,
                padding: isMobile ? '8px' : '16px',
                color: '#fff'
              }}>
                <div style={{ fontSize: isMobile ? 10 : 14, opacity: 0.9, marginBottom: 4 }}>昨日涨停</div>
                <div style={{ fontSize: isMobile ? 16 : 24, fontWeight: 'bold' }}>{yesterdayStocks.length}<span style={{ fontSize: isMobile ? 10 : 14, marginLeft: 2 }}>只</span></div>
              </div>
            </Col>
            <Col span={6}>
              <div style={{ 
                background: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
                borderRadius: 8,
                padding: isMobile ? '8px' : '16px',
                color: '#fff'
              }}>
                <div style={{ fontSize: isMobile ? 10 : 14, opacity: 0.9, marginBottom: 4 }}>晋级</div>
                <div style={{ fontSize: isMobile ? 16 : 24, fontWeight: 'bold' }}>{promotedCount}<span style={{ fontSize: isMobile ? 10 : 14, marginLeft: 2 }}>只</span></div>
              </div>
            </Col>
            <Col span={6}>
              <div style={{ 
                background: 'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)',
                borderRadius: 8,
                padding: isMobile ? '8px' : '16px',
                color: '#fff'
              }}>
                <div style={{ fontSize: isMobile ? 10 : 14, opacity: 0.9, marginBottom: 4 }}>今日首板</div>
                <div style={{ fontSize: isMobile ? 16 : 24, fontWeight: 'bold' }}>{firstBoardStocks.length}<span style={{ fontSize: isMobile ? 10 : 14, marginLeft: 2 }}>只</span></div>
              </div>
            </Col>
          </Row>
        </div>
        <div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: isMobile ? 8 : 24, marginBottom: isMobile ? 12 : 16 }}>
            <div style={{ 
              background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
              color: '#fff',
              padding: isMobile ? '10px 12px' : '12px 16px',
              borderRadius: '8px 8px 0 0',
              fontWeight: 'bold',
              fontSize: isMobile ? 13 : 14
            }}>
              昨日梯队
            </div>
            <div style={{ 
              background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
              color: '#fff',
              padding: isMobile ? '10px 12px' : '12px 16px',
              borderRadius: '8px 8px 0 0',
              fontWeight: 'bold',
              fontSize: isMobile ? 13 : 14
            }}>
              今日晋级
            </div>
          </div>
          {yesterdayHeights.map((height, index) => {
            const yesterdayStocks = yesterdayLadder[height] || [];
            const nextHeight = height + 1;
            const promotedStocks = promotedLadder[nextHeight] || [];
            
            const avgChangePercent = comparisonData?.yesterday?.avg_premium?.[height] ?? null;
            const avgAuctionPremium = comparisonData?.yesterday?.avg_auction_premium?.[height] ?? null;
            
            return (
              <div key={height} style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: isMobile ? 8 : 24, marginBottom: isMobile ? 12 : 16 }}>
                <div>
                  <div style={{
                    background: '#e6f7ff',
                    padding: isMobile ? '5px 6px' : '6px 12px',
                    borderRadius: 4,
                    marginBottom: 8,
                    fontWeight: 'bold',
                    fontSize: isMobile ? 12 : 13,
                    color: '#1890ff',
                    minHeight: isMobile ? 26 : 28,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between'
                  }}>
                    <span style={{ whiteSpace: 'nowrap' }}>
                      {height}板 ({yesterdayStocks.length}只)
                      {avgAuctionPremium !== null && !isNaN(avgAuctionPremium) && (
                        <span
                          style={{
                            marginLeft: isMobile ? 4 : 8,
                            fontSize: isMobile ? 10 : 12,
                            color: avgAuctionPremium >= 0 ? '#f5222d' : '#52c41a',
                            cursor: 'pointer',
                            textDecoration: 'underline'
                          }}
                          onClick={() => {
                            setSelectedContinuousDays(height);
                            setPremiumTrendType('auction');
                            setPremiumTrendVisible(true);
                          }}
                        >
                          竞{avgAuctionPremium >= 0 ? '+' : ''}{avgAuctionPremium.toFixed(2)}%
                        </span>
                      )}
                    </span>
                    <span style={{ display: 'flex', alignItems: 'center' }}>
                      {avgChangePercent !== null && !isNaN(avgChangePercent) && (
                        <span
                          style={{
                            marginRight: isMobile ? 2 : 6,
                            fontSize: isMobile ? 10 : 12,
                            color: avgChangePercent >= 0 ? '#f5222d' : '#52c41a',
                            cursor: 'pointer',
                            textDecoration: 'underline'
                          }}
                          onClick={() => {
                            setSelectedContinuousDays(height);
                            setPremiumTrendType('premium');
                            setPremiumTrendVisible(true);
                          }}
                        >
                          溢{avgChangePercent >= 0 ? '+' : ''}{avgChangePercent.toFixed(2)}%
                        </span>
                      )}
                      <ArrowRightOutlined style={{ fontSize: isMobile ? 12 : 14, color: '#52c41a' }} />
                    </span>
                  </div>
                  {yesterdayStocks.length > 0 ? (
                    <div style={{ display: 'grid', gridTemplateColumns: isMobile ? 'repeat(2, 1fr)' : 'repeat(3, 1fr)', gap: 8 }}>
                      {yesterdayStocks.map(stock => renderStockCard(stock, false, false, comparisonData.yesterday.date.replace(/-/g, ''), height))}
                    </div>
                  ) : (
                    <div style={{ 
                      padding: isMobile ? '8px' : '10px', 
                      textAlign: 'center', 
                      color: '#999',
                      fontSize: isMobile ? 11 : 12,
                      background: '#f5f5f5',
                      borderRadius: 4
                    }}>
                      暂无股票
                    </div>
                  )}
                </div>
                <div>
                  <div style={{ 
                    background: '#e6f7ff',
                    padding: isMobile ? '5px 10px' : '6px 12px',
                    borderRadius: 4,
                    marginBottom: 8,
                    fontWeight: 'bold',
                    fontSize: isMobile ? 12 : 13,
                    color: '#1890ff',
                    minHeight: isMobile ? 26 : 28,
                    display: 'flex',
                    alignItems: 'center'
                  }}>
                    {nextHeight}连板 ({promotedStocks.length}只)
                  </div>
                  {promotedStocks.length > 0 ? (
                    <div style={{ display: 'grid', gridTemplateColumns: isMobile ? 'repeat(2, 1fr)' : 'repeat(3, 1fr)', gap: 8 }}>
                      {promotedStocks.map(stock => renderStockCard(stock, true, true, comparisonData.today.date.replace(/-/g, ''), nextHeight))}
                    </div>
                  ) : (
                    <div style={{ 
                      padding: isMobile ? '8px' : '10px', 
                      textAlign: 'center', 
                      color: '#999',
                      fontSize: isMobile ? 11 : 12,
                      background: '#f5f5f5',
                      borderRadius: 4
                    }}>
                      暂无股票
                    </div>
                  )}
                </div>
              </div>
            );
          })}

          {showFirstBoardProp && firstBoardStocks.length > 0 && (
            <div style={{ marginTop: isMobile ? 12 : 24 }}>
              <div style={{ 
                background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                color: '#fff',
                padding: isMobile ? '10px 12px' : '12px 16px',
                borderRadius: 8,
                fontWeight: 'bold',
                fontSize: isMobile ? 13 : 14,
                marginBottom: 12
              }}>
                今日首板 ({firstBoardStocks.length}只)
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: isMobile ? 'repeat(4, 1fr)' : 'repeat(6, 1fr)', gap: isMobile ? 4 : 8 }}>
                {firstBoardStocks.map(stock => (
                  <div
                    key={stock.code}
                    style={{
                      padding: isMobile ? '3px 4px' : '8px 12px',
                      background: '#fafafa',
                      borderRadius: 6,
                      border: '1px solid #e8e8e8',
                      transition: 'all 0.3s',
                      cursor: 'pointer'
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.boxShadow = '0 2px 8px rgba(0,0,0,0.15)';
                      e.currentTarget.style.transform = 'translateY(-2px)';
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.boxShadow = 'none';
                      e.currentTarget.style.transform = 'translateY(0)';
                    }}
                    onClick={() => {
                      setSelectedStock(stock);
                      setKlineVisible(true);
                    }}
                  >
                    <div style={{ display: 'flex', flexDirection: 'column', gap: isMobile ? 1 : 4 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: isMobile ? 2 : 4, justifyContent: 'center' }}>
                        <span style={{ fontWeight: 'bold', fontSize: isMobile ? 10 : 13, color: '#1890ff' }}>
                          {stock.name}
                        </span>
                        <span style={{ color: '#999', fontSize: isMobile ? 8 : 11 }}>
                          {stock.code}
                        </span>
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: isMobile ? 2 : 4 }}>
                        {stock.change_percent !== null && stock.change_percent !== undefined && (
                          <div style={{ 
                            fontSize: isMobile ? 10 : 12, 
                            fontWeight: 'bold',
                            color: stock.change_percent >= 0 ? '#f5222d' : '#52c41a'
                          }}>
                            {stock.change_percent >= 0 ? '+' : ''}{stock.change_percent.toFixed(2)}%
                          </div>
                        )}
                        <div 
                          id={`ai-analysis-btn-${stock.code}`}
                          style={{ 
                            display: 'inline-flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            width: isMobile ? 16 : 20,
                            height: isMobile ? 16 : 20,
                            borderRadius: 3,
                            background: completedAnalysis.has(`${stock.code}_${comparisonData.today.date.replace(/-/g, '')}`) ? '#52c41a' : 
                                        analyzingStocks.has(`${stock.code}_${comparisonData.today.date.replace(/-/g, '')}`) ? '#fa8c16' : '#722ed1',
                            cursor: 'pointer'
                          }}
                          onClick={(e) => {
                            e.stopPropagation();
                            handleAnalysisClick(stock, comparisonData.today.date.replace(/-/g, ''));
                          }}
                        >
                          <RobotOutlined style={{ fontSize: isMobile ? 9 : 11, color: '#fff' }} />
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    );
  };

  const aiKeywordLoadedRef = useRef('');

  const handleAiAnalyze = useCallback(async () => {
    setAiKeywordLoading(true);
    try {
      const response = await stockApi.analyzeKeywords({
        date: currentDate,
        keywords: keywordStats,
        force_refresh: true
      });
      if (response.data.success) {
        setAiKeywordResult(response.data.data);
        message.success('AI 分析完成');
      } else {
        message.error(response.data.error || '分析失败');
      }
    } catch (error) {
      message.error('分析失败：' + (error.response?.data?.error || error.message));
    } finally {
      setAiKeywordLoading(false);
    }
  }, [currentDate, keywordStats]);

  const loadAiCache = useCallback(async () => {
    if (aiKeywordLoadedRef.current === currentDate) return;
    aiKeywordLoadedRef.current = currentDate;
    setAiKeywordLoading(true);
    try {
      const response = await stockApi.getKeywordAnalysis(currentDate);
      if (response.data.success && response.data.data) {
        setAiKeywordResult(response.data.data);
      } else {
        setAiKeywordResult(null);
      }
    } catch (error) {
      message.error('加载失败：' + (error.response?.data?.error || error.message));
    } finally {
      setAiKeywordLoading(false);
    }
  }, [currentDate]);

  // 切换日期时清空旧结果，重置加载标记，并自动读取缓存（不触发 AI 分析）
  useEffect(() => {
    setAiKeywordResult(null);
    aiKeywordLoadedRef.current = '';
    loadAiCache();
  }, [currentDate, loadAiCache]);

  // 打开弹窗时：若当前日期无缓存结果，自动触发 AI 分析
  useEffect(() => {
    if (aiKeywordModalVisible && !aiKeywordResult) {
      handleAiAnalyze();
    }
  }, [aiKeywordModalVisible, aiKeywordResult, handleAiAnalyze]);

  const renderAiKeywordModal = () => {
    if (!aiKeywordModalVisible) return null;

    const mergedKeywords = aiKeywordResult?.merged_keywords || [];
    const analysisText = aiKeywordResult?.analysis_text || '';

    return (
      <Modal
        title={
          <Space>
            <span>涨停关键词 AI 分析</span>
            <Tag color="blue">
              {currentDate ? dayjs(currentDate, 'YYYYMMDD').format('MM月DD日') : ''}
            </Tag>
          </Space>
        }
        open={aiKeywordModalVisible}
        onCancel={() => {
          setAiKeywordModalVisible(false);
        }}
        width={isMobile ? '95%' : 800}
        footer={null}
        centered
        styles={{ body: { maxHeight: '70vh', overflow: 'auto' } }}
        destroyOnClose
      >
        <Spin spinning={aiKeywordLoading && mergedKeywords.length > 0}>
          {mergedKeywords.length > 0 ? (
            <>
              <div style={{ marginBottom: 16 }}>
                <div style={{ fontWeight: 600, marginBottom: 8, fontSize: 14 }}>
                  题材归类结果（按强度降序）
                </div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                  {mergedKeywords.map((item, idx) => {
                    const isSelected = selectedKeyword === item.keyword;
                    return (
                      <Tooltip
                        key={item.keyword}
                        title={item.source ? `合并自：${item.source.join('、')}` : ''}
                      >
                        <Tag
                          color={isSelected ? 'red' : (TREND_TAG_COLORS[item.trend] || (idx < 3 ? 'red' : idx < 6 ? 'orange' : 'blue'))}
                          style={{
                            fontSize: isMobile ? 12 : 13,
                            padding: isMobile ? '1px 6px' : '2px 8px',
                            cursor: 'pointer',
                            fontWeight: isSelected ? 'bold' : 'normal',
                            borderWidth: isSelected ? 2 : 1,
                            borderColor: isSelected ? '#f5222d' : undefined
                          }}
                          onClick={() => {
                            setSelectedKeyword(isSelected ? '' : item.keyword);
                          }}
                        >
                          {item.keyword}
                          <Badge
                            count={item.count}
                            style={{ backgroundColor: TREND_BADGE_COLORS[item.trend] || (idx < 3 ? '#cf1322' : idx < 6 ? '#d46b08' : '#1890ff'), marginLeft: 6 }}
                            overflowCount={999}
                          />
                        </Tag>
                      </Tooltip>
                    );
                  })}
                </div>
              </div>

              {analysisText && (
                <div style={{
                  background: '#fafafa',
                  padding: 12,
                  borderRadius: 6,
                  fontSize: 13,
                  lineHeight: 1.8,
                  color: '#333',
                  whiteSpace: 'pre-wrap',
                  marginBottom: 16
                }}>
                  {analysisText}
                </div>
              )}

              <div style={{ textAlign: 'center' }}>
                <Button
                  type="primary"
                  icon={<ReloadOutlined />}
                  onClick={handleAiAnalyze}
                >
                  重新 AI 分析
                </Button>
              </div>
            </>
          ) : aiKeywordLoading ? (
            <div style={{ textAlign: 'center', padding: '60px 0' }}>
              <Spin size="large" />
              <div style={{ marginTop: 12, color: '#8c8c8c', fontSize: 13 }}>AI 分析中，请稍候...</div>
            </div>
          ) : (
            <div style={{ textAlign: 'center', padding: 24 }}>
              <Button
                type="primary"
                size="large"
                onClick={handleAiAnalyze}
              >
                开始 AI 分析
              </Button>
            </div>
          )}
        </Spin>
      </Modal>
    );
  };

  return (
    <>
      <MarketAlertBar />
      {showAnnouncement && (
        <div
          style={{
            position: 'fixed',
            top: isMobile ? 46 : 64,
            left: isMobile ? 0 : 200,
            right: 0,
            zIndex: 98,
            background: 'linear-gradient(90deg, #52c41a 0%, #389e0d 100%)',
            color: '#fff',
            cursor: 'pointer',
            boxShadow: '0 2px 12px rgba(0, 0, 0, 0.3)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '8px 16px',
            fontSize: isMobile ? 12 : 14,
          }}
          onClick={() => { localStorage.setItem('announcement_dismissed', '1'); setShowAnnouncement(false); }}
        >
          <MailOutlined style={{ marginRight: 8, fontSize: isMobile ? 14 : 16 }} />
          <span>涨停梯队AI分析支持一键发送报告到邮箱啦！</span>
          <button
            style={{
              position: 'absolute',
              right: 16,
              background: 'rgba(255,255,255,0.2)',
              border: 'none',
              color: '#fff',
              cursor: 'pointer',
              fontSize: 12,
              padding: '2px 8px',
              borderRadius: 4,
            }}
            onClick={(e) => {
              e.stopPropagation();
              localStorage.setItem('announcement_dismissed', '1');
              setShowAnnouncement(false);
            }}
          >
            知道了
          </button>
        </div>
      )}
      {mode === 'comparison' ? (
        renderComparisonContent()
      ) : (
        <>
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
              {renderStatistics()}
              <div style={{ marginTop: isMobile ? 12 : 24 }}>
                {renderLadderTitle()}
                {renderLadder()}
              </div>
            </>
          )}
        </>
      )}
      
      {wencaiVisible && (
        <WencaiAssistant
          visible={wencaiVisible}
          onClose={() => setWencaiVisible(false)}
          dateStr={currentDate}
          type="breakout"
          nextDayBlocks={blockStrengthData.tomorrow?.blocks || []}
          enableBlur={enableBlur}
        />
      )}
      
      {blockStrengthVisible && (
        <BlockStrengthModal
          visible={blockStrengthVisible}
          onClose={() => setBlockStrengthVisible(false)}
          date={currentDate}
        />
      )}
      
      {renderAiKeywordModal()}
      
      <StockKlineModal
        visible={klineVisible}
        stockCode={selectedStock?.code}
        stockName={selectedStock?.name}
        targetDate={currentDate}
        onClose={() => {
          setKlineVisible(false);
          setSelectedStock(null);
        }}
      />
      
      <StockAnalysisModal
        visible={analysisVisible}
        stockCode={analysisStock?.code}
        stockName={analysisStock?.name}
        tradeDate={analysisDate}
        analysisData={analysisDate && analysisStock ? completedAnalysis.get(`${analysisStock.code}_${analysisDate}`) : null}
        onClose={() => {
          setAnalysisVisible(false);
          setAnalysisStock(null);
          setAnalysisDate(null);
        }}
      />
      
      <PremiumTrendModal
        visible={premiumTrendVisible}
        continuousDays={selectedContinuousDays}
        date={comparisonData?.today?.date?.replace(/-/g, '')}
        type={premiumTrendType}
        onClose={() => {
          setPremiumTrendVisible(false);
          setSelectedContinuousDays(null);
        }}
      />
      
      <ComparableStockModal
        visible={comparableVisible}
        stockCode={comparableStock?.code}
        stockName={comparableStock?.name}
        block={comparableStock?.block}
        limitUpReason={comparableStock?.limit_up_reason}
        dateStr={comparableDate}
        onClose={() => {
          setComparableVisible(false);
          setComparableStock(null);
          setComparableDate(null);
        }}
      />
    </>
  );
};

export default LadderPage;