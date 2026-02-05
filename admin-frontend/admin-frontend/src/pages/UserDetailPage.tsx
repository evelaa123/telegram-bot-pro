import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Card,
  Descriptions,
  Table,
  Button,
  Space,
  Tag,
  Typography,
  message,
  Popconfirm,
  Modal,
  Form,
  InputNumber,
  Input,
  Spin,
  Alert,
} from 'antd';
import {
  ArrowLeftOutlined,
  StopOutlined,
  CheckOutlined,
  SendOutlined,
  SettingOutlined,
  CrownOutlined,
} from '@ant-design/icons';
import { usersApi } from '../services/api';
import dayjs from 'dayjs';

const { Title, Text } = Typography;
const { TextArea } = Input;

interface User {
  id: number;
  telegram_id: number;
  username: string | null;
  first_name: string | null;
  last_name: string | null;
  language_code: string | null;
  is_blocked: boolean;
  custom_limits: { [key: string]: number } | null;
  settings: { [key: string]: unknown } | null;
  created_at: string;
  updated_at: string;
  last_active_at: string | null;
  total_requests: number;
  // Subscription fields
  subscription_type: string | null;
  subscription_expires_at: string | null;
  has_active_subscription: boolean;
}

interface UserRequest {
  id: number;
  type: string;
  prompt: string | null;
  response_preview: string | null;
  model: string | null;
  status: string;
  cost_usd: number | null;
  duration_ms: number | null;
  created_at: string;
}

