import { useState, useEffect, useRef } from 'react';
import { Card, Row, Col, Tag, Spin, message, Tooltip, Button, Modal, Badge } from 'antd';
import { EditOutlined, DiffOutlined, RobotOutlined } from '@ant-design/icons';
import { stockApi } from '../services/api';
import { useGlobal } from '../contexts/GlobalContext';
import WencaiAssistant from '../components/WencaiAssistant';
import BlockStrengthModal from '../components/BlockStrengthModal';
import EditBlockModal from '../components/EditBlockModal';
import StockKlineModal from '../components/StockKlineModal';
import StockAnalysisModal from '../components/StockAnalysisModal';

const LadderPage = ({ showFirstBoard }) => {
  const { currentDate, loading, setLoading, refreshKey, autoRefresh } = useGlobal();
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
    }
  }, [currentDate, refreshKey]);

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
          
          console.log('之前的股票代码:', Array.from(previousCodes).slice(0, 10));
          console.log('当前的股票代码:', Array.from(currentCodes).slice(0, 10));
          
          const added = currentStocks.filter(s => !previousCodes.has(s.code));
          
          const removed = previousStocksRef.current.filter(s => !currentCodes.has(s.code));
          
          console.log('数据对比:', {
            之前股票数: previousStocksRef.current.length,
            当前股票数: currentStocks.length,
            新增: added.length,
            减少: removed.length,
            新增股票: added,
            减少股票: removed
          });
          
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
            console.log('检测到数据变化，已累积对比结果');
          } else {
            console.log('数据无变化');
            if (previousStocksRef.current.length !== currentStocks.length) {
              console.warn('警告：股票数量变化但未检测到新增或减少，可能是数据格式问题');
            }
          }
        } else {
          console.log('首次加载或日期切换，跳过对比');
        }
        
        setLadderData(data.ladder);
        setStatistics(data.statistics);
        setYesterdayData(data.yesterday);
        setNextDayBlocks(data.next_day_blocks || []);
        setNextDayDate(data.next_day_date || null);
        previousStocksRef.current = currentStocks;
        setPreviousStocks(currentStocks);
        
        const isBroken = data.yesterday && data.ladder && data.ladder.length > 0;
        if (isBroken) {
          const todayMaxLevel = Math.max(...data.ladder.map(item => item.level));
          const expectedLevel = data.yesterday.max_level + 1;
          const isBrokenDay = todayMaxLevel !== expectedLevel;
          
          if (isBrokenDay && data.next_day_blocks && data.next_day_blocks.length > 0) {
            setSelectedBlocks(data.next_day_blocks.map(b => b.block_name));
          } else {
            setSelectedBlocks([]);
          }
        } else {
          setSelectedBlocks([]);
        }
      } else {
        const errorMsg = response.data.error || '加载数据失败';
        message.error(errorMsg);
        setLadderData([]);
        setStatistics({});
        setYesterdayData(null);
        setNextDayBlocks([]);
        setNextDayDate(null);
        setSelectedBlocks([]);
      }
    } catch (error) {
      const errorMsg = error.response?.data?.error || error.message || '加载数据失败';
      message.error(errorMsg);
      setLadderData([]);
      setStatistics({});
      setYesterdayData(null);
      setNextDayBlocks([]);
      setNextDayDate(null);
      setSelectedBlocks([]);
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
    if (!blockName || !nextDayBlocks || nextDayBlocks.length === 0) return null;
    
    const blockRank = nextDayBlocks.find(b => b.block_name === blockName);
    if (!blockRank) return null;
    
    const colorMap = {
      1: '#f5222d',  // 第1名 - 红色
      2: '#fa8c16',  // 第2名 - 橙色
      3: '#faad14',  // 第3名 - 黄色
      4: '#52c41a',  // 第4名 - 绿色
      5: '#1890ff',  // 第5名 - 蓝色
    };
    
    return colorMap[blockRank.rank] || '#b37feb';  // 第6名及以后 - 淡紫色
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

    const displayLadder = showFirstBoard 
      ? ladderData 
      : ladderData.filter(item => item.level !== 1);

    return displayLadder.map(item => {
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
    const hasNextDayBlocks = nextDayBlocks && nextDayBlocks.length > 0;
    
    return (
      <div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: isMobile ? 8 : 12 }}>
          <h2 style={{ margin: 0, fontSize: isMobile ? 14 : 16 }}>🎯 涨停梯队</h2>
          <div style={{ display: 'flex', gap: 8 }}>
            {broken && (
              <Button 
                type="primary" 
                danger 
                size="small"
                onClick={() => setWencaiVisible(true)}
                style={{ fontSize: isMobile ? 12 : 14 }}
              >
                断板日选股
              </Button>
            )}
            {hasNextDayBlocks && (
              <Button 
                type="primary" 
                size="small"
                onClick={() => setBlockStrengthVisible(true)}
                style={{ fontSize: isMobile ? 12 : 14 }}
              >
                次日强势板块
              </Button>
            )}
          </div>
        </div>
        
        {hasNextDayBlocks && (
          <div style={{ marginBottom: isMobile ? 8 : 12, display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
            <span style={{ fontSize: isMobile ? 12 : 13, color: '#666' }}>次日强势板块：</span>
            <Tag 
              color={selectedBlocks.length === 0 ? 'blue' : 'default'}
              style={{ cursor: 'pointer', margin: 0 }}
              onClick={() => {
                if (selectedBlocks.length === 0) {
                  // 当前是"全部"状态，恢复上一次的选择
                  if (previousSelectedBlocks.length > 0) {
                    setSelectedBlocks(previousSelectedBlocks);
                    setPreviousSelectedBlocks([]);
                  }
                } else {
                  // 当前不是"全部"状态，保存当前选择并切换到"全部"
                  setPreviousSelectedBlocks(selectedBlocks);
                  setSelectedBlocks([]);
                }
              }}
            >
              全部
            </Tag>
            {(isMobile ? nextDayBlocks.slice(0, 5) : nextDayBlocks).map((block) => {
              const colorMap = {
                1: '#f5222d',  // 第1名 - 红色
                2: '#fa8c16',  // 第2名 - 橙色
                3: '#faad14',  // 第3名 - 黄色
                4: '#52c41a',  // 第4名 - 绿色
                5: '#1890ff',  // 第5名 - 蓝色
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
            {isMobile && nextDayBlocks.length > 5 && (
              <Tag 
                color={selectedBlocks.some(b => {
                  const otherBlocks = nextDayBlocks.slice(5);
                  return otherBlocks.some(ob => ob.block_name === b);
                }) ? '#b37feb' : 'default'}
                style={{ cursor: 'pointer', margin: 0 }}
                onClick={() => {
                  const otherBlocks = nextDayBlocks.slice(5);
                  const otherBlockNames = otherBlocks.map(b => b.block_name);
                  const hasOtherSelected = selectedBlocks.some(b => otherBlockNames.includes(b));
                  
                  if (hasOtherSelected) {
                    // 取消选中所有其他板块
                    setSelectedBlocks(selectedBlocks.filter(b => !otherBlockNames.includes(b)));
                  } else {
                    // 选中所有其他板块
                    setSelectedBlocks([...selectedBlocks, ...otherBlockNames]);
                  }
                }}
              >
                其他板块
              </Tag>
            )}
          </div>
        )}
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
          dateStr={nextDayDate || currentDate}
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
            left: 16,
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