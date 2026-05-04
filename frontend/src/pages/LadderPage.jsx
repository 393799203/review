import { useState, useEffect } from 'react';
import { Card, Row, Col, Tag, Spin, message, Tooltip, Button } from 'antd';
import { EditOutlined } from '@ant-design/icons';
import { stockApi } from '../services/api';
import { useGlobal } from '../contexts/GlobalContext';
import WencaiAssistant from '../components/WencaiAssistant';
import BlockStrengthModal from '../components/BlockStrengthModal';
import EditBlockModal from '../components/EditBlockModal';

const LadderPage = ({ showFirstBoard }) => {
  const { currentDate, loading, setLoading } = useGlobal();
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
      loadData(currentDate);
    }
  }, [currentDate]);

  const loadData = async (dateStr) => {
    try {
      setLoading(true);
      const response = await stockApi.getDataByDate(dateStr);

      if (response.data.success) {
        const data = response.data.data;
        setLadderData(data.ladder);
        setStatistics(data.statistics);
        setYesterdayData(data.yesterday);
        setNextDayBlocks(data.next_day_blocks || []);
        setNextDayDate(data.next_day_date || null);
        
        // 判断是否是断板日
        const isBroken = data.yesterday && data.ladder && data.ladder.length > 0;
        if (isBroken) {
          const todayMaxLevel = Math.max(...data.ladder.map(item => item.level));
          const expectedLevel = data.yesterday.max_level + 1;
          const isBrokenDay = todayMaxLevel !== expectedLevel;
          
          // 如果是断板日，默认选中所有板块；否则选中"全部"
          if (isBrokenDay && data.next_day_blocks && data.next_day_blocks.length > 0) {
            setSelectedBlocks(data.next_day_blocks.map(b => b.block_name));
          } else {
            setSelectedBlocks([]);
          }
        } else {
          setSelectedBlocks([]);
        }
      } else {
        setLadderData([]);
        setStatistics({});
        setYesterdayData(null);
        setNextDayBlocks([]);
        setNextDayDate(null);
        setSelectedBlocks([]);
      }
    } catch (error) {
      message.error('加载数据失败');
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
                <span style={{ fontWeight: 'bold', fontSize: 14 }}>{stock.code}</span>
                <span style={{ fontWeight: 'bold', fontSize: 14, color: '#262626' }}>{stock.name}</span>
                  {stock.limit_up_type && (
                    <Tag color={getLimitUpTypeColor(stock.limit_up_type)} style={{ fontSize: 10, margin: 0, padding: '0 4px' }}>{stock.limit_up_type}</Tag>
                  )}
                  {stock.high_days && stock.high_days !== '首板' && (
                    <Tag color={getHighDaysColor(stock.high_days)} style={{ fontSize: 10, margin: 0, padding: '0 4px' }}>{stock.high_days}</Tag>
                  )}
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
                <span style={{ fontWeight: 'bold', fontSize: 14 }}>{stock.code}</span>
                {stock.limit_up_type && (
                  <Tag color={getLimitUpTypeColor(stock.limit_up_type)} style={{ fontSize: 10, margin: 0, padding: '0 4px' }}>{stock.limit_up_type}</Tag>
                )}
                {stock.high_days && stock.high_days !== '首板' && (
                  <Tag color={getHighDaysColor(stock.high_days)} style={{ fontSize: 10, margin: 0, padding: '0 4px' }}>{stock.high_days}</Tag>
                )}
              </div>
              <div style={{ fontSize: 15, fontWeight: 'bold', color: '#262626', marginBottom: 4 }}>{stock.name}</div>
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
      
      // 如果没有符合条件的股票，不显示这个梯队
      if (filteredStocks.length === 0) return null;
      
      return (
        <Card
          key={item.level}
          title={
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: isMobile ? 14 : 16, fontWeight: 'bold' }}>{item.label}</span>
              <Tag color="red">共 {filteredStocks.length} 只</Tag>
            </div>
          }
          style={{ marginBottom: isMobile ? 12 : 16 }}
          size={isMobile ? 'small' : 'medium'}
        >
          <Row gutter={[isMobile ? 8 : 12, isMobile ? 8 : 12]}>
            {filteredStocks.map(stock => renderStockCard(stock))}
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
                断板策略
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
    </>
  );
};

export default LadderPage;