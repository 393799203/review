import React, { useState, useEffect } from 'react';
import { Card, Descriptions, Tag, Form, Input, Button, message, Alert, Space, Typography, Segmented } from 'antd';
import { RobotOutlined, KeyOutlined, LinkOutlined, ThunderboltOutlined } from '@ant-design/icons';
import { useAuth } from '../contexts/AuthContext';

const { Text, Link } = Typography;

// 模型选项：value 为 API 中的 model 名
const MODEL_OPTIONS = [
  { label: 'V4-Flash（快·省）', value: 'deepseek-v4-flash' },
  { label: 'V4-Pro（强·贵）', value: 'deepseek-v4-pro' },
];

const SettingsPage = () => {
  const { user, settings, updateSettings, isAuthenticated } = useAuth();
  const [form] = Form.useForm();
  const [saving, setSaving] = useState(false);
  const [switchingModel, setSwitchingModel] = useState(false);

  const savedKey = (settings?.deepseek_api_key || '').trim();
  const hasKey = savedKey.length > 0;
  const currentModel = settings?.deepseek_model || 'deepseek-v4-flash';

  // 已保存的 Key 不回显明文，编辑时输入框留空让用户重新输入
  useEffect(() => {
    form.setFieldsValue({ deepseek_api_key: '' });
  }, [savedKey]);

  const handleSave = async (values) => {
    const key = (values.deepseek_api_key || '').trim();
    if (!key) {
      message.warning('请输入 API Key');
      return;
    }
    if (!key.startsWith('sk-')) {
      message.warning('DeepSeek API Key 通常以 sk- 开头，请确认输入是否正确');
    }
    setSaving(true);
    const ok = await updateSettings({ deepseek_api_key: key });
    setSaving(false);
    if (ok) {
      message.success('API Key 已保存');
      form.setFieldsValue({ deepseek_api_key: '' });
    } else {
      message.error('保存失败，请重试');
    }
  };

  const handleClear = async () => {
    setSaving(true);
    const ok = await updateSettings({ deepseek_api_key: '' });
    setSaving(false);
    if (ok) {
      message.success('API Key 已清除');
      form.setFieldsValue({ deepseek_api_key: '' });
    } else {
      message.error('清除失败，请重试');
    }
  };

  const handleModelChange = async (value) => {
    setSwitchingModel(true);
    const ok = await updateSettings({ deepseek_model: value });
    setSwitchingModel(false);
    if (ok) {
      message.success(`已切换到 ${value === 'deepseek-v4-pro' ? 'V4-Pro' : 'V4-Flash'}`);
    } else {
      message.error('模型切换失败，请重试');
    }
  };

  return (
    <div>
      {/* ===== DeepSeek API Key 配置 ===== */}
      <Card
        title={
          <Space>
            <RobotOutlined style={{ color: '#722ed1' }} />
            <span>DeepSeek API Key 配置</span>
          </Space>
        }
        style={{ marginBottom: 16 }}
      >
        <Alert
          type="info"
          showIcon
          icon={<KeyOutlined />}
          message="AI 找对标功能需要 DeepSeek API Key"
          description={
            <div style={{ fontSize: 13, lineHeight: 1.8 }}>
              <div>· 每位用户使用自己的 API Key 调用 AI，费用由各自承担。</div>
              <div>· Key 仅保存在你的账户设置里，不会泄露给他人。</div>
              <div>· 获取地址：
                <Link href="https://platform.deepseek.com/" target="_blank" rel="noreferrer">
                  <LinkOutlined /> https://platform.deepseek.com/
                </Link>
              </div>
            </div>
          }
          style={{ marginBottom: 16 }}
        />

        {!isAuthenticated ? (
          <Alert type="warning" message="请先登录后再配置 API Key" showIcon />
        ) : user?.role === 'guest' ? (
          <Alert type="warning" message="访客无法使用此功能，请注册登录后再配置" showIcon />
        ) : (
          <>
            <div style={{ marginBottom: 16 }}>
              <Space>
                <Text type="secondary">当前状态：</Text>
                {hasKey ? (
                  <Tag color="success">✓ 已配置</Tag>
                ) : (
                  <Tag color="default">未配置</Tag>
                )}
                {hasKey && <Text type="secondary" style={{ fontSize: 12 }}>（已保存的 Key 不会显示明文）</Text>}
              </Space>
            </div>

            <Form form={form} layout="vertical" onFinish={handleSave}>
              <Form.Item
                name="deepseek_api_key"
                label="API Key"
                rules={[{ required: true, message: '请输入 API Key' }]}
              >
                <Input.Password
                  prefix={<KeyOutlined style={{ color: '#bfbfbf' }} />}
                  placeholder={hasKey ? '已配置，如需更新请输入新 Key' : 'sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'}
                  autoComplete="new-password"
                />
              </Form.Item>
              <Form.Item>
                <Space>
                  <Button type="primary" htmlType="submit" loading={saving} icon={<KeyOutlined />}>
                    {hasKey ? '更新 Key' : '保存 Key'}
                  </Button>
                  {hasKey && (
                    <Button danger onClick={handleClear} loading={saving}>
                      清除 Key
                    </Button>
                  )}
                </Space>
              </Form.Item>
            </Form>

            {/* 模型选择 */}
            <div style={{ marginTop: 8, paddingTop: 16, borderTop: '1px dashed #f0f0f0' }}>
              <div style={{ marginBottom: 8 }}>
                <Space>
                  <ThunderboltOutlined style={{ color: '#fa8c16' }} />
                  <Text strong>模型选择</Text>
                  <Tag color={currentModel === 'deepseek-v4-pro' ? 'orange' : 'blue'}>
                    {currentModel === 'deepseek-v4-pro' ? 'V4-Pro' : 'V4-Flash'}
                  </Tag>
                </Space>
              </div>
              <Segmented
                options={MODEL_OPTIONS}
                value={currentModel}
                onChange={handleModelChange}
                loading={switchingModel}
                block
              />
              <div style={{ fontSize: 12, color: '#8c8c8c', marginTop: 8, lineHeight: 1.6 }}>
                · <Text strong>V4-Flash</Text>：响应快、成本低，适合日常对标分析（推荐）<br/>
                · <Text strong>V4-Pro</Text>：推理更强、质量更高，适合复杂题材拆解，但更慢更贵
              </div>
            </div>
          </>
        )}
      </Card>

      {/* ===== 数据源信息（原有） ===== */}
      <Card title="数据源信息">
        <Descriptions column={1} bordered size="small">
          <Descriptions.Item label="主数据源">
            <Tag color="blue">同花顺</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="备用数据源">
            <Tag color="green">Akshare</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="数据接口">
            <div style={{ fontSize: 12 }}>
              <div>• 涨停梯队: /dataapi/limit_up/continuous_limit_up</div>
              <div>• 涨停池: /dataapi/limit_up/limit_up_pool</div>
              <div>• 板块强度: /dataapi/limit_up/block_top</div>
            </div>
          </Descriptions.Item>
          <Descriptions.Item label="更新频率">
            每日收盘后自动更新
          </Descriptions.Item>
        </Descriptions>
      </Card>
    </div>
  );
};

export default SettingsPage;
