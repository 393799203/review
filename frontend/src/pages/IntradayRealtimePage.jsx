import React, { useState, useEffect, useMemo, useCallback, useRef } from 'react';
import { Card, Tag, Spin, Tooltip, Button, Space, Badge, Table, Empty, DatePicker } from 'antd';
import { ClockCircleOutlined, ReloadOutlined, LeftOutlined, RightOutlined, AimOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';
import { stockApi } from '../services/api';
import { useGlobal } from '../contexts/GlobalContext';
import { useAutoRefresh } from '../hooks/useAutoRefresh';
import StockKlineModal from '../components/StockKlineModal';
import ComparableStockModal from '../components/ComparableStockModal';

const IntradayRealtimePage = () => {
  const isMobile = window.innerWidth < 768;
  const {
    currentDate,
    latestDate,
    tradingDays,
    refreshKey,
    autoRefresh,
    refreshInterval,
    smartMode,
    loading: globalLoading,
    setLoading: setGlobalLoading,
    loadPageSettings,
    handleDateChange,
    handlePrevDay,
    handleNextDay,
  } = useGlobal();

  const [ladderData, setLadderData] = useState([]);
  const [yesterdayData, setYesterdayData] = useState(null);
  const [localLoading, setLocalLoading] = useState(false);
  const [klineVisible, setKlineVisible] = useState(false);
  const [selectedStock, setSelectedStock] = useState(null);
  const [comparableVisible, setComparableVisible] = useState(false);
  const [comparableContext, setComparableContext] = useState(null);
  const firstLoadDone = useRef(false);

  useEffect(() => {
    loadPageSettings('intraday');
  }, []);

  const fetchData = useCallback(async () => {
    if (!currentDate) return;
    try {
      setLocalLoading(true);
      const response = await stockApi.getDataByDate(currentDate);
      if (response.data.success && response.data.data) {
        setLadderData(response.data.data.ladder || []);
        setYesterdayData(response.data.data.yesterday || null);
      }
    } catch (error) {
      console.error('获取盘中实时数据失败:', error);
    } finally {
      setLocalLoading(false);
      firstLoadDone.current = true;
    }
  }, [currentDate]);

  useEffect(() => {
    fetchData();
  }, [currentDate, refreshKey, fetchData]);

  useEffect(() => {
    setGlobalLoading(localLoading);
  }, [localLoading, setGlobalLoading]);

  useAutoRefresh({
    autoRefresh,
    refreshInterval,
    smartMode,
    currentPage: 'intraday',
    tradingDays,
    currentDate,
    latestDate,
    callback: fetchData
  });

  const intradayStocks = useMemo(() => {
    const allStocks = [];
    ladderData.forEach(item => {
      if (item.level < 2) return;
      item.stocks.forEach(stock => {
        if (stock.limit_up_time && stock.limit_up_time < '10:00') {
          allStocks.push({
            ...stock,
            level: item.level,
            levelLabel: item.label
          });
        }
      });
    });
    return allStocks.sort((a, b) => a.limit_up_time.localeCompare(b.limit_up_time));
  }, [ladderData]);

  const currentIndex = tradingDays.indexOf(currentDate);
  const hasPrev = currentIndex > 0;
  const hasNext = currentIndex >= 0 && currentIndex < tradingDays.length - 1;
  const isLatestDate = currentDate === latestDate;

  const isBrokenBoard = useMemo(() => {
    if (!yesterdayData || !ladderData || ladderData.length === 0) return false;
    const todayMaxLevel = Math.max(...ladderData.map(item => item.level));
    const expectedLevel = yesterdayData.max_level + 1;
    return todayMaxLevel !== expectedLevel;
  }, [yesterdayData, ladderData]);

  const columns = [
    {
      title: '#',
      dataIndex: 'index',
      key: 'index',
      width: 40,
      align: 'center',
      render: (_, __, idx) => <span style={{ color: '#999', fontSize: 12 }}>{idx + 1}</span>
    },
    {
      title: '涨停时间',
      dataIndex: 'limit_up_time',
      key: 'limit_up_time',
      width: 80,
      align: 'center',
      render: (text) => (
        <Tag color="orange" style={{ margin: 0, fontWeight: 600 }}>{text}</Tag>
      )
    },
    {
      title: '股票',
      dataIndex: 'name',
      key: 'name',
      width: 140,
      render: (text, record) => (
        <Space size={4}>
          <Tooltip title={`查看K线 - ${text}`}>
            <Button
              type="link"
              size="small"
              style={{ padding: 0, fontWeight: 600, fontSize: 13 }}
              onClick={() => {
                setKlineVisible(true);
                setSelectedStock({ code: record.code, name: record.name });
              }}
            >
              {text}
            </Button>
          </Tooltip>
          <span style={{ color: '#999', fontSize: 11 }}>{record.code}</span>
        </Space>
      )
    },
    {
      title: '连板',
      dataIndex: 'levelLabel',
      key: 'levelLabel',
      width: 75,
      align: 'center',
      render: (text) => {
        const colorMap = {
          '2连板': '#f50', '3连板': '#ff4d4f', '4连板': '#ff7a45',
          '5连板': '#cf1322', '6连板': '#a8071a', '7连板': '#610b0b',
        };
        return (
          <Tag color={colorMap[text] || '#820014'} style={{ margin: 0, fontSize: 12, fontWeight: 600 }}>
            {text}
          </Tag>
        );
      }
    },
    {
      title: '涨停原因',
      dataIndex: 'reason',
      key: 'reason',
      width: 200,
      ellipsis: true,
      render: (text) => (
        <Tooltip title={text} placement="topLeft">
          <span style={{ color: '#666', fontSize: 12 }}>{text || '-'}</span>
        </Tooltip>
      )
    },
    {
      title: '封单',
      dataIndex: 'seal_amount_wan',
      key: 'seal_amount_wan',
      width: 90,
      align: 'right',
      render: (val) => {
        if (!val || val === 0) return <span style={{ color: '#999', fontSize: 12 }}>-</span>;
        const yi = val / 10000;
        return (
          <span style={{ color: '#cf1322', fontSize: 12, fontWeight: 500 }}>
            {yi.toFixed(2)}<span style={{ fontSize: 10 }}>亿</span>
          </span>
        );
      }
    },
    {
      title: '换手',
      dataIndex: 'turnover_rate',
      key: 'turnover_rate',
      width: 70,
      align: 'right',
      render: (val) => (
        <span style={{ color: '#666', fontSize: 12 }}>
          {val != null ? `${val.toFixed(2)}%` : '-'}
        </span>
      )
    },
    {
      title: '板块',
      dataIndex: 'block_name',
      key: 'block_name',
      width: 120,
      ellipsis: true,
      render: (text) => (
        <Tooltip title={text} placement="topLeft">
          <span style={{ color: '#1890ff', fontSize: 12 }}>{text || '-'}</span>
        </Tooltip>
      )
    },
    {
      title: '操作',
      key: 'action',
      width: 80,
      align: 'center',
      render: (_, record) => (
        <Button
          type="link"
          size="small"
          icon={<AimOutlined />}
          style={{ fontSize: 12, padding: 0 }}
          onClick={() => {
            setComparableContext({
              stockCode: record.code,
              stockName: record.name,
              blockName: record.block_name,
              reason: record.reason
            });
            setComparableVisible(true);
          }}
        >
          找对标
        </Button>
      )
    }
  ];

  if (!firstLoadDone.current && localLoading) {
    return (
      <div style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        minHeight: '400px'
      }}>
        <Spin size="large" description="加载中..." />
      </div>
    );
  }

  return (
    <div style={{ padding: isMobile ? 8 : 16 }}>
      <Card
        size="small"
        title={
          <Space wrap>
            <ClockCircleOutlined style={{ color: '#fa8c16', fontSize: 18 }} />
            <span style={{ fontWeight: 700, fontSize: isMobile ? 16 : 18, color: '#fa8c16' }}>
              盘中实时
            </span>
            <span style={{
              color: '#999', fontSize: 14, fontWeight: 400,
              borderLeft: '1px solid #e8e8e8', paddingLeft: 8
            }}>
              {currentDate ? dayjs(currentDate, 'YYYYMMDD').format('YYYY年MM月DD日') : '-'}
            </span>
            <Tag color="orange" style={{ fontSize: 12 }}>
              10点前涨停 · 2板以上
            </Tag>
            <Badge
              count={intradayStocks.length}
              style={{ backgroundColor: '#fa8c16' }}
              overflowCount={999}
            />
            {isBrokenBoard && (
              <Tag color="red" style={{ margin: 0 }}>断板日</Tag>
            )}
          </Space>
        }
        extra={
          <Space>
            <Button
              size="small"
              icon={<LeftOutlined />}
              disabled={!hasPrev}
              onClick={handlePrevDay}
            />
            <DatePicker
              size="small"
              value={currentDate ? dayjs(currentDate, 'YYYYMMDD') : null}
              onChange={handleDateChange}
              format="YYYYMMDD"
              allowClear={false}
              style={{ width: 130 }}
            />
            <Button
              size="small"
              icon={<RightOutlined />}
              disabled={!hasNext}
              onClick={handleNextDay}
            />
            <Tooltip title="手动刷新">
              <Button
                type="text"
                icon={<ReloadOutlined spin={localLoading} />}
                onClick={fetchData}
                loading={localLoading}
                size="small"
              />
            </Tooltip>
          </Space>
        }
        styles={{ body: { padding: isMobile ? '8px 4px' : '16px' } }}
      >
        {intradayStocks.length === 0 ? (
          <Empty description="当前无符合条件的股票" />
        ) : (
          <Table
            columns={columns}
            dataSource={intradayStocks}
            rowKey={(record) => record.code}
            size="small"
            pagination={false}
            scroll={{ x: isMobile ? 700 : 'max-content' }}
          />
        )}
      </Card>

      {klineVisible && selectedStock && (
        <StockKlineModal
          visible={klineVisible}
          stockCode={selectedStock.code}
          stockName={selectedStock.name}
          targetDate={currentDate}
          onClose={() => {
            setKlineVisible(false);
            setSelectedStock(null);
          }}
        />
      )}

      <ComparableStockModal
        visible={comparableVisible}
        onClose={() => {
          setComparableVisible(false);
          setComparableContext(null);
        }}
        dateStr={currentDate}
        context={comparableContext}
      />
    </div>
  );
};

export default IntradayRealtimePage;
