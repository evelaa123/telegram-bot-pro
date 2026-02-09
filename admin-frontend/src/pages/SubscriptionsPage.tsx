import { useEffect, useState } from 'react';
import {
  Card,
  Table,
  Typography,
  Spin,
  Row,
  Col,
  Statistic,
  DatePicker,
  Tag,
  message,
} from 'antd';
import {
  DollarOutlined,
  UserOutlined,
  CrownOutlined,
} from '@ant-design/icons';
import { statsApi } from '../services/api';
import { useLangStore } from '../store/langStore';
import dayjs from 'dayjs';

const { Title } = Typography;

interface SubscriptionRecord {
  id: number;
  user_id: number;
  telegram_id: number;
  username: string | null;
  first_name: string | null;
  payment_id: string;
  payment_provider: string;
  amount_rub: number;
  starts_at: string | null;
  expires_at: string | null;
  is_active: boolean;
  created_at: string | null;
}

interface SubscriptionsData {
  year: number;
  month: number;
  total_subscriptions: number;
  total_revenue_rub: number;
  active_premium_users: number;
  subscriptions: SubscriptionRecord[];
}

function SubscriptionsPage() {
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<SubscriptionsData | null>(null);
  const [selectedMonth, setSelectedMonth] = useState(dayjs());
  const { t } = useLangStore();

  useEffect(() => {
    fetchData(selectedMonth.year(), selectedMonth.month() + 1);
  }, [selectedMonth]);

  const fetchData = async (year: number, month: number) => {
    setLoading(true);
    try {
      const response = await statsApi.subscriptionsMonthly(year, month);
      setData(response.data);
    } catch (error) {
      console.error('Failed to fetch subscriptions:', error);
      message.error('Failed to load subscriptions data');
    } finally {
      setLoading(false);
    }
  };

  const columns = [
    {
      title: t('col.user'),
      key: 'user',
      render: (_: any, record: SubscriptionRecord) => (
        <span>
          {record.username ? `@${record.username}` : record.first_name || `ID: ${record.telegram_id}`}
        </span>
      ),
    },
    {
      title: 'Telegram ID',
      dataIndex: 'telegram_id',
      key: 'telegram_id',
    },
    {
      title: t('col.amount'),
      dataIndex: 'amount_rub',
      key: 'amount_rub',
      render: (val: number) => `${val.toFixed(2)} ₽`,
    },
    {
      title: t('col.provider'),
      dataIndex: 'payment_provider',
      key: 'payment_provider',
      render: (val: string) => <Tag color="blue">{val}</Tag>,
    },
    {
      title: t('col.status'),
      dataIndex: 'is_active',
      key: 'is_active',
      render: (val: boolean) => (
        <Tag color={val ? 'green' : 'red'}>{val ? t('subs.active') : t('subs.inactive')}</Tag>
      ),
    },
    {
      title: t('col.start'),
      dataIndex: 'starts_at',
      key: 'starts_at',
      render: (val: string | null) => val ? dayjs(val).format('DD.MM.YY') : '-',
    },
    {
      title: t('col.expires'),
      dataIndex: 'expires_at',
      key: 'expires_at',
      render: (val: string | null) => val ? dayjs(val).format('DD.MM.YY') : '-',
    },
    {
      title: t('col.purchased'),
      dataIndex: 'created_at',
      key: 'created_at',
      render: (val: string | null) => val ? dayjs(val).format('DD.MM.YY HH:mm') : '-',
    },
  ];

  if (loading && !data) {
    return (
      <div style={{ textAlign: 'center', padding: 100 }}>
        <Spin size="large" />
      </div>
    );
  }

  return (
    <div>
      <Title level={3} style={{ marginBottom: 24 }}>
        {t('subs.title')}
      </Title>

      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col>
          <DatePicker
            picker="month"
            value={selectedMonth}
            onChange={(val) => val && setSelectedMonth(val)}
            allowClear={false}
          />
        </Col>
      </Row>

      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={8}>
          <Card>
            <Statistic
              title={t('subs.this_month')}
              value={data?.total_subscriptions || 0}
              prefix={<CrownOutlined />}
            />
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic
              title={t('subs.revenue')}
              value={data?.total_revenue_rub || 0}
              precision={2}
              prefix={<DollarOutlined />}
              suffix="₽"
            />
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic
              title={t('subs.active_premium')}
              value={data?.active_premium_users || 0}
              prefix={<UserOutlined />}
            />
          </Card>
        </Col>
      </Row>

      <Card title={t('subs.history')}>
        <Table
          columns={columns}
          dataSource={data?.subscriptions || []}
          rowKey="id"
          loading={loading}
          pagination={{ pageSize: 20 }}
          locale={{ emptyText: t('subs.no_data') }}
        />
      </Card>
    </div>
  );
}

export default SubscriptionsPage;
