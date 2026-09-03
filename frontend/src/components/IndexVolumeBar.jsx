import React, { useState, useEffect, useRef } from 'react';
import { stockApi } from '../services/api';

/**
 * 沪深创三大指数成交量 + 全天预测
 * 显示: 指数名 | 当前成交额 | 较昨日预测全天增减%
 * 数据来源: GET /api/market/index-volume（mootdx）
 * 盘中每 60s 刷新
 */
const IndexVolumeBar = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const timerRef = useRef(null);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const response = await stockApi.getIndexVolume();
        if (!cancelled && response.data?.success) {
          setData(response.data.data || null);
          setError('');
        }
      } catch (e) {
        if (!cancelled) setError('指数行情获取失败');
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    load();
    // 盘中每 60s 刷新一次（成交额随交易变化）
    timerRef.current = setInterval(load, 60000);
    return () => { cancelled = true; clearInterval(timerRef.current); };
  }, []);

  if (loading) return null;
  if (!data || !data.items || data.items.length === 0) {
    return error ? null : null;
  }

  const fmtAmount = (v) => {
    if (v == null) return '--';
    const yi = v / 1e8;
    if (yi >= 10000) return (yi / 10000).toFixed(2) + '万亿';
    return yi.toFixed(0) + '亿';
  };

  // 增减金额：预测全天 - 昨日全天，显示 +XX亿 / -XX亿
  const fmtAmountChange = (it) => {
    const pred = it.predicted_amount;
    const yest = it.yesterday_amount;
    if (pred == null || yest == null) return '';
    const dif = pred - yest;
    const yi = dif / 1e8;
    const sign = yi > 0 ? '+' : (yi < 0 ? '-' : '');
    const abs = Math.abs(yi);
    const text = abs >= 10000 ? (abs / 10000).toFixed(2) + '万亿' : abs.toFixed(0) + '亿';
    return `${sign}${text}`;
  };

  const pctColor = (v) => {
    if (v == null) return '#999';
    return v >= 0 ? '#f5222d' : '#52c41a';
  };

  const changeColor = (it) => {
    const dif = (it.predicted_amount ?? 0) - (it.yesterday_amount ?? 0);
    if (it.predicted_amount == null || it.yesterday_amount == null) return '#999';
    return dif >= 0 ? '#f5222d' : '#52c41a';
  };

  return (
    <div style={{
      display: 'flex',
      flexWrap: 'wrap',
      alignItems: 'center',
      gap: '6px 16px',
      marginBottom: 12,
      padding: '8px 12px',
      background: '#fff',
      borderRadius: 8,
      border: '1px solid #f0f0f0',
      boxShadow: '0 1px 4px rgba(0,0,0,0.04)',
      fontSize: 12,
    }}>
      <span style={{ color: '#595959', fontWeight: 600, whiteSpace: 'nowrap' }}>
        指数成交
      </span>
      {data.items.map((it) => (
        <div key={it.code} style={{ display: 'flex', alignItems: 'baseline', gap: 6, whiteSpace: 'nowrap' }}>
          <span style={{ color: '#333', fontWeight: 600 }}>{it.short}</span>
          <span style={{ color: '#595959' }}>{fmtAmount(it.amount)}</span>
          {it.predicted_amount != null && it.yesterday_amount != null ? (
            <span style={{ color: changeColor(it), fontWeight: 600 }}>
              {data.trading ? '预测' : ''}{fmtAmountChange(it)}
            </span>
          ) : (
            <span style={{ color: '#bfbfbf' }}>待开盘</span>
          )}
        </div>
      ))}
      {!data.trading && data.items[0]?.progress === 1 && (
        <span style={{ color: '#999', marginLeft: 'auto' }}>已收盘</span>
      )}
    </div>
  );
};

export default IndexVolumeBar;
