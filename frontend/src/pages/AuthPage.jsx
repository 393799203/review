import React, { useState, useEffect } from 'react';
import { Form, Input, Button, Card, Tabs, message, Divider } from 'antd';
import { UserOutlined, LockOutlined, MailOutlined, IdcardOutlined, StockOutlined, FireOutlined, TrophyOutlined, DollarOutlined, NotificationOutlined, FileTextOutlined, BarChartOutlined, BulbOutlined } from '@ant-design/icons';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

const AuthPage = () => {
  const [activeTab, setActiveTab] = useState('login');
  const [loading, setLoading] = useState(false);
  const [guestLoading, setGuestLoading] = useState(false);
  const [isMobile, setIsMobile] = useState(false);
  const { login, guestLogin, register } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 768);
    };
    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  const handleLogin = async (values) => {
    setLoading(true);
    const success = await login(values.username, values.password);
    setLoading(false);

    if (success) {
      const from = location.state?.from?.pathname || '/';
      navigate(from, { replace: true });
    }
  };

  const handleGuestLogin = async () => {
    setGuestLoading(true);
    const success = await guestLogin();
    setGuestLoading(false);

    if (success) {
      const from = location.state?.from?.pathname || '/';
      navigate(from, { replace: true });
    }
  };

  const handleRegister = async (values) => {
    setLoading(true);
    const success = await register(
      values.username,
      values.email,
      values.password,
      values.nickname
    );
    setLoading(false);

    if (success) {
      setActiveTab('login');
      message.success('注册成功，请登录');
    }
  };

  const loginForm = (
    <Form
      name="login"
      onFinish={handleLogin}
      autoComplete="off"
      size="large"
    >
      <Form.Item
        name="username"
        rules={[{ required: true, message: '请输入用户名' }]}
      >
        <Input
          prefix={<UserOutlined style={{ color: '#1890ff' }} />}
          placeholder="用户名"
          style={{ height: isMobile ? 44 : 50, borderRadius: isMobile ? 8 : 12 }}
        />
      </Form.Item>

      <Form.Item
        name="password"
        rules={[{ required: true, message: '请输入密码' }]}
      >
        <Input.Password
          prefix={<LockOutlined style={{ color: '#1890ff' }} />}
          placeholder="密码"
          style={{ height: isMobile ? 44 : 50, borderRadius: isMobile ? 8 : 12 }}
        />
      </Form.Item>

      <Form.Item>
        <Button
          type="primary"
          htmlType="submit"
          loading={loading}
          block
          style={{
            height: isMobile ? 44 : 50,
            borderRadius: isMobile ? 8 : 12,
            background: 'linear-gradient(135deg, #1890ff 0%, #096dd9 100%)',
            border: 'none',
            fontWeight: 'bold',
            fontSize: isMobile ? 14 : 16
          }}
        >
          登录
        </Button>
      </Form.Item>

      <Form.Item>
        <Button
          type="default"
          loading={guestLoading}
          onClick={handleGuestLogin}
          block
          style={{
            height: isMobile ? 44 : 50,
            borderRadius: isMobile ? 8 : 12,
            fontWeight: 'bold',
            fontSize: isMobile ? 14 : 16
          }}
        >
          访客登录
        </Button>
      </Form.Item>
    </Form>
  );

  const registerForm = (
    <Form
      name="register"
      onFinish={handleRegister}
      autoComplete="off"
      size="large"
    >
      <Form.Item
        name="username"
        rules={[
          { required: true, message: '请输入用户名' },
          { min: 3, message: '用户名至少3个字符' }
        ]}
      >
        <Input
          prefix={<UserOutlined style={{ color: '#1890ff' }} />}
          placeholder="用户名"
          style={{ height: isMobile ? 44 : 50, borderRadius: isMobile ? 8 : 12 }}
        />
      </Form.Item>

      <Form.Item
        name="email"
        rules={[
          { required: true, message: '请输入邮箱' },
          { type: 'email', message: '请输入有效的邮箱地址' }
        ]}
      >
        <Input
          prefix={<MailOutlined style={{ color: '#1890ff' }} />}
          placeholder="邮箱"
          style={{ height: isMobile ? 44 : 50, borderRadius: isMobile ? 8 : 12 }}
        />
      </Form.Item>

      <Form.Item
        name="nickname"
      >
        <Input
          prefix={<IdcardOutlined style={{ color: '#1890ff' }} />}
          placeholder="昵称（选填）"
          style={{ height: isMobile ? 44 : 50, borderRadius: isMobile ? 8 : 12 }}
        />
      </Form.Item>

      <Form.Item
        name="password"
        rules={[
          { required: true, message: '请输入密码' },
          { min: 6, message: '密码至少6个字符' }
        ]}
      >
        <Input.Password
          prefix={<LockOutlined style={{ color: '#1890ff' }} />}
          placeholder="密码"
          style={{ height: isMobile ? 44 : 50, borderRadius: isMobile ? 8 : 12 }}
        />
      </Form.Item>

      <Form.Item
        name="confirmPassword"
        dependencies={['password']}
        rules={[
          { required: true, message: '请确认密码' },
          ({ getFieldValue }) => ({
            validator(_, value) {
              if (!value || getFieldValue('password') === value) {
                return Promise.resolve();
              }
              return Promise.reject(new Error('两次输入的密码不一致'));
            },
          }),
        ]}
      >
        <Input.Password
          prefix={<LockOutlined style={{ color: '#1890ff' }} />}
          placeholder="确认密码"
          style={{ height: isMobile ? 44 : 50, borderRadius: isMobile ? 8 : 12 }}
        />
      </Form.Item>

      <Form.Item>
        <Button
          type="primary"
          htmlType="submit"
          loading={loading}
          block
          style={{
            height: isMobile ? 44 : 50,
            borderRadius: isMobile ? 8 : 12,
            background: 'linear-gradient(135deg, #1890ff 0%, #096dd9 100%)',
            border: 'none',
            fontWeight: 'bold',
            fontSize: isMobile ? 14 : 16
          }}
        >
          注册
        </Button>
      </Form.Item>
    </Form>
  );

  const tabItems = [
    {
      key: 'login',
      label: '登录',
      children: loginForm,
    },
    {
      key: 'register',
      label: '注册',
      children: registerForm,
    },
  ];

  if (isMobile) {
    return (
      <div style={{
        minHeight: '100vh',
        background: 'linear-gradient(180deg, #001529 0%, #1890ff 100%)',
        padding: '30px 16px',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
      }}>
        <div style={{
          textAlign: 'center',
          marginBottom: 24
        }}>
          <div style={{
            width: 70,
            height: 70,
            borderRadius: 16,
            background: 'rgba(255, 255, 255, 0.2)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            margin: '0 auto 12px',
          }}>
            <StockOutlined style={{ fontSize: 32, color: '#fff' }} />
          </div>
          <h1 style={{
            fontSize: 28,
            fontWeight: 'bold',
            color: '#fff',
            marginBottom: 6,
            letterSpacing: 3
          }}>
            云雀AI
          </h1>
          <p style={{
            fontSize: 13,
            color: 'rgba(255, 255, 255, 0.8)',
          }}>
            A股涨停复盘系统
          </p>
        </div>

        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(3, 1fr)',
          gap: 10,
          width: '100%',
          maxWidth: 360,
          marginBottom: 20
        }}>
          <div style={{
            background: 'rgba(255, 255, 255, 0.1)',
            borderRadius: 12,
            padding: 12,
            textAlign: 'center',
          }}>
            <FireOutlined style={{ fontSize: 20, color: '#ff4d4f', marginBottom: 4 }} />
            <div style={{ color: '#fff', fontSize: 11 }}>涨停复盘</div>
          </div>
          <div style={{
            background: 'rgba(255, 255, 255, 0.1)',
            borderRadius: 12,
            padding: 12,
            textAlign: 'center',
          }}>
            <TrophyOutlined style={{ fontSize: 20, color: '#faad14', marginBottom: 4 }} />
            <div style={{ color: '#fff', fontSize: 11 }}>连板追踪</div>
          </div>
          <div style={{
            background: 'rgba(255, 255, 255, 0.1)',
            borderRadius: 12,
            padding: 12,
            textAlign: 'center',
          }}>
            <NotificationOutlined style={{ fontSize: 20, color: '#13c2c2', marginBottom: 4 }} />
            <div style={{ color: '#fff', fontSize: 11 }}>财经播报</div>
          </div>
          <div style={{
            background: 'rgba(255, 255, 255, 0.1)',
            borderRadius: 12,
            padding: 12,
            textAlign: 'center',
          }}>
            <FileTextOutlined style={{ fontSize: 20, color: '#722ed1', marginBottom: 4 }} />
            <div style={{ color: '#fff', fontSize: 11 }}>研报解读</div>
          </div>
          <div style={{
            background: 'rgba(255, 255, 255, 0.1)',
            borderRadius: 12,
            padding: 12,
            textAlign: 'center',
          }}>
            <BarChartOutlined style={{ fontSize: 20, color: '#eb2f96', marginBottom: 4 }} />
            <div style={{ color: '#fff', fontSize: 11 }}>数据统计</div>
          </div>
          <div style={{
            background: 'rgba(255, 255, 255, 0.1)',
            borderRadius: 12,
            padding: 12,
            textAlign: 'center',
          }}>
            <BulbOutlined style={{ fontSize: 20, color: '#52c41a', marginBottom: 4 }} />
            <div style={{ color: '#fff', fontSize: 11 }}>AI分析</div>
          </div>
        </div>

        <Card
          style={{
            width: '100%',
            maxWidth: 400,
            borderRadius: 16,
            boxShadow: '0 8px 24px rgba(0, 0, 0, 0.15)',
            border: 'none',
          }}
          styles={{ body: { padding: '20px 16px' } }}
        >
          <Tabs
            activeKey={activeTab}
            onChange={setActiveTab}
            items={tabItems}
            style={{ marginBottom: 16 }}
          />

          <Divider style={{ margin: '12px 0' }}>
            <span style={{ color: '#8c8c8c', fontSize: 11 }}>登录即表示同意</span>
          </Divider>

          <div style={{
            textAlign: 'center',
            color: '#8c8c8c',
            fontSize: 11,
            marginTop: 12
          }}>
            <span style={{ color: '#1890ff', cursor: 'pointer' }}>用户协议</span>
            <span style={{ margin: '0 6px' }}>和</span>
            <span style={{ color: '#1890ff', cursor: 'pointer' }}>隐私政策</span>
          </div>
        </Card>

        <div style={{
          marginTop: 24,
          color: 'rgba(255, 255, 255, 0.5)',
          fontSize: 11
        }}>
          © 2024 云雀AI All Rights Reserved
        </div>
      </div>
    );
  }

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      width: '100%',
    }}>
      <div
        style={{
          width: '60%',
          background: 'linear-gradient(135deg, #001529 0%, #1890ff 100%)',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          alignItems: 'center',
          padding: 60,
          position: 'relative',
          overflow: 'hidden',
          minHeight: '100vh',
        }}
      >
        <div style={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'radial-gradient(circle at 20% 80%, rgba(24, 144, 255, 0.3) 0%, transparent 50%)',
        }} />
        <div style={{
          position: 'absolute',
          top: '10%',
          left: '10%',
          width: 200,
          height: 200,
          borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(24, 144, 255, 0.2) 0%, transparent 70%)',
        }} />
        <div style={{
          position: 'absolute',
          bottom: '20%',
          right: '10%',
          width: 150,
          height: 150,
          borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(24, 144, 255, 0.15) 0%, transparent 70%)',
        }} />

        <div style={{
          position: 'relative',
          zIndex: 1,
          textAlign: 'center',
          marginBottom: 80
        }}>
          <div style={{
            width: 120,
            height: 120,
            borderRadius: 28,
            background: 'rgba(255, 255, 255, 0.2)',
            backdropFilter: 'blur(10px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            margin: '0 auto 32px',
            boxShadow: '0 8px 32px rgba(0, 0, 0, 0.1)'
          }}>
            <StockOutlined style={{ fontSize: 56, color: '#fff' }} />
          </div>
          <h1 style={{
            fontSize: 48,
            fontWeight: 'bold',
            color: '#fff',
            marginBottom: 16,
            letterSpacing: 6
          }}>
            云雀AI
          </h1>
          <p style={{
            fontSize: 20,
            color: 'rgba(255, 255, 255, 0.8)',
            letterSpacing: 3
          }}>
            A股涨停复盘系统
          </p>
        </div>

        <div style={{
          position: 'relative',
          zIndex: 1,
          display: 'grid',
          gridTemplateColumns: 'repeat(3, 1fr)',
          gap: 20,
          maxWidth: 600
        }}>
          <div style={{
            background: 'rgba(255, 255, 255, 0.1)',
            backdropFilter: 'blur(10px)',
            borderRadius: 16,
            padding: 20,
            textAlign: 'center',
            border: '1px solid rgba(255, 255, 255, 0.1)'
          }}>
            <FireOutlined style={{ fontSize: 28, color: '#ff4d4f', marginBottom: 8 }} />
            <div style={{ color: '#fff', fontSize: 13, fontWeight: 500 }}>涨停复盘</div>
          </div>
          <div style={{
            background: 'rgba(255, 255, 255, 0.1)',
            backdropFilter: 'blur(10px)',
            borderRadius: 16,
            padding: 20,
            textAlign: 'center',
            border: '1px solid rgba(255, 255, 255, 0.1)'
          }}>
            <TrophyOutlined style={{ fontSize: 28, color: '#faad14', marginBottom: 8 }} />
            <div style={{ color: '#fff', fontSize: 13, fontWeight: 500 }}>连板追踪</div>
          </div>
          <div style={{
            background: 'rgba(255, 255, 255, 0.1)',
            backdropFilter: 'blur(10px)',
            borderRadius: 16,
            padding: 20,
            textAlign: 'center',
            border: '1px solid rgba(255, 255, 255, 0.1)'
          }}>
            <NotificationOutlined style={{ fontSize: 28, color: '#13c2c2', marginBottom: 8 }} />
            <div style={{ color: '#fff', fontSize: 13, fontWeight: 500 }}>财经播报</div>
          </div>
          <div style={{
            background: 'rgba(255, 255, 255, 0.1)',
            backdropFilter: 'blur(10px)',
            borderRadius: 16,
            padding: 20,
            textAlign: 'center',
            border: '1px solid rgba(255, 255, 255, 0.1)'
          }}>
            <FileTextOutlined style={{ fontSize: 28, color: '#722ed1', marginBottom: 8 }} />
            <div style={{ color: '#fff', fontSize: 13, fontWeight: 500 }}>研报解读</div>
          </div>
          <div style={{
            background: 'rgba(255, 255, 255, 0.1)',
            backdropFilter: 'blur(10px)',
            borderRadius: 16,
            padding: 20,
            textAlign: 'center',
            border: '1px solid rgba(255, 255, 255, 0.1)'
          }}>
            <BarChartOutlined style={{ fontSize: 28, color: '#eb2f96', marginBottom: 8 }} />
            <div style={{ color: '#fff', fontSize: 13, fontWeight: 500 }}>数据统计</div>
          </div>
          <div style={{
            background: 'rgba(255, 255, 255, 0.1)',
            backdropFilter: 'blur(10px)',
            borderRadius: 16,
            padding: 20,
            textAlign: 'center',
            border: '1px solid rgba(255, 255, 255, 0.1)'
          }}>
            <BulbOutlined style={{ fontSize: 28, color: '#52c41a', marginBottom: 8 }} />
            <div style={{ color: '#fff', fontSize: 13, fontWeight: 500 }}>AI分析</div>
          </div>
        </div>

        <div style={{
          position: 'absolute',
          bottom: 30,
          color: 'rgba(255, 255, 255, 0.5)',
          fontSize: 12
        }}>
          © 2024 云雀AI All Rights Reserved
        </div>
      </div>

      <div
        style={{
          width: '40%',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          padding: '60px 50px',
          background: '#fff',
          minHeight: '100vh',
        }}
      >
        <div style={{ maxWidth: 400, margin: '0 auto', width: '100%' }}>
          <div style={{ marginBottom: 48 }}>
            <h2 style={{
              fontSize: 32,
              fontWeight: 'bold',
              color: '#262626',
              marginBottom: 12
            }}>
              欢迎回来
            </h2>
            <p style={{ color: '#8c8c8c', fontSize: 16 }}>
              请登录您的账户以继续
            </p>
          </div>

          <Tabs
            activeKey={activeTab}
            onChange={setActiveTab}
            items={tabItems}
            style={{ marginBottom: 32 }}
            tabBarStyle={{ marginBottom: 32 }}
          />

          <Divider style={{ margin: '32px 0' }}>
            <span style={{ color: '#8c8c8c', fontSize: 14 }}>登录即表示同意</span>
          </Divider>

          <div style={{
            textAlign: 'center',
            color: '#8c8c8c',
            fontSize: 14,
            marginTop: 24
          }}>
            <span style={{ color: '#1890ff', cursor: 'pointer' }}>用户协议</span>
            <span style={{ margin: '0 12px' }}>和</span>
            <span style={{ color: '#1890ff', cursor: 'pointer' }}>隐私政策</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AuthPage;