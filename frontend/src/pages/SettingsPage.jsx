import React from 'react';
import { Card, Descriptions, Tag } from 'antd';

const SettingsPage = () => {
  return (
    <div style={{ padding: 16 }}>
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
