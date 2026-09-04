import React, { useState, useEffect } from 'react';
import { stockApi } from '../services/api';

/**
 * 沪深创三大指数成交量 + 全天预测（紧凑单行，H5 压缩至 1~2 行）
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
  const [isMobile, setIsMobile] = useState(() => window.innerWidth < 768);

  useEffect(() => {
    const check = () => setIsMobile(window.innerWidth < 768);
    window.addEventListener('resize', check);
    return () => window.removeEventListener('resize', check);
  }, []);

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
  const caution = pred < target;       // 低于 2.5 万亿 → 谨慎
  const hot = pred >= 30000e8;         // 达到/超过 3 万亿 → 火爆
  const diffText = `${dif >= 0 ? '+' : ''}${(dif / 1e8).toFixed(0)}亿`;
  const gapText = over ? `超2.5万亿 ${(-gapYi).toFixed(0)}亿` : `距2.5万亿 ${gapYi.toFixed(0)}亿`;

  const badgeStyle = (color, bg) => ({
    fontSize: 11, color, background: bg, padding: '1px 8px', borderRadius: 12,
    fontWeight: 600, whiteSpace: 'nowrap', lineHeight: '18px',
  });

  const statusBadge = () => {
    if (isHistory) return <span style={badgeStyle(GRAY, '#f5f5f5')}>历史</span>;
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

  const barStyle = {
    display: 'flex', flexWrap: 'wrap', alignItems: 'center',
    gap: isMobile ? '3px 8px' : '4px 14px',
    padding: isMobile ? '4px 10px' : '6px 12px',
    marginBottom: 12,
    background: '#fff', borderRadius: 8, border: '1px solid #f0f0f0',
    boxShadow: '0 1px 4px rgba(0,0,0,0.04)',
    fontSize: isMobile ? 11 : 12, lineHeight: isMobile ? '18px' : '22px',
  };

  const title = (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontWeight: 700, color: '#1f2329' }}>
      <span style={{ width: 3, height: 14, borderRadius: 2, background: 'linear-gradient(180deg,#f5222d,#fa8c16)' }} />
      市场成交
    </span>
  );

  // H5：只显示 短名+金额，汇总单行；桌面端保留单指数增减
  const renderItem = (it) => {
    const hasChange = it.predicted_amount != null && it.yesterday_amount != null;
    const diff = (it.predicted_amount ?? 0) - (it.yesterday_amount ?? 0);
    const change = fmtChange(hasChange ? diff : null);
    return (
      <span key={it.code} style={{ display: 'inline-flex', alignItems: 'baseline', gap: 4, whiteSpace: 'nowrap' }}>
        <span style={{ fontWeight: 600, color: '#333' }}>{it.short}</span>
        <span style={{ fontWeight: 700, color: '#262626' }}>{fmtAmount(it.amount)}</span>
        {!isMobile && (
          <span style={{ fontWeight: 600, color: hasChange ? (diff >= 0 ? RED : GREEN) : GRAY }}>
            {hasChange ? `${changeLabel} ${change}` : '待开盘'}
          </span>
        )}
      </span>
    );
  };

  const summary = !!cur && (
    <span style={{
      display: 'inline-flex', alignItems: 'baseline', gap: isMobile ? '4px 8px' : '6px 12px',
      marginLeft: 'auto', whiteSpace: 'nowrap', flexWrap: 'wrap',
      ...(isMobile ? { flexBasis: '100%' } : {}),
    }}>
      <span style={{ fontWeight: 700, color: '#262626' }}>合计 {fmtAmount(cur)}</span>
      <span style={{ fontWeight: 600, color: dif >= 0 ? RED : GREEN }}>{isHistory ? '较前日' : '较昨日'} {diffText}</span>
      <span style={{ color: over ? RED : GREEN, fontWeight: over ? 700 : 600 }}>{gapText}</span>
      {hot && (
        <span style={{ color: '#fa8c16', fontWeight: 700, background: '#fff7e6', padding: '0 6px', borderRadius: 4 }}>
          🔥 火爆
        </span>
      )}
      {caution && (
        <span style={{ color: RED, fontWeight: 700, background: '#fff1f0', padding: '0 6px', borderRadius: 4 }}>
          ⚠️ 谨慎
        </span>
      )}
    </span>
  );

  return (
    <div style={barStyle}>
      {title}
      {!isMobile && <span style={badgeStyle('#595959', '#f5f5f5')}>{data.date}</span>}
      {!isMobile && statusBadge()}

      {data.items.map(renderItem)}

      {summary}
    </div>
  );
};

export default IndexVolumeBar;
