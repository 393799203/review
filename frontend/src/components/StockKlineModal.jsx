import React, { useState, useEffect } from 'react';
import { Modal, Spin, message } from 'antd';
import ReactECharts from 'echarts-for-react';
import { stockApi } from '../services/api';

const StockKlineModal = ({ visible, stockCode, stockName, onClose }) => {
  const [loading, setLoading] = useState(false);
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
    try {
      setLoading(true);
      
      const [klineResponse, intradayResponse] = await Promise.all([
        stockApi.getStockKline(stockCode, 250),
        stockApi.getStockIntraday(stockCode)
      ]);
      
      if (klineResponse.data.success) {
        setKlineData(klineResponse.data.data || []);
      } else {
        message.error('加载K线数据失败');
      }
      
      if (intradayResponse.data.success) {
        const data = intradayResponse.data.data;
        if (data && data.intraday) {
          setIntradayData(data.intraday);
          setYesterdayClose(data.yesterday_close);
        }
      }
      
    } catch (error) {
      message.error('加载数据失败：' + error.message);
    } finally {
      setLoading(false);
    }
  };

  const getOption = () => {
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

    const hasIntraday = intradayData && intradayData.length > 0;
    const intradayTimes = hasIntraday ? intradayData.map(item => item.time.split(' ')[1]) : [];
    const intradayPrices = hasIntraday ? intradayData.map(item => item.price) : [];
    const intradayVolumes = hasIntraday ? intradayData.map(item => item.volume) : [];
    
    const intradayChangePercent = hasIntraday && yesterdayClose 
      ? intradayPrices.map(price => ((price - yesterdayClose) / yesterdayClose * 100))
      : [];
    
    let yAxisMin = 0;
    let yAxisMax = 0;
    if (hasIntraday && intradayChangePercent.length > 0) {
      const minChange = Math.min(...intradayChangePercent);
      const maxChange = Math.max(...intradayChangePercent);
      
      if (minChange === maxChange) {
        yAxisMin = -10;
        yAxisMax = 10;
      } else {
        const range = maxChange - minChange;
        const padding = Math.max(range * 0.2, 1);
        yAxisMin = Math.floor(minChange - padding);
        yAxisMax = Math.ceil(maxChange + padding);
        
        if (yAxisMin > 0) yAxisMin = -Math.ceil(padding);
        if (yAxisMax < 0) yAxisMax = Math.ceil(padding);
      }
    }

    const grids = hasIntraday ? [
      {
        left: isMobile ? '8%' : '10%',
        right: isMobile ? '5%' : '8%',
        top: isMobile ? 50 : 65,
        height: isMobile ? '22%' : '25%'
      },
      {
        left: isMobile ? '8%' : '10%',
        right: isMobile ? '5%' : '8%',
        top: isMobile ? '28%' : '30%',
        height: isMobile ? '8%' : '10%'
      },
      {
        left: isMobile ? '8%' : '10%',
        right: isMobile ? '5%' : '8%',
        top: isMobile ? '42%' : '44%',
        height: isMobile ? '26%' : '30%'
      },
      {
        left: isMobile ? '8%' : '10%',
        right: isMobile ? '5%' : '8%',
        top: isMobile ? '76%' : '80%',
        height: isMobile ? '6%' : '5%'
      }
    ] : [
      {
        left: isMobile ? '8%' : '10%',
        right: isMobile ? '5%' : '8%',
        top: isMobile ? 60 : 80,
        height: isMobile ? '50%' : '55%'
      },
      {
        left: isMobile ? '8%' : '10%',
        right: isMobile ? '5%' : '8%',
        top: isMobile ? '74%' : '79%',
        height: isMobile ? '10%' : '8%'
      }
    ];

    const xAxes = hasIntraday ? [
      {
        type: 'category',
        data: intradayTimes,
        boundaryGap: false,
        axisLine: { onZero: false },
        splitLine: { show: false },
        min: 'dataMin',
        max: 'dataMax',
        axisLabel: { show: false }
      },
      {
        type: 'category',
        gridIndex: 1,
        data: intradayTimes,
        boundaryGap: false,
        axisLine: { onZero: false },
        splitLine: { show: false },
        min: 'dataMin',
        max: 'dataMax',
        axisLabel: { show: false }
      },
      {
        type: 'category',
        gridIndex: 2,
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
        gridIndex: 3,
        data: dates,
        boundaryGap: false,
        axisLine: { onZero: false },
        axisTick: { show: false },
        splitLine: { show: false },
        axisLabel: { show: false },
        min: 'dataMin',
        max: 'dataMax'
      }
    ] : [
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
    ];

    const yAxes = hasIntraday ? [
      {
        scale: false,
        min: yAxisMin,
        max: yAxisMax,
        splitArea: { show: true },
        axisLabel: {
          formatter: function(value) {
            return Math.round(value) + '%';
          },
          color: function(value) {
            if (value > 0) return '#f5222d';
            if (value < 0) return '#52c41a';
            return '#666';
          }
        },
        splitLine: {
          lineStyle: {
            color: '#e0e0e0'
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
      },
      {
        scale: true,
        gridIndex: 2,
        splitArea: { show: true }
      },
      {
        scale: true,
        gridIndex: 3,
        splitNumber: 2,
        axisLabel: { show: false },
        axisLine: { show: false },
        axisTick: { show: false },
        splitLine: { show: false }
      }
    ] : [
      {
        scale: true,
        splitArea: { show: true }
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
    ];

    const dataZoomConfig = hasIntraday ? [
      {
        type: 'inside',
        xAxisIndex: [0, 1],
        start: 0,
        end: 100
      },
      {
        show: true,
        xAxisIndex: [2, 3],
        type: 'slider',
        bottom: 20,
        start: 70,
        end: 100,
        height: 20
      }
    ] : [
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
        bottom: 20,
        start: 70,
        end: 100,
        height: 20
      }
    ];

    const series = hasIntraday ? [
      {
        name: '分时',
        type: 'line',
        data: intradayChangePercent,
        smooth: true,
        lineStyle: {
          width: 2,
          color: '#1890ff'
        },
        symbol: 'none',
        itemStyle: {
          color: '#1890ff'
        },
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
        name: '分时成交量',
        type: 'bar',
        xAxisIndex: 1,
        yAxisIndex: 1,
        data: intradayVolumes,
        itemStyle: {
          color: '#1890ff'
        }
      },
      {
        name: '日K',
        type: 'candlestick',
        xAxisIndex: 2,
        yAxisIndex: 2,
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
        xAxisIndex: 2,
        yAxisIndex: 2,
        data: calculateMA(5),
        smooth: true,
        lineStyle: { width: 1 },
        symbol: 'none'
      },
      {
        name: '10日均线',
        type: 'line',
        xAxisIndex: 2,
        yAxisIndex: 2,
        data: calculateMA(10),
        smooth: true,
        lineStyle: { width: 1 },
        symbol: 'none'
      },
      {
        name: '20日均线',
        type: 'line',
        xAxisIndex: 2,
        yAxisIndex: 2,
        data: calculateMA(20),
        smooth: true,
        lineStyle: { width: 1 },
        symbol: 'none'
      },
      {
        name: '成交量',
        type: 'bar',
        xAxisIndex: 3,
        yAxisIndex: 3,
        data: volumes,
        itemStyle: {
          color: function (params) {
            const dataIndex = params.dataIndex;
            const data = klineData[dataIndex];
            return data.close >= data.open ? '#f5222d' : '#52c41a';
          }
        }
      }
    ] : [
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
          color: function (params) {
            const dataIndex = params.dataIndex;
            const data = klineData[dataIndex];
            return data.close >= data.open ? '#f5222d' : '#52c41a';
          }
        }
      }
    ];

    return {
      title: {
        text: `${stockName || stockCode} - ${hasIntraday ? '分时 & K线' : '日K线'}`,
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
          type: 'cross',
          link: [{ xAxisIndex: 'all' }]
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
          const seriesIndex = params[0].seriesIndex;
          
          // 格式化时间函数
          const formatTime = (timeStr) => {
            if (!timeStr) return '';
            // 如果是完整的日期时间格式 (2025-05-05 09:30:00)，只显示时间部分
            if (timeStr.includes(' ')) {
              return timeStr.split(' ')[1].substring(0, 5); // 返回 "09:30"
            }
            return timeStr;
          };
          
          // 判断是否在分时图上（seriesIndex 0或1）
          if (hasIntraday && (seriesIndex === 0 || seriesIndex === 1)) {
            const time = formatTime(intradayTimes[dataIndex]);
            const price = intradayPrices[dataIndex];
            const changePercent = intradayChangePercent[dataIndex];
            const volume = intradayVolumes[dataIndex];
            const color = changePercent >= 0 ? '#f5222d' : '#52c41a';
            
            return `
              <div style="font-weight: bold; margin-bottom: 5px;">${time}</div>
              <div>价格: ${price.toFixed(2)}</div>
              ${yesterdayClose ? `<div>昨收: ${yesterdayClose.toFixed(2)}</div>` : ''}
              <div>涨跌幅: <span style="color: ${color}; font-weight: bold;">${changePercent > 0 ? '+' : ''}${changePercent.toFixed(2)}%</span></div>
              <div>成交量: ${volume.toFixed(0)}手</div>
            `;
          } else if (klineData[dataIndex]) {
            const data = klineData[dataIndex];
            const changeColor = data.change_percent >= 0 ? '#f5222d' : '#52c41a';
            const dateStr = data.date.replace(/-/g, '').substring(0, 8);
            
            return `
              <div style="font-weight: bold; margin-bottom: 5px;">${dateStr}</div>
              <div>开盘: ${data.open.toFixed(2)}</div>
              <div>收盘: <span style="color: ${changeColor}; font-weight: bold;">${data.close.toFixed(2)}</span></div>
              <div>最高: ${data.high.toFixed(2)}</div>
              <div>最低: ${data.low.toFixed(2)}</div>
              <div>涨跌幅: <span style="color: ${changeColor}; font-weight: bold;">${data.change_percent > 0 ? '+' : ''}${data.change_percent.toFixed(2)}%</span></div>
              <div>成交量: ${data.volume.toFixed(0)}手</div>
              <div>成交额: ${(data.amount / 100000000).toFixed(2)}亿</div>
              <div>换手率: ${data.turnover.toFixed(2)}%</div>
            `;
          }
          
          return '';
        }
      },
      legend: hasIntraday ? [
        {
          data: ['分时'],
          top: isMobile ? 30 : 40,
          left: 'center',
          itemWidth: isMobile ? 15 : 25,
          itemHeight: isMobile ? 10 : 14,
          textStyle: {
            fontSize: isMobile ? 11 : 12
          }
        },
        {
          data: ['日K', '5日均线', '10日均线', '20日均线'],
          top: isMobile ? '40%' : '42%',
          left: 'center',
          itemWidth: isMobile ? 15 : 25,
          itemHeight: isMobile ? 10 : 14,
          textStyle: {
            fontSize: isMobile ? 11 : 12
          }
        }
      ] : {
        data: ['日K', '5日均线', '10日均线', '20日均线'],
        top: isMobile ? 30 : 40,
        itemWidth: isMobile ? 15 : 25,
        itemHeight: isMobile ? 10 : 14,
        textStyle: {
          fontSize: isMobile ? 11 : 12
        }
      },
      grid: grids,
      xAxis: xAxes,
      yAxis: yAxes,
      dataZoom: dataZoomConfig,
      series: series
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
          padding: isMobile ? '2px' : '5px'
        } 
      }}
    >
      <Spin spinning={loading}>
        {klineData.length > 0 ? (
          <ReactECharts
            option={getOption()}
            style={{ height: isMobile ? '650px' : '750px', width: '100%' }}
            notMerge={true}
            lazyUpdate={true}
          />
        ) : (
          <div style={{ height: isMobile ? '650px' : '750px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#999' }}>
            暂无K线数据
          </div>
        )}
      </Spin>
    </Modal>
  );
};

export default StockKlineModal;
