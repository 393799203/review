import React, { useState, useEffect } from 'react';
import { Card, Table, Tag, Spin, message, Statistic, Row, Col, Badge, Button, Tooltip, Modal, Input, Popconfirm } from 'antd';
import { UserOutlined, TeamOutlined, LoginOutlined, ClockCircleOutlined, EyeOutlined, MailOutlined, SearchOutlined, DeleteOutlined } from '@ant-design/icons';
import api from '../services/api';

const { Search } = Input;
const { TextArea } = Input;

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
  const [emailModalVisible, setEmailModalVisible] = useState(false);
  const [currentEmailUser, setCurrentEmailUser] = useState({ email: '', username: '' });
  const [emailSubject, setEmailSubject] = useState('');
  const [emailContent, setEmailContent] = useState('');
  const [sendingEmail, setSendingEmail] = useState(false);
  const [searchText, setSearchText] = useState('');
  const [displayCount, setDisplayCount] = useState(20);

  const getCurrentUserUid = () => {
    try {
      const user = localStorage.getItem('user');
      if (user) return JSON.parse(user).uid || '';
    } catch (e) { /* ignore */ }
    return '';
  };
  const currentUserUid = getCurrentUserUid();

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

  useEffect(() => {
    setDisplayCount(20);
  }, [searchText]);

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

  const getDefaultEmailContent = (username) => {
    return `<div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
    <h2 style="color: #1890ff; text-align: center;">欢迎您，${username}！</h2>
    
    <p style="font-size: 16px; line-height: 1.6; color: #333;">
        感谢您注册使用云雀AI涨停复盘智能体！我们很高兴为您提供专业的股票分析工具。
    </p>
    
    <div style="background-color: #f5f5f5; padding: 20px; border-radius: 8px; margin: 20px 0;">
        <h3 style="color: #1890ff; margin-top: 0;">🎯 产品主要能力</h3>
        <ul style="line-height: 1.8; color: #555;">
            <li><strong>🤖 AI智能体分析</strong>：全链路AI智能分析，从数据采集到决策建议，智能体全程辅助</li>
            <li><strong>涨停复盘</strong>：实时追踪涨停股票，深度分析涨停原因和板块联动</li>
            <li><strong>连板天梯</strong>：可视化展示连板股票，把握市场情绪和热点</li>
            <li><strong>板块强度</strong>：智能分析板块热度，识别强势板块和龙头股</li>
            <li><strong>自选股管理</strong>：个性化自选股池，实时监控股票动态</li>
            <li><strong>智能问答助手</strong>：基于AI技术的股票分析和投资问答助手</li>
            <li><strong>数据统计</strong>：全面的市场数据统计和历史回溯</li>
        </ul>
    </div>
    
    <div style="background-color: #e6f7ff; padding: 20px; border-radius: 8px; margin: 20px 0;">
        <h3 style="color: #1890ff; margin-top: 0;">🤖 AI智能体特色功能</h3>
        <ul style="line-height: 1.8; color: #555;">
            <li><strong>全链路AI分析</strong>：从行情监控、数据分析到投资建议，AI智能体全程参与</li>
            <li><strong>智能体问答</strong>：随时向AI智能体咨询股票相关问题，获得专业解答</li>
            <li><strong>自动化监控</strong>：AI智能体7x24小时监控市场动态，及时发现投资机会</li>
            <li><strong>个性化推荐</strong>：基于您的投资偏好，智能体提供定制化建议</li>
        </ul>
    </div>
    
    <div style="background-color: #fff7e6; padding: 20px; border-radius: 8px; margin: 20px 0;">
        <h3 style="color: #1890ff; margin-top: 0;">👥 适用客户</h3>
        <ul style="line-height: 1.8; color: #555;">
            <li><strong>短线交易者</strong>：需要实时捕捉涨停板机会的投资者</li>
            <li><strong>板块轮动投资者</strong>：关注板块联动和市场热点的交易者</li>
            <li><strong>量化交易者</strong>：需要数据支持和统计分析的专业人士</li>
            <li><strong>股票分析师</strong>：需要深度分析工具的研究人员</li>
            <li><strong>个人投资者</strong>：希望提升投资决策水平的散户朋友</li>
        </ul>
    </div>
    
    <div style="text-align: center; margin: 30px 0;">
        <a href="http://yunqueai.cloud/news" style="background-color: #1890ff; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; font-size: 16px;">立即开始使用</a>
    </div>
    
    <p style="font-size: 14px; color: #999; text-align: center; margin-top: 30px;">
        如有任何问题或需求建议，请随时联系我们：yunque.ai@qq.com
    </p>
</div>`;
  };

  const openEmailModal = (email, username) => {
    if (!email) {
      message.warning('该用户没有设置邮箱地址');
      return;
    }
    
    setCurrentEmailUser({ email, username });
    setEmailSubject('感谢您注册使用云雀AI涨停复盘智能体');
    setEmailContent(getDefaultEmailContent(username));
    setEmailModalVisible(true);
  };

  const handleDeleteUser = async (record) => {
    try {
      const response = await api.delete(`/admin/users/${record.uid}`);
      if (response.data.success) {
        message.success(response.data.message || '删除成功');
        loadUsers();
      } else {
        message.error(response.data.error || '删除失败');
      }
    } catch (error) {
      message.error('删除用户失败：' + (error.response?.data?.error || error.message));
    }
  };

  const handleSendEmail = async () => {
    if (!emailSubject.trim()) {
      message.warning('请输入邮件主题');
      return;
    }
    
    if (!emailContent.trim()) {
      message.warning('请输入邮件内容');
      return;
    }
    
    setSendingEmail(true);
    try {
      const response = await api.post('/admin/send-email', {
        email: currentEmailUser.email,
        subject: emailSubject,
        content: emailContent
      });
      
      if (response.data.success) {
        message.success(response.data.message);
        setEmailModalVisible(false);
      } else {
        message.error(response.data.error || '发送邮件失败');
      }
    } catch (error) {
      message.error('发送邮件失败：' + (error.response?.data?.error || error.message));
    } finally {
      setSendingEmail(false);
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
      width: isMobile ? 150 : 250,
      responsive: ['md'],
      render: (email, record) => (
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ flex: 1 }}>{email || '-'}</span>
          {email && record.role !== 'guest' && (
            <Tooltip title="发送邮件">
              <Button
                type="link"
                size="small"
                icon={<MailOutlined />}
                onClick={() => openEmailModal(email, record.username)}
                style={{ padding: '0 4px' }}
              />
            </Tooltip>
          )}
        </div>
      ),
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
      title: '最后操作',
      dataIndex: 'last_activity',
      key: 'last_activity',
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
    {
      title: '操作',
      key: 'action',
      width: 90,
      fixed: isMobile ? 'right' : false,
      render: (_, record) => (
        record.uid !== currentUserUid && (
          <Popconfirm
            title={`确定删除用户「${record.username}」？`}
            description="将同时删除其自选股、交易记录、策略及自动筛选配置，且不可恢复"
            okText="删除"
            cancelText="取消"
            okButtonProps={{ danger: true }}
            onConfirm={() => handleDeleteUser(record)}
          >
            <Button
              type="link"
              danger
              size="small"
              icon={<DeleteOutlined />}
              style={{ padding: '0 4px' }}
            >
              删除
            </Button>
          </Popconfirm>
        )
      ),
    },
  ];

  const getTotalUsers = () => users.length;
  const getTotalLogins = () => users.reduce((sum, user) => sum + (user.login_count || 0), 0);
  const getActiveUsersToday = () => {
    const today = new Date().toDateString();
    return users.filter(user => {
      if (!user.last_activity) return false;
      return new Date(user.last_activity).toDateString() === today;
    }).length;
  };
  const getAdminCount = () => users.filter(user => user.role === 'admin').length;

  const filteredUsers = users.filter(user => {
    if (!searchText) return true;
    const search = searchText.toLowerCase();
    return (
      user.username?.toLowerCase().includes(search) ||
      user.nickname?.toLowerCase().includes(search) ||
      user.email?.toLowerCase().includes(search)
    );
  });

  useEffect(() => {
    if (!isMobile) return;
    
    const handleScroll = () => {
      const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
      const scrollHeight = document.documentElement.scrollHeight;
      const clientHeight = window.innerHeight;
      
      if (scrollTop + clientHeight >= scrollHeight - 100) {
        setDisplayCount(prev => {
          const newCount = prev + 20;
          return newCount <= filteredUsers.length ? newCount : prev;
        });
      }
    };
    
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, [isMobile, filteredUsers.length]);

  return (
    <div style={{ padding: isMobile ? '0' : '12px' }}>
      <div style={{ 
        marginBottom: isMobile ? '12px' : '24px', 
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between'
      }}>
        <div style={{ 
          fontSize: isMobile ? 14 : 16,
          fontWeight: 'bold',
          display: 'flex',
          alignItems: 'center'
        }}>
          <TeamOutlined style={{ marginRight: '8px', color: '#1890ff' }} />
          用户看板
        </div>
        <Search
          placeholder="搜索用户名/昵称/邮箱"
          allowClear
          style={{ width: isMobile ? 150 : 250 }}
          value={searchText}
          onChange={(e) => setSearchText(e.target.value)}
        />
      </div>

      <Row gutter={[8, 8]} style={{ marginBottom: '16px' }}>
        <Col span={6}>
          <Card size="small" bodyStyle={{ padding: '8px 10px' }}>
            <Statistic
              title="用户数"
              value={getTotalUsers()}
              prefix={<UserOutlined />}
              styles={{ content: { color: '#1890ff', fontSize: 18 } }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small" bodyStyle={{ padding: '8px 10px' }}>
            <Statistic
              title="在线"
              value={onlineCount}
              prefix={<EyeOutlined />}
              styles={{ content: { color: '#52c41a', fontSize: 18 } }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small" bodyStyle={{ padding: '8px 10px' }}>
            <Statistic
              title="登录次数"
              value={getTotalLogins()}
              prefix={<LoginOutlined />}
              styles={{ content: { color: '#722ed1', fontSize: 18 } }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small" bodyStyle={{ padding: '8px 10px' }}>
            <Statistic
              title="今日活跃"
              value={getActiveUsersToday()}
              prefix={<ClockCircleOutlined />}
              styles={{ content: { color: '#faad14', fontSize: 18 } }}
            />
          </Card>
        </Col>
      </Row>

      <Spin spinning={loading} tip="加载中...">
        {isMobile ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {filteredUsers.slice(0, displayCount).map(user => (
              <div 
                key={user.username} 
                style={{ 
                  background: '#fff',
                  borderRadius: 8,
                  padding: 12,
                  boxShadow: '0 1px 2px rgba(0, 0, 0, 0.06)',
                  borderLeft: `3px solid ${user.is_online ? '#52c41a' : '#d9d9d9'}`
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <Badge status={user.is_online ? 'success' : 'default'} />
                    <span style={{ fontWeight: 'bold', fontSize: 15 }}>{user.username}</span>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                    <Tag color={getRoleColor(user.role)} style={{ margin: 0 }}>
                      {getRoleText(user.role)}
                    </Tag>
                    {user.uid !== currentUserUid && (
                      <Popconfirm
                        title={`确定删除用户「${user.username}」？`}
                        description="将同时删除其自选股、交易记录、策略及自动筛选配置，且不可恢复"
                        okText="删除"
                        cancelText="取消"
                        okButtonProps={{ danger: true }}
                        onConfirm={() => handleDeleteUser(user)}
                      >
                        <Button
                          type="link"
                          danger
                          size="small"
                          icon={<DeleteOutlined />}
                          style={{ padding: '0 4px', fontSize: 13 }}
                        />
                      </Popconfirm>
                    )}
                  </div>
                </div>
                
                <div style={{ display: 'grid', gridTemplateColumns: '6fr 4fr', gap: '8px 16px', fontSize: 13 }}>
                  <div style={{ color: '#666', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    <span style={{ color: '#999' }}>昵称：</span>
                    {user.nickname || '-'}
                  </div>
                  <div style={{ color: '#666', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    <span style={{ color: '#999' }}>登录次数：</span>
                    {user.login_count || 0}次
                  </div>
                  <div style={{ color: '#666', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', display: 'flex', alignItems: 'center', gap: 4 }}>
                    <span style={{ color: '#999' }}>邮箱：</span>
                    <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {user.email || '-'}
                    </span>
                    {user.email && user.role !== 'guest' && (
                      <Tooltip title="发送邮件">
                        <Button
                          type="link"
                          size="small"
                          icon={<MailOutlined />}
                          onClick={() => openEmailModal(user.email, user.username)}
                          style={{ padding: '0 4px', fontSize: 13 }}
                        />
                      </Tooltip>
                    )}
                  </div>
                  <div style={{ color: '#666', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    <span style={{ color: '#999' }}>状态：</span>
                    <span style={{ color: user.is_online ? '#52c41a' : '#999' }}>
                      {user.is_online ? '在线' : '离线'}
                    </span>
                  </div>
                  <div style={{ gridColumn: '1 / -1', color: '#999', fontSize: 12 }}>
                    最后活动：{user.last_activity || '从未操作'}
                  </div>
                </div>
              </div>
            ))}
            {displayCount < filteredUsers.length && (
              <div style={{ textAlign: 'center', padding: '20px 0', color: '#999', fontSize: 13 }}>
                下拉加载更多...
              </div>
            )}
            {filteredUsers.length === 0 && !loading && (
              <div style={{ textAlign: 'center', padding: '40px 0', color: '#999' }}>
                暂无用户数据
              </div>
            )}
          </div>
        ) : (
          <Table
            columns={columns}
            dataSource={filteredUsers}
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

      <Modal
        title="发送邮件"
        open={emailModalVisible}
        onCancel={() => setEmailModalVisible(false)}
        onOk={handleSendEmail}
        confirmLoading={sendingEmail}
        width={800}
        okText="发送"
        cancelText="取消"
      >
        <div style={{ marginBottom: 16 }}>
          <div style={{ marginBottom: 8, fontWeight: 'bold' }}>
            收件人：{currentEmailUser.email}
          </div>
          <div style={{ marginBottom: 8 }}>
            <Input
              placeholder="邮件主题"
              value={emailSubject}
              onChange={(e) => setEmailSubject(e.target.value)}
            />
          </div>
          <div>
            <TextArea
              placeholder="邮件内容（支持HTML格式）"
              value={emailContent}
              onChange={(e) => setEmailContent(e.target.value)}
              rows={15}
            />
          </div>
        </div>
      </Modal>
    </div>
  );
};

export default UserDashboardPage;
