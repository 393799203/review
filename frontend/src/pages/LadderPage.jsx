import { useState, useEffect, useRef } from 'react';
import { Card, Row, Col, Tag, Spin, message, Tooltip, Button, Modal, Badge, Select } from 'antd';
import { EditOutlined, DiffOutlined, RobotOutlined } from '@ant-design/icons';
import { stockApi } from '../services/api';
import { useGlobal } from '../contexts/GlobalContext';
import WencaiAssistant from '../components/WencaiAssistant';
import BlockStrengthModal from '../components/BlockStrengthModal';
import EditBlockModal from '../components/EditBlockModal';
import StockKlineModal from '../components/StockKlineModal';
import StockAnalysisModal from '../components/StockAnalysisModal';
import axios from 'axios';

const LadderPage = () => {
  const { currentDate, loading, setLoading, refreshKey, autoRefresh, showFirstBoard } = useGlobal();
  const showFirstBoardProp = showFirstBoard;
  const [ladderData, setLadderData] = useState([]);
  const [statistics, setStatistics] = useState({});
  const [yesterdayData, setYesterdayData] = useState(null);
  const [nextDayBlocks, setNextDayBlocks] = useState([]);
  const [nextDayDate, setNextDayDate] = useState(null);
  const [selectedBlocks, setSelectedBlocks] = useState([]);
  const [previousSelectedBlocks, setPreviousSelectedBlocks] = useState([]);
  const [isMobile, setIsMobile] = useState(false);
  const [wencaiVisible, setWencaiVisible] = useState(false);
  const [blockStrengthVisible, setBlockStrengthVisible] = useState(false);
  const [editBlockVisible, setEditBlockVisible] = useState(false);
  const [editingStock, setEditingStock] = useState(null);
  const [klineVisible, setKlineVisible] = useState(false);
  const [selectedStock, setSelectedStock] = useState(null);

  const [previousStocks, setPreviousStocks] = useState([]);
  const [diffVisible, setDiffVisible] = useState(false);
  const [diffData, setDiffData] = useState({ added: [], removed: [] });

  const [analysisVisible, setAnalysisVisible] = useState(false);
  const [analysisStock, setAnalysisStock] = useState(null);

  const [blockFilterDay, setBlockFilterDay] = useState('today');
  const [blockStrengthData, setBlockStrengthData] = useState({});
  
  const lastDateRef = useRef('');
  const previousStocksRef = useRef([]);

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
      if (lastDateRef.current && lastDateRef.current !== currentDate) {
        setDiffData({ added: [], removed: [] });
        previousStocksRef.current = [];
        setPreviousStocks([]);
      }
      lastDateRef.current = currentDate;
      loadData(currentDate);
      loadBlockStrengthData();
    }
  }, [currentDate, refreshKey]);

  const loadBlockStrengthData = async () => {
    try {
      const isDev = import.meta.env.DEV;
      const API_BASE = isDev ? 'http://localhost:5001/api' : '/api';
      const response = await axios.get(`${API_BASE}/block-strength/continuous?date=${currentDate}`);
      if (response.data.success) {
        setBlockStrengthData(response.data.data);
        setSelectedBlocks([]);
      }
    } catch (error) {
      console.error('加载板块强度数据失败:', error);
    }
  };

  useEffect(() => {
    if (currentDate) {
      loadBlockStrengthData();
    }
  }, [blockFilterDay]);

  const loadData = async (dateStr) => {
    try {
      setLoading(true);
      const response = await stockApi.getDataByDate(dateStr);

      if (response.data.success) {
        const data = response.data.data;
        
        const currentStocks = [];
        data.ladder.forEach(item => {
          item.stocks.forEach(stock => {
            currentStocks.push({
              code: stock.code,
              name: stock.name,
              level: item.level,
              limitUpTime: stock.limit_up_time,
            });
          });
        });
        
        if (lastDateRef.current === dateStr && previousStocksRef.current.length > 0) {
          const previousCodes = new Set(previousStocksRef.current.map(s => s.code));
          const currentCodes = new Set(currentStocks.map(s => s.code));
          
          const added = currentStocks.filter(s => !previousCodes.has(s.code));
          
          const removed = previousStocksRef.current.filter(s => !currentCodes.has(s.code));
          
          if (added.length > 0 || removed.length > 0) {
            setDiffData(prev => {
              const existingAddedCodes = new Set(prev.added.map(s => s.code));
              const existingRemovedCodes = new Set(prev.removed.map(s => s.code));
              
              const newAdded = added.filter(s => !existingAddedCodes.has(s.code));
              const newRemoved = removed.filter(s => !existingRemovedCodes.has(s.code));
              
              return {
                added: [...prev.added, ...newAdded],
                removed: [...prev.removed, ...newRemoved],
              };
            });
          }
        }
        
        setLadderData(data.ladder);
        setStatistics(data.statistics);
        setYesterdayData(data.yesterday);
        setNextDayBlocks(data.next_day_blocks || []);
        setNextDayDate(data.next_day_date || null);
        previousStocksRef.current = currentStocks;
        setPreviousStocks(currentStocks);
      } else {
        const errorMsg = response.data.error || '加载数据失败';
        message.error(errorMsg);
        setLadderData([]);
        setStatistics({});
        setYesterdayData(null);
        setNextDayBlocks([]);
        setNextDayDate(null);
      }
    } catch (error) {
      const errorMsg = error.response?.data?.error || error.message || '加载数据失败';
      message.error(errorMsg);
      setLadderData([]);
      setStatistics({});
      setYesterdayData(null);
      setNextDayBlocks([]);
      setNextDayDate(null);
    } finally {
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
    const displayReasons = reasons.slice(0, isMobile ? 3 : 5);
    const hasMore = reasons.length > (isMobile ? 3 : 5);
    
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
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <div style={{ flex: 1 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 4, marginBottom: 4, flexWrap: 'wrap' }}>
                <span 
                  style={{ fontWeight: 'bold', fontSize: 14, color: '#1890ff', cursor: 'pointer' }}
                  onClick={() => {
                    setSelectedStock({ code: stock.code, name: stock.name });
                    setKlineVisible(true);
                  }}
                >
                  {stock.code}
                </span>
                <span 
                  style={{ fontWeight: 'bold', fontSize: 14, color: '#262626', cursor: 'pointer' }}
                  onClick={() => {
                    setSelectedStock({ code: stock.code, name: stock.name });
                    setKlineVisible(true);
                  }}
                >
                  {stock.name}
                </span>
                  {stock.limit_up_type && (
                    <Tag color={getLimitUpTypeColor(stock.limit_up_type)} style={{ fontSize: 10, margin: 0, padding: '0 4px' }}>{stock.limit_up_type}</Tag>
                  )}
                  {stock.high_days && stock.high_days !== '首板' && (
                    <Tag color={getHighDaysColor(stock.high_days)} style={{ fontSize: 10, margin: 0, padding: '0 4px' }}>{stock.high_days}</Tag>
                  )}
                  <div 
                    style={{ 
                      display: 'inline-flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      width: 20,
                      height: 20,
                      borderRadius: '50%',
                      background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                      cursor: 'pointer',
                      marginLeft: 4
                    }}
                    onClick={(e) => {
                      e.stopPropagation();
                      setAnalysisStock({ code: stock.code, name: stock.name });
                      setAnalysisVisible(true);
                    }}
                  >
                    <RobotOutlined style={{ fontSize: 11, color: '#fff' }} />
                  </div>
                </div>
                <div style={{ fontSize: 11, color: '#666', marginBottom: 4 }}>
                  涨停: {stock.limit_up_time || '-'} | 封单: {(stock.seal_amount_wan / 10000).toFixed(2)}亿
                </div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                  {displayReasons.map((reason, index) => (
                    <Tag key={index} color="blue" style={{ fontSize: 10, marginBottom: 0 }}>
                      {reason.trim()}
                    </Tag>
                  ))}
                  {hasMore && (
                    <Tag color="default" style={{ fontSize: 10, marginBottom: 0 }}>
                      +{reasons.length - 3}
                    </Tag>
                  )}
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
                      ) : ''
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
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
                <span 
                  style={{ fontWeight: 'bold', fontSize: 14, color: '#1890ff', cursor: 'pointer' }}
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
              <div style={{ fontSize: 15, fontWeight: 'bold', color: '#262626', marginBottom: 4, display: 'flex', alignItems: 'center', gap: 6 }}>
                {stock.name}
                <div 
                  style={{ 
                    display: 'inline-flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    width: 20,
                    height: 20,
                    borderRadius: '50%',
                    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                    cursor: 'pointer'
                  }}
                  onClick={(e) => {
                    e.stopPropagation();
                    setAnalysisStock({ code: stock.code, name: stock.name });
                    setAnalysisVisible(true);
                  }}
                >
                  <RobotOutlined style={{ fontSize: 11, color: '#fff' }} />
                </div>
              </div>
              <div style={{ fontSize: 11, color: '#666' }}>
                <strong>涨停:</strong> {stock.limit_up_time || '-'} | <strong>封单:</strong> {(stock.seal_amount_wan / 10000).toFixed(2)}亿
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
                    ) : ''
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
            {displayReasons.map((reason, index) => (
              <Tooltip 
                key={index} 
                title={
                  hasDetailReason ? (
                    <div style={{ whiteSpace: 'pre-wrap' }}>
                      {filterDisclaimer(stock.detail_reason)}
                    </div>
                  ) : ''
                } 
                placement="top"
                styles={{ root: { maxWidth: '500px' } }}
              >
                <Tag color="blue" style={{ marginBottom: 4, fontSize: 11, cursor: hasDetailReason ? 'help' : 'default' }}>
                  {reason.trim()}
                </Tag>
              </Tooltip>
            ))}
            {hasMore && (
              <Tag color="default" style={{ marginBottom: 4, fontSize: 11 }}>
                +{reasons.length - 5}
              </Tag>
            )}
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
        ? item.stocks.filter(stock => selectedBlocks.includes(stock.block_name))
        : item.stocks;
      
      // 按照涨停时间排序（时间早的排在前面）
      const sortedStocks = [...filteredStocks].sort((a, b) => {
        if (!a.limit_up_time && !b.limit_up_time) return 0;
        if (!a.limit_up_time) return 1;
        if (!b.limit_up_time) return -1;
        return a.limit_up_time.localeCompare(b.limit_up_time);
      });
      
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
            {broken && (
              <Tag color="red" style={{ margin: 0 }}>断板日</Tag>
            )}
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
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
            {['yesterday', 'today', 'tomorrow'].map((day) => {
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

  return (
    <>
      <Spin spinning={loading}>
        {renderStatistics()}
        <div style={{ marginTop: isMobile ? 12 : 24 }}>
          {renderLadderTitle()}
          {renderLadder()}
        </div>
      </Spin>
      
      {wencaiVisible && (
        <WencaiAssistant
          visible={wencaiVisible}
          onClose={() => setWencaiVisible(false)}
          dateStr={currentDate}
          type="breakout"
          nextDayBlocks={nextDayBlocks}
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
        onClose={() => {
          setAnalysisVisible(false);
          setAnalysisStock(null);
        }}
      />
      
      <Modal
        title="刷新对比结果"
        open={diffVisible}
        onCancel={() => setDiffVisible(false)}
        footer={
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <Button onClick={() => setDiffData({ added: [], removed: [] })}>
              清空记录
            </Button>
            <Button type="primary" onClick={() => setDiffVisible(false)}>
              关闭
            </Button>
          </div>
        }
        width={800}
      >
        <div>
          {diffData.added.length > 0 && (
            <div style={{ marginBottom: 16 }}>
              <h4 style={{ color: '#52c41a', marginBottom: 8 }}>
                新增股票 ({diffData.added.length}只)
              </h4>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                {diffData.added.map((stock, index) => (
                  <Tag key={index} color="green">
                    {stock.code.split('.')[0]} {stock.name} ({stock.level}连板)
                  </Tag>
                ))}
              </div>
            </div>
          )}
          
          {diffData.removed.length > 0 && (
            <div>
              <h4 style={{ color: '#ff4d4f', marginBottom: 8 }}>
                减少股票 ({diffData.removed.length}只)
              </h4>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                {diffData.removed.map((stock, index) => (
                  <Tag key={index} color="red">
                    {stock.code.split('.')[0]} {stock.name} ({stock.level}连板)
                  </Tag>
                ))}
              </div>
            </div>
          )}
          
          {diffData.added.length === 0 && diffData.removed.length === 0 && (
            <div style={{ textAlign: 'center', color: '#8c8c8c', padding: 20 }}>
              暂无变化
            </div>
          )}
        </div>
      </Modal>
      
      {autoRefresh && (
        <div
          style={{
            position: 'fixed',
            right: 16,
            bottom: 16,
            zIndex: 1000,
          }}
        >
          <Badge count={diffData.added.length + diffData.removed.length} showZero={false}>
            <Button
              type="primary"
              shape="circle"
              size="large"
              icon={<DiffOutlined />}
              onClick={() => setDiffVisible(true)}
              style={{ width: 56, height: 56 }}
            />
          </Badge>
        </div>
      )}
    </>
  );
};

export default LadderPage;