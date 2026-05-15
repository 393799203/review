import React, { useState, useEffect } from 'react';
import { Card, Table, Button, message, Spin, Popconfirm, Tag, Modal, InputNumber, Form, Tooltip } from 'antd';
import { DeleteOutlined, ShoppingCartOutlined, DollarOutlined } from '@ant-design/icons';
import axios from 'axios';
import { useGlobal } from '../contexts/GlobalContext';
import { stockApi } from '../services/api';
import StockKlineModal from '../components/StockKlineModal';

const WatchlistPage = () => {
  const { loading, setLoading } = useGlobal();
  const [watchlist, setWatchlist] = useState([]);
  const [isMobile, setIsMobile] = useState(false);
  const [buyModalVisible, setBuyModalVisible] = useState(false);
  const [sellModalVisible, setSellModalVisible] = useState(false);
  const [selectedStock, setSelectedStock] = useState(null);
  const [buyForm] = Form.useForm();
  const [sellForm] = Form.useForm();
  const [klineVisible, setKlineVisible] = useState(false);
  const [klineStock, setKlineStock] = useState(null);

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
          const isHolding = record.position_status === '持仓';
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
          
          return (
            <Card
              key={record.id}
              size="small"
              style={{ 
                marginBottom: 8,
                borderLeft: `3px solid ${totalProfitColor}`,
                background: `${totalProfitColor}08`,
                position: 'relative',
                overflow: 'hidden',
              }}
              styles={{ body: { padding: '8px 10px' } }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div style={{ flex: 1 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
                    <span 
                      style={{ fontWeight: 'bold', fontSize: 14, color: '#1890ff', cursor: 'pointer' }}
                      onClick={() => {
                        setKlineStock({ code: record.stock_code.split('.')[0], name: record.stock_name });
                        setKlineVisible(true);
                      }}
                    >
                      {record.stock_code.split('.')[0]}
                    </span>
                    <span 
                      style={{ fontWeight: 'bold', fontSize: 14, color: '#262626', cursor: 'pointer' }}
                      onClick={() => {
                        setKlineStock({ code: record.stock_code.split('.')[0], name: record.stock_name });
                        setKlineVisible(true);
                      }}
                    >
                      {record.stock_name}
                    </span>
                    <Tag color={isHolding ? 'blue' : 'default'} style={{ fontSize: 10, margin: 0, padding: '0 4px' }}>
                      {isHolding ? '持仓' : '空仓'}
                    </Tag>
                    <Tag color="purple" style={{ fontSize: 10, margin: 0, padding: '0 4px' }}>
                      {record.add_date ? `${record.add_date.slice(4, 6)}-${record.add_date.slice(6, 8)}` : '-'}
                    </Tag>
                  </div>
                  <div style={{ display: 'flex', gap: 8, fontSize: 11, color: '#595959' }}>
                    {isHolding ? (
                      <>
                        <span>买入: <span style={{ fontWeight: 'bold', color: '#1890ff' }}>¥{record.buy_price ? record.buy_price.toFixed(2) : '-'}</span></span>
                        <span>×{record.buy_quantity}股</span>
                      </>
                    ) : (
                      <span>加入: <span style={{ fontWeight: 'bold', color: '#262626' }}>¥{record.add_price ? record.add_price.toFixed(2) : '-'}</span></span>
                    )}
                    <span>现价: <span style={{ fontWeight: 'bold', color: profitColor }}>¥{record.current_price ? record.current_price.toFixed(2) : '-'}</span></span>
                    {addPriceChange !== null && (
                      <span style={{ fontWeight: 'bold', color: addPriceChangeColor }}>
                        ({addPriceChange > 0 ? '+' : ''}{addPriceChange.toFixed(2)}%)
                      </span>
                    )}
                  </div>
                </div>
                <div style={{ textAlign: 'right', marginLeft: 10, minWidth: 85 }}>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                    <div style={{ fontSize: 12, fontWeight: 'bold', color: totalProfitColor }}>
                      累计: {totalProfit.toFixed(0)}
                    </div>
                    {isHolding && positionProfit !== null && (
                      <div style={{ fontSize: 12, fontWeight: 'bold', color: profitColor }}>
                        盈亏: {positionProfit.toFixed(0)}
                        <span style={{ fontSize: 10, marginLeft: 2 }}>{positionProfitRatio > 0 ? '+' : ''}{profitPercent}%</span>
                      </div>
                    )}
                  </div>
                </div>
              </div>
              
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 6, gap: 4 }}>
                <div style={{ flex: 1 }}>
                  {record.limit_up_reason_category && (
                    <Tag color="blue" style={{ fontSize: 10, margin: 0 }}>
                      {record.limit_up_reason_category}
                    </Tag>
                  )}
                </div>
                <div style={{ display: 'flex', gap: 4 }}>
                  <Button
                    type="primary"
                    size="small"
                    icon={<ShoppingCartOutlined />}
                    onClick={() => handleBuy(record)}
                    style={{ fontSize: 10, padding: '0 8px', height: 22 }}
                  >
                    买入
                  </Button>
                  {isHolding && (
                    <Button
                      type="primary"
                      size="small"
                      icon={<DollarOutlined />}
                      onClick={() => handleSell(record)}
                      style={{ fontSize: 10, padding: '0 8px', height: 22 }}
                    >
                      卖出
                    </Button>
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
                        style={{ fontSize: 10, padding: '0 8px', height: 22 }}
                      >
                        删除
                      </Button>
                    </Popconfirm>
                  )}
                </div>
              </div>
            </Card>
          );
        })}
      </div>
    );
  };

  const renderDesktopContent = () => {
    const columns = [
      {
        title: '股票代码',
        dataIndex: 'stock_code',
        key: 'stock_code',
        width: 100,
        render: (text, record) => (
          <span 
            style={{ color: '#1890ff', cursor: 'pointer' }}
            onClick={() => {
              setKlineStock({ code: text.split('.')[0], name: record.stock_name });
              setKlineVisible(true);
            }}
          >
            {text.split('.')[0]}
          </span>
        ),
      },
      {
        title: '股票名称',
        dataIndex: 'stock_name',
        key: 'stock_name',
        width: 100,
        render: (text, record) => (
          <span 
            style={{ cursor: 'pointer' }}
            onClick={() => {
              setKlineStock({ code: record.stock_code.split('.')[0], name: text });
              setKlineVisible(true);
            }}
          >
            {text}
          </span>
        ),
      },
      {
        title: '持仓状态',
        dataIndex: 'position_status',
        key: 'position_status',
        width: 80,
        render: (text) => (
          <Tag color={text === '持仓' ? 'blue' : 'default'}>
            {text || '空仓'}
          </Tag>
        ),
      },
      {
        title: '加入价格',
        dataIndex: 'add_price',
        key: 'add_price',
        width: 100,
        render: (value) => value ? `¥${value.toFixed(2)}` : '-',
      },
      {
        title: '当前价格',
        dataIndex: 'current_price',
        key: 'current_price',
        width: 100,
        render: (value, record) => {
          const color = record.position_status === '持仓' && record.position_profit > 0 ? '#f5222d' : 
                       record.position_status === '持仓' && record.position_profit < 0 ? '#52c41a' : '#262626';
          return value ? <span style={{ color, fontWeight: 'bold' }}>¥{value.toFixed(2)}</span> : '-';
        },
      },
      {
        title: '较加入价涨跌',
        key: 'add_price_change',
        width: 120,
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
        title: '买入信息',
        key: 'buy_info',
        width: 150,
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
        title: '持仓盈亏',
        dataIndex: 'position_profit',
        key: 'position_profit',
        width: 120,
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
        title: '策略日期',
        key: 'source_info',
        width: 100,
        render: (_, record) => (
          <Tag color="purple" style={{ fontSize: 11 }}>
            {record.add_date ? `${record.add_date.slice(4, 6)}-${record.add_date.slice(6, 8)}` : '-'}
          </Tag>
        ),
      },
      {
        title: '涨停原因',
        dataIndex: 'limit_up_reason_category',
        key: 'limit_up_reason_category',
        width: 150,
        ellipsis: true,
        render: (text) => {
          if (!text) return '-';
          return (
            <Tooltip title={text}>
              <Tag color="blue" style={{ fontSize: 11 }}>
                {text}
              </Tag>
            </Tooltip>
          );
        },
      },
      {
        title: '操作',
        key: 'action',
        width: 150,
        fixed: 'right',
        render: (_, record) => (
          <div style={{ display: 'flex', gap: 4 }}>
            {record.position_status === '持仓' ? (
              <Button
                type="primary"
                size="small"
                icon={<DollarOutlined />}
                onClick={() => handleSell(record)}
              >
                卖出
              </Button>
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
        dataSource={watchlist}
        rowKey="id"
        loading={loading}
        scroll={{ x: 1300 }}
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
        style={{ marginBottom: 8 }}
        styles={{ body: { padding: isMobile ? '8px' : '12px' } }}
      >
        <Spin spinning={loading} description="加载中...">
          <div style={{ marginBottom: 8, fontSize: isMobile ? 11 : 12, color: '#8c8c8c' }}>
            共 {watchlist.length} 只自选股，{watchlist.filter(s => s.position_status === '持仓').length} 只持仓中
          </div>
          
          {isMobile ? renderMobileContent() : renderDesktopContent()}
        </Spin>
      </Card>

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

      <StockKlineModal
        visible={klineVisible}
        stockCode={klineStock?.code}
        stockName={klineStock?.name}
        onClose={() => {
          setKlineVisible(false);
          setKlineStock(null);
        }}
      />
    </div>
  );
};

export default WatchlistPage;
