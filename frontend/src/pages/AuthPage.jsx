import React, { useState, useEffect } from 'react';
import { Form, Input, Button, Card, Tabs, message, Divider } from 'antd';
import { UserOutlined, LockOutlined, MailOutlined, IdcardOutlined, StockOutlined, FireOutlined, TrophyOutlined, DollarOutlined } from '@ant-design/icons';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

const AuthPage = () => {
  const [activeTab, setActiveTab] = useState('login');
  const [loading, setLoading] = useState(false);
  const [isMobile, setIsMobile] = useState(false);
  const { login, register } = useAuth();
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
        padding: '40px 20px',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
      }}>
        <div style={{
          textAlign: 'center',
          marginBottom: 40
        }}>
          <div style={{
            width: 80,
            height: 80,
            borderRadius: 20,
            background: 'rgba(255, 255, 255, 0.2)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            margin: '0 auto 16px',
          }}>
            <StockOutlined style={{ fontSize: 40, color: '#fff' }} />
          </div>
          <h1 style={{
            fontSize: 32,
            fontWeight: 'bold',
            color: '#fff',
            marginBottom: 8,
            letterSpacing: 4
          }}>
            节节高
          </h1>
          <p style={{
            fontSize: 14,
            color: 'rgba(255, 255, 255, 0.8)',
          }}>
            A股涨停复盘系统
          </p>
        </div>

        <Card
          style={{
            width: '100%',
            borderRadius: 16,
            boxShadow: '0 8px 24px rgba(0, 0, 0, 0.15)',
            border: 'none',
          }}
          styles={{ body: { padding: '24px 20px' } }}
        >
          <Tabs
            activeKey={activeTab}
            onChange={setActiveTab}
            items={tabItems}
            style={{ marginBottom: 16 }}
          />

          <Divider style={{ margin: '16px 0' }}>
            <span style={{ color: '#8c8c8c', fontSize: 12 }}>登录即表示同意</span>
          </Divider>

          <div style={{
            textAlign: 'center',
            color: '#8c8c8c',
            fontSize: 12,
            marginTop: 16
          }}>
            <span style={{ color: '#1890ff', cursor: 'pointer' }}>用户协议</span>
            <span style={{ margin: '0 8px' }}>和</span>
            <span style={{ color: '#1890ff', cursor: 'pointer' }}>隐私政策</span>
          </div>
        </Card>

        <div style={{
          marginTop: 40,
          color: 'rgba(255, 255, 255, 0.5)',
          fontSize: 12
        }}>
          © 2024 节节高 All Rights Reserved
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
            节节高
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
          gridTemplateColumns: 'repeat(2, 1fr)',
          gap: 24,
          maxWidth: 480
        }}>
          <div style={{
            background: 'rgba(255, 255, 255, 0.1)',
            backdropFilter: 'blur(10px)',
            borderRadius: 16,
            padding: 24,
            textAlign: 'center',
            border: '1px solid rgba(255, 255, 255, 0.1)'
          }}>
            <FireOutlined style={{ fontSize: 32, color: '#ff4d4f', marginBottom: 12 }} />
            <div style={{ color: '#fff', fontSize: 14, fontWeight: 500 }}>涨停复盘</div>
          </div>
          <div style={{
            background: 'rgba(255, 255, 255, 0.1)',
            backdropFilter: 'blur(10px)',
            borderRadius: 16,
            padding: 24,
            textAlign: 'center',
            border: '1px solid rgba(255, 255, 255, 0.1)'
          }}>
            <TrophyOutlined style={{ fontSize: 32, color: '#faad14', marginBottom: 12 }} />
            <div style={{ color: '#fff', fontSize: 14, fontWeight: 500 }}>连板追踪</div>
          </div>
          <div style={{
            background: 'rgba(255, 255, 255, 0.1)',
            backdropFilter: 'blur(10px)',
            borderRadius: 16,
            padding: 24,
            textAlign: 'center',
            border: '1px solid rgba(255, 255, 255, 0.1)'
          }}>
            <DollarOutlined style={{ fontSize: 32, color: '#52c41a', marginBottom: 12 }} />
            <div style={{ color: '#fff', fontSize: 14, fontWeight: 500 }}>智能分析</div>
          </div>
          <div style={{
            background: 'rgba(255, 255, 255, 0.1)',
            backdropFilter: 'blur(10px)',
            borderRadius: 16,
            padding: 24,
            textAlign: 'center',
            border: '1px solid rgba(255, 255, 255, 0.1)'
          }}>
            <StockOutlined style={{ fontSize: 32, color: '#1890ff', marginBottom: 12 }} />
            <div style={{ color: '#fff', fontSize: 14, fontWeight: 500 }}>板块热度</div>
          </div>
        </div>

        <div style={{
          position: 'absolute',
          bottom: 30,
          color: 'rgba(255, 255, 255, 0.5)',
          fontSize: 12
        }}>
          © 2024 节节高 All Rights Reserved
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