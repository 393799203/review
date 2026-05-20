import React, { useState, useEffect } from 'react';
import { Modal, Spin, message, Button } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';
import { stockApi } from '../services/api';
import api from '../services/api';

const StockKlineModal = ({ visible, stockCode, stockName, onClose }) => {
  const [klineLoading, setKlineLoading] = useState(false);
  const [intradayLoading, setIntradayLoading] = useState(false);
  const [quoteLoading, setQuoteLoading] = useState(false);
  const [klineData, setKlineData] = useState([]);
  const [intradayData, setIntradayData] = useState([]);
  const [yesterdayClose, setYesterdayClose] = useState(null);
  const [quoteData, setQuoteData] = useState(null);
  const [isMobile, setIsMobile] = useState(false);
  const [isInWatchlist, setIsInWatchlist] = useState(false);
  const [adding, setAdding] = useState(false);

  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 768);
    };
    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  useEffect(() => {
    if (visible && stockCode) {
      loadData();
    }
    if (!visible) {
      setIsInWatchlist(false);
    }
  }, [visible, stockCode]);

  const loadData = async () => {
    loadKlineData();
    loadIntradayData();
  };

  const loadKlineData = async () => {
    try {
      setKlineLoading(true);
      
      const klineResponse = await stockApi.getStockKline(stockCode, 250);
      
      if (klineResponse.data.success) {
        setKlineData(klineResponse.data.data || []);
      } else {
        message.error('加载K线数据失败');
      }
      
    } catch (error) {
      message.error('加载K线数据失败：' + error.message);
    } finally {
      setKlineLoading(false);
    }
  };

  const loadIntradayData = async () => {
    try {
      setIntradayLoading(true);
      setQuoteLoading(true);
      
      const intradayResponse = await stockApi.getStockIntraday(stockCode);
      
      if (intradayResponse.data.success) {
        const data = intradayResponse.data.data;
        if (data && data.intraday) {
          setIntradayData(data.intraday);
          setYesterdayClose(data.yesterday_close);
        }
        if (data && data.quote) {
          setQuoteData(data.quote);
        }
        if (data && data.is_in_watchlist !== undefined) {
          setIsInWatchlist(data.is_in_watchlist);
        }
      }
      
    } catch (error) {
      console.error('加载分时数据失败：', error.message);
    } finally {
      setIntradayLoading(false);
      setQuoteLoading(false);
    }
  };

  const handleAddToWatchlist = async () => {
    try {
      setAdding(true);
      const today = new Date();
      const addDate = today.getFullYear().toString() + 
                      (today.getMonth() + 1).toString().padStart(2, '0') + 
                      today.getDate().toString().padStart(2, '0');
      
      let addPrice = null;
      try {
        const quoteResponse = await api.get(`/stock/quote/${stockCode}`);
        if (quoteResponse.data.success && quoteResponse.data.data) {
          addPrice = quoteResponse.data.data.price;
        }
      } catch (error) {
        console.warn('获取股票价格失败，将不设置加入价格:', error);
      }
      
      const response = await api.post('/watchlist', {
        stock_code: stockCode,
        stock_name: stockName,
        add_date: addDate,
        add_price: addPrice,
        add_reason: '手动添加',
        add_type: 'manual'
      });
      
      if (response.data.success) {
        message.success(`${stockName} 已添加到自选`);
        setIsInWatchlist(true);
      } else {
        message.error(response.data.error || '添加失败');
      }
    } catch (error) {
      message.error('添加失败：' + (error.response?.data?.error || error.message));
    } finally {
      setAdding(false);
    }
  };

  const getIntradayOption = () => {
    if (!intradayData || intradayData.length === 0) {
      return {};
    }

    const intradayTimes = intradayData.map(item => item.time);
    const intradayPrices = intradayData.map(item => item.price);
    const intradayVolumes = intradayData.map(item => item.volume);
    
    const intradayChangePercent = intradayPrices.map(price => {
      if (yesterdayClose && price) {
        return ((price - yesterdayClose) / yesterdayClose) * 100;
      }
      return 0;
    });

    const generateFullTimeSeries = () => {
      const times = [];
      for (let hour = 9; hour <= 11; hour++) {
        for (let minute = 0; minute <= 59; minute++) {
          if (hour === 9 && minute < 30) continue;
          if (hour === 11 && minute > 30) break;
          times.push(`${hour.toString().padStart(2, '0')}:${minute.toString().padStart(2, '0')}`);
        }
      }
      for (let hour = 13; hour <= 15; hour++) {
        for (let minute = 0; minute <= 59; minute++) {
          if (hour === 15 && minute > 0) break;
          times.push(`${hour.toString().padStart(2, '0')}:${minute.toString().padStart(2, '0')}`);
        }
      }
      return times;
    };

    const fullTimes = generateFullTimeSeries();
    const fullPrices = fullTimes.map(time => {
      const index = intradayTimes.findIndex(t => t.substring(0, 5) === time);
      return index >= 0 ? intradayPrices[index] : null;
    });
    const fullVolumes = fullTimes.map(time => {
      const index = intradayTimes.findIndex(t => t.substring(0, 5) === time);
      return index >= 0 ? intradayVolumes[index] : 0;
    });
    const fullChangePercent = fullTimes.map(time => {
      const index = intradayTimes.findIndex(t => t.substring(0, 5) === time);
      return index >= 0 ? intradayChangePercent[index] : null;
    });

    const getLimitByStockCode = (code) => {
      if (!code) return 10;
      const codeStr = code.toString();
      if (codeStr.startsWith('60') || codeStr.startsWith('00')) return 10;
      if (codeStr.startsWith('30') || codeStr.startsWith('68')) return 20;
      if (codeStr.startsWith('920')) return 30;
      return 10;
    };
    
    const limitPercent = getLimitByStockCode(stockCode);
    
    const validChangePercents = fullChangePercent.filter(p => p !== null);
    const maxChangePercent = Math.max(...validChangePercents);
    const minChangePercent = Math.min(...validChangePercents);
    
    let yAxisMin, yAxisMax;
    
    const isNearLimitUp = maxChangePercent >= limitPercent * 0.9;
    const isNearLimitDown = minChangePercent <= -limitPercent * 0.9;
    
    if (isNearLimitUp || isNearLimitDown) {
      yAxisMin = -limitPercent;
      yAxisMax = limitPercent;
    } else {
      const maxAbsChange = Math.max(Math.abs(minChangePercent), Math.abs(maxChangePercent));
      const padding = Math.max(maxAbsChange * 0.1, 0.5);
      yAxisMin = -(maxAbsChange + padding);
      yAxisMax = maxAbsChange + padding;
    }

    const maxPrice = yesterdayClose ? yesterdayClose * (1 + maxChangePercent / 100) : null;
    const minPrice = yesterdayClose ? yesterdayClose * (1 + minChangePercent / 100) : null;

    return {
      tooltip: {
        trigger: 'axis',
        axisPointer: {
          type: 'line',
          lineStyle: {
            color: 'rgba(0, 0, 0, 0)',
            width: 0
          }
        },
        formatter: function(params) {
          if (!params || params.length === 0) return '';
          const time = params[0].axisValue;
          const price = fullPrices[params[0].dataIndex];
          const changePercent = fullChangePercent[params[0].dataIndex];
          const volume = fullVolumes[params[0].dataIndex];
          
          if (price === null || changePercent === null) {
            return `<div style="font-weight: bold;">${time}</div><div style="color: #999;">无交易数据</div>`;
          }
          
          const color = changePercent >= 0 ? '#f5222d' : '#52c41a';
          const changeValue = yesterdayClose ? (price - yesterdayClose).toFixed(2) : '0.00';
          return `
            <div style="font-weight: bold; margin-bottom: 5px;">${time}</div>
            <div>价格: <span style="color: ${color}; font-weight: bold;">${price.toFixed(2)}</span></div>
            ${yesterdayClose ? `<div>昨收: ${yesterdayClose.toFixed(2)}</div>` : ''}
            <div>涨跌额: <span style="color: ${color};">${changeValue > 0 ? '+' : ''}${changeValue}</span></div>
            <div>涨跌幅: <span style="color: ${color}; font-weight: bold;">${changePercent > 0 ? '+' : ''}${changePercent.toFixed(2)}%</span></div>
            <div>成交量: ${volume.toFixed(0)}手</div>
          `;
        }
      },
      grid: [
        {
          left: '2%',
          right: '2%',
          top: isMobile ? '12%' : '8%',
          height: isMobile ? '50%' : '55%'
        },
        {
          left: '2%',
          right: '2%',
          top: isMobile ? '70%' : '72%',
          height: isMobile ? '18%' : '15%'
        }
      ],
      xAxis: [
        {
          type: 'category',
          data: fullTimes,
          boundaryGap: false,
          axisLine: { show: false },
          splitLine: { show: false },
          min: 'dataMin',
          max: 'dataMax',
          axisLabel: { show: false }
        },
        {
          type: 'category',
          gridIndex: 1,
          data: fullTimes,
          boundaryGap: false,
          axisLine: { show: false },
          axisTick: { show: false },
          splitLine: { show: false },
          axisLabel: { show: false },
          min: 'dataMin',
          max: 'dataMax'
        }
      ],
      yAxis: [
        {
          type: 'value',
          min: yAxisMin,
          max: yAxisMax,
          interval: (yAxisMax - yAxisMin) / 4,
          position: 'left',
          axisLabel: {
            inside: true,
            formatter: function(value) {
              if (!yesterdayClose) return '';
              if (Math.abs(value - yAxisMax) < 0.01) {
                const price = yesterdayClose * (1 + value / 100);
                return price.toFixed(2);
              }
              if (Math.abs(value - yAxisMin) < 0.01) {
                const price = yesterdayClose * (1 + value / 100);
                return price.toFixed(2);
              }
              if (Math.abs(value) < 0.01) {
                return yesterdayClose.toFixed(2);
              }
              return '';
            }
          },
          splitLine: {
            lineStyle: {
              type: 'dashed'
            }
          },
          splitArea: {
            show: true
          }
        },
        {
          type: 'value',
          min: yAxisMin,
          max: yAxisMax,
          interval: (yAxisMax - yAxisMin) / 4,
          position: 'right',
          axisLine: { show: false },
          axisTick: { show: false },
          splitLine: { show: false },
          axisLabel: {
            inside: true,
            formatter: function(value) {
              if (Math.abs(value - yAxisMax) < 0.01) {
                return (value > 0 ? '+' : '') + value.toFixed(2) + '%';
              }
              if (Math.abs(value - yAxisMin) < 0.01) {
                return (value > 0 ? '+' : '') + value.toFixed(2) + '%';
              }
              return '';
            }
          }
        },
        {
          scale: true,
          gridIndex: 1,
          splitNumber: 2,
          axisLabel: { show: false },
          axisLine: { show: false },
          axisTick: { show: false },
          splitLine: { show: false }
        }
      ],
      series: [
        {
          name: '分时',
          type: 'line',
          data: fullChangePercent,
          smooth: true,
          lineStyle: {
            width: 1,
            color: '#1890ff'
          },
          areaStyle: {
            color: {
              type: 'linear',
              x: 0,
              y: 0,
              x2: 0,
              y2: 1,
              colorStops: [{
                offset: 0, color: 'rgba(24, 144, 255, 0.3)'
              }, {
                offset: 1, color: 'rgba(24, 144, 255, 0.05)'
              }]
            }
          },
          symbol: 'none',
          markLine: {
            silent: true,
            data: [
              {
                yAxis: 0,
                lineStyle: {
                  color: '#999',
                  type: 'dashed',
                  width: 1
                },
                label: {
                  show: true,
                  position: 'insideEndTop',
                  formatter: '0.00%',
                  color: '#666',
                  fontSize: 11
                }
              }
            ]
          },
          markPoint: {
            symbol: 'pin',
            symbolSize: 1,
            data: [
              {
                coord: [fullTimes[fullTimes.length - 1], maxChangePercent],
                label: {
                  show: true,
                  position: 'right',
                  formatter: maxChangePercent > 0 ? '+' + maxChangePercent.toFixed(2) + '%' : maxChangePercent.toFixed(2) + '%',
                  color: '#f5222d',
                  fontSize: 12,
                  fontWeight: 'bold'
                }
              },
              {
                coord: [fullTimes[fullTimes.length - 1], minChangePercent],
                label: {
                  show: true,
                  position: 'right',
                  formatter: minChangePercent > 0 ? '+' + minChangePercent.toFixed(2) + '%' : minChangePercent.toFixed(2) + '%',
                  color: '#52c41a',
                  fontSize: 12,
                  fontWeight: 'bold'
                }
              }
            ]
          }
        },
        {
          name: '成交量',
          type: 'bar',
          xAxisIndex: 1,
          yAxisIndex: 2,
          data: fullVolumes,
          itemStyle: {
            color: function(params) {
              const dataIndex = params.dataIndex;
              const changePercent = fullChangePercent[dataIndex];
              return changePercent >= 0 ? '#f5222d' : '#52c41a';
            }
          }
        }
      ]
    };
  };

  const getKlineOption = () => {
    if (!klineData || klineData.length === 0) {
      return {};
    }

    const dates = klineData.map(item => item.date);
    const ohlc = klineData.map(item => [
      item.open,
      item.close,
      item.low,
      item.high
    ]);
    const volumes = klineData.map(item => item.volume);

    const calculateMA = (dayCount) => {
      const result = [];
      for (let i = 0; i < klineData.length; i++) {
        if (i < dayCount) {
          result.push('-');
          continue;
        }
        let sum = 0;
        for (let j = 0; j < dayCount; j++) {
          sum += klineData[i - j].close;
        }
        result.push((sum / dayCount).toFixed(2));
      }
      return result;
    };

    const exDividendMarks = [];
    klineData.forEach((item, index) => {
      if (item.is_ex_dividend) {
        exDividendMarks.push({
          name: '除权除息',
          coord: [index, item.high],
          value: item.ex_dividend_desc || '除权',
          itemStyle: {
            color: '#faad14'
          },
          label: {
            show: true,
            position: 'top',
            color: '#faad14',
            fontSize: 10,
            formatter: item.ex_dividend_desc || '除权'
          }
        });
      }
    });

    return {
      tooltip: {
        trigger: 'axis',
        axisPointer: {
          type: 'cross'
        },
        backgroundColor: 'rgba(245, 245, 245, 0.9)',
        borderWidth: 1,
        borderColor: '#ccc',
        padding: isMobile ? 6 : 10,
        textStyle: {
          color: '#000',
          fontSize: isMobile ? 12 : 14
        },
        confine: true,
        formatter: function(params) {
          if (!params || params.length === 0) return '';
          
          const dataIndex = params[0].dataIndex;
          const data = klineData[dataIndex];
          
          if (data) {
            const changeColor = (data.change_percent || 0) >= 0 ? '#f5222d' : '#52c41a';
            const dateStr = data.date.replace(/-/g, '').substring(0, 8);
            const exDividendBadge = data.is_ex_dividend ? 
              `<span style="background: #faad14; color: white; padding: 2px 6px; border-radius: 3px; font-size: 11px; margin-left: 5px;">${data.ex_dividend_desc || '除权'}</span>` : '';
            
            return `
              <div style="font-weight: bold; margin-bottom: 5px;">${dateStr}${exDividendBadge}</div>
              <div>开盘: ${(data.open || 0).toFixed(2)}</div>
              <div>收盘: <span style="color: ${changeColor}; font-weight: bold;">${(data.close || 0).toFixed(2)}</span></div>
              <div>最高: ${(data.high || 0).toFixed(2)}</div>
              <div>最低: ${(data.low || 0).toFixed(2)}</div>
              <div>涨跌幅: <span style="color: ${changeColor}; font-weight: bold;">${(data.change_percent || 0) > 0 ? '+' : ''}${(data.change_percent || 0).toFixed(2)}%</span></div>
              <div>成交量: ${(data.volume || 0).toFixed(0)}手</div>
              <div>成交额: ${((data.amount || 0) / 100000000).toFixed(2)}亿</div>
              <div>换手率: ${(data.turnover || 0).toFixed(2)}%</div>
            `;
          }
          
          return '';
        }
      },
      legend: {
        data: ['日K', '5日', '10日', '20日'],
        top: isMobile ? 30 : 40,
        itemWidth: isMobile ? 15 : 25,
        itemHeight: isMobile ? 10 : 14,
        textStyle: {
          fontSize: isMobile ? 11 : 12
        }
      },
      grid: [
        {
          left: '2%',
          right: '3%',
          top: isMobile ? '12%' : '8%',
          height: isMobile ? '50%' : '55%'
        },
        {
          left: '2%',
          right: '3%',
          top: isMobile ? '70%' : '72%',
          height: isMobile ? '18%' : '15%'
        }
      ],
      xAxis: [
        {
          type: 'category',
          data: dates,
          boundaryGap: false,
          axisLine: { show: false },
          splitLine: { show: false },
          min: 'dataMin',
          max: 'dataMax',
          axisLabel: { show: false }
        },
        {
          type: 'category',
          gridIndex: 1,
          data: dates,
          boundaryGap: false,
          axisLine: { show: false },
          axisTick: { show: false },
          splitLine: { show: false },
          axisLabel: { show: false },
          min: 'dataMin',
          max: 'dataMax'
        }
      ],
      yAxis: [
        {
          scale: true,
          axisLabel: {
            inside: true
          },
          splitArea: {
            show: true
          }
        },
        {
          scale: true,
          gridIndex: 1,
          splitNumber: 2,
          axisLabel: { show: false },
          axisLine: { show: false },
          axisTick: { show: false },
          splitLine: { show: false }
        }
      ],
      dataZoom: [
        {
          type: 'inside',
          xAxisIndex: [0, 1],
          start: 70,
          end: 100
        },
        {
          show: true,
          xAxisIndex: [0, 1],
          type: 'slider',
          top: isMobile ? '88%' : '90%',
          start: 70,
          end: 100
        }
      ],
      series: [
        {
          name: '日K',
          type: 'candlestick',
          data: ohlc,
          itemStyle: {
            color: '#f5222d',
            color0: '#52c41a',
            borderColor: '#f5222d',
            borderColor0: '#52c41a'
          },
          markPoint: {
            symbol: 'pin',
            symbolSize: 30,
            data: exDividendMarks,
            label: {
              show: true,
              fontSize: 10
            }
          }
        },
        {
          name: '5日',
          type: 'line',
          data: calculateMA(5),
          smooth: true,
          lineStyle: { width: 1 },
          symbol: 'none'
        },
        {
          name: '10日',
          type: 'line',
          data: calculateMA(10),
          smooth: true,
          lineStyle: { width: 1 },
          symbol: 'none'
        },
        {
          name: '20日',
          type: 'line',
          data: calculateMA(20),
          smooth: true,
          lineStyle: { width: 1 },
          symbol: 'none'
        },
        {
          name: '成交量',
          type: 'bar',
          xAxisIndex: 1,
          yAxisIndex: 1,
          data: volumes,
          itemStyle: {
            color: function(params) {
              const dataIndex = params.dataIndex;
              const data = klineData[dataIndex];
              return data.close >= data.open ? '#f5222d' : '#52c41a';
            }
          }
        }
      ]
    };
  };

  const renderQuotePanel = () => {
    if (!quoteData) return null;
    
    return (
      <div style={{ 
        padding: '0 10px', 
        backgroundColor: '#fafafa', 
        borderRadius: '4px',
        height: '100%',
        display: 'flex',
        flexDirection: 'column'
      }}>
        {/* 五档盘口 - 卖在上买在下 */}
        <div style={{ fontSize: '13px', fontWeight: 'bold', marginBottom: '6px', color: '#333' }}>
          五档盘口
        </div>
        
        {/* 卖盘 - 从卖5到卖1 */}
        {[5, 4, 3, 2, 1].map(i => (
          <div key={`ask${i}`} style={{ 
            display: 'flex', 
            justifyContent: 'space-between',
            padding: '3px 6px',
            backgroundColor: '#f6ffed',
            marginBottom: '2px',
            borderRadius: '2px',
            fontSize: '13px'
          }}>
            <span style={{ color: '#999', width: '28px' }}>卖{i}</span>
            <span style={{ color: '#52c41a', width: '55px', textAlign: 'right' }}>{quoteData[`ask${i}`]?.toFixed(2) || '--'}</span>
            <span style={{ color: '#666', width: '55px', textAlign: 'right' }}>{quoteData[`ask_vol${i}`]?.toFixed(0) || '--'}</span>
          </div>
        ))}
        
        {/* 分隔线 */}
        <div style={{ height: '2px', backgroundColor: '#e8e8e8', margin: '4px 0' }}></div>
        
        {/* 买盘 - 从买1到买5 */}
        {[1, 2, 3, 4, 5].map(i => (
          <div key={`bid${i}`} style={{ 
            display: 'flex', 
            justifyContent: 'space-between',
            padding: '3px 6px',
            backgroundColor: '#fff1f0',
            marginBottom: '2px',
            borderRadius: '2px',
            fontSize: '13px'
          }}>
            <span style={{ color: '#999', width: '28px' }}>买{i}</span>
            <span style={{ color: '#f5222d', width: '55px', textAlign: 'right' }}>{quoteData[`bid${i}`]?.toFixed(2) || '--'}</span>
            <span style={{ color: '#666', width: '55px', textAlign: 'right' }}>{quoteData[`bid_vol${i}`]?.toFixed(0) || '--'}</span>
          </div>
        ))}
      </div>
    );
  };

  const renderQuoteHeader = () => {
    if (!quoteData) return null;
    
    const price = quoteData.price || 0;
    const prevClose = quoteData.prev_close || 0;
    const change = quoteData.change_amount || 0;
    const changePercent = quoteData.change_percent || 0;
    const color = change >= 0 ? '#f5222d' : '#52c41a';
    const volatility = quoteData.volatility;
    const turnover = quoteData.turnover;
    
    const getPriceColor = (currentPrice) => {
      if (!currentPrice || !prevClose) return '#333';
      if (currentPrice > prevClose) return '#f5222d';
      if (currentPrice < prevClose) return '#52c41a';
      return '#333';
    };
    
    if (isMobile) {
      return (
        <div style={{ 
          padding: '6px 10px', 
          backgroundColor: '#fff', 
          borderBottom: '1px solid #f0f0f0',
        }}>
          {/* 第一行：股票名称和代码 */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '4px' }}>
            <span style={{ fontSize: '15px', color: '#333', fontWeight: '600' }}>{stockName}</span>
            <span style={{ fontSize: '11px', color: '#888', fontFamily: 'monospace' }}>{stockCode}</span>
            {!quoteLoading && (
              <Button
                type="primary"
                icon={<PlusOutlined />}
                size="small"
                onClick={handleAddToWatchlist}
                loading={adding}
                disabled={isInWatchlist}
                style={{ 
                  background: isInWatchlist ? '#d9d9d9' : '#1890ff', 
                  borderColor: isInWatchlist ? '#d9d9d9' : '#1890ff',
                  borderRadius: 3,
                  fontSize: 10,
                  height: 20,
                  padding: '0 6px'
                }}
              >
                {isInWatchlist ? '已添加' : '加自选'}
              </Button>
            )}
          </div>
          
          {/* 第二行：价格信息 */}
          <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px' }}>
            <span style={{ fontSize: '20px', fontWeight: 'bold', color: color, fontFamily: 'monospace' }}>
              {price.toFixed(2)}
            </span>
            <span style={{ fontSize: '13px', color: color }}>
              {change >= 0 ? '+' : ''}{change.toFixed(2)}
            </span>
            <span style={{ 
              fontSize: '11px', 
              color: '#fff', 
              backgroundColor: color,
              padding: '1px 5px',
              borderRadius: '3px',
              fontWeight: '500'
            }}>
              {changePercent >= 0 ? '+' : ''}{changePercent.toFixed(2)}%
            </span>
          </div>
          
          {/* 第三行：行情数据 */}
          <div style={{ display: 'flex', gap: '8px', marginTop: '4px' }}>
            <div style={{ flex: 1, textAlign: 'center' }}>
              <div style={{ fontSize: '9px', color: '#999' }}>昨收</div>
              <div style={{ fontSize: '11px', color: '#333' }}>{prevClose.toFixed(2)}</div>
            </div>
            <div style={{ flex: 1, textAlign: 'center' }}>
              <div style={{ fontSize: '9px', color: '#999' }}>开盘</div>
              <div style={{ fontSize: '11px', color: getPriceColor(quoteData.open) }}>{quoteData.open?.toFixed(2) || '--'}</div>
            </div>
            <div style={{ flex: 1, textAlign: 'center' }}>
              <div style={{ fontSize: '9px', color: '#999' }}>最高</div>
              <div style={{ fontSize: '11px', color: getPriceColor(quoteData.high) }}>{quoteData.high?.toFixed(2) || '--'}</div>
            </div>
            <div style={{ flex: 1, textAlign: 'center' }}>
              <div style={{ fontSize: '9px', color: '#999' }}>最低</div>
              <div style={{ fontSize: '11px', color: getPriceColor(quoteData.low) }}>{quoteData.low?.toFixed(2) || '--'}</div>
            </div>
            <div style={{ flex: 1, textAlign: 'center' }}>
              <div style={{ fontSize: '9px', color: '#999' }}>换手率</div>
              <div style={{ fontSize: '11px', color: '#333' }}>{turnover ? `${turnover.toFixed(2)}%` : '--'}</div>
            </div>
            <div style={{ flex: 1, textAlign: 'center' }}>
              <div style={{ fontSize: '9px', color: '#999' }}>波动率</div>
              <div style={{ fontSize: '11px', color: '#333' }}>{volatility ? `${volatility.toFixed(1)}%` : '--'}</div>
            </div>
          </div>
        </div>
      );
    }
    
    return (
      <div style={{ 
        padding: '12px 16px', 
        backgroundColor: '#fff', 
        borderBottom: '1px solid #f0f0f0',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          {/* 左侧：股票信息 */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div style={{ 
              display: 'flex',
              alignItems: 'center',
              gap: '8px'
            }}>
              <span style={{ fontSize: '16px', color: '#333', fontWeight: '600' }}>{stockName}</span>
              <span style={{ fontSize: '13px', color: '#888', fontFamily: 'monospace' }}>{stockCode}</span>
              {!quoteLoading && (
                <Button
                  type="primary"
                  icon={<PlusOutlined />}
                  size="small"
                  onClick={handleAddToWatchlist}
                  loading={adding}
                  disabled={isInWatchlist}
                  style={{ 
                    background: isInWatchlist ? '#d9d9d9' : '#1890ff', 
                    borderColor: isInWatchlist ? '#d9d9d9' : '#1890ff',
                    borderRadius: 3,
                    fontSize: 12,
                    height: 24
                  }}
                >
                  {isInWatchlist ? '已添加' : '加自选'}
                </Button>
              )}
            </div>
          </div>
          
          {/* 中间：价格信息 */}
          <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px' }}>
            <span style={{ fontSize: '24px', fontWeight: 'bold', color: color, fontFamily: 'monospace' }}>
              {price.toFixed(2)}
            </span>
            <span style={{ fontSize: '15px', color: color, fontWeight: '500' }}>
              {change >= 0 ? '+' : ''}{change.toFixed(2)}
            </span>
            <span style={{ 
              fontSize: '13px', 
              color: '#fff', 
              backgroundColor: color,
              padding: '2px 8px',
              borderRadius: '3px',
              fontWeight: '500'
            }}>
              {changePercent >= 0 ? '+' : ''}{changePercent.toFixed(2)}%
            </span>
          </div>
          
          {/* 右侧：行情数据 */}
          <div style={{ display: 'flex', gap: '16px' }}>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '11px', color: '#999' }}>昨收</div>
              <div style={{ fontSize: '14px', color: '#333', fontWeight: '500' }}>{prevClose.toFixed(2)}</div>
            </div>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '11px', color: '#999' }}>开盘</div>
              <div style={{ fontSize: '14px', color: getPriceColor(quoteData.open), fontWeight: '500' }}>{quoteData.open?.toFixed(2) || '--'}</div>
            </div>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '11px', color: '#999' }}>最高</div>
              <div style={{ fontSize: '14px', color: getPriceColor(quoteData.high), fontWeight: '500' }}>{quoteData.high?.toFixed(2) || '--'}</div>
            </div>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '11px', color: '#999' }}>最低</div>
              <div style={{ fontSize: '14px', color: getPriceColor(quoteData.low), fontWeight: '500' }}>{quoteData.low?.toFixed(2) || '--'}</div>
            </div>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '11px', color: '#999' }}>成交额</div>
              <div style={{ fontSize: '14px', color: '#333', fontWeight: '500' }}>{((quoteData.amount || 0) / 100000000).toFixed(2)}亿</div>
            </div>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '11px', color: '#999' }}>换手率</div>
              <div style={{ fontSize: '14px', color: '#333', fontWeight: '500' }}>{turnover ? `${turnover.toFixed(2)}%` : '--'}</div>
            </div>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '11px', color: '#999' }}>波动率</div>
              <div style={{ fontSize: '14px', color: '#333', fontWeight: '500' }}>{volatility ? `${volatility.toFixed(1)}%` : '--'}</div>
            </div>
          </div>
        </div>
      </div>
    );
  };

  return (
    <Modal
      title={null}
      open={visible}
      onCancel={onClose}
      footer={null}
      width={isMobile ? '98%' : 1100}
      centered
      autoFocus={false}
      focusable={{ focusTriggerAfterClose: false }}
      className="stock-kline-modal"
      styles={{ 
        body: { 
          padding: isMobile ? '1px' : '2px'
        } 
      }}
    >
      <div>
        {/* 分时图区域 + 五档盘口 */}
        <div style={{ marginBottom: isMobile ? '0px' : '10px' }}>
          {/* 实时行情头部 */}
          {renderQuoteHeader()}
          
          <div style={{ display: 'flex' }}>
            {/* 分时图 */}
            <div style={{ flex: isMobile ? '1' : '1' }}>
              <Spin spinning={intradayLoading}>
                {intradayData && intradayData.length > 0 ? (
                  <ReactECharts
                    option={getIntradayOption()}
                    style={{ height: isMobile ? '280px' : '320px', width: '100%' }}
                    notMerge={true}
                    lazyUpdate={true}
                  />
                ) : (
                  <div style={{ 
                    height: isMobile ? '280px' : '320px', 
                    display: 'flex', 
                    alignItems: 'center', 
                    justifyContent: 'center', 
                    color: '#999',
                    border: '1px solid #f0f0f0',
                    borderRadius: '4px'
                  }}>
                    {intradayLoading ? '分时数据加载中...' : '暂无分时数据'}
                  </div>
                )}
              </Spin>
            </div>
            
            {/* 五档盘口 */}
            {!isMobile && (
              <div style={{ flex: '0 0 180px' }}>
                <Spin spinning={quoteLoading}>
                  <div style={{ height: '320px' }}>
                    {renderQuotePanel()}
                  </div>
                </Spin>
              </div>
            )}
          </div>
        </div>
        
        {/* K线图区域 */}
        <div style={{ marginTop: isMobile ? '-8px' : '0px' }}>
          <Spin spinning={klineLoading}>
            {klineData && klineData.length > 0 ? (
              <ReactECharts
                option={getKlineOption()}
                style={{ height: isMobile ? '300px' : '350px', width: '100%' }}
                notMerge={true}
                lazyUpdate={true}
              />
            ) : (
              <div style={{ 
                height: isMobile ? '300px' : '350px', 
                display: 'flex', 
                alignItems: 'center', 
                justifyContent: 'center', 
                color: '#999',
                border: '1px solid #f0f0f0',
                borderRadius: '4px'
              }}>
                {klineLoading ? 'K线数据加载中...' : '暂无K线数据'}
              </div>
            )}
          </Spin>
        </div>
      </div>
    </Modal>
  );
};

export default StockKlineModal;
