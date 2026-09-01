import React, { useState, useEffect, useMemo } from 'react';
import { Card, Table, Button, message, Spin, Popconfirm, Tag, Modal, InputNumber, Form, AutoComplete, Input, Checkbox } from 'antd';
import { DeleteOutlined, ShoppingCartOutlined, DollarOutlined, LoadingOutlined, RobotOutlined, ThunderboltOutlined, PlusOutlined, SearchOutlined, HeartOutlined, AlertOutlined } from '@ant-design/icons';
import api, { stockApi } from '../services/api';
import StockKlineModal from '../components/StockKlineModal';
import WatchlistAnalysisModal from '../components/WatchlistAnalysisModal';

const WatchlistPage = () => {
  const [watchlist, setWatchlist] = useState([]);
  const [isMobile, setIsMobile] = useState(false);
  const [buyModalVisible, setBuyModalVisible] = useState(false);
  const [sellModalVisible, setSellModalVisible] = useState(false);
  const [selectedStock, setSelectedStock] = useState(null);
  const [buyForm] = Form.useForm();
  const [sellForm] = Form.useForm();
  const [klineVisible, setKlineVisible] = useState(false);
  const [klineStock, setKlineStock] = useState(null);
  const [isFirstLoad, setIsFirstLoad] = useState(true);
  const [loading, setLoading] = useState(true);
  const [analysisStock, setAnalysisStock] = useState(null);
  const [analysisVisible, setAnalysisVisible] = useState(false);
  const [searchKeyword, setSearchKeyword] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [searching, setSearching] = useState(false);
  const [comfortModalVisible, setComfortModalVisible] = useState(false);
  const [comfortStock, setComfortStock] = useState(null);
  const [comfortLoading, setComfortLoading] = useState(false);
  const [comfortResult, setComfortResult] = useState('');
  const [analyzingStocks, setAnalyzingStocks] = useState(new Set());
  const [completedAnalysis, setCompletedAnalysis] = useState(new Map());
  const [selectedRowKeys, setSelectedRowKeys] = useState([]);
  const [alertModalVisible, setAlertModalVisible] = useState(false);
  const [alertStock, setAlertStock] = useState(null);
  const [alertForm] = Form.useForm();
  const [mobileSelectMode, setMobileSelectMode] = useState(false);
  const [mobileSelected, setMobileSelected] = useState(new Set());
  const [mobilePage, setMobilePage] = useState(1);
  const MOBILE_PAGE_SIZE = 20;

  // 告警判定：当日最低价低于预警价
  const isAlert = (record) => {
    if (record.day_low == null || record.alert_price == null) return false;
    return Number(record.day_low) < Number(record.alert_price);
  };

  // 排序：触发预警的股票置顶，其余保持原顺序
  const sortedWatchlist = useMemo(() => {
    const alerts = watchlist.filter(isAlert);
    const others = watchlist.filter((r) => !isAlert(r));
    return [...alerts, ...others];
  }, [watchlist]);

  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 768);
    };
    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  useEffect(() => {
    loadWatchlist();
  }, []);

  const loadWatchlist = async () => {
    setLoading(true);
    try {
      const response = await api.get('/watchlist');
      
      if (response.data.success) {
        setWatchlist(response.data.data || []);
        setMobilePage(1);
      } else {
        message.error('加载自选股失败');
      }
    } catch (error) {
      message.error('加载自选股失败：' + (error.response?.data?.error || error.message));
    } finally {
      setLoading(false);
      if (isFirstLoad) {
        setIsFirstLoad(false);
      }
    }
  };

  const handleDelete = async (stockCode) => {
    try {
      const response = await api.delete(`/watchlist/${stockCode}`);
      
      if (response.data.success) {
        message.success('删除成功');
        // 增量更新：本地移除，不整页刷新
        setWatchlist(prev => prev.filter(r => r.stock_code !== stockCode));
      } else {
        message.error(response.data.error || '删除失败');
      }
    } catch (error) {
      message.error('删除失败：' + (error.response?.data?.error || error.message));
    }
  };

  // 加入类型标签：策略加入的标签显示策略名，其他显示"手动"
  const renderAddType = (record) => {
    if (record.add_type === 'strategy') {
      return (
        <Tag color="orange" style={{ fontSize: 10, margin: 0, padding: '0 4px' }}>
          {record.add_reason || '策略'}
        </Tag>
      );
    }
    return (
      <Tag color="green" style={{ fontSize: 10, margin: 0, padding: '0 4px' }}>
        手动
      </Tag>
    );
  };

  // 策略日期（标签下方显示），非策略返回 null
  const renderStrategyInfo = (record) => {
    if (record.add_type !== 'strategy') return null;
    const dateStr = record.add_date
      ? `${record.add_date.slice(0, 4)}-${record.add_date.slice(4, 6)}-${record.add_date.slice(6, 8)}`
      : '';
    if (!dateStr) return null;
    return (
      <div style={{ fontSize: 11, color: '#666', lineHeight: 1.4, marginTop: 2 }}>
        {dateStr}
      </div>
    );
  };

  const handleAlertEdit = (stock) => {
    setAlertStock(stock);
    alertForm.setFieldsValue({
      alert_price: stock.alert_price,
    });
    setAlertModalVisible(true);
  };

  const handleAlertSubmit = async () => {
    try {
      const values = await alertForm.validateFields();
      const response = await stockApi.updateAlertPrice({
        stock_code: alertStock.stock_code,
        alert_price: values.alert_price ?? null,
      });
      
      if (response.data.success) {
        message.success(response.data.message || '预警价格已更新');
        setAlertModalVisible(false);
        alertForm.resetFields();
        // 本地更新预警价，不整页刷新
        setWatchlist(prev => prev.map(r =>
          r.stock_code === alertStock.stock_code
            ? { ...r, alert_price: values.alert_price ?? null }
            : r
        ));
      } else {
        message.error(response.data.error || '更新失败');
      }
    } catch (error) {
      message.error('更新失败：' + (error.response?.data?.error || error.message));
    }
  };

  const handleBatchDelete = async (stockCodes) => {
    if (!stockCodes || stockCodes.length === 0) {
      message.warning('请先勾选要删除的股票');
      return;
    }
    try {
      const response = await stockApi.batchDeleteWatchlist(stockCodes);
      if (response.data.success) {
        message.success(response.data.message || '删除成功');
        setSelectedRowKeys([]);
        setMobileSelected(new Set());
        setMobileSelectMode(false);
        // 增量更新：本地移除，不整页刷新
        const removed = new Set(stockCodes);
        setWatchlist(prev => prev.filter(r => !removed.has(r.stock_code)));
      } else {
        message.error(response.data.error || '删除失败');
      }
    } catch (error) {
      message.error('删除失败：' + (error.response?.data?.error || error.message));
    }
  };

  const handleBuy = (stock) => {
    setSelectedStock(stock);
    const buyPrice = stock.current_price || stock.add_price;
    // 计算10万金额对应的股数（100的整数倍）
    const defaultQuantity = Math.floor(100000 / buyPrice / 100) * 100;
    buyForm.setFieldsValue({
      buy_price: buyPrice,
      buy_quantity: defaultQuantity
    });
    setBuyModalVisible(true);
  };

  const handleSell = (stock) => {
    setSelectedStock(stock);
    sellForm.setFieldsValue({
      sell_price: stock.current_price,
      sell_quantity: stock.buy_quantity
    });
    setSellModalVisible(true);
  };

  const handleBuySubmit = async () => {
    try {
      const values = await buyForm.validateFields();
      const response = await stockApi.buyStock({
        stock_code: selectedStock.stock_code,
        buy_price: values.buy_price,
        buy_quantity: values.buy_quantity
      });
      
      if (response.data.success) {
        message.success(response.data.message);
        setBuyModalVisible(false);
        buyForm.resetFields();
        loadWatchlist();
      } else {
        message.error(response.data.error);
      }
    } catch (error) {
      message.error('买入失败：' + (error.response?.data?.error || error.message));
    }
  };

  const handleSellSubmit = async () => {
    try {
      const values = await sellForm.validateFields();
      const response = await stockApi.sellStock({
        stock_code: selectedStock.stock_code,
        sell_price: values.sell_price,
        sell_quantity: values.sell_quantity
      });
      
      if (response.data.success) {
        message.success(response.data.message);
        setSellModalVisible(false);
        sellForm.resetFields();
        loadWatchlist();
      } else {
        message.error(response.data.error);
      }
    } catch (error) {
      message.error('卖出失败：' + (error.response?.data?.error || error.message));
    }
  };

  const handleAIAnalyze = async (stock) => {
    const stockCode = stock.stock_code.split('.')[0];
    const analysisKey = stockCode;
    
    if (completedAnalysis.has(analysisKey)) {
      setAnalysisStock({ code: stockCode, name: stock.stock_name });
      setAnalysisVisible(true);
      return;
    }
    
    if (analyzingStocks.has(analysisKey)) {
      message.info('该股票正在分析中，请稍后...');
      return;
    }
    
    try {
      const checkResponse = await api.post('/stock/analyze', {
        stock_code: stockCode,
        stock_name: stock.stock_name,
        check_only: true
      }, { timeout: 5000 });
      
      if (checkResponse.data.success && checkResponse.data.has_cache) {
        setCompletedAnalysis(prev => new Map(prev).set(analysisKey, checkResponse.data.data));
        setAnalysisStock({ code: stockCode, name: stock.stock_name });
        setAnalysisVisible(true);
        return;
      }
    } catch (error) {
      console.error('检查缓存失败:', error);
    }
    
    setAnalyzingStocks(prev => new Set(prev).add(analysisKey));
    message.info(`开始分析 ${stock.stock_name}，分析时间可能较长，请稍后...`);
    
    try {
      const response = await api.post('/stock/analyze', {
        stock_code: stockCode,
        stock_name: stock.stock_name,
        force: false
      }, { timeout: 120000 });
      
      if (response.data.success) {
        setCompletedAnalysis(prev => new Map(prev).set(analysisKey, response.data.data));
        message.success(`${stock.stock_name} 分析完成，点击图标查看结果`);
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

  const handleSearchStock = async (value) => {
    setSearchKeyword(value);
    
    if (!value || value.trim().length === 0) {
      setSearchResults([]);
      return;
    }
    
    setSearching(true);
    try {
      const response = await api.get(`/stock/search?keyword=${encodeURIComponent(value.trim())}`);
      
      if (response.data.success) {
        setSearchResults(response.data.data || []);
      } else {
        message.error('搜索失败');
      }
    } catch (error) {
      message.error('搜索失败：' + (error.response?.data?.error || error.message));
    } finally {
      setSearching(false);
    }
  };

  const handleAddToWatchlist = async (stock) => {
    try {
      const today = new Date();
      const addDate = today.getFullYear().toString() + 
                      (today.getMonth() + 1).toString().padStart(2, '0') + 
                      today.getDate().toString().padStart(2, '0');
      
      let addPrice = null;
      try {
        const quoteResponse = await api.get(`/stock/quote/${stock.code}`);
        if (quoteResponse.data.success && quoteResponse.data.data) {
          addPrice = quoteResponse.data.data.price;
        }
      } catch (error) {
        console.warn('获取股票价格失败，将不设置加入价格:', error);
      }
      
      const response = await api.post('/watchlist', {
        stock_code: stock.code,
        stock_name: stock.name,
        add_date: addDate,
        add_price: addPrice,
        add_reason: '手动添加',
        add_type: 'manual'
      });
      
      if (response.data.success) {
        message.success(`${stock.name} 已添加到自选`);
        setSearchKeyword('');
        setSearchResults([]);
        loadWatchlist();
      } else {
        message.error(response.data.error || '添加失败');
      }
    } catch (error) {
      message.error('添加失败：' + (error.response?.data?.error || error.message));
    }
  };

  const handleComfort = async (stock) => {
    setComfortStock(stock);
    setComfortModalVisible(true);
    setComfortLoading(true);
    setComfortResult('');
    
    try {
      const response = await api.post('/stock/comfort', {
        stock_code: stock.stock_code,
        stock_name: stock.stock_name,
        buy_price: stock.buy_price,
        current_price: stock.current_price,
        position_profit: stock.position_profit,
        position_profit_ratio: stock.position_profit_ratio
      }, {
        timeout: 60000
      });
      
      if (response.data.success) {
        setComfortResult(response.data.data.analysis);
      } else {
        message.error(response.data.error || '安慰分析失败');
        setComfortModalVisible(false);
      }
    } catch (error) {
      message.error('安慰分析失败：' + (error.response?.data?.error || error.message));
      setComfortModalVisible(false);
    } finally {
      setComfortLoading(false);
    }
  };

  const renderMobileContent = () => {
    if (watchlist.length === 0 && !loading) {
      return (
        <div style={{ 
          textAlign: 'center', 
          padding: '40px 20px', 
          color: '#999',
          fontSize: 14 
        }}>
          暂无自选股
        </div>
      );
    }
    
    return (
      <div>
        {sortedWatchlist.slice(0, mobilePage * MOBILE_PAGE_SIZE).map((record) => {
          const isHolding = record.position_status === '持仓';
          const alertActive = isAlert(record);
          const positionProfit = record.position_profit !== null && record.position_profit !== undefined ? parseFloat(record.position_profit) : null;
          const positionProfitRatio = record.position_profit_ratio !== null && record.position_profit_ratio !== undefined ? parseFloat(record.position_profit_ratio) : null;
          const totalProfit = record.total_profit || 0;
          const totalProfitColor = totalProfit > 0 ? '#f5222d' : totalProfit < 0 ? '#52c41a' : '#8c8c8c';
          const profitColor = positionProfit !== null ? (positionProfit > 0 ? '#f5222d' : positionProfit < 0 ? '#52c41a' : '#8c8c8c') : '#8c8c8c';
          const profitPercent = positionProfitRatio !== null ? (positionProfitRatio * 100).toFixed(2) : '0.00';
          
          const addPriceChange = record.add_price && record.current_price 
            ? ((record.current_price - record.add_price) / record.add_price * 100) 
            : null;
          const addPriceChangeColor = addPriceChange !== null 
            ? (addPriceChange > 0 ? '#f5222d' : addPriceChange < 0 ? '#52c41a' : '#8c8c8c')
            : '#8c8c8c';
          
          const dayChangePct = record.day_change_pct !== null && record.day_change_pct !== undefined 
            ? parseFloat(record.day_change_pct) 
            : null;
          const dayChangeColor = dayChangePct !== null 
            ? (dayChangePct > 0 ? '#f5222d' : dayChangePct < 0 ? '#52c41a' : '#8c8c8c')
            : '#8c8c8c';
          
          const stockCode = record.stock_code.split('.')[0];
          const analysisKey = stockCode;
          const isAnalyzing = analyzingStocks.has(analysisKey);
          const isCompleted = completedAnalysis.has(analysisKey);
          
          return (
            <Card
              key={record.id}
              size="small"
              style={{ 
                marginBottom: 8,
                borderLeft: `3px solid ${alertActive ? '#faad14' : totalProfitColor}`,
                background: alertActive ? '#fff1f0' : `${totalProfitColor}08`,
                position: 'relative',
                overflow: 'hidden',
              }}
              styles={{ body: { padding: '8px 10px' } }}
            >
              {mobileSelectMode && (
                <Checkbox
                  checked={mobileSelected.has(record.stock_code)}
                  onChange={(e) => {
                    setMobileSelected((prev) => {
                      const next = new Set(prev);
                      if (e.target.checked) next.add(record.stock_code);
                      else next.delete(record.stock_code);
                      return next;
                    });
                  }}
                  style={{ position: 'absolute', top: 8, left: 8, zIndex: 10 }}
                />
              )}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div style={{ flex: 1 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4, height: 22 }}>
                    <span 
                      style={{ fontWeight: 'bold', fontSize: 14, color: '#1890ff', cursor: 'pointer' }}
                      onClick={() => {
                        setKlineStock({ code: record.stock_code.split('.')[0], name: record.stock_name, signalDate: record.signal_date || undefined });
                        setKlineVisible(true);
                      }}
                    >
                      {record.stock_code.split('.')[0]}
                    </span>
                    <span 
                      style={{ fontWeight: 'bold', fontSize: 14, color: '#262626', cursor: 'pointer' }}
                      onClick={() => {
                        setKlineStock({ code: record.stock_code.split('.')[0], name: record.stock_name, signalDate: record.signal_date || undefined });
                        setKlineVisible(true);
                      }}
                    >
                      {record.stock_name}
                    </span>
                    <Button
                      type="primary"
                      icon={<RobotOutlined />}
                      size="small"
                      onClick={() => handleAIAnalyze(record)}
                      style={{ 
                        background: isCompleted ? '#52c41a' : isAnalyzing ? '#fa8c16' : '#722ed1', 
                        borderColor: isCompleted ? '#52c41a' : isAnalyzing ? '#fa8c16' : '#722ed1', 
                        borderRadius: 3, 
                        padding: '0 6px', 
                        height: 18, 
                        minWidth: 18 
                      }}
                    />
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 4, height: 22 }}>
                    {alertActive && (
                      <Tag color="red" style={{ fontSize: 10, margin: 0, padding: '0 4px' }}>
                        告警
                      </Tag>
                    )}
                    {renderAddType(record)}
                    <Tag color="purple" style={{ fontSize: 10, margin: 0, padding: '0 4px' }}>
                      {record.add_date ? `${record.add_date.slice(4, 6)}-${record.add_date.slice(6, 8)}` : '-'}
                    </Tag>
                    <Tag
                      color={record.alert_price ? 'red' : 'default'}
                      icon={<AlertOutlined />}
                      style={{ fontSize: 10, margin: 0, padding: '0 4px', cursor: 'pointer' }}
                      onClick={() => handleAlertEdit(record)}
                    >
                      {record.alert_price ? `预警 ¥${Number(record.alert_price).toFixed(2)}` : '设预警'}
                    </Tag>
                  </div>
                </div>
                <div style={{ textAlign: 'right', marginLeft: 8, minWidth: 75 }}>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                    <div style={{ fontSize: 14, fontWeight: 'bold', color: totalProfitColor, height: 22, lineHeight: '22px' }}>
                      累计: {totalProfit.toFixed(0)}
                    </div>
                    {isHolding && positionProfit !== null && (
                      <div style={{ fontSize: 12, fontWeight: 'bold', color: profitColor, height: 22, lineHeight: '22px' }}>
                        盈亏: {positionProfit.toFixed(0)}
                        <span style={{ fontSize: 9, marginLeft: 2 }}>{positionProfitRatio > 0 ? '+' : ''}{profitPercent}%</span>
                      </div>
                    )}
                  </div>
                </div>
              </div>
              
              <div style={{ 
                display: 'flex', 
                justifyContent: 'space-between', 
                alignItems: 'center', 
                marginTop: 6,
                background: '#fafafa',
                borderRadius: 4,
                fontSize: 11,
                flexWrap: 'nowrap'
              }}>
                {isHolding ? (
                  <div style={{ whiteSpace: 'nowrap', flex: '0 0 auto' }}>
                    <span style={{ color: '#8c8c8c' }}>买入: </span>
                    <span style={{ fontWeight: 'bold', color: '#1890ff' }}>¥{record.buy_price ? record.buy_price.toFixed(2) : '-'}</span>
                    <span style={{ color: '#8c8c8c', marginLeft: 4 }}>×{record.buy_quantity}</span>
                  </div>
                ) : (
                  <div style={{ whiteSpace: 'nowrap', flex: '0 0 auto' }}>
                    <span style={{ color: '#8c8c8c' }}>加入: </span>
                    <span style={{ fontWeight: 'bold', color: '#262626' }}>¥{record.add_price ? record.add_price.toFixed(2) : '-'}</span>
                  </div>
                )}
                <div style={{ textAlign: 'right', whiteSpace: 'nowrap', flex: '1 1 auto' }}>
                  <span style={{ color: '#8c8c8c' }}>现价: </span>
                  <span style={{ fontWeight: 'bold', color: dayChangeColor }}>¥{record.current_price ? record.current_price.toFixed(2) : '-'}</span>
                  <span style={{ color: '#8c8c8c', marginLeft: 4 }}>最低: </span>
                  <span style={{ fontWeight: 'bold', color: alertActive ? '#fa8c16' : '#666' }}>
                    ¥{record.day_low ? record.day_low.toFixed(2) : '-'}
                  </span>
                  {dayChangePct !== null && (
                    <span style={{ fontWeight: 'bold', color: dayChangeColor, marginLeft: 4 }}>
                      ({dayChangePct > 0 ? '+' : ''}{dayChangePct.toFixed(2)}%)
                    </span>
                  )}
                  {addPriceChange !== null && (
                    <span style={{ fontWeight: 'bold', color: addPriceChangeColor, marginLeft: 6 }}>
                      较加: {addPriceChange > 0 ? '+' : ''}{addPriceChange.toFixed(1)}%
                    </span>
                  )}
                </div>
              </div>
              
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 6, gap: 4 }}>
                <div style={{ flex: 1 }}>
                  {mobileSelectMode ? (
                    <span style={{ color: '#8c8c8c', fontSize: 11 }}>
                      {mobileSelected.has(record.stock_code) ? '已选中' : '未选中'}
                    </span>
                  ) : (
                    record.limit_up_reason_category && (
                      <Tag color="blue" style={{ fontSize: 10, margin: 0 }}>
                        {record.limit_up_reason_category}
                      </Tag>
                    )
                  )}
                </div>
                {!mobileSelectMode && (
                  <div style={{ display: 'flex', gap: 3 }}>
                  <Button
                    type="primary"
                    size="small"
                    icon={<ShoppingCartOutlined />}
                    onClick={() => handleBuy(record)}
                    style={{ fontSize: 10, padding: '0 6px', height: 20 }}
                  >
                    买
                  </Button>
                  {isHolding && (
                    <>
                      <Button
                        type="primary"
                        size="small"
                        icon={<HeartOutlined />}
                        onClick={() => handleComfort(record)}
                        style={{ fontSize: 10, padding: '0 6px', height: 20, background: '#eb2f96', borderColor: '#eb2f96' }}
                      >
                        安慰
                      </Button>
                      <Button
                        type="primary"
                        size="small"
                        icon={<DollarOutlined />}
                        onClick={() => handleSell(record)}
                        style={{ fontSize: 10, padding: '0 6px', height: 20 }}
                      >
                        卖
                      </Button>
                    </>
                  )}
                  {!isHolding && (
                    <Popconfirm
                      title="确定删除？"
                      onConfirm={() => handleDelete(record.stock_code)}
                      okText="确定"
                      cancelText="取消"
                    >
                      <Button
                        danger
                        size="small"
                        icon={<DeleteOutlined />}
                        style={{ fontSize: 10, padding: '0 6px', height: 20 }}
                      >
                        删除
                      </Button>
                    </Popconfirm>
                  )}
                  </div>
                )}
              </div>
            </Card>
          );
        })}
        {sortedWatchlist.length > mobilePage * MOBILE_PAGE_SIZE && (
          <div style={{ textAlign: 'center', padding: '12px 0' }}>
            <Button
              size="small"
              block
              onClick={() => setMobilePage(p => p + 1)}
            >
              加载更多（已显示 {Math.min(mobilePage * MOBILE_PAGE_SIZE, sortedWatchlist.length)} / {sortedWatchlist.length}）
            </Button>
          </div>
        )}
      </div>
    );
  };

  const renderDesktopContent = () => {
    const columns = [
      {
        title: '股票',
        key: 'stock',
        width: 130,
        render: (text, record) => {
          return (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                <span 
                  style={{ cursor: 'pointer', fontWeight: 'bold', fontSize: 13 }}
                  onClick={() => {
                    setKlineStock({ code: record.stock_code.split('.')[0], name: record.stock_name, signalDate: record.signal_date || undefined });
                    setKlineVisible(true);
                  }}
                >
                  {record.stock_name}
                </span>
                <Button
                  type="primary"
                  icon={<RobotOutlined />}
                  size="small"
                  onClick={() => handleAIAnalyze(record)}
                  style={{ 
                    background: '#722ed1', 
                    borderColor: '#722ed1', 
                    borderRadius: 3, 
                    padding: '0 4px', 
                    height: 16, 
                    minWidth: 16,
                    fontSize: 10
                  }}
                />
              </div>
              <span 
                style={{ color: '#1890ff', cursor: 'pointer', fontSize: 12 }}
                onClick={() => {
                  setKlineStock({ code: record.stock_code.split('.')[0], name: record.stock_name, signalDate: record.signal_date || undefined });
                  setKlineVisible(true);
                }}
              >
                {record.stock_code.split('.')[0]}
              </span>
            </div>
          );
        },
      },
      {
        title: '策略',
        key: 'strategy_info',
        width: 130,
        render: (_, record) => (
          <div>
            {renderAddType(record)}
            {renderStrategyInfo(record)}
          </div>
        ),
      },
      {
        title: '加入/预警价',
        key: 'add_alert_price',
        width: 130,
        render: (_, record) => (
          <div>
            <div style={{ fontSize: 13 }}>
              {record.add_price ? `¥${record.add_price.toFixed(2)}` : '-'}
            </div>
            <a onClick={() => handleAlertEdit(record)} style={{ fontSize: 11 }}>
              {record.alert_price ? `预警 ¥${Number(record.alert_price).toFixed(2)}` : '设预警'}
            </a>
          </div>
        ),
      },
      {
        title: '现价/最低',
        key: 'current_price',
        width: 130,
        render: (_, record) => {
          const dayChange = record.day_change_pct;
          const dayChangeColor = dayChange > 0 ? '#f5222d' : dayChange < 0 ? '#52c41a' : '#8c8c8c';
          const alertActive = isAlert(record);
          return (
            <div>
              <div>
                <span style={{ color: dayChangeColor, fontWeight: 'bold' }}>
                  ¥{record.current_price ? record.current_price.toFixed(2) : '-'}
                </span>
                {dayChange !== null && dayChange !== undefined && (
                  <span style={{ color: dayChangeColor, fontSize: 10, marginLeft: 4 }}>
                    ({dayChange > 0 ? '+' : ''}{dayChange.toFixed(2)}%)
                  </span>
                )}
              </div>
              <div style={{ fontSize: 11, color: alertActive ? '#fa8c16' : '#8c8c8c', fontWeight: alertActive ? 'bold' : 'normal' }}>
                最低 ¥{record.day_low ? record.day_low.toFixed(2) : '-'}
              </div>
            </div>
          );
        },
      },
      {
        title: '较加入涨跌',
        key: 'add_price_change',
        width: 100,
        render: (_, record) => {
          if (!record.add_price || !record.current_price) return '-';
          const changeRatio = ((record.current_price - record.add_price) / record.add_price * 100);
          const color = changeRatio > 0 ? '#f5222d' : changeRatio < 0 ? '#52c41a' : '#8c8c8c';
          return (
            <div style={{ color, fontWeight: 'bold' }}>
              {changeRatio > 0 ? '+' : ''}{changeRatio.toFixed(2)}%
            </div>
          );
        },
      },
      {
        title: '买入',
        key: 'buy_info',
        width: 100,
        render: (_, record) => {
          if (!record.buy_price) return '-';
          return (
            <div>
              <div style={{ fontWeight: 'bold', color: '#1890ff' }}>¥{record.buy_price.toFixed(2)}</div>
              {record.buy_quantity && <div style={{ fontSize: 12, color: '#8c8c8c' }}>{record.buy_quantity}股</div>}
            </div>
          );
        },
      },
      {
        title: '盈亏',
        dataIndex: 'position_profit',
        key: 'position_profit',
        width: 110,
        render: (value, record) => {
          if (record.position_status !== '持仓' || value === null) return '-';
          const color = value > 0 ? '#f5222d' : value < 0 ? '#52c41a' : '#8c8c8c';
          const ratio = record.position_profit_ratio ? (record.position_profit_ratio * 100).toFixed(2) : '0.00';
          return (
            <div style={{ color }}>
              <div style={{ fontWeight: 'bold' }}>{value > 0 ? '+' : ''}{value.toFixed(2)}元</div>
              <div style={{ fontSize: 12 }}>{ratio > 0 ? '+' : ''}{ratio}%</div>
            </div>
          );
        },
      },
      {
        title: '入选原因',
        dataIndex: 'limit_up_reason_category',
        key: 'limit_up_reason_category',
        width: 230,
        render: (text) => {
          if (!text) return '-';
          const items = String(text).split('/').filter(Boolean);
          return (
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
              {items.map((item, i) => (
                <Tag key={i} color={i === 0 ? 'purple' : 'blue'} style={{ fontSize: 11, margin: 0 }}>
                  {item}
                </Tag>
              ))}
            </div>
          );
        },
      },
      {
        title: '操作',
        key: 'action',
        width: 200,
        render: (_, record) => (
          <div style={{ display: 'flex', gap: 4 }}>
            {record.position_status === '持仓' ? (
              <>
                <Button
                  type="primary"
                  size="small"
                  icon={<HeartOutlined />}
                  onClick={() => handleComfort(record)}
                  style={{ background: '#eb2f96', borderColor: '#eb2f96' }}
                >
                  安慰
                </Button>
                <Button
                  type="primary"
                  size="small"
                  icon={<DollarOutlined />}
                  onClick={() => handleSell(record)}
                >
                  卖出
                </Button>
              </>
            ) : (
              <>
                <Button
                  type="primary"
                  size="small"
                  icon={<ShoppingCartOutlined />}
                  onClick={() => handleBuy(record)}
                >
                  买入
                </Button>
                <Popconfirm
                  title="确定删除？"
                  onConfirm={() => handleDelete(record.stock_code)}
                  okText="确定"
                  cancelText="取消"
                >
                  <Button
                    danger
                    size="small"
                    icon={<DeleteOutlined />}
                  >
                    删除
                  </Button>
                </Popconfirm>
              </>
            )}
          </div>
        ),
      },
    ];

    return (
      <Table
        columns={columns}
        dataSource={sortedWatchlist}
        rowKey="id"
        rowSelection={{
          selectedRowKeys,
          onChange: setSelectedRowKeys,
        }}
        onRow={(record) => ({
          style: isAlert(record) ? { background: '#fff1f0' } : {},
        })}
        pagination={{
          pageSize: 20,
          showSizeChanger: true,
          showQuickJumper: true,
          showTotal: (total) => `共 ${total} 条`,
        }}
        size="middle"
      />
    );
  };

  return (
    <div style={{ padding: 0 }}>
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
        <Card
          style={{ marginBottom: 8 }}
          styles={{ body: { padding: isMobile ? '8px' : '12px' } }}
        >
          <div style={{ marginBottom: 8, fontSize: isMobile ? 11 : 12, color: '#8c8c8c', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
              <span>共 {watchlist.length} 只自选股，{watchlist.filter(isAlert).length} 只触发预警</span>
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
              {isMobile ? (
                mobileSelectMode ? (
                  <>
                    <Button
                      size="small"
                      danger
                      icon={<DeleteOutlined />}
                      onClick={() => {
                        if (mobileSelected.size === 0) {
                          message.warning('请先勾选要删除的股票');
                          return;
                        }
                        Modal.confirm({
                          title: `确定删除选中的 ${mobileSelected.size} 只自选股？`,
                          okText: '确定',
                          cancelText: '取消',
                          onOk: () => handleBatchDelete([...mobileSelected]),
                        });
                      }}
                    >
                      删除所选
                    </Button>
                    <Button
                      size="small"
                      onClick={() => {
                        setMobileSelectMode(false);
                        setMobileSelected(new Set());
                      }}
                    >
                      取消
                    </Button>
                  </>
                ) : (
                  <Button
                    size="small"
                    danger
                    icon={<DeleteOutlined />}
                    onClick={() => setMobileSelectMode(true)}
                  >
                    批量删除
                  </Button>
                )
              ) : (
                <Popconfirm
                  title={`确定删除选中的 ${selectedRowKeys.length} 只自选股？`}
                  onConfirm={() => handleBatchDelete(
                    watchlist.filter((r) => selectedRowKeys.includes(r.id)).map((r) => r.stock_code)
                  )}
                  okText="确定"
                  cancelText="取消"
                  disabled={selectedRowKeys.length === 0}
                >
                  <Button
                    size="small"
                    danger
                    icon={<DeleteOutlined />}
                    disabled={selectedRowKeys.length === 0}
                  >
                    批量删除{selectedRowKeys.length > 0 ? ` (${selectedRowKeys.length})` : ''}
                  </Button>
                </Popconfirm>
              )}
            </div>
            
            <AutoComplete
              style={{ width: isMobile ? 180 : 250 }}
              value={searchKeyword}
              options={searchResults.map(stock => ({
                value: stock.code,
                label: (
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span>{stock.display}</span>
                    <Button
                      type="link"
                      size="small"
                      icon={<PlusOutlined />}
                      onClick={(e) => {
                        e.stopPropagation();
                        handleAddToWatchlist(stock);
                      }}
                      style={{ padding: 0, height: 'auto' }}
                    >
                      添加
                    </Button>
                  </div>
                )
              }))}
              onSearch={handleSearchStock}
              onChange={setSearchKeyword}
              placeholder="搜索股票代码或名称"
            >
              <Input 
                suffix={searching ? <LoadingOutlined spin /> : <SearchOutlined />}
                allowClear
              />
            </AutoComplete>
          </div>
          
          {isMobile ? renderMobileContent() : renderDesktopContent()}
        </Card>
      )}

      <Modal
        title="买入股票"
        open={buyModalVisible}
        onOk={handleBuySubmit}
        onCancel={() => {
          setBuyModalVisible(false);
          buyForm.resetFields();
        }}
        okText="确认买入"
        cancelText="取消"
      >
        <Form form={buyForm} layout="vertical">
          <Form.Item
            label="买入价格"
            name="buy_price"
            rules={[{ required: true, message: '请输入买入价格' }]}
          >
            <InputNumber
              style={{ width: '100%' }}
              precision={2}
              min={0}
              step={0.01}
              placeholder="请输入买入价格"
            />
          </Form.Item>
          <Form.Item
            label="买入数量（股）"
            name="buy_quantity"
            rules={[
              { required: true, message: '请输入买入数量' },
              { 
                validator: (_, value) => {
                  if (value && value % 100 !== 0) {
                    return Promise.reject('买入数量必须是100的倍数');
                  }
                  return Promise.resolve();
                }
              }
            ]}
          >
            <InputNumber
              style={{ width: '100%' }}
              min={100}
              step={100}
              placeholder="请输入买入数量（100股的倍数）"
            />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title="卖出股票"
        open={sellModalVisible}
        onOk={handleSellSubmit}
        onCancel={() => {
          setSellModalVisible(false);
          sellForm.resetFields();
        }}
        okText="确认卖出"
        cancelText="取消"
      >
        <Form form={sellForm} layout="vertical">
          <Form.Item
            label="卖出价格"
            name="sell_price"
            rules={[{ required: true, message: '请输入卖出价格' }]}
          >
            <InputNumber
              style={{ width: '100%' }}
              precision={2}
              min={0}
              step={0.01}
              placeholder="请输入卖出价格"
            />
          </Form.Item>
          <Form.Item
            label={`卖出数量（持仓：${selectedStock?.buy_quantity || 0}股）`}
            name="sell_quantity"
            rules={[
              { required: true, message: '请输入卖出数量' },
              { 
                validator: (_, value) => {
                  if (value && value % 100 !== 0) {
                    return Promise.reject('卖出数量必须是100的倍数');
                  }
                  return Promise.resolve();
                }
              }
            ]}
          >
            <InputNumber
              style={{ width: '100%' }}
              min={100}
              max={selectedStock?.buy_quantity || 0}
              step={100}
              placeholder="请输入卖出数量（100股的倍数）"
            />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title={alertStock ? `设置预警价格 - ${alertStock.stock_name}` : '设置预警价格'}
        open={alertModalVisible}
        onOk={handleAlertSubmit}
        onCancel={() => {
          setAlertModalVisible(false);
          alertForm.resetFields();
        }}
        okText="保存"
        cancelText="取消"
      >
        <Form form={alertForm} layout="vertical">
          <Form.Item
            label="预警价格"
            name="alert_price"
            extra={alertStock?.alert_price
              ? `当前预警：¥${Number(alertStock.alert_price).toFixed(2)}；清空输入框可清除预警`
              : '清空输入框可清除预警'}
          >
            <InputNumber
              style={{ width: '100%' }}
              precision={2}
              min={0}
              step={0.01}
              placeholder="输入预警价格（留空清除）"
            />
          </Form.Item>
          {alertStock?.current_price != null && (
            <div style={{ color: '#8c8c8c', fontSize: 12 }}>
              当前价格：¥{Number(alertStock.current_price).toFixed(2)}
            </div>
          )}
        </Form>
      </Modal>

      <WatchlistAnalysisModal
        visible={analysisVisible}
        stockCode={analysisStock?.code}
        stockName={analysisStock?.name}
        onClose={() => {
          setAnalysisVisible(false);
          setAnalysisStock(null);
        }}
      />

      <StockKlineModal
        visible={klineVisible}
        stockCode={klineStock?.code}
        stockName={klineStock?.name}
        signalDate={klineStock?.signalDate}
        onClose={() => {
          setKlineVisible(false);
          setKlineStock(null);
        }}
      />

      <Modal
        title={
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <HeartOutlined style={{ color: '#eb2f96' }} />
            <span>AI安慰分析</span>
          </div>
        }
        open={comfortModalVisible}
        onCancel={() => {
          setComfortModalVisible(false);
          setComfortResult('');
        }}
        footer={[
          <Button key="close" onClick={() => {
            setComfortModalVisible(false);
            setComfortResult('');
          }}>
            关闭
          </Button>
        ]}
        width={700}
      >
        {comfortLoading ? (
          <div style={{ textAlign: 'center', padding: '40px 0' }}>
            <Spin size="large" />
            <div style={{ marginTop: 16, color: '#8c8c8c' }}>AI正在为您分析并准备安慰...</div>
          </div>
        ) : (
          <div>
            {comfortResult && typeof comfortResult === 'object' && (
              <>
                {comfortResult.emotion_comfort && (
                  <Card size="small" style={{ marginBottom: 12, borderLeft: '3px solid #eb2f96' }}>
                    <div style={{ fontWeight: 'bold', marginBottom: 8, color: '#eb2f96' }}>💗 情感安慰</div>
                    <div style={{ lineHeight: 1.6 }}>{comfortResult.emotion_comfort}</div>
                  </Card>
                )}
                
                {comfortResult.rational_analysis && (
                  <Card size="small" style={{ marginBottom: 12, borderLeft: '3px solid #1890ff' }}>
                    <div style={{ fontWeight: 'bold', marginBottom: 8, color: '#1890ff' }}>📊 理性分析</div>
                    <div style={{ lineHeight: 1.6 }}>{comfortResult.rational_analysis}</div>
                  </Card>
                )}
                
                {comfortResult.operation_advice && (
                  <Card size="small" style={{ marginBottom: 12, borderLeft: '3px solid #52c41a' }}>
                    <div style={{ fontWeight: 'bold', marginBottom: 8, color: '#52c41a' }}>💡 操作建议</div>
                    <div style={{ lineHeight: 1.6 }}>{comfortResult.operation_advice}</div>
                  </Card>
                )}
                
                {comfortResult.risk_warning && (
                  <Card size="small" style={{ marginBottom: 12, borderLeft: '3px solid #faad14' }}>
                    <div style={{ fontWeight: 'bold', marginBottom: 8, color: '#faad14' }}>⚠️ 风险提示</div>
                    <div style={{ lineHeight: 1.6 }}>{comfortResult.risk_warning}</div>
                  </Card>
                )}
                
                {comfortResult.future_outlook && (
                  <Card size="small" style={{ marginBottom: 12, borderLeft: '3px solid #722ed1' }}>
                    <div style={{ fontWeight: 'bold', marginBottom: 8, color: '#722ed1' }}>🔮 未来展望</div>
                    <div style={{ lineHeight: 1.6 }}>{comfortResult.future_outlook}</div>
                  </Card>
                )}
                
                {comfortResult.overall_suggestion && (
                  <Card size="small" style={{ marginBottom: 0, background: '#f6ffed', borderColor: '#b7eb8f' }}>
                    <div style={{ fontWeight: 'bold', marginBottom: 8, color: '#52c41a' }}>✨ 总体建议</div>
                    <Tag color="green" style={{ fontSize: 14, padding: '4px 12px' }}>
                      {comfortResult.overall_suggestion}
                    </Tag>
                  </Card>
                )}
              </>
            )}
          </div>
        )}
      </Modal>
    </div>
  );
};

export default WatchlistPage;
