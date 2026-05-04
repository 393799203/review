import React, { useState, useEffect } from 'react';
import { Modal, Input, Button, Table, message, Spin, Tooltip, Card, Tag } from 'antd';
import { SearchOutlined, RobotOutlined } from '@ant-design/icons';
import axios from 'axios';

const { TextArea } = Input;

const WencaiAssistant = ({ visible, onClose, dateStr, type = 'breakout', nextDayBlocks = [] }) => {
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState([]);
  const [isMobile, setIsMobile] = useState(false);

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
    
    if (queryType === 'blockStrength') {
      return `${dateFormatted} 涨停
按板块统计涨停数量
显示板块名称、涨停数量
按涨停数量降序排列
取前3名`;
    }
    
    const top3Blocks = nextDayBlocks.slice(0, 3).map(b => b.block_name).join('、');
    const blockCondition = top3Blocks ? `所属板块是 ${top3Blocks}` : '所属概念为近期热门题材';
    
    return `${dateFormatted} 涨停
非ST 非科创板 非北交所
${dateFormatted} 前60个交易日未创年度新高 放量上涨 站稳前期高点 非连续加速创新高
${dateFormatted} 近1年涨停次数大于等于2次 近1月涨幅大于等于10%
${blockCondition}`;
  };

  const getTitleByType = (queryType) => {
    if (queryType === 'blockStrength') {
      return '次日板块强度';
    }
    return '问财智能助手';
  };

  React.useEffect(() => {
    if (visible) {
      setQuery(getQueryByType(type, dateStr));
      setResult([]);
    }
  }, [visible, dateStr, type]);

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

  const columns = [
    {
      title: '股票信息',
      key: 'stockInfo',
      width: isMobile ? 90 : 100,
      fixed: 'left',
      render: (_, record) => (
        <div style={{ lineHeight: '18px' }}>
          <div style={{ fontWeight: 'bold', color: '#1890ff', fontSize: isMobile ? 12 : 13 }}>{record['股票代码']}</div>
          <div style={{ fontSize: isMobile ? 11 : 12, color: '#666' }}>{record['股票简称']}</div>
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
  ];

  const tableColumns = columns;

  const renderMobileContent = () => {
    if (result.length === 0) return null;
    
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
          
          return (
            <Card
              key={index}
              size="small"
              style={{ marginBottom: 8 }}
              styles={{ body: { padding: '8px 10px' } }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 6 }}>
                <div>
                  <div style={{ fontWeight: 'bold', color: '#1890ff', fontSize: 13 }}>{record['股票代码']}</div>
                  <div style={{ fontSize: 12, color: '#666' }}>{record['股票简称']}</div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <div style={{ color: changeColor, fontWeight: 'bold', fontSize: 14 }}>
                    {numChange ? `${numChange.toFixed(2)}%` : '-'}
                  </div>
                  <div style={{ fontSize: 12, color: '#666' }}>¥{priceVal || '-'}</div>
                </div>
              </div>
              
              {reasonVal && (
                <div style={{ marginBottom: 6 }}>
                  <Tag color="blue" style={{ fontSize: 10, margin: 0 }}>{reasonVal}</Tag>
                </div>
              )}
              
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
    if (result.length === 0) return null;
    
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
    </Modal>
  );
};

export default WencaiAssistant;
