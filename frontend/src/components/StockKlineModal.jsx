import React, { useState, useEffect } from 'react';
import { Modal, Spin, message } from 'antd';
import ReactECharts from 'echarts-for-react';
import { stockApi } from '../services/api';

const StockKlineModal = ({ visible, stockCode, stockName, onClose }) => {
  const [klineLoading, setKlineLoading] = useState(false);
  const [intradayLoading, setIntradayLoading] = useState(false);
  const [klineData, setKlineData] = useState([]);
  const [intradayData, setIntradayData] = useState([]);
  const [yesterdayClose, setYesterdayClose] = useState(null);
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
    if (visible && stockCode) {
      loadData();
    }
  }, [visible, stockCode]);

  const loadData = async () => {
    // 先加载K线数据
    loadKlineData();
    // 再加载分时数据
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
      
      const intradayResponse = await stockApi.getStockIntraday(stockCode);
      
      if (intradayResponse.data.success) {
        const data = intradayResponse.data.data;
        if (data && data.intraday) {
          setIntradayData(data.intraday);
          setYesterdayClose(data.yesterday_close);
        }
      }
      
    } catch (error) {
      console.error('加载分时数据失败：', error.message);
    } finally {
      setIntradayLoading(false);
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
      return index >= 0 ? intradayChangePercent[index] : 0;
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
    
    const priceMax = Math.max(...fullPrices.filter(p => p !== null));
    const priceMin = Math.min(...fullPrices.filter(p => p !== null));
    
    const maxChangePercent = Math.max(...fullChangePercent.filter(p => p !== null));
    const minChangePercent = Math.min(...fullChangePercent.filter(p => p !== null));
    
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

    return {
      title: {
        text: `${stockName || stockCode} - 分时图`,
        left: 'center',
        top: isMobile ? 5 : 10,
        textStyle: {
          fontSize: isMobile ? 14 : 16,
          fontWeight: 'bold'
        }
      },
      tooltip: {
        trigger: 'axis',
        axisPointer: {
          type: 'cross'
        },
        formatter: function(params) {
          if (!params || params.length === 0) return '';
          const time = params[0].axisValue;
          const price = fullPrices[params[0].dataIndex];
          const changePercent = fullChangePercent[params[0].dataIndex];
          const volume = fullVolumes[params[0].dataIndex];
          
          if (price === null) {
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
          left: '10%',
          right: '8%',
          top: isMobile ? '18%' : '15%',
          height: isMobile ? '45%' : '50%'
        },
        {
          left: '10%',
          right: '8%',
          top: isMobile ? '68%' : '70%',
          height: isMobile ? '15%' : '12%'
        }
      ],
      xAxis: [
        {
          type: 'category',
          data: fullTimes,
          boundaryGap: false,
          axisLine: { onZero: false },
          splitLine: { show: false },
          min: 'dataMin',
          max: 'dataMax',
          axisLabel: {
            interval: 59,
            formatter: function(value) {
              return value;
            }
          }
        },
        {
          type: 'category',
          gridIndex: 1,
          data: fullTimes,
          boundaryGap: false,
          axisLine: { onZero: false },
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
          axisLabel: {
            formatter: function(value) {
              return value.toFixed(2) + '%';
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
                  show: false
                }
              }
            ]
          }
        },
        {
          name: '成交量',
          type: 'bar',
          xAxisIndex: 1,
          yAxisIndex: 1,
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

    return {
      title: {
        text: `${stockName || stockCode} - 日K线`,
        left: 'center',
        top: isMobile ? 5 : 10,
        textStyle: {
          fontSize: isMobile ? 14 : 16,
          fontWeight: 'bold'
        }
      },
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
            
            return `
              <div style="font-weight: bold; margin-bottom: 5px;">${dateStr}</div>
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
        data: ['日K', '5日均线', '10日均线', '20日均线'],
        top: isMobile ? 30 : 40,
        itemWidth: isMobile ? 15 : 25,
        itemHeight: isMobile ? 10 : 14,
        textStyle: {
          fontSize: isMobile ? 11 : 12
        }
      },
      grid: [
        {
          left: '10%',
          right: '8%',
          top: isMobile ? '18%' : '15%',
          height: isMobile ? '45%' : '50%'
        },
        {
          left: '10%',
          right: '8%',
          top: isMobile ? '68%' : '70%',
          height: isMobile ? '15%' : '12%'
        }
      ],
      xAxis: [
        {
          type: 'category',
          data: dates,
          boundaryGap: false,
          axisLine: { onZero: false },
          splitLine: { show: false },
          min: 'dataMin',
          max: 'dataMax',
          axisLabel: {
            show: true,
            formatter: function(value) {
              return value.replace(/-/g, '').substring(0, 8);
            }
          }
        },
        {
          type: 'category',
          gridIndex: 1,
          data: dates,
          boundaryGap: false,
          axisLine: { onZero: false },
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
          }
        },
        {
          name: '5日均线',
          type: 'line',
          data: calculateMA(5),
          smooth: true,
          lineStyle: { width: 1 },
          symbol: 'none'
        },
        {
          name: '10日均线',
          type: 'line',
          data: calculateMA(10),
          smooth: true,
          lineStyle: { width: 1 },
          symbol: 'none'
        },
        {
          name: '20日均线',
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
        {/* 分时图区域 */}
        <div style={{ marginBottom: '10px' }}>
          <Spin spinning={intradayLoading}>
            {intradayData && intradayData.length > 0 ? (
              <ReactECharts
                option={getIntradayOption()}
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
                {intradayLoading ? '分时数据加载中...' : '暂无分时数据'}
              </div>
            )}
          </Spin>
        </div>
        
        {/* K线图区域 */}
        <div>
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
