import { useEffect, useState } from 'react';
import {
  Card,
  Table,
  Tabs,
  Tag,
  Button,
  Statistic,
  Row,
  Col,
  Typography,
  message,
  Popconfirm,
  Progress,
} from 'antd';
import {
  ClockCircleOutlined,
  SyncOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  DeleteOutlined,
} from '@ant-design/icons';
import { tasksApi } from '../services/api';
import dayjs from 'dayjs';

const { Title } = Typography;

interface Task {
  id: number;
  user_telegram_id: number;
  username: string | null;
  prompt: string;
  model: string;
  status: string;
  progress: number;
  error_message: string | null;
  duration_seconds: number;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
}

interface QueueStats {
  queued_count: number;
  in_progress_count: number;
  completed_today: number;
  failed_today: number;
  average_wait_time_seconds: number | null;
  average_processing_time_seconds: number | null;
}

function TasksPage() {
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState<QueueStats | null>(null);
  const [queueTasks, setQueueTasks] = useState<Task[]>([]);
  const [historyTasks, setHistoryTasks] = useState<Task[]>([]);
  const [activeTab, setActiveTab] = useState('queue');

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [statsRes, queueRes, historyRes] = await Promise.all([
        tasksApi.queueStats(),
        tasksApi.queue(),
        tasksApi.history(),
      ]);
      setStats(statsRes.data);
      setQueueTasks(queueRes.data.tasks);
      setHistoryTasks(historyRes.data.tasks);
    } catch (error) {
      console.error('Failed to fetch tasks:', error);
      message.error('Failed to load tasks');
    } finally {
      setLoading(false);
    }
  };

  const handleCancel = async (taskId: number) => {
    try {
      await tasksApi.cancel(taskId);
      message.success('Task cancelled');
      fetchData();
    } catch {
      message.error('Failed to cancel task');
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'queued':
        return <ClockCircleOutlined style={{ color: '#faad14' }} />;
      case 'in_progress':
        return <SyncOutlined spin style={{ color: '#1890ff' }} />;
      case 'completed':
        return <CheckCircleOutlined style={{ color: '#52c41a' }} />;
      case 'failed':
        return <CloseCircleOutlined style={{ color: '#ff4d4f' }} />;
      default:
        return null;
    }
  };

  const getStatusTag = (status: string) => {
    const colors: { [key: string]: string } = {
      queued: 'gold',
      in_progress: 'blue',
      completed: 'green',
      failed: 'red',
    };
    return (
      <Tag icon={getStatusIcon(status)} color={colors[status]}>
        {status.replace('_', ' ')}
      </Tag>
    );
  };

  const columns = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 60,
    },
    {
      title: 'User',
      key: 'user',
      width: 150,
      render: (_: unknown, record: Task) =>
        record.username ? `@${record.username}` : `ID: ${record.user_telegram_id}`,
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
      width: 100,
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      width: 120,
      render: (status: string) => getStatusTag(status),
    },
    {
      title: 'Progress',
      dataIndex: 'progress',
      key: 'progress',
      width: 100,
      render: (progress: number, record: Task) =>
        record.status === 'in_progress' ? (
          <Progress percent={progress} size="small" />
        ) : (
          '-'
        ),
    },
    {
      title: 'Created',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 130,
      render: (date: string) => dayjs(date).format('DD.MM HH:mm'),
    },
  ];

  const queueColumns = [
    ...columns,
    {
      title: 'Actions',
      key: 'actions',
      width: 80,
      render: (_: unknown, record: Task) =>
        record.status === 'queued' ? (
          <Popconfirm
            title="Cancel this task?"
            onConfirm={() => handleCancel(record.id)}
          >
            <Button
              type="link"
              danger
              icon={<DeleteOutlined />}
              size="small"
            >
              Cancel
            </Button>
          </Popconfirm>
        ) : null,
    },
  ];

  const historyColumns = [
    ...columns,
    {
      title: 'Error',
      dataIndex: 'error_message',
      key: 'error_message',
      width: 200,
      ellipsis: true,
      render: (error: string | null) => (error ? <Tag color="red">{error}</Tag> : '-'),
    },
    {
      title: 'Completed',
      dataIndex: 'completed_at',
      key: 'completed_at',
      width: 130,
      render: (date: string | null) =>
        date ? dayjs(date).format('DD.MM HH:mm') : '-',
    },
  ];

  const formatDuration = (seconds: number | null) => {
    if (seconds === null) return '-';
    if (seconds < 60) return `${Math.round(seconds)}s`;
    return `${Math.round(seconds / 60)}m ${Math.round(seconds % 60)}s`;
  };

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
          Task Queue
        </Title>
        <Button onClick={fetchData} loading={loading}>
          Refresh
        </Button>
      </div>

      {/* Stats Cards */}
      {stats && (
        <Row gutter={16} style={{ marginBottom: 24 }}>
          <Col span={6}>
            <Card className="dashboard-card">
              <Statistic
                title="Queued"
                value={stats.queued_count}
                prefix={<ClockCircleOutlined />}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card className="dashboard-card">
              <Statistic
                title="In Progress"
                value={stats.in_progress_count}
                prefix={<SyncOutlined />}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card className="dashboard-card">
              <Statistic
                title="Completed Today"
                value={stats.completed_today}
                valueStyle={{ color: '#52c41a' }}
                prefix={<CheckCircleOutlined />}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card className="dashboard-card">
              <Statistic
                title="Failed Today"
                value={stats.failed_today}
                valueStyle={{ color: '#ff4d4f' }}
                prefix={<CloseCircleOutlined />}
              />
            </Card>
          </Col>
        </Row>
      )}

      {/* Average Times */}
      {stats && (stats.average_wait_time_seconds || stats.average_processing_time_seconds) && (
        <Row gutter={16} style={{ marginBottom: 24 }}>
          <Col span={12}>
            <Card size="small">
              <Statistic
                title="Avg Wait Time"
                value={formatDuration(stats.average_wait_time_seconds)}
              />
            </Card>
          </Col>
          <Col span={12}>
            <Card size="small">
              <Statistic
                title="Avg Processing Time"
                value={formatDuration(stats.average_processing_time_seconds)}
              />
            </Card>
          </Col>
        </Row>
      )}

      {/* Tabs */}
      <Card>
        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          items={[
            {
              key: 'queue',
              label: `Queue (${queueTasks.length})`,
              children: (
                <Table
                  columns={queueColumns}
                  dataSource={queueTasks}
                  rowKey="id"
                  loading={loading}
                  size="small"
                  pagination={false}
                />
              ),
            },
            {
              key: 'history',
              label: 'History',
              children: (
                <Table
                  columns={historyColumns}
                  dataSource={historyTasks}
                  rowKey="id"
                  loading={loading}
                  size="small"
                  pagination={{ pageSize: 20 }}
                />
              ),
            },
          ]}
        />
      </Card>
    </div>
  );
}

export default TasksPage;
