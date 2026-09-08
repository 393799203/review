import React, { useState, useEffect, useMemo } from 'react';
import { Card, Table, Radio, Tag, Spin, message, Empty, Row, Col, Space, Typography, Alert, Tooltip, Button, Checkbox, Statistic, Select, InputNumber, Divider } from 'antd';
import { LineChartOutlined, TableOutlined, LoadingOutlined, QuestionCircleOutlined, ReloadOutlined, FundOutlined } from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';
import api, { stockApi } from '../services/api';

const { Title, Text } = Typography;

const fmt = (v, nd = 4) => (v === null || v === undefined || Number.isNaN(v) ? '-' : Number(v).toFixed(nd));
const pct = (v, nd = 1) => (v === null || v === undefined || Number.isNaN(v) ? '-' : `${(v * 100).toFixed(nd)}%`);
const pct3 = (v) => (v === null || v === undefined || Number.isNaN(v) ? '-' : `${(v * 100).toFixed(3)}%`);

// A股配色：正=红，负=绿
const icColor = (v) => {
  if (v === null || v === undefined || Number.isNaN(v)) return 'rgba(0,0,0,0.45)';
  if (v > 0) return '#cf1322';
  if (v < 0) return '#389e0d';
  return 'rgba(0,0,0,0.65)';
};

const CATEGORY_COLOR = {
  趋势: 'blue',
  摆动: 'purple',
  波动: 'orange',
  量价: 'red',
};

// 样本中文名兜底（后端 meta.universe_labels 优先）
const UNIVERSE_SHORT = {
  all: '全市场',
  ashare: '沪深A股',
  main: '沪深主板',
  gem: '创业科创',
  hs300: '沪深300',
};

// 表头说明（悬停 ? 图标查看）
const HEADER_TIPS = {
  factor: '因子名，对应 tdx.raw_stock_indicators 数据表列；悬停因子名可查看完整说明',
  category: '因子类别：趋势 / 摆动 / 波动 / 量价关系',
  n_dates: '有效评估交易日数（当日截面样本不足时跳过）',
  mean_ic: '全时段截面 Spearman 秩 IC 均值。|IC| 越大预测力越强；正负号表示因子方向（正=高值组未来收益更高）',
  ic_std: 'IC 的标准差，衡量 IC 在时间上的稳定性，越小越稳定',
  icir: 'ICIR = mean_ic / ic_std。经验上 |ICIR| > 0.3 为较优因子',
  t_stat: 't 值 = ICIR × √n。|t| > 2 表示 IC 显著不为 0',
  ic_pos_pct: 'IC 为正的交易日占比。越偏离 50% 说明方向越稳定',
  q: '按因子值等频分为 5 组（Q1=因子值最小），各组在未来 H 日的平均超额收益（后复权；已按每日截面去均值消除市场行情影响，并按 1%/99% 缩尾抑制极端妖股）。显示为 3 位小数，0.000% 表示该组与当日市场平均水平持平',
  spread: 'Q1 组超额收益 − Q5 组超额收益。>0 表示低因子值组占优（负向因子），<0 表示高因子值组占优（正向因子）',
  mono: '组序与组均收益的 Spearman 相关，|mono| 越接近 1 分层越单调（线性关系越强）',
  delta: '风格贡献 ΔICIR = 原始ICIR − 中性化ICIR。|Δ| 越大说明该因子效果越多来自行业/市值风格（中性化后可能反转，需警惕）；|Δ| 小说明是"纯"因子',
};

const tipTitle = (text, tip) => (
  <Tooltip title={tip}>
    <span>
      {text} <QuestionCircleOutlined style={{ fontSize: 11, color: '#999' }} />
    </span>
  </Tooltip>
);

// 推荐规则：当前视图（样本×口径×H）|ICIR| ≥ 0.5 自动标「荐」（动态判定，统一规则）
const RECOMMENDED_THRESHOLD = 0.5;
const isRecommended = (r) => r && r.icir !== null && r.icir !== undefined && Math.abs(r.icir) >= RECOMMENDED_THRESHOLD;

