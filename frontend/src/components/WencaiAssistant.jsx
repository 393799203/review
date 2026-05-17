import React, { useState, useEffect } from 'react';
import { Modal, Input, Button, Table, message, Spin, Tooltip, Card, Tag, Form, Popconfirm } from 'antd';
import { SearchOutlined, RobotOutlined, PlusOutlined, CheckOutlined, EditOutlined, DeleteOutlined, SaveOutlined } from '@ant-design/icons';
import axios from 'axios';
import StockKlineModal from './StockKlineModal';
import StockAnalysisModal from './StockAnalysisModal';

const { TextArea } = Input;

const WencaiAssistant = ({ visible, onClose, dateStr, type = 'breakout', nextDayBlocks = [], enableBlur = false }) => {
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState([]);
  const [isMobile, setIsMobile] = useState(false);
  const [queryType, setQueryType] = useState(null);
  const [watchlistCodes, setWatchlistCodes] = useState([]);
  const [klineVisible, setKlineVisible] = useState(false);
  const [selectedStock, setSelectedStock] = useState(null);
  const [analysisVisible, setAnalysisVisible] = useState(false);
  const [analysisStock, setAnalysisStock] = useState(null);
  
  const [userStrategies, setUserStrategies] = useState([]);
  const [strategiesLoading, setStrategiesLoading] = useState(false);
  const [showStrategyModal, setShowStrategyModal] = useState(false);
  const [editingStrategy, setEditingStrategy] = useState(null);
  const [strategyForm] = Form.useForm();

  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 768);
    };
    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  const getQueryByType = (queryType, date) => {
    const dateFormatted = `${date.slice(0, 4)}年${date.slice(4, 6)}月${date.slice(6, 8)}日`;
    
    const userStrategy = userStrategies.find(s => s.id === queryType);
    if (userStrategy) {
      let template = userStrategy.query_template;
      template = template.replace(/\{date\}/g, dateFormatted);
      return template;
    }
    
    return '';
  };

  const getTitleByType = (queryType) => {
    return '问财智能助手';
  };

  const loadWatchlistCodes = async () => {
    try {
      const isDev = import.meta.env.DEV;
      const API_BASE = isDev ? 'http://localhost:5001/api' : '/api';
      
      const response = await axios.get(`${API_BASE}/watchlist`);
      
      if (response.data.success) {
        const codes = response.data.data.map(stock => {
          const code = stock.stock_code || '';
          const normalizedCode = code.replace(/\.(SH|SZ|BJ)$/, '');
          return normalizedCode;
        });
        console.log('加载自选股 codes:', codes);
        setWatchlistCodes(codes);
      } else {
        console.error('获取自选股失败:', response.data.error);
      }
    } catch (error) {
      console.error('加载自选股列表失败:', error);
    }
  };

  const loadUserStrategies = async () => {
    try {
      setStrategiesLoading(true);
      const isDev = import.meta.env.DEV;
      const API_BASE = isDev ? 'http://localhost:5001/api' : '/api';
      
      const userStr = localStorage.getItem('user');
      if (!userStr) {
        setStrategiesLoading(false);
        return;
      }
      
      const user = JSON.parse(userStr);
      
      const response = await axios.get(`${API_BASE}/wencai/strategies`, {
        headers: {
          'X-User-Uid': user.uid
        }
      });
      
      if (response.data.success) {
        const strategies = response.data.data || [];
        setUserStrategies(strategies);
        
        if (strategies.length > 0 && !queryType) {
          const defaultStrategy = strategies.find(s => s.is_default === 1);
          setQueryType(defaultStrategy ? defaultStrategy.id : strategies[0].id);
        }
      }
    } catch (error) {
      console.error('加载用户策略失败:', error);
    } finally {
      setStrategiesLoading(false);
    }
  };

  useEffect(() => {
    if (visible) {
      setQuery(getQueryByType(queryType, dateStr));
      setResult([]);
      loadWatchlistCodes();
      loadUserStrategies();
    }
  }, [visible, dateStr, queryType]);

  useEffect(() => {
    if (visible && queryType) {
      setQuery(getQueryByType(queryType, dateStr));
    }
  }, [userStrategies]);

  const handleSearch = async () => {
    if (!query.trim()) {
      message.error('请输入查询语句');
      return;
    }

    setLoading(true);
    try {
      const isDev = import.meta.env.DEV;
      const API_BASE = isDev ? 'http://localhost:5001/api' : '/api';
      
      const response = await axios.post(`${API_BASE}/wencai/query`, {
        query: query
      }, {
        timeout: 60000
      });

      if (response.data.success) {
        setResult(response.data.data || []);
        message.success(`查询成功，找到 ${response.data.count} 条结果`);
      } else {
        message.error(response.data.error || '查询失败');
      }
    } catch (error) {
      message.error('查询失败：' + (error.response?.data?.error || error.message));
    } finally {
      setLoading(false);
    }
  };

  const handleAddToWatchlist = async (record) => {
    try {
      const stockCodeRaw = record['股票代码'];
      const stockCode = stockCodeRaw.replace(/\.(SH|SZ|BJ)$/, '');
      const stockName = record['股票简称'];
      const price = record['最新价'];
      
      const reasonKey = Object.keys(record).find(k => k.includes('涨停原因类别'));
      const limitUpReasonCategory = record[reasonKey] || '';
      
      if (!stockCode || !stockName) {
        message.error('股票信息不完整');
        return;
      }
      
      const isDev = import.meta.env.DEV;
      const API_BASE = isDev ? 'http://localhost:5001/api' : '/api';
      
      const response = await axios.post(`${API_BASE}/watchlist`, {
        stock_code: stockCode,
        stock_name: stockName,
        add_date: dateStr,
        add_price: price,
        add_reason: query.substring(0, 200),
        source: 'wencai',
        limit_up_reason_category: limitUpReasonCategory
      });
      
      if (response.data.success) {
        message.success('已加入自选');
        setWatchlistCodes([...watchlistCodes, stockCode]);
      } else {
        message.error(response.data.error || '添加失败');
      }
    } catch (error) {
      message.error('添加失败：' + (error.response?.data?.error || error.message));
    }
  };

  const handleSaveStrategy = async (values) => {
    try {
      const isDev = import.meta.env.DEV;
      const API_BASE = isDev ? 'http://localhost:5001/api' : '/api';
      
      const userStr = localStorage.getItem('user');
      if (!userStr) {
        message.error('请先登录');
        return;
      }
      
      const user = JSON.parse(userStr);
      
      if (editingStrategy) {
        const response = await axios.put(
          `${API_BASE}/wencai/strategies/${editingStrategy.id}`,
          values,
          {
            headers: {
              'X-User-Uid': user.uid
            }
          }
        );
        
        if (response.data.success) {
          message.success('策略更新成功');
          loadUserStrategies();
          setShowStrategyModal(false);
          strategyForm.resetFields();
        } else {
          message.error(response.data.error || '更新失败');
        }
      } else {
        const response = await axios.post(
          `${API_BASE}/wencai/strategies`,
          values,
          {
            headers: {
              'X-User-Uid': user.uid
            }
          }
        );
        
        if (response.data.success) {
          message.success('策略创建成功');
          loadUserStrategies();
          setShowStrategyModal(false);
          strategyForm.resetFields();
        } else {
          message.error(response.data.error || '创建失败');
        }
      }
    } catch (error) {
      message.error('保存失败：' + (error.response?.data?.error || error.message));
    }
  };

  const handleDeleteStrategy = async (strategyId) => {
    try {
      const isDev = import.meta.env.DEV;
      const API_BASE = isDev ? 'http://localhost:5001/api' : '/api';
      
      const userStr = localStorage.getItem('user');
      if (!userStr) {
        message.error('请先登录');
        return;
      }
      
      const user = JSON.parse(userStr);
      
      const response = await axios.delete(
        `${API_BASE}/wencai/strategies/${strategyId}`,
        {
          headers: {
            'X-User-Uid': user.uid
          }
        }
      );
      
      if (response.data.success) {
        message.success('策略删除成功');
        loadUserStrategies();
        if (queryType === strategyId) {
          setQueryType('breakthrough');
        }
      } else {
        message.error(response.data.error || '删除失败');
      }
    } catch (error) {
      message.error('删除失败：' + (error.response?.data?.error || error.message));
    }
  };

  const columns = [
    {
      title: '股票信息',
      key: 'stockInfo',
      width: isMobile ? 90 : 100,
      fixed: 'left',
      render: (_, record) => {
        const stockCode = record['股票代码'].replace(/\.(SH|SZ|BJ)$/, '');
        return (
          <div style={{ lineHeight: '18px' }}>
            <div 
              style={{ 
                fontWeight: 'bold', 
                color: '#1890ff', 
                fontSize: isMobile ? 12 : 13, 
                cursor: 'pointer',
                filter: enableBlur ? 'blur(5px)' : 'none',
                userSelect: enableBlur ? 'none' : 'auto'
              }}
              onClick={() => {
                setSelectedStock({ code: stockCode, name: record['股票简称'] });
                setKlineVisible(true);
              }}
            >
              {stockCode}
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
              <div 
                style={{ 
                  fontSize: isMobile ? 11 : 12, 
                  color: '#262626', 
                  fontWeight: 'bold', 
                  cursor: 'pointer',
                  filter: enableBlur ? 'blur(5px)' : 'none',
                  userSelect: enableBlur ? 'none' : 'auto'
                }}
                onClick={() => {
                  setSelectedStock({ code: stockCode, name: record['股票简称'] });
                  setKlineVisible(true);
                }}
              >
                {record['股票简称']}
              </div>
              <div 
                style={{ 
                  display: 'inline-flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  width: 16,
                  height: 16,
                  borderRadius: '50%',
                  background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                  cursor: 'pointer'
                }}
                onClick={(e) => {
                  e.stopPropagation();
                  setAnalysisStock({ code: stockCode, name: record['股票简称'] });
                  setAnalysisVisible(true);
                }}
              >
                <RobotOutlined style={{ fontSize: 9, color: '#fff' }} />
              </div>
            </div>
          </div>
        );
      },
    },
    {
      title: '价格信息',
      key: 'priceInfo',
      width: isMobile ? 70 : 80,
      render: (_, record) => {
        const changeVal = record['最新涨跌幅'];
        const priceVal = record['最新价'];
        
        if (!changeVal && !priceVal) return <span>-</span>;
        
        const numChange = typeof changeVal === 'string' ? parseFloat(changeVal) : changeVal;
        const color = numChange > 0 ? '#f5222d' : numChange < 0 ? '#52c41a' : '#666';
        
        return (
          <div style={{ lineHeight: '18px' }}>
            <div style={{ color, fontWeight: 'bold', fontSize: isMobile ? 12 : 13 }}>
              {numChange ? `${numChange.toFixed(2)}%` : '-'}
            </div>
            <div style={{ fontSize: isMobile ? 11 : 12, color: '#666' }}>¥{priceVal || '-'}</div>
          </div>
        );
      },
    },
    {
      title: '涨停原因类别',
      key: 'reasonCategory',
      width: isMobile ? 150 : 180,
      ellipsis: true,
      render: (_, record) => {
        const key = Object.keys(record).find(k => k.includes('涨停原因类别'));
        const val = record[key];
        if (!val) return <span>-</span>;
        return (
          <Tooltip title={val}>
            <span style={{ fontSize: isMobile ? 11 : 12 }}>{val}</span>
          </Tooltip>
        );
      },
    },
    {
      title: '近1年涨停',
      key: 'yearLimitUp',
      width: isMobile ? 80 : 100,
      render: (_, record) => {
        const key = Object.keys(record).find(k => k.includes('涨停次数['));
        const val = record[key];
        return (
          <span style={{ fontWeight: 'bold', fontSize: isMobile ? 12 : 13, color: '#f5222d' }}>
            {val || '-'}
          </span>
        );
      },
    },
    {
      title: '近1月涨幅',
      key: 'monthChange',
      width: isMobile ? 80 : 100,
      render: (_, record) => {
        const key = Object.keys(record).find(k => k.includes('区间涨跌幅'));
        const val = record[key];
        if (!val) return <span>-</span>;
        const numVal = typeof val === 'string' ? parseFloat(val) : val;
        const color = numVal > 0 ? '#f5222d' : numVal < 0 ? '#52c41a' : '#666';
        return (
          <span style={{ fontWeight: 'bold', fontSize: isMobile ? 12 : 13, color }}>
            {numVal ? `${numVal.toFixed(2)}%` : '-'}
          </span>
        );
      },
    },
    {
      title: '所属概念',
      key: 'concept',
      width: isMobile ? 150 : 200,
      ellipsis: true,
      render: (_, record) => {
        const key = Object.keys(record).find(k => k.includes('所属概念'));
        const val = record[key];
        if (!val) return <span>-</span>;
        return (
          <Tooltip title={val}>
            <span style={{ fontSize: isMobile ? 11 : 12 }}>{val}</span>
          </Tooltip>
        );
      },
    },
    {
      title: '操作',
      key: 'action',
      width: isMobile ? 60 : 80,
      fixed: 'right',
      render: (_, record) => {
        const stockCodeRaw = record['股票代码'];
        const stockCode = stockCodeRaw ? stockCodeRaw.replace(/\.(SH|SZ|BJ)$/, '') : '';
        const isAdded = watchlistCodes.includes(stockCode);
        return (
          <Button
            type={isAdded ? 'default' : 'primary'}
            size="small"
            icon={isAdded ? <CheckOutlined /> : <PlusOutlined />}
            onClick={() => !isAdded && handleAddToWatchlist(record)}
            disabled={isAdded}
            style={{ fontSize: isMobile ? 11 : 12 }}
          >
            {isMobile ? '' : (isAdded ? '已添加' : '自选')}
          </Button>
        );
      },
    },
  ];

  const tableColumns = columns;

  const renderMobileContent = () => {
    if (result.length === 0) {
      return (
        <div style={{ 
          textAlign: 'center', 
          padding: '40px 20px', 
          color: '#999',
          fontSize: 14 
        }}>
          暂无数据
        </div>
      );
    }
    
    return (
      <div>
        <div style={{ marginBottom: 8, fontWeight: 'bold', fontSize: 12, textAlign: 'center' }}>
          查询结果：共 {result.length} 条
        </div>
        {result.map((record, index) => {
          const changeVal = record['最新涨跌幅'];
          const priceVal = record['最新价'];
          const numChange = typeof changeVal === 'string' ? parseFloat(changeVal) : changeVal;
          const changeColor = numChange > 0 ? '#f5222d' : numChange < 0 ? '#52c41a' : '#666';
          
          const reasonKey = Object.keys(record).find(k => k.includes('涨停原因类别'));
          const reasonVal = record[reasonKey];
          
          const yearLimitUpKey = Object.keys(record).find(k => k.includes('涨停次数['));
          const yearLimitUpVal = record[yearLimitUpKey];
          
          const monthChangeKey = Object.keys(record).find(k => k.includes('区间涨跌幅'));
          const monthChangeVal = record[monthChangeKey];
          const numMonthChange = typeof monthChangeVal === 'string' ? parseFloat(monthChangeVal) : monthChangeVal;
          const monthChangeColor = numMonthChange > 0 ? '#f5222d' : numMonthChange < 0 ? '#52c41a' : '#666';
          
          const conceptKey = Object.keys(record).find(k => k.includes('所属概念'));
          const conceptVal = record[conceptKey];
            
            const stockCode = record['股票代码'].replace(/\.(SH|SZ|BJ)$/, '');
            const isAdded = watchlistCodes.includes(stockCode);
            console.log('股票:', stockCode, 'isAdded:', isAdded, 'watchlistCodes:', watchlistCodes);
          
          return (
            <Card
              key={index}
              size="small"
              style={{ marginBottom: 8 }}
              styles={{ body: { padding: '8px 10px' } }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 6 }}>
                <div style={{ flex: 1 }}>
                  <div 
                    style={{ 
                      fontWeight: 'bold', 
                      color: '#1890ff', 
                      fontSize: 13, 
                      cursor: 'pointer',
                      filter: enableBlur ? 'blur(5px)' : 'none',
                      userSelect: enableBlur ? 'none' : 'auto'
                    }}
                    onClick={() => {
                      setSelectedStock({ code: stockCode, name: record['股票简称'] });
                      setKlineVisible(true);
                    }}
                  >
                    {stockCode}
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                    <div 
                      style={{ 
                        fontSize: 12, 
                        color: '#262626', 
                        fontWeight: 'bold', 
                        cursor: 'pointer',
                        filter: enableBlur ? 'blur(5px)' : 'none',
                        userSelect: enableBlur ? 'none' : 'auto'
                      }}
                      onClick={() => {
                        setSelectedStock({ code: stockCode, name: record['股票简称'] });
                        setKlineVisible(true);
                      }}
                    >
                      {record['股票简称']}
                    </div>
                    <div 
                      style={{ 
                        display: 'inline-flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        width: 16,
                        height: 16,
                        borderRadius: '50%',
                        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                        cursor: 'pointer'
                      }}
                      onClick={(e) => {
                        e.stopPropagation();
                        setAnalysisStock({ code: stockCode, name: record['股票简称'] });
                        setAnalysisVisible(true);
                      }}
                    >
                      <RobotOutlined style={{ fontSize: 9, color: '#fff' }} />
                    </div>
                  </div>
                </div>
                <div style={{ textAlign: 'right', marginLeft: 8 }}>
                  <div style={{ color: changeColor, fontWeight: 'bold', fontSize: 14 }}>
                    {numChange ? `${numChange.toFixed(2)}%` : '-'}
                  </div>
                  <div style={{ fontSize: 12, color: '#666' }}>¥{priceVal || '-'}</div>
                </div>
              </div>
              
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                {reasonVal ? (
                  <Tag color="blue" style={{ fontSize: 10, margin: 0 }}>{reasonVal}</Tag>
                ) : (
                  <div></div>
                )}
                <Button
                  type={isAdded ? 'default' : 'primary'}
                  size="small"
                  icon={isAdded ? <CheckOutlined /> : <PlusOutlined />}
                  onClick={() => !isAdded && handleAddToWatchlist(record)}
                  disabled={isAdded}
                  style={{ fontSize: 10, padding: '0 6px', height: 22 }}
                >
                  {isAdded ? '已添加' : '自选'}
                </Button>
              </div>
              
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, marginBottom: 4 }}>
                <div>
                  <span style={{ color: '#999' }}>近1年涨停：</span>
                  <span style={{ color: '#f5222d', fontWeight: 'bold' }}>
                    {yearLimitUpVal || '-'}
                  </span>
                </div>
                <div>
                  <span style={{ color: '#999' }}>近1月涨幅：</span>
                  <span style={{ color: monthChangeColor, fontWeight: 'bold' }}>
                    {numMonthChange ? `${numMonthChange.toFixed(2)}%` : '-'}
                  </span>
                </div>
              </div>
              
              {conceptVal && (
                <div style={{ fontSize: 11 }}>
                  <span style={{ color: '#999' }}>所属概念：</span>
                  <span>{conceptVal}</span>
                </div>
              )}
            </Card>
          );
        })}
      </div>
    );
  };

  const renderDesktopContent = () => {
    if (result.length === 0) {
      return (
        <div style={{ 
          textAlign: 'center', 
          padding: '60px 20px', 
          color: '#999',
          fontSize: 14 
        }}>
          暂无数据
        </div>
      );
    }
    
    return (
      <div>
        <div style={{ marginBottom: 4, fontWeight: 'bold', fontSize: 13 }}>
          查询结果：共 {result.length} 条
        </div>
        <Table
          columns={tableColumns}
          dataSource={result}
          rowKey={(record) => record['股票代码'] || record['code'] || Math.random()}
          scroll={{ x: 'max-content', y: 400 }}
          size="small"
          pagination={{
            pageSize: 20,
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 条`,
            size: 'small',
          }}
          style={{
            fontSize: 12,
          }}
          styles={{
            body: {
              fontSize: 12,
            },
            header: {
              fontSize: 12,
              fontWeight: 'bold',
            },
          }}
        />
      </div>
    );
  };

  return (
    <>
      <Modal
        title={
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <RobotOutlined style={{ fontSize: isMobile ? 16 : 18, color: '#1890ff' }} />
            <span style={{ fontSize: isMobile ? 14 : 16 }}>{getTitleByType(type)}</span>
          </div>
        }
        open={visible}
        onCancel={onClose}
        width={isMobile ? '95%' : 1100}
        footer={null}
        style={{ top: isMobile ? 20 : 10 }}
        styles={{
          body: {
            padding: isMobile ? '8px' : '8px 12px',
            maxHeight: isMobile ? '75vh' : 'none',
            overflow: isMobile ? 'auto' : 'visible',
          },
        }}
      >
        <div style={{ marginBottom: isMobile ? 6 : 8 }}>
          <div style={{ marginBottom: isMobile ? 8 : 12 }}>
            <div style={{ 
              display: 'flex', 
              alignItems: 'center', 
              justifyContent: 'space-between',
              marginBottom: isMobile ? 8 : 12 
            }}>
              <div style={{ 
                fontSize: isMobile ? 12 : 13, 
                fontWeight: 600, 
                color: '#262626',
                display: 'flex',
                alignItems: 'center',
                gap: 6
              }}>
                <span style={{
                  display: 'inline-block',
                  width: 3,
                  height: 14,
                  background: 'linear-gradient(180deg, #1890ff 0%, #096dd9 100%)',
                  borderRadius: 2
                }}></span>
                选择策略
              </div>
            </div>
            
            <Spin spinning={strategiesLoading} tip="加载策略中...">
              <div style={{ 
                display: isMobile ? 'flex' : 'grid',
                gridTemplateColumns: isMobile ? undefined : 'repeat(auto-fill, minmax(160px, 1fr))',
                gap: isMobile ? 8 : 10,
                overflowX: isMobile ? 'auto' : 'visible',
                overflowY: isMobile ? 'hidden' : 'visible',
                whiteSpace: isMobile ? 'nowrap' : 'normal',
                WebkitOverflowScrolling: isMobile ? 'touch' : 'auto',
                scrollbarWidth: isMobile ? 'none' : 'auto',
                msOverflowStyle: isMobile ? 'none' : 'auto',
                paddingBottom: isMobile ? 4 : 0,
                ...(isMobile && {
                  '&::-webkit-scrollbar': {
                    display: 'none'
                  }
                })
              }}>
                {userStrategies.map(strategy => {
                const isActive = queryType === strategy.id;
                return (
                  <div
                    key={strategy.id}
                    onClick={() => setQueryType(strategy.id)}
                    style={{
                      position: 'relative',
                      padding: isMobile ? '10px 12px' : '12px 14px',
                      borderRadius: 8,
                      border: `2px solid ${isActive ? 'transparent' : '#f0f0f0'}`,
                      background: isActive 
                        ? 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'
                        : '#fafafa',
                      cursor: 'pointer',
                      transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
                      transform: isActive ? 'scale(1.02)' : 'scale(1)',
                      boxShadow: isActive 
                        ? '0 4px 12px rgba(102, 126, 234, 0.4)'
                        : '0 1px 3px rgba(0, 0, 0, 0.05)',
                      overflow: 'hidden',
                      minWidth: isMobile ? 140 : 'auto',
                      flexShrink: isMobile ? 0 : 1
                    }}
                    onMouseEnter={(e) => {
                      if (!isActive) {
                        e.currentTarget.style.transform = 'scale(1.02)';
                        e.currentTarget.style.boxShadow = '0 4px 12px rgba(0, 0, 0, 0.1)';
                        e.currentTarget.style.borderColor = '#d9d9d9';
                      }
                    }}
                    onMouseLeave={(e) => {
                      if (!isActive) {
                        e.currentTarget.style.transform = 'scale(1)';
                        e.currentTarget.style.boxShadow = '0 1px 3px rgba(0, 0, 0, 0.05)';
                        e.currentTarget.style.borderColor = '#f0f0f0';
                      }
                    }}
                  >
                    {isActive && (
                      <div style={{
                        position: 'absolute',
                        top: 0,
                        right: 0,
                        width: 0,
                        height: 0,
                        borderStyle: 'solid',
                        borderWidth: '0 32px 32px 0',
                        borderColor: 'transparent rgba(255, 255, 255, 0.3) transparent transparent',
                        pointerEvents: 'none'
                      }} />
                    )}
                    
                    <div style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between'
                    }}>
                      <div style={{
                        fontSize: isMobile ? 12 : 13,
                        fontWeight: 600,
                        color: isActive ? '#fff' : '#262626',
                        flex: 1,
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap'
                      }}>
                        {strategy.strategy_name}
                      </div>
                      
                      <div style={{
                         display: 'flex',
                         alignItems: 'center',
                         gap: 4,
                         marginLeft: 8
                       }}
                       onClick={(e) => e.stopPropagation()}
                       >
                         <div
                           onClick={(e) => {
                             e.stopPropagation();
                             setEditingStrategy(strategy);
                             strategyForm.setFieldsValue(strategy);
                             setShowStrategyModal(true);
                           }}
                           style={{
                             display: 'flex',
                             alignItems: 'center',
                             justifyContent: 'center',
                             width: 22,
                             height: 22,
                             borderRadius: 4,
                             background: isActive ? 'rgba(255, 255, 255, 0.15)' : '#fff',
                             cursor: 'pointer',
                             outline: 'none',
                             boxShadow: 'none'
                           }}
                           tabIndex={-1}
                           onMouseEnter={(e) => {
                             if (isActive) {
                               e.currentTarget.style.background = 'rgba(255, 255, 255, 0.25)';
                             } else {
                               e.currentTarget.style.background = '#e6f7ff';
                               e.currentTarget.style.color = '#1890ff';
                             }
                           }}
                           onMouseLeave={(e) => {
                             if (isActive) {
                               e.currentTarget.style.background = 'rgba(255, 255, 255, 0.15)';
                             } else {
                               e.currentTarget.style.background = '#fff';
                               e.currentTarget.style.color = '#595959';
                             }
                           }}
                           onFocus={(e) => {
                             e.target.style.outline = 'none';
                             e.target.style.boxShadow = 'none';
                           }}
                         >
                           <EditOutlined style={{ 
                             fontSize: 11, 
                             color: isActive ? '#fff' : '#595959',
                             pointerEvents: 'none'
                           }} />
                         </div>
                        
                        <Popconfirm
                          title="确定要删除这个策略吗？"
                          description="删除后无法恢复"
                          onConfirm={(e) => {
                            e.stopPropagation();
                            handleDeleteStrategy(strategy.id);
                          }}
                          okText="确定"
                          cancelText="取消"
                          okButtonProps={{ danger: true }}
                        >
                          <div
                            onClick={(e) => e.stopPropagation()}
                            style={{
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'center',
                              width: 22,
                              height: 22,
                              borderRadius: 4,
                              background: isActive ? 'rgba(255, 255, 255, 0.15)' : '#fff',
                              cursor: 'pointer',
                              outline: 'none',
                              boxShadow: 'none'
                            }}
                            tabIndex={-1}
                            onMouseEnter={(e) => {
                              if (isActive) {
                                e.currentTarget.style.background = 'rgba(255, 107, 107, 0.3)';
                              } else {
                                e.currentTarget.style.background = '#fff1f0';
                              }
                            }}
                            onMouseLeave={(e) => {
                              if (isActive) {
                                e.currentTarget.style.background = 'rgba(255, 255, 255, 0.15)';
                              } else {
                                e.currentTarget.style.background = '#fff';
                              }
                            }}
                            onFocus={(e) => {
                              e.target.style.outline = 'none';
                              e.target.style.boxShadow = 'none';
                            }}
                          >
                            <DeleteOutlined style={{ 
                              fontSize: 11, 
                              color: isActive ? '#fff' : '#ff4d4f'
                            }} />
                          </div>
                        </Popconfirm>
                      </div>
                    </div>
                    
                    {strategy.description && (
                      <div style={{
                        fontSize: isMobile ? 10 : 11,
                        color: isActive ? 'rgba(255, 255, 255, 0.8)' : '#8c8c8c',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap',
                        marginTop: 4
                      }}>
                        {strategy.description}
                      </div>
                    )}
                  </div>
                );
              })}
              
              <div
                onClick={() => {
                  setEditingStrategy(null);
                  strategyForm.resetFields();
                  setShowStrategyModal(true);
                }}
                style={{
                  position: 'relative',
                  padding: isMobile ? '10px 12px' : '12px 14px',
                  borderRadius: 8,
                  border: '2px dashed #d9d9d9',
                  background: '#fafafa',
                  cursor: 'pointer',
                  transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
                  minHeight: isMobile ? 60 : 68,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  outline: 'none',
                  order: 999,
                  minWidth: isMobile ? 140 : 'auto',
                  flexShrink: isMobile ? 0 : 1
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.borderColor = '#1890ff';
                  e.currentTarget.style.background = '#e6f7ff';
                  e.currentTarget.style.transform = 'scale(1.02)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.borderColor = '#d9d9d9';
                  e.currentTarget.style.background = '#fafafa';
                  e.currentTarget.style.transform = 'scale(1)';
                }}
              >
                <div style={{
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  gap: 4
                }}>
                  <PlusOutlined style={{ 
                    fontSize: isMobile ? 18 : 20, 
                    color: '#8c8c8c'
                  }} />
                  <div style={{
                    fontSize: isMobile ? 11 : 12,
                    color: '#8c8c8c',
                    fontWeight: 500
                  }}>
                    新增策略
                  </div>
                </div>
              </div>
            </div>
          </Spin>
          </div>
          
          <div style={{ 
            position: 'relative',
            marginBottom: isMobile ? 8 : 10
          }}>
            <div style={{
              position: 'absolute',
              top: -8,
              left: 12,
              background: '#fff',
              padding: '0 4px',
              fontSize: isMobile ? 11 : 12,
              color: '#8c8c8c',
              zIndex: 1
            }}>
              查询语句
            </div>
            <TextArea
              rows={4}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="输入自然语言查询语句...&#10;支持变量：{date} 会被替换为当前日期"
              style={{ 
                fontFamily: 'Consolas, Monaco, "Courier New", monospace', 
                fontSize: isMobile ? 12 : 13,
                borderRadius: 8,
                minHeight: isMobile ? '100px' : '120px',
                border: '1px solid #e8e8e8',
                backgroundColor: '#fafafa',
                padding: isMobile ? '10px 12px' : '12px 14px',
                transition: 'all 0.3s',
                boxShadow: '0 1px 3px rgba(0, 0, 0, 0.04)'
              }}
              onFocus={(e) => {
                e.target.style.borderColor = '#1890ff';
                e.target.style.boxShadow = '0 2px 8px rgba(24, 144, 255, 0.15)';
                e.target.style.backgroundColor = '#fff';
              }}
              onBlur={(e) => {
                e.target.style.borderColor = '#e8e8e8';
                e.target.style.boxShadow = '0 1px 3px rgba(0, 0, 0, 0.04)';
                e.target.style.backgroundColor = '#fafafa';
              }}
            />
          </div>
        </div>

        <Button
          type="primary"
          icon={<SearchOutlined />}
          onClick={handleSearch}
          loading={loading}
          size={isMobile ? 'small' : 'middle'}
          block
          style={{ marginBottom: isMobile ? 4 : 6 }}
        >
          开始查询
        </Button>

        <Spin spinning={loading}>
          {isMobile ? renderMobileContent() : renderDesktopContent()}
        </Spin>

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
      </Modal>

      <Modal
        title={editingStrategy ? '编辑策略' : '创建新策略'}
        open={showStrategyModal}
        onCancel={() => {
          setShowStrategyModal(false);
          strategyForm.resetFields();
          setEditingStrategy(null);
        }}
        footer={null}
        width={isMobile ? '95%' : 600}
      >
        <Form
          form={strategyForm}
          layout="vertical"
          onFinish={handleSaveStrategy}
        >
          <Form.Item
            name="strategy_name"
            label="策略名称"
            rules={[{ required: true, message: '请输入策略名称' }]}
          >
            <Input placeholder="例如：强势股突破策略" />
          </Form.Item>
          
          <Form.Item
            name="query_template"
            label="查询模板"
            rules={[{ required: true, message: '请输入查询模板' }]}
            extra="支持变量：{date} 会被替换为当前日期，例如：2026年05月15日"
          >
            <TextArea 
              rows={6} 
              placeholder="{date} 涨停 显示涨停原因类别 显示概念&#10;非ST 非科创板 非北交所&#10;近1年涨停次数大于等于2次"
              style={{ fontFamily: 'monospace' }}
            />
          </Form.Item>
          
          <Form.Item
            name="description"
            label="策略描述"
          >
            <Input.TextArea rows={2} placeholder="描述这个策略的选股逻辑" />
          </Form.Item>
          
          <Form.Item>
            <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
              <Button onClick={() => {
                setShowStrategyModal(false);
                strategyForm.resetFields();
                setEditingStrategy(null);
              }}>
                取消
              </Button>
              <Button type="primary" htmlType="submit" icon={<SaveOutlined />}>
                保存策略
              </Button>
            </div>
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
};

export default WencaiAssistant;
