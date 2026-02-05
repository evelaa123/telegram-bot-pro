import { useEffect, useState } from 'react';
import {
  Row,
  Col,
  Card,
  Statistic,
  Table,
  Spin,
  Typography,
  Alert,
  Progress,
  Tag,
  Divider,
  InputNumber,
  Button,
  Space,
} from 'antd';
import {
  DollarOutlined,
  ApiOutlined,
  WarningOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  ReloadOutlined,
  ThunderboltOutlined,
  ExclamationCircleOutlined,
} from '@ant-design/icons';
import { statsApi } from '../services/api';

const { Title, Text } = Typography;

interface ProviderStats {
  requests: number;
  input_tokens: number;
  output_tokens: number;
  cost_usd: number;
  cost_rub: number;
  avg_duration_ms: number;
}

interface ModelStats {
  requests: number;
  cost_usd: number;
}

interface DailyUsageData {
  date: string;
  requests: number;
  cost_usd: number;
  cost_rub: number;
}

interface DailySummary {
  date: string;
  total_requests: number;
  total_cost_usd: number;
  total_cost_rub: number;
  error_count: number;
  error_rate: number;
  by_provider: Record<string, ProviderStats>;
  by_model: Record<string, ModelStats>;
}

interface MonthlySummary {
  year: number;
  month: number;
  total_requests: number;
  total_cost_usd: number;
  total_cost_rub: number;
  projected_monthly_usd: number;
  projected_monthly_rub: number;
  days_elapsed: number;
  days_in_month: number;
  daily_data: DailyUsageData[];
  by_provider: Record<string, ModelStats>;
}

interface CostAlert {
  type: string;
  severity: string;
  message: string;
  current?: number;
  projected?: number;
  budget?: number;
  error_rate?: number;
}

interface ApiUsageData {
  daily: DailySummary;
  monthly: MonthlySummary;
  alerts: CostAlert[];
}

