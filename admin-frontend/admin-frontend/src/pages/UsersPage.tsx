import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Table,
  Input,
  Button,
  Space,
  Tag,
  Typography,
  message,
  Popconfirm,
} from 'antd';
import {
  SearchOutlined,
  StopOutlined,
  CheckOutlined,
  EyeOutlined,
  CrownOutlined,
} from '@ant-design/icons';
import { usersApi } from '../services/api';
import dayjs from 'dayjs';

const { Title } = Typography;

interface User {
  id: number;
  telegram_id: number;
  username: string | null;
  first_name: string | null;
  last_name: string | null;
  language_code: string | null;
  is_blocked: boolean;
  custom_limits: object | null;
  created_at: string;
  last_active_at: string | null;
  total_requests: number;
  // Subscription fields
  subscription_type: string | null;
  subscription_expires_at: string | null;
  has_active_subscription: boolean;
}

function UsersPage() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [users, setUsers] = useState<User[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(50);
  const [search, setSearch] = useState('');

  useEffect(() => {
    fetchUsers();
  }, [page, pageSize, search]);

  const fetchUsers = async () => {
    setLoading(true);
    try {
      const response = await usersApi.list({
        page,
        page_size: pageSize,
        search: search || undefined,
      });
      setUsers(response.data.users);
      setTotal(response.data.total);
    } catch (error) {
      console.error('Failed to fetch users:', error);
      message.error('Failed to load users');
    } finally {
      setLoading(false);
    }
  };

  const handleBlock = async (telegramId: number) => {
    try {
      await usersApi.block(telegramId);
      message.success('User blocked');
      fetchUsers();
    } catch {
      message.error('Failed to block user');
    }
  };

  const handleUnblock = async (telegramId: number) => {
    try {
      await usersApi.unblock(telegramId);
      message.success('User unblocked');
      fetchUsers();
    } catch {
      message.error('Failed to unblock user');
    }
  };

  const columns = [
    {
      title: 'ID',
      dataIndex: 'telegram_id',
      key: 'telegram_id',
      width: 120,
    },
    {
      title: 'Username',
      dataIndex: 'username',
      key: 'username',
      render: (username: string | null) =>
        username ? `@${username}` : <em>No username</em>,
    },
    {
      title: 'Name',
      key: 'name',
      render: (_: unknown, record: User) =>
        [record.first_name, record.last_name].filter(Boolean).join(' ') || '-',
    },
    {
      title: 'Requests',
      dataIndex: 'total_requests',
      key: 'total_requests',
      sorter: (a: User, b: User) => a.total_requests - b.total_requests,
    },
    {
      title: 'Subscription',
      key: 'subscription',
      width: 120,
      render: (_: unknown, record: User) =>
        record.has_active_subscription ? (
          <Tag color="gold" icon={<CrownOutlined />}>
            {record.subscription_type?.toUpperCase() || 'PREMIUM'}
          </Tag>
        ) : (
          <Tag>FREE</Tag>
        ),
    },
    {
      title: 'Status',
      dataIndex: 'is_blocked',
      key: 'is_blocked',
      render: (isBlocked: boolean) =>
        isBlocked ? (
          <Tag color="red">Blocked</Tag>
        ) : (
          <Tag color="green">Active</Tag>
        ),
    },
    {
      title: 'Limits',
      dataIndex: 'custom_limits',
      key: 'custom_limits',
      render: (limits: object | null) =>
        limits ? <Tag color="blue">Custom</Tag> : <Tag>Default</Tag>,
    },
    {
      title: 'Last Active',
      dataIndex: 'last_active_at',
      key: 'last_active_at',
      render: (date: string | null) =>
        date ? dayjs(date).format('DD.MM.YYYY HH:mm') : '-',
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_: unknown, record: User) => (
        <Space>
          <Button
            type="link"
            icon={<EyeOutlined />}
            onClick={() => navigate(`/users/${record.telegram_id}`)}
          >
            View
          </Button>
          {record.is_blocked ? (
            <Popconfirm
              title="Unblock this user?"
              onConfirm={() => handleUnblock(record.telegram_id)}
            >
              <Button type="link" icon={<CheckOutlined />}>
                Unblock
              </Button>
            </Popconfirm>
          ) : (
            <Popconfirm
              title="Block this user?"
              onConfirm={() => handleBlock(record.telegram_id)}
            >
              <Button type="link" danger icon={<StopOutlined />}>
                Block
              </Button>
            </Popconfirm>
          )}
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          marginBottom: 24,
        }}
      >
        <Title level={3} style={{ margin: 0 }}>
          Users
        </Title>
        <Input
          placeholder="Search by ID, username, or name"
          prefix={<SearchOutlined />}
          style={{ width: 300 }}
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
            setPage(1);
          }}
          allowClear
        />
      </div>

      <Table
        columns={columns}
        dataSource={users}
        rowKey="telegram_id"
        loading={loading}
        pagination={{
          current: page,
          pageSize,
          total,
          showSizeChanger: true,
          showTotal: (total) => `Total ${total} users`,
          onChange: (newPage, newPageSize) => {
            setPage(newPage);
            setPageSize(newPageSize);
          },
        }}
      />
    </div>
  );
}

export default UsersPage;
