import React, { useState, useEffect } from 'react';
import { Modal, Input, Button, message, Spin, Card, Tag, Form, Popconfirm, Divider, Progress, Badge } from 'antd';
import { SearchOutlined, RobotOutlined, PlusOutlined, EditOutlined, DeleteOutlined, SaveOutlined, BulbOutlined, TrophyOutlined, WarningOutlined, CheckCircleOutlined } from '@ant-design/icons';
import ReactMarkdown from 'react-markdown';
import api from '../services/api';

const { TextArea } = Input;

// 结构化结果展示组件
const StructuredResultDisplay = ({ data }) => {
  // 检查是否是结构化数据
  if (!data) {
    return <div style={{ textAlign: 'center', color: '#999' }}>暂无结果</div>;
  }
  
  // 如果数据对象包含 structured 字段，判断是否结构化
  const isStructured = data.structured === true;
  
  console.log('isStructured:', isStructured);
  
  // 如果不是结构化数据，使用Markdown展示
  if (!isStructured) {
    const text = typeof data === 'string' ? data : (data.analysis || data.raw_analysis || '');
    console.log('Fallback to markdown, text:', text);
    return <ReactMarkdown>{text}</ReactMarkdown>;
  }
  
  // 获取解析后的结构化分析数据
  const analysis = data.analysis || {};
  
  console.log('Using structured analysis:', analysis);
  
  return (
    <div style={{ fontSize: 14 }}>
      {/* 总结部分 */}
      {analysis.summary && (
        <Card 
          size="small" 
          style={{ marginBottom: 12, backgroundColor: '#f0f7ff', border: '1px solid #1890ff' }}
        >
          <div style={{ fontWeight: 'bold', marginBottom: 8, color: '#1890ff' }}>
            <BulbOutlined /> 分析总结
          </div>
          <div>{analysis.summary}</div>
        </Card>
      )}
      
      {/* 目标股票信息 */}
      {analysis.target_stock && (
        <Card size="small" style={{ marginBottom: 12 }}>
          <div style={{ fontWeight: 'bold', marginBottom: 8 }}>
            目标股票：{analysis.target_stock.name} ({analysis.target_stock.code})
          </div>
          <div style={{ fontSize: 13, color: '#666' }}>
            板块：{analysis.target_stock.block} | 
            涨停原因：{analysis.target_stock.reason} | 
            涨停日期：{analysis.target_stock.date}
          </div>
        </Card>
      )}
      
      {/* 对标股票列表 */}
      {analysis.comparable_stocks && analysis.comparable_stocks.length > 0 && (
        <div style={{ marginBottom: 12 }}>
          <div style={{ fontWeight: 'bold', marginBottom: 8, color: '#52c41a' }}>
            <TrophyOutlined /> 对标股票推荐 ({analysis.comparable_stocks.length}只)
          </div>
          {analysis.comparable_stocks.map((stock, index) => (
            <Card 
              key={index} 
              size="small" 
              style={{ marginBottom: 8, border: stock.match_score >= 8 ? '2px solid #52c41a' : '1px solid #d9d9d9' }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                <div>
                  <span style={{ fontWeight: 'bold', fontSize: 15 }}>{stock.name}</span>
                  <span style={{ marginLeft: 8, color: '#999', fontSize: 13 }}>{stock.code}</span>
                  {stock.match_score >= 8 && <Badge count="高度匹配" style={{ marginLeft: 8, backgroundColor: '#52c41a' }} />}
                </div>
                <div style={{ textAlign: 'right' }}>
                  <Progress 
                    type="circle" 
                    percent={stock.match_score * 10} 
                    width={50} 
                    format={percent => `${stock.match_score}分`}
                    strokeColor={stock.match_score >= 8 ? '#52c41a' : stock.match_score >= 6 ? '#1890ff' : '#faad14'}
                  />
                </div>
              </div>
              
              <div style={{ fontSize: 12, color: '#666', marginBottom: 6 }}>
                板块：{stock.block} | 涨停原因：{stock.reason} | 日期：{stock.date}
              </div>
              
              {/* 标签 */}
              {stock.tags && stock.tags.length > 0 && (
                <div style={{ marginBottom: 6 }}>
                  {stock.tags.map((tag, i) => (
                    <Tag key={i} color="blue" style={{ marginBottom: 4 }}>{tag}</Tag>
                  ))}
                </div>
              )}
              
              {/* 主题 */}
              {stock.themes && stock.themes.length > 0 && (
                <div style={{ marginBottom: 6 }}>
                  {stock.themes.map((theme, i) => (
                    <Tag key={i} color="cyan" style={{ marginBottom: 4 }}>{theme}</Tag>
                  ))}
                </div>
              )}
              
              {/* 匹配度详情 */}
              {stock.match_details && (
                <div style={{ fontSize: 12, marginTop: 8 }}>
                  <div style={{ marginBottom: 4, fontWeight: 'bold' }}>匹配度评分：</div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 4 }}>
                    <span>市值匹配：{stock.match_details.market_cap_match}分</span>
                    <span>涨停匹配：{stock.match_details.limit_up_match}分</span>
                    <span>板块题材：{stock.match_details.block_theme_match}分</span>
                    <span>历史表现：{stock.match_details.history_match}分</span>
                    <span>技术形态：{stock.match_details.tech_match}分</span>
                  </div>
                </div>
              )}
              
              {/* 分析说明 */}
              {stock.analysis && (
                <div style={{ fontSize: 12, marginTop: 8, padding: 8, backgroundColor: '#fafafa', borderRadius: 4 }}>
                  {stock.analysis}
                </div>
              )}
            </Card>
          ))}
        </div>
      )}
      
      {/* 投资建议 */}
      {analysis.recommendations && (
        <Card size="small" style={{ marginBottom: 12, backgroundColor: '#fff7e6', border: '1px solid #faad14' }}>
          <div style={{ fontWeight: 'bold', marginBottom: 8, color: '#faad14' }}>
            <CheckCircleOutlined /> 投资建议
          </div>
          
          {analysis.recommendations.best_match && (
            <div style={{ marginBottom: 8 }}>
              <span style={{ fontWeight: 'bold' }}>最佳对标：</span>
              <Tag color="green">{analysis.recommendations.best_match}</Tag>
            </div>
          )}
          
          {analysis.recommendations.logic_match && (
            <div style={{ marginBottom: 8 }}>
              <span style={{ fontWeight: 'bold' }}>逻辑对标：</span>
              <Tag color="blue">{analysis.recommendations.logic_match}</Tag>
            </div>
          )}
          
          {analysis.recommendations.other_matches && analysis.recommendations.other_matches.length > 0 && (
            <div style={{ marginBottom: 8 }}>
              <span style={{ fontWeight: 'bold' }}>其他对标：</span>
              {analysis.recommendations.other_matches.map((code, i) => (
                <Tag key={i} color="default" style={{ marginBottom: 4 }}>{code}</Tag>
              ))}
            </div>
          )}
          
          {analysis.recommendations.operation_advice && (
            <div style={{ marginBottom: 8, padding: 8, backgroundColor: '#fff', borderRadius: 4 }}>
              <div style={{ fontWeight: 'bold', marginBottom: 4 }}>操作建议：</div>
              {analysis.recommendations.operation_advice}
            </div>
          )}
          
          {analysis.recommendations.risk_warning && (
            <div style={{ padding: 8, backgroundColor: '#fff2f0', borderRadius: 4, border: '1px solid #ffccc7' }}>
              <div style={{ fontWeight: 'bold', marginBottom: 4, color: '#ff4d4f' }}>
                <WarningOutlined /> 风险提示
              </div>
              {analysis.recommendations.risk_warning}
            </div>
          )}
        </Card>
      )}
    </div>
  );
};

