import React, { useState, useEffect } from 'react';
import { Card, Row, Col, Statistic, Table, Tag, Spin, message, Radio, Divider } from 'antd';
import { ArrowUpOutlined, ArrowDownOutlined, TrophyOutlined, FallOutlined, RiseOutlined } from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';
import axios from 'axios';
import { useGlobal } from '../contexts/GlobalContext';

const StatisticsPage = () => {
  const { refreshKey } = useGlobal();
  const [period, setPeriod] = useState('day');
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [trades, setTrades] = useState([]);
  const [isMobile, setIsMobile] = useState(window.innerWidth < 768);

  useEffect(() => {
    const handleResize = () => {
      setIsMobile(window.innerWidth < 768);
    };
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  useEffect(() => {
    loadStatistics();
    loadTrades();
  }, [period, refreshKey]);

  const loadStatistics = async () => {
    setLoading(true);
    try {
      const isDev = import.meta.env.DEV;
      const API_BASE = isDev ? 'http://localhost:5001/api' : '/api';
      
      const response = await axios.get(`${API_BASE}/statistics/profit?period=${period}`);
      
      if (response.data.success) {
        setData(response.data.data || []);
      } else {
        message.error('加载统计数据失败');
      }
    } catch (error) {
      message.error('加载统计数据失败：' + (error.response?.data?.error || error.message));
    } finally {
      setLoading(false);
    }
  };

  const loadTrades = async () => {
    try {
      const isDev = import.meta.env.DEV;
      const API_BASE = isDev ? 'http://localhost:5001/api' : '/api';
      
      const response = await axios.get(`${API_BASE}/trade-records`);
      
      if (response.data.success) {
        const sellRecords = response.data.data.filter(item => item.operation_type === '卖出' && item.profit !== null);
        setTrades(sellRecords);
      }
    } catch (error) {
      console.error('加载交易记录失败:', error);
    }
  };

  const getTotalProfit = () => {
    return trades.reduce((sum, item) => sum + parseFloat(item.profit || 0), 0);
  };

  const getTotalCount = () => {
    return trades.length;
  };

  const getWinCount = () => {
    return trades.filter(item => parseFloat(item.profit || 0) > 0).length;
  };

  const getLossCount = () => {
    return trades.filter(item => parseFloat(item.profit || 0) < 0).length;
  };

  const getWinRate = () => {
    const total = getTotalCount();
    if (total === 0) return 0;
    return (getWinCount() / total * 100).toFixed(1);
  };

  const getAverageProfit = () => {
    const total = getTotalCount();
    if (total === 0) return 0;
    return getTotalProfit() / total;
  };

  const getMaxProfit = () => {
    if (trades.length === 0) return 0;
    return Math.max(...trades.map(item => parseFloat(item.profit || 0)));
  };

  const getMaxLoss = () => {
    if (trades.length === 0) return 0;
    const lossTrades = trades.filter(item => parseFloat(item.profit || 0) < 0);
    if (lossTrades.length === 0) return 0;
    return Math.min(...lossTrades.map(item => parseFloat(item.profit || 0)));
  };

  const getProfitLossRatio = () => {
    const winTrades = trades.filter(item => parseFloat(item.profit || 0) > 0);
    const lossTrades = trades.filter(item => parseFloat(item.profit || 0) < 0);
    
    if (winTrades.length === 0 || lossTrades.length === 0) return '-';
    
    const avgWin = winTrades.reduce((sum, item) => sum + parseFloat(item.profit || 0), 0) / winTrades.length;
    const avgLoss = Math.abs(lossTrades.reduce((sum, item) => sum + parseFloat(item.profit || 0), 0) / lossTrades.length);
    
    if (avgLoss === 0) return '-';
    return (avgWin / avgLoss).toFixed(2);
  };

  const getTrendOption = () => {
    if (data.length === 0) {
      return {
        title: {
          text: '暂无数据',
          left: 'center',
          top: 'center',
          textStyle: { color: '#999', fontSize: 12 }
        }
      };
    }

    const dates = data.map(item => item.date);
    const profits = data.map(item => item.profit);
    const amounts = data.map(item => item.amount || 0);
    const cumulativeProfits = [];
    const cumulativeReturns = [];
    let cumulativeProfit = 0;
    let cumulativeAmount = 0;
    
    profits.forEach((profit, index) => {
      cumulativeProfit += profit;
      cumulativeAmount += amounts[index];
      cumulativeProfits.push(cumulativeProfit);
      // 计算累计收益率
      const returnRate = cumulativeAmount > 0 ? (cumulativeProfit / cumulativeAmount) * 100 : 0;
      cumulativeReturns.push(returnRate);
    });

    return {
      title: {
        text: '盈亏趋势',
        left: 'center',
        textStyle: { fontSize: 14 }
      },
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'cross' },
        formatter: function(params) {
          let result = params[0].axisValue + '<br/>';
          params.forEach(param => {
            if (param.seriesName === '盈亏金额') {
              result += `${param.marker}${param.seriesName}: ¥${param.value.toFixed(2)}<br/>`;
            } else if (param.seriesName === '累计收益率') {
              result += `${param.marker}${param.seriesName}: ${param.value.toFixed(2)}%<br/>`;
            }
          });
          return result;
        }
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '3%',
        containLabel: true
      },
      xAxis: {
        type: 'category',
        data: dates,
        axisLabel: { rotate: 45, fontSize: 10 }
      },
      yAxis: [
        {
          type: 'value',
          name: '盈亏金额',
          position: 'left',
          axisLabel: { formatter: '¥{value}', fontSize: 10 },
          nameTextStyle: { fontSize: 10 }
        },
        {
          type: 'value',
          name: '累计收益率',
          position: 'right',
          axisLabel: { formatter: '{value}%', fontSize: 10 },
          nameTextStyle: { fontSize: 10 }
        }
      ],
      series: [
        {
          name: '盈亏金额',
          type: 'bar',
          data: profits,
          itemStyle: {
            color: params => params.value > 0 ? '#f5222d' : params.value < 0 ? '#52c41a' : '#8c8c8c'
          }
        },
        {
          name: '累计收益率',
          type: 'line',
          yAxisIndex: 1,
          data: cumulativeReturns,
          itemStyle: { color: '#1890ff' },
          lineStyle: { width: 2 },
          symbol: 'circle',
          symbolSize: 4
        }
      ]
    };
  };

  const getPieOption = () => {
    const winCount = getWinCount();
    const lossCount = getLossCount();
    
    if (winCount === 0 && lossCount === 0) {
      return {
        title: {
          text: '暂无数据',
          left: 'center',
          top: 'center',
          textStyle: { color: '#999', fontSize: 12 }
        }
      };
    }

    return {
      title: {
        text: '盈亏分布',
        left: 'center',
        textStyle: { fontSize: 14 }
      },
      tooltip: {
        trigger: 'item',
        formatter: '{b}: {c}笔 ({d}%)'
      },
      legend: {
        bottom: '5%',
        left: 'center',
        textStyle: { fontSize: 11 }
      },
      series: [{
        name: '交易笔数',
        type: 'pie',
        radius: ['40%', '65%'],
        center: ['50%', '45%'],
        itemStyle: {
          borderRadius: 6,
          borderColor: '#fff',
          borderWidth: 2
        },
        label: {
          show: true,
          formatter: '{b}\n{c}笔',
          fontSize: 11
        },
        data: [
          { value: winCount, name: '获利', itemStyle: { color: '#f5222d' } },
          { value: lossCount, name: '亏损', itemStyle: { color: '#52c41a' } }
        ]
      }]
    };
  };

  const tradeColumns = [
    {
      title: '股票代码',
      dataIndex: 'stock_code',
      key: 'stock_code',
      width: 100,
      render: text => text.split('.')[0]
    },
    {
      title: '股票名称',
      dataIndex: 'stock_name',
      key: 'stock_name',
      width: 100
    },
    {
      title: '操作类型',
      dataIndex: 'operation_type',
      key: 'operation_type',
      width: 80,
      render: (text) => (
        <Tag color={text === '买入' ? 'blue' : 'orange'}>{text}</Tag>
      )
    },
    {
      title: '买入价',
      dataIndex: 'buy_price',
      key: 'buy_price',
      width: 90,
      render: (value, record) => {
        if (record.operation_type === '卖出') {
          return value ? `¥${parseFloat(value).toFixed(2)}` : '-';
        }
        return record.price ? `¥${parseFloat(record.price).toFixed(2)}` : '-';
      }
    },
    {
      title: '卖出价',
      dataIndex: 'price',
      key: 'sell_price',
      width: 90,
      render: (value, record) => {
        if (record.operation_type === '卖出') {
          return value ? `¥${parseFloat(value).toFixed(2)}` : '-';
        }
        return '-';
      }
    },
    {
      title: '数量',
      dataIndex: 'quantity',
      key: 'quantity',
      width: 80,
      render: value => `${value}股`
    },
    {
      title: '盈亏',
      dataIndex: 'profit',
      key: 'profit',
      width: 100,
      render: value => {
        if (value === null || value === undefined) return '-';
        const profit = parseFloat(value || 0);
        const color = profit > 0 ? '#f5222d' : profit < 0 ? '#52c41a' : '#8c8c8c';
        return <span style={{ color, fontWeight: 'bold' }}>¥{profit.toFixed(2)}</span>;
      }
    },
    {
      title: '收益率',
      dataIndex: 'profit_ratio',
      key: 'profit_ratio',
      width: 90,
      render: value => {
        if (value === null || value === undefined) return '-';
        const ratio = parseFloat(value || 0) * 100;
        const color = ratio > 0 ? '#f5222d' : ratio < 0 ? '#52c41a' : '#8c8c8c';
        return <span style={{ color }}>{ratio > 0 ? '+' : ''}{ratio.toFixed(2)}%</span>;
      }
    },
    {
      title: '操作日期',
      dataIndex: 'operation_date',
      key: 'operation_date',
      width: 140,
      render: value => value ? value.substring(0, 16) : '-'
    }
  ];

  return (
    <div style={{ padding: 0 }}>
      <Spin spinning={loading}>
        <Row gutter={[8, 8]}>
          <Col span={24}>
            <Card size="small">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                <span style={{ fontSize: 14, fontWeight: 'bold' }}>盈亏统计</span>
                <Radio.Group value={period} onChange={(e) => setPeriod(e.target.value)} size="small">
                  <Radio.Button value="day">按日</Radio.Button>
                  <Radio.Button value="week">按周</Radio.Button>
                  <Radio.Button value="month">按月</Radio.Button>
                </Radio.Group>
              </div>
              
              <Row gutter={[8, 8]}>
                <Col xs={8} sm={6}>
                  <Card size="small" style={{ background: getTotalProfit() >= 0 ? '#fff1f0' : '#f6ffed' }} styles={{ body: { padding: '8px 10px' } }}>
                    <Statistic
                      title={<span style={{ fontSize: 10 }}>总盈亏</span>}
                      value={getTotalProfit()}
                      precision={2}
                      prefix="¥"
                      valueStyle={{ fontSize: 14, color: getTotalProfit() >= 0 ? '#f5222d' : '#52c41a' }}
                    />
                  </Card>
                </Col>
                <Col xs={8} sm={6}>
                  <Card size="small" styles={{ body: { padding: '8px 10px' } }}>
                    <Statistic
                      title={<span style={{ fontSize: 10 }}>交易笔数</span>}
                      value={getTotalCount()}
                      suffix="笔"
                      valueStyle={{ fontSize: 14 }}
                    />
                  </Card>
                </Col>
                <Col xs={8} sm={6}>
                  <Card size="small" style={{ background: '#e6f7ff' }} styles={{ body: { padding: '8px 10px' } }}>
                    <Statistic
                      title={<span style={{ fontSize: 10 }}>胜率</span>}
                      value={getWinRate()}
                      suffix="%"
                      valueStyle={{ fontSize: 14, color: '#1890ff' }}
                    />
                  </Card>
                </Col>
              </Row>

              <Row gutter={[8, 8]} style={{ marginTop: 8 }}>
                <Col xs={8} sm={6}>
                  <Card size="small" styles={{ body: { padding: '8px 10px' } }}>
                    <Statistic
                      title={<span style={{ fontSize: 10 }}>平均盈亏</span>}
                      value={getAverageProfit()}
                      precision={2}
                      prefix="¥"
                      valueStyle={{ fontSize: 14, color: getAverageProfit() >= 0 ? '#f5222d' : '#52c41a' }}
                    />
                  </Card>
                </Col>
                <Col xs={8} sm={6}>
                  <Card size="small" styles={{ body: { padding: '8px 10px' } }}>
                    <Statistic
                      title={<span style={{ fontSize: 10 }}>最大盈利</span>}
                      value={getMaxProfit()}
                      precision={2}
                      prefix={<><TrophyOutlined style={{ color: '#f5222d' }} /> ¥</>}
                      valueStyle={{ fontSize: 13, color: '#f5222d' }}
                    />
                  </Card>
                </Col>
                <Col xs={8} sm={6}>
                  <Card size="small" styles={{ body: { padding: '8px 10px' } }}>
                    <Statistic
                      title={<span style={{ fontSize: 10 }}>最大亏损</span>}
                      value={Math.abs(getMaxLoss())}
                      precision={2}
                      prefix={<><FallOutlined style={{ color: '#52c41a' }} /> ¥</>}
                      valueStyle={{ fontSize: 13, color: '#52c41a' }}
                    />
                  </Card>
                </Col>
              </Row>

              <Row gutter={[8, 8]} style={{ marginTop: 8 }}>
                <Col xs={8} sm={6}>
                  <Card size="small" styles={{ body: { padding: '8px 10px' } }}>
                    <Statistic
                      title={<span style={{ fontSize: 10 }}>盈利笔数</span>}
                      value={getWinCount()}
                      suffix="笔"
                      prefix={<ArrowUpOutlined style={{ color: '#f5222d' }} />}
                      valueStyle={{ fontSize: 13, color: '#f5222d' }}
                    />
                  </Card>
                </Col>
                <Col xs={8} sm={6}>
                  <Card size="small" styles={{ body: { padding: '8px 10px' } }}>
                    <Statistic
                      title={<span style={{ fontSize: 10 }}>亏损笔数</span>}
                      value={getLossCount()}
                      suffix="笔"
                      prefix={<ArrowDownOutlined style={{ color: '#52c41a' }} />}
                      valueStyle={{ fontSize: 13, color: '#52c41a' }}
                    />
                  </Card>
                </Col>
                <Col xs={8} sm={6}>
                  <Card size="small" styles={{ body: { padding: '8px 10px' } }}>
                    <Statistic
                      title={<span style={{ fontSize: 10 }}>盈亏比</span>}
                      value={getProfitLossRatio()}
                      suffix={getProfitLossRatio() === '-' ? '' : ':1'}
                      valueStyle={{ fontSize: 13, color: '#1890ff' }}
                    />
                  </Card>
                </Col>
              </Row>
            </Card>
          </Col>

          <Col xs={24} lg={16}>
            <Card size="small">
              <ReactECharts
                option={getTrendOption()}
                style={{ height: '350px', width: '100%' }}
                notMerge={true}
              />
            </Card>
          </Col>

          <Col xs={24} lg={8}>
            <Card size="small">
              <ReactECharts
                option={getPieOption()}
                style={{ height: '350px', width: '100%' }}
                notMerge={true}
              />
            </Card>
          </Col>

          <Col span={24}>
            <Card size="small" title={<span style={{ fontSize: 13 }}>交易记录</span>}>
              {isMobile ? (
                <div>
                  {trades.map((trade, index) => (
                    <Card 
                      key={trade.id} 
                      size="small" 
                      style={{ 
                        marginBottom: 6,
                        borderLeft: `3px solid ${parseFloat(trade.profit || 0) > 0 ? '#f5222d' : parseFloat(trade.profit || 0) < 0 ? '#52c41a' : '#8c8c8c'}`
                      }}
                      styles={{ body: { padding: '6px 8px' } }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                          <span style={{ fontWeight: 'bold', fontSize: 12, color: '#1890ff' }}>{trade.stock_code.split('.')[0]}</span>
                          <span style={{ fontSize: 11, color: '#666' }}>{trade.stock_name}</span>
                        </div>
                        <span style={{ fontSize: 10, color: '#8c8c8c' }}>{trade.quantity}股</span>
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, color: '#595959' }}>
                        {trade.operation_type === '卖出' && trade.buy_price ? (
                          <>
                            <span>买¥{parseFloat(trade.buy_price).toFixed(2)} → 卖¥{trade.price ? parseFloat(trade.price).toFixed(2) : '-'}</span>
                            <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                              <span style={{ 
                                fontWeight: 'bold', 
                                color: parseFloat(trade.profit) > 0 ? '#f5222d' : parseFloat(trade.profit) < 0 ? '#52c41a' : '#8c8c8c'
                              }}>
                                {parseFloat(trade.profit) > 0 ? '+' : ''}¥{parseFloat(trade.profit).toFixed(0)} ({(parseFloat(trade.profit_ratio) * 100).toFixed(1)}%)
                              </span>
                              <span style={{ color: '#8c8c8c', fontSize: 9 }}>{trade.operation_date ? trade.operation_date.substring(5, 10) : '-'}</span>
                            </span>
                          </>
                        ) : (
                          <>
                            <span>¥{trade.price ? parseFloat(trade.price).toFixed(2) : '-'}</span>
                            <span style={{ color: '#8c8c8c' }}>{trade.operation_date ? trade.operation_date.substring(5, 10) : '-'}</span>
                          </>
                        )}
                      </div>
                    </Card>
                  ))}
                  {trades.length === 0 && (
                    <div style={{ textAlign: 'center', color: '#999', padding: '20px 0', fontSize: 12 }}>
                      暂无交易记录
                    </div>
                  )}
                </div>
              ) : (
                <Table
                  columns={tradeColumns}
                  dataSource={trades}
                  rowKey="id"
                  size="small"
                  pagination={{ pageSize: 10, size: 'small' }}
                  scroll={{ x: 'max-content' }}
                />
              )}
            </Card>
          </Col>
        </Row>
      </Spin>
    </div>
  );
};

export default StatisticsPage;
