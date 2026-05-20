import { useState, useEffect, useRef } from 'react';
import { Card, Table, Tag, Spin, Input, Button, Empty, Tooltip, Modal } from 'antd';
import { FileTextOutlined, RobotOutlined, ThunderboltOutlined, InfoCircleOutlined, UpOutlined } from '@ant-design/icons';
import axios from 'axios';
import StockKlineModal from '../components/StockKlineModal';

let loadReportsRef = null;

export const refreshReportsData = () => {
  if (loadReportsRef) {
    loadReportsRef();
  }
};

const ReportPage = () => {
  const [isMobile, setIsMobile] = useState(window.innerWidth <= 768);
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [searchCode, setSearchCode] = useState('');
  const [pagination, setPagination] = useState({
    current: 1,
    pageSize: 50,
    total: 0
  });
  const [analyzingIds, setAnalyzingIds] = useState(new Set());
  const [analysisCache, setAnalysisCache] = useState({});
  const [modalVisible, setModalVisible] = useState(false);
  const [currentReport, setCurrentReport] = useState(null);
  const [currentAnalysis, setCurrentAnalysis] = useState(null);
  const [klineVisible, setKlineVisible] = useState(false);
  const [selectedStock, setSelectedStock] = useState(null);
  const listEndRef = useRef(null);
  const searchTimeoutRef = useRef(null);
  const [showBackTop, setShowBackTop] = useState(false);

  useEffect(() => {
    const handleResize = () => {
      setIsMobile(window.innerWidth <= 768);
    };
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  useEffect(() => {
    const handleScroll = () => {
      const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
      setShowBackTop(scrollTop > 300);
    };
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const scrollToTop = () => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleStockClick = (stockCode, stockName) => {
    setSelectedStock({ code: stockCode, name: stockName });
    setKlineVisible(true);
  };

  const loadReports = async (page = 1, code = '', append = false) => {
    if (append) {
      setLoadingMore(true);
    } else {
      setLoading(true);
    }
    
    try {
      const response = await axios.get('/api/reports', {
        params: {
          page: page,
          pageSize: 50,
          code: code
        }
      });
      
      if (response.data.success) {
        const newList = response.data.data.list || [];
        if (append) {
          setReports(prev => [...prev, ...newList]);
        } else {
          setReports(newList);
        }
        setPagination(prev => ({
          ...prev,
          current: page,
          total: response.data.data.total
        }));
      }
    } catch (error) {
      console.error('加载研报失败:', error);
    } finally {
      setLoading(false);
      setLoadingMore(false);
    }
  };

  const loadMoreReports = () => {
    if (loadingMore || pagination.current >= pagination.total) return;
    loadReports(pagination.current + 1, searchCode, true);
  };

  useEffect(() => {
    const handleScroll = () => {
      if (!isMobile || loadingMore || loading) return;
      
      const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
      const scrollHeight = document.documentElement.scrollHeight;
      const clientHeight = document.documentElement.clientHeight;
      
      if (scrollTop + clientHeight >= scrollHeight - 200) {
        loadMoreReports();
      }
    };

    if (isMobile) {
      window.addEventListener('scroll', handleScroll);
      return () => window.removeEventListener('scroll', handleScroll);
    }
  }, [isMobile, loadingMore, loading, pagination.current, pagination.total, searchCode]);

  useEffect(() => {
    loadReports();
  }, []);

  useEffect(() => {
    loadReportsRef = () => loadReports(1, searchCode);
    return () => {
      loadReportsRef = null;
    };
  }, [searchCode]);

  const handleSearch = (value) => {
    const code = value ? value.trim() : '';
    setSearchCode(code);
    loadReports(1, code);
  };

  const handleSearchChange = (e) => {
    const value = e.target.value;
    setSearchCode(value);
    
    if (searchTimeoutRef.current) {
      clearTimeout(searchTimeoutRef.current);
    }
    
    searchTimeoutRef.current = setTimeout(() => {
      const code = value ? value.trim() : '';
      loadReports(1, code);
    }, 500);
  };

  const handleReset = () => {
    setSearchCode('');
    loadReports(1, '');
  };

  const handleTableChange = (pag) => {
    loadReports(pag.current, searchCode);
  };

  const analyzeReport = async (report, force = false) => {
    if (analysisCache[report.infoCode] && !force) {
      setCurrentReport(report);
      setCurrentAnalysis(analysisCache[report.infoCode]);
      setModalVisible(true);
      return;
    }

    try {
      setAnalyzingIds(prev => new Set([...prev, report.infoCode]));
      const isDev = import.meta.env.DEV;
      const API_BASE = isDev ? 'http://localhost:5001/api' : '/api';
      const response = await axios.post(`${API_BASE}/reports/analyze`, {
        info_code: report.infoCode,
        title: report.title,
        stock_name: report.stockName,
        stock_code: report.stockCode,
        rating: report.emRatingName,
        rating_change: report.ratingChange,
        predict_this_year_eps: report.predictThisYearEps,
        predict_next_year_eps: report.predictNextYearEps,
        predict_next_two_year_eps: report.predictNextTwoYearEps,
        predict_this_year_pe: report.predictThisYearPe,
        predict_next_year_pe: report.predictNextYearPe,
        predict_next_two_year_pe: report.predictNextTwoYearPe,
        force: force
      });

      if (response.data.success) {
        const analysis = response.data.data;
        const isCached = response.data.cached;
        
        setAnalysisCache(prev => ({
          ...prev,
          [report.infoCode]: analysis
        }));
        setCurrentReport(report);
        setCurrentAnalysis(analysis);
        setModalVisible(true);
        
        if (isCached) {
          console.log('使用缓存的分析结果');
        }
      }
    } catch (error) {
      console.error('分析研报失败:', error);
    } finally {
      setAnalyzingIds(prev => {
        const newSet = new Set(prev);
        newSet.delete(report.infoCode);
        return newSet;
      });
    }
  };

  const getRatingColor = (rating) => {
    if (!rating || typeof rating !== 'string') return 'default';
    if (rating.includes('买入') || rating.includes('强烈推荐')) return 'red';
    if (rating.includes('增持') || rating.includes('推荐')) return 'orange';
    if (rating.includes('中性') || rating.includes('持有')) return 'blue';
    if (rating.includes('减持') || rating.includes('卖出')) return 'green';
    return 'default';
  };

  const getRatingChangeColor = (change) => {
    if (!change || typeof change !== 'string') return 'default';
    if (change.includes('上调')) return 'red';
    if (change.includes('下调')) return 'green';
    if (change.includes('维持')) return 'blue';
    if (change.includes('首次')) return 'purple';
    return 'default';
  };

  const columns = [
    {
      title: '发布日期',
      dataIndex: 'publishDate',
      key: 'publishDate',
      width: isMobile ? 90 : 110,
      render: (date) => date ? date.substring(0, 10) : '--'
    },
    {
      title: '股票',
      key: 'stock',
      width: isMobile ? 120 : 160,
      render: (_, record) => {
        const isAnalyzing = analyzingIds.has(record.infoCode);
        const analysis = analysisCache[record.infoCode];
        return (
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <div>
              <div 
                style={{ fontWeight: 500, cursor: 'pointer', color: '#1890ff' }}
                onClick={() => {
                  setSelectedStock({ code: record.stockCode, name: record.stockName });
                  setKlineVisible(true);
                }}
              >
                {record.stockName || '--'}
              </div>
              <div 
                style={{ fontSize: 12, color: '#888', cursor: 'pointer' }}
                onClick={() => {
                  setSelectedStock({ code: record.stockCode, name: record.stockName });
                  setKlineVisible(true);
                }}
              >
                {record.stockCode || '--'}
              </div>
            </div>
            <Button 
              type="primary"
              icon={<RobotOutlined />}
              size="small"
              loading={isAnalyzing}
              onClick={() => analyzeReport(record, false)}
              style={{
                background: analysis ? '#52c41a' : '#722ed1',
                borderColor: analysis ? '#52c41a' : '#722ed1',
                borderRadius: 3
              }}
            />
          </div>
        );
      }
    },
    {
      title: '标题',
      dataIndex: 'title',
      key: 'title',
      ellipsis: true,
      render: (title, record) => (
        <Tooltip title={title}>
          <a 
            href={`https://pdf.dfcfw.com/pdf/H3_${record.infoCode}_1.pdf`}
            target="_blank"
            rel="noopener noreferrer"
            style={{ color: '#1890ff' }}
          >
            {title}
          </a>
        </Tooltip>
      )
    },
    {
      title: '机构',
      dataIndex: 'orgSName',
      key: 'orgSName',
      width: isMobile ? 80 : 120,
      ellipsis: true
    },
    {
      title: '行业',
      dataIndex: 'indvInduName',
      key: 'indvInduName',
      width: isMobile ? 80 : 100,
      ellipsis: true,
      render: (industry) => industry ? (
        <Tag color="cyan" style={{ margin: 0 }}>
          {industry}
        </Tag>
      ) : '--'
    },
    {
      title: (
        <span>
          评级 <Tooltip title={
            <div>
              <div><b>买入</b>：最高级别，强烈推荐</div>
              <div><b>增持/推荐</b>：次高级别，看好但预期涨幅有限</div>
              <div><b>中性/持有</b>：观望，不建议操作</div>
              <div><b>减持/卖出</b>：看空，建议卖出</div>
            </div>
          }><InfoCircleOutlined style={{ marginLeft: 4, color: '#999' }} /></Tooltip>
        </span>
      ),
      dataIndex: 'emRatingName',
      key: 'emRatingName',
      width: isMobile ? 70 : 90,
      render: (rating) => (
        <Tag color={getRatingColor(rating)} style={{ margin: 0 }}>
          {rating || '--'}
        </Tag>
      )
    },
    {
      title: 'EPS预测(今-明-后)',
      key: 'epsForecast',
      width: isMobile ? 120 : 160,
      render: (_, record) => {
        const thisYear = parseFloat(record.predictThisYearEps);
        const nextYear = parseFloat(record.predictNextYearEps);
        const nextTwoYear = parseFloat(record.predictNextTwoYearEps);
        
        const formatNum = (num) => !isNaN(num) ? num.toFixed(2) : '--';
        
        return (
          <span style={{ fontSize: 12 }}>
            {formatNum(thisYear)} → {formatNum(nextYear)} → {formatNum(nextTwoYear)}
          </span>
        );
      }
    },
    {
      title: 'PE预测(今-明-后)',
      key: 'peForecast',
      width: isMobile ? 120 : 160,
      render: (_, record) => {
        const thisYear = parseFloat(record.predictThisYearPe);
        const nextYear = parseFloat(record.predictNextYearPe);
        const nextTwoYear = parseFloat(record.predictNextTwoYearPe);
        
        const formatNum = (num) => !isNaN(num) ? num.toFixed(2) : '--';
        
        return (
          <span style={{ fontSize: 12 }}>
            {formatNum(thisYear)} → {formatNum(nextYear)} → {formatNum(nextTwoYear)}
          </span>
        );
      }
    }
  ];

  const renderMobileCard = (report) => {
    const isAnalyzing = analyzingIds.has(report.infoCode);
    const analysis = analysisCache[report.infoCode];
    
    const thisYearEps = parseFloat(report.predictThisYearEps);
    const nextYearEps = parseFloat(report.predictNextYearEps);
    const nextTwoYearEps = parseFloat(report.predictNextTwoYearEps);
    const thisYearPe = parseFloat(report.predictThisYearPe);
    const nextYearPe = parseFloat(report.predictNextYearPe);
    const nextTwoYearPe = parseFloat(report.predictNextTwoYearPe);
    
    const formatNum = (num) => !isNaN(num) ? num.toFixed(2) : '--';
    
    return (
      <Card
        key={report.infoCode}
        style={{
          marginBottom: 12,
          borderLeft: '3px solid #1890ff',
          transition: 'all 0.3s ease'
        }}
        styles={{ body: { padding: isMobile ? 12 : 16 } }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
          <div style={{ flex: 1 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6, flexWrap: 'wrap' }}>
              <span style={{ fontSize: 12, color: '#999' }}>{report.publishDate ? report.publishDate.substring(0, 10) : '--'}</span>
              <Tag color="blue" style={{ margin: 0 }}>{report.orgSName || '--'}</Tag>
              {report.indvInduName && (
                <Tag color="cyan" style={{ margin: 0 }}>
                  {report.indvInduName}
                </Tag>
              )}
              <Tag color={getRatingColor(report.emRatingName)} style={{ margin: 0 }}>
                {report.emRatingName || '--'}
              </Tag>
            </div>
            
            <div 
              onClick={() => handleStockClick(report.stockCode, report.stockName)}
              style={{ fontSize: isMobile ? 14 : 16, fontWeight: 500, marginBottom: 6, color: '#1890ff', cursor: 'pointer' }}
            >
              {report.stockName || '--'}
              <span style={{ fontSize: 12, color: '#999', marginLeft: 8, fontWeight: 'normal' }}>{report.stockCode || '--'}</span>
            </div>
            
            <a 
              href={`https://pdf.dfcfw.com/pdf/H3_${report.infoCode}_1.pdf`}
              target="_blank"
              rel="noopener noreferrer"
              style={{ color: '#1890ff', fontSize: 13, display: 'block', marginBottom: 8, lineHeight: 1.5 }}
            >
              {report.title}
            </a>
            
            <div style={{ fontSize: 13, color: '#666', lineHeight: 1.6 }}>
              <div>
                <span style={{ color: '#999' }}>EPS预测：</span>
                {formatNum(thisYearEps)} → {formatNum(nextYearEps)} → {formatNum(nextTwoYearEps)}
              </div>
              <div>
                <span style={{ color: '#999' }}>PE预测：</span>
                {formatNum(thisYearPe)} → {formatNum(nextYearPe)} → {formatNum(nextTwoYearPe)}
              </div>
            </div>
          </div>
          
          <div style={{ marginLeft: 12, display: 'flex', flexDirection: 'column', gap: 8 }}>
            <Button
              type="primary"
              icon={<RobotOutlined />}
              onClick={() => analyzeReport(report, false)}
              loading={isAnalyzing}
              style={{
                background: analysis ? '#52c41a' : '#722ed1',
                borderColor: analysis ? '#52c41a' : '#722ed1',
                borderRadius: 3
              }}
              size="small"
            >
              {isMobile ? '' : (analysis ? '查看分析' : 'AI分析')}
            </Button>
          </div>
        </div>
      </Card>
    );
  };

  return (
    <div style={{ padding: isMobile ? 0 : 12 }}>
      <div style={{ marginBottom: 12, display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
        <div style={{ fontSize: isMobile ? 14 : 16, fontWeight: 'bold', display: 'flex', alignItems: 'center' }}>
          <FileTextOutlined style={{ color: '#1890ff', marginRight: 8 }} />
          研报解读
          {loading && !loadingMore && (
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              color: '#1890ff',
              fontSize: 12,
              marginLeft: 12
            }}>
              <Spin size="small" />
              <span>加载中...</span>
            </div>
          )}
        </div>
        <Input
          placeholder="输入股票代码搜索"
          value={searchCode}
          onChange={handleSearchChange}
          allowClear
          onClear={handleReset}
          style={{ width: isMobile ? 150 : 250 }}
        />
      </div>

      {loading && !loadingMore ? (
        <div style={{ textAlign: 'center', padding: '100px 0' }}>
          <Spin size="large" />
          <div style={{ marginTop: 16, color: '#999' }}>加载研报数据...</div>
        </div>
      ) : reports.length === 0 ? (
        <Empty description="暂无研报数据" />
      ) : isMobile ? (
        <div>
          {reports.map(report => renderMobileCard(report))}
          {loadingMore && (
            <div style={{ textAlign: 'center', padding: '20px 0' }}>
              <Spin />
              <div style={{ marginTop: 8, color: '#999' }}>加载更多研报...</div>
            </div>
          )}
          {!loadingMore && pagination.current < pagination.total && (
            <div style={{ textAlign: 'center', padding: '16px 0', color: '#999', fontSize: 12 }}>
              下拉加载更多
            </div>
          )}
          {pagination.current >= pagination.total && reports.length > 0 && (
            <div style={{ textAlign: 'center', padding: '16px 0', color: '#999', fontSize: 12 }}>
              已加载全部研报
            </div>
          )}
        </div>
      ) : (
        <Card style={{ marginTop: 16 }}>
          <Table
            dataSource={reports}
            columns={columns}
            rowKey="infoCode"
            pagination={{
              ...pagination,
              showSizeChanger: false,
              showTotal: (total) => `共 ${total} 条`
            }}
            onChange={handleTableChange}
            scroll={{ x: 1000 }}
            size="middle"
          />
        </Card>
      )}

      <Modal
        title={
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <ThunderboltOutlined style={{ color: '#1890ff' }} />
            <span>研报AI分析</span>
          </div>
        }
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        footer={[
          <Button key="close" onClick={() => setModalVisible(false)}>
            关闭
          </Button>,
          currentReport && (
            <Button 
              key="reanalyze" 
              type="primary"
              onClick={() => {
                setModalVisible(false);
                analyzeReport(currentReport, true);
              }}
            >
              重新分析
            </Button>
          )
        ]}
        width={isMobile ? '95%' : 600}
      >
        {currentReport && (
          <div style={{ marginBottom: 16 }}>
            <div style={{ fontWeight: 500, marginBottom: 8 }}>{currentReport.title}</div>
            <div 
              style={{ fontSize: 12, color: '#1890ff', cursor: 'pointer' }}
              onClick={() => {
                setSelectedStock({ code: currentReport.stockCode, name: currentReport.stockName });
                setKlineVisible(true);
              }}
            >
              {currentReport.stockName} ({currentReport.stockCode})
            </div>
          </div>
        )}
        {currentAnalysis && (
          <div style={{ padding: 12, background: '#f5f5f5', borderRadius: 6 }}>
            <div style={{ fontSize: 13, color: '#333', lineHeight: 1.6 }}>
              {currentAnalysis.analysis}
            </div>
            {currentAnalysis.related_stocks && currentAnalysis.related_stocks.length > 0 && (
              <div style={{ marginTop: 12 }}>
                <div style={{ fontSize: 12, color: '#666', marginBottom: 6 }}>相关个股:</div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                  {currentAnalysis.related_stocks.map((stock, idx) => {
                    const stockCode = typeof stock === 'string' ? stock : stock.code || '';
                    const stockName = typeof stock === 'string' ? stock : stock.name || stock.code || '';
                    return (
                      <Tag 
                        key={idx} 
                        color="blue" 
                        style={{ cursor: 'pointer' }}
                        onClick={() => {
                          if (stockCode) {
                            setSelectedStock({ code: stockCode, name: stockName });
                            setKlineVisible(true);
                          }
                        }}
                      >
                        {stockName}
                      </Tag>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        )}
      </Modal>

      <StockKlineModal
        visible={klineVisible}
        stockCode={selectedStock?.code}
        stockName={selectedStock?.name}
        onClose={() => setKlineVisible(false)}
      />

      {isMobile && showBackTop && (
        <div
          onClick={scrollToTop}
          style={{
            position: 'fixed',
            right: 16,
            bottom: 70,
            width: 36,
            height: 36,
            borderRadius: 8,
            background: '#1890ff',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 2px 8px rgba(24, 144, 255, 0.4)',
            cursor: 'pointer',
            zIndex: 100,
            transition: 'all 0.3s'
          }}
        >
          <UpOutlined style={{ color: '#fff', fontSize: 14 }} />
        </div>
      )}
    </div>
  );
};

export default ReportPage;
