import { useEffect, useState } from 'react';
import { Row, Col, Card, Statistic, Table, Spin, Typography } from 'antd';
import {
  UserOutlined,
  MessageOutlined,
  DollarOutlined,
  ClockCircleOutlined,
} from '@ant-design/icons';
import { statsApi } from '../services/api';

const { Title } = Typography;

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

function DashboardPage() {
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState<DashboardStats | null>(null);

  useEffect(() => {
    fetchStats();
  }, []);

  const fetchStats = async () => {
    try {
      const response = await statsApi.dashboard();
      setStats(response.data);
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
        username || record.first_name || `ID: ${record.telegram_id}`,
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
      render: (cost: number) => `$${cost.toFixed(4)}`,
    },
  ];

  const requestsByTypeColumns = [
    {
      title: 'Type',
      dataIndex: 'label',
      key: 'label',
    },
    {
      title: 'Count',
      dataIndex: 'value',
      key: 'value',
    },
  ];

  return (
    <div>
      <Title level={3} style={{ marginBottom: 24 }}>
        Dashboard
      </Title>

      {/* Today's Stats */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card className="dashboard-card">
            <Statistic
              title="Active Users Today"
              value={stats.active_users_today}
              prefix={<UserOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card className="dashboard-card">
            <Statistic
              title="Requests Today"
              value={stats.total_requests_today}
              prefix={<MessageOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card className="dashboard-card">
            <Statistic
              title="Cost Today"
              value={stats.total_cost_today_usd}
              precision={4}
              prefix={<DollarOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card className="dashboard-card">
            <Statistic
              title="Queue Size"
              value={stats.queue_size}
              prefix={<ClockCircleOutlined />}
            />
          </Card>
        </Col>
      </Row>

      {/* Total Stats */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={8}>
          <Card className="dashboard-card">
            <Statistic
              title="Total Users"
              value={stats.total_users}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col span={8}>
          <Card className="dashboard-card">
            <Statistic
              title="Total Requests"
              value={stats.total_requests}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col span={8}>
          <Card className="dashboard-card">
            <Statistic
              title="Total Cost"
              value={stats.total_cost_usd}
              precision={2}
              prefix="$"
              valueStyle={{ color: '#faad14' }}
            />
          </Card>
        </Col>
      </Row>

      {/* Charts and Tables */}
      <Row gutter={16}>
        <Col span={12}>
          <Card title="Requests by Type (Today)" style={{ marginBottom: 16 }}>
            <Table
              columns={requestsByTypeColumns}
              dataSource={stats.requests_by_type}
              rowKey="label"
              pagination={false}
              size="small"
            />
          </Card>
        </Col>
        <Col span={12}>
          <Card title="Top Users" style={{ marginBottom: 16 }}>
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
    </div>
  );
}

export default DashboardPage;
