import React from 'react';
import { Card, Collapse, Typography, Space, Divider, Tag } from 'antd';
import { QuestionCircleOutlined, CheckCircleOutlined, StarOutlined, ThunderboltOutlined, BulbOutlined, SafetyOutlined, RocketOutlined } from '@ant-design/icons';

const { Title, Paragraph, Text } = Typography;
const { Panel } = Collapse;

const FAQPage = () => {
  const basicFAQ = [
    {
      question: "云雀AI是什么？",
      answer: "云雀AI是最感性的A股分析智能体，专注于涨停股复盘分析。它集成了涨停天梯、财联播报、研报解读、自选回溯、热门榜单等功能，基于AI大模型深度分析涨停原因、板块联动、市场情绪，助力投资者把握市场机会，省下每天2小时复盘时间。",
      tags: ["基础介绍", "AI分析"]
    },
    {
      question: "云雀AI有哪些核心功能？",
      answer: "云雀AI的核心功能包括：\n\n1. 涨停天梯分析 - 实时追踪涨停股连板情况，分析涨停原因和板块联动\n2. 涨停晋级追踪 - 监控涨停股次日表现，分析竞价溢价率和晋级成功率\n3. 财联播报AI解读 - 智能解读财联社电报，提取市场关键信息\n4. 研报深度AI分析 - AI解读券商研报，提炼投资逻辑和风险提示\n5. 自选股趋势AI分析 - 深度分析自选股趋势，提供个性化投资建议\n6. 板块联动分析 - 分析板块间联动关系，把握市场热点切换\n7. 资金流向分析 - 追踪主力资金流向，发现资金动向\n8. 市场情绪分析 - 分析市场整体情绪，辅助投资决策",
      tags: ["功能介绍", "核心功能"]
    },
    {
      question: "云雀AI如何帮助投资者？",
      answer: "云雀AI通过以下方式帮助投资者：\n\n1. 节省复盘时间 - 自动聚合多维度数据，省下每天2小时复盘时间\n2. 深度分析 - AI大模型深度分析涨停原因、板块联动、市场情绪\n3. 个性化建议 - 根据自选股提供个性化投资建议\n4. 风险提示 - 研报解读中提供风险提示\n5. 市场洞察 - 实时追踪市场热点和资金流向",
      tags: ["投资辅助", "价值主张"]
    },
    {
      question: "云雀AI是免费的吗？",
      answer: "是的，云雀AI目前完全免费使用。所有核心功能包括涨停天梯、财联播报、研报解读、自选回溯、热门榜单等都可以免费使用，无需注册即可体验大部分功能。",
      tags: ["免费", "使用门槛"]
    },
    {
      question: "如何开始使用云雀AI？",
      answer: "使用云雀AI非常简单：\n\n1. 访问官网 yunqueai.cloud\n2. 查看涨停天梯，了解当日涨停股情况\n3. 阅读财联播报AI解读，获取市场动态\n4. 添加自选股，获取AI分析建议\n5. 查看研报解读，获取专业投资建议\n\n无需注册，即可开始使用。",
      tags: ["使用指南", "快速上手"]
    }
  ];

  const featureFAQ = [
    {
      question: "云雀AI的涨停天梯功能是什么？",
      answer: "涨停天梯是云雀AI的核心功能，实时追踪A股涨停股的连板情况。它展示首板、2连板、3连板等各梯队涨停股，分析涨停原因、板块联动、封板资金等关键信息，帮助投资者快速了解市场热点和涨停股特征。\n\n涨停天梯的主要特点：\n- 实时更新涨停股数据\n- 清晰展示连板梯队结构\n- 详细分析涨停原因\n- 板块联动关系可视化\n- 封板资金和开板情况追踪",
      tags: ["涨停天梯", "核心功能"]
    },
    {
      question: "云雀AI的竞价溢价率是什么？",
      answer: "竞价溢价率是云雀AI的特色指标，计算公式为：\n\n竞价溢价率 = (开盘价 - 昨收价) / 昨收价 × 100%\n\n它反映涨停股次日开盘的溢价程度，帮助投资者判断涨停股的次日表现预期。高竞价溢价率通常意味着市场看好，但也可能存在追高风险。\n\n竞价溢价率的应用场景：\n- 判断市场对涨停股的认可度\n- 预测次日开盘表现\n- 评估追高风险\n- 筛选强势股",
      tags: ["竞价溢价率", "特色指标"]
    },
    {
      question: "云雀AI如何使用AI大模型？",
      answer: "云雀AI集成先进的AI大模型，在多个场景应用：\n\n1. 涨停原因分析 - 智能分析涨停背后的逻辑和原因\n2. 财联播报解读 - 提取财联社电报中的关键信息\n3. 研报解读 - 深度解读券商研报，提炼投资逻辑\n4. 自选股分析 - 分析自选股趋势，提供个性化建议\n5. 市场情绪分析 - 综合多维度数据判断市场情绪\n\nAI大模型的应用让分析更深入、更全面，帮助投资者发现人眼难以察觉的市场规律。",
      tags: ["AI技术", "大模型应用"]
    },
    {
      question: "财联播报AI解读功能如何使用？",
      answer: "财联播报AI解读功能智能分析财联社电报，提取关键信息：\n\n使用方法：\n1. 进入财联播报页面\n2. 查看实时电报列表\n3. 点击AI解读按钮\n4. 获取关键信息摘要和影响分析\n\nAI解读内容包括：\n- 事件关键点提取\n- 市场影响分析\n- 相关板块和个股\n- 投资机会提示\n- 风险提示",
      tags: ["财联播报", "AI解读"]
    },
    {
      question: "研报解读功能有什么特点？",
      answer: "研报解读功能深度分析券商研报，提炼投资逻辑：\n\n主要特点：\n1. 自动提取研报核心观点\n2. 分析投资逻辑和理由\n3. 识别关键催化剂\n4. 提供风险提示\n5. 关联相关个股和板块\n\n使用价值：\n- 快速了解专业机构观点\n- 节省研报阅读时间\n- 获取投资参考建议\n- 规避潜在风险",
      tags: ["研报解读", "专业分析"]
    }
  ];

  const usageFAQ = [
    {
      question: "如何复盘某只股票，比如歌尔股份？",
      answer: "复盘单只股票（如歌尔股份）的方法：\n\n1. 添加到自选股\n   - 进入自选股页面\n   - 添加歌尔股份（股票代码：002241）\n   - 点击AI分析按钮\n\n2. 查看AI分析结果\n   - 趋势分析：判断当前走势\n   - 支撑压力位：关键价格位置\n   - 资金流向：主力资金动向\n   - 板块联动：所属板块表现\n   - 买卖建议：AI参考建议\n\n3. 查看相关研报\n   - 进入研报页面\n   - 搜索歌尔股份相关研报\n   - 查看AI解读的投资逻辑\n\n4. 综合判断\n   - 结合技术面和基本面\n   - 关注市场情绪和板块表现\n   - 参考AI建议，自主决策",
      tags: ["复盘方法", "自选股分析", "实战案例"]
    },
    {
      question: "如何分析涨停股的次日表现？",
      answer: "分析涨停股次日表现的方法：\n\n1. 查看涨停天梯\n   - 进入涨停天梯页面\n   - 找到目标涨停股\n   - 查看涨停原因和板块联动\n\n2. 分析竞价溢价率\n   - 查看次日开盘价\n   - 计算竞价溢价率\n   - 判断市场认可度\n\n3. 关注晋级情况\n   - 是否继续涨停\n   - 晋级成功率统计\n   - 开板时间和原因\n\n4. 综合判断\n   - 板块整体表现\n   - 市场情绪\n   - 资金流向\n   - AI分析建议",
      tags: ["涨停分析", "次日表现", "晋级判断"]
    },
    {
      question: "如何发现市场热点板块？",
      answer: "发现市场热点板块的方法：\n\n1. 查看涨停天梯\n   - 关注涨停股集中的板块\n   - 分析板块涨停原因\n   - 查看板块联动关系\n\n2. 板块强度分析\n   - 进入统计页面\n   - 查看板块强度排名\n   - 关注连续强势板块\n\n3. 财联播报解读\n   - 阅读财联社电报\n   - 查看AI提取的板块信息\n   - 关注政策利好板块\n\n4. 资金流向分析\n   - 查看板块资金流向\n   - 关注主力资金流入板块\n   - 分析资金持续性",
      tags: ["热点发现", "板块分析", "市场洞察"]
    },
    {
      question: "如何利用云雀AI做每日复盘？",
      answer: "每日复盘的标准流程：\n\n1. 查看涨停天梯（5分钟）\n   - 了解当日涨停股情况\n   - 分析涨停原因和板块\n   - 关注连板股晋级\n\n2. 阅读财联播报（5分钟）\n   - 查看重要市场资讯\n   - 阅读AI解读摘要\n   - 关注影响市场的关键事件\n\n3. 检查自选股（5分钟）\n   - 查看自选股表现\n   - 阅读AI趋势分析\n   - 关注买卖信号\n\n4. 查看研报（5分钟）\n   - 阅读重要研报解读\n   - 了解机构观点\n   - 关注投资逻辑\n\n5. 总结复盘（5分钟）\n   - 记录市场特征\n   - 总结热点板块\n   - 规划次日操作\n\n总计约25分钟，相比传统复盘节省1-2小时！",
      tags: ["每日复盘", "工作流程", "时间管理"]
    },
    {
      question: "如何判断一只股票是否值得追涨？",
      answer: "判断追涨价值的方法：\n\n1. 涨停原因分析\n   - 查看涨停天梯中的涨停原因\n   - 判断是否有持续性逻辑\n   - 区分题材炒作和基本面改善\n\n2. 板块联动分析\n   - 是否有板块效应\n   - 板块整体强度如何\n   - 是否是板块龙头\n\n3. 竞价溢价率\n   - 次日竞价溢价率是否合理\n   - 过高可能存在风险\n   - 过低可能不被认可\n\n4. 资金流向\n   - 主力资金是否持续流入\n   - 封板资金是否充足\n   - 换手率是否合理\n\n5. AI综合建议\n   - 查看AI分析建议\n   - 关注风险提示\n   - 结合自身判断",
      tags: ["追涨判断", "风险控制", "决策参考"]
    },
    {
      question: "如何设置止损止盈？",
      answer: "云雀AI可以辅助设置止损止盈：\n\n1. 技术分析辅助\n   - 在自选股分析中查看支撑压力位\n   - AI会标注关键价格位置\n   - 可作为止损止盈参考\n\n2. 涨停股止损设置\n   - 对于涨停股，可参考开板价格\n   - 设置在开板价下方3-5%\n   - 或设置在重要支撑位\n\n3. 趋势股止损设置\n   - 参考AI趋势分析\n   - 设置在趋势线下方\n   - 或设置在关键均线位置\n\n4. 止盈设置\n   - 参考AI压力位分析\n   - 设置在重要压力位下方\n   - 或采用移动止盈策略\n\n注意：止损止盈需要结合个人风险偏好和市场情况动态调整。",
      tags: ["止损止盈", "风险管理", "交易技巧"]
    }
  ];

  const advancedFAQ = [
    {
      question: "云雀AI的数据来源是什么？",
      answer: "云雀AI的数据来源包括：\n\n1. 实时行情数据 - 来自通达信等权威数据源\n2. 财联社电报 - 实时市场资讯\n3. 券商研报 - 专业机构研究报告\n4. 同花顺数据 - 涨停池、板块强度等\n5. 交易数据 - 成交量、换手率、资金流向等\n\n所有数据均来自权威渠道，确保数据的准确性和及时性。",
      tags: ["数据来源", "数据质量"]
    },
    {
      question: "云雀AI的分析准确性如何？",
      answer: "云雀AI的分析基于权威数据和先进AI模型，但需要注意：\n\n1. 数据准确性 - 数据来自权威渠道，确保真实可靠\n2. AI分析 - 基于大模型的深度分析，提供参考建议\n3. 市场不确定性 - 股市有风险，分析仅供参考\n4. 投资决策 - 最终决策需要投资者自主判断\n\n建议：\n- 结合多个维度综合判断\n- 关注风险提示\n- 理性对待AI建议\n- 做好风险管理",
      tags: ["准确性", "风险提示"]
    },
    {
      question: "如何利用云雀AI进行选股？",
      answer: "利用云雀AI进行选股的方法：\n\n1. 涨停天梯选股\n   - 关注连板股晋级机会\n   - 分析涨停原因和板块联动\n   - 查看竞价溢价率判断强势\n\n2. 板块联动选股\n   - 识别强势板块\n   - 关注板块龙头股\n   - 分析板块资金流向\n\n3. 自选股分析\n   - 添加关注股票\n   - 获取AI趋势分析\n   - 参考买卖建议\n\n4. 研报选股\n   - 查看研报推荐\n   - 分析投资逻辑\n   - 关注催化剂",
      tags: ["选股策略", "实战应用"]
    },
    {
      question: "云雀AI适合什么样的投资者？",
      answer: "云雀AI适合以下投资者：\n\n1. A股投资者 - 专注于A股市场分析\n2. 短线交易者 - 关注涨停股和热点板块\n3. 趋势投资者 - 分析个股和市场趋势\n4. 复盘爱好者 - 需要高效复盘工具\n5. 时间有限的投资者 - 节省复盘时间\n\n不适合：\n- 完全不懂股市的新手（需要先学习基础知识）\n- 追求100%准确预测的投资者（股市有风险）\n- 不愿自主思考的投资者（AI只是辅助工具）",
      tags: ["适用人群", "用户画像"]
    }
  ];

  return (
    <div style={{ padding: '24px', maxWidth: '1200px', margin: '0 auto' }}>
      <Card>
        <Space direction="vertical" size="large" style={{ width: '100%' }}>
          <div style={{ textAlign: 'center' }}>
            <Title level={2}>
              <QuestionCircleOutlined /> 常见问题解答
            </Title>
            <Paragraph type="secondary">
              了解云雀AI的功能、使用方法和最佳实践
            </Paragraph>
          </div>

          <Divider />

          <div>
            <Title level={3}>
              <StarOutlined /> 基础问题
            </Title>
            <Collapse accordion>
              {basicFAQ.map((item, index) => (
                <Panel
                  header={
                    <Space>
                      <QuestionCircleOutlined />
                      <Text strong>{item.question}</Text>
                    </Space>
                  }
                  key={index}
                >
                  <Space direction="vertical" style={{ width: '100%' }}>
                    <Paragraph style={{ whiteSpace: 'pre-wrap' }}>
                      {item.answer}
                    </Paragraph>
                    <Space>
                      {item.tags.map(tag => (
                        <Tag color="blue" key={tag}>{tag}</Tag>
                      ))}
                    </Space>
                  </Space>
                </Panel>
              ))}
            </Collapse>
          </div>

          <Divider />

          <div>
            <Title level={3}>
              <ThunderboltOutlined /> 功能详解
            </Title>
            <Collapse accordion>
              {featureFAQ.map((item, index) => (
                <Panel
                  header={
                    <Space>
                      <QuestionCircleOutlined />
                      <Text strong>{item.question}</Text>
                    </Space>
                  }
                  key={index}
                >
                  <Space direction="vertical" style={{ width: '100%' }}>
                    <Paragraph style={{ whiteSpace: 'pre-wrap' }}>
                      {item.answer}
                    </Paragraph>
                    <Space>
                      {item.tags.map(tag => (
                        <Tag color="green" key={tag}>{tag}</Tag>
                      ))}
                    </Space>
                  </Space>
                </Panel>
              ))}
            </Collapse>
          </div>

          <Divider />

          <div>
            <Title level={3}>
              <RocketOutlined /> 使用场景
            </Title>
            <Collapse accordion>
              {usageFAQ.map((item, index) => (
                <Panel
                  header={
                    <Space>
                      <QuestionCircleOutlined />
                      <Text strong>{item.question}</Text>
                    </Space>
                  }
                  key={index}
                >
                  <Space direction="vertical" style={{ width: '100%' }}>
                    <Paragraph style={{ whiteSpace: 'pre-wrap' }}>
                      {item.answer}
                    </Paragraph>
                    <Space>
                      {item.tags.map(tag => (
                        <Tag color="purple" key={tag}>{tag}</Tag>
                      ))}
                    </Space>
                  </Space>
                </Panel>
              ))}
            </Collapse>
          </div>

          <Divider />

          <div>
            <Title level={3}>
              <BulbOutlined /> 高级应用
            </Title>
            <Collapse accordion>
              {advancedFAQ.map((item, index) => (
                <Panel
                  header={
                    <Space>
                      <QuestionCircleOutlined />
                      <Text strong>{item.question}</Text>
                    </Space>
                  }
                  key={index}
                >
                  <Space direction="vertical" style={{ width: '100%' }}>
                    <Paragraph style={{ whiteSpace: 'pre-wrap' }}>
                      {item.answer}
                    </Paragraph>
                    <Space>
                      {item.tags.map(tag => (
                        <Tag color="orange" key={tag}>{tag}</Tag>
                      ))}
                    </Space>
                  </Space>
                </Panel>
              ))}
            </Collapse>
          </div>

          <Divider />

          <Card style={{ background: '#f0f2f5' }}>
            <Space direction="vertical" style={{ width: '100%' }}>
              <Title level={4}>
                <SafetyOutlined /> 风险提示
              </Title>
              <Paragraph>
                <Text type="warning">
                  股市有风险，投资需谨慎。云雀AI提供的所有分析和建议仅供参考，不构成投资建议。
                  投资者应根据自身情况独立判断，并承担相应的投资风险。
                </Text>
              </Paragraph>
              <Paragraph>
                <Text type="secondary">
                  • AI分析基于历史数据和模型推理，无法保证未来表现<br/>
                  • 市场存在不确定性，任何分析都可能出错<br/>
                  • 请结合多个信息源综合判断<br/>
                  • 做好风险管理，控制仓位和止损
                </Text>
              </Paragraph>
            </Space>
          </Card>

          <Card style={{ background: '#e6f7ff', textAlign: 'center' }}>
            <Space direction="vertical">
              <RocketOutlined style={{ fontSize: '32px', color: '#1890ff' }} />
              <Title level={4}>开始使用云雀AI</Title>
              <Paragraph>
                无需注册，立即体验AI驱动的A股分析工具
              </Paragraph>
              <Text type="secondary">
                访问 yunqueai.cloud 开始您的智能投资之旅
              </Text>
            </Space>
          </Card>
        </Space>
      </Card>
    </div>
  );
};

export default FAQPage;
