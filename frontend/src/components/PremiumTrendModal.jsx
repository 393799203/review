import React, { useState, useEffect } from 'react';
import { Modal, Spin, message } from 'antd';
import ReactECharts from 'echarts-for-react';
import api from '../services/api';

const PremiumTrendModal = ({ visible, continuousDays, date, onClose }) => {
  const [loading, setLoading] = useState(false);
  const [trendData, setTrendData] = useState(null);
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
    if (visible && continuousDays) {
      loadTrendData();
    }
  }, [visible, continuousDays, date]);

  const loadTrendData = async () => {
    setLoading(true);
    try {
      const params = date ? { date } : {};
      const response = await api.get(`/premium-trend/${continuousDays}`, { params });
      
      if (response.data.success) {
        setTrendData(response.data.data);
      } else {
        message.error(response.data.error || '获取溢价率趋势失败');
      }
    } catch (error) {
      message.error('获取溢价率趋势失败：' + (error.response?.data?.error || error.message));
    } finally {
      setLoading(false);
    }
  };

  const getChartOption = () => {
    if (!trendData || !trendData.trend) {
      return {};
    }

    const dates = trendData.trend.map(item => {
      // 格式化日期为 MMDD 格式
      const dateStr = item.date;
      if (dateStr.includes('-')) {
        // 格式：2026-05-25 -> 0525
        const parts = dateStr.split('-');
        return parts[1] + parts[2];
      } else if (dateStr.length === 8) {
        // 格式：20260525 -> 0525
        return dateStr.substring(4, 6) + dateStr.substring(6, 8);
      }
      return dateStr;
    });
    const values = trendData.trend.map(item => item.avg_change_percent);
    const counts = trendData.trend.map(item => item.stock_count);

    return {
      title: {
        text: `${continuousDays}连板溢价率趋势`,
        left: 'center',
        top: 10,
        textStyle: {
          fontSize: isMobile ? 14 : 18,
          fontWeight: 'bold',
          color: '#262626'
        }
      },
      tooltip: {
        trigger: 'axis',
        backgroundColor: 'rgba(255, 255, 255, 0.95)',
        borderColor: '#e8e8e8',
        borderWidth: 1,
        padding: [12, 16],
        textStyle: {
          color: '#262626',
          fontSize: isMobile ? 12 : 13
        },
        formatter: (params) => {
          const dataIndex = params[0].dataIndex;
          const date = dates[dataIndex];
          const value = values[dataIndex];
          const count = counts[dataIndex];
          
          return `
            <div style="padding: 4px 0;">
              <div style="font-weight: 600; margin-bottom: 8px; font-size: ${isMobile ? 13 : 14}px;">${date}</div>
              <div style="margin-bottom: 4px;">
                <span style="color: #8c8c8c;">平均溢价率：</span>
                <span style="color: ${value >= 0 ? '#f5222d' : '#52c41a'}; font-weight: 600; font-size: ${isMobile ? 14 : 15}px;">
                  ${value !== null ? (value >= 0 ? '+' : '') + value.toFixed(2) + '%' : '无数据'}
                </span>
              </div>
              <div>
                <span style="color: #8c8c8c;">股票数量：</span>
                <span style="font-weight: 500;">${count}只</span>
              </div>
            </div>
          `;
        }
      },
      grid: {
        left: isMobile ? 40 : 60,
        right: isMobile ? 20 : 40,
        bottom: isMobile ? 60 : 80,
        top: isMobile ? 60 : 80,
        containLabel: false
      },
      xAxis: {
        type: 'category',
        data: dates,
        boundaryGap: false,
        axisLine: {
          lineStyle: {
            color: '#e8e8e8',
            width: 2
          }
        },
        axisTick: {
          show: false
        },
        axisLabel: {
          rotate: isMobile ? 60 : 45,
          fontSize: isMobile ? 10 : 11,
          color: '#8c8c8c',
          margin: isMobile ? 12 : 15
        },
        splitLine: {
          show: true,
          lineStyle: {
            color: '#f5f5f5',
            width: 1
          }
        }
      },
      yAxis: {
        type: 'value',
        position: 'left',
        axisLine: {
          show: true,
          lineStyle: {
            color: '#e8e8e8',
            width: 2
          }
        },
        axisTick: {
          show: true,
          lineStyle: {
            color: '#e8e8e8'
          }
        },
        axisLabel: {
          formatter: '{value}%',
          fontSize: isMobile ? 10 : 12,
          color: '#8c8c8c',
          margin: 10
        },
        splitLine: {
          lineStyle: {
            color: '#f5f5f5',
            type: 'dashed',
            width: 1
          }
        }
      },
      series: [
        {
          name: '平均溢价率',
          type: 'line',
          data: values,
          smooth: true,
          symbol: 'circle',
          symbolSize: isMobile ? 6 : 8,
          showSymbol: true,
          emphasis: {
            focus: 'series',
            itemStyle: {
              borderWidth: 3
            }
          },
          lineStyle: {
            width: isMobile ? 2 : 3,
            color: {
              type: 'linear',
              x: 0,
              y: 0,
              x2: 1,
              y2: 0,
              colorStops: [
                { offset: 0, color: '#1890ff' },
                { offset: 0.5, color: '#40a9ff' },
                { offset: 1, color: '#1890ff' }
              ]
            },
            shadowColor: 'rgba(24, 144, 255, 0.3)',
            shadowBlur: 10,
            shadowOffsetY: 5
          },
          itemStyle: {
            color: (params) => {
              const value = params.value;
              return value >= 0 ? '#f5222d' : '#52c41a';
            },
            borderWidth: 2,
            borderColor: '#fff',
            shadowColor: 'rgba(0, 0, 0, 0.1)',
            shadowBlur: 4
          },
          areaStyle: {
            color: {
              type: 'linear',
              x: 0,
              y: 0,
              x2: 0,
              y2: 1,
              colorStops: [
                { offset: 0, color: 'rgba(24, 144, 255, 0.25)' },
                { offset: 0.5, color: 'rgba(24, 144, 255, 0.1)' },
                { offset: 1, color: 'rgba(24, 144, 255, 0.02)' }
              ]
            }
          },
          markLine: {
            silent: true,
            symbol: 'none',
            data: [
              {
                yAxis: 0,
                lineStyle: {
                  color: '#d9d9d9',
                  type: 'solid',
                  width: 1.5
                },
                label: {
                  show: true,
                  position: 'insideEndTop',
                  formatter: '零线',
                  fontSize: isMobile ? 10 : 11,
                  color: '#8c8c8c'
                }
              }
            ]
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
      width={isMobile ? '95%' : 900}
      centered
    >
      <Spin spinning={loading}>
        {trendData && (
          <ReactECharts
            option={getChartOption()}
            style={{ height: isMobile ? 300 : 450 }}
            opts={{ renderer: 'svg' }}
          />
        )}
      </Spin>
    </Modal>
  );
};

export default PremiumTrendModal;
