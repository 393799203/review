import { useState, useEffect } from 'react';
import { Modal, Select, message, Spin } from 'antd';
import { EditOutlined } from '@ant-design/icons';
import axios from 'axios';

const EditBlockModal = ({ visible, onClose, stockCode, stockName, currentBlock, dateStr, onSuccess }) => {
  const [loading, setLoading] = useState(false);
  const [selectedBlock, setSelectedBlock] = useState(null);
  const [blocks, setBlocks] = useState([]);
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
      loadBlocks();
      setSelectedBlock(currentBlock);
    }
  }, [visible, dateStr, currentBlock]);

  const loadBlocks = async () => {
    setLoading(true);
    try {
      const isDev = import.meta.env.DEV;
      const API_BASE = isDev ? 'http://localhost:5001/api' : '/api';
      
      const response = await axios.get(`${API_BASE}/block-strength/${dateStr}`);
      
      if (response.data.success) {
        setBlocks(response.data.data.blocks || []);
      } else {
        message.error(response.data.error || '获取板块数据失败');
      }
    } catch (error) {
      message.error('获取板块数据失败：' + (error.response?.data?.error || error.message));
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    if (!selectedBlock) {
      message.warning('请选择板块');
      return;
    }

    setLoading(true);
    try {
      const isDev = import.meta.env.DEV;
      const API_BASE = isDev ? 'http://localhost:5001/api' : '/api';
      
      const response = await axios.put(`${API_BASE}/stock/block`, {
        stock_code: stockCode,
        trade_date: dateStr,
        block_name: selectedBlock
      });

      if (response.data.success) {
        message.success('修改成功');
        if (onSuccess) {
          onSuccess(selectedBlock);
        }
        onClose();
      } else {
        message.error(response.data.error || '修改失败');
      }
    } catch (error) {
      message.error('修改失败：' + (error.response?.data?.error || error.message));
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      title={
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <EditOutlined style={{ fontSize: isMobile ? 14 : 16, color: '#1890ff' }} />
          <span style={{ fontSize: isMobile ? 14 : 16 }}>编辑所属板块</span>
        </div>
      }
      open={visible}
      onCancel={onClose}
      onOk={handleSave}
      confirmLoading={loading}
      okText="保存"
      cancelText="取消"
      width={isMobile ? '90%' : 400}
      style={{ top: isMobile ? 20 : undefined }}
      styles={{ body: { padding: isMobile ? '12px' : '24px' } }}
    >
      <Spin spinning={loading}>
        <div style={{ marginBottom: isMobile ? 12 : 16 }}>
          <div style={{ marginBottom: isMobile ? 6 : 8, fontWeight: 'bold', fontSize: isMobile ? 13 : 14 }}>
            股票：{stockName} ({stockCode})
          </div>
          <div style={{ marginBottom: isMobile ? 6 : 8, color: '#666', fontSize: isMobile ? 12 : 13 }}>
            当前板块：{currentBlock || '无'}
          </div>
        </div>
        
        <div style={{ marginBottom: isMobile ? 6 : 8, fontWeight: 'bold', fontSize: isMobile ? 13 : 14 }}>
          选择新板块：
        </div>
        
        <Select
          style={{ width: '100%', fontSize: isMobile ? 13 : 14 }}
          value={selectedBlock}
          onChange={setSelectedBlock}
          placeholder="请选择板块"
          showSearch
          filterOption={(input, option) =>
            option.children.toLowerCase().indexOf(input.toLowerCase()) >= 0
          }
          size={isMobile ? 'middle' : 'middle'}
        >
          {blocks.map(block => (
            <Select.Option key={block.block_code} value={block.block_name} style={{ fontSize: isMobile ? 13 : 14 }}>
              {block.block_name} (涨停{block.limit_up_num}只)
            </Select.Option>
          ))}
        </Select>
      </Spin>
    </Modal>
  );
};

export default EditBlockModal;
