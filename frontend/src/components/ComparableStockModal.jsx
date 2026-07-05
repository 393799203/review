import React, { useState, useEffect } from 'react';
import { Modal, Input, Button, message, Spin, Tag, Form, Popconfirm, Alert, Space, Switch, Table, Divider } from 'antd';
import { RobotOutlined, PlusOutlined, EditOutlined, DeleteOutlined, AimOutlined, UpOutlined, DownOutlined } from '@ant-design/icons';
import { stockApi } from '../services/api';
import StockKlineModal from './StockKlineModal';
import ReactMarkdown from 'react-markdown';

const { TextArea } = Input;

const ComparableStockModal = ({ visible, onClose, dateStr, context = {} }) => {
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [isMobile, setIsMobile] = useState(false);
  const [queryType, setQueryType] = useState(null);
  const [enableSkill, setEnableSkill] = useState(true);
  const [result, setResult] = useState(null);
  const [showAnalysis, setShowAnalysis] = useState(false);
  const [klineVisible, setKlineVisible] = useState(false);
  const [selectedStock, setSelectedStock] = useState(null);
  const [dateRange, setDateRange] = useState('');

  const [userStrategies, setUserStrategies] = useState([]);
  const [strategiesLoading, setStrategiesLoading] = useState(false);
  const [showStrategyModal, setShowStrategyModal] = useState(false);
  const [editingStrategy, setEditingStrategy] = useState(null);
  const [strategyForm] = Form.useForm();

  useEffect(() => {
    const checkMobile = () => { setIsMobile(window.innerWidth < 768); };
    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  const loadUserStrategies = async () => {
    try {
      setStrategiesLoading(true);
      const response = await stockApi.getWencaiStrategies();
      if (response.data.success) {
        const comparableStrategies = (response.data.data || []).filter(s => s.strategy_type === 'comparable');
        setUserStrategies(comparableStrategies);
        if (comparableStrategies.length > 0 && !queryType) {
          const ds = comparableStrategies.find(s => s.is_default === 1);
          setQueryType(ds ? ds.id : comparableStrategies[0].id);
          const first = comparableStrategies[0];
          setEnableSkill(first.enable_skill !== 0);
        }
      }
    } catch (error) {
      console.error('加载用户策略失败:', error);
    } finally {
      setStrategiesLoading(false);
    }
  };

  useEffect(() => {
    if (visible) {
      setResult(null);
      setDateRange('');
      const init = async () => {
        if (context?.stockCode && dateStr) {
          try {
            const r = await stockApi.getFirstLimitUpDate(context.stockCode, dateStr);
            if (r.data.success) setDateRange(r.data.data.range);
          } catch { setDateRange(dateStr); }
        }
        loadUserStrategies();
      };
      init();
    }
  }, [visible]);

  useEffect(() => {
    if (visible && queryType) {
      const strategy = userStrategies.find(s => s.id === queryType);
      if (strategy) {
        let t = (strategy.query_template || '');
        t = t.replace(/\{date\}/g, dateRange || dateStr || '');
        t = t.replace(/\{code\}/g, context?.stockCode || '').replace(/\{name\}/g, context?.stockName || '').replace(/\{block\}/g, context?.blockName || '');
        setQuery(t);
        setEnableSkill(strategy.enable_skill !== 0);
      }
    }
  }, [visible, queryType, userStrategies, dateStr, context, dateRange]);

  const handleAnalyze = async () => {
    if (!query.trim()) { message.error('请输入查询需求'); return; }
    setLoading(true);
    setResult(null);
    try {
      const originalTemplate = userStrategies.find(s => s.id === queryType)?.query_template || '';
      const payload = { query, context: { stock_code: context?.stockCode || '', stock_name: context?.stockName || '', block_name: context?.blockName || '', reason: context?.reason || '' }, base_date: dateStr || undefined, has_date: originalTemplate.includes('{date}') };
      if (enableSkill) payload.query = query + ' 并使用A股全栈数据技能';
      const response = await stockApi.comparableAnalyze(payload);
      if (response.data.success) { setResult(response.data.data); message.success('分析完成'); }
      else { message.error(response.data.error || '分析失败'); }
    } catch (error) {
      message.error('分析失败：' + (error.response?.data?.error || error.message));
    } finally { setLoading(false); }
  };

  const handleSaveStrategy = async (values) => {
    try {
      const payload = { ...values, strategy_type: 'comparable', enable_skill: enableSkill ? 1 : 0 };
      if (editingStrategy) {
        const r = await stockApi.updateWencaiStrategy(editingStrategy.id, payload);
        if (r.data.success) { message.success('策略更新成功'); loadUserStrategies(); setShowStrategyModal(false); strategyForm.resetFields(); }
        else { message.error(r.data.error || '更新失败'); }
      } else {
        const r = await stockApi.createWencaiStrategy(payload);
        if (r.data.success) { message.success('策略创建成功'); loadUserStrategies(); setShowStrategyModal(false); strategyForm.resetFields(); }
        else { message.error(r.data.error || '创建失败'); }
      }
    } catch (error) {
      message.error('保存失败：' + (error.response?.data?.error || error.message));
    }
  };

  const handleDeleteStrategy = async (strategyId) => {
    try {
      const r = await stockApi.deleteWencaiStrategy(strategyId);
      if (r.data.success) { message.success('策略删除成功'); loadUserStrategies(); if (queryType === strategyId) setQueryType(null); }
      else { message.error(r.data.error || '删除失败'); }
    } catch (error) { message.error('删除失败：' + (error.response?.data?.error || error.message)); }
  };

  const categoryOrder = ['最直接对标', '核心逻辑对标', '其他相关对标'];
  const categoryColors = {
    '最直接对标': { bg: '#f6ffed', border: '#52c41a', text: '#389e0d' },
    '核心逻辑对标': { bg: '#fff2e8', border: '#fa8c16', text: '#d46b08' },
    '其他相关对标': { bg: '#e6f7ff', border: '#1890ff', text: '#096dd9' },
  };

  const sortByCategory = (stocks) => {
    return [...stocks].sort((a, b) => {
      const ia = categoryOrder.indexOf(a.category);
      const ib = categoryOrder.indexOf(b.category);
      return (ia >= 0 ? ia : 99) - (ib >= 0 ? ib : 99);
    });
  };

  const stockColumns = [
    {
      title: '对标角度', dataIndex: 'category', key: 'category', width: 110,
      render: (val) => {
        const c = categoryColors[val] || { bg: '#fafafa', border: '#d9d9d9', text: '#666' };
        return <Tag color={c.text} style={{ background: c.bg, borderColor: c.border, color: c.text }}>{val || '-'}</Tag>;
      }
    },
    { title: '股票代码', dataIndex: 'code', key: 'code', width: 100,
      render: (text, record) => (<a style={{ fontWeight: 600 }} onClick={() => { setSelectedStock({ code: text, name: record.name }); setKlineVisible(true); }}>{text}</a>) },
    { title: '股票名称', dataIndex: 'name', key: 'name', width: 120,
      render: (text, record) => (<a style={{ color: '#1890ff' }} onClick={() => { setSelectedStock({ code: record.code, name: text }); setKlineVisible(true); }}>{text}</a>) },
    { title: '日期', dataIndex: 'date', key: 'date', width: 110 },
    { title: '涨幅', dataIndex: 'change_pct', key: 'change_pct', width: 80, align: 'right',
      render: (val) => { const n = parseFloat(val); const c = n > 0 ? '#f5222d' : n < 0 ? '#52c41a' : '#666'; return <span style={{ color: c, fontWeight: 600 }}>{isNaN(n) ? '-' : `${n}%`}</span>; } },
    { title: '题材标签', dataIndex: 'reason', key: 'reason', ellipsis: true },
  ];

  const renderStrategyCards = () => (
    <Spin spinning={strategiesLoading}>
      <div style={{ display: isMobile ? 'flex' : 'grid', gridTemplateColumns: isMobile ? undefined : 'repeat(auto-fill, minmax(160px, 1fr))', gap: isMobile ? 8 : 10, overflowX: isMobile ? 'auto' : 'visible', paddingBottom: isMobile ? 4 : 0 }}>
        {userStrategies.map(s => {
          const isActive = queryType === s.id;
          return (
            <div key={s.id} onClick={() => setQueryType(s.id)} style={{ position: 'relative', padding: isMobile ? '10px 12px' : '12px 14px', borderRadius: 8, border: `2px solid ${isActive ? 'transparent' : '#f0f0f0'}`, background: isActive ? 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' : '#fafafa', cursor: 'pointer', transition: 'all 0.3s', transform: isActive ? 'scale(1.02)' : 'scale(1)', boxShadow: isActive ? '0 4px 12px rgba(102,126,234,0.4)' : '0 1px 3px rgba(0,0,0,0.05)', minWidth: isMobile ? 'calc(50% - 4px)' : 'auto', flexShrink: isMobile ? 0 : 1, width: isMobile ? 'calc(50% - 4px)' : 'auto' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div style={{ fontSize: isMobile ? 12 : 13, fontWeight: 600, color: isActive ? '#fff' : '#262626', flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{s.strategy_name}</div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 4, marginLeft: 8 }} onClick={(e) => e.stopPropagation()}>
                  <div onClick={() => { setEditingStrategy(s); strategyForm.setFieldsValue(s); setEnableSkill(s.enable_skill !== 0); setShowStrategyModal(true); }} style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', width: 22, height: 22, borderRadius: 4, background: isActive ? 'rgba(255,255,255,0.15)' : '#fff', cursor: 'pointer' }}><EditOutlined style={{ fontSize: 11, color: isActive ? '#fff' : '#595959' }} /></div>
                  <Popconfirm title="确定要删除这个策略吗？" onConfirm={(e) => { e.stopPropagation(); handleDeleteStrategy(s.id); }} okText="确定" cancelText="取消" okButtonProps={{ danger: true }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', width: 22, height: 22, borderRadius: 4, background: isActive ? 'rgba(255,255,255,0.15)' : '#fff', cursor: 'pointer' }} onClick={(e) => e.stopPropagation()}><DeleteOutlined style={{ fontSize: 11, color: isActive ? '#fff' : '#ff4d4f' }} /></div>
                  </Popconfirm>
                </div>
              </div>
              {s.description && <div style={{ fontSize: isMobile ? 10 : 11, color: isActive ? 'rgba(255,255,255,0.8)' : '#8c8c8c', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', marginTop: 4 }}>{s.description}</div>}
            </div>
          );
        })}
        <div onClick={() => { setEditingStrategy(null); strategyForm.resetFields(); setEnableSkill(true); setShowStrategyModal(true); }} style={{ position: 'relative', padding: isMobile ? '10px 12px' : '12px 14px', borderRadius: 8, border: '2px dashed #d9d9d9', background: '#fafafa', cursor: 'pointer', minHeight: isMobile ? 60 : 68, display: 'flex', alignItems: 'center', justifyContent: 'center', minWidth: isMobile ? 'calc(50% - 4px)' : 'auto', flexShrink: isMobile ? 0 : 1, width: isMobile ? 'calc(50% - 4px)' : 'auto' }}>
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 }}><PlusOutlined style={{ fontSize: isMobile ? 18 : 20, color: '#8c8c8c' }} /><div style={{ fontSize: isMobile ? 11 : 12, color: '#8c8c8c', fontWeight: 500 }}>新增策略</div></div>
        </div>
      </div>
    </Spin>
  );

  return (
    <>
      <Modal
        title={<div style={{ display: 'flex', alignItems: 'center', gap: 6 }}><AimOutlined style={{ fontSize: isMobile ? 16 : 18, color: '#52c41a' }} /><span style={{ fontSize: isMobile ? 14 : 16 }}>找对标股票</span></div>}
        open={visible}
        onCancel={onClose}
        width={isMobile ? '95%' : 1100}
        footer={null}
        style={{ top: isMobile ? 20 : 10 }}
        styles={{ body: { padding: isMobile ? '8px' : '8px 12px', maxHeight: isMobile ? '75vh' : '75vh', overflow: 'auto' } }}
      >
        {(context && (context.stockName || context.stockCode)) && (
          <Alert type="info" showIcon icon={<AimOutlined />} message={<Space size="small"><span style={{ fontWeight: 600 }}>对标目标：</span><span>{context.stockName}</span><Tag color="blue">{context.stockCode}</Tag>{context.blockName && <Tag color="green">{context.blockName}</Tag>}</Space>} style={{ marginBottom: 12 }} />
        )}

        <div style={{ marginBottom: 8 }}>
          <div style={{ fontSize: isMobile ? 12 : 13, fontWeight: 600, color: '#262626', display: 'flex', alignItems: 'center', gap: 6, marginBottom: 8 }}>
            <span style={{ display: 'inline-block', width: 3, height: 14, background: 'linear-gradient(180deg, #52c41a 0%, #389e0d 100%)', borderRadius: 2 }}></span>选择策略
          </div>
          {renderStrategyCards()}
        </div>

        <div style={{ position: 'relative', marginBottom: 8 }}>
          <div style={{ position: 'absolute', top: -8, left: 12, background: '#fff', padding: '0 4px', fontSize: isMobile ? 11 : 12, color: '#8c8c8c', zIndex: 1 }}>查询需求</div>
          <TextArea rows={4} value={query} onChange={(e) => { setQuery(e.target.value); setResult(null); }} placeholder="输入你对标股票的查询需求...&#10;例如：帮我在2026年6月26日找出对标兴业股份相关题材的涨停股票" style={{ fontFamily: 'Consolas, Monaco, "Courier New", monospace', fontSize: isMobile ? 12 : 13, borderRadius: 8, minHeight: '100px', border: '1px solid #e8e8e8', backgroundColor: '#fafafa', padding: isMobile ? '10px 12px' : '12px 14px' }} />
        </div>

        <div style={{ marginBottom: 12, display: 'flex', alignItems: 'center', gap: 12 }}>
          <Button type="primary" icon={<RobotOutlined />} onClick={handleAnalyze} loading={loading} size={isMobile ? 'small' : 'middle'} style={{ background: 'linear-gradient(135deg, #722ed1 0%, #531dab 100%)', border: 'none' }}>开始分析</Button>
          <div style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 12, color: '#8c8c8c' }}><Switch size="small" checked={enableSkill} onChange={setEnableSkill} /><span>A股全栈数据技能</span></div>
        </div>

        <Spin spinning={loading}>
          {result ? (
            <div>
              {result.dates_queried && <div style={{ marginBottom: 8, fontSize: 12, color: '#8c8c8c' }}>查询日期：{result.dates_queried.join(', ')} | 热点数据：{result.hot_data_count} 条</div>}

              {result.analysis && (
                <div style={{ marginBottom: 12 }}>
                  <Button type="text" size="small" icon={showAnalysis ? <UpOutlined /> : <DownOutlined />} onClick={() => setShowAnalysis(!showAnalysis)} style={{ fontSize: 12, color: '#1890ff', padding: '0 4px', marginBottom: 4 }}>{showAnalysis ? '收起分析' : '展开分析'}</Button>
                  {showAnalysis && (
                    <div style={{ background: '#fafafa', border: '1px solid #f0f0f0', borderRadius: 8, padding: isMobile ? 10 : 16, marginBottom: 8 }}>
                      <style>{`.markdown-body table{width:100%;border-collapse:collapse;margin:8px 0;font-size:12px}.markdown-body th{background:#f0f5ff;padding:6px 10px;text-align:left;border:1px solid #d9e1f2;font-weight:600}.markdown-body td{padding:5px 10px;border:1px solid #e8e8e8}.markdown-body h2{font-size:15px;margin:14px 0 6px;color:#262626}.markdown-body h3{font-size:13px;margin:10px 0 4px;color:#434343}.markdown-body p{margin:4px 0;line-height:1.6;font-size:13px}.markdown-body ul,.markdown-body ol{margin:4px 0;padding-left:20px}.markdown-body li{font-size:13px;line-height:1.6}.markdown-body code{background:#f5f5f5;padding:1px 4px;border-radius:3px;font-size:12px}.markdown-body pre{background:#f5f5f5;padding:10px;border-radius:6px;overflow-x:auto}.markdown-body hr{border:none;border-top:1px solid #f0f0f0;margin:12px 0}`}</style>
                      <div className="markdown-body"><ReactMarkdown>{result.analysis || ''}</ReactMarkdown></div>
                    </div>
                  )}
                </div>
              )}

              {result.stocks && result.stocks.length > 0 && (
                <div>
                  <Divider style={{ margin: '8px 0', fontSize: 12, fontWeight: 600, color: '#1890ff' }}>对标股票列表 ({result.stocks.length})</Divider>
                  <Table columns={stockColumns} dataSource={sortByCategory(result.stocks).map((s, i) => ({ ...s, _key: s.code + i }))} rowKey="_key" size="small" pagination={{ pageSize: 20, showSizeChanger: true, showTotal: (t) => `共 ${t} 条`, size: 'small' }} scroll={{ y: 400 }} getPopupContainer={() => document.body} />
                </div>
              )}

              {(!result.stocks || result.stocks.length === 0) && !result.analysis && <div style={{ textAlign: 'center', padding: '20px', color: '#999' }}>未找到对标股票数据</div>}
            </div>
          ) : (!loading && <div style={{ textAlign: 'center', padding: '40px 20px', color: '#999', fontSize: 14 }}>输入查询需求后点击"开始分析"按钮</div>)}
        </Spin>
      </Modal>

      <StockKlineModal visible={klineVisible} stockCode={selectedStock?.code} stockName={selectedStock?.name} targetDate={dateStr} onClose={() => { setKlineVisible(false); setSelectedStock(null); }} />

      <Modal title={editingStrategy ? '编辑策略' : '创建新策略'} open={showStrategyModal} onCancel={() => { setShowStrategyModal(false); strategyForm.resetFields(); setEditingStrategy(null); }} onOk={() => strategyForm.submit()} okText="保存" cancelText="取消" width={isMobile ? '95%' : 600}>
        <Form form={strategyForm} layout="vertical" onFinish={handleSaveStrategy}>
          <Form.Item name="strategy_name" label="策略名称" rules={[{ required: true, message: '请输入策略名称' }]}><Input placeholder="例如：同板块小市值对标" maxLength={100} /></Form.Item>
          <Form.Item name="query_template" label={<div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: '100%' }}><span>查询模板</span><div style={{ display: 'flex', alignItems: 'center', gap: 4 }}><Switch size="small" checked={enableSkill} onChange={setEnableSkill} /><span style={{ fontSize: 11, color: '#8c8c8c', fontWeight: 400 }}>A股全栈数据技能</span></div></div>} rules={[{ required: true, message: '请输入查询模板' }]} extra="支持变量：{date} {code} {name} {block}"><TextArea rows={4} placeholder="例如：找出对标{name}涨停股票，所属板块包含{block}" /></Form.Item>
          <Form.Item name="description" label="策略描述"><Input placeholder="策略说明（可选）" maxLength={500} /></Form.Item>
          <Form.Item name="is_default" label="设为默认" valuePropName="checked"><input type="checkbox" style={{ width: 16, height: 16 }} /></Form.Item>
        </Form>
      </Modal>
    </>
  );
};

export default ComparableStockModal;
