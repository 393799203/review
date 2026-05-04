import React, { useState, useEffect } from 'react';
import { Modal, Table, message, Spin, Card, Row, Col, Tag } from 'antd';
import { BarChartOutlined } from '@ant-design/icons';
import axios from 'axios';

const BlockStrengthModal = ({ visible, onClose, dateStr }) => {
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
    if (visible && dateStr) {
      loadBlockStrength();
    }
  }, [visible, dateStr]);

  const loadBlockStrength = async () => {
    setLoading(true);
    try {
      const isDev = import.meta.env.DEV;
      const API_BASE = isDev ? 'http://localhost:5001/api' : '/api';
      
      const response = await axios.get(`${API_BASE}/block-strength/${dateStr}`);
      
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
    return colorMap[index] || '#666';
  };

  const columns = [
    {
      title: '排名',
      key: 'rank',
      width: isMobile ? 50 : 60,
      render: (_, __, index) => (
        <span style={{ 
          fontWeight: 'bold', 
          color: getRankColor(index)
        }}>
          {index + 1}
        </span>
      ),
    },
    {
      title: '板块名称',
      dataIndex: 'block_name',
      key: 'block_name',
      width: isMobile ? 120 : 200,
      render: (text) => <span style={{ fontWeight: 'bold', fontSize: isMobile ? 12 : 14 }}>{text}</span>,
    },
    {
      title: '涨停数量',
      dataIndex: 'limit_up_num',
      key: 'limit_up_num',
      width: isMobile ? 80 : 100,
      render: (val) => (
        <span style={{ color: '#f5222d', fontWeight: 'bold', fontSize: isMobile ? 14 : 16 }}>
          {val}
        </span>
      ),
    },
    {
      title: '连板数量',
      dataIndex: 'continuous_plate_num',
      key: 'continuous_plate_num',
      width: isMobile ? 70 : 100,
    },
    {
      title: '板块涨幅',
      dataIndex: 'change_rate',
      key: 'change_rate',
      width: isMobile ? 80 : 100,
      render: (val) => (
        <span style={{ color: val > 0 ? '#f5222d' : val < 0 ? '#52c41a' : '#666', fontSize: isMobile ? 12 : 14 }}>
          {val ? `${val.toFixed(2)}%` : '-'}
        </span>
      ),
    },
    {
      title: '板块高度',
      dataIndex: 'high',
      key: 'high',
      width: isMobile ? 70 : 100,
      render: (val) => <span style={{ fontSize: isMobile ? 12 : 14 }}>{val || '-'}</span>,
    },
  ];

  const renderMobileContent = () => {
    if (!data || !data.blocks) return null;
    
    return (
      <div>
        <div style={{ marginBottom: 8, fontSize: 12, color: '#666', textAlign: 'center' }}>
          日期：{data.date}
        </div>
        {data.blocks.map((block, index) => (
          <Card
            key={block.block_code}
            size="small"
            style={{
              marginBottom: 8,
              borderLeft: `3px solid ${getRankColor(index)}`,
            }}
            styles={{ body: { padding: '8px 12px' } }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span style={{ 
                  fontWeight: 'bold', 
                  color: getRankColor(index),
                  fontSize: 16,
                  minWidth: 20
                }}>
                  {index + 1}
                </span>
                <span style={{ fontWeight: 'bold', fontSize: 14 }}>{block.block_name}</span>
              </div>
              <Tag color="red" style={{ fontSize: 13, fontWeight: 'bold', margin: 0 }}>
                {block.limit_up_num}只
              </Tag>
            </div>
            <Row gutter={8}>
              <Col span={8}>
                <div style={{ fontSize: 11, color: '#999' }}>连板数量</div>
                <div style={{ fontSize: 13, fontWeight: 'bold' }}>{block.continuous_plate_num || '-'}</div>
              </Col>
              <Col span={8}>
                <div style={{ fontSize: 11, color: '#999' }}>板块涨幅</div>
                <div style={{ 
                  fontSize: 13, 
                  fontWeight: 'bold',
                  color: block.change_rate > 0 ? '#f5222d' : block.change_rate < 0 ? '#52c41a' : '#666'
                }}>
                  {block.change_rate ? `${block.change_rate.toFixed(2)}%` : '-'}
                </div>
              </Col>
              <Col span={8}>
                <div style={{ fontSize: 11, color: '#999' }}>板块高度</div>
                <div style={{ fontSize: 13, fontWeight: 'bold' }}>{block.high || '-'}</div>
              </Col>
            </Row>
          </Card>
        ))}
      </div>
    );
  };

  const renderDesktopContent = () => {
    if (!data) return null;
    
    return (
      <div>
        <div style={{ marginBottom: 8, fontSize: 13, color: '#666' }}>
          日期：{data.date}
        </div>
        <Table
          columns={columns}
          dataSource={data.blocks}
          rowKey={(record) => record.block_code}
          pagination={false}
          size="small"
          style={{ fontSize: 12 }}
          styles={{
            body: {
              fontSize: 12,
            },
            header: {
              fontSize: 12,
              fontWeight: 'bold',
            },
          }}
        />
      </div>
    );
  };

  return (
    <Modal
      title={
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <BarChartOutlined style={{ fontSize: isMobile ? 16 : 18, color: '#1890ff' }} />
          <span style={{ fontSize: isMobile ? 14 : 16 }}>次日板块强度</span>
        </div>
      }
      open={visible}
      onCancel={onClose}
      width={isMobile ? '95%' : 700}
      footer={null}
      style={{ top: isMobile ? 20 : 10 }}
      styles={{
        body: {
          padding: isMobile ? '8px' : '8px 12px',
          maxHeight: isMobile ? '70vh' : 'none',
          overflow: isMobile ? 'auto' : 'visible',
        },
      }}
    >
      <Spin spinning={loading}>
        {isMobile ? renderMobileContent() : renderDesktopContent()}
      </Spin>
    </Modal>
  );
};

export default BlockStrengthModal;