const ComparableStockModal = ({ 
  visible, 
  onClose, 
  stockCode, 
  stockName, 
  block, 
  limitUpReason,
  dateStr 
}) => {
  const [strategy, setStrategy] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState('');
  const [isMobile, setIsMobile] = useState(false);
  const [userStrategies, setUserStrategies] = useState([]);
  const [strategiesLoading, setStrategiesLoading] = useState(false);
  const [showStrategyModal, setShowStrategyModal] = useState(false);
  const [editingStrategy, setEditingStrategy] = useState(null);
  const [strategyForm] = Form.useForm();
  const [selectedStrategyId, setSelectedStrategyId] = useState(null);
  

  
  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 768);
    };
    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);
  
  useEffect(() => {
    if (visible) {
      loadUserStrategies();
      setStrategy('');
      setResult('');
    }
  }, [visible]);
  
  const loadUserStrategies = async () => {
    try {
      setStrategiesLoading(true);
      
      const response = await api.get('/strategies', { params: { strategy_type: 'comparable' } });
      
      if (response.data.success) {
        const strategies = response.data.data || [];
        setUserStrategies(strategies);
        
        if (strategies.length > 0) {
          // 查找默认策略
          const defaultStrategy = strategies.find(s => s.is_default === 1 || s.is_default === true);
          if (defaultStrategy) {
            setSelectedStrategyId(defaultStrategy.id);
            setStrategy(defaultStrategy.query_template);
          } else {
            // 没有默认策略，选择第一个
            setSelectedStrategyId(strategies[0].id);
            setStrategy(strategies[0].query_template);
          }
        }
      }
    } catch (error) {
      console.error('加载用户策略失败:', error);
      message.error('加载策略失败');
    } finally {
      setStrategiesLoading(false);
    }
  };
  
  const handleAnalyze = async () => {
    if (!strategy.trim()) {
      message.warning('请输入对标条件');
      return;
    }
    
    try {
      setLoading(true);
      setResult('');
      
      const response = await api.post('/comparable/analyze', {
        stock_code: stockCode,
        stock_name: stockName,
        block: block || '',
        limit_up_reason: limitUpReason || '',
        date: dateStr,
        strategy: strategy
      });
      
      if (response.data.success) {
        // 保存完整的分析结果（可能是结构化JSON或原始文本）
        const analysisData = response.data.data;
        setResult(analysisData);
        message.success('分析完成');
      } else {
        message.error(response.data.message || '分析失败');
      }
    } catch (error) {
      console.error('对标分析失败:', error);
      message.error('分析失败，请稍后重试');
    } finally {
      setLoading(false);
    }
  };
  
  const handleSaveStrategy = async (values) => {
    try {
      if (editingStrategy) {
        // 更新现有策略
        const response = await api.put(`/strategies/${editingStrategy.id}`, {
          strategy_name: values.strategy_name,
          query_template: values.query_template,
          description: values.description,
          strategy_type: 'comparable',
          is_default: values.is_default || false
        });
        
        if (response.data.success) {
          message.success('策略更新成功');
          loadUserStrategies();
          setShowStrategyModal(false);
          strategyForm.resetFields();
        } else {
          message.error(response.data.message || '更新失败');
        }
      } else {
        // 创建新策略
        const response = await api.post('/strategies', {
          strategy_name: values.strategy_name,
          query_template: values.query_template,
          description: values.description,
          strategy_type: 'comparable',
          is_default: values.is_default || false
        });
        
        if (response.data.success) {
          message.success('策略保存成功');
          loadUserStrategies();
          setShowStrategyModal(false);
          strategyForm.resetFields();
        } else {
          message.error(response.data.message || '保存失败');
        }
      }
      
      setEditingStrategy(null);
    } catch (error) {
      console.error('保存策略失败:', error);
      message.error('保存失败，请稍后重试');
    }
  };
  
  const handleDeleteStrategy = async (strategyId) => {
    try {
      const response = await api.delete(`/strategies/${strategyId}`);
      
      if (response.data.success) {
        message.success('策略删除成功');
        loadUserStrategies();
        
        // 如果删除的是当前选中的策略，清空选择
        if (selectedStrategyId === strategyId) {
          setSelectedStrategyId(null);
          setStrategy('');
        }
      } else {
        message.error(response.data.message || '删除失败');
      }
    } catch (error) {
      console.error('删除策略失败:', error);
      message.error('删除失败，请稍后重试');
    }
  };
  
  return (
    <>
      <Modal
        title={
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <RobotOutlined style={{ fontSize: isMobile ? 16 : 18, color: '#1890ff' }} />
            <span style={{ fontSize: isMobile ? 14 : 16 }}>
              找对标分析 - {stockName} ({stockCode})
            </span>
          </div>
        }
        open={visible}
        onCancel={onClose}
        width={isMobile ? '95%' : 1100}
        footer={null}
        style={{ top: isMobile ? 20 : 10 }}
        styles={{
          body: {
            padding: isMobile ? '8px' : '8px 12px',
            maxHeight: isMobile ? '75vh' : 'none',
            overflow: isMobile ? 'auto' : 'visible',
          },
        }}
      >
        <div style={{ marginBottom: isMobile ? 6 : 8 }}>
          <div style={{ marginBottom: isMobile ? 8 : 12 }}>
            <div style={{ 
              display: 'flex', 
              alignItems: 'center', 
              justifyContent: 'space-between',
              marginBottom: isMobile ? 8 : 12 
            }}>
              <div style={{ 
                fontSize: isMobile ? 12 : 13, 
                fontWeight: 600, 
                color: '#262626',
                display: 'flex',
                alignItems: 'center',
                gap: 6
              }}>
                <span style={{
                  display: 'inline-block',
                  width: 3,
                  height: 14,
                  background: 'linear-gradient(180deg, #1890ff 0%, #096dd9 100%)',
                  borderRadius: 2
                }}></span>
                选择策略
              </div>
              
              <div style={{ fontSize: isMobile ? 10 : 11, color: '#8c8c8c' }}>
                <BulbOutlined style={{ marginRight: 4 }} />
                支持：{`{date}`}、{`{code}`}、{`{name}`}、{`{block}`}
              </div>
            </div>
            
            <Spin spinning={strategiesLoading} description="加载策略中...">
              <div style={{ 
                display: isMobile ? 'flex' : 'grid',
                gridTemplateColumns: isMobile ? undefined : 'repeat(auto-fill, minmax(160px, 1fr))',
                gap: isMobile ? 8 : 10,
                overflowX: isMobile ? 'auto' : 'visible',
                overflowY: isMobile ? 'hidden' : 'visible',
                whiteSpace: isMobile ? 'nowrap' : 'normal',
                WebkitOverflowScrolling: isMobile ? 'touch' : 'auto',
                scrollbarWidth: isMobile ? 'none' : 'auto',
                msOverflowStyle: isMobile ? 'none' : 'auto',
                paddingBottom: isMobile ? 4 : 0
              }}>
                {userStrategies.map(strategyItem => {
                  const isActive = selectedStrategyId === strategyItem.id;
                  return (
                    <div
                      key={strategyItem.id}
                      onClick={() => {
                        setSelectedStrategyId(strategyItem.id);
                        setStrategy(strategyItem.query_template);
                      }}
                      style={{
                        position: 'relative',
                        padding: isMobile ? '10px 12px' : '12px 14px',
                        borderRadius: 8,
                        border: `2px solid ${isActive ? 'transparent' : '#f0f0f0'}`,
                        background: isActive 
                          ? 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'
                          : '#fafafa',
                        cursor: 'pointer',
                        transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
                        transform: isActive ? 'scale(1.02)' : 'scale(1)',
                        boxShadow: isActive 
                          ? '0 4px 12px rgba(102, 126, 234, 0.4)'
                          : '0 1px 3px rgba(0, 0, 0, 0.05)',
                        overflow: 'hidden',
                        minWidth: isMobile ? 'calc(50% - 4px)' : 'auto',
                        flexShrink: isMobile ? 0 : 1,
                        width: isMobile ? 'calc(50% - 4px)' : 'auto'
                      }}
                      onMouseEnter={(e) => {
                        if (!isActive) {
                          e.currentTarget.style.transform = 'scale(1.02)';
                          e.currentTarget.style.boxShadow = '0 4px 12px rgba(0, 0, 0, 0.1)';
                          e.currentTarget.style.borderColor = '#d9d9d9';
                        }
                      }}
                      onMouseLeave={(e) => {
                        if (!isActive) {
                          e.currentTarget.style.transform = 'scale(1)';
                          e.currentTarget.style.boxShadow = '0 1px 3px rgba(0, 0, 0, 0.05)';
                          e.currentTarget.style.borderColor = '#f0f0f0';
                        }
                      }}
                    >
                      {isActive && (
                        <div style={{
                          position: 'absolute',
                          top: 0,
                          right: 0,
                          width: 0,
                          height: 0,
                          borderStyle: 'solid',
                          borderWidth: '0 32px 32px 0',
                          borderColor: 'transparent rgba(255, 255, 255, 0.3) transparent transparent',
                          pointerEvents: 'none'
                        }} />
                      )}
                      
                      <div style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between'
                      }}>
                        <div style={{
                          fontSize: isMobile ? 12 : 13,
                          fontWeight: 600,
                          color: isActive ? '#fff' : '#262626',
                          flex: 1,
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          whiteSpace: 'nowrap'
                        }}>
                          {strategyItem.strategy_name}
                        </div>
                        
                        <div style={{
                           display: 'flex',
                           alignItems: 'center',
                           gap: 4,
                           marginLeft: 8
                         }}
                         onClick={(e) => e.stopPropagation()}
                         >
                             <div
                               onClick={(e) => {
                                 e.stopPropagation();
                                 setEditingStrategy(strategyItem);
                                 strategyForm.setFieldsValue({
                                   strategy_name: strategyItem.strategy_name,
                                   query_template: strategyItem.query_template,
                                   description: strategyItem.description
                                 });
                                 setShowStrategyModal(true);
                               }}
                               style={{
                                 display: 'flex',
                                 alignItems: 'center',
                                 justifyContent: 'center',
                                 width: 22,
                                 height: 22,
                                 borderRadius: 4,
                                 background: isActive ? 'rgba(255, 255, 255, 0.15)' : '#fff',
                                 cursor: 'pointer',
                                 outline: 'none',
                                 boxShadow: 'none'
                               }}
                               tabIndex={-1}
                               onMouseEnter={(e) => {
                                 if (isActive) {
                                   e.currentTarget.style.background = 'rgba(255, 255, 255, 0.25)';
                                 } else {
                                   e.currentTarget.style.background = '#e6f7ff';
                                   e.currentTarget.style.color = '#1890ff';
                                 }
                               }}
                               onMouseLeave={(e) => {
                                 if (isActive) {
                                   e.currentTarget.style.background = 'rgba(255, 255, 255, 0.15)';
                                 } else {
                                   e.currentTarget.style.background = '#fff';
                                   e.currentTarget.style.color = '#595959';
                                 }
                               }}
                             >
                               <EditOutlined style={{ 
                                 fontSize: 11, 
                                 color: isActive ? '#fff' : '#595959',
                                 pointerEvents: 'none'
                               }} />
                             </div>
                            
                            <Popconfirm
                              title="确定要删除这个策略吗？"
                              description="删除后无法恢复"
                              onConfirm={(e) => {
                                e.stopPropagation();
                                handleDeleteStrategy(strategyItem.id);
                              }}
                              okText="确定"
                              cancelText="取消"
                              okButtonProps={{ danger: true }}
                            >
                              <div
                                onClick={(e) => e.stopPropagation()}
                                style={{
                                  display: 'flex',
                                  alignItems: 'center',
                                  justifyContent: 'center',
                                  width: 22,
                                  height: 22,
                                  borderRadius: 4,
                                  background: isActive ? 'rgba(255, 255, 255, 0.15)' : '#fff',
                                  cursor: 'pointer',
                                  outline: 'none',
                                  boxShadow: 'none'
                                }}
                                tabIndex={-1}
                                onMouseEnter={(e) => {
                                  if (isActive) {
                                    e.currentTarget.style.background = 'rgba(255, 107, 107, 0.3)';
                                  } else {
                                    e.currentTarget.style.background = '#fff1f0';
                                  }
                                }}
                                onMouseLeave={(e) => {
                                  if (isActive) {
                                    e.currentTarget.style.background = 'rgba(255, 255, 255, 0.15)';
                                  } else {
                                    e.currentTarget.style.background = '#fff';
                                  }
                                }}
                              >
                                <DeleteOutlined style={{ 
                                  fontSize: 11, 
                                  color: isActive ? '#fff' : '#ff4d4f'
                                }} />
                              </div>
                            </Popconfirm>
                          </div>
                      </div>
                      
                      {strategyItem.description && (
                        <div style={{
                          fontSize: isMobile ? 10 : 11,
                          color: isActive ? 'rgba(255, 255, 255, 0.8)' : '#8c8c8c',
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          whiteSpace: 'nowrap',
                          marginTop: 4
                        }}>
                          {strategyItem.description}
                        </div>
                      )}
                    </div>
                  );
                })}
                
                <div
                  onClick={() => {
                    setEditingStrategy(null);
                    strategyForm.resetFields();
                    setShowStrategyModal(true);
                  }}
                  style={{
                    position: 'relative',
                    padding: isMobile ? '10px 12px' : '12px 14px',
                    borderRadius: 8,
                    border: '2px dashed #d9d9d9',
                    background: '#fafafa',
                    cursor: 'pointer',
                    transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
                    minHeight: isMobile ? 60 : 68,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    outline: 'none',
                    order: 999,
                    minWidth: isMobile ? 'calc(50% - 4px)' : 'auto',
                    flexShrink: isMobile ? 0 : 1,
                    width: isMobile ? 'calc(50% - 4px)' : 'auto'
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.borderColor = '#1890ff';
                    e.currentTarget.style.background = '#e6f7ff';
                    e.currentTarget.style.transform = 'scale(1.02)';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.borderColor = '#d9d9d9';
                    e.currentTarget.style.background = '#fafafa';
                    e.currentTarget.style.transform = 'scale(1)';
                  }}
                >
                  <div style={{
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    gap: 4
                  }}>
                    <PlusOutlined style={{ 
                      fontSize: isMobile ? 18 : 20, 
                      color: '#8c8c8c'
                    }} />
                    <div style={{
                      fontSize: isMobile ? 11 : 12,
                      color: '#8c8c8c',
                      fontWeight: 500
                    }}>
                      新增策略
                    </div>
                  </div>
                </div>
              </div>
            </Spin>
          </div>
          
          <div style={{ 
            position: 'relative',
            marginBottom: isMobile ? 8 : 10
          }}>
            <div style={{
              position: 'absolute',
              top: -8,
              left: 12,
              background: '#fff',
              padding: '0 4px',
              fontSize: isMobile ? 11 : 12,
              color: '#8c8c8c',
              zIndex: 1
            }}>
              对标条件
            </div>
            <TextArea
              rows={4}
              value={strategy}
              onChange={(e) => setStrategy(e.target.value)}
              placeholder="输入对标条件...&#10;支持变量：{date}、{code}、{name}、{block}"
              style={{ 
                fontFamily: 'Consolas, Monaco, "Courier New", monospace', 
                fontSize: isMobile ? 12 : 13,
                borderRadius: 8,
                minHeight: isMobile ? '120px' : '120px',
                border: '1px solid #e8e8e8',
                backgroundColor: '#fafafa',
                padding: isMobile ? '10px 12px' : '12px 14px',
                transition: 'all 0.3s',
                boxShadow: '0 1px 3px rgba(0, 0, 0, 0.04)'
              }}
              onFocus={(e) => {
                e.target.style.borderColor = '#1890ff';
                e.target.style.boxShadow = '0 2px 8px rgba(24, 144, 255, 0.15)';
                e.target.style.backgroundColor = '#fff';
              }}
              onBlur={(e) => {
                e.target.style.borderColor = '#e8e8e8';
                e.target.style.boxShadow = '0 1px 3px rgba(0, 0, 0, 0.04)';
                e.target.style.backgroundColor = '#fafafa';
              }}
            />
          </div>
        </div>

        <Button
          type="primary"
          icon={<SearchOutlined />}
          onClick={handleAnalyze}
          loading={loading}
          size={isMobile ? 'small' : 'middle'}
          block
          style={{ marginBottom: isMobile ? 4 : 6 }}
        >
          开始对标分析
        </Button>

        <Spin spinning={loading}>
          <div style={{ 
            height: isMobile ? '300px' : '400px',
            backgroundColor: '#f5f5f5', 
            borderRadius: 4,
            overflowY: 'auto',
            display: 'flex',
            flexDirection: 'column'
          }}>
            {result && (
              <div style={{ 
                padding: 16,
                flex: 1
              }}>
                <StructuredResultDisplay data={result} />
              </div>
            )}
            
            {!result && !loading && (
              <div style={{ 
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                height: '100%',
                color: '#999',
                fontSize: isMobile ? 12 : 14 
              }}>
                暂无结果
              </div>
            )}
          </div>
        </Spin>
      </Modal>

      <Modal
        title={editingStrategy ? '编辑策略' : '创建新策略'}
        open={showStrategyModal}
        onCancel={() => {
          setShowStrategyModal(false);
          strategyForm.resetFields();
          setEditingStrategy(null);
        }}
        footer={null}
        width={isMobile ? '95%' : 600}
      >
        <Form
          form={strategyForm}
          layout="vertical"
          onFinish={handleSaveStrategy}
        >
          <Form.Item
            name="strategy_name"
            label="策略名称"
            rules={[{ required: true, message: '请输入策略名称' }]}
          >
            <Input placeholder="例如：同板块对标策略" />
          </Form.Item>
          
          <Form.Item
            name="query_template"
            label="对标条件模板"
            rules={[{ required: true, message: '请输入对标条件模板' }]}
            extra="支持变量：{date}、{code}、{name}、{block} 会被自动替换"
          >
            <TextArea 
              rows={6} 
              placeholder="市值小于50亿，{block}板块&#10;近期有涨停记录&#10;流通市值相近"
              style={{ fontFamily: 'monospace' }}
            />
          </Form.Item>
          
          <Form.Item
            name="description"
            label="策略描述"
          >
            <Input.TextArea rows={2} placeholder="描述这个策略的对标逻辑" />
          </Form.Item>
          
          <Form.Item>
            <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
              <Button onClick={() => {
                setShowStrategyModal(false);
                strategyForm.resetFields();
                setEditingStrategy(null);
              }}>
                取消
              </Button>
              <Button type="primary" htmlType="submit" icon={<SaveOutlined />}>
                保存策略
              </Button>
            </div>
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
};

export default ComparableStockModal;