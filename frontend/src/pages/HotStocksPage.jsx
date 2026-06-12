import { useState, useEffect } from 'react';
import { Card, Tag, Spin, message, Row, Col, Tooltip, Button } from 'antd';
import { RiseOutlined, FallOutlined, FireOutlined, DollarOutlined, LineChartOutlined, BulbOutlined, RobotOutlined } from '@ant-design/icons';
import api from '../services/api';
import StockKlineModal from '../components/StockKlineModal';
import HotTopicAnalysisModal from '../components/HotTopicAnalysisModal';

let loadAllDataRef = null;
let loadHotTopicsRef = null;

export const refreshHotStocksData = (force = true) => {
  if (loadAllDataRef) {
    loadAllDataRef(force);
  }
  if (loadHotTopicsRef) {
    loadHotTopicsRef();
  }
};

const HotStocksPage = () => {
  const [stocksData, setStocksData] = useState({
    normal: [],
    value: [],
    trend: []
  });
  const [hotTopics, setHotTopics] = useState([]);
  const [loading, setLoading] = useState(false);
  const [topicsLoading, setTopicsLoading] = useState(false);
  const [klineVisible, setKlineVisible] = useState(false);
  const [selectedStock, setSelectedStock] = useState(null);
  const [isMobile, setIsMobile] = useState(false);
  const [topicAnalysisVisible, setTopicAnalysisVisible] = useState(false);
  const [selectedTopic, setSelectedTopic] = useState(null);
  const [analyzingTopics, setAnalyzingTopics] = useState(new Set());
  const [completedTopicAnalysis, setCompletedTopicAnalysis] = useState(new Map());

  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 768);
    };
    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  const loadAllData = async (force = false) => {
    setLoading(true);
    try {
      const promises = ['normal', 'value', 'trend'].map(type => 
        api.get(`/hot-stocks?list_type=${type}`)
      );
      
      const responses = await Promise.all(promises);
      
      const newData = {};
      responses.forEach((response, index) => {
        const type = ['normal', 'value', 'trend'][index];
        if (response.data.success) {
          newData[type] = response.data.data;
        }
      });
      
      setStocksData(prev => ({ ...prev, ...newData }));
    } catch (error) {
      console.error('获取热股数据失败:', error);
      message.error('获取热股数据失败');
    } finally {
      setLoading(false);
    }
  };

  const loadHotTopics = async () => {
    setTopicsLoading(true);
    try {
      const response = await api.get('/hot-topics?days=1');
      if (response.data.success) {
        setHotTopics(response.data.data || []);
      }
    } catch (error) {
      console.error('获取热门话题失败:', error);
    } finally {
      setTopicsLoading(false);
    }
  };

  const handleTopicAnalysisClick = async (topic) => {
    const topicKey = topic.event_id || topic.title;
    
    if (completedTopicAnalysis.has(topicKey)) {
      setSelectedTopic({
        title: topic.title,
        themes: topic.themes,
        investment_direction: topic.investment_direction,
        event_id: topic.event_id
      });
      setTopicAnalysisVisible(true);
      return;
    }
    
    if (analyzingTopics.has(topicKey)) {
      message.info('该话题正在分析中，请稍后...');
      return;
    }
    
    try {
      const checkResponse = await api.post('/hot-topic/analyze', {
        topic_title: topic.title,
        themes: topic.themes || [],
        investment_direction: topic.investment_direction || '',
        force: false
      });
      
      if (checkResponse.data.success && checkResponse.data.cached) {
        setCompletedTopicAnalysis(prev => new Map(prev).set(topicKey, checkResponse.data.data));
        setSelectedTopic({
          title: topic.title,
          themes: topic.themes,
          investment_direction: topic.investment_direction,
          event_id: topic.event_id
        });
        setTopicAnalysisVisible(true);
        return;
      }
    } catch (error) {
      console.error('检查缓存失败:', error);
    }
    
    setAnalyzingTopics(prev => new Set(prev).add(topicKey));
    message.info(`开始分析"${topic.title}"，分析时间可能较长，请稍后...`);
    
    try {
      const response = await api.post('/hot-topic/analyze', {
        topic_title: topic.title,
        themes: topic.themes || [],
        investment_direction: topic.investment_direction || '',
        force: true
      });
      
      if (response.data.success) {
        setCompletedTopicAnalysis(prev => new Map(prev).set(topicKey, response.data.data));
        message.success(`"${topic.title}"分析完成，点击图标查看结果`);
      }
    } catch (error) {
      console.error('分析失败:', error);
      message.error('分析失败，请稍后重试');
    } finally {
      setAnalyzingTopics(prev => {
        const newSet = new Set(prev);
        newSet.delete(topicKey);
        return newSet;
      });
    }
  };

  useEffect(() => {
    loadAllDataRef = loadAllData;
    loadHotTopicsRef = loadHotTopics;
    return () => {
      loadAllDataRef = null;
      loadHotTopicsRef = null;
    };
  }, []);

  useEffect(() => {
    loadAllData();
    loadHotTopics();
  }, []);

  const renderStockCard = (stock, index) => {
    const changeColor = stock.change_percent > 0 ? '#cf1322' : stock.change_percent < 0 ? '#3f8600' : '#666';
    
    const filterDisclaimer = (text) => {
      if (!text) return '';
      return text.replace(/（免责声明：[^）]+）/g, '').trim();
    };

    const reasons = stock.analyse_title ? stock.analyse_title.split('+').filter(r => r.trim()) : [];
    const hasDetailReason = stock.reason && stock.reason.trim();

    if (isMobile) {
      return (
        <div
          key={stock.code}
          style={{
            background: '#fff',
            borderRadius: 6,
            border: `1px solid ${index < 3 ? '#ffccc7' : '#d9d9d9'}`,
            borderLeft: `3px solid ${index < 3 ? '#ff4d4f' : '#1890ff'}`,
            padding: '8px',
            cursor: 'pointer',
            transition: 'all 0.3s'
          }}
          onClick={() => {
            setSelectedStock({ code: stock.code, name: stock.name });
            setKlineVisible(true);
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
              <div style={{ 
                width: 18, 
                height: 18, 
                borderRadius: '50%', 
                background: index < 3 ? 'linear-gradient(135deg, #ff4d4f 0%, #ff7875 100%)' : 'linear-gradient(135deg, #1890ff 0%, #40a9ff 100%)',
                display: 'flex', 
                alignItems: 'center', 
                justifyContent: 'center',
                color: '#fff',
                fontSize: 9,
                fontWeight: 'bold'
              }}>
                {index + 1}
              </div>
              <div>
                <div style={{ fontWeight: 600, fontSize: 12, color: '#1890ff' }}>
                  {stock.name}
                </div>
                <div style={{ fontSize: 9, color: '#8c8c8c' }}>
                  {stock.code}
                </div>
              </div>
            </div>
            <div style={{ textAlign: 'right' }}>
              <div style={{ color: changeColor, fontWeight: 600, fontSize: 13 }}>
                {stock.change_percent > 0 ? '+' : ''}{stock.change_percent.toFixed(2)}%
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 2, justifyContent: 'flex-end' }}>
                <FireOutlined style={{ fontSize: 10, color: '#ff4d4f' }} />
                <span style={{ fontSize: 9, color: '#ff4d4f', fontWeight: 500 }}>
                  {stock.hot_value ? (stock.hot_value > 9999 ? `${(stock.hot_value / 10000).toFixed(1)}万` : stock.hot_value.toLocaleString()) : 0}
                </span>
              </div>
            </div>
          </div>
          
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', marginTop: 4 }}>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, flex: 1 }}>
              {reasons.length > 0 && reasons.slice(0, 2).map((reason, i) => (
                <Tag 
                  key={i}
                  style={{ 
                    fontSize: 9, 
                    margin: 0, 
                    padding: '1px 4px',
                    borderRadius: 2,
                    background: '#e6f7ff',
                    border: 'none',
                    color: '#1890ff'
                  }}
                >
                  {reason.trim().length > 8 ? reason.trim().substring(0, 8) + '...' : reason.trim()}
                </Tag>
              ))}
              {reasons.length === 0 && stock.industry && stock.industry.split(', ').slice(0, 2).map((tag, i) => (
                <Tag 
                  key={i}
                  style={{ 
                    fontSize: 9, 
                    margin: 0, 
                    padding: '1px 4px',
                    borderRadius: 2,
                    background: '#f9f0ff',
                    border: 'none',
                    color: '#722ed1'
                  }}
                >
                  {tag}
                </Tag>
              ))}
            </div>
            {stock.popularity_tag && (
              <Tag color="orange" style={{ fontSize: 8, padding: '1px 4px', margin: 0, marginLeft: 4 }}>
                {stock.popularity_tag}
              </Tag>
            )}
          </div>
        </div>
      );
    }

    return (
      <Card 
        key={stock.code} 
        size="small"
        style={{ 
          marginBottom: 0,
          borderLeft: `3px solid ${index < 3 ? '#ff4d4f' : '#1890ff'}`,
          background: '#fff',
          boxShadow: '0 1px 2px rgba(0,0,0,0.06)',
          transition: 'all 0.3s'
        }}
        styles={{ body: { padding: '8px 10px' } }}
        hoverable
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 6 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <div style={{ 
              width: 20, 
              height: 20, 
              borderRadius: '50%', 
              background: index < 3 ? 'linear-gradient(135deg, #ff4d4f 0%, #ff7875 100%)' : 'linear-gradient(135deg, #1890ff 0%, #40a9ff 100%)',
              display: 'flex', 
              alignItems: 'center', 
              justifyContent: 'center',
              color: '#fff',
              fontSize: 11,
              fontWeight: 'bold',
              flexShrink: 0
            }}>
              {index + 1}
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                <span 
                  style={{ 
                    fontWeight: 600, 
                    fontSize: 13, 
                    color: '#1890ff',
                    cursor: 'pointer'
                  }}
                  onClick={() => {
                    setSelectedStock({ code: stock.code, name: stock.name });
                    setKlineVisible(true);
                  }}
                >
                  {stock.name}
                </span>
              </div>
              <div 
                style={{ fontSize: 10, color: '#8c8c8c', cursor: 'pointer' }}
                onClick={() => {
                  setSelectedStock({ code: stock.code, name: stock.name });
                  setKlineVisible(true);
                }}
              >
                {stock.code}
              </div>
            </div>
          </div>
          <div style={{ textAlign: 'right' }}>
            <div style={{ color: changeColor, fontWeight: 600, fontSize: 14 }}>
              {stock.change_percent > 0 ? '+' : ''}{stock.change_percent.toFixed(2)}%
            </div>
            <div style={{ 
              display: 'flex', 
              alignItems: 'center', 
              gap: 2, 
              justifyContent: 'flex-end'
            }}>
              <FireOutlined style={{ fontSize: 12, color: '#ff4d4f' }} />
              <span style={{ 
                fontSize: 11, 
                fontWeight: 600, 
                color: '#ff4d4f'
              }}>
                {stock.hot_value ? (stock.hot_value > 9999 ? `${(stock.hot_value / 10000).toFixed(1)}万` : stock.hot_value.toLocaleString()) : 0}
              </span>
            </div>
          </div>
        </div>
        
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end' }}>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, flex: 1 }}>
            {reasons.length > 0 && reasons.slice(0, 2).map((reason, i) => (
              <Tag 
                key={i}
                style={{ 
                  fontSize: 9, 
                  margin: 0, 
                  padding: '1px 4px',
                  borderRadius: 2,
                  background: '#e6f7ff',
                  border: 'none',
                  color: '#1890ff'
                }}
              >
                {reason.trim().length > 8 ? reason.trim().substring(0, 8) + '...' : reason.trim()}
              </Tag>
            ))}
            {reasons.length === 0 && stock.industry && stock.industry.split(', ').slice(0, 2).map((tag, i) => (
              <Tag 
                key={i}
                style={{ 
                  fontSize: 9, 
                  margin: 0, 
                  padding: '1px 4px',
                  borderRadius: 2,
                  background: '#f9f0ff',
                  border: 'none',
                  color: '#722ed1'
                }}
              >
                {tag}
              </Tag>
            ))}
          </div>
          {stock.popularity_tag && (
            <Tag color="orange" style={{ fontSize: 8, padding: '1px 4px', margin: 0, marginLeft: 4 }}>
              {stock.popularity_tag}
            </Tag>
          )}
        </div>
      </Card>
    );
  };

  const renderHotTopics = () => {
    if (hotTopics.length === 0 && !topicsLoading) {
      return null;
    }

    const displayTopics = hotTopics.slice(0, 10);

    const getTopicStyle = (index) => {
      if (index === 0) {
        return {
          background: 'linear-gradient(135deg, #fff7e6 0%, #ffe7ba 100%)',
          border: '1px solid #ffd591',
          badgeBg: 'linear-gradient(135deg, #faad14 0%, #ffc53d 100%)',
        };
      } else if (index === 1) {
        return {
          background: 'linear-gradient(135deg, #f5f5f5 0%, #e8e8e8 100%)',
          border: '1px solid #d9d9d9',
          badgeBg: 'linear-gradient(135deg, #bfbfbf 0%, #d9d9d9 100%)',
        };
      } else if (index === 2) {
        return {
          background: 'linear-gradient(135deg, #fff1e6 0%, #ffd8bf 100%)',
          border: '1px solid #ffbb96',
          badgeBg: 'linear-gradient(135deg, #d48806 0%, #fa8c16 100%)',
        };
      } else {
        return {
          background: 'linear-gradient(135deg, #ffffff 0%, #fafafa 100%)',
          border: '1px solid #e8e8e8',
          badgeBg: '#8c8c8c',
        };
      }
    };

    return (
      <div style={{ 
        marginBottom: isMobile ? 12 : 24,
      }}>
        <div style={{ 
          fontSize: isMobile ? 14 : 16, 
          fontWeight: 'bold', 
          marginBottom: isMobile ? 12 : 16,
          padding: isMobile ? '10px 12px' : '12px 16px',
          background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
          borderRadius: 8,
          display: 'flex',
          alignItems: 'center',
          gap: 8,
          color: '#fff',
          boxShadow: '0 4px 12px rgba(102, 126, 234, 0.3)'
        }}>
          <BulbOutlined />
          热门话题
          <Tag color="#fff" style={{ marginLeft: 'auto', fontSize: isMobile ? 10 : 12, color: '#667eea' }}>
            {hotTopics.length}条
          </Tag>
        </div>
        {topicsLoading ? (
          <div style={{ textAlign: 'center', padding: '40px 0' }}>
            <Spin />
          </div>
        ) : (
          <div style={{ 
            display: 'grid', 
            gridTemplateColumns: isMobile ? '1fr' : 'repeat(3, 1fr)', 
            gap: isMobile ? 6 : 12 
          }}>
            {displayTopics.map((topic, index) => {
              const style = getTopicStyle(index);
              return (
            <div
              key={topic.event_id}
              style={{
                background: style.background,
                borderRadius: 8,
                padding: isMobile ? '10px 12px' : '10px',
                border: style.border,
                boxShadow: '0 2px 8px rgba(0, 0, 0, 0.08)',
                transition: 'all 0.3s'
              }}
            >
              <div style={{ 
                display: 'flex', 
                alignItems: 'flex-start', 
                gap: 6, 
                marginBottom: 6 
              }}>
                <div style={{ 
                  minWidth: 20, 
                  height: 20, 
                  borderRadius: '50%', 
                  background: style.badgeBg,
                  display: 'flex', 
                  alignItems: 'center', 
                  justifyContent: 'center',
                  color: '#fff',
                  fontSize: 11,
                  fontWeight: 'bold',
                  flexShrink: 0,
                  boxShadow: '0 2px 4px rgba(0, 0, 0, 0.2)'
                }}>
                  {index + 1}
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ 
                    fontSize: isMobile ? 12 : 13, 
                    fontWeight: 500, 
                    color: '#262626',
                    marginBottom: 4,
                    lineHeight: isMobile ? 1.4 : 1.5,
                    display: '-webkit-box',
                    WebkitLineClamp: 2,
                    WebkitBoxOrient: 'vertical',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis'
                  }}>
                    {topic.title}
                  </div>
                  <div style={{ 
                    display: 'flex', 
                    alignItems: 'center', 
                    gap: 4, 
                    flexWrap: 'wrap',
                    justifyContent: 'space-between'
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 4, flexWrap: 'wrap' }}>
                      <Tag 
                        style={{ 
                          fontSize: 9, 
                          margin: 0, 
                          padding: '1px 4px',
                          background: 'linear-gradient(135deg, #ff4d4f 0%, #ff7875 100%)',
                          border: 'none',
                          color: '#fff',
                          fontWeight: 'bold'
                        }}
                      >
                        <FireOutlined style={{ fontSize: 9, marginRight: 2 }} />
                        {topic.heat > 9999 ? `${(topic.heat / 10000).toFixed(1)}万` : topic.heat.toLocaleString()}
                      </Tag>
                      {topic.themes.slice(0, 2).map((theme, i) => (
                        <Tag 
                          key={i}
                          style={{ 
                            fontSize: 9, 
                            margin: 0, 
                            padding: '1px 4px',
                            background: 'linear-gradient(135deg, #1890ff 0%, #40a9ff 100%)',
                            border: 'none',
                            color: '#fff',
                            fontWeight: 'bold'
                          }}
                        >
                          {theme}
                        </Tag>
                      ))}
                    </div>
                    <div 
                      style={{ 
                        display: 'inline-flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        width: 22,
                        height: 22,
                        borderRadius: 3,
                        background: completedTopicAnalysis.has(topic.event_id || topic.title) ? 'linear-gradient(135deg, #52c41a 0%, #73d13d 100%)' : 
                                    analyzingTopics.has(topic.event_id || topic.title) ? 'linear-gradient(135deg, #fa8c16 0%, #ffa940 100%)' : 'linear-gradient(135deg, #722ed1 0%, #9254de 100%)',
                        cursor: 'pointer',
                        flexShrink: 0,
                        boxShadow: '0 2px 4px rgba(0, 0, 0, 0.2)'
                      }}
                      onClick={() => handleTopicAnalysisClick(topic)}
                    >
                      <RobotOutlined style={{ fontSize: 12, color: '#fff' }} />
                    </div>
                  </div>
                </div>
              </div>
              {topic.top_stocks && topic.top_stocks.length > 0 && (
                <div style={{ 
                  marginTop: 6, 
                  paddingTop: 6, 
                  borderTop: '1px solid #f0f0f0',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 4
                }}>
                  <span style={{ fontSize: 9, color: '#8c8c8c' }}>领涨:</span>
                  {topic.top_stocks.slice(0, 1).map((stock, i) => (
                    <span 
                      key={i}
                      style={{ 
                        fontSize: 10, 
                        color: stock.change_percent > 0 ? '#cf1322' : '#3f8600',
                        cursor: 'pointer',
                        fontWeight: 500
                      }}
                      onClick={() => {
                        setSelectedStock({ code: stock.code, name: stock.name });
                        setKlineVisible(true);
                      }}
                    >
                      {stock.name} {stock.change_percent > 0 ? '+' : ''}{stock.change_percent.toFixed(2)}%
                    </span>
                  ))}
                </div>
              )}
            </div>
              );
            })}
        </div>
        )}
      </div>
    );
  };

  const renderColumn = (title, icon, data, bgColor, gradientColors) => {
    const displayData = isMobile ? data.slice(0, 10) : data;
    
    return (
      <div>
        <div style={{ 
          fontSize: isMobile ? 14 : 16, 
          fontWeight: 'bold', 
          marginBottom: isMobile ? 12 : 16, 
          padding: isMobile ? '10px 12px' : '12px 16px',
          background: gradientColors.header,
          borderRadius: 8,
          display: 'flex',
          alignItems: 'center',
          gap: 8,
          color: '#fff',
          boxShadow: `0 4px 12px ${gradientColors.shadow}`
        }}>
          {icon}
          {title}
          <Tag style={{ marginLeft: 'auto', fontSize: isMobile ? 10 : 12, background: '#fff', color: gradientColors.tagColor, border: 'none', fontWeight: 'bold' }}>{displayData.length}只</Tag>
        </div>
        <div style={{ maxHeight: isMobile ? 'none' : 'calc(100vh - 200px)', overflowY: isMobile ? 'visible' : 'auto' }}>
          {loading ? (
            <div style={{ textAlign: 'center', padding: '40px 0' }}>
              <Spin />
            </div>
          ) : displayData.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '40px 0', color: '#999' }}>
              暂无数据
            </div>
          ) : (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: isMobile ? 8 : 12 }}>
              {displayData.map((stock, index) => renderStockCard(stock, index))}
            </div>
          )}
        </div>
      </div>
    );
  };

  return (
    <div style={{ padding: isMobile ? '0' : '0 16px' }}>
      {renderHotTopics()}
      {isMobile ? (
        <div>
          <div style={{ marginBottom: 16 }}>
            {renderColumn('大家都在看(每小时更新)', <FireOutlined />, stocksData.normal, '#fff1f0', {
              header: 'linear-gradient(135deg, #ff4d4f 0%, #ff7875 100%)',
              shadow: 'rgba(255, 77, 79, 0.3)',
              tagColor: '#ff4d4f'
            })}
          </div>
          <div style={{ marginBottom: 16 }}>
            {renderColumn('价值派(每天更新)', <DollarOutlined />, stocksData.value, '#f6ffed', {
              header: 'linear-gradient(135deg, #52c41a 0%, #73d13d 100%)',
              shadow: 'rgba(82, 196, 26, 0.3)',
              tagColor: '#52c41a'
            })}
          </div>
          <div>
            {renderColumn('趋势派(每天更新)', <LineChartOutlined />, stocksData.trend, '#e6f7ff', {
              header: 'linear-gradient(135deg, #1890ff 0%, #40a9ff 100%)',
              shadow: 'rgba(24, 144, 255, 0.3)',
              tagColor: '#1890ff'
            })}
          </div>
        </div>
      ) : (
        <Row gutter={16}>
          <Col span={8}>
            {renderColumn('大家都在看(每小时更新)', <FireOutlined />, stocksData.normal, '#fff1f0', {
              header: 'linear-gradient(135deg, #ff4d4f 0%, #ff7875 100%)',
              shadow: 'rgba(255, 77, 79, 0.3)',
              tagColor: '#ff4d4f'
            })}
          </Col>
          <Col span={8}>
            {renderColumn('价值派(每天更新)', <DollarOutlined />, stocksData.value, '#f6ffed', {
              header: 'linear-gradient(135deg, #52c41a 0%, #73d13d 100%)',
              shadow: 'rgba(82, 196, 26, 0.3)',
              tagColor: '#52c41a'
            })}
          </Col>
          <Col span={8}>
            {renderColumn('趋势派(每天更新)', <LineChartOutlined />, stocksData.trend, '#e6f7ff', {
              header: 'linear-gradient(135deg, #1890ff 0%, #40a9ff 100%)',
              shadow: 'rgba(24, 144, 255, 0.3)',
              tagColor: '#1890ff'
            })}
          </Col>
        </Row>
      )}
      
      <StockKlineModal
        visible={klineVisible}
        stockCode={selectedStock?.code}
        stockName={selectedStock?.name}
        onClose={() => {
          setKlineVisible(false);
          setSelectedStock(null);
        }}
      />
      
      <HotTopicAnalysisModal
        visible={topicAnalysisVisible}
        topicTitle={selectedTopic?.title}
        themes={selectedTopic?.themes}
        investmentDirection={selectedTopic?.investment_direction}
        analysisData={selectedTopic?.event_id ? completedTopicAnalysis.get(selectedTopic.event_id) : null}
        onClose={() => {
          setTopicAnalysisVisible(false);
          setSelectedTopic(null);
        }}
      />
    </div>
  );
};

export default HotStocksPage;
