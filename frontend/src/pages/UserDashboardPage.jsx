import React, { useState, useEffect } from 'react';
import { Card, Table, Tag, Spin, message, Statistic, Row, Col } from 'antd';
import { UserOutlined, TeamOutlined, LoginOutlined, ClockCircleOutlined } from '@ant-design/icons';
import api from '../services/api';

const UserDashboardPage = () => {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
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
      } else {
        message.error('加载用户数据失败');
      }
    } catch (error) {
      message.error('加载用户数据失败：' + (error.response?.data?.error || error.message));
    } finally {
      setLoading(false);
    }
  };

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

      <Row gutter={[16, 16]} style={{ marginBottom: '24px' }}>
        <Col xs={12} sm={12} md={6}>
          <Card>
            <Statistic
              title="总用户数"
              value={getTotalUsers()}
              prefix={<UserOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={12} md={6}>
          <Card>
            <Statistic
              title="总登录次数"
              value={getTotalLogins()}
              prefix={<LoginOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={12} md={6}>
          <Card>
            <Statistic
              title="今日活跃"
              value={getActiveUsersToday()}
              prefix={<ClockCircleOutlined />}
              valueStyle={{ color: '#faad14' }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={12} md={6}>
          <Card>
            <Statistic
              title="管理员数"
              value={getAdminCount()}
              prefix={<TeamOutlined />}
              valueStyle={{ color: '#f5222d' }}
            />
          </Card>
        </Col>
      </Row>

      <Card>
        <Spin spinning={loading} tip="加载中...">
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
            size={isMobile ? 'small' : 'middle'}
          />
        </Spin>
      </Card>
    </div>
  );
};

export default UserDashboardPage;