// 组合回测可选因子（技术 14 + 基本面 12）
const BACKTEST_FACTOR_OPTIONS = [
  { value: 'vol_cv20', label: 'vol_cv20 量能变异系数(低波)', category: '技术' },
  { value: 'corr_pv20', label: 'corr_pv20 量价相关性', category: '技术' },
  { value: 'vol_pos20', label: 'vol_pos20 量能位置', category: '技术' },
  { value: 'vr20', label: 'vr20 量比(20日)', category: '技术' },
  { value: 'vr10', label: 'vr10 量比(10日)', category: '技术' },
  { value: 'vol_trend', label: 'vol_trend 量能趋势', category: '技术' },
  { value: 'vpt', label: 'vpt 量价趋势', category: '技术' },
  { value: 'cmf20', label: 'cmf20 蔡金资金流', category: '技术' },
  { value: 'mfi14', label: 'mfi14 资金流量', category: '技术' },
  { value: 'mom60', label: 'mom60 长期动量(反向)', category: '技术' },
  { value: 'mom20', label: 'mom20 动量', category: '技术' },
  { value: 'dif', label: 'dif MACD快线', category: '技术' },
  { value: 'dea', label: 'dea MACD信号线', category: '技术' },
  { value: 'rsi24', label: 'rsi24 RSI', category: '技术' },
  { value: 'pe', label: 'pe 市盈率', category: '基本面' },
  { value: 'pb', label: 'pb 市净率', category: '基本面' },
  { value: 'ps', label: 'ps 市销率', category: '基本面' },
  { value: 'pcf', label: 'pcf 市现率', category: '基本面' },
  { value: 'roe', label: 'roe 净资产收益率', category: '基本面' },
  { value: 'roa', label: 'roa 总资产收益率', category: '基本面' },
  { value: 'net_margin', label: 'net_margin 净利率', category: '基本面' },
  { value: 'op_margin', label: 'op_margin 主营利润率', category: '基本面' },
  { value: 'debt_ratio', label: 'debt_ratio 资产负债率', category: '基本面' },
  { value: 'cf_quality', label: 'cf_quality 盈利含金量', category: '基本面' },
  { value: 'ar_ratio', label: 'ar_ratio 应收占比', category: '基本面' },
  { value: 'inv_ratio', label: 'inv_ratio 存货占比', category: '基本面' },
];
const DEFAULT_BT_FACTORS = ['vol_cv20', 'corr_pv20']; // 默认 = 推荐因子（|ICIR|≥0.5）

// 错误边界：任一子组件渲染出错时显示红条（避免整页白屏）
class BtErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }
  static getDerivedStateFromError(error) {
    return { error };
  }
  render() {
    if (this.state.error) {
      return (
        <Alert
          type="error"
          showIcon
          message="渲染出错（非接口问题）"
          description={String(this.state.error && this.state.error.message || this.state.error)}
          style={{ marginTop: 12 }}
        />
      );
    }
    return this.props.children;
  }
}

