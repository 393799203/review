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
    
    return `${dateFormatted} 涨停 连板高度不大于2板
非ST 非科创板 非北交所
股价大于等于120日最高价的95%
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
      title: '连板情况',
      key: 'continuousDays',
      width: isMobile ? 80 : 100,
      render: (_, record) => {
        const daysKey = Object.keys(record).find(k => k.includes('连续涨停天数'));
        const boardsKey = Object.keys(record).find(k => k.includes('几天几板'));
        const days = record[daysKey];
        const boards = record[boardsKey];
        
        if (!days && !boards) return '-';
        
        const color = days >= 5 ? '#f5222d' : days >= 3 ? '#fa8c16' : '#1890ff';
        
        return (
          <div style={{ lineHeight: '18px' }}>
            <div style={{ color, fontWeight: 'bold', fontSize: isMobile ? 12 : 13 }}>{boards || `${days}天${days}板`}</div>
            {days && <div style={{ fontSize: isMobile ? 10 : 11, color: '#999' }}>连续{days}天</div>}
          </div>
        );
      },
    },
    {
      title: '强度',
      key: 'strength',
      width: isMobile ? 80 : 100,
      render: (_, record) => {
        const sealKey = Object.keys(record).find(k => k.includes('涨停封单额['));
        const timeKey = Object.keys(record).find(k => k.includes('首次涨停时间'));
        const sealVal = record[sealKey];
        const timeVal = record[timeKey];
        
        return (
          <div style={{ lineHeight: '18px' }}>
            <div style={{ fontSize: isMobile ? 11 : 12 }}>
              {sealVal && typeof sealVal === 'number' ? `${(sealVal / 100000000).toFixed(2)}亿` : '-'}
            </div>
            <div style={{ fontSize: isMobile ? 10 : 11, color: '#999' }}>{timeVal || '-'}</div>
          </div>
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
          
          const daysKey = Object.keys(record).find(k => k.includes('连续涨停天数'));
          const boardsKey = Object.keys(record).find(k => k.includes('几天几板'));
          const days = record[daysKey];
          const boards = record[boardsKey];
          const daysColor = days >= 5 ? '#f5222d' : days >= 3 ? '#fa8c16' : '#1890ff';
          
          const reasonKey = Object.keys(record).find(k => k.includes('涨停原因类别'));
          const reasonVal = record[reasonKey];
          
          const sealKey = Object.keys(record).find(k => k.includes('涨停封单额['));
          const timeKey = Object.keys(record).find(k => k.includes('首次涨停时间'));
          const sealVal = record[sealKey];
          const timeVal = record[timeKey];
          
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
              
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11 }}>
                <div>
                  <span style={{ color: '#999' }}>连板：</span>
                  <span style={{ color: daysColor, fontWeight: 'bold' }}>
                    {boards || (days ? `${days}天${days}板` : '-')}
                  </span>
                </div>
                <div>
                  <span style={{ color: '#999' }}>封单：</span>
                  <span style={{ fontWeight: 'bold' }}>
                    {sealVal && typeof sealVal === 'number' ? `${(sealVal / 100000000).toFixed(2)}亿` : '-'}
                  </span>
                </div>
                <div>
                  <span style={{ color: '#999' }}>时间：</span>
                  <span>{timeVal || '-'}</span>
                </div>
              </div>
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
