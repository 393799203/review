import React, { useState, useEffect } from 'react';
import { Layout, Menu, DatePicker, Button, Switch } from 'antd';
import { StockOutlined, LineChartOutlined, SettingOutlined, ReloadOutlined } from '@ant-design/icons';
import { useNavigate, useLocation } from 'react-router-dom';
import { useGlobal } from '../contexts/GlobalContext';
import dayjs from 'dayjs';

const { Sider, Content, Header } = Layout;

const MainLayout = ({ children }) => {
  const navigate = useNavigate();
  const location = useLocation();
  const [isMobile, setIsMobile] = useState(false);
  const [showFirstBoard, setShowFirstBoard] = useState(true);
  
  const {
    currentDate,
    latestDate,
    tradingDays,
    loading,
    handleDateChange,
    handlePrevDay,
    handleNextDay,
    refreshCurrentData,
  } = useGlobal();

  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 768);
    };
    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  useEffect(() => {
    if (currentDate && latestDate) {
      const isLatest = currentDate === latestDate;
      setShowFirstBoard(!isLatest);
    }
  }, [currentDate, latestDate]);

  const menuItems = [
    {
      key: '/',
      icon: <StockOutlined />,
      label: '涨停天梯',
    },
    {
      key: '/watchlist',
      icon: <LineChartOutlined />,
      label: '自选回溯',
    },
    {
      key: '/settings',
      icon: <SettingOutlined />,
      label: '设置',
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
    if (isMobile) {
      return (
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          {isLadderPage && (
            <Switch 
              checked={showFirstBoard} 
              onChange={setShowFirstBoard} 
              size="small"
              checkedChildren="首板"
              unCheckedChildren="首板"
            />
          )}
          <Button onClick={handlePrevDay} size="small">前</Button>
          <DatePicker
            value={currentDate ? dayjs(currentDate, 'YYYYMMDD') : null}
            onChange={handleDateChange}
            format="YYYYMMDD"
            placeholder="日期"
            disabledDate={disabledDate}
            size="small"
            style={{ width: 110 }}
          />
          {!isLatestDate && <Button onClick={handleNextDay} size="small">后</Button>}
          <Button 
            type="primary" 
            icon={<ReloadOutlined />} 
            size="small"
            onClick={refreshCurrentData}
            loading={loading}
          />
        </div>
      );
    }

    return (
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        {isLadderPage && (
          <>
            <span>显示首板:</span>
            <Switch checked={showFirstBoard} onChange={setShowFirstBoard} />
          </>
        )}
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
        <Button type="primary" icon={<ReloadOutlined />} onClick={refreshCurrentData}>
          刷新数据
        </Button>
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
          <div style={{ color: '#fff', fontSize: 16, fontWeight: 'bold', display: 'flex', alignItems: 'center', gap: 8 }}>
            <img src="/favicon.svg" alt="logo" style={{ width: 24, height: 24 }} />
            复盘系统
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
          {typeof children === 'function' ? children({ showFirstBoard }) : children}
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
        }}
      >
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
          复盘系统
        </div>
        {menuContent}
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
          {typeof children === 'function' ? children({ showFirstBoard }) : children}
        </Content>
      </Layout>
    </Layout>
  );
};

export default MainLayout;