const FactorResearchPage = () => {
  const [universes, setUniverses] = useState(['all']);
  const [universe, setUniverse] = useState('all');
  const [methods, setMethods] = useState(['neutral']);
  const [method, setMethod] = useState('neutral');
  const [horizons, setHorizons] = useState([5]);
  const [horizon, setHorizon] = useState(5);
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [metaInfo, setMetaInfo] = useState(null);
  const [selected, setSelected] = useState(null); // {factor, row}
  const [series, setSeries] = useState([]);
  const [seriesLoading, setSeriesLoading] = useState(false);
  const [showRecommended, setShowRecommended] = useState(true); // 默认只看核心

  // 后端返回的样本中文名（如不存在则用兜底）
  const universeLabels = useMemo(() => {
    const labels = (metaInfo && metaInfo.universe_labels) || {};
    return (u) => labels[u] || UNIVERSE_SHORT[u] || u;
  }, [metaInfo]);

  // 某样本可用的口径与持有期
  const availableOf = (u) => {
    const perUniverse = (metaInfo?.horizons || {})[u] || {}; // {method: [horizon...]}
    const ms = Object.keys(perUniverse);
    return {
      methods: ms.length > 0 ? ms : ['neutral'],
      horizons: (perUniverse[method] || ms.length > 0 ? perUniverse[ms[0]] : []) || [5],
    };
  };

  useEffect(() => {
    (async () => {
      try {
        const res = await api.get('/factor-research/meta');
        if (res.data.success) {
          const meta = res.data.data || {};
          setMetaInfo(meta);
          // 界面只提供个股样本：沪深A股/沪深主板/创业科创/沪深300（「全市场」含指数/基金等噪音样本，隐藏保留）
          const usAll = Array.isArray(meta.universes) && meta.universes.length > 0 ? meta.universes : ['all'];
          const us = usAll.filter((u) => u !== 'all');
          setUniverses(us);
          // 默认样本优先沪深A股（干净的个股样本；全市场含指数/北交所/基金，仅作对照）
          const defaultU = us.includes('ashare') ? 'ashare' : us[0];
          setUniverse(defaultU);
          const perU = (meta.horizons || {})[defaultU] || {};
          const ms = Object.keys(perU);
          const defaultM = ms.includes('neutral') ? 'neutral' : ms[0] || 'neutral';
          setMethods(ms.length > 0 ? ms : ['neutral']);
          setMethod(defaultM);
          const hs = (perU[defaultM] || (ms.length > 0 ? perU[ms[0]] : [])) || [5];
          setHorizons(hs);
          setHorizon(hs.includes(5) ? 5 : hs[0]);
        }
      } catch (e) {
        message.error('因子研究元信息加载失败：' + (e.response?.data?.error || e.message));
      }
    })();
  }, []);

  const loadSummary = async (h, u, m) => {
    setLoading(true);
    try {
      const res = await api.get('/factor-research/summary', { params: { horizon: h, universe: u, method: m } });
      if (res.data.success) {
        const factors = (res.data.data?.factors || []).map((r) => ({
          ...r,
          spread:
            r.q_means && r.q_means.length >= 2 && r.q_means[0] !== null && r.q_means[r.q_means.length - 1] !== null
              ? r.q_means[0] - r.q_means[r.q_means.length - 1]
              : null,
        }));
        setRows(factors);
        setSelected(null);
        setSeries([]);
      } else {
        message.error(res.data.error || '加载失败');
      }
    } catch (e) {
      message.error('因子汇总加载失败：' + (e.response?.data?.error || e.message));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSummary(horizon, universe, method);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [horizon, universe, method]);

  // 切换样本：取该样本已有的口径与持有期
  const onUniverseChange = (u) => {
    setUniverse(u);
    const perU = (metaInfo?.horizons || {})[u] || {};
    const ms = Object.keys(perU);
    const m = ms.includes(method) ? method : ms.includes('neutral') ? 'neutral' : ms[0];
    if (ms.length > 0) {
      setMethods(ms);
      setMethod(m);
      const hs = perU[m] || [];
      if (hs.length > 0) {
        setHorizons(hs);
        setHorizon((prev) => (hs.includes(prev) ? prev : hs[0]));
      }
    }
  };

  const loadIcSeries = async (factor, u, m) => {
    setSeriesLoading(true);
    try {
      const res = await api.get('/factor-research/ic-series', { params: { factor, horizon, universe: u, method: m } });
      if (res.data.success) {
        setSeries(res.data.data?.series || []);
      } else {
        message.error(res.data.error || 'IC 序列加载失败');
        setSeries([]);
      }
    } catch (e) {
      message.error('IC 序列加载失败：' + (e.response?.data?.error || e.message));
      setSeries([]);
    } finally {
      setSeriesLoading(false);
    }
  };

  const onRowClick = (record) => {
    setSelected({ factor: record.factor, row: record });
    loadIcSeries(record.factor, universe, method);
  };

  const displayRows = showRecommended ? rows.filter(isRecommended) : rows;

  const columns = useMemo(() => {
    const qCols = (rows[0]?.q_means || []).map((_, idx) => ({
      title: tipTitle(`Q${idx + 1}`, HEADER_TIPS.q),
      key: `q${idx}`,
      width: 74,
      align: 'right',
      render: (_, r) => {
        const v = r.q_means?.[idx];
        return <span style={{ color: icColor(v) }}>{pct3(v)}</span>;
      },
    }));
    return [
      {
        title: tipTitle('因子/类别', HEADER_TIPS.factor), dataIndex: 'factor', key: 'factor',
        width: 170,
        render: (v, r) => (
          <Space size={4}>
            <Tooltip title={r.desc ? `${v}：${r.desc}` : v}>
              <Text strong style={{ fontFamily: 'monospace', cursor: 'help' }}>{v}</Text>
            </Tooltip>
            {r.category && (
              <Tag color={CATEGORY_COLOR[r.category] || 'default'} style={{ marginInlineEnd: 0, fontSize: 10 }}>{r.category}</Tag>
            )}
            {isRecommended(r) && (
              <Tooltip title={`推荐：当前视图 |ICIR| = ${Math.abs(r.icir).toFixed(3)} ≥ 0.5`}>
                <Tag color="gold" style={{ marginInlineEnd: 0, fontSize: 10 }}>荐</Tag>
              </Tooltip>
            )}
          </Space>
        ),
      },
      { title: tipTitle('交易日数', HEADER_TIPS.n_dates), dataIndex: 'n_dates', key: 'n_dates', width: 68, align: 'right',
        render: (v, r) => (v !== null && v !== undefined && v < 20
          ? <Tooltip title={`样本仅 ${v} 个交易日，IC/分位统计意义不足，仅供参考`}>
              <span style={{ color: '#d46b08', fontWeight: 600 }}>{v} ⚠</span>
            </Tooltip>
          : v) },
      {
        title: tipTitle('Mean IC', HEADER_TIPS.mean_ic), dataIndex: 'mean_ic', key: 'mean_ic', width: 76, align: 'right',
        render: (v) => <span style={{ color: icColor(v) }}>{fmt(v)}</span>,
      },
      { title: tipTitle('ICstd', HEADER_TIPS.ic_std), dataIndex: 'ic_std', key: 'ic_std', width: 72, align: 'right', render: (v) => fmt(v) },
      {
        title: tipTitle('ICIR', HEADER_TIPS.icir), dataIndex: 'icir', key: 'icir', width: 70, align: 'right',
        render: (v) => <Text strong style={{ color: icColor(v) }}>{fmt(v, 3)}</Text>,
      },
      ...(method === 'neutral'
        ? [{
            title: tipTitle('风格贡献Δ', HEADER_TIPS.delta), dataIndex: 'delta', key: 'delta', width: 80, align: 'right',
            render: (_, r) => {
              if (r.raw_icir === null || r.raw_icir === undefined || r.icir === null || r.icir === undefined) return '-';
              const d = r.raw_icir - r.icir;
              const big = Math.abs(d) >= 0.15;
              return (
                <Tooltip title={`原始ICIR=${r.raw_icir.toFixed(3)} → 中性化=${r.icir.toFixed(3)}${big ? '；风格贡献大，中性化后结论可能反转' : ''}`}>
                  <span style={{ color: big ? '#d46b08' : 'rgba(0,0,0,0.65)', fontWeight: big ? 600 : 400 }}>
                    {fmt(d, 3)}
                    {big && ' ⚠'}
                  </span>
                </Tooltip>
              );
            },
          }]
        : []),
      {
        title: tipTitle('t 值', HEADER_TIPS.t_stat), dataIndex: 't_stat', key: 't_stat', width: 64, align: 'right',
        render: (v) => <span style={{ color: icColor(v) }}>{fmt(v, 2)}</span>,
      },
      {
        title: tipTitle('IC>0%', HEADER_TIPS.ic_pos_pct), dataIndex: 'ic_pos_pct', key: 'ic_pos_pct', width: 66, align: 'right',
        render: (v) => pct(v, 0),
      },
      ...qCols,
      {
        title: tipTitle('Q1-Q5价差', HEADER_TIPS.spread), dataIndex: 'spread', key: 'spread', width: 78, align: 'right',
        render: (v) => <span style={{ color: icColor(v) }}>{pct(v, 2)}</span>,
      },
      {
        title: tipTitle('单调性', HEADER_TIPS.mono), dataIndex: 'mono', key: 'mono', width: 68, align: 'right',
        render: (v) => (v === null || v === undefined ? '-' : <Tag color={v >= 0.6 ? 'red' : v <= -0.6 ? 'green' : 'default'} style={{ marginInlineEnd: 0 }}>{fmt(v, 2)}</Tag>),
      },
    ];
  }, [rows, method]);

  const icSeriesOption = useMemo(() => {
    if (!series.length) return null;
    const dates = series.map((s) => s.date);
    const values = series.map((s) => s.ic);
    return {
      grid: { left: 60, right: 24, top: 40, bottom: 40 },
      tooltip: { trigger: 'axis' },
      title: {
        text: `${selected?.factor || ''} 逐日 IC（${universeLabels(universe)} / ${method === 'neutral' ? '中性化' : '原始'} / H=${horizon}）`,
        left: 'center',
        textStyle: { fontSize: 14 },
      },
      xAxis: { type: 'category', data: dates, axisLabel: { rotate: 45, fontSize: 10 } },
      yAxis: { type: 'value', name: 'IC', scale: true },
      series: [
        {
          type: 'line',
          data: values,
          showSymbol: false,
          lineStyle: { width: 1.5, color: '#cf1322' },
          areaStyle: { opacity: 0.08 },
        },
        { type: 'line', data: [], markLine: { silent: true, symbol: 'none', data: [{ yAxis: 0 }], lineStyle: { color: '#999', type: 'dashed' } } },
      ],
    };
  }, [series, selected, horizon, universeLabels, universe]);

  const quantileOption = useMemo(() => {
    const q = selected?.row?.q_means;
    if (!q || !q.length) return null;
    const groups = q.map((_, i) => `Q${i + 1}`);
    return {
      grid: { left: 60, right: 24, top: 40, bottom: 40 },
      tooltip: { trigger: 'axis' },
      title: {
        text: `${selected?.factor || ''} 分位组超额收益（${universeLabels(universe)} / ${method === 'neutral' ? '中性化' : '原始'} / H=${horizon}）`,
        left: 'center',
        textStyle: { fontSize: 14 },
      },
      xAxis: { type: 'category', data: groups },
      yAxis: { type: 'value', name: '超额收益', axisLabel: { formatter: (v) => `${(v * 100).toFixed(1)}%` } },
      series: [
        {
          type: 'bar',
          data: q.map((v) => (v === null ? null : Number((v * 100).toFixed(3)))),
          itemStyle: {
            color: (p) => (p.data === null ? '#ccc' : p.data >= 0 ? '#cf1322' : '#389e0d'),
          },
          label: { show: true, position: 'top', formatter: (p) => (p.data === null ? '-' : `${p.data.toFixed(2)}%`) },
        },
      ],
    };
  }, [selected, horizon, universeLabels, universe]);

  const latestInfo = useMemo(() => {
    const item = (metaInfo?.latest || []).find(
      (l) => l.universe === universe && l.horizon === horizon && l.method === method
    );
    return item ? `评估截至 ${item.max_date}，更新于 ${(item.computed_at || '').replace('T', ' ').slice(0, 16)}` : '该样本/口径/持有期尚未评估';
  }, [metaInfo, universe, horizon, method]);

  // ===== 组合回测 =====
  const [btFactors, setBtFactors] = useState(DEFAULT_BT_FACTORS);
  const [btUniverse, setBtUniverse] = useState('ashare');
  const [btTopPct, setBtTopPct] = useState(0.2);
  const [btTopK, setBtTopK] = useState(0);
  const [btRebalance, setBtRebalance] = useState(5);
  const [btCost, setBtCost] = useState(0);
  const [btStopMode, setBtStopMode] = useState('trail');
  const [btStopPct, setBtStopPct] = useState(0.15);
  const [btTrailPct, setBtTrailPct] = useState(0.10);
  const [btAtrMult, setBtAtrMult] = useState(2.0);
  const [btMaExit, setBtMaExit] = useState(10);
  const [btLoading, setBtLoading] = useState(false);
  const [btResult, setBtResult] = useState(null);

  const runBacktest = async () => {
    if (!btFactors || btFactors.length === 0) {
      message.warning('请至少选择一个因子');
      return;
    }
    setBtLoading(true);
    try {
      const res = await stockApi.runBacktest({
        factors: btFactors,
        universe: btUniverse,
        top_pct: btTopPct,
        top_k: btTopK || 0,
        rebalance: 1,
        cost: btCost,
        stop_mode: btStopMode,
        stop_pct: btStopPct,
        trail_pct: btTrailPct,
        atr_mult: btAtrMult,
        ma_exit: btMaExit,
      });
      if (res.data.success) {
        setBtResult(res.data.data);
      } else {
        message.error(res.data.error || '回测失败');
      }
    } catch (e) {
      message.error('回测失败：' + (e.response?.data?.error || e.message));
    } finally {
      setBtLoading(false);
    }
  };

  const navOption = useMemo(() => {
    if (!btResult || !btResult.nav || btResult.nav.length === 0) return null;
    const dates = btResult.nav.map((x) => x.date);
    const strategy = btResult.nav.map((x) => x.nav);
    const bench = (btResult.bench_nav || []).map((x) => x.nav);
    return {
      grid: { left: 60, right: 20, top: 40, bottom: 45 },
      tooltip: { trigger: 'axis' },
      legend: { data: ['策略净值', '沪深300'], top: 4 },
      title: { text: `组合净值（${btResult.params.factors.length} 因子 | ${btResult.params.universe} | 前${btResult.params.top_k ? btResult.params.top_k : (btResult.params.top_pct * 100).toFixed(0)}% | 每日轮动）`, left: 'center', top: 26, textStyle: { fontSize: 13 } },
      xAxis: { type: 'category', data: dates, axisLabel: { rotate: 45, fontSize: 10 } },
      yAxis: { type: 'value', name: '净值', scale: true },
      series: [
        { name: '策略净值', type: 'line', data: strategy, showSymbol: false, lineStyle: { width: 2, color: '#cf1322' } },
        bench.length > 0 && { name: '沪深300', type: 'line', data: bench, showSymbol: false, lineStyle: { width: 1.5, color: '#389e0d' } },
      ].filter(Boolean),
    };
  }, [btResult]);

  const holdingsCols = [
    { title: '代码', dataIndex: 'code', key: 'code', width: 76 },
    { title: '名称', dataIndex: 'name', key: 'name', width: 120 },
    { title: '组合分', dataIndex: 'score', key: 'score', width: 76, align: 'right', render: (v) => fmt(v, 3) },
    { title: '入场日', dataIndex: 'entry_date', key: 'entry_date', width: 100, align: 'center', render: (v) => (v ? String(v).slice(5) : '-') },
    { title: '入场价', dataIndex: 'entry_open', key: 'entry_open', width: 80, align: 'right', render: (v) => (v === null || v === undefined ? '-' : v) },
    { title: '出场日', dataIndex: 'exit_date', key: 'exit_date', width: 100, align: 'center', render: (v) => (v ? String(v).slice(5) : '持有中') },
    { title: '最新收盘', dataIndex: 'exit_close', key: 'exit_close', width: 90, align: 'right', render: (v) => (v === null || v === undefined ? '-' : v) },
  ];

    const tradesCols = [
    { title: '日期', dataIndex: 'date', key: 'date', width: 100, align: 'center', render: (v) => (v ? String(v).slice(5) : '-') },
    { title: '代码', dataIndex: 'code', key: 'code', width: 76 },
    { title: '名称', dataIndex: 'name', key: 'name', width: 120 },
    { title: '方向', dataIndex: 'dir', key: 'dir', width: 60, align: 'center',
      render: (v) => (v === 'buy' ? <Tag color="red" style={{ marginInlineEnd: 0 }}>买</Tag> : <Tag color="green" style={{ marginInlineEnd: 0 }}>卖</Tag>) },
    { title: '价格', dataIndex: 'price', key: 'price', width: 80, align: 'right', render: (v) => (v === null || v === undefined ? '-' : v) },
    { title: '原因', dataIndex: 'reason', key: 'reason', width: 90, align: 'center' },
    { title: '单笔盈亏', dataIndex: 'pnl', key: 'pnl', width: 90, align: 'right',
      render: (v) => (v === null || v === undefined ? '-' : <span style={{ color: v >= 0 ? '#cf1322' : '#389e0d' }}>{v > 0 ? '+' : ''}{v}%</span>) },
  ];

  const btMetrics = btResult?.metrics || {};
  const metricVal = (v, digits = 2) => (v === null || v === undefined ? '-' : (v * 100).toFixed(digits));

  return (
    <BtErrorBoundary>
    <div style={{ padding: 16 }}>
      <Row gutter={[16, 16]}>
        <Col span={24}>
          <Card
            size="small"
            title={
              <Space>
                <LineChartOutlined />
                <span>因子研究 · IC/IR 评估</span>
              </Space>
            }
            extra={
              <Space wrap>
                <Text type="secondary" style={{ fontSize: 12 }}>{latestInfo}</Text>
                <Radio.Group
                  value={universe}
                  onChange={(e) => onUniverseChange(e.target.value)}
                  optionType="button"
                  buttonStyle="solid"
                  options={universes.map((u) => ({
                    label: (
                      <Tooltip title={universeLabels(u)}>
                        <span>{UNIVERSE_SHORT[u] || u}</span>
                      </Tooltip>
                    ),
                    value: u,
                  }))}
                />
                <Radio.Group
                  value={method}
                  onChange={(e) => setMethod(e.target.value)}
                  optionType="button"
                  buttonStyle="solid"
                  options={methods.map((m) => ({ label: m === 'neutral' ? '中性化IC' : '原始IC', value: m }))}
                />
                <Radio.Group
                  value={horizon}
                  onChange={(e) => setHorizon(e.target.value)}
                  optionType="button"
                  buttonStyle="solid"
                  options={horizons.map((h) => ({ label: `H=${h}`, value: h }))}
                />
                <Checkbox checked={showRecommended} onChange={(e) => setShowRecommended(e.target.checked)}>
                  只看推荐(|ICIR|≥0.5)
                </Checkbox>
              </Space>
            }
          >
            <Alert
              type="info"
              showIcon
              style={{ marginBottom: 12 }}
              message="悬停表头「?」查看指标说明，悬停因子名查看该因子解释。口径：中性化IC = 因子值减申万一级行业均值后再对 ln 市值回归取残差（剥离行业与小市值风格）；原始IC = 未中性化。H = 未来 N 个交易日收益（v_hfq_daily 后复权）；Q1~Q5 为相对市场超额收益（日度截面去均值 + 1%/99% 缩尾，3 位小数）。入场价按 T 日收盘近似，实盘需 T+1 执行。"
            />
            <Table
              rowKey="factor"
              size="small"
              loading={loading}
              columns={columns}
              dataSource={displayRows}
              pagination={{ pageSize: 20, showSizeChanger: false }}
              scroll={{ x: 'max-content' }}
              locale={{
                emptyText: (
                  <Empty
                    description={`「${universeLabels(universe)} / ${method === 'neutral' ? '中性化' : '原始'} / H=${horizon}」暂无评估数据`}
                    image={Empty.PRESENTED_IMAGE_SIMPLE}
                  >
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      运行评估命令生成：eval_factor_standalone.py --save --horizon {horizon} --universe {universe} --limit-dates 120
                    </Text>
                  </Empty>
                ),
              }}
              rowClassName={(r) => (selected?.factor === r.factor ? 'ant-table-row-selected' : '')}
              onRow={(record) => ({
                onClick: () => onRowClick(record),
                style: { cursor: 'pointer' },
              })}
            />
          </Card>
        </Col>

        {selected && (
          <>
            <Col xs={24} lg={14}>
              <Card size="small" title={<Space><LineChartOutlined />IC 时间序列</Space>} loading={seriesLoading}>
                {icSeriesOption ? (
                  <ReactECharts option={icSeriesOption} style={{ height: 300 }} notMerge />
                ) : (
                  <Empty description="暂无 IC 序列数据" />
                )}
              </Card>
            </Col>
            <Col xs={24} lg={10}>
              <Card size="small" title={<Space><TableOutlined />分位组超额收益</Space>}>
                {quantileOption ? (
                  <ReactECharts option={quantileOption} style={{ height: 300 }} notMerge />
                ) : (
                  <Empty description="暂无分位数据" />
                )}
              </Card>
            </Col>
          </>
        )}
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col span={24}>
          <Card
            size="small"
            title={<Space><FundOutlined />组合回测（每日轮动：因子打分自动选股，掉出前 N% 自动卖出、新进自动买入）</Space>}
          >
            <Space wrap style={{ marginBottom: 12 }}>
              <Select
                mode="multiple"
                style={{ width: 560 }}
                value={btFactors}
                onChange={setBtFactors}
                placeholder="选择因子（默认推荐 2 个：vol_cv20、corr_pv20）"
                showSearch
                optionFilterProp="label"
                options={BACKTEST_FACTOR_OPTIONS}
                maxTagCount={20}
              />
              <Select
                value={btUniverse}
                onChange={setBtUniverse}
                style={{ width: 110 }}
                options={[
                  { value: 'ashare', label: '沪深A股' },
                  { value: 'main', label: '沪深主板' },
                  { value: 'gem', label: '创业科创' },
                  { value: 'hs300', label: '沪深300' },
                ]}
              />
              <InputNumber value={btTopPct} onChange={setBtTopPct} min={0.05} max={1} step={0.05} style={{ width: 90 }} addonBefore="前" addonAfter="比例" />
              <Tooltip title="交易费用比例（佣金+印花税+滑点）。单边=买卖各扣一次，如 0.1% 表示买扣0.1%、卖再扣0.1%；A股实际约 0.1%~0.15%；默认 0 为理想状态">
                <InputNumber value={btCost} onChange={setBtCost} min={0} max={0.01} step={0.0005} style={{ width: 130 }} addonBefore="成本" addonAfter="单边" />
              </Tooltip>
              <Select
                value={btStopMode}
                onChange={setBtStopMode}
                style={{ width: 130 }}
                options={[
                  { value: 'off', label: '不止损' },
                  { value: 'trail', label: '移动止盈' },
                  { value: 'fixed', label: '固定止损' },
                  { value: 'atr', label: 'ATR止损' },
                ]}
              />
              {btStopMode === 'trail' && (
                <Tooltip title="移动止盈：从持仓期最高收盘回撤 X% 卖出（默认10%，让利润奔跑）">
                  <InputNumber value={btTrailPct} onChange={setBtTrailPct} min={0.02} max={0.3} step={0.01} style={{ width: 100 }} addonBefore="回撤" addonAfter="%" />
                </Tooltip>
              )}
              {btStopMode === 'fixed' && (
                <Tooltip title="固定止损：跌破买入价 X% 无条件卖出（默认15%，只防黑天鹅，太紧会割在低点）">
                  <InputNumber value={btStopPct} onChange={setBtStopPct} min={0.03} max={0.3} step={0.01} style={{ width: 100 }} addonBefore="止损" addonAfter="%" />
                </Tooltip>
              )}
              {btStopMode === 'atr' && (
                <Tooltip title="ATR自适应：止损价 = 买入价 − N×ATR14（按个股波动率设止损，高波动股不误杀）">
                  <InputNumber value={btAtrMult} onChange={setBtAtrMult} min={0.5} max={5} step={0.5} style={{ width: 100 }} addonBefore="ATR" addonAfter="倍" />
                </Tooltip>
              )}
              <Tooltip title="趋势退出：收盘跌破 N 日均线卖出（默认10日，比5日更钝少洗盘；0=关闭）">
                <Select
                  value={btMaExit}
                  onChange={setBtMaExit}
                  style={{ width: 90 }}
                  options={[
                    { value: 0, label: '均线关' },
                    { value: 5, label: 'MA5' },
                    { value: 10, label: 'MA10' },
                    { value: 20, label: 'MA20' },
                  ]}
                />
              </Tooltip>
              <Button type="primary" icon={<FundOutlined />} loading={btLoading} onClick={runBacktest}>运行回测</Button>
            </Space>

            {btLoading && !btResult && (
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '40px 0', gap: 14 }}>
                <Spin size="large" />
                <Text type="secondary">回测计算中…（沪深A股全量约需 1 分钟，请勿关闭页面）</Text>
              </div>
            )}

            {btResult && (
              <>
                <Row gutter={[12, 12]} style={{ marginBottom: 12 }}>
                  <Col xs={8} md={4}><Statistic title="累计收益" value={metricVal(btMetrics.total_ret)} suffix="%" valueStyle={{ color: btMetrics.total_ret >= 0 ? '#cf1322' : '#389e0d' }} /></Col>
                  <Col xs={8} md={4}><Statistic title="年化" value={metricVal(btMetrics.annual_ret)} suffix="%" valueStyle={{ color: btMetrics.annual_ret >= 0 ? '#cf1322' : '#389e0d' }} /></Col>
                  <Col xs={8} md={4}><Statistic title="Sharpe" value={btMetrics.sharpe} precision={2} /></Col>
                  <Col xs={8} md={4}><Statistic title="最大回撤" value={metricVal(btMetrics.max_drawdown)} suffix="%" valueStyle={{ color: '#d46b08' }} /></Col>
                  <Col xs={8} md={4}><Statistic title="Calmar" value={btMetrics.calmar} precision={2} /></Col>
                  <Col xs={8} md={4}>
                    <Statistic
                      title="vs 沪深300"
                      value={btMetrics.bench_total === null || btMetrics.bench_total === undefined ? '-' : metricVal(btMetrics.bench_total)}
                      suffix={btMetrics.bench_total !== null && btMetrics.bench_total !== undefined ? '%' : ''}
                      valueStyle={{ color: (btMetrics.bench_total || 0) >= 0 ? '#389e0d' : '#cf1322', fontSize: 16 }}
                    />
                  </Col>
                </Row>
                <Text type="secondary" style={{ fontSize: 12 }}>
                  区间 {btResult.params.start} ~ {btResult.params.end}（{btResult.params.periods} 期；基准为同期沪深300 累计）
                </Text>
                {navOption && <ReactECharts option={navOption} style={{ height: 300 }} notMerge />}

                <Divider style={{ margin: '12px 0' }}>当前股票池（每日轮动最新持仓 Top 100；入场日 = 各股买入日，仍在持有则出场日为空）</Divider>
                <Table
                  rowKey="symbol"
                  size="small"
                  columns={holdingsCols}
                  dataSource={btResult.holdings || []}
                  pagination={{ pageSize: 20, showSizeChanger: false }}
                  scroll={{ x: 'max-content' }}
                  locale={{ emptyText: <Empty description="本期无持仓数据" image={Empty.PRESENTED_IMAGE_SIMPLE} /> }}
                />
                <Divider style={{ margin: '12px 0' }}>交易明细（最近 500 笔，倒序；卖出含原因与单笔盈亏）</Divider>
                <Table
                  rowKey={(r) => `${r.date}-${r.symbol}-${r.dir}-${r.price}`}
                  size="small"
                  columns={tradesCols}
                  dataSource={btResult.trades || []}
                  pagination={{ pageSize: 20, showSizeChanger: false }}
                  scroll={{ x: 'max-content' }}
                  locale={{ emptyText: <Empty description="暂无交易记录" image={Empty.PRESENTED_IMAGE_SIMPLE} /> }}
                />
              </>
            )}
          </Card>
        </Col>
      </Row>
    </div>
    </BtErrorBoundary>
  );
};

export default FactorResearchPage;
