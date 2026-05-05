import React, { useState, useEffect } from 'react';
import { Modal, Input, Button, Table, message, Spin, Tooltip, Card, Tag, Radio } from 'antd';
import { SearchOutlined, RobotOutlined, PlusOutlined, CheckOutlined } from '@ant-design/icons';
import axios from 'axios';
import StockKlineModal from './StockKlineModal';

const { TextArea } = Input;

const WencaiAssistant = ({ visible, onClose, dateStr, type = 'breakout', nextDayBlocks = [] }) => {
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState([]);
  const [isMobile, setIsMobile] = useState(false);
  const [queryType, setQueryType] = useState('breakthrough');
  const [watchlistCodes, setWatchlistCodes] = useState([]);
  const [klineVisible, setKlineVisible] = useState(false);
  const [selectedStock, setSelectedStock] = useState(null);

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
    
    const top3Blocks = nextDayBlocks.slice(0, 3).map(b => b.block_name).join('、');
    const blockCondition = top3Blocks ? `所属板块是 ${top3Blocks}` : '所属概念为近期热门题材';
    
    // 默认提示词
    if (queryType === 'default') {
      return `${dateFormatted} 涨停 显示涨停原因类别 显示概念
非ST 非科创板 非北交所
${dateFormatted} 前60个交易日未创年度新高 放量上涨 站稳前期高点 非连续加速创新高
近1年涨停次数大于等于2次 近1月涨幅大于等于10%
${blockCondition}`;
    }
    
    // 新高突破提示词
    if (queryType === 'breakthrough') {
      return `${dateFormatted} 涨停 显示涨停原因类别 显示概念
非ST 非科创板 非北交所 非创业板 
当天最高价大于等于120日内最高价的90%
近1年涨停次数大于等于2次 显示近1月涨幅`;
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
        const codes = response.data.data.map(stock => stock.stock_code);
        setWatchlistCodes(codes);
      }
    } catch (error) {
      console.error('加载自选股列表失败:', error);
    }
  };

  useEffect(() => {
    if (visible) {
      setQuery(getQueryByType(queryType, dateStr));
      setResult([]);
      loadWatchlistCodes();
    }
  }, [visible, dateStr, queryType]);

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
      const stockCode = record['股票代码'];
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

  const columns = [
    {
      title: '股票信息',
      key: 'stockInfo',
      width: isMobile ? 90 : 100,
      fixed: 'left',
      render: (_, record) => (
        <div style={{ lineHeight: '18px' }}>
          <div 
            style={{ fontWeight: 'bold', color: '#1890ff', fontSize: isMobile ? 12 : 13, cursor: 'pointer' }}
            onClick={() => {
              setSelectedStock({ code: record['股票代码'], name: record['股票简称'] });
              setKlineVisible(true);
            }}
          >
            {record['股票代码']}
          </div>
          <div 
            style={{ fontSize: isMobile ? 11 : 12, color: '#262626', fontWeight: 'bold', cursor: 'pointer' }}
            onClick={() => {
              setSelectedStock({ code: record['股票代码'], name: record['股票简称'] });
              setKlineVisible(true);
            }}
          >
            {record['股票简称']}
          </div>
        </div>
      ),
    },
    {
      title: '价格信息',
      key: 'priceInfo',
      width: isMobile ? 70 : 80,
      render: (_, record) => {
        const changeVal = record['最新涨跌幅'];
        const priceVal = record['最新价'];
        
        if (!changeVal && !priceVal) return '-';
        
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
        if (!val) return '-';
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
        if (!val) return '-';
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
        if (!val) return '-';
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
      render: (_, record) => (
        <Button
          type="primary"
          size="small"
          icon={<PlusOutlined />}
          onClick={() => handleAddToWatchlist(record)}
          style={{ fontSize: isMobile ? 11 : 12 }}
        >
          {isMobile ? '' : '自选'}
        </Button>
      ),
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
          
          const stockCode = record['股票代码'];
          const isAdded = watchlistCodes.includes(stockCode);
          
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
                    style={{ fontWeight: 'bold', color: '#1890ff', fontSize: 13, cursor: 'pointer' }}
                    onClick={() => {
                      setSelectedStock({ code: record['股票代码'], name: record['股票简称'] });
                      setKlineVisible(true);
                    }}
                  >
                    {record['股票代码']}
                  </div>
                  <div 
                    style={{ fontSize: 12, color: '#262626', fontWeight: 'bold', cursor: 'pointer' }}
                    onClick={() => {
                      setSelectedStock({ code: record['股票代码'], name: record['股票简称'] });
                      setKlineVisible(true);
                    }}
                  >
                    {record['股票简称']}
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
        <div style={{ marginBottom: isMobile ? 6 : 8 }}>
          <Radio.Group 
            value={queryType} 
            onChange={(e) => setQueryType(e.target.value)}
            size={isMobile ? 'small' : 'middle'}
            style={{ width: '100%' }}
          >
            <Radio.Button value="default" style={{ fontSize: isMobile ? 11 : 12 }}>默认策略</Radio.Button>
            <Radio.Button value="breakthrough" style={{ fontSize: isMobile ? 11 : 12 }}>新高突破</Radio.Button>
          </Radio.Group>
        </div>
        <TextArea
          rows={4}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="输入自然语言查询语句..."
          style={{ 
            fontFamily: 'monospace', 
            fontSize: isMobile ? 12 : 13,
            borderRadius: 4,
            minHeight: isMobile ? '100px' : '120px'
          }}
        />
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
    </Modal>
  );
};

export default WencaiAssistant;
