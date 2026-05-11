import { useState, useEffect } from 'react';
import { Modal, Card, Row, Col, Spin, message } from 'antd';
import { BarChartOutlined, FireOutlined, ThunderboltOutlined, RiseOutlined } from '@ant-design/icons';
import axios from 'axios';

const BlockStrengthModal = ({ visible, onClose, date }) => {
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState(null);
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 768);
    };
    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  useEffect(() => {
    if (visible) {
      loadBlockStrength();
    }
  }, [visible, date]);

  const loadBlockStrength = async () => {
    setLoading(true);
    try {
      const isDev = import.meta.env.DEV;
      const API_BASE = isDev ? 'http://localhost:5001/api' : '/api';

      const url = date
        ? `${API_BASE}/block-strength/continuous?date=${date}`
        : `${API_BASE}/block-strength/continuous`;

      const response = await axios.get(url);

      if (response.data.success) {
        setData(response.data.data);
      } else {
        message.error(response.data.error || '获取板块强度失败');
      }
    } catch (error) {
      message.error('获取板块强度失败：' + (error.response?.data?.error || error.message));
    } finally {
      setLoading(false);
    }
  };

  const getRankColor = (index) => {
    const colorMap = {
      0: '#f5222d',
      1: '#fa8c16',
      2: '#faad14',
      3: '#52c41a',
      4: '#1890ff',
    };
    return colorMap[index] || '#b37feb';
  };

  const getDayLabel = (label) => {
    const labelMap = {
      yesterday: '前日',
      today: '当日',
      tomorrow: '次日',
    };
    return labelMap[label] || label;
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '';
    return `${dateStr.slice(4, 6)}/${dateStr.slice(6, 8)}`;
  };

  const renderBlockItem = (block, index) => {
    return (
      <div
        key={block.block_code}
        style={{
          display: 'flex',
          alignItems: 'center',
          padding: isMobile ? '8px 6px' : '6px 8px',
          borderBottom: '1px solid #f5f5f5',
          fontSize: isMobile ? 12 : 13,
        }}
      >
        <span
          style={{
            width: 20,
            height: 20,
            borderRadius: '50%',
            background: getRankColor(index),
            color: '#fff',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontWeight: 'bold',
            fontSize: 11,
            marginRight: 8,
            flexShrink: 0,
          }}
        >
          {index + 1}
        </span>
        <span
          style={{
            flex: 1,
            fontWeight: 'bold',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
            marginRight: 8,
          }}
        >
          {block.block_name}
        </span>
        <span style={{ color: '#f5222d', fontWeight: 'bold', marginRight: 8, flexShrink: 0 }}>
          {block.limit_up_num}涨停
        </span>
        <span style={{ color: '#fa8c16', fontWeight: 'bold', marginRight: 8, flexShrink: 0 }}>
          {block.continuous_plate_num || 0}连板
        </span>
        <span
          style={{
            color: block.change_rate > 0 ? '#f5222d' : block.change_rate < 0 ? '#52c41a' : '#666',
            fontWeight: 'bold',
            flexShrink: 0,
            minWidth: 50,
            textAlign: 'right',
          }}
        >
          {block.change_rate ? `${block.change_rate > 0 ? '+' : ''}${block.change_rate.toFixed(1)}%` : '-'}
        </span>
      </div>
    );
  };

  const renderDayColumn = (label, dayData) => {
    if (!dayData || !dayData.blocks || dayData.blocks.length === 0) {
      return (
        <Card
          size="small"
          title={
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: 13, fontWeight: 'bold' }}>{getDayLabel(label)}</span>
              <span style={{ fontSize: 11, color: '#666' }}>{dayData?.date || '-'}</span>
            </div>
          }
          styles={{ body: { padding: 0 } }}
        >
          <div style={{ textAlign: 'center', color: '#999', padding: '40px 0' }}>
            暂无数据
          </div>
        </Card>
      );
    }

    return (
      <Card
        size="small"
        title={
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: 13, fontWeight: 'bold' }}>{getDayLabel(label)}</span>
            <span style={{ fontSize: 11, color: '#666' }}>{formatDate(dayData.date)}</span>
          </div>
        }
        styles={{ body: { padding: 0 } }}
      >
        <div
          style={{
            maxHeight: 'none',
            overflow: 'visible',
          }}
        >
          {dayData.blocks.map((block, index) => renderBlockItem(block, index))}
        </div>
      </Card>
    );
  };

  const renderContent = () => {
    if (!data) return null;

    const days = ['yesterday', 'today', 'tomorrow'].filter((day) => data[day]);

    if (isMobile) {
      return (
        <div>
          {days.map((label) => (
            <div key={label} style={{ marginBottom: 12 }}>
              {renderDayColumn(label, data[label])}
            </div>
          ))}
        </div>
      );
    }

    return (
      <Row gutter={[12, 12]}>
        {days.map((label) => (
          <Col span={8} key={label}>
            {renderDayColumn(label, data[label])}
          </Col>
        ))}
      </Row>
    );
  };

  return (
    <Modal
      title={
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <BarChartOutlined style={{ fontSize: isMobile ? 16 : 18, color: '#1890ff' }} />
          <span style={{ fontSize: isMobile ? 14 : 16 }}>强势板块</span>
        </div>
      }
      open={visible}
      onCancel={onClose}
      width={isMobile ? '95%' : 1100}
      footer={null}
      centered
      styles={{
        body: {
          padding: isMobile ? '8px' : '12px 16px',
          maxHeight: isMobile ? '80vh' : '85vh',
          overflow: 'auto',
        },
      }}
    >
      <Spin spinning={loading}>
        {renderContent()}
      </Spin>
    </Modal>
  );
};

export default BlockStrengthModal;