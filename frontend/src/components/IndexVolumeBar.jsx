import React, { useState, useEffect } from 'react';
import { stockApi } from '../services/api';

/**
 * 沪深创三大指数成交量 + 全天预测（紧凑单行，自适应换行）
 * 数据来源: GET /api/market/index-volume?date=YYYYMMDD（mootdx）
 * 跟随所选日期: 传入 currentDate，历史日期返回该日实际成交额
 * 刷新: 跟随天梯页 refreshKey，盘中每 60s 兜底刷新
 */
const RED = '#f5222d';
const GREEN = '#52c41a';
const GRAY = '#8c8c8c';

const IndexVolumeBar = ({ refreshKey = 0, currentDate = '' }) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const response = await stockApi.getIndexVolume(currentDate);
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
    const timer = setInterval(load, 60000);
    return () => { cancelled = true; clearInterval(timer); };
  }, [refreshKey, currentDate]);

  if (loading && !data) return null;
  if (error && !data) return null;
  if (!data || !data.items || data.items.length === 0) return null;

  const fmtAmount = (v) => {
    if (v == null) return '--';
    const yi = v / 1e8;
    if (yi >= 10000) return (yi / 10000).toFixed(2) + '万亿';
    return yi.toFixed(0) + '亿';
  };

  const fmtChange = (v) => {
    if (v == null) return '--';
    const yi = v / 1e8;
    const sign = yi > 0 ? '+' : (yi < 0 ? '-' : '');
    const abs = Math.abs(yi);
    const text = abs >= 10000 ? (abs / 10000).toFixed(2) + '万亿' : abs.toFixed(0) + '亿';
    return `${sign}${text}`;
  };

  const trading = !!data.trading;
  const isHistory = !!data.is_history;
  const changeLabel = isHistory ? '较前日' : trading ? '预测' : '较昨日';

  const sum = (k) => data.items.reduce((s, it) => s + (it[k] || 0), 0);
  const cur = sum('amount');
  const pred = sum('predicted_amount');
  const yest = sum('yesterday_amount');
  const dif = pred - yest;
  const target = 25000e8; // 2.5万亿
  const gap = target - pred;
  const gapYi = gap / 1e8;
  const over = gapYi <= 0;
  const caution = pred < target;
  const diffText = `${dif >= 0 ? '+' : ''}${(dif / 1e8).toFixed(0)}亿`;
  const gapText = over ? `超2.5万亿 ${(-gapYi).toFixed(0)}亿` : `距2.5万亿 ${gapYi.toFixed(0)}亿`;

  const statusBadge = () => {
    if (isHistory) {
      return <span style={badgeStyle(GRAY, '#f5f5f5')}>历史</span>;
    }
    if (trading) {
      return (
        <span style={{ ...badgeStyle(RED, '#fff1f0'), display: 'inline-flex', alignItems: 'center', gap: 5 }}>
          <span style={{ width: 6, height: 6, borderRadius: '50%', background: RED }} />
          盘中
        </span>
      );
    }
    return <span style={badgeStyle(GRAY, '#f5f5f5')}>已收盘</span>;
  };

  const badgeStyle = (color, bg) => ({
    fontSize: 11, color, background: bg, padding: '1px 8px', borderRadius: 12,
    fontWeight: 600, whiteSpace: 'nowrap', lineHeight: '18px',
  });

  const renderItem = (it) => {
    const hasChange = it.predicted_amount != null && it.yesterday_amount != null;
    const diff = (it.predicted_amount ?? 0) - (it.yesterday_amount ?? 0);
    const change = fmtChange(hasChange ? diff : null);
    return (
      <div key={it.code} style={{ display: 'flex', alignItems: 'baseline', gap: 5, whiteSpace: 'nowrap' }}>
        <span style={{ fontWeight: 600, color: '#333' }}>{it.short}</span>
        <span style={{ fontWeight: 700, color: '#262626' }}>{fmtAmount(it.amount)}</span>
        <span style={{ fontWeight: 600, color: hasChange ? (diff >= 0 ? RED : GREEN) : GRAY }}>
          {hasChange ? `${changeLabel} ${change}` : '待开盘'}
        </span>
      </div>
    );
  };

  return (
    <div style={{
      display: 'flex', flexWrap: 'wrap', alignItems: 'center',
      gap: '4px 14px', padding: '6px 12px', marginBottom: 12,
      background: '#fff', borderRadius: 8, border: '1px solid #f0f0f0',
      boxShadow: '0 1px 4px rgba(0,0,0,0.04)', fontSize: 12, lineHeight: '22px',
    }}>
      <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontWeight: 700, color: '#1f2329' }}>
        <span style={{ width: 3, height: 14, borderRadius: 2, background: 'linear-gradient(180deg,#f5222d,#fa8c16)' }} />
        指数成交
      </span>
      <span style={badgeStyle('#595959', '#f5f5f5')}>{data.date}</span>
      {statusBadge()}

      {data.items.map(renderItem)}

      {!!cur && (
        <div style={{ display: 'flex', alignItems: 'baseline', gap: '6px 12px', marginLeft: 'auto', whiteSpace: 'nowrap', flexWrap: 'wrap' }}>
          <span style={{ fontWeight: 700, color: '#262626' }}>合计 {fmtAmount(cur)}</span>
          <span style={{ fontWeight: 600, color: dif >= 0 ? RED : GREEN }}>{isHistory ? '较前日' : '较昨日'} {diffText}</span>
          <span style={{ color: over ? RED : '#595959', fontWeight: over ? 700 : 400 }}>{gapText}</span>
          {caution && (
            <span style={{ color: RED, fontWeight: 700, background: '#fff1f0', padding: '0 6px', borderRadius: 4 }}>
              ⚠️ 谨慎
            </span>
          )}
        </div>
      )}
    </div>
  );
};

export default IndexVolumeBar;
