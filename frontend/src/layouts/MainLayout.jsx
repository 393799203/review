import React, { useState, useEffect } from 'react';
import { Layout, Menu, DatePicker, Button, Switch, Select, Popover, Avatar } from 'antd';
import { StockOutlined, StarOutlined, BarChartOutlined, ReloadOutlined, UserOutlined, LogoutOutlined, LoginOutlined } from '@ant-design/icons';
import { useNavigate, useLocation } from 'react-router-dom';
import { useGlobal } from '../contexts/GlobalContext';
import { useAuth } from '../contexts/AuthContext';
import dayjs from 'dayjs';

const { Sider, Content, Header } = Layout;

const MainLayout = ({ children }) => {
  const navigate = useNavigate();
  const location = useLocation();
  const [isMobile, setIsMobile] = useState(false);
  const [popoverVisible, setPopoverVisible] = useState(false);

  const { user, logout, isAuthenticated } = useAuth();

  const {
    currentDate,
    latestDate,
    tradingDays,
    loading,
    autoRefresh,
    setAutoRefresh,
    refreshInterval,
    setRefreshInterval,
    smartMode,
    setSmartMode,
    showFirstBoard,
    setShowFirstBoard,
    setAutoRefreshCallback,
    loadPageSettings,
    handleDateChange,
    handlePrevDay,
    handleNextDay,
    refreshCurrentData,
    refreshWatchlistPrices,
    refreshStatistics,
  } = useGlobal();

  useEffect(() => {
    const pageMap = {
      '/': 'ladder',
      '/watchlist': 'watchlist',
      '/statistics': 'statistics',
    };

    const page = pageMap[location.pathname] || 'ladder';
    loadPageSettings(page);

    if (location.pathname === '/') {
      setAutoRefreshCallback(refreshCurrentData);
    } else if (location.pathname === '/watchlist') {
      setAutoRefreshCallback(refreshWatchlistPrices);
    } else if (location.pathname === '/statistics') {
      setAutoRefreshCallback(refreshStatistics);
    }

    return () => {
      setAutoRefreshCallback(null);
    };
  }, [location.pathname]);

  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 768);
    };
    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  const menuItems = [
    {
      key: '/',
      icon: <StockOutlined />,
      label: '涨停天梯',
    },
    {
      key: '/watchlist',
      icon: <StarOutlined />,
      label: '自选回溯',
    },
    {
      key: '/statistics',
      icon: <BarChartOutlined />,
      label: '数据统计',
    },
  ];

  const handleMenuClick = ({ key }) => {
    navigate(key);
  };

  const disabledDate = (current) => {
    if (!current) {
      return true;
    }
    const dateStr = current.format('YYYYMMDD');
    return !tradingDays.includes(dateStr);
  };

  const isLatestDate = currentDate === latestDate;
  const isLadderPage = location.pathname === '/';

  const renderHeaderRight = () => {
    const isWatchlistPage = location.pathname === '/watchlist';
    const isStatisticsPage = location.pathname === '/statistics';

    const settingsContent = (
      <div style={{ width: isMobile ? 200 : 250 }}>
        <div style={{ marginBottom: 12 }}>
          <div style={{ marginBottom: 8, fontWeight: 500 }}>刷新时段</div>
          <Select
            value={smartMode ? 'trading' : 'all'}
            onChange={(value) => setSmartMode(value === 'trading')}
            style={{ width: '100%' }}
            options={[
              { value: 'trading', label: '交易时段 (9:15-11:30, 13:00-15:00)' },
              { value: 'all', label: '全天' },
            ]}
          />
        </div>

        <div>
          <div style={{ marginBottom: 8, fontWeight: 500 }}>刷新频率</div>
          <Select
            value={refreshInterval}
            onChange={setRefreshInterval}
            style={{ width: '100%' }}
            options={[
              { value: 10, label: '10秒' },
              { value: 30, label: '30秒' },
              { value: 60, label: '1分钟' },
              { value: 300, label: '5分钟' },
            ]}
          />
        </div>
      </div>
    );

    const handleAutoRefreshChange = (checked) => {
      setAutoRefresh(checked);
      if (!checked) {
        setPopoverVisible(false);
      }
    };

    const getRefreshHandler = () => {
      if (isWatchlistPage) return refreshWatchlistPrices;
      if (isStatisticsPage) return refreshStatistics;
      return refreshCurrentData;
    };

    if (isMobile) {
      return (
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          {isLadderPage && (
            <>
              <Button onClick={handlePrevDay} size="small">前</Button>
              <DatePicker
                value={currentDate ? dayjs(currentDate, 'YYYYMMDD') : null}
                onChange={handleDateChange}
                format="YYYYMMDD"
                placeholder="日期"
                disabledDate={disabledDate}
                size="small"
                style={{ width: 100 }}
              />
              {!isLatestDate && <Button onClick={handleNextDay} size="small">后</Button>}
              <Switch
                checked={showFirstBoard}
                onChange={setShowFirstBoard}
                size="small"
                checkedChildren="首"
                unCheckedChildren="首"
                style={{ marginLeft: 4 }}
              />
            </>
          )}
          <Button
            type="primary"
            icon={<ReloadOutlined />}
            size="small"
            onClick={getRefreshHandler()}
            loading={loading}
          />

          <Popover
            content={settingsContent}
            title="设置"
            trigger="click"
            placement="bottomRight"
            open={popoverVisible}
            onOpenChange={setPopoverVisible}
          >
            <Switch
              checked={autoRefresh}
              onChange={handleAutoRefreshChange}
              size="small"
              checkedChildren="自"
              unCheckedChildren="自"
            />
          </Popover>
        </div>
      );
    }

    return (
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        {isLadderPage && (
          <>
            <Button onClick={handlePrevDay}>前一天</Button>
            <DatePicker
              value={currentDate ? dayjs(currentDate, 'YYYYMMDD') : null}
              onChange={handleDateChange}
              format="YYYYMMDD"
              placeholder="选择日期"
              disabledDate={disabledDate}
              placement="bottomLeft"
            />
            {!isLatestDate && <Button onClick={handleNextDay}>后一天</Button>}
            <span style={{ marginLeft: 8 }}>显示首板:</span>
            <Switch checked={showFirstBoard} onChange={setShowFirstBoard} />
          </>
        )}

        <Button type="primary" icon={<ReloadOutlined />} onClick={getRefreshHandler()}>
          {isWatchlistPage ? '更新价格' : '刷新数据'}
        </Button>

        <Popover
          content={settingsContent}
          title="设置"
          trigger="click"
          placement="bottomRight"
          open={autoRefresh && popoverVisible}
          onOpenChange={setPopoverVisible}
        >
          <Switch
            checked={autoRefresh}
            onChange={handleAutoRefreshChange}
            checkedChildren="自动"
            unCheckedChildren="手动"
          />
        </Popover>
      </div>
    );
  };

  const menuContent = (
    <Menu
      mode="inline"
      selectedKeys={[location.pathname]}
      items={menuItems}
      onClick={handleMenuClick}
      style={{ borderRight: 0 }}
      theme="dark"
    />
  );

  if (isMobile) {
    return (
      <Layout style={{ minHeight: '100vh' }}>
        <Header
          style={{
            background: '#001529',
            padding: '0 12px',
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            zIndex: 100,
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            height: 48,
          }}
        >
          <div style={{ color: '#fff', fontSize: 14, fontWeight: 'bold', display: 'flex', alignItems: 'center', gap: 8 }}>
            <img src="/favicon.svg" alt="logo" style={{ width: 22, height: 22 }} />
            节节高
          </div>
          {renderHeaderRight()}
        </Header>
        <Content
          style={{
            margin: '48px 0 56px 0',
            padding: 8,
            background: '#f5f5f5',
            minHeight: 'calc(100vh - 104px)',
            overflow: 'auto',
          }}
        >
          {children}
        </Content>
        <div
          style={{
            position: 'fixed',
            bottom: 0,
            left: 0,
            right: 0,
            background: '#fff',
            borderTop: '1px solid #f0f0f0',
            zIndex: 100,
            display: 'flex',
            justifyContent: 'space-around',
            alignItems: 'center',
            height: 56,
          }}
        >
          {menuItems.map(item => (
            <div
              key={item.key}
              onClick={() => navigate(item.key)}
              style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                flex: 1,
                height: '100%',
                cursor: 'pointer',
                color: location.pathname === item.key ? '#1890ff' : '#666',
                transition: 'color 0.3s',
              }}
            >
              <div style={{ fontSize: 20 }}>{item.icon}</div>
              <div style={{ fontSize: 10, marginTop: 2 }}>{item.label}</div>
            </div>
          ))}
        </div>
      </Layout>
    );
  }

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider
        width={200}
        style={{
          background: '#001529',
          position: 'fixed',
          left: 0,
          top: 0,
          bottom: 0,
          overflow: 'auto',
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        <div style={{ flex: 1 }}>
          <div
            style={{
              height: 64,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'flex-start',
              color: '#fff',
              fontSize: 18,
              fontWeight: 'bold',
              paddingLeft: 20,
              gap: 8,
            }}
          >
            <img src="/favicon.svg" alt="logo" style={{ width: 28, height: 28 }} />
            节节高
          </div>
          {menuContent}
        </div>

        <div
          style={{
            position: 'fixed',
            bottom: 0,
            left: 0,
            width: 200,
            borderTop: '1px solid rgba(255,255,255,0.1)',
            padding: '12px 16px',
            background: '#001529',
          }}
        >
          {isAuthenticated && user ? (
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <Avatar
                size={32}
                icon={<UserOutlined />}
                style={{ backgroundColor: '#1890ff' }}
              >
                {user.nickname?.[0] || user.username?.[0] || 'U'}
              </Avatar>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{
                  color: '#fff',
                  fontSize: 13,
                  fontWeight: 500,
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap'
                }}>
                  {user.nickname || user.username}
                </div>
                <div style={{
                  color: 'rgba(255,255,255,0.45)',
                  fontSize: 11,
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap'
                }}>
                  {user.email}
                </div>
              </div>
              <Button
                type="text"
                icon={<LogoutOutlined />}
                onClick={() => {
                  logout();
                  navigate('/login');
                }}
                style={{ color: 'rgba(255,255,255,0.65)' }}
                size="small"
              />
            </div>
          ) : (
            <Button
              type="primary"
              icon={<LoginOutlined />}
              onClick={() => navigate('/login')}
              block
              size="small"
            >
              登录
            </Button>
          )}
        </div>
      </Sider>
      <Layout style={{ marginLeft: 200 }}>
        <Header
          style={{
            background: '#fff',
            padding: '0 24px',
            borderBottom: '1px solid #f0f0f0',
            position: 'fixed',
            top: 0,
            right: 0,
            left: 200,
            zIndex: 1,
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}
        >
          <div style={{ fontSize: 18, fontWeight: 'bold', display: 'flex', alignItems: 'center', gap: 8 }}>
            <img src="/favicon.svg" alt="logo" style={{ width: 28, height: 28 }} />
            A股涨停复盘系统
          </div>
          {renderHeaderRight()}
        </Header>
        <Content
          style={{
            margin: '88px 24px 24px',
            padding: 24,
            background: '#fff',
            borderRadius: 8,
            minHeight: 280,
          }}
        >
          {children}
        </Content>
      </Layout>
    </Layout>
  );
};

export default MainLayout;