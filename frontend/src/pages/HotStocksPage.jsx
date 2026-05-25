import { useState, useEffect } from 'react';
import { Card, Tag, Spin, message, Row, Col, Tooltip } from 'antd';
import { RiseOutlined, FallOutlined, FireOutlined, DollarOutlined, LineChartOutlined } from '@ant-design/icons';
import axios from 'axios';
import { useGlobal } from '../contexts/GlobalContext';
import StockKlineModal from '../components/StockKlineModal';

const isDev = import.meta.env.DEV;
const API_BASE = isDev ? 'http://localhost:5001/api' : '/api';

let loadAllDataRef = null;

export const refreshHotStocksData = (force = true) => {
  if (loadAllDataRef) {
    loadAllDataRef(force);
  }
};

const HotStocksPage = () => {
  const { currentDate } = useGlobal();
  const [stocksData, setStocksData] = useState({
    normal: [],
    value: [],
    trend: []
  });
  const [loading, setLoading] = useState(false);
  const [klineVisible, setKlineVisible] = useState(false);
  const [selectedStock, setSelectedStock] = useState(null);
  const [isMobile, setIsMobile] = useState(false);

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
        axios.get(`${API_BASE}/hot-stocks?list_type=${type}`)
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

  useEffect(() => {
    loadAllDataRef = loadAllData;
    return () => {
      loadAllDataRef = null;
    };
  }, []);

  useEffect(() => {
    loadAllData();
  }, [currentDate]);

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
          
          {reasons.length > 0 && (
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, marginTop: 6 }}>
              {reasons.slice(0, 2).map((reason, i) => (
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
            </div>
          )}
          
          {reasons.length === 0 && stock.industry && (
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, marginTop: 6 }}>
              {stock.industry.split(', ').slice(0, 2).map((tag, i) => (
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
          )}
        </div>
      );
    }

    return (
      <Card 
        key={stock.code} 
        size="small"
        style={{ 
          marginBottom: 8,
          borderLeft: `3px solid ${index < 3 ? '#ff4d4f' : '#1890ff'}`,
          background: '#fff',
          boxShadow: '0 1px 2px rgba(0,0,0,0.06)',
          transition: 'all 0.3s'
        }}
        styles={{ body: { padding: '10px 12px' } }}
        hoverable
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 6 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <div style={{ 
              width: 24, 
              height: 24, 
              borderRadius: '50%', 
              background: index < 3 ? 'linear-gradient(135deg, #ff4d4f 0%, #ff7875 100%)' : 'linear-gradient(135deg, #1890ff 0%, #40a9ff 100%)',
              display: 'flex', 
              alignItems: 'center', 
              justifyContent: 'center',
              color: '#fff',
              fontSize: 12,
              fontWeight: 'bold',
              flexShrink: 0
            }}>
              {index + 1}
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <span 
                  style={{ 
                    fontWeight: 600, 
                    fontSize: 14, 
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
                {stock.popularity_tag && (
                  <Tag color="orange" style={{ fontSize: 10, padding: '2px 6px', margin: 0 }}>
                    {stock.popularity_tag}
                  </Tag>
                )}
              </div>
              <div 
                style={{ fontSize: 11, color: '#8c8c8c', cursor: 'pointer' }}
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
            <div style={{ 
              display: 'flex', 
              alignItems: 'center', 
              gap: 4, 
              justifyContent: 'flex-end',
              marginBottom: 4
            }}>
              <FireOutlined style={{ fontSize: 14, color: '#ff4d4f' }} />
              <span style={{ 
                fontSize: 13, 
                fontWeight: 600, 
                color: '#ff4d4f',
                background: 'linear-gradient(135deg, #fff1f0 0%, #ffccc7 100%)',
                padding: '2px 8px',
                borderRadius: 12
              }}>
                {stock.hot_value ? stock.hot_value.toLocaleString() : 0}
              </span>
            </div>
            <div style={{ color: changeColor, fontWeight: 600, fontSize: 15 }}>
              {stock.change_percent > 0 ? '+' : ''}{stock.change_percent.toFixed(2)}%
            </div>
          </div>
        </div>
        
        {reasons.length > 0 && (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, marginBottom: 6 }}>
            {reasons.map((reason, i) => (
              <Tooltip
                key={i}
                title={hasDetailReason ? <div style={{ whiteSpace: 'pre-wrap' }}>{filterDisclaimer(stock.reason)}</div> : null}
                placement="top"
                styles={{ root: { maxWidth: '390px' } }}
              >
                <Tag 
                  color="blue"
                  style={{ 
                    fontSize: 10, 
                    marginBottom: 0,
                    cursor: hasDetailReason ? 'pointer' : 'default'
                  }}
                >
                  {reason.trim()}
                </Tag>
              </Tooltip>
            ))}
          </div>
        )}
        
        {stock.industry && (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
            {stock.industry.split(', ').slice(0, 3).map((tag, i) => (
              <Tag 
                key={i}
                style={{ 
                  fontSize: 10, 
                  marginBottom: 0,
                  background: '#fafafa',
                  border: '1px solid #d9d9d9',
                  color: '#595959'
                }}
              >
                {tag}
              </Tag>
            ))}
            {stock.industry.split(', ').length > 3 && (
              <span style={{ fontSize: 10, color: '#8c8c8c' }}>
                +{stock.industry.split(', ').length - 3}
              </span>
            )}
          </div>
        )}
      </Card>
    );
  };

  const renderColumn = (title, icon, data, bgColor) => {
    const displayData = isMobile ? data.slice(0, 10) : data;
    
    return (
      <div>
        <div style={{ 
          fontSize: isMobile ? 14 : 16, 
          fontWeight: 'bold', 
          marginBottom: isMobile ? 12 : 16, 
          padding: isMobile ? '10px 12px' : '12px 16px',
          background: bgColor,
          borderRadius: 8,
          display: 'flex',
          alignItems: 'center',
          gap: 8
        }}>
          {icon}
          {title}
          <Tag color="blue" style={{ marginLeft: 'auto', fontSize: isMobile ? 10 : 12 }}>{displayData.length}只</Tag>
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
          ) : isMobile ? (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 8 }}>
              {displayData.map((stock, index) => renderStockCard(stock, index))}
            </div>
          ) : (
            displayData.map((stock, index) => renderStockCard(stock, index))
          )}
        </div>
      </div>
    );
  };

  return (
    <div style={{ padding: isMobile ? '0' : '0 16px' }}>
      {isMobile ? (
        <div>
          <div style={{ marginBottom: 16 }}>
            {renderColumn('大家都在看', <FireOutlined style={{ color: '#ff4d4f' }} />, stocksData.normal, '#fff1f0')}
          </div>
          <div style={{ marginBottom: 16 }}>
            {renderColumn('价值派', <DollarOutlined style={{ color: '#52c41a' }} />, stocksData.value, '#f6ffed')}
          </div>
          <div>
            {renderColumn('趋势派', <LineChartOutlined style={{ color: '#1890ff' }} />, stocksData.trend, '#e6f7ff')}
          </div>
        </div>
      ) : (
        <Row gutter={16}>
          <Col span={8}>
            {renderColumn('大家都在看', <FireOutlined style={{ color: '#ff4d4f' }} />, stocksData.normal, '#fff1f0')}
          </Col>
          <Col span={8}>
            {renderColumn('价值派', <DollarOutlined style={{ color: '#52c41a' }} />, stocksData.value, '#f6ffed')}
          </Col>
          <Col span={8}>
            {renderColumn('趋势派', <LineChartOutlined style={{ color: '#1890ff' }} />, stocksData.trend, '#e6f7ff')}
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
    </div>
  );
};

export default HotStocksPage;