function UserDetailPage() {
  const { telegramId } = useParams<{ telegramId: string }>();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [user, setUser] = useState<User | null>(null);
  const [requests, setRequests] = useState<UserRequest[]>([]);
  const [limitsModalOpen, setLimitsModalOpen] = useState(false);
  const [messageModalOpen, setMessageModalOpen] = useState(false);
  const [limitsForm] = Form.useForm();
  const [messageForm] = Form.useForm();

  useEffect(() => {
    if (telegramId) {
      fetchUser();
      fetchRequests();
    }
  }, [telegramId]);

  const fetchUser = async () => {
    try {
      const response = await usersApi.get(Number(telegramId));
      setUser(response.data);
    } catch (error) {
      console.error('Failed to fetch user:', error);
      message.error('User not found');
      navigate('/users');
    } finally {
      setLoading(false);
    }
  };

  const fetchRequests = async () => {
    try {
      const response = await usersApi.getRequests(Number(telegramId), 100);
      setRequests(response.data.requests);
    } catch (error) {
      console.error('Failed to fetch requests:', error);
    }
  };

  const handleBlock = async () => {
    try {
      await usersApi.block(Number(telegramId));
      message.success('User blocked');
      fetchUser();
    } catch {
      message.error('Failed to block user');
    }
  };

  const handleUnblock = async () => {
    try {
      await usersApi.unblock(Number(telegramId));
      message.success('User unblocked');
      fetchUser();
    } catch {
      message.error('Failed to unblock user');
    }
  };

  const handleUpdateLimits = async (values: { [key: string]: number }) => {
    try {
      await usersApi.updateLimits(Number(telegramId), values);
      message.success('Limits updated');
      setLimitsModalOpen(false);
      fetchUser();
    } catch {
      message.error('Failed to update limits');
    }
  };

  const handleResetLimits = async () => {
    try {
      await usersApi.resetLimits(Number(telegramId));
      message.success('Limits reset to defaults');
      fetchUser();
    } catch {
      message.error('Failed to reset limits');
    }
  };

  const handleSendMessage = async (values: { message: string }) => {
    try {
      await usersApi.sendMessage(Number(telegramId), values.message);
      message.success('Message sent');
      setMessageModalOpen(false);
      messageForm.resetFields();
    } catch {
      message.error('Failed to send message');
    }
  };

  const requestColumns = [
    {
      title: 'Time',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 150,
      render: (date: string) => dayjs(date).format('DD.MM.YY HH:mm'),
    },
    {
      title: 'Type',
      dataIndex: 'type',
      key: 'type',
      width: 100,
      render: (type: string) => <Tag>{type}</Tag>,
    },
    {
      title: 'Prompt',
      dataIndex: 'prompt',
      key: 'prompt',
      ellipsis: true,
    },
    {
      title: 'Model',
      dataIndex: 'model',
      key: 'model',
      width: 120,
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => (
        <Tag color={status === 'success' ? 'green' : 'red'}>{status}</Tag>
      ),
    },
    {
      title: 'Cost',
      dataIndex: 'cost_usd',
      key: 'cost_usd',
      width: 100,
      render: (cost: number | null) => (cost ? `$${cost.toFixed(4)}` : '-'),
    },
  ];

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: 100 }}>
        <Spin size="large" />
      </div>
    );
  }

  if (!user) {
    return null;
  }

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/users')}>
          Back to Users
        </Button>
      </div>

      <Card style={{ marginBottom: 24 }}>
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            marginBottom: 16,
          }}
        >
          <Title level={4} style={{ margin: 0 }}>
            User: {user.username ? `@${user.username}` : user.telegram_id}
          </Title>
          <Space>
            <Button
              icon={<SettingOutlined />}
              onClick={() => {
                limitsForm.setFieldsValue(user.custom_limits || {});
                setLimitsModalOpen(true);
              }}
            >
              Set Limits
            </Button>
            <Button
              icon={<SendOutlined />}
              onClick={() => setMessageModalOpen(true)}
            >
              Send Message
            </Button>
            {user.is_blocked ? (
              <Popconfirm title="Unblock this user?" onConfirm={handleUnblock}>
                <Button icon={<CheckOutlined />}>Unblock</Button>
              </Popconfirm>
            ) : (
              <Popconfirm title="Block this user?" onConfirm={handleBlock}>
                <Button danger icon={<StopOutlined />}>
                  Block
                </Button>
              </Popconfirm>
            )}
          </Space>
        </div>

        <Descriptions bordered column={2}>
          <Descriptions.Item label="Telegram ID">
            {user.telegram_id}
          </Descriptions.Item>
          <Descriptions.Item label="Username">
            {user.username ? `@${user.username}` : '-'}
          </Descriptions.Item>
          <Descriptions.Item label="Name">
            {[user.first_name, user.last_name].filter(Boolean).join(' ') || '-'}
          </Descriptions.Item>
          <Descriptions.Item label="Language">
            {user.language_code || '-'}
          </Descriptions.Item>
          <Descriptions.Item label="Status">
            {user.is_blocked ? (
              <Tag color="red">Blocked</Tag>
            ) : (
              <Tag color="green">Active</Tag>
            )}
          </Descriptions.Item>
          <Descriptions.Item label="Subscription">
            {user.has_active_subscription ? (
              <Space>
                <Tag color="gold" icon={<CrownOutlined />}>
                  {user.subscription_type?.toUpperCase() || 'PREMIUM'}
                </Tag>
                {user.subscription_expires_at && (
                  <Text type="secondary">
                    until {dayjs(user.subscription_expires_at).format('DD.MM.YYYY')}
                  </Text>
                )}
              </Space>
            ) : (
              <Tag>FREE</Tag>
            )}
          </Descriptions.Item>
          <Descriptions.Item label="Total Requests">
            {user.total_requests}
          </Descriptions.Item>
          <Descriptions.Item label="Created">
            {dayjs(user.created_at).format('DD.MM.YYYY HH:mm')}
          </Descriptions.Item>
          <Descriptions.Item label="Last Active">
            {user.last_active_at
              ? dayjs(user.last_active_at).format('DD.MM.YYYY HH:mm')
              : '-'}
          </Descriptions.Item>
          <Descriptions.Item label="Custom Limits" span={2}>
            {user.custom_limits ? (
              <Space wrap>
                {Object.entries(user.custom_limits).map(([key, value]) => (
                  <Tag key={key} color="blue">
                    {key}: {value === -1 ? '∞' : value}
                  </Tag>
                ))}
              </Space>
            ) : (
              <Text type="secondary">Using defaults</Text>
            )}
          </Descriptions.Item>
        </Descriptions>
      </Card>

      <Card title="Request History">
        <Table
          columns={requestColumns}
          dataSource={requests}
          rowKey="id"
          size="small"
          pagination={{ pageSize: 20 }}
        />
      </Card>

      {/* Limits Modal */}
      <Modal
        title="Set Custom Limits"
        open={limitsModalOpen}
        onCancel={() => setLimitsModalOpen(false)}
        footer={[
          <Button key="reset" onClick={handleResetLimits}>
            Reset to Defaults
          </Button>,
          <Button key="cancel" onClick={() => setLimitsModalOpen(false)}>
            Cancel
          </Button>,
          <Button
            key="save"
            type="primary"
            onClick={() => limitsForm.submit()}
          >
            Save
          </Button>,
        ]}
      >
        <Form form={limitsForm} onFinish={handleUpdateLimits} layout="vertical">
          <Alert
            message="Set -1 for unlimited"
            description="Use -1 to give this user unlimited requests for that type"
            type="info"
            showIcon
            style={{ marginBottom: 16 }}
          />
          <Form.Item name="text" label="Text Requests (per day)" extra="-1 = unlimited">
            <InputNumber min={-1} style={{ width: '100%' }} placeholder="Default" />
          </Form.Item>
          <Form.Item name="image" label="Image Generations (per day)" extra="-1 = unlimited">
            <InputNumber min={-1} style={{ width: '100%' }} placeholder="Default" />
          </Form.Item>
          <Form.Item name="video" label="Video Generations (per day)" extra="-1 = unlimited">
            <InputNumber min={-1} style={{ width: '100%' }} placeholder="Default" />
          </Form.Item>
          <Form.Item name="voice" label="Voice Transcriptions (per day)" extra="-1 = unlimited">
            <InputNumber min={-1} style={{ width: '100%' }} placeholder="Default" />
          </Form.Item>
          <Form.Item name="document" label="Document Processing (per day)" extra="-1 = unlimited">
            <InputNumber min={-1} style={{ width: '100%' }} placeholder="Default" />
          </Form.Item>
        </Form>
      </Modal>

      {/* Message Modal */}
      <Modal
        title="Send Message to User"
        open={messageModalOpen}
        onCancel={() => setMessageModalOpen(false)}
        onOk={() => messageForm.submit()}
        okText="Send"
      >
        <Form form={messageForm} onFinish={handleSendMessage}>
          <Form.Item
            name="message"
            rules={[{ required: true, message: 'Please enter a message' }]}
          >
            <TextArea rows={4} placeholder="Enter your message..." />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}

export default UserDetailPage;
