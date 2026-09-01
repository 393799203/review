import React, { useState, useEffect, useMemo } from 'react';
import { Form, DatePicker, InputNumber, Button, Table, Card, message, Empty, Row, Col, Space, Radio } from 'antd';
import { SearchOutlined, PlusOutlined } from '@ant-design/icons';
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
  vol_pct: 30,
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

// A股配色：红涨绿跌
const renderChangePct = (value) => {
  if (value === null || value === undefined) return '-';
  const color = value >= 0 ? '#cf1322' : '#3f8600';
  return <span style={{ color }}>{value > 0 ? '+' : ''}{value.toFixed(2)}%</span>;
};

const ScreeningPage = () => {
  const { tradingDays, currentDate } = useGlobal();
  const [form] = Form.useForm();

  const [screeningDates, setScreeningDates] = useState([]);
  const [datesLoaded, setDatesLoaded] = useState(false);
  const [strategy, setStrategy] = useState('bottom');
  const [results, setResults] = useState([]);
  const [searched, setSearched] = useState(false);
  const [loading, setLoading] = useState(false);
  const [selectedRowKeys, setSelectedRowKeys] = useState([]);
  const [adding, setAdding] = useState(false);

  const [klineVisible, setKlineVisible] = useState(false);
  const [selectedStock, setSelectedStock] = useState(null);

  // 移动端适配（与 MainLayout 同一套判断）
  const [isMobile, setIsMobile] = useState(false);
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
        params.close_window = values.close_window;
        params.close_ratio = values.close_ratio;
      }
      const response = await stockApi.runScreening(params);
      if (response.data.success) {
        setResults(response.data.data || []);
        setSearched(true);
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
    for (const row of selectedRows) {
      try {
        // 默认预警价 = 放量日最低价 × 1.02（bottom 放量日=放量首日 signal_date，breakout 放量日=D）
        const volDayLow = strategy === 'bottom'
          ? (row.signal_low != null ? row.signal_low : row.low)
          : row.low;
        const alertPrice = volDayLow != null ? Number((volDayLow * 1.02).toFixed(2)) : undefined;
        // 入选原因：申万一级-申万二级（如"电子-半导体"）
        const category = row.sw1_name && row.sw2_name
          ? `${row.sw1_name}-${row.sw2_name}`
          : (row.sw1_name || '');
        const response = await stockApi.addWatchlist({
          stock_code: row.code,
          stock_name: row.name || row.code,
          add_date: (row.date || '').replace(/-/g, ''),
          add_price: row.close,
          add_reason: strategyName,
          source: 'screening',
          add_type: 'strategy',
          alert_price: alertPrice,
          limit_up_reason_category: category,
        });
        if (response.data.success) {
          successCount += 1;
        } else {
          failCount += 1;
        }
      } catch (error) {
        failCount += 1;
      }
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
            setSelectedStock({ code: record.code, name: record.name, signalDate: record.signal_date });
            setKlineVisible(true);
          }}
        >
          <div>{record.code}</div>
          <div style={{ fontSize: 11, color: '#666' }}>{record.name || '-'}</div>
        </a>
      ),
    },
    { title: '日期', dataIndex: 'date', key: 'date', width: 90 },
    { title: '放量首日', dataIndex: 'signal_date', key: 'signal_date', width: 90, render: (v) => v || '-' },
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
      title: '评分',
      dataIndex: 'ml_score',
      key: 'ml_score',
      width: 65,
      align: 'right',
      render: (v) => (v === null || v === undefined ? '-' : v),
    },
  ];

  // 移动端精简列：代码/简称合并，只保留关键字段
  const mobileColumns = [
    {
      title: '代码/简称',
      key: 'code',
      width: 95,
      render: (_, record) => (
        <a
          onClick={() => {
            setSelectedStock({ code: record.code, name: record.name, signalDate: record.signal_date });
            setKlineVisible(true);
          }}
        >
          <div>{record.code}</div>
          <div style={{ fontSize: 11, color: '#666' }}>{record.name || '-'}</div>
        </a>
      ),
    },
    {
      title: '收盘',
      dataIndex: 'close',
      key: 'close',
      width: 65,
      align: 'right',
      render: (v) => (v === null || v === undefined ? '-' : v.toFixed(2)),
    },
    {
      title: '涨跌幅%',
      dataIndex: 'change_pct',
      key: 'change_pct',
      width: 70,
      align: 'right',
      render: renderChangePct,
    },
    {
      title: '换手%',
      dataIndex: 'turnover',
      key: 'turnover',
      width: 60,
      align: 'right',
      render: (v) => (v === null || v === undefined ? '-' : v.toFixed(1)),
    },
    {
      title: '行业',
      dataIndex: 'sw1_name',
      key: 'sw1_name',
      width: 70,
      render: (v) => v || '-',
    },
  ];

  const filterTab = (
    <Row gutter={16}>
      <Col xs={24} lg={6}>
        <Card title="筛选参数" size="small">
          <Form
            form={form}
            layout="vertical"
            initialValues={DEFAULT_PARAMS}
            onFinish={handleRun}
          >
            <Form.Item label="策略" style={{ marginBottom: 12 }}>
              <Radio.Group
                value={strategy}
                onChange={handleStrategyChange}
                optionType="button"
                buttonStyle="solid"
                style={{ width: '100%', display: 'flex' }}
                options={[
                  { value: 'bottom', label: '抄底放量' },
                  { value: 'breakout', label: '突破放量' },
                ]}
              />
            </Form.Item>
            <Form.Item
              name="date"
              label="交易日期"
              rules={[{ required: true, message: '请选择交易日期' }]}
            >
              <DatePicker
                style={{ width: '100%' }}
                format="YYYY-MM-DD"
                disabledDate={disabledDate}
                allowClear={false}
              />
            </Form.Item>
            <Form.Item name="vol_window" label="放量参考窗口日">
              <InputNumber style={{ width: '100%' }} min={1} precision={0} />
            </Form.Item>
            {strategy === 'bottom' && (
              <>
                <Form.Item name="day1_mult" label="第1天放量倍数（×均量）">
                  <InputNumber style={{ width: '100%' }} min={0} step={0.1} />
                </Form.Item>
                <Form.Item name="day23_mult" label="第2/3天放量倍数（×均量）">
                  <InputNumber style={{ width: '100%' }} min={0} step={0.1} />
                </Form.Item>
                <Form.Item name="cv_max" label="地量CV上限（放量前波动）">
                  <InputNumber style={{ width: '100%' }} min={0} max={2} step={0.05} />
                </Form.Item>
                <Form.Item name="day1_change_min" label="首日涨幅下限%（可负）">
                  <InputNumber style={{ width: '100%' }} min={-20} max={20} step={0.5} />
                </Form.Item>
              </>
            )}
            {strategy === 'breakout' && (
              <>
                <Form.Item name="turnover_min" label="换手率阈值%（≥）">
                  <InputNumber style={{ width: '100%' }} min={0} step={1} />
                </Form.Item>
                <Form.Item name="upper_shadow_max" label="上影线≤%（相对昨收）">
                  <InputNumber style={{ width: '100%' }} min={0} step={1} />
                </Form.Item>
                <Form.Item name="prev_high_days" label="前高回溯交易日">
                  <InputNumber style={{ width: '100%' }} min={1} precision={0} />
                </Form.Item>
                <Form.Item name="prev_high_coef" label="前高系数（收盘≥前高×系数）">
                  <InputNumber style={{ width: '100%' }} min={0.5} max={1.5} step={0.05} />
                </Form.Item>
                <Form.Item name="vol_pct" label="放量阈值%（相对均量）">
                  <InputNumber style={{ width: '100%' }} min={0} step={5} />
                </Form.Item>
                <Form.Item name="close_window" label="收盘价参考窗口日（均价）">
                  <InputNumber style={{ width: '100%' }} min={1} precision={0} />
                </Form.Item>
                <Form.Item name="close_ratio" label="收盘价最大比例（相对窗口均价）">
                  <InputNumber style={{ width: '100%' }} min={1} step={0.05} />
                </Form.Item>
              </>
            )}
            <Form.Item style={{ marginBottom: 0 }}>
              <Button type="primary" htmlType="submit" icon={<SearchOutlined />} loading={loading} block>
                执行筛选
              </Button>
            </Form.Item>
          </Form>
        </Card>
      </Col>
      <Col xs={24} lg={18}>
        <Card
          size="small"
          title={`筛选结果 (${results.length}只)`}
          extra={
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
          }
        >
          {searched && results.length === 0 ? (
            <Empty description="当日无符合条件的股票，可尝试放宽参数" />
          ) : (
            <Table
              rowKey="symbol"
              columns={isMobile ? mobileColumns : columns}
              dataSource={results}
              loading={loading}
              size="small"
              scroll={isMobile ? undefined : { x: 800 }}
              pagination={{ pageSize: 20, showSizeChanger: !isMobile, showTotal: (t) => `共 ${t} 只` }}
              rowSelection={{
                selectedRowKeys,
                onChange: setSelectedRowKeys,
              }}
            />
          )}
        </Card>
      </Col>
    </Row>
  );

  return (
    <div>
      {filterTab}
      <StockKlineModal
        visible={klineVisible}
        stockCode={selectedStock?.code}
        stockName={selectedStock?.name}
        signalDate={selectedStock?.signalDate}
        onClose={() => setKlineVisible(false)}
      />
    </div>
  );
};

export default ScreeningPage;
