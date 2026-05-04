import React, { useState, useEffect } from 'react';
import { Card, Table, Button, message, Spin, Popconfirm, Tag, Statistic, Row, Col } from 'antd';
import { DeleteOutlined, ReloadOutlined, SyncOutlined, RiseOutlined, FallOutlined } from '@ant-design/icons';
import axios from 'axios';
import { useGlobal } from '../contexts/GlobalContext';

const WatchlistPage = () => {
  const { loading, setLoading } = useGlobal();
  const [watchlist, setWatchlist] = useState([]);
  const [isMobile, setIsMobile] = useState(false);

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
      const isDev = import.meta.env.DEV;
      const API_BASE = isDev ? 'http://localhost:5001/api' : '/api';
      
      const response = await axios.get(`${API_BASE}/watchlist`);
      
      if (response.data.success) {
        setWatchlist(response.data.data || []);
      } else {
        message.error('加载自选股失败');
      }
    } catch (error) {
      message.error('加载自选股失败：' + (error.response?.data?.error || error.message));
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (stockCode) => {
    try {
      const isDev = import.meta.env.DEV;
      const API_BASE = isDev ? 'http://localhost:5001/api' : '/api';
      
      const response = await axios.delete(`${API_BASE}/watchlist/${stockCode}`);
      
      if (response.data.success) {
        message.success('删除成功');
        loadWatchlist();
      } else {
        message.error(response.data.error || '删除失败');
      }
    } catch (error) {
      message.error('删除失败：' + (error.response?.data?.error || error.message));
    }
  };

  const handleRefresh = async () => {
    setLoading(true);
    try {
      const isDev = import.meta.env.DEV;
      const API_BASE = isDev ? 'http://localhost:5001/api' : '/api';
      
      // 先更新价格
      const updateResponse = await axios.post(`${API_BASE}/watchlist/update-prices`);
      
      if (updateResponse.data.success) {
        // 然后重新加载列表
        const listResponse = await axios.get(`${API_BASE}/watchlist`);
        
        if (listResponse.data.success) {
          setWatchlist(listResponse.data.data || []);
          message.success(`已更新价格并刷新列表`);
        }
      } else {
        message.error(updateResponse.data.error || '更新失败');
      }
    } catch (error) {
      message.error('刷新失败：' + (error.response?.data?.error || error.message));
    } finally {
      setLoading(false);
    }
  };

  const columns = [
    {
      title: '股票信息',
      key: 'stockInfo',
      width: isMobile ? 100 : 120,
      fixed: 'left',
      render: (_, record) => (
        <div style={{ lineHeight: '18px' }}>
          <div style={{ fontWeight: 'bold', fontSize: isMobile ? 12 : 13 }}>{record.stock_code}</div>
          <div style={{ fontSize: isMobile ? 11 : 12, color: '#666' }}>{record.stock_name}</div>
        </div>
      ),
    },
    {
      title: '加入日期',
      dataIndex: 'add_date',
      key: 'add_date',
      width: isMobile ? 90 : 100,
      render: (val) => (
        <span style={{ fontSize: isMobile ? 11 : 12 }}>
          {val ? `${val.slice(0, 4)}-${val.slice(4, 6)}-${val.slice(6, 8)}` : '-'}
        </span>
      ),
    },
    {
      title: '加入价格',
      dataIndex: 'add_price',
      key: 'add_price',
      width: isMobile ? 80 : 100,
      render: (val) => (
        <span style={{ fontWeight: 'bold', fontSize: isMobile ? 12 : 13 }}>
          {val ? `¥${val.toFixed(2)}` : '-'}
        </span>
      ),
    },
    {
      title: '当前价格',
      dataIndex: 'current_price',
      key: 'current_price',
      width: isMobile ? 80 : 100,
      render: (val) => (
        <span style={{ fontWeight: 'bold', fontSize: isMobile ? 12 : 13 }}>
          {val ? `¥${val.toFixed(2)}` : '-'}
        </span>
      ),
    },
    {
      title: '盈亏金额',
      dataIndex: 'profit_amount',
      key: 'profit_amount',
      width: isMobile ? 80 : 100,
      render: (val, record) => {
        if (!val) return '-';
        const numVal = parseFloat(val);
        const color = numVal > 0 ? '#f5222d' : numVal < 0 ? '#52c41a' : '#666';
        const icon = numVal > 0 ? <RiseOutlined /> : numVal < 0 ? <FallOutlined /> : null;
        return (
          <span style={{ fontWeight: 'bold', fontSize: isMobile ? 12 : 13, color }}>
            {icon} ¥{numVal.toFixed(2)}
          </span>
        );
      },
    },
    {
      title: '盈亏比例',
      dataIndex: 'profit_ratio',
      key: 'profit_ratio',
      width: isMobile ? 80 : 100,
      render: (val, record) => {
        if (!val) return '-';
        const numVal = parseFloat(val);
        const color = numVal > 0 ? '#f5222d' : numVal < 0 ? '#52c41a' : '#666';
        return (
          <span style={{ fontWeight: 'bold', fontSize: isMobile ? 12 : 13, color }}>
            {numVal > 0 ? '+' : ''}{(numVal * 100).toFixed(2)}%
          </span>
        );
      },
    },
    {
      title: '加入原因',
      dataIndex: 'add_reason',
      key: 'add_reason',
      width: isMobile ? 150 : 200,
      ellipsis: true,
      render: (val) => (
        <span style={{ fontSize: isMobile ? 11 : 12 }}>{val || '-'}</span>
      ),
    },
    {
      title: '来源',
      dataIndex: 'source',
      key: 'source',
      width: isMobile ? 70 : 80,
      render: (val) => {
        const colorMap = {
          'wencai': 'blue',
          'manual': 'green'
        };
        const textMap = {
          'wencai': '问财',
          'manual': '手动'
        };
        return (
          <Tag color={colorMap[val] || 'default'} style={{ fontSize: isMobile ? 10 : 11 }}>
            {textMap[val] || val || '-'}
          </Tag>
        );
      },
    },
    {
      title: '加入时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: isMobile ? 120 : 150,
      render: (val) => (
        <span style={{ fontSize: isMobile ? 11 : 12 }}>{val || '-'}</span>
      ),
    },
    {
      title: '操作',
      key: 'action',
      width: isMobile ? 60 : 80,
      fixed: 'right',
      render: (_, record) => (
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
            style={{ fontSize: isMobile ? 11 : 12 }}
          >
            {isMobile ? '' : '删除'}
          </Button>
        </Popconfirm>
      ),
    },
  ];

  const renderMobileContent = () => {
    if (watchlist.length === 0) {
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
        {watchlist.map((record) => {
          const profitAmount = record.profit_amount ? parseFloat(record.profit_amount) : null;
          const profitRatio = record.profit_ratio ? parseFloat(record.profit_ratio) : null;
          const profitColor = profitAmount > 0 ? '#f5222d' : profitAmount < 0 ? '#52c41a' : '#666';
          const profitIcon = profitAmount > 0 ? <RiseOutlined /> : profitAmount < 0 ? <FallOutlined /> : null;
          
          return (
            <Card
              key={record.id}
              size="small"
              style={{ 
                marginBottom: 8,
                border: profitAmount > 0 ? '1px solid #ffccc7' : profitAmount < 0 ? '1px solid #b7eb8f' : '1px solid #f0f0f0'
              }}
              styles={{ body: { padding: '10px' } }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
                <div>
                  <div style={{ fontWeight: 'bold', color: '#1890ff', fontSize: 14 }}>{record.stock_code}</div>
                  <div style={{ fontSize: 12, color: '#666' }}>{record.stock_name}</div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  {profitAmount !== null && (
                    <>
                      <div style={{ color: profitColor, fontWeight: 'bold', fontSize: 16 }}>
                        {profitIcon} ¥{profitAmount.toFixed(2)}
                      </div>
                      <div style={{ fontSize: 12, color: profitColor }}>
                        {profitRatio > 0 ? '+' : ''}{(profitRatio * 100).toFixed(2)}%
                      </div>
                    </>
                  )}
                </div>
              </div>
              
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, marginBottom: 6, padding: '6px 0', borderTop: '1px dashed #f0f0f0' }}>
                <div>
                  <span style={{ color: '#999' }}>加入：</span>
                  <span style={{ fontWeight: 'bold' }}>
                    {record.add_date ? `${record.add_date.slice(0, 4)}-${record.add_date.slice(4, 6)}-${record.add_date.slice(6, 8)}` : '-'}
                  </span>
                </div>
                <div>
                  <span style={{ color: '#999' }}>加入价：</span>
                  <span style={{ fontWeight: 'bold' }}>
                    ¥{record.add_price ? record.add_price.toFixed(2) : '-'}
                  </span>
                </div>
                <div>
                  <span style={{ color: '#999' }}>现价：</span>
                  <span style={{ fontWeight: 'bold', color: profitColor }}>
                    ¥{record.current_price ? record.current_price.toFixed(2) : '-'}
                  </span>
                </div>
              </div>
              
              {record.add_reason && (
                <div style={{ fontSize: 10, color: '#999', marginBottom: 6, padding: '4px 6px', background: '#f5f5f5', borderRadius: 4 }}>
                  {record.add_reason.substring(0, 50)}{record.add_reason.length > 50 ? '...' : ''}
                </div>
              )}
              
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 8 }}>
                <Tag color={record.source === 'wencai' ? 'blue' : 'green'} style={{ fontSize: 10, margin: 0 }}>
                  {record.source === 'wencai' ? '问财' : '手动'}
                </Tag>
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
                    style={{ fontSize: 10 }}
                  >
                    删除
                  </Button>
                </Popconfirm>
              </div>
            </Card>
          );
        })}
      </div>
    );
  };

  const renderDesktopContent = () => {
    if (watchlist.length === 0) {
      return (
        <div style={{ 
          textAlign: 'center', 
          padding: '60px 20px', 
          color: '#999',
          fontSize: 14 
        }}>
          暂无自选股
        </div>
      );
    }
    
    return (
      <Table
        columns={columns}
        dataSource={watchlist}
        rowKey="id"
        loading={loading}
        scroll={{ x: 1100 }}
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
      <Card
        title={
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: isMobile ? 14 : 16 }}>自选回溯</span>
            <Button
              icon={<SyncOutlined />}
              onClick={handleRefresh}
              loading={loading}
              size="small"
              type="primary"
              style={{ fontSize: isMobile ? 11 : 12 }}
            >
              {isMobile ? '' : '刷新'}
            </Button>
          </div>
        }
        style={{ marginBottom: 16 }}
      >
        <div style={{ marginBottom: 12, fontSize: isMobile ? 11 : 12, color: '#666' }}>
          共 {watchlist.length} 只自选股
        </div>
        
        {isMobile ? renderMobileContent() : renderDesktopContent()}
      </Card>
    </div>
  );
};

export default WatchlistPage;
