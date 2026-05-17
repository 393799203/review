import { useState, useEffect } from 'react';
import { Modal, Card, Tag, Spin, Rate, Progress, Divider, Empty, Alert, Button } from 'antd';
import { StockOutlined, FireOutlined, RobotOutlined, TrophyOutlined, DollarOutlined, WarningOutlined, TagsOutlined, ReloadOutlined } from '@ant-design/icons';
import { stockApi } from '../services/api';

const StockAnalysisModal = ({ visible, stockCode, stockName, onClose }) => {
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
    if (visible && stockCode) {
      setAnalysisData(null); // 清空之前的数据
      loadAnalysisData();
    }
  }, [visible, stockCode]);

  const loadAnalysisData = async (force = false) => {
    try {
      setLoading(true);
      const response = await stockApi.analyzeStock(stockCode, force);
      
      if (response.data.success) {
        setAnalysisData(response.data.data);
      }
    } catch (error) {
      console.error('加载分析数据失败:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleReanalyze = () => {
    loadAnalysisData(true);
  };

  const getHeatColor = (heat) => {
    if (heat >= 7) return '#f5222d';
    if (heat >= 4) return '#fa8c16';
    return '#52c41a';
  };

  const getHeatText = (heat) => {
    if (heat >= 7) return '高';
    if (heat >= 4) return '中';
    return '低';
  };

  return (
      <Modal
        title={
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingRight: 30 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <RobotOutlined style={{ color: '#1890ff' }} />
              <span style={{ fontSize: isMobile ? 14 : 16 }}>涨停原因智能分析</span>
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
        width={isMobile ? '100%' : 800}
        style={{ top: isMobile ? 0 : 20 }}
        styles={{
          body: {
            maxHeight: isMobile ? 'calc(100vh - 110px)' : '75vh',
            overflowY: 'auto',
            padding: isMobile ? 6 : 10
          }
        }}
      >
      {loading ? (
        <div style={{ textAlign: 'center', padding: '40px 0' }}>
          <Spin size="large" description="正在分析涨停原因..." />
        </div>
      ) : !analysisData ? (
        <Empty description="暂无分析数据" />
      ) : (
        <div>
          <Card size="small" style={{ marginBottom: 12 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
              <div>
                <div style={{ fontSize: 16, fontWeight: 'bold', marginBottom: 2, display: 'flex', alignItems: 'center', gap: 8 }}>
                  {stockName} ({stockCode})
                  {analysisData.continuous_days && analysisData.continuous_days > 1 ? (
                    <Tag color="red" style={{ fontSize: 11, padding: '0 6px', margin: 0 }}>
                      {analysisData.continuous_days}连板
                    </Tag>
                  ) : (
                    <Tag color="blue" style={{ fontSize: 11, padding: '0 6px', margin: 0 }}>
                      首板
                    </Tag>
                  )}
                </div>
                <div style={{ fontSize: 11, color: '#666' }}>
                  涨停日期: {analysisData.trade_date}
                </div>
              </div>
              <div style={{ textAlign: 'right' }}>
                <div style={{ fontSize: 11, color: '#666', marginBottom: 2 }}>买入推荐指数</div>
                <Rate disabled value={analysisData.recommendation_score} style={{ fontSize: 14 }} />
              </div>
            </div>
            {analysisData.recommendation_reason && (
              <div style={{ marginTop: 8, padding: 8, background: '#f0f5ff', borderRadius: 4, fontSize: 12, lineHeight: 1.6 }}>
                <strong style={{ color: '#1890ff' }}>推荐原因：</strong>
                <span style={{ color: '#262626' }}>{analysisData.recommendation_reason}</span>
              </div>
            )}
            {analysisData.stock_attribute && (
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, paddingTop: 8, borderTop: '1px solid #f0f0f0' }}>
                {analysisData.stock_attribute.type && (
                  <Tag color="purple" style={{ 
                    fontSize: 11, 
                    padding: '2px 6px', 
                    margin: 0,
                    maxWidth: isMobile ? '100%' : 'auto',
                    wordBreak: 'break-word',
                    whiteSpace: 'normal',
                    lineHeight: '16px'
                  }}>
                    {analysisData.stock_attribute.type}
                  </Tag>
                )}
                {analysisData.stock_attribute.market_cap && (
                  <Tag color="blue" style={{ 
                    fontSize: 11, 
                    padding: '2px 6px', 
                    margin: 0,
                    maxWidth: isMobile ? '100%' : 'auto',
                    wordBreak: 'break-word',
                    whiteSpace: 'normal',
                    lineHeight: '16px'
                  }}>
                    {analysisData.stock_attribute.market_cap}
                  </Tag>
                )}
                {analysisData.stock_attribute.investor_type && (
                  <Tag color={analysisData.stock_attribute.investor_type.includes('机构') ? 'green' : analysisData.stock_attribute.investor_type.includes('游资') ? 'red' : 'default'} style={{ 
                    fontSize: 11, 
                    padding: '2px 6px', 
                    margin: 0,
                    maxWidth: isMobile ? '100%' : 'auto',
                    wordBreak: 'break-word',
                    whiteSpace: 'normal',
                    lineHeight: '16px'
                  }}>
                    {analysisData.stock_attribute.investor_type}
                  </Tag>
                )}
                {analysisData.stock_attribute.trading_style && (
                  <Tag color="orange" style={{ 
                    fontSize: 11, 
                    padding: '2px 6px', 
                    margin: 0,
                    maxWidth: isMobile ? '100%' : 'auto',
                    wordBreak: 'break-word',
                    whiteSpace: 'normal',
                    lineHeight: '16px'
                  }}>
                    {analysisData.stock_attribute.trading_style}
                  </Tag>
                )}
              </div>
            )}
          </Card>

          <Card 
            title={<span style={{ fontSize: 13, fontWeight: 'bold' }}>涨停原因 & 炒作逻辑</span>}
            size="small"
            style={{ marginBottom: 12 }}
            styles={{ body: { padding: '8px 12px' } }}
          >
            <div style={{ marginBottom: 8 }}>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                {analysisData.keywords?.map((keyword, index) => (
                  <Tag key={index} color="blue" style={{ 
                    fontSize: 11, 
                    padding: '2px 6px', 
                    margin: 0,
                    maxWidth: isMobile ? '100%' : 'auto',
                    wordBreak: 'break-word',
                    whiteSpace: 'normal',
                    lineHeight: '16px'
                  }}>
                    {keyword}
                  </Tag>
                ))}
              </div>
            </div>
            {analysisData.speculation_logic?.length > 0 && (
              <div style={{ paddingTop: 8, borderTop: '1px solid #f0f0f0' }}>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                  {analysisData.speculation_logic.map((logic, index) => (
                    <Tag key={index} color="orange" style={{ 
                      fontSize: 11, 
                      padding: '2px 6px', 
                      margin: 0,
                      maxWidth: isMobile ? '100%' : 'auto',
                      wordBreak: 'break-word',
                      whiteSpace: 'normal',
                      lineHeight: '16px'
                    }}>
                      {logic.logic}
                    </Tag>
                  ))}
                </div>
              </div>
            )}
          </Card>

          <Card 
            title={
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: 13, fontWeight: 'bold' }}>关联板块</span>
                {analysisData.market_heat && (
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{ fontSize: 11, color: '#666' }}>板块热度</span>
                    <Tag color={getHeatColor(analysisData.market_heat)} style={{ fontSize: 11, padding: '2px 6px', margin: 0 }}>
                      {getHeatText(analysisData.market_heat)} ({analysisData.market_heat})
                    </Tag>
                  </div>
                )}
              </div>
            }
            size="small"
            style={{ marginBottom: 12 }}
            styles={{ body: { padding: '8px 12px' } }}
          >
            {analysisData.sectors?.length > 0 ? (
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                {analysisData.sectors.map((sector, index) => (
                  <Tag key={index} color="green" style={{ 
                    fontSize: 11, 
                    padding: '2px 6px', 
                    margin: 0,
                    maxWidth: isMobile ? '100%' : 'auto',
                    wordBreak: 'break-word',
                    whiteSpace: 'normal',
                    lineHeight: '16px'
                  }}>
                    {sector.name} ({(sector.score * 100).toFixed(0)}%)
                  </Tag>
                ))}
              </div>
            ) : (
              <Empty description="未识别到关联板块" image={Empty.PRESENTED_IMAGE_SIMPLE} />
            )}
          </Card>

          {analysisData.trading_advice && (
            <Card 
              title={<span style={{ fontSize: 13, fontWeight: 'bold' }}>买入建议</span>}
              size="small"
              style={{ marginBottom: 12 }}
              styles={{ body: { padding: '8px 12px' } }}
            >
              <div>
                {analysisData.trading_advice.buy_strategy && (
                  <div style={{ marginBottom: 8 }}>
                    <div style={{ fontSize: 11, color: '#666', marginBottom: 2 }}>买入策略</div>
                    <div style={{ fontSize: 12, lineHeight: 1.5 }}>{analysisData.trading_advice.buy_strategy}</div>
                  </div>
                )}
                
                <div style={{ 
                  display: 'grid', 
                  gridTemplateColumns: isMobile ? 'repeat(2, 1fr)' : 'repeat(2, 1fr)', 
                  gap: isMobile ? 6 : 8, 
                  marginBottom: 8 
                }}>
                  {analysisData.trading_advice.buy_price_range && (
                    <div>
                      <div style={{ fontSize: 11, color: '#666', marginBottom: 2 }}>买入价位</div>
                      <Tag color="blue" style={{ 
                        fontSize: 11, 
                        padding: '2px 6px', 
                        margin: 0,
                        maxWidth: '100%',
                        wordBreak: 'break-word',
                        whiteSpace: 'normal',
                        lineHeight: '16px'
                      }}>{analysisData.trading_advice.buy_price_range}</Tag>
                    </div>
                  )}
                  
                  {analysisData.trading_advice.position_ratio && (
                    <div>
                      <div style={{ fontSize: 11, color: '#666', marginBottom: 2 }}>建议仓位</div>
                      <Tag color="purple" style={{ 
                        fontSize: 11, 
                        padding: '2px 6px', 
                        margin: 0,
                        maxWidth: '100%',
                        wordBreak: 'break-word',
                        whiteSpace: 'normal',
                        lineHeight: '16px'
                      }}>{analysisData.trading_advice.position_ratio}</Tag>
                    </div>
                  )}
                  
                  {analysisData.trading_advice.stop_loss_price && (
                    <div>
                      <div style={{ fontSize: 11, color: '#666', marginBottom: 2 }}>止损位</div>
                      <Tag color="red" style={{ 
                        fontSize: 11, 
                        padding: '2px 6px', 
                        margin: 0,
                        maxWidth: '100%',
                        wordBreak: 'break-word',
                        whiteSpace: 'normal',
                        lineHeight: '16px'
                      }}>{analysisData.trading_advice.stop_loss_price}</Tag>
                    </div>
                  )}
                  
                  {analysisData.trading_advice.take_profit_price && (
                    <div>
                      <div style={{ fontSize: 11, color: '#666', marginBottom: 2 }}>止盈位</div>
                      <Tag color="green" style={{ 
                        fontSize: 11, 
                        padding: '2px 6px', 
                        margin: 0,
                        maxWidth: '100%',
                        wordBreak: 'break-word',
                        whiteSpace: 'normal',
                        lineHeight: '16px'
                      }}>{analysisData.trading_advice.take_profit_price}</Tag>
                    </div>
                  )}
                </div>
                
                <div style={{ 
                  display: 'grid', 
                  gridTemplateColumns: isMobile ? 'repeat(2, 1fr)' : 'repeat(2, 1fr)', 
                  gap: isMobile ? 6 : 8, 
                  marginBottom: 8 
                }}>
                  {analysisData.trading_advice.risk_level && (
                    <div>
                      <div style={{ fontSize: 11, color: '#666', marginBottom: 2 }}>风险等级</div>
                      <Tag color={analysisData.trading_advice.risk_level === '高' ? 'red' : analysisData.trading_advice.risk_level === '中' ? 'orange' : 'green'} style={{ 
                        fontSize: 11, 
                        padding: '2px 6px', 
                        margin: 0,
                        maxWidth: '100%',
                        wordBreak: 'break-word',
                        whiteSpace: 'normal',
                        lineHeight: '16px'
                      }}>
                        {analysisData.trading_advice.risk_level}
                      </Tag>
                    </div>
                  )}
                  
                  {analysisData.trading_advice.holding_period && (
                    <div>
                      <div style={{ fontSize: 11, color: '#666', marginBottom: 2 }}>持有周期</div>
                      <Tag color="cyan" style={{ 
                        fontSize: 11, 
                        padding: '2px 6px', 
                        margin: 0,
                        maxWidth: '100%',
                        wordBreak: 'break-word',
                        whiteSpace: 'normal',
                        lineHeight: '16px'
                      }}>{analysisData.trading_advice.holding_period}</Tag>
                    </div>
                  )}
                </div>
                
                {analysisData.trading_advice.key_points && analysisData.trading_advice.key_points.length > 0 && (
                  <div>
                    <div style={{ fontSize: 11, color: '#666', marginBottom: 4 }}>关键关注点</div>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                      {analysisData.trading_advice.key_points.map((point, index) => (
                        <Tag key={index} color="default" style={{ fontSize: 10, padding: '1px 4px', margin: 0 }}>
                          {point}
                        </Tag>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </Card>
          )}

          {analysisData.holding_advice && (
            <Card 
              title={<span style={{ fontSize: 13, fontWeight: 'bold' }}>持有建议</span>}
              size="small"
              style={{ marginBottom: 12 }}
              styles={{ body: { padding: '8px 12px' } }}
            >
              <div>
                {analysisData.holding_advice.holding_strategy && (
                  <div style={{ marginBottom: 8 }}>
                    <div style={{ fontSize: 11, color: '#666', marginBottom: 4 }}>持有策略</div>
                    <div style={{ fontSize: 12, lineHeight: 1.5 }}>{analysisData.holding_advice.holding_strategy}</div>
                  </div>
                )}
                
                <div style={{ 
                  display: 'grid', 
                  gridTemplateColumns: isMobile ? 'repeat(2, 1fr)' : 'repeat(2, 1fr)', 
                  gap: isMobile ? 6 : 8, 
                  marginBottom: 8 
                }}>
                  {analysisData.holding_advice.target_price && (
                    <div>
                      <div style={{ fontSize: 11, color: '#666', marginBottom: 2 }}>目标价位</div>
                      <Tag color="blue" style={{ 
                        fontSize: 11, 
                        padding: '2px 6px', 
                        margin: 0,
                        maxWidth: '100%',
                        wordBreak: 'break-word',
                        whiteSpace: 'normal',
                        lineHeight: '16px'
                      }}>{analysisData.holding_advice.target_price}</Tag>
                    </div>
                  )}
                  
                  {analysisData.holding_advice.holding_period && (
                    <div>
                      <div style={{ fontSize: 11, color: '#666', marginBottom: 2 }}>持有周期</div>
                      <Tag color="cyan" style={{ 
                        fontSize: 11, 
                        padding: '2px 6px', 
                        margin: 0,
                        maxWidth: '100%',
                        wordBreak: 'break-word',
                        whiteSpace: 'normal',
                        lineHeight: '16px'
                      }}>{analysisData.holding_advice.holding_period}</Tag>
                    </div>
                  )}
                  
                  {analysisData.holding_advice.stop_loss_price && (
                    <div>
                      <div style={{ fontSize: 11, color: '#666', marginBottom: 2 }}>止损价位</div>
                      <Tag color="red" style={{ 
                        fontSize: 11, 
                        padding: '2px 6px', 
                        margin: 0,
                        maxWidth: '100%',
                        wordBreak: 'break-word',
                        whiteSpace: 'normal',
                        lineHeight: '16px'
                      }}>{analysisData.holding_advice.stop_loss_price}</Tag>
                    </div>
                  )}
                  
                  {analysisData.holding_advice.take_profit_price && (
                    <div>
                      <div style={{ fontSize: 11, color: '#666', marginBottom: 2 }}>止盈价位</div>
                      <Tag color="green" style={{ 
                        fontSize: 11, 
                        padding: '2px 6px', 
                        margin: 0,
                        maxWidth: '100%',
                        wordBreak: 'break-word',
                        whiteSpace: 'normal',
                        lineHeight: '16px'
                      }}>{analysisData.holding_advice.take_profit_price}</Tag>
                    </div>
                  )}
                </div>
                
                {analysisData.holding_advice.risk_warning && (
                  <div style={{ marginBottom: 8 }}>
                    <div style={{ fontSize: 11, color: '#666', marginBottom: 4 }}>风险提示</div>
                    <div style={{ fontSize: 12, lineHeight: 1.5, color: '#f5222d' }}>{analysisData.holding_advice.risk_warning}</div>
                  </div>
                )}
                
                {analysisData.holding_advice.key_points && analysisData.holding_advice.key_points.length > 0 && (
                  <div>
                    <div style={{ fontSize: 11, color: '#666', marginBottom: 4 }}>关注要点</div>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                      {analysisData.holding_advice.key_points.map((point, index) => (
                        <Tag key={index} color="default" style={{ fontSize: 10, padding: '1px 4px', margin: 0 }}>
                          {point}
                        </Tag>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </Card>
          )}

          <Divider style={{ margin: '8px 0' }} />

          <div style={{ 
            padding: 8, 
            background: '#f5f5f5', 
            borderRadius: 4,
            fontSize: 12,
            lineHeight: 1.6
          }}>
            <strong>分析摘要：</strong>
            <div style={{ marginTop: 4 }}>
              {analysisData.analysis_summary}
            </div>
          </div>
        </div>
      )}
    </Modal>
  );
};

export default StockAnalysisModal;
