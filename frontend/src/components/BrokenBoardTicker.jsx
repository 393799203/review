import React, { useEffect, useState, useLayoutEffect, useRef } from 'react';
import { Tooltip } from 'antd';
import { FireOutlined } from '@ant-design/icons';
import { stockApi } from '../services/api';

/**
 * 断板强势股展示栏（整行分页切换，不做内容内滚动）
 * 展示以当前选择日期为准、前7天内出现3连板及以上、断板后2天内回撤不超过10%的股票名称
 * 内容一行放得下时静止展示；超过一行宽度时按行分页，定时整行切换。
 */
const BrokenBoardTicker = ({ currentDate, onStockClick }) => {
  const [items, setItems] = useState([]);
  const [pages, setPages] = useState([]);   // 按可视宽度分好页的 item 组
  const [page, setPage] = useState(0);
  const [paused, setPaused] = useState(false); // 悬停暂停轮播
  const viewportRef = useRef(null);
  const measureRef = useRef(null);
  const touchStartX = useRef(null);
  const touchStartY = useRef(null);

  // 触摸滑动切页：横向滑动手势切上一页/下一页
  const handleTouchStart = (e) => {
    const t = e.touches && e.touches[0];
    if (!t) return;
    touchStartX.current = t.clientX;
    touchStartY.current = t.clientY;
  };

  const handleTouchEnd = (e) => {
    if (touchStartX.current == null) return;
    const t = e.changedTouches && e.changedTouches[0];
    if (!t) return;
    const deltaX = t.clientX - touchStartX.current;
    const deltaY = t.clientY - (touchStartY.current || t.clientY);
    touchStartX.current = null;
    touchStartY.current = null;
    if (pages.length <= 1) return;
    // 仅识别横向滑动（|dx| > 40 且明显大于纵向），避免与页面纵向滚动冲突
    if (Math.abs(deltaX) < 40 || Math.abs(deltaX) <= Math.abs(deltaY)) return;
    if (deltaX < 0) {
      setPage(p => (p + 1) % pages.length);                  // 左滑 → 下一页
    } else {
      setPage(p => (p - 1 + pages.length) % pages.length);   // 右滑 → 上一页
    }
  };

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

  // items 变化时测量可视宽度并分页（一行放得下的归为一页）
  useLayoutEffect(() => {
    if (!items.length) {
      setPages([]);
      return;
    }
    const measure = measureRef.current;
    const viewport = viewportRef.current;
    if (!measure || !viewport || viewport.clientWidth <= 0) {
      setPages([items]);
      setPage(0);
      return;
    }
    const avail = viewport.clientWidth;
    const children = Array.from(measure.children);
    const groups = [];
    let cur = [];
    let curW = 0;
    children.forEach((el, idx) => {
      const w = el.offsetWidth + 28; // item 左右 margin 14px 各一
      if (cur.length > 0 && curW + w > avail) {
        groups.push(cur);
        cur = [];
        curW = 0;
      }
      cur.push(idx);
      curW += w;
    });
    if (cur.length > 0) groups.push(cur);

    const g = groups.length
      ? groups.map(grp => grp.map(i => items[i]))
      : [items];
    setPages(g);
    setPage(0);
  }, [items]);

  // 整行轮播：超过一页时 3.5s 自动切下一页。
  // 页面切换(page)、悬停暂停/恢复(paused)、数据重分页(pages)任一变化都会
  // 清除旧计时并重新开始，保证：点击切换后重新计时、悬停停止计时、离开后重新计时。
  useEffect(() => {
    if (pages.length <= 1 || paused) return undefined;
    const t = setTimeout(() => {
      setPage(p => (p + 1) % pages.length);
    }, 3500);
    return () => clearTimeout(t);
  }, [pages, page, paused]);

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

  const current = pages[page] || items;

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
      position: 'relative',
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
        <span>断板</span>
      </div>
      <div
        ref={viewportRef}
        className="broken-board-ticker-viewport"
        onMouseEnter={() => setPaused(true)}
        onMouseLeave={() => setPaused(false)}
        onTouchStart={handleTouchStart}
        onTouchEnd={handleTouchEnd}
      >
        <div className="broken-board-ticker-row">
          {current.map(item => renderItem(item, 'v'))}
        </div>
      </div>
      {pages.length > 1 && (
        <div className="broken-board-ticker-dots">
          {pages.map((_, i) => (
            <span
              key={i}
              className={`broken-board-ticker-dot${i === page ? ' active' : ''}`}
              onClick={() => setPage(i)}
            />
          ))}
        </div>
      )}
      {/* 测量行：不可见，仅用于计算一行容量 */}
      <div
        ref={measureRef}
        aria-hidden
        style={{
          position: 'absolute',
          left: 0,
          top: 0,
          visibility: 'hidden',
          whiteSpace: 'nowrap',
          pointerEvents: 'none',
          zIndex: -1,
        }}
      >
        {items.map((item, i) => renderItem(item, 'm' + i))}
      </div>
      <style>{`
        .broken-board-ticker-viewport {
          flex: 1;
          overflow: hidden;
          min-width: 0;
          height: 32px;
          display: flex;
          align-items: center;
        }
        .broken-board-ticker-row {
          display: inline-flex;
          align-items: center;
          white-space: nowrap;
          padding: 6px 0;
        }
        .broken-board-ticker-dots {
          flexShrink: 0;
          display: flex;
          align-items: center;
          gap: 4px;
          padding: 0 10px;
        }
        .broken-board-ticker-dot {
          width: 5px;
          height: 5px;
          border-radius: 50%;
          background: #ffccc7;
          cursor: pointer;
          transition: background 0.2s, width 0.2s;
        }
        .broken-board-ticker-dot.active {
          background: #fa8c16;
          width: 14px;
          border-radius: 3px;
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
