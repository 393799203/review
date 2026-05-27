import { useState, useEffect } from 'react';
import { Modal, Card, Tag, Spin, Empty, Button, message } from 'antd';
import { RobotOutlined, ReloadOutlined, TagsOutlined, StockOutlined } from '@ant-design/icons';
import api from '../services/api';

const HotTopicAnalysisModal = ({ visible, topicTitle, themes, investmentDirection, analysisData: propAnalysisData, onClose }) => {
  const [loading, setLoading] = useState(false);
  const [analysisData, setAnalysisData] = useState(null);
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
    if (visible && topicTitle) {
      if (propAnalysisData) {
        setAnalysisData(propAnalysisData);
      } else {
        loadAnalysisData();
      }
    }
  }, [visible, topicTitle, propAnalysisData]);

  const loadAnalysisData = async (force = false) => {
    try {
      setLoading(true);
      const response = await api.post('/hot-topic/analyze', {
        topic_title: topicTitle,
        themes: themes || [],
        investment_direction: investmentDirection || '',
        force: force
      });
      
      if (response.data.success) {
        setAnalysisData(response.data.data);
      } else {
        message.error(response.data.error || '分析失败');
      }
    } catch (error) {
      console.error('加载分析数据失败:', error);
      message.error('加载分析数据失败');
    } finally {
      setLoading(false);
    }
  };

  const handleReanalyze = () => {
    loadAnalysisData(true);
  };

  return (
    <Modal
      title={
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingRight: 30 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <RobotOutlined style={{ color: '#722ed1' }} />
            <span style={{ fontSize: isMobile ? 14 : 16 }}>热门话题AI分析</span>
          </div>
          <Button 
            type="text" 
            icon={<ReloadOutlined />} 
            onClick={handleReanalyze}
            loading={loading}
            size="small"
            style={{ color: '#1890ff' }}
          >
            {!isMobile && '重新分析'}
          </Button>
        </div>
      }
      open={visible}
      onCancel={onClose}
      footer={null}
      width={isMobile ? '100%' : 700}
      style={{ top: isMobile ? 0 : 20 }}
      styles={{
        body: {
          maxHeight: isMobile ? 'calc(100vh - 110px)' : '70vh',
          overflowY: 'auto',
          padding: isMobile ? 6 : 16
        }
      }}
    >
      {loading ? (
        <div style={{ textAlign: 'center', padding: '40px 0' }}>
          <Spin size="large" />
          <div style={{ marginTop: 16, color: '#999' }}>正在分析热门话题...</div>
        </div>
      ) : !analysisData ? (
        <Empty description="暂无分析数据" />
      ) : (
        <div>
          <Card 
            size="small" 
            title={
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span style={{ fontSize: isMobile ? 13 : 14 }}>话题概要</span>
              </div>
            }
            style={{ marginBottom: 12 }}
            styles={{ body: { padding: isMobile ? 8 : 12 } }}
          >
            <div style={{ fontSize: isMobile ? 12 : 13, lineHeight: 1.6 }}>
              {analysisData.analysis || '暂无分析'}
            </div>
          </Card>

          {analysisData.related_sectors && analysisData.related_sectors.length > 0 && (
            <Card 
              size="small" 
              title={
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <TagsOutlined style={{ color: '#1890ff' }} />
                  <span style={{ fontSize: isMobile ? 13 : 14 }}>相关板块</span>
                </div>
              }
              style={{ marginBottom: 12 }}
              styles={{ body: { padding: isMobile ? 8 : 12 } }}
            >
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                {analysisData.related_sectors.map((sector, index) => (
                  <Tag 
                    key={index}
                    color="blue"
                    style={{ fontSize: isMobile ? 11 : 12, padding: '4px 8px', margin: 0 }}
                  >
                    {sector.name}
                    {sector.relevance && ` (${(sector.relevance * 100).toFixed(0)}%)`}
                  </Tag>
                ))}
              </div>
            </Card>
          )}

          {analysisData.related_stocks && analysisData.related_stocks.length > 0 && (
            <Card 
              size="small" 
              title={
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <StockOutlined style={{ color: '#52c41a' }} />
                  <span style={{ fontSize: isMobile ? 13 : 14 }}>相关个股</span>
                </div>
              }
              style={{ marginBottom: 12 }}
              styles={{ body: { padding: isMobile ? 8 : 12 } }}
            >
              {analysisData.related_stocks.map((stock, index) => (
                <div 
                  key={index}
                  style={{ 
                    padding: '6px 0',
                    borderBottom: index < analysisData.related_stocks.length - 1 ? '1px solid #f0f0f0' : 'none'
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{ fontWeight: 500, color: '#1890ff', fontSize: isMobile ? 12 : 13 }}>
                      {stock.name}
                    </span>
                    <span style={{ color: '#8c8c8c', fontSize: isMobile ? 11 : 12 }}>
                      {stock.code}
                    </span>
                  </div>
                  {stock.reason && (
                    <div style={{ color: '#595959', fontSize: isMobile ? 11 : 12, marginTop: 4 }}>
                      {stock.reason}
                    </div>
                  )}
                </div>
              ))}
            </Card>
          )}

          {analysisData.market_impact && (
            <Card 
              size="small" 
              title={<span style={{ fontSize: isMobile ? 13 : 14 }}>市场影响</span>}
              style={{ marginBottom: 12 }}
              styles={{ body: { padding: isMobile ? 8 : 12 } }}
            >
              <div style={{ 
                fontSize: isMobile ? 12 : 13, 
                lineHeight: 1.6,
                color: analysisData.market_impact.includes('利好') ? '#cf1322' :
                       analysisData.market_impact.includes('利空') ? '#3f8600' : '#595959'
              }}>
                {analysisData.market_impact}
              </div>
            </Card>
          )}

          {analysisData.investment_suggestion && (
            <Card 
              size="small" 
              title={<span style={{ fontSize: isMobile ? 13 : 14 }}>投资建议</span>}
              styles={{ body: { padding: isMobile ? 8 : 12 } }}
            >
              <div style={{ fontSize: isMobile ? 12 : 13, lineHeight: 1.6 }}>
                {analysisData.investment_suggestion}
              </div>
            </Card>
          )}
        </div>
      )}
    </Modal>
  );
};

export default HotTopicAnalysisModal;
