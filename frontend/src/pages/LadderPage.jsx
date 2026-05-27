import React, { useState, useEffect, useRef, useMemo, useCallback, memo } from 'react';
import { Card, Row, Col, Tag, Spin, message, Tooltip, Button, Modal, Badge, Select, Table, Space, Statistic, Empty } from 'antd';
import { EditOutlined, DiffOutlined, RobotOutlined, LoadingOutlined, ArrowUpOutlined, ArrowDownOutlined, MinusOutlined, StockOutlined, RiseOutlined, FallOutlined, ArrowRightOutlined } from '@ant-design/icons';
import api, { stockApi } from '../services/api';
import { useGlobal } from '../contexts/GlobalContext';
import WencaiAssistant from '../components/WencaiAssistant';
import BlockStrengthModal from '../components/BlockStrengthModal';
import EditBlockModal from '../components/EditBlockModal';
import StockKlineModal from '../components/StockKlineModal';
import StockAnalysisModal from '../components/StockAnalysisModal';
import PremiumTrendModal from '../components/PremiumTrendModal';
import MarketAlertBar from '../components/MarketAlertBar';

const LadderPage = () => {
  const { currentDate, loading: globalLoading, setLoading: setGlobalLoading, refreshKey, autoRefresh, showFirstBoard, ladderMode, marketAlerts, setMarketAlerts } = useGlobal();
  const mode = ladderMode || 'ladder';
  const showFirstBoardProp = showFirstBoard;
  const [ladderData, setLadderData] = useState([]);
  const [statistics, setStatistics] = useState({});
  const [yesterdayData, setYesterdayData] = useState(null);
  const [selectedBlocks, setSelectedBlocks] = useState([]);
  const [previousSelectedBlocks, setPreviousSelectedBlocks] = useState([]);
  const [isMobile, setIsMobile] = useState(false);
  const [wencaiVisible, setWencaiVisible] = useState(false);
  const [blockStrengthVisible, setBlockStrengthVisible] = useState(false);
  const [editBlockVisible, setEditBlockVisible] = useState(false);
  const [editingStock, setEditingStock] = useState(null);
  const [klineVisible, setKlineVisible] = useState(false);
  const [selectedStock, setSelectedStock] = useState(null);

  const [analysisVisible, setAnalysisVisible] = useState(false);
  const [analysisStock, setAnalysisStock] = useState(null);
  const [analysisDate, setAnalysisDate] = useState(null);
  const [analyzingStocks, setAnalyzingStocks] = useState(new Set());
  const [completedAnalysis, setCompletedAnalysis] = useState(new Map());

  const [blockFilterDay, setBlockFilterDay] = useState('today');
  const [blockStrengthData, setBlockStrengthData] = useState({});
  const [enableBlur, setEnableBlur] = useState(false);
  const [isFirstLoad, setIsFirstLoad] = useState(true);
  const [loading, setLoading] = useState(true);
  
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

  const renderStockCard = (stock) => {
    const blockRankColor = getBlockRankColor(stock.block_name);
    
    const reasons = stock.reason ? stock.reason.split('+').filter(r => r.trim()) : ['未分类'];
    
    const hasDetailReason = stock.detail_reason && stock.detail_reason.trim();
    
    const filterDisclaimer = (text) => {
      if (!text) return '';
      return text.replace(/（免责声明：[^）]+）/g, '').trim();
    };

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
          }}
          styles={{ body: { padding: '8px 10px' } }}
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
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', overflow: 'visible' }}>
            <div style={{ flex: 1, minWidth: 0, overflow: 'visible' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 4, marginBottom: 4, flexWrap: 'nowrap', overflow: 'visible' }}>
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
              </div>
                <div style={{ fontSize: 11, color: '#666', marginBottom: 4 }}>
                  涨停: {stock.limit_up_time || '-'} | 封单: {(stock.seal_amount_wan / 10000).toFixed(2)}亿 | 换手: {stock.turnover_rate?.toFixed(2) || '-'}%
                </div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                  {reasons.map((reason, index) => (
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
                      styles={{ root: { maxWidth: '390px' } }}
                    >
                      <Tag 
                        color="blue" 
                        style={{ 
                          fontSize: 10, 
                          marginBottom: 0,
                          cursor: hasDetailReason ? 'pointer' : 'default'
                        }}
                      >
                        {reason.trim()}
                      </Tag>
                    </Tooltip>
                  ))}
                </div>
              </div>
              <div style={{ textAlign: 'right', marginLeft: 10 }}>
                <div style={{ fontSize: 14, fontWeight: 'bold', color: '#f5222d' }}>
                  +{stock.change_percent.toFixed(2)}%
                </div>
                {stock.limit_up_price > 0 && (
                  <div style={{ fontSize: 13, fontWeight: 'bold', color: '#f5222d' }}>¥{stock.limit_up_price.toFixed(2)}</div>
                )}
                {stock.block_name && (
                  <Tooltip 
                    title={
                      stock.block_info && Object.keys(stock.block_info).length > 0 ? (
                        <div>
                          <div>板块涨跌幅: {stock.block_info.change_rate.toFixed(2)}%</div>
                          <div>涨停家数: {stock.block_info.limit_up_num}</div>
                          <div>连板家数: {stock.block_info.continuous_num}</div>
                          {stock.block_info.high && <div>板块高度: {stock.block_info.high}</div>}
                          <div>上榜天数: {stock.block_info.list_days}</div>
                          {stock.block_info.high_stock_name && <div>连板龙头: {stock.block_info.high_stock_name}</div>}
                        </div>
                      ) : null
                    }
                    placement="left"
                  >
                    <Tag 
                      color="#722ed1" 
                      style={{ 
                        fontSize: 10, 
                        marginTop: 4, 
                        cursor: 'default',
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: 4
                      }}
                    >
                      {stock.block_name}
                      <EditOutlined 
                        style={{ fontSize: 10, cursor: 'pointer' }} 
                        onClick={(e) => {
                          e.stopPropagation();
                          setEditingStock(stock);
                          setEditBlockVisible(true);
                        }}
                      />
                    </Tag>
                  </Tooltip>
                )}
              </div>
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
              {stock.block_name && (
                <Tooltip 
                  title={
                    stock.block_info && Object.keys(stock.block_info).length > 0 ? (
                      <div>
                        <div>板块涨跌幅: {stock.block_info.change_rate.toFixed(2)}%</div>
                        <div>涨停家数: {stock.block_info.limit_up_num}</div>
                        <div>连板家数: {stock.block_info.continuous_num}</div>
                        {stock.block_info.high && <div>板块高度: {stock.block_info.high}</div>}
                        <div>上榜天数: {stock.block_info.list_days}</div>
                        {stock.block_info.high_stock_name && <div>连板龙头: {stock.block_info.high_stock_name}</div>}
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
                    {stock.block_name}
                    <EditOutlined 
                      style={{ fontSize: 10, cursor: 'pointer' }} 
                      onClick={(e) => {
                        e.stopPropagation();
                        setEditingStock(stock);
                        setEditBlockVisible(true);
                      }}
                    />
                  </Tag>
                </Tooltip>
              )}
            </div>
          </div>
          <div style={{ marginTop: 8 }}>
            {reasons.map((reason, index) => (
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
                <Tag color="blue" style={{ marginBottom: 4, fontSize: 11, cursor: hasDetailReason ? 'help' : 'default' }}>
                  {reason.trim()}
                </Tag>
              </Tooltip>
            ))}
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

      // 根据选中的板块过滤股票
      const filteredStocks = selectedBlocks.length > 0
        ? item.stocks.filter(stock => selectedBlocks.includes(stock.block_name) && stock.current_status === 'close')
        : item.stocks.filter(stock => stock.current_status === 'close');
      
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
            {sortedStocks.map(stock => renderStockCard(stock))}
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

    const renderStockCard = (stock, showYesterdayHeight = false, isRightColumn = false, tradeDate = null) => {
      const isPromoted = !isRightColumn && promotedHeights.some(height => {
        const stocks = promotedLadder[height] || [];
        return stocks.some(s => s.code === stock.code);
      });
      
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
                    {stocks.map(stock => renderStockCard(stock, showYesterdayHeight, isRightColumn))}
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
                      {yesterdayStocks.map(stock => renderStockCard(stock, false, false, comparisonData.yesterday.date.replace(/-/g, '')))}
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
                      {promotedStocks.map(stock => renderStockCard(stock, true, true, comparisonData.today.date.replace(/-/g, '')))}
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

  return (
    <>
      <MarketAlertBar />
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
      
      {editBlockVisible && editingStock && (
        <EditBlockModal
          visible={editBlockVisible}
          onClose={() => {
            setEditBlockVisible(false);
            setEditingStock(null);
          }}
          stockCode={editingStock.code}
          stockName={editingStock.name}
          currentBlock={editingStock.block_name}
          dateStr={currentDate}
          onSuccess={() => {
            loadData(currentDate);
          }}
        />
      )}
      
      <StockKlineModal
        visible={klineVisible}
        stockCode={selectedStock?.code}
        stockName={selectedStock?.name}
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
    </>
  );
};

export default LadderPage;