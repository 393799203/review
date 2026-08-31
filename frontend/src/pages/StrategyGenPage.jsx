import React, { useState } from 'react';
import { Card, Input, Switch, Button, Alert, Empty, Space, message, Row, Col, Tag } from 'antd';
import { CodeOutlined, CopyOutlined, DownloadOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';
import { stockApi } from '../services/api';

const { TextArea } = Input;

const DEFAULT_REQUIREMENT =
  '连续3日放量抄底：第1天成交量大于前20日均量2倍，第2、3天大于1.5倍，结合申万行业输出结果';

const StrategyGenPage = () => {
  const [requirement, setRequirement] = useState(DEFAULT_REQUIREMENT);
  const [withBacktest, setWithBacktest] = useState(false);
  const [loading, setLoading] = useState(false);
  const [generated, setGenerated] = useState(false);
  const [code, setCode] = useState('');
  const [model, setModel] = useState('');

  const handleGenerate = async () => {
    if (!requirement.trim()) {
      message.warning('请填写选股/量化条件描述');
      return;
    }
    setLoading(true);
    try {
      const response = await stockApi.generateStrategy({
        requirement: requirement.trim(),
        with_backtest: withBacktest,
      });
      if (response.data.success) {
        setCode(response.data.data?.code || '');
        setModel(response.data.data?.model || '');
        setGenerated(true);
        message.success('代码生成成功');
      } else {
        message.error(response.data.error || '生成失败');
      }
    } catch (error) {
      message.error(error.response?.data?.error || '生成失败：' + error.message);
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(code);
      message.success('已复制到剪贴板');
    } catch (error) {
      message.error('复制失败，请手动选择复制');
    }
  };

  const handleDownload = () => {
    const blob = new Blob([code], { type: 'text/x-python;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `strategy_${dayjs().format('YYYYMMDD_HHmmss')}.py`;
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div>
      <Alert
        style={{ marginBottom: 16 }}
        type="info"
        showIcon
        message="生成的代码在本地运行：需 pip install psycopg2-binary pandas，并设置环境变量 DB_URL 指向行情数据库。服务端只生成代码，不执行。"
      />
      <Row gutter={16}>
        <Col xs={24} lg={8}>
          <Card title="条件描述" size="small">
            <TextArea
              rows={10}
              value={requirement}
              onChange={(e) => setRequirement(e.target.value)}
              placeholder={DEFAULT_REQUIREMENT}
              maxLength={2000}
              showCount
            />
            <div style={{ margin: '12px 0', display: 'flex', alignItems: 'center', gap: 8 }}>
              <Switch checked={withBacktest} onChange={setWithBacktest} />
              <span>附带简单回测</span>
            </div>
            <Button
              type="primary"
              icon={<CodeOutlined />}
              loading={loading}
              onClick={handleGenerate}
              block
            >
              生成代码
            </Button>
          </Card>
        </Col>
        <Col xs={24} lg={16}>
          <Card
            size="small"
            title={
              <Space>
                生成结果
                {model && <Tag>{model}</Tag>}
              </Space>
            }
            extra={
              code && (
                <Space>
                  <Button size="small" icon={<CopyOutlined />} onClick={handleCopy}>
                    复制
                  </Button>
                  <Button size="small" icon={<DownloadOutlined />} onClick={handleDownload}>
                    下载 .py
                  </Button>
                </Space>
              )
            }
          >
            {generated && !code ? (
              <Empty description="模型未返回有效代码，请调整条件描述后重试" />
            ) : !code ? (
              <Empty description="填写左侧条件描述，点击「生成代码」" />
            ) : (
              <pre
                style={{
                  background: '#1e1e1e',
                  color: '#d4d4d4',
                  padding: 16,
                  borderRadius: 6,
                  overflow: 'auto',
                  maxHeight: '70vh',
                  fontSize: 13,
                  lineHeight: 1.6,
                  fontFamily: "'SF Mono', Menlo, Consolas, monospace",
                  margin: 0,
                }}
              >
                {code}
              </pre>
            )}
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default StrategyGenPage;
