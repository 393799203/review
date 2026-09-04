import React, { useState, useEffect, useMemo } from 'react';
import { Form, DatePicker, InputNumber, Button, Table, Card, message, Empty, Row, Col, Space, Tooltip, Tag, Switch, Collapse, Checkbox } from 'antd';
import { SearchOutlined, PlusOutlined, SlidersOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';
import { stockApi } from '../services/api';
import { useGlobal } from '../contexts/GlobalContext';
import StockKlineModal from '../components/StockKlineModal';

// 突破放量策略默认参数
const BREAKOUT_DEFAULT_PARAMS = {
  turnover_min: 15,
  upper_shadow_max: 10,
  prev_high_days: 60,
  prev_high_coef: 0.9,
  vol_window: 10,
  vol_pct: 30,      // 放量下限%（相对均量）
  vol_pct_max: 50,  // 放量上限%（相对均量），默认上限 50
  close_window: 20,
  close_ratio: 1.3,
};

// 抄底放量策略默认参数
const BOTTOM_DEFAULT_PARAMS = {
  vol_window: 20,
  day1_mult: 2.5,
  day23_mult: 2.0,
  cv_max: 0.5,
  day1_change_min: 3,
};

const DEFAULT_PARAMS = { ...BREAKOUT_DEFAULT_PARAMS, ...BOTTOM_DEFAULT_PARAMS };

const { Panel } = Collapse;

// 策略选择卡片配置：简短说明 + 选中渐变（红涨/蓝紫，与全站风格一致）
const STRATEGY_CARDS = [
  {
    value: 'bottom',
    label: '抄底放量',
    desc: '低位缩量后放量',
    gradient: 'linear-gradient(135deg, #13c2c2 0%, #36cfc9 100%)',
    shadow: '0 4px 12px rgba(19,194,194,0.30)',
  },
  {
    value: 'breakout',
    label: '突破放量',
    desc: '放量突破前高',
    gradient: 'linear-gradient(135deg, #f5222d 0%, #ff7875 100%)',
    shadow: '0 4px 12px rgba(245,34,45,0.28)',
  },
];

// A股配色：红涨绿跌
const renderChangePct = (value) => {
  if (value === null || value === undefined) return '-';
  const color = value >= 0 ? '#cf1322' : '#3f8600';
  return <span style={{ color }}>{value > 0 ? '+' : ''}{value.toFixed(2)}%</span>;
};

const ScreeningPage = () => {
  const { tradingDays, currentDate } = useGlobal();
  const [form] = Form.useForm();

  // 移动端适配（与 MainLayout 同一套判断）
  const [isMobile, setIsMobile] = useState(false);

  const [screeningDates, setScreeningDates] = useState([]);
  const [datesLoaded, setDatesLoaded] = useState(false);
  const [strategy, setStrategy] = useState('bottom');
  const [results, setResults] = useState([]);
  const [searchDate, setSearchDate] = useState('');
  const [searched, setSearched] = useState(false);
  const [loading, setLoading] = useState(false);
  const [selectedRowKeys, setSelectedRowKeys] = useState([]);
  const [adding, setAdding] = useState(false);
  // H5 卡片流无限加载：每页条数 + 已加载页数
  const MOBILE_PAGE_SIZE = 20;
  const [mobilePage, setMobilePage] = useState(1);
  const hasMore = results.length > mobilePage * MOBILE_PAGE_SIZE;
  const displayedResults = results.slice(0, mobilePage * MOBILE_PAGE_SIZE);

  // H5：滚动接近底部时自动加载下一页（无限加载）
  useEffect(() => {
    const handleScroll = () => {
      if (!isMobile || loading || !hasMore) return;
      const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
      const scrollHeight = document.documentElement.scrollHeight;
      const clientHeight = document.documentElement.clientHeight;
      if (scrollTop + clientHeight >= scrollHeight - 300) {
        setMobilePage((p) => p + 1);
      }
    };
    if (isMobile) {
      window.addEventListener('scroll', handleScroll, { passive: true });
      return () => window.removeEventListener('scroll', handleScroll);
    }
  }, [isMobile, loading, hasMore, results.length]);

  const [klineVisible, setKlineVisible] = useState(false);
  const [selectedStock, setSelectedStock] = useState(null);
  const [autoEnabled, setAutoEnabled] = useState(false);
  const [autoSaving, setAutoSaving] = useState(false);
  const [autoLogs, setAutoLogs] = useState([]);

  // 加载每日自动筛选配置（按当前策略分别读取/显示各自开关）
  useEffect(() => {
    const loadAutoConfig = async () => {
      try {
        const response = await stockApi.getAutoScreeningConfig(strategy);
        if (response.data.success) {
          setAutoEnabled(response.data.data?.enabled || false);
        }
        const logsResponse = await stockApi.getAutoScreeningLogs(strategy);
        if (logsResponse.data.success) {
          setAutoLogs(logsResponse.data.data || []);
        }
      } catch (error) {
        // 配置接口失败不打扰用户
        console.warn('加载自动筛选配置失败:', error);
      }
    };
    loadAutoConfig();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [strategy]);

  // 开关：保存配置（带当前表单参数）
  const handleAutoToggle = async (checked) => {
    setAutoSaving(true);
    try {
      const values = form.getFieldsValue();
      const params = {
        date: values.date ? values.date.format('YYYY-MM-DD') : undefined,
        vol_window: values.vol_window,
      };
      if (strategy === 'bottom') {
        params.day1_mult = values.day1_mult;
        params.day23_mult = values.day23_mult;
        params.cv_max = values.cv_max;
        params.day1_change_min = values.day1_change_min;
      } else {
        params.turnover_min = values.turnover_min;
        params.upper_shadow_max = values.upper_shadow_max;
        params.prev_high_days = values.prev_high_days;
        params.prev_high_coef = values.prev_high_coef;
        params.vol_pct = values.vol_pct;
        params.vol_pct_max = values.vol_pct_max;
        params.close_window = values.close_window;
        params.close_ratio = values.close_ratio;
      }
      const response = await stockApi.saveAutoScreeningConfig({
        enabled: checked,
        strategy,
        params,
      });
      if (response.data.success) {
        setAutoEnabled(checked);
        message.success(checked ? '已开启每日 19:00 自动筛选' : '已关闭每日自动筛选');
      } else {
        message.error(response.data.error || '保存失败');
      }
    } catch (error) {
      message.error('保存失败：' + (error.response?.data?.error || error.message));
    } finally {
      setAutoSaving(false);
    }
  };

  // 移动端适配（与 MainLayout 同一套判断）
  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 768);
    };
    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);
  // 可选交易日：全局交易日(YYYYMMDD) ∪ TDX 有数据的交易日
  const allowedDays = useMemo(() => {
    const set = new Set(tradingDays || []);
    screeningDates.forEach((d) => set.add(d.replace(/-/g, '')));
    return set;
  }, [tradingDays, screeningDates]);

  const disabledDate = (current) => {
    if (!current) return true;
    return !allowedDays.has(current.format('YYYYMMDD'));
  };

  // 加载 TDX 有数据的交易日
  useEffect(() => {
    const loadDates = async () => {
      try {
        const response = await stockApi.getScreeningDates();
        if (response.data.success) {
          setScreeningDates(response.data.data || []);
        }
      } catch (error) {
        // TDX 未配置等场景不打扰用户，执行筛选时会明确报错
        console.warn('获取筛选交易日失败:', error);
      } finally {
        setDatesLoaded(true);
      }
    };
    loadDates();
  }, []);

  // 默认日期：TDX 库最近一个有数据的交易日；取不到再用全局当前交易日
  useEffect(() => {
    if (!datesLoaded) return;
    if (form.getFieldValue('date')) return;
    let target = null;
    if (screeningDates.length > 0) {
      target = screeningDates[0].replace(/-/g, '');
    } else if (currentDate) {
      target = currentDate;
    }
    if (target) {
      form.setFieldsValue({ date: dayjs(target, 'YYYYMMDD') });
    }
  }, [currentDate, screeningDates, datesLoaded, allowedDays, form]);

  // 切换策略时把"放量参考窗口日"重置为对应策略的默认值
  const handleStrategyChange = (e) => {
    const value = e.target.value;
    setStrategy(value);
    form.setFieldsValue({
      vol_window: value === 'bottom' ? BOTTOM_DEFAULT_PARAMS.vol_window : BREAKOUT_DEFAULT_PARAMS.vol_window,
    });
  };

  const handleRun = async (values) => {
    setLoading(true);
    setSelectedRowKeys([]);
    try {
      const params = {
        strategy,
        date: values.date.format('YYYY-MM-DD'),
        vol_window: values.vol_window,
      };
      if (strategy === 'bottom') {
        params.day1_mult = values.day1_mult;
        params.day23_mult = values.day23_mult;
        params.cv_max = values.cv_max;
        params.day1_change_min = values.day1_change_min;
      } else {
        params.turnover_min = values.turnover_min;
        params.upper_shadow_max = values.upper_shadow_max;
        params.prev_high_days = values.prev_high_days;
        params.prev_high_coef = values.prev_high_coef;
        params.vol_pct = values.vol_pct;
        params.vol_pct_max = values.vol_pct_max;
        params.close_window = values.close_window;
        params.close_ratio = values.close_ratio;
      }
      const response = await stockApi.runScreening(params);
      if (response.data.success) {
        setResults(response.data.data || []);
        setSearchDate(params.date);
        setSearched(true);
        setMobilePage(1);  // 新结果重新从第 1 页卡片开始
      } else {
        message.error(response.data.error || '筛选失败');
      }
    } catch (error) {
      message.error(error.response?.data?.error || '筛选失败：' + error.message);
    } finally {
      setLoading(false);
    }
  };

  const handleAddSelected = async () => {
    if (selectedRowKeys.length === 0) {
      message.warning('请先勾选要添加的股票');
      return;
    }
    setAdding(true);
    let successCount = 0;
    let failCount = 0;
    const strategyName = strategy === 'bottom' ? '抄底放量' : '突破放量';
    const selectedRows = results.filter((r) => selectedRowKeys.includes(r.symbol));

    const buildParams = (row) => {
      // 默认预警价 = 放量日最低价 × 1.02（bottom 放量日=放量首日 signal_date，breakout 放量日=D）
      const volDayLow = strategy === 'bottom'
        ? (row.signal_low != null ? row.signal_low : row.low)
        : row.low;
      const alertPrice = volDayLow != null ? Number((volDayLow * 1.02).toFixed(2)) : undefined;
      // 入选原因：当日所走概念板块（前 3 个拼接）
      const conceptBlocks = row.concept_blocks
        || (row.concept_block ? [row.concept_block_info].filter(Boolean) : []);
      const category = conceptBlocks.slice(0, 3).map((b) => b.block_name).filter(Boolean).join('/');
      return {
        stock_code: row.code,
        stock_name: row.name || row.code,
        add_date: (row.date || '').replace(/-/g, ''),
        add_price: row.close,
        add_reason: strategyName,
        source: 'screening',
        add_type: 'strategy',
        alert_price: alertPrice,
        signal_date: (row.signal_date || '').replace(/-/g, '') || undefined,
        limit_up_reason_category: category,
      };
    };

    // 分批并发（每批 10 只），避免 300+ 只串行等待
    const BATCH = 10;
    for (let i = 0; i < selectedRows.length; i += BATCH) {
      const batch = selectedRows.slice(i, i + BATCH);
      const results = await Promise.all(batch.map(async (row) => {
        try {
          const response = await stockApi.addWatchlist(buildParams(row));
          return response.data.success;
        } catch (error) {
          return false;
        }
      }));
      results.forEach((ok) => { if (ok) successCount += 1; else failCount += 1; });
    }
    setAdding(false);
    if (failCount === 0) {
      message.success(`已加入自选 ${successCount} 只，可到「自选股」页面查看`);
    } else {
      message.warning(`添加完成：成功 ${successCount} 只，失败 ${failCount} 只`);
    }
  };

  const columns = [
    {
      title: '代码/简称',
      key: 'code_name',
      width: 110,
      render: (_, record) => (
        <a
          onClick={() => {
            setSelectedStock({ code: record.code, name: record.name, signalDate: record.signal_date, strategyDate: searchDate || undefined });
            setKlineVisible(true);
          }}
        >
          <div>{record.code}</div>
          <div style={{ fontSize: 11, color: '#666' }}>{record.name || '-'}</div>
        </a>
      ),
    },
    {
      title: '日期/放量日',
      key: 'date_signal',
      width: 100,
      render: (_, record) => (
        <div>
          <div>{record.date || '-'}</div>
          <div style={{ fontSize: 11, color: '#666' }}>{record.signal_date || '-'}</div>
        </div>
      ),
    },
    {
      title: '收盘/涨跌',
      key: 'close_change',
      width: 100,
      render: (_, record) => (
        <div>
          <div>{record.close === null || record.close === undefined ? '-' : record.close.toFixed(2)}</div>
          <div>{renderChangePct(record.change_pct)}</div>
        </div>
      ),
    },
    {
      title: '换手率/总市值',
      key: 'turnover_mv',
      width: 105,
      render: (_, record) => (
        <div>
          <div>{record.turnover === null || record.turnover === undefined ? '-' : `${record.turnover.toFixed(2)}%`}</div>
          <div style={{ fontSize: 11, color: '#666' }}>
            {record.totalmv ? `${(record.totalmv / 100000000).toFixed(1)}亿` : '-'}
          </div>
        </div>
      ),
    },
    {
      title: '申万一级/涨跌',
      key: 'sw1',
      width: 115,
      render: (_, record) => (
        <div>
          <div>{record.sw1_name || '-'}</div>
          <div>{renderChangePct(record.sw1_change_pct)}</div>
        </div>
      ),
    },
    {
      title: '申万二级/涨跌',
      key: 'sw2',
      width: 125,
      render: (_, record) => (
        <div>
          <div>{record.sw2_name || '-'}</div>
          <div>{renderChangePct(record.sw2_change_pct)}</div>
        </div>
      ),
    },
    {
      title: '概念板块',
      key: 'concept_block',
      width: 200,
      render: (_, record) => {
        const blocks = record.concept_blocks
          || (record.concept_block ? [record.concept_block_info].filter(Boolean) : []);
        if (blocks.length === 0) return '-';
        return (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 2 }}>
            {blocks.slice(0, 3).map((b, i) => (
              <Tooltip
                key={`${b.block_name}_${i}`}
                title={
                  b.matched_tag ? (
                    <div>
                      <div>{b.block_name}</div>
                      <div>依据: {b.matched_tag}</div>
                      <div>板块涨跌: {b.change_rate ? `${b.change_rate > 0 ? '+' : ''}${b.change_rate.toFixed(1)}%` : '-'}</div>
                    </div>
                  ) : null
                }
              >
                <Tag
                  color={i === 0 ? 'purple' : 'default'}
                  style={{ fontSize: 10, margin: 0, cursor: 'help' }}
                >
                  {b.block_name}
                </Tag>
              </Tooltip>
            ))}
          </div>
        );
      },
    },
    {
      title: '评分',
      dataIndex: 'ml_score',
      key: 'ml_score',
      width: 65,
      align: 'right',
      render: (v) => (v === null || v === undefined ? '-' : v),
    },
  ];

  // H5 结果卡片流（点击卡片看K线，左侧勾选，滚动无限加载）
  const renderMobileCards = () => (
    <div>
      {displayedResults.map((record) => {
        const blocks = record.concept_blocks
          || (record.concept_block ? [record.concept_block_info].filter(Boolean) : []);
        const checked = selectedRowKeys.includes(record.symbol);
        const close = record.close == null ? '-' : record.close.toFixed(2);
        return (
          <div
            key={record.symbol}
            style={{
              background: '#fff',
              borderRadius: 8,
              marginBottom: 8,
              padding: '10px 12px',
              border: checked ? '1px solid #1890ff' : '1px solid #f0f0f0',
              boxShadow: '0 1px 2px rgba(0,0,0,0.04)',
              cursor: 'pointer',
            }}
            onClick={() => {
              setSelectedStock({ code: record.code, name: record.name, signalDate: record.signal_date, strategyDate: searchDate || undefined });
              setKlineVisible(true);
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <Checkbox
                checked={checked}
                onClick={(e) => e.stopPropagation()}
                onChange={(e) => {
                  const ks = e.target.checked
                    ? [...selectedRowKeys, record.symbol]
                    : selectedRowKeys.filter((k) => k !== record.symbol);
                  setSelectedRowKeys(ks);
                }}
              />
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <span style={{ fontWeight: 600, color: '#262626', fontSize: 15 }}>{record.name || '-'}</span>
                  <span style={{ fontSize: 11, color: '#999' }}>{record.code}</span>
                </div>
                <div style={{ fontSize: 11, color: '#999', marginTop: 2 }}>
                  放量日 {record.signal_date || '-'} · 申万 {record.sw1_name || '-'}
                </div>
                {blocks.length > 0 && (
                  <div style={{ marginTop: 4, display: 'flex', flexWrap: 'wrap', gap: 3 }}>
                    {blocks.slice(0, 3).map((b, i) => (
                      <Tag key={`${b.block_name}_${i}`} color={i === 0 ? 'purple' : 'default'} style={{ fontSize: 10, margin: 0, lineHeight: '16px' }}>
                        {b.block_name}
                      </Tag>
                    ))}
                  </div>
                )}
              </div>
              <div style={{ textAlign: 'right', flexShrink: 0 }}>
                <div style={{ fontWeight: 600, color: '#262626', fontSize: 15 }}>{close}</div>
                <div style={{ fontSize: 13 }}>{renderChangePct(record.change_pct)}</div>
                <div style={{ fontSize: 11, color: '#666', marginTop: 1 }}>
                  换手 {record.turnover == null ? '-' : record.turnover.toFixed(1)}%
                </div>
                {record.ml_score != null && (
                  <div style={{ fontSize: 11, color: '#fa8c16' }}>评分 {record.ml_score}</div>
                )}
              </div>
            </div>
          </div>
        );
      })}
      {loading && (
        <div style={{ textAlign: 'center', padding: '16px 0', color: '#999', fontSize: 12 }}>加载中...</div>
      )}
      {!loading && hasMore && (
        <div style={{ textAlign: 'center', padding: '12px 0', color: '#999', fontSize: 12 }}>上拉加载更多</div>
      )}
      {!loading && !hasMore && results.length > 0 && (
        <div style={{ textAlign: 'center', padding: '12px 0', color: '#bbb', fontSize: 12 }}>
          — 已加载全部 {results.length} 只 —
        </div>
      )}
    </div>
  );

  // 策略专属参数（桌面平铺，H5 折叠进"更多参数"）
  const strategyParamFields = strategy === 'bottom' ? (
    <>
      <Form.Item name="day1_mult" label="第1天放量倍数（×均量）">
        <InputNumber className="screening-field" style={{ width: '100%' }} min={0} step={0.1} />
      </Form.Item>
      <Form.Item name="day23_mult" label="第2/3天放量倍数（×均量）">
        <InputNumber className="screening-field" style={{ width: '100%' }} min={0} step={0.1} />
      </Form.Item>
      <Form.Item name="cv_max" label="地量CV上限（放量前波动）">
        <InputNumber className="screening-field" style={{ width: '100%' }} min={0} max={2} step={0.05} />
      </Form.Item>
      <Form.Item name="day1_change_min" label="首日涨幅下限%（可负）">
        <InputNumber className="screening-field" style={{ width: '100%' }} min={-20} max={20} step={0.5} />
      </Form.Item>
    </>
  ) : (
    <>
      <Form.Item
        label="放量区间%（相对均量）"
        style={{ marginBottom: 4 }}
        tooltip="当日成交量较前 vol_window 日均量的放大幅度下限~上限（如 30%~50% 表示 1.3~1.5 倍均量）"
      >
        <Space.Compact style={{ width: '100%' }}>
          <Form.Item name="vol_pct" noStyle>
            <InputNumber
              style={{ width: '50%' }}
              min={0}
              step={5}
              placeholder="下限"
            />
          </Form.Item>
          <Form.Item name="vol_pct_max" noStyle>
            <InputNumber
              style={{ width: '50%' }}
              min={0}
              step={5}
              placeholder="上限"
            />
          </Form.Item>
        </Space.Compact>
      </Form.Item>
      <Form.Item name="turnover_min" label="换手率阈值%（≥）">
        <InputNumber className="screening-field" style={{ width: '100%' }} min={0} step={1} />
      </Form.Item>
      <Form.Item name="upper_shadow_max" label="上影线≤%（相对昨收）">
        <InputNumber className="screening-field" style={{ width: '100%' }} min={0} step={1} />
      </Form.Item>
      <Form.Item name="prev_high_days" label="前高回溯交易日">
        <InputNumber className="screening-field" style={{ width: '100%' }} min={1} precision={0} />
      </Form.Item>
      <Form.Item name="prev_high_coef" label="前高系数（收盘≥前高×系数）">
        <InputNumber className="screening-field" style={{ width: '100%' }} min={0.5} max={1.5} step={0.05} />
      </Form.Item>
      <Form.Item name="close_window" label="收盘价参考窗口日（均价）">
        <InputNumber className="screening-field" style={{ width: '100%' }} min={1} precision={0} />
      </Form.Item>
      <Form.Item name="close_ratio" label="收盘价最大比例（相对窗口均价）">
        <InputNumber className="screening-field" style={{ width: '100%' }} min={1} step={0.05} />
      </Form.Item>
    </>
  );

  // 每日自动筛选开关块
  const autoScreeningBlock = (
    <div style={{ marginBottom: isMobile ? 0 : 12, padding: '8px 10px', background: '#fafafa', borderRadius: 6 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 6 }}>
        <div style={{ minWidth: 0 }}>
          <div style={{ fontSize: 12, color: '#333', fontWeight: 500 }}>每日 19:00 自动筛选</div>
          <div style={{ fontSize: 11, color: '#999' }}>
            仅针对「{strategy === 'bottom' ? '抄底放量' : '突破放量'}」策略
          </div>
        </div>
        <Switch checked={autoEnabled} onChange={handleAutoToggle} loading={autoSaving} size="small" />
      </div>
      {autoLogs.length > 0 && (
        <div style={{ fontSize: 11, color: '#999', marginTop: 6, lineHeight: 1.5 }}>
          上次执行：{autoLogs[0].run_date} 新增 {autoLogs[0].added_count} 只
          {autoLogs[0].skipped_count > 0 ? `（${autoLogs[0].skipped_count} 只在自选中跳过）` : ''}
        </div>
      )}
    </div>
  );

  // H5：全选当前结果 + sticky 底部操作条
  const allSelected = results.length > 0 && selectedRowKeys.length === results.length;
  const handleSelectAll = (e) => {
    setSelectedRowKeys(e.target.checked ? results.map((r) => r.symbol) : []);
  };

  const filterTab = (
    <Row gutter={16}>
      <Col xs={24} lg={6}>
        <Card
          size="small"
          className="screening-filter-card"
          styles={{ body: { padding: isMobile ? 14 : 16 } }}
          title={
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 15, fontWeight: 600 }}>
              <span
                style={{
                  width: 26, height: 26, borderRadius: 8, display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
                  background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', color: '#fff', fontSize: 14,
                }}
              >
                <SlidersOutlined />
              </span>
              筛选参数
            </div>
          }
        >
          <Form
            form={form}
            layout="vertical"
            className="screening-form"
            size={isMobile ? 'small' : undefined}
            initialValues={DEFAULT_PARAMS}
            onFinish={handleRun}
          >
            <Form.Item style={{ marginBottom: 14 }}>
              <div className="screening-strategy-cards">
                {STRATEGY_CARDS.map((card) => {
                  const active = strategy === card.value;
                  return (
                    <button
                      type="button"
                      key={card.value}
                      className={`screening-strategy-card${active ? ' active' : ''}`}
                      style={active ? {
                        background: card.gradient,
                        boxShadow: card.shadow,
                        color: '#fff',
                        borderColor: 'transparent',
                      } : undefined}
                      onClick={() => handleStrategyChange({ target: { value: card.value } })}
                    >
                      <span className="screening-strategy-label">{card.label}</span>
                      <span className="screening-strategy-desc">{card.desc}</span>
                    </button>
                  );
                })}
              </div>
            </Form.Item>
            <Form.Item
              name="date"
              rules={[{ required: true, message: '请选择交易日期' }]}
            >
              <DatePicker
                style={{ width: '100%' }}
                format="YYYY-MM-DD"
                disabledDate={disabledDate}
                allowClear={false}
                size="large"
                className="screening-field screening-date-field"
              />
            </Form.Item>

            {isMobile ? (
              <>
                {/* H5：执行按钮放在核心区，首屏即可操作 */}
                <Form.Item style={{ marginBottom: 8 }}>
                  <Button
                    type="primary"
                    htmlType="submit"
                    icon={<SearchOutlined />}
                    loading={loading}
                    block
                    size="large"
                    className="screening-run-btn"
                  >
                    执行筛选
                  </Button>
                </Form.Item>
                <Collapse ghost className="screening-more-params">
                  <Panel
                    header={
                      <span>
                        <SlidersOutlined style={{ marginRight: 4, color: '#667eea' }} />
                        更多参数
                        <span style={{ color: '#999', fontSize: 12, marginLeft: 6 }}>
                          {strategy === 'bottom' ? '（抄底）' : '（突破）'}
                        </span>
                      </span>
                    }
                    key="params"
                  >
                    <Form.Item name="vol_window" label="放量参考窗口日">
                      <InputNumber className="screening-field" style={{ width: '100%' }} min={1} precision={0} />
                    </Form.Item>
                    {strategyParamFields}
                  </Panel>
                </Collapse>
                {autoScreeningBlock}
              </>
            ) : (
              <>
                <Form.Item name="vol_window" label="放量参考窗口日">
                  <InputNumber className="screening-field" style={{ width: '100%' }} min={1} precision={0} />
                </Form.Item>
                {strategyParamFields}
                {autoScreeningBlock}
                <Form.Item style={{ marginBottom: 0 }}>
                  <Button
                    type="primary"
                    htmlType="submit"
                    icon={<SearchOutlined />}
                    loading={loading}
                    block
                    className="screening-run-btn"
                  >
                    执行筛选
                  </Button>
                </Form.Item>
              </>
            )}
          </Form>
        </Card>
      </Col>
      <Col xs={24} lg={18}>
        <Card
          size="small"
          title={`筛选结果 (${results.length}只)`}
          extra={
            !isMobile && (
              <Space wrap size="small">
                <Button
                  style={{ backgroundColor: '#52c41a', borderColor: '#52c41a', color: '#fff' }}
                  icon={<PlusOutlined />}
                  onClick={handleAddSelected}
                  loading={adding}
                  disabled={selectedRowKeys.length === 0}
                >
                  加入自选
                </Button>
              </Space>
            )
          }
        >
          {results.length === 0 ? (
            <Empty
              style={{ padding: '48px 0' }}
              description={searched ? '当日无符合条件的股票，可尝试放宽参数' : '暂无内容，设置参数后点击「执行筛选」'}
            />
          ) : (
            <>
              {isMobile ? (
                renderMobileCards()
              ) : (
                <Table
                  rowKey="symbol"
                  columns={columns}
                  dataSource={results}
                  loading={loading}
                  size="small"
                  scroll={{ x: 940 }}
                  pagination={{ pageSize: 20, showSizeChanger: true, showTotal: (t) => `共 ${t} 只` }}
                  rowSelection={{
                    selectedRowKeys,
                    onChange: setSelectedRowKeys,
                  }}
                />
              )}
              {isMobile && searched && results.length > 0 && (
                <div className="screening-mobile-bar">
                  <Checkbox checked={allSelected} onChange={handleSelectAll} style={{ flexShrink: 0 }}>
                    全选
                  </Checkbox>
                  <span style={{ fontSize: 12, color: '#666', flexShrink: 0 }}>
                    已选 {selectedRowKeys.length} 只
                  </span>
                  <Button
                    type="primary"
                    style={{ backgroundColor: '#52c41a', borderColor: '#52c41a', color: '#fff', marginLeft: 'auto' }}
                    icon={<PlusOutlined />}
                    onClick={handleAddSelected}
                    loading={adding}
                    disabled={selectedRowKeys.length === 0}
                  >
                    加入自选
                  </Button>
                </div>
              )}
            </>
          )}
        </Card>
      </Col>
    </Row>
  );

  return (
    <div>
      <style>{`
        /* 筛选参数卡片整体 */
        .screening-filter-card {
          border-radius: 12px;
          box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        }
        .screening-filter-card .ant-card-head {
          border-bottom: 1px dashed #f0f0f0;
        }
        .screening-filter-card .ant-card-head-title {
          padding: 10px 0;
        }

        /* 策略选择卡片：双选紧凑横排 */
        .screening-strategy-cards {
          display: flex;
          gap: 8px;
        }
        .screening-strategy-card {
          flex: 1;
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 6px;
          padding: 8px 6px;
          border-radius: 10px;
          border: 1.5px solid #e8e8e8;
          background: #fff;
          cursor: pointer;
          transition: all 0.25s ease;
          outline: none;
          font-family: inherit;
          min-height: 36px;
        }
        .screening-strategy-card:hover {
          border-color: #b7c4ff;
        }
        .screening-strategy-card .screening-strategy-label {
          font-size: 13px;
          font-weight: 600;
          white-space: nowrap;
        }
        .screening-strategy-card .screening-strategy-desc {
          font-size: 10px;
          opacity: 0.75;
          white-space: nowrap;
        }
        .screening-strategy-card.active {
          color: #fff;
        }

        /* 输入控件：圆角 + 柔和阴影 */
        .screening-field.ant-input-number,
        .screening-field.ant-picker {
          border-radius: 8px;
          border-color: #e0e0e0;
        }
        /* 日期选择器加高 */
        .screening-date-field.ant-picker {
          height: 40px;
          font-size: 14px;
        }
        .screening-date-field.ant-picker-lg {
          height: 44px;
          font-size: 15px;
        }
        .screening-field.ant-input-number:hover,
        .screening-field.ant-picker:hover {
          border-color: #8a9bff;
        }
        .screening-field.ant-input-number-focused,
        .screening-field.ant-picker-focused {
          border-color: #667eea;
          box-shadow: 0 0 0 2px rgba(102,126,234,0.15);
        }

        /* 执行按钮：品牌渐变 */
        .screening-run-btn {
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
          border: none !important;
          border-radius: 10px !important;
          box-shadow: 0 4px 12px rgba(102,126,234,0.30) !important;
          font-weight: 600;
          letter-spacing: 1px;
        }
        .screening-run-btn:hover {
          opacity: 0.92;
          transform: translateY(-1px);
          box-shadow: 0 6px 16px rgba(102,126,234,0.40) !important;
        }
        .screening-run-btn.ant-btn-lg {
          height: 44px;
          font-size: 15px;
        }

        /* 更多参数折叠面板 */
        .screening-more-params {
          margin-bottom: 8px;
        }
        .screening-more-params .ant-collapse-header {
          border-radius: 8px !important;
          background: #f6f7ff;
          padding: 8px 12px !important;
          font-size: 13px;
        }
        .screening-more-params .ant-collapse-content-box {
          background: #fafbff;
          border-radius: 0 0 8px 8px;
          padding: 10px 12px 2px !important;
        }
        .screening-more-params .ant-form-item {
          margin-bottom: 10px;
        }

        @media (max-width: 767px) {
          .screening-form .ant-form-item {
            margin-bottom: 8px;
          }
          .screening-form .ant-form-item-label {
            padding-bottom: 2px;
          }
          /* H5 更多参数折叠面板紧凑 */
          .screening-more-params .ant-collapse-header {
            padding: 6px 0 !important;
            font-size: 13px;
          }
          .screening-more-params .ant-collapse-content-box {
            padding: 0 !important;
          }
          /* H5 底部固定操作条 */
          .screening-mobile-bar {
            position: sticky;
            bottom: 0;
            z-index: 10;
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 10px 12px;
            margin: 0 -12px -12px;
            background: rgba(255, 255, 255, 0.96);
            border-top: 1px solid #f0f0f0;
            box-shadow: 0 -2px 8px rgba(0, 0, 0, 0.06);
            backdrop-filter: blur(4px);
          }
        }
      `}</style>
      {filterTab}
      <StockKlineModal
        visible={klineVisible}
        stockCode={selectedStock?.code}
        stockName={selectedStock?.name}
        signalDate={selectedStock?.signalDate}
        strategyDate={selectedStock?.strategyDate}
        onClose={() => setKlineVisible(false)}
      />
    </div>
  );
};

export default ScreeningPage;
