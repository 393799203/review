import React from 'react';
import { Card, Row, Col, Typography, Space, Tag, Divider, List } from 'antd';
import { 
  TrophyOutlined, 
  ThunderboltOutlined, 
  FileTextOutlined, 
  StarOutlined,
  BarChartOutlined,
  TeamOutlined,
  BulbOutlined,
  SafetyOutlined,
  RocketOutlined,
  LineChartOutlined,
  FundOutlined
} from '@ant-design/icons';

const { Title, Paragraph, Text } = Typography;

const FeaturesPage = () => {
  const features = [
    {
      icon: <TrophyOutlined style={{ fontSize: '32px', color: '#1890ff' }} />,
      title: "涨停天梯",
      subtitle: "实时追踪涨停股连板情况",
      description: "涨停天梯是云雀AI的核心功能，实时追踪A股涨停股的连板情况，帮助投资者快速了解市场热点。",
      details: [
        "实时展示首板、2连板、3连板等各梯队涨停股",
        "详细分析涨停原因，包括题材、消息、技术等因素",
        "板块联动关系可视化，发现热点板块",
        "封板资金和开板情况追踪，判断涨停强度",
        "涨停时间分布，分析市场情绪",
        "连板晋级统计，评估晋级成功率"
      ],
      useCases: [
        "快速了解当日市场热点",
        "发现潜在连板机会",
        "分析板块轮动规律",
        "评估市场整体情绪"
      ],
      tags: ["核心功能", "实时数据", "AI分析"]
    },
    {
      icon: <ThunderboltOutlined style={{ fontSize: '32px', color: '#52c41a' }} />,
      title: "涨停晋级追踪",
      subtitle: "监控涨停股次日表现",
      description: "追踪涨停股次日表现，分析竞价溢价率和晋级成功率，帮助投资者判断涨停股的持续性。",
      details: [
        "竞价溢价率计算：反映市场对涨停股的认可度",
        "次日涨跌幅统计：评估涨停股次日表现",
        "晋级成功率分析：统计不同梯队晋级概率",
        "开板时间追踪：分析涨停强度和持续性",
        "资金流向监控：追踪主力资金动向",
        "板块效应分析：判断是否有板块联动"
      ],
      useCases: [
        "判断是否追涨",
        "评估涨停股风险",
        "发现强势股特征",
        "优化选股策略"
      ],
      tags: ["特色功能", "数据分析", "风险评估"]
    },
    {
      icon: <FileTextOutlined style={{ fontSize: '32px', color: '#faad14' }} />,
      title: "财联播报AI解读",
      subtitle: "智能解读财联社电报",
      description: "AI智能解读财联社电报，提取关键信息，帮助投资者快速了解市场动态。",
      details: [
        "实时获取财联社电报，第一时间了解市场资讯",
        "AI提取关键信息，包括事件、影响、机会等",
        "关联相关板块和个股，发现投资机会",
        "市场影响分析，判断事件重要性",
        "投资机会提示，辅助决策",
        "风险提示，规避潜在风险"
      ],
      useCases: [
        "快速了解市场动态",
        "发现突发事件影响",
        "识别投资机会",
        "规避市场风险"
      ],
      tags: ["AI解读", "实时资讯", "机会发现"]
    },
    {
      icon: <StarOutlined style={{ fontSize: '32px', color: '#eb2f96' }} />,
      title: "研报深度AI分析",
      subtitle: "AI解读券商研报",
      description: "AI深度解读券商研报，提炼投资逻辑和风险提示，帮助投资者获取专业投资建议。",
      details: [
        "自动提取研报核心观点和投资逻辑",
        "识别关键催化剂和驱动因素",
        "分析目标价和估值逻辑",
        "提供风险提示和注意事项",
        "关联相关个股和板块",
        "研报质量评估，筛选优质研报"
      ],
      useCases: [
        "快速了解机构观点",
        "获取专业投资建议",
        "发现潜在投资机会",
        "规避研报风险"
      ],
      tags: ["专业分析", "机构观点", "投资建议"]
    },
    {
      icon: <BarChartOutlined style={{ fontSize: '32px', color: '#722ed1' }} />,
      title: "自选股趋势AI分析",
      subtitle: "深度分析自选股趋势",
      description: "AI深度分析自选股趋势，提供个性化投资建议，帮助投资者把握个股机会。",
      details: [
        "趋势分析：判断个股当前走势和未来预期",
        "支撑压力位：标注关键价格位置",
        "资金流向：追踪主力资金动向",
        "板块联动：分析所属板块表现",
        "技术指标：MACD、KDJ等技术分析",
        "AI买卖建议：基于综合分析的参考建议"
      ],
      useCases: [
        "跟踪关注股票",
        "获取买卖时机",
        "设置止损止盈",
        "优化持仓结构"
      ],
      tags: ["个性化", "趋势分析", "AI建议"]
    },
    {
      icon: <TeamOutlined style={{ fontSize: '32px', color: '#13c2c2' }} />,
      title: "板块联动分析",
      subtitle: "分析板块间联动关系",
      description: "分析板块间联动关系，把握市场热点切换，帮助投资者发现板块轮动机会。",
      details: [
        "板块强度排名：识别强势板块",
        "板块联动关系：发现相关板块",
        "板块资金流向：追踪板块资金动向",
        "板块涨停统计：分析板块热度",
        "板块轮动规律：把握热点切换",
        "板块龙头识别：发现板块领涨股"
      ],
      useCases: [
        "发现热点板块",
        "把握板块轮动",
        "选择板块龙头",
        "优化板块配置"
      ],
      tags: ["板块分析", "热点发现", "轮动规律"]
    },
    {
      icon: <FundOutlined style={{ fontSize: '32px', color: '#fa8c16' }} />,
      title: "资金流向分析",
      subtitle: "追踪主力资金流向",
      description: "追踪主力资金流向，发现资金动向，帮助投资者跟随主力资金操作。",
      details: [
        "主力资金流向：追踪大单资金动向",
        "板块资金分布：分析板块资金情况",
        "个股资金排名：发现资金流入流出前列",
        "资金持续性：判断资金流入持续性",
        "资金强度：评估资金流入强度",
        "资金趋势：分析资金流向趋势"
      ],
      useCases: [
        "跟随主力资金",
        "发现资金异动",
        "判断资金意图",
        "规避资金流出股"
      ],
      tags: ["资金分析", "主力追踪", "异动发现"]
    },
    {
      icon: <LineChartOutlined style={{ fontSize: '32px', color: '#2f54eb' }} />,
      title: "市场情绪分析",
      subtitle: "分析市场整体情绪",
      description: "分析市场整体情绪，辅助投资决策，帮助投资者把握市场节奏。",
      details: [
        "涨停数量统计：反映市场活跃度",
        "连板高度分析：判断市场强度",
        "开板率统计：评估市场分歧",
        "板块热度分布：分析市场结构",
        "资金情绪：判断资金态度",
        "综合情绪指数：量化市场情绪"
      ],
      useCases: [
        "判断市场强弱",
        "把握市场节奏",
        "调整仓位策略",
        "规避情绪极端"
      ],
      tags: ["情绪分析", "市场判断", "仓位管理"]
    }
  ];

  return (
    <div style={{ padding: '24px', maxWidth: '1400px', margin: '0 auto' }}>
      <Card>
        <Space direction="vertical" size="large" style={{ width: '100%' }}>
          <div style={{ textAlign: 'center' }}>
            <Title level={2}>
              <RocketOutlined /> 功能详解
            </Title>
            <Paragraph type="secondary" style={{ fontSize: '16px' }}>
              云雀AI提供全方位的A股分析功能，助力投资者把握市场机会
            </Paragraph>
          </div>

          <Divider />

          {features.map((feature, index) => (
            <div key={index}>
              <Card 
                style={{ 
                  background: index % 2 === 0 ? '#fafafa' : '#fff',
                  border: '1px solid #e8e8e8'
                }}
              >
                <Row gutter={[24, 24]}>
                  <Col xs={24} sm={24} md={6} style={{ textAlign: 'center' }}>
                    <Space direction="vertical" size="middle">
                      {feature.icon}
                      <Title level={3}>{feature.title}</Title>
                      <Text type="secondary">{feature.subtitle}</Text>
                      <Space wrap>
                        {feature.tags.map(tag => (
                          <Tag color="blue" key={tag}>{tag}</Tag>
                        ))}
                      </Space>
                    </Space>
                  </Col>
                  <Col xs={24} sm={24} md={18}>
                    <Space direction="vertical" size="middle" style={{ width: '100%' }}>
                      <Paragraph style={{ fontSize: '15px' }}>
                        {feature.description}
                      </Paragraph>
                      
                      <div>
                        <Text strong>功能特点：</Text>
                        <List
                          size="small"
                          dataSource={feature.details}
                          renderItem={item => (
                            <List.Item>
                              <Text>• {item}</Text>
                            </List.Item>
                          )}
                        />
                      </div>
                      
                      <div>
                        <Text strong>应用场景：</Text>
                        <div style={{ marginTop: '8px' }}>
                          <Space wrap>
                            {feature.useCases.map(useCase => (
                              <Tag color="green" key={useCase}>{useCase}</Tag>
                            ))}
                          </Space>
                        </div>
                      </div>
                    </Space>
                  </Col>
                </Row>
              </Card>
              {index < features.length - 1 && <Divider />}
            </div>
          ))}

          <Divider />

          <Card style={{ background: '#e6f7ff' }}>
            <Space direction="vertical" style={{ width: '100%' }}>
              <Title level={4}>
                <BulbOutlined /> 使用建议
              </Title>
              <Paragraph>
                <Text>
                  1. <Text strong>每日复盘</Text>：建议每天花费25分钟，依次查看涨停天梯、财联播报、自选股、研报，全面了解市场情况。<br/>
                  2. <Text strong>选股决策</Text>：结合涨停天梯、板块分析、资金流向、AI建议等多个维度综合判断。<br/>
                  3. <Text strong>风险控制</Text>：关注研报风险提示、资金流向变化、市场情绪极端等风险信号。<br/>
                  4. <Text strong>持续学习</Text>：通过每日复盘积累经验，总结市场规律，提升投资能力。
                </Text>
              </Paragraph>
            </Space>
          </Card>

          <Card style={{ background: '#fff7e6' }}>
            <Space direction="vertical" style={{ width: '100%' }}>
              <Title level={4}>
                <SafetyOutlined /> 风险提示
              </Title>
              <Paragraph>
                <Text type="warning">
                  • 股市有风险，投资需谨慎。云雀AI提供的所有分析和建议仅供参考，不构成投资建议。<br/>
                  • AI分析基于历史数据和模型推理，无法保证未来表现。<br/>
                  • 市场存在不确定性，任何分析都可能出错。<br/>
                  • 请结合多个信息源综合判断，做好风险管理。
                </Text>
              </Paragraph>
            </Space>
          </Card>
        </Space>
      </Card>
    </div>
  );
};

export default FeaturesPage;
