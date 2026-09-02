import React, { useEffect, useState } from 'react';
import { Tooltip } from 'antd';
import { FireOutlined } from '@ant-design/icons';
import { stockApi } from '../services/api';

/**
 * 断板强势股滚动栏
 * 展示以当前选择日期为准、前7天内出现3连板及以上、断板后2天内回撤不超过10%的股票名称
 */
const BrokenBoardTicker = ({ currentDate, onStockClick }) => {
  const [items, setItems] = useState([]);

  useEffect(() => {
    if (!currentDate) return;
    let cancelled = false;
    stockApi.getBrokenBoardStrong(currentDate)
      .then(res => {
        if (!cancelled && res.data?.success) {
          setItems(res.data.data?.items || []);
        }
      })
      .catch(() => { /* 静默失败，不干扰主页面 */ });
    return () => { cancelled = true; };
  }, [currentDate]);

  if (items.length === 0) return null;

  const renderItem = (item, keyPrefix) => (
    <Tooltip
      key={`${keyPrefix}-${item.code}`}
      title={
        <div>
          <div>{item.name}（{item.code}）</div>
          <div>{item.peak_days}连板 · 断板日 {item.break_date}</div>
          <div>基准价 ¥{item.base_price} · 断板后最大回撤 {item.max_drawdown_pct}%（已观察{item.days_checked}天）</div>
        </div>
      }
      placement="top"
    >
      <span
        className="broken-board-ticker-item"
        onClick={() => onStockClick && onStockClick(item.code, item.name)}
      >
        {item.name}
        <span className="broken-board-ticker-badge">{item.peak_days}板</span>
      </span>
    </Tooltip>
  );

  const duration = Math.max(18, items.length * 5);

  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      marginBottom: 12,
      borderRadius: 8,
      overflow: 'hidden',
      background: 'linear-gradient(90deg, #fff1f0 0%, #fff7e6 100%)',
      border: '1px solid #ffa39e',
      boxShadow: '0 1px 4px rgba(0,0,0,0.06)',
    }}>
      <div style={{
        flexShrink: 0,
        display: 'flex',
        alignItems: 'center',
        gap: 4,
        padding: '6px 12px',
        background: 'linear-gradient(135deg, #f5222d 0%, #fa8c16 100%)',
        color: '#fff',
        fontSize: 12,
        fontWeight: 'bold',
        alignSelf: 'stretch',
      }}>
        <FireOutlined />
        <span>断板强势</span>
      </div>
      <div className="broken-board-ticker-viewport">
        <div
          className="broken-board-ticker-track"
          style={{ animationDuration: `${duration}s` }}
        >
          {items.map(item => renderItem(item, 'a'))}
          {items.map(item => renderItem(item, 'b'))}
        </div>
      </div>
      <style>{`
        .broken-board-ticker-viewport {
          flex: 1;
          overflow: hidden;
          min-width: 0;
        }
        .broken-board-ticker-track {
          display: inline-flex;
          align-items: center;
          white-space: nowrap;
          padding: 6px 0;
          animation-name: brokenBoardTickerScroll;
          animation-timing-function: linear;
          animation-iteration-count: infinite;
          will-change: transform;
        }
        .broken-board-ticker-viewport:hover .broken-board-ticker-track {
          animation-play-state: paused;
        }
        @keyframes brokenBoardTickerScroll {
          from { transform: translateX(0); }
          to { transform: translateX(-50%); }
        }
        .broken-board-ticker-item {
          display: inline-flex;
          align-items: center;
          gap: 4px;
          margin: 0 14px;
          font-size: 13px;
          font-weight: 600;
          color: #cf1322;
          cursor: pointer;
          transition: transform 0.15s;
        }
        .broken-board-ticker-item:hover {
          transform: scale(1.08);
          text-decoration: underline;
        }
        .broken-board-ticker-badge {
          font-size: 10px;
          font-weight: normal;
          color: #fff;
          background: #fa8c16;
          border-radius: 8px;
          padding: 0 6px;
          line-height: 16px;
        }
      `}</style>
    </div>
  );
};

export default BrokenBoardTicker;
