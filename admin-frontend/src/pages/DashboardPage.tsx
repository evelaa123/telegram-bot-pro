import { useEffect, useState } from 'react';
import { Row, Col, Card, Statistic, Table, Spin, Typography, Tag, Button } from 'antd';
import {
  UserOutlined,
  MessageOutlined,
  DollarOutlined,
  ClockCircleOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import { statsApi } from '../services/api';
import { useLangStore } from '../store/langStore';

const { Title, Text } = Typography;

interface DashboardStats {
  active_users_today: number;
  total_requests_today: number;
  total_cost_today_usd: number;
  queue_size: number;
  total_users: number;
  total_requests: number;
  total_cost_usd: number;
  hourly_activity: { label: string; value: number }[];
  requests_by_type: { label: string; value: number }[];
  daily_costs: { label: string; value: number }[];
  top_users: {
    telegram_id: number;
    username: string | null;
    first_name: string | null;
    total_requests: number;
    total_cost_usd: number;
  }[];
}

interface CostAnalysis {
  total_cost_usd: number;
  cost_by_model: Record<string, number>;
  cost_by_type: Record<string, number>;
  daily_average_usd: number;
  monthly_projection_usd: number;
}

function DashboardPage() {
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [costData, setCostData] = useState<CostAnalysis | null>(null);
  const { t } = useLangStore();

  useEffect(() => {
    fetchAll();
  }, []);

  const fetchAll = async () => {
    setLoading(true);
    try {
      const [dashRes, costRes] = await Promise.all([
        statsApi.dashboard(),
        statsApi.costs(30),
      ]);
      setStats(dashRes.data);
      setCostData(costRes.data);
    } catch (error) {
      console.error('Failed to fetch stats:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: 100 }}>
        <Spin size="large" />
      </div>
    );
  }

  if (!stats) {
    return <div>Failed to load statistics</div>;
  }

  const topUsersColumns = [
    {
      title: 'User',
      dataIndex: 'username',
      key: 'username',
      render: (username: string | null, record: (typeof stats.top_users)[0]) =>
        username ? `@${username}` : record.first_name || `ID: ${record.telegram_id}`,
    },
    {
      title: 'Requests',
      dataIndex: 'total_requests',
      key: 'total_requests',
    },
    {
      title: 'Cost ($)',
      dataIndex: 'total_cost_usd',
      key: 'total_cost_usd',
      render: (cost: number) => `$${(cost || 0).toFixed(4)}`,
    },
  ];

  const requestsByTypeColumns = [
    {
      title: 'Type',
      dataIndex: 'label',
      key: 'label',
      render: (label: string) => <Tag>{label}</Tag>,
    },
    {
      title: 'Count',
      dataIndex: 'value',
      key: 'value',
    },
  ];

  // Cost by type table data
  const costByTypeData = costData
    ? Object.entries(costData.cost_by_type)
        .map(([type, cost]) => ({ key: type, type, cost }))
        .sort((a, b) => b.cost - a.cost)
    : [];

  // Cost by model table data
  const costByModelData = costData
    ? Object.entries(costData.cost_by_model)
        .map(([model, cost]) => ({ key: model, model, cost }))
        .sort((a, b) => b.cost - a.cost)
    : [];

  // Daily costs (last 7 days) from dashboard data
  const recentDailyCosts = stats.daily_costs.slice(-7);

  return (
    <div>
      <Row justify="space-between" align="middle" style={{ marginBottom: 24 }}>
        <Col>
          <Title level={3} style={{ margin: 0 }}>{t('dash.title')}</Title>
        </Col>
        <Col>
          <Button icon={<ReloadOutlined />} onClick={fetchAll}>{t('dash.refresh')}</Button>
        </Col>
      </Row>

      {/* Today's Stats */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card className="dashboard-card">
            <Statistic
              title={t('dash.active_users_today')}
              value={stats.active_users_today}
              prefix={<UserOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card className="dashboard-card">
            <Statistic
              title={t('dash.requests_today')}
              value={stats.total_requests_today}
              prefix={<MessageOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card className="dashboard-card">
            <Statistic
              title={t('dash.cost_today')}
              value={stats.total_cost_today_usd}
              precision={4}
              prefix={<DollarOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card className="dashboard-card">
            <Statistic
              title={t('dash.queue_size')}
              value={stats.queue_size}
              prefix={<ClockCircleOutlined />}
            />
          </Card>
        </Col>
      </Row>

      {/* Total Stats + Cost Projections */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card className="dashboard-card">
            <Statistic
              title={t('dash.total_users')}
              value={stats.total_users}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card className="dashboard-card">
            <Statistic
              title={t('dash.total_requests')}
              value={stats.total_requests}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card className="dashboard-card">
            <Statistic
              title={t('dash.total_cost_30d')}
              value={costData?.total_cost_usd || stats.total_cost_usd}
              precision={2}
              prefix="$"
              valueStyle={{ color: '#faad14' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card className="dashboard-card">
            <Statistic
              title={t('dash.monthly_projection')}
              value={costData?.monthly_projection_usd || 0}
              precision={2}
              prefix="$"
              valueStyle={{ color: (costData?.monthly_projection_usd || 0) > 100 ? '#ff4d4f' : '#52c41a' }}
            />
            <Text type="secondary" style={{ fontSize: 11 }}>
              Avg: ${(costData?.daily_average_usd || 0).toFixed(4)}/day
            </Text>
          </Card>
        </Col>
      </Row>

      {/* Charts and Tables */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={12}>
          <Card title={t('dash.requests_by_type')} style={{ marginBottom: 16 }}>
            <Table
              columns={requestsByTypeColumns}
              dataSource={stats.requests_by_type.filter(r => r.value > 0)}
              rowKey="label"
              pagination={false}
              size="small"
              locale={{ emptyText: 'No requests today' }}
            />
          </Card>
        </Col>
        <Col span={12}>
          <Card title={t('dash.top_users')} style={{ marginBottom: 16 }}>
            <Table
              columns={topUsersColumns}
              dataSource={stats.top_users}
              rowKey="telegram_id"
              pagination={false}
              size="small"
            />
          </Card>
        </Col>
      </Row>

      {/* Cost Breakdown */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={12}>
          <Card title={t('dash.cost_by_type')}>
            <Table
              columns={[
                { title: 'Type', dataIndex: 'type', key: 'type', render: (t: string) => <Tag>{t}</Tag> },
                { title: 'Cost ($)', dataIndex: 'cost', key: 'cost', render: (c: number) => `$${(c || 0).toFixed(4)}` },
              ]}
              dataSource={costByTypeData}
              rowKey="type"
              pagination={false}
              size="small"
              locale={{ emptyText: 'No cost data' }}
            />
          </Card>
        </Col>
        <Col span={12}>
          <Card title={t('dash.cost_by_model')}>
            <Table
              columns={[
                { title: 'Model', dataIndex: 'model', key: 'model', render: (m: string) => <Text code>{m}</Text> },
                { title: 'Cost ($)', dataIndex: 'cost', key: 'cost', render: (c: number) => `$${(c || 0).toFixed(4)}` },
              ]}
              dataSource={costByModelData}
              rowKey="model"
              pagination={false}
              size="small"
              locale={{ emptyText: 'No cost data' }}
            />
          </Card>
        </Col>
      </Row>

      {/* Recent Daily Costs */}
      <Row gutter={16}>
        <Col span={24}>
          <Card title={t('dash.daily_costs_7d')}>
            <Table
              columns={[
                { title: 'Date', dataIndex: 'label', key: 'label' },
                {
                  title: 'Cost ($)',
                  dataIndex: 'value',
                  key: 'value',
                  render: (v: number) => `$${(v || 0).toFixed(4)}`,
                },
              ]}
              dataSource={recentDailyCosts}
              rowKey="label"
              pagination={false}
              size="small"
              locale={{ emptyText: 'No cost data' }}
            />
          </Card>
        </Col>
      </Row>
    </div>
  );
}

export default DashboardPage;