function ApiUsagePage() {
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<ApiUsageData | null>(null);
  const [dailyBudget, setDailyBudget] = useState(10);
  const [monthlyBudget, setMonthlyBudget] = useState(200);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      const response = await statsApi.apiUsage(dailyBudget, monthlyBudget);
      setData(response.data);
    } catch (error) {
      console.error('Failed to fetch API usage data:', error);
    } finally {
      setLoading(false);
    }
  };



  const getAlertIcon = (severity: string) => {
    switch (severity) {
      case 'critical':
        return <ExclamationCircleOutlined />;
      case 'high':
        return <WarningOutlined />;
      default:
        return <ExclamationCircleOutlined />;
    }
  };

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: 100 }}>
        <Spin size="large" />
      </div>
    );
  }

  if (!data) {
    return <Alert type="error" message="Failed to load API usage data" />;
  }

  const { daily, monthly, alerts } = data;

  // Prepare provider table data
  const providerData = Object.entries(daily.by_provider).map(([name, stats]) => ({
    key: name,
    name,
    ...stats,
  }));

  // Prepare model table data
  const modelData = Object.entries(daily.by_model).map(([name, stats]) => ({
    key: name,
    name,
    ...stats,
  }));



  const providerColumns = [
    {
      title: 'Provider',
      dataIndex: 'name',
      key: 'name',
      render: (name: string) => (
        <Tag color={name === 'cometapi' ? 'blue' : name === 'gigachat' ? 'green' : 'purple'}>
          {name.toUpperCase()}
        </Tag>
      ),
    },
    {
      title: 'Requests',
      dataIndex: 'requests',
      key: 'requests',
    },
    {
      title: 'Input Tokens',
      dataIndex: 'input_tokens',
      key: 'input_tokens',
      render: (val: number) => val?.toLocaleString() || '0',
    },
    {
      title: 'Output Tokens',
      dataIndex: 'output_tokens',
      key: 'output_tokens',
      render: (val: number) => val?.toLocaleString() || '0',
    },
    {
      title: 'Cost (USD)',
      dataIndex: 'cost_usd',
      key: 'cost_usd',
      render: (val: number) => `$${val?.toFixed(4) || '0.0000'}`,
    },
    {
      title: 'Cost (RUB)',
      dataIndex: 'cost_rub',
      key: 'cost_rub',
      render: (val: number) => `${val?.toFixed(2) || '0.00'}`,
    },
    {
      title: 'Avg Duration',
      dataIndex: 'avg_duration_ms',
      key: 'avg_duration_ms',
      render: (val: number) => `${(val / 1000)?.toFixed(2) || '0.00'}s`,
    },
  ];

  const modelColumns = [
    {
      title: 'Model',
      dataIndex: 'name',
      key: 'name',
      render: (name: string) => <Text code>{name}</Text>,
    },
    {
      title: 'Requests',
      dataIndex: 'requests',
      key: 'requests',
    },
    {
      title: 'Cost (USD)',
      dataIndex: 'cost_usd',
      key: 'cost_usd',
      render: (val: number) => `$${val?.toFixed(4) || '0.0000'}`,
    },
  ];

  const dailyBudgetUsed = (daily.total_cost_usd / dailyBudget) * 100;
  const monthlyBudgetUsed = (monthly.total_cost_usd / monthlyBudget) * 100;

  return (
    <div style={{ padding: 24 }}>
      <Row justify="space-between" align="middle" style={{ marginBottom: 24 }}>
        <Col>
          <Title level={3} style={{ margin: 0 }}>
            <ApiOutlined /> API Usage & Cost Monitoring
          </Title>
        </Col>
        <Col>
          <Space>
            <Text>Daily Budget:</Text>
            <InputNumber
              prefix="$"
              value={dailyBudget}
              onChange={(v) => setDailyBudget(v || 10)}
              min={1}
              max={1000}
              style={{ width: 100 }}
            />
            <Text>Monthly Budget:</Text>
            <InputNumber
              prefix="$"
              value={monthlyBudget}
              onChange={(v) => setMonthlyBudget(v || 200)}
              min={10}
              max={10000}
              style={{ width: 100 }}
            />
            <Button icon={<ReloadOutlined />} onClick={fetchData}>
              Refresh
            </Button>
          </Space>
        </Col>
      </Row>

      {/* Alerts */}
      {alerts.length > 0 && (
        <Row gutter={16} style={{ marginBottom: 24 }}>
          <Col span={24}>
            {alerts.map((alert, idx) => (
              <Alert
                key={idx}
                type={alert.severity === 'critical' ? 'error' : alert.severity === 'high' ? 'warning' : 'info'}
                message={alert.message}
                icon={getAlertIcon(alert.severity)}
                showIcon
                style={{ marginBottom: 8 }}
              />
            ))}
          </Col>
        </Row>
      )}

      {/* Daily Stats */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card className="dashboard-card">
            <Statistic
              title="Today's Requests"
              value={daily.total_requests}
              prefix={<ThunderboltOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card className="dashboard-card">
            <Statistic
              title="Today's Cost (USD)"
              value={daily.total_cost_usd}
              precision={4}
              prefix={<DollarOutlined />}
              valueStyle={{ color: dailyBudgetUsed > 80 ? '#ff4d4f' : '#52c41a' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card className="dashboard-card">
            <Statistic
              title="Today's Cost (RUB)"
              value={daily.total_cost_rub}
              precision={2}
              prefix=""
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card className="dashboard-card">
            <Statistic
              title="Error Rate"
              value={daily.error_rate}
              precision={1}
              suffix="%"
              valueStyle={{ color: daily.error_rate > 5 ? '#ff4d4f' : '#52c41a' }}
              prefix={daily.error_rate > 5 ? <WarningOutlined /> : <CheckCircleOutlined />}
            />
          </Card>
        </Col>
      </Row>

      {/* Budget Progress */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={12}>
          <Card title="Daily Budget Usage">
            <Progress
              percent={Math.min(dailyBudgetUsed, 100)}
              status={dailyBudgetUsed > 100 ? 'exception' : dailyBudgetUsed > 80 ? 'active' : 'normal'}
              strokeColor={dailyBudgetUsed > 100 ? '#ff4d4f' : dailyBudgetUsed > 80 ? '#faad14' : '#52c41a'}
              format={() => `$${daily.total_cost_usd.toFixed(2)} / $${dailyBudget}`}
            />
          </Card>
        </Col>
        <Col span={12}>
          <Card title="Monthly Budget Usage">
            <Progress
              percent={Math.min(monthlyBudgetUsed, 100)}
              status={monthlyBudgetUsed > 100 ? 'exception' : monthlyBudgetUsed > 80 ? 'active' : 'normal'}
              strokeColor={monthlyBudgetUsed > 100 ? '#ff4d4f' : monthlyBudgetUsed > 80 ? '#faad14' : '#52c41a'}
              format={() => `$${monthly.total_cost_usd.toFixed(2)} / $${monthlyBudget}`}
            />
            <Divider />
            <Row>
              <Col span={12}>
                <Statistic
                  title="Projected Monthly"
                  value={monthly.projected_monthly_usd}
                  precision={2}
                  prefix="$"
                  valueStyle={{
                    fontSize: 16,
                    color: monthly.projected_monthly_usd > monthlyBudget ? '#ff4d4f' : '#52c41a',
                  }}
                />
              </Col>
              <Col span={12}>
                <Statistic
                  title="Days Remaining"
                  value={monthly.days_in_month - monthly.days_elapsed}
                  suffix={`/ ${monthly.days_in_month}`}
                  prefix={<ClockCircleOutlined />}
                  valueStyle={{ fontSize: 16 }}
                />
              </Col>
            </Row>
          </Card>
        </Col>
      </Row>

      {/* Monthly Stats */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card className="dashboard-card">
            <Statistic
              title="Monthly Requests"
              value={monthly.total_requests}
              prefix={<ThunderboltOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card className="dashboard-card">
            <Statistic
              title="Monthly Cost (USD)"
              value={monthly.total_cost_usd}
              precision={2}
              prefix={<DollarOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card className="dashboard-card">
            <Statistic
              title="Monthly Cost (RUB)"
              value={monthly.total_cost_rub}
              precision={2}
              prefix=""
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card className="dashboard-card">
            <Statistic
              title="Projected (RUB)"
              value={monthly.projected_monthly_rub}
              precision={2}
              prefix=""
            />
          </Card>
        </Col>
      </Row>

      {/* Provider Breakdown */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={24}>
          <Card title="Today's Usage by Provider">
            <Table
              columns={providerColumns}
              dataSource={providerData}
              pagination={false}
              size="small"
              locale={{ emptyText: 'No API calls today' }}
            />
          </Card>
        </Col>
      </Row>

      {/* Model Breakdown */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={12}>
          <Card title="Today's Usage by Model">
            <Table
              columns={modelColumns}
              dataSource={modelData}
              pagination={false}
              size="small"
              scroll={{ y: 300 }}
              locale={{ emptyText: 'No API calls today' }}
            />
          </Card>
        </Col>
        <Col span={12}>
          <Card title="Monthly Usage by Provider">
            <Table
              columns={[
                {
                  title: 'Provider',
                  dataIndex: 'name',
                  key: 'name',
                  render: (name: string) => (
                    <Tag color={name === 'cometapi' ? 'blue' : name === 'gigachat' ? 'green' : 'purple'}>
                      {name.toUpperCase()}
                    </Tag>
                  ),
                },
                {
                  title: 'Requests',
                  dataIndex: 'requests',
                  key: 'requests',
                },
                {
                  title: 'Cost (USD)',
                  dataIndex: 'cost_usd',
                  key: 'cost_usd',
                  render: (val: number) => `$${val?.toFixed(4) || '0.0000'}`,
                },
              ]}
              dataSource={Object.entries(monthly.by_provider).map(([name, stats]) => ({
                key: name,
                name,
                ...stats,
              }))}
              pagination={false}
              size="small"
              locale={{ emptyText: 'No API calls this month' }}
            />
          </Card>
        </Col>
      </Row>

      {/* Daily Cost Chart (Simple Table View) */}
      <Row gutter={16}>
        <Col span={24}>
          <Card title="Monthly Daily Costs">
            <Table
              columns={[
                {
                  title: 'Date',
                  dataIndex: 'date',
                  key: 'date',
                },
                {
                  title: 'Requests',
                  dataIndex: 'requests',
                  key: 'requests',
                },
                {
                  title: 'Cost (USD)',
                  dataIndex: 'cost_usd',
                  key: 'cost_usd',
                  render: (val: number) => `$${val?.toFixed(4) || '0.0000'}`,
                },
                {
                  title: 'Cost (RUB)',
                  dataIndex: 'cost_rub',
                  key: 'cost_rub',
                  render: (val: number) => `${val?.toFixed(2) || '0.00'}`,
                },
              ]}
              dataSource={monthly.daily_data.map((d, idx) => ({ ...d, key: idx }))}
              pagination={{ pageSize: 10 }}
              size="small"
              locale={{ emptyText: 'No data this month' }}
            />
          </Card>
        </Col>
      </Row>
    </div>
  );
}

export default ApiUsagePage;
