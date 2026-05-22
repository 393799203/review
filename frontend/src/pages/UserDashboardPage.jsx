import React, { useState, useEffect } from 'react';
import { Card, Table, Tag, Spin, message, Statistic, Row, Col, Badge } from 'antd';
import { UserOutlined, TeamOutlined, LoginOutlined, ClockCircleOutlined, EyeOutlined } from '@ant-design/icons';
import api from '../services/api';

let loadUsersRef = null;

export const refreshUserDashboard = () => {
  if (loadUsersRef) {
    loadUsersRef();
  }
};

const UserDashboardPage = () => {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [onlineCount, setOnlineCount] = useState(0);
  const [isMobile, setIsMobile] = useState(window.innerWidth < 768);

  useEffect(() => {
    const handleResize = () => {
      setIsMobile(window.innerWidth < 768);
    };
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  useEffect(() => {
    loadUsers();
  }, []);

  const loadUsers = async () => {
    setLoading(true);
    try {
      const response = await api.get('/admin/user-stats');
      
      if (response.data.success) {
        setUsers(response.data.data.users || []);
        setOnlineCount(response.data.data.online_count || 0);
      } else {
        message.error('加载用户数据失败');
      }
    } catch (error) {
      message.error('加载用户数据失败：' + (error.response?.data?.error || error.message));
    } finally {
      setLoading(false);
    }
  };

  loadUsersRef = loadUsers;

  const getRoleColor = (role) => {
    const colors = {
      'admin': 'red',
      'vip': 'gold',
      'user': 'blue',
      'guest': 'default'
    };
    return colors[role] || 'default';
  };

  const getRoleText = (role) => {
    const texts = {
      'admin': '管理员',
      'vip': 'VIP用户',
      'user': '普通用户',
      'guest': '访客'
    };
    return texts[role] || role;
  };

  const columns = [
    {
      title: '状态',
      dataIndex: 'is_online',
      key: 'is_online',
      width: 70,
      fixed: isMobile ? 'left' : false,
      render: (is_online) => (
        <Badge 
          status={is_online ? 'success' : 'default'} 
          text={is_online ? '在线' : '离线'}
        />
      ),
    },
    {
      title: '用户名',
      dataIndex: 'username',
      key: 'username',
      fixed: isMobile ? 'left' : false,
      width: isMobile ? 100 : 150,
    },
    {
      title: '昵称',
      dataIndex: 'nickname',
      key: 'nickname',
      width: isMobile ? 100 : 150,
    },
    {
      title: '邮箱',
      dataIndex: 'email',
      key: 'email',
      width: isMobile ? 150 : 200,
      responsive: ['md'],
    },
    {
      title: '角色',
      dataIndex: 'role',
      key: 'role',
      width: 100,
      render: (role) => (
        <Tag color={getRoleColor(role)}>
          {getRoleText(role)}
        </Tag>
      ),
    },
    {
      title: '登录次数',
      dataIndex: 'login_count',
      key: 'login_count',
      width: 100,
      sorter: (a, b) => a.login_count - b.login_count,
      render: (count) => (
        <span style={{ fontWeight: 'bold', color: '#1890ff' }}>
          {count || 0}
        </span>
      ),
    },
    {
      title: '最后登录',
      dataIndex: 'last_login',
      key: 'last_login',
      width: isMobile ? 150 : 180,
      responsive: ['sm'],
    },
    {
      title: '注册时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: isMobile ? 150 : 180,
      responsive: ['md'],
    },
  ];

  const getTotalUsers = () => users.length;
  const getTotalLogins = () => users.reduce((sum, user) => sum + (user.login_count || 0), 0);
  const getActiveUsersToday = () => {
    const today = new Date().toDateString();
    return users.filter(user => {
      if (!user.last_login) return false;
      return new Date(user.last_login).toDateString() === today;
    }).length;
  };
  const getAdminCount = () => users.filter(user => user.role === 'admin').length;

  return (
    <div style={{ padding: isMobile ? '12px' : '24px' }}>
      <h2 style={{ 
        marginBottom: '24px', 
        fontSize: isMobile ? '20px' : '24px',
        fontWeight: 'bold' 
      }}>
        <TeamOutlined style={{ marginRight: '8px' }} />
        用户看板
      </h2>

      <Row gutter={[8, 8]} style={{ marginBottom: '16px' }}>
        <Col span={6}>
          <Card size="small" bodyStyle={{ padding: '8px 10px' }}>
            <Statistic
              title="用户数"
              value={getTotalUsers()}
              prefix={<UserOutlined />}
              valueStyle={{ color: '#1890ff', fontSize: 18 }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small" bodyStyle={{ padding: '8px 10px' }}>
            <Statistic
              title="在线"
              value={onlineCount}
              prefix={<EyeOutlined />}
              valueStyle={{ color: '#52c41a', fontSize: 18 }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small" bodyStyle={{ padding: '8px 10px' }}>
            <Statistic
              title="登录次数"
              value={getTotalLogins()}
              prefix={<LoginOutlined />}
              valueStyle={{ color: '#722ed1', fontSize: 18 }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small" bodyStyle={{ padding: '8px 10px' }}>
            <Statistic
              title="今日活跃"
              value={getActiveUsersToday()}
              prefix={<ClockCircleOutlined />}
              valueStyle={{ color: '#faad14', fontSize: 18 }}
            />
          </Card>
        </Col>
      </Row>

      <Card>
        <Spin spinning={loading} tip="加载中...">
          {isMobile ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {users.map(user => (
                <Card 
                  key={user.username} 
                  size="small"
                  style={{ 
                    background: user.is_online ? '#f6ffed' : '#fafafa',
                    borderLeft: `3px solid ${user.is_online ? '#52c41a' : '#d9d9d9'}`
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <Badge 
                        status={user.is_online ? 'success' : 'default'} 
                      />
                      <span style={{ fontWeight: 'bold', fontSize: 14 }}>{user.username}</span>
                    </div>
                    <Tag color={getRoleColor(user.role)} style={{ margin: 0 }}>
                      {getRoleText(user.role)}
                    </Tag>
                  </div>
                  <div style={{ fontSize: 12, color: '#666', marginBottom: 4 }}>
                    昵称: {user.nickname || '-'}
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, color: '#999' }}>
                    <span>登录: {user.login_count || 0}次</span>
                    <span>{user.last_login || '从未登录'}</span>
                  </div>
                </Card>
              ))}
              {users.length === 0 && !loading && (
                <div style={{ textAlign: 'center', padding: '40px 0', color: '#999' }}>
                  暂无用户数据
                </div>
              )}
            </div>
          ) : (
            <Table
              columns={columns}
              dataSource={users}
              rowKey="username"
              pagination={{
                pageSize: 10,
                showSizeChanger: true,
                showTotal: (total) => `共 ${total} 条记录`,
              }}
              scroll={{ x: 'max-content' }}
              size="middle"
            />
          )}
        </Spin>
      </Card>
    </div>
  );
};

export default UserDashboardPage;
