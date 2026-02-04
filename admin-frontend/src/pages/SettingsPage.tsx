import { useEffect, useState } from 'react';
import {
  Card,
  Form,
  InputNumber,
  Input,
  Switch,
  Button,
  Typography,
  message,
  Spin,
  Divider,
  Row,
  Col,
  Select,
} from 'antd';
import { settingsApi } from '../services/api';

const { Title, Text } = Typography;

interface GlobalLimits {
  text: number;
  image: number;
  video: number;
  voice: number;
  document: number;
}

interface BotSettings {
  is_enabled: boolean;
  disabled_message: string;
  subscription_check_enabled: boolean;
  channel_id: number;
  channel_username: string;
}

interface ApiSettings {
  default_gpt_model: string;
  default_image_model: string;
  default_video_model: string;
  default_qwen_model: string;
  default_ai_provider: 'openai' | 'qwen';
  max_context_messages: number;
  context_ttl_seconds: number;
  openai_timeout: number;
}

interface ApiKeysStatus {
  openai_configured: boolean;
  qwen_configured: boolean;
  openai_key_preview: string | null;
  qwen_key_preview: string | null;
}

function SettingsPage() {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [limitsForm] = Form.useForm();
  const [botForm] = Form.useForm();
  const [apiForm] = Form.useForm();
  const [apiKeysForm] = Form.useForm();
  const [apiKeysStatus, setApiKeysStatus] = useState<ApiKeysStatus | null>(null);

  useEffect(() => {
    fetchSettings();
  }, []);

  const fetchSettings = async () => {
    setLoading(true);
    try {
      const response = await settingsApi.getAll();
      const { limits, bot, api, api_keys_status } = response.data;
      limitsForm.setFieldsValue(limits);
      botForm.setFieldsValue(bot);
      apiForm.setFieldsValue(api);
      if (api_keys_status) {
        setApiKeysStatus(api_keys_status);
      }
    } catch (error) {
      console.error('Failed to fetch settings:', error);
      message.error('Failed to load settings');
    } finally {
      setLoading(false);
    }
  };

  const handleSaveLimits = async (values: GlobalLimits) => {
    setSaving(true);
    try {
      await settingsApi.updateLimits(values);
      message.success('Limits saved');
    } catch {
      message.error('Failed to save limits');
    } finally {
      setSaving(false);
    }
  };

  const handleSaveBot = async (values: BotSettings) => {
    setSaving(true);
    try {
      await settingsApi.updateBot(values);
      message.success('Bot settings saved');
    } catch {
      message.error('Failed to save bot settings');
    } finally {
      setSaving(false);
    }
  };

  const handleSaveApi = async (values: ApiSettings) => {
    setSaving(true);
    try {
      await settingsApi.updateApi(values);
      message.success('API settings saved');
    } catch {
      message.error('Failed to save API settings');
    } finally {
      setSaving(false);
    }
  };

  const handleSaveApiKeys = async (values: { openai_api_key?: string; qwen_api_key?: string }) => {
    setSaving(true);
    try {
      // Only send keys that were actually entered
      const keysToUpdate: { openai_api_key?: string; qwen_api_key?: string } = {};
      if (values.openai_api_key && values.openai_api_key.trim()) {
        keysToUpdate.openai_api_key = values.openai_api_key.trim();
      }
      if (values.qwen_api_key && values.qwen_api_key.trim()) {
        keysToUpdate.qwen_api_key = values.qwen_api_key.trim();
      }
      
      if (Object.keys(keysToUpdate).length === 0) {
        message.warning('No API keys to update');
        return;
      }
      
      const response = await settingsApi.updateApiKeys(keysToUpdate);
      message.success(response.data.message || 'API keys updated');
      
      // Refresh status
      const statusResponse = await settingsApi.getApiKeysStatus();
      setApiKeysStatus(statusResponse.data);
      
      // Clear form
      apiKeysForm.resetFields();
    } catch (error: any) {
      message.error(error.response?.data?.detail || 'Failed to save API keys');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: 100 }}>
        <Spin size="large" />
      </div>
    );
  }

  return (
    <div>
      <Title level={3} style={{ marginBottom: 24 }}>
        Settings
      </Title>

      <Row gutter={24}>
        <Col span={12}>
          {/* Global Limits */}
          <Card
            title="Global Limits (per user per day)"
            style={{ marginBottom: 24 }}
          >
            <Form
              form={limitsForm}
              layout="vertical"
              onFinish={handleSaveLimits}
            >
              <Form.Item
                name="text"
                label="Text Requests"
                rules={[{ required: true }]}
              >
                <InputNumber min={0} style={{ width: '100%' }} />
              </Form.Item>
              <Form.Item
                name="image"
                label="Image Generations"
                rules={[{ required: true }]}
              >
                <InputNumber min={0} style={{ width: '100%' }} />
              </Form.Item>
              <Form.Item
                name="video"
                label="Video Generations"
                rules={[{ required: true }]}
              >
                <InputNumber min={0} style={{ width: '100%' }} />
              </Form.Item>
              <Form.Item
                name="voice"
                label="Voice Transcriptions"
                rules={[{ required: true }]}
              >
                <InputNumber min={0} style={{ width: '100%' }} />
              </Form.Item>
              <Form.Item
                name="document"
                label="Document Processing"
                rules={[{ required: true }]}
              >
                <InputNumber min={0} style={{ width: '100%' }} />
              </Form.Item>
              <Form.Item>
                <Button type="primary" htmlType="submit" loading={saving}>
                  Save Limits
                </Button>
              </Form.Item>
            </Form>
          </Card>

          {/* Bot Settings */}
          <Card title="Bot Settings">
            <Form form={botForm} layout="vertical" onFinish={handleSaveBot}>
              <Form.Item
                name="is_enabled"
                label="Bot Enabled"
                valuePropName="checked"
              >
                <Switch />
              </Form.Item>
              <Form.Item
                name="disabled_message"
                label="Disabled Message"
                rules={[{ required: true }]}
              >
                <Input.TextArea rows={2} />
              </Form.Item>
              <Form.Item
                name="subscription_check_enabled"
                label="Subscription Check"
                valuePropName="checked"
              >
                <Switch />
              </Form.Item>
              <Form.Item
                name="channel_id"
                label="Channel ID"
                rules={[{ required: true }]}
              >
                <InputNumber style={{ width: '100%' }} />
              </Form.Item>
              <Form.Item
                name="channel_username"
                label="Channel Username"
                rules={[{ required: true }]}
              >
                <Input placeholder="@channel_name" />
              </Form.Item>
              <Form.Item>
                <Button type="primary" htmlType="submit" loading={saving}>
                  Save Bot Settings
                </Button>
              </Form.Item>
            </Form>
          </Card>
        </Col>

        <Col span={12}>
          {/* API Keys Card */}
          <Card 
            title="🔑 API Keys" 
            style={{ marginBottom: 24 }}
            extra={
              apiKeysStatus && (
                <Text type="secondary">
                  OpenAI: {apiKeysStatus.openai_configured ? '✅' : '❌'} | 
                  Qwen: {apiKeysStatus.qwen_configured ? '✅' : '❌'}
                </Text>
              )
            }
          >
            {apiKeysStatus && (
              <div style={{ marginBottom: 16 }}>
                <Text type="secondary">
                  <strong>Current Status:</strong><br />
                  OpenAI: {apiKeysStatus.openai_configured 
                    ? `Configured (${apiKeysStatus.openai_key_preview})` 
                    : 'Not configured'}<br />
                  Qwen: {apiKeysStatus.qwen_configured 
                    ? `Configured (${apiKeysStatus.qwen_key_preview})` 
                    : 'Not configured'}
                </Text>
              </div>
            )}
            <Divider />
            <Form form={apiKeysForm} layout="vertical" onFinish={handleSaveApiKeys}>
              <Form.Item
                name="openai_api_key"
                label="OpenAI API Key"
                extra="Leave empty to keep current key"
              >
                <Input.Password 
                  placeholder="sk-..." 
                  autoComplete="off"
                />
              </Form.Item>
              <Form.Item
                name="qwen_api_key"
                label="Qwen API Key (DashScope)"
                extra="Leave empty to keep current key"
              >
                <Input.Password 
                  placeholder="sk-..." 
                  autoComplete="off"
                />
              </Form.Item>
              <Form.Item>
                <Button type="primary" htmlType="submit" loading={saving}>
                  Update API Keys
                </Button>
              </Form.Item>
              <Text type="warning">
                ⚠️ Server restart required after updating API keys
              </Text>
            </Form>
          </Card>

          {/* API Settings */}
          <Card title="API Settings">
            <Form form={apiForm} layout="vertical" onFinish={handleSaveApi}>
              <Form.Item
                name="default_ai_provider"
                label="Default AI Provider"
                rules={[{ required: true }]}
              >
                <Select>
                  <Select.Option value="openai">OpenAI</Select.Option>
                  <Select.Option value="qwen">Qwen (Alibaba)</Select.Option>
                </Select>
              </Form.Item>
              <Divider />
              <Form.Item
                name="default_gpt_model"
                label="Default GPT Model (OpenAI)"
                rules={[{ required: true }]}
              >
                <Select>
                  <Select.Option value="gpt-4o">GPT-4o</Select.Option>
                  <Select.Option value="gpt-4o-mini">GPT-4o-mini</Select.Option>
                </Select>
              </Form.Item>
              <Form.Item
                name="default_qwen_model"
                label="Default Qwen Model"
                rules={[{ required: true }]}
              >
                <Select>
                  <Select.Option value="qwen-turbo">Qwen Turbo (Fast)</Select.Option>
                  <Select.Option value="qwen-plus">Qwen Plus (Balanced)</Select.Option>
                  <Select.Option value="qwen-max">Qwen Max (Smart)</Select.Option>
                </Select>
              </Form.Item>
              <Divider />
              <Form.Item
                name="default_image_model"
                label="Default Image Model"
                rules={[{ required: true }]}
              >
                <Select>
                  <Select.Option value="dall-e-3">DALL-E 3</Select.Option>
                </Select>
              </Form.Item>
              <Form.Item
                name="default_video_model"
                label="Default Video Model"
                rules={[{ required: true }]}
              >
                <Select>
                  <Select.Option value="sora-2">Sora 2</Select.Option>
                  <Select.Option value="sora-2-pro">Sora 2 Pro</Select.Option>
                </Select>
              </Form.Item>
              <Divider />
              <Form.Item
                name="max_context_messages"
                label="Max Context Messages"
                rules={[{ required: true }]}
              >
                <InputNumber min={1} max={50} style={{ width: '100%' }} />
              </Form.Item>
              <Form.Item
                name="context_ttl_seconds"
                label="Context TTL (seconds)"
                rules={[{ required: true }]}
              >
                <InputNumber min={60} style={{ width: '100%' }} />
              </Form.Item>
              <Form.Item
                name="openai_timeout"
                label="API Timeout (seconds)"
                rules={[{ required: true }]}
              >
                <InputNumber min={30} max={300} style={{ width: '100%' }} />
              </Form.Item>
              <Form.Item>
                <Button type="primary" htmlType="submit" loading={saving}>
                  Save API Settings
                </Button>
              </Form.Item>
            </Form>
          </Card>

          {/* Info Card */}
          <Card title="Information" style={{ marginTop: 24 }}>
            <Text type="secondary">
              Changes to settings take effect immediately. Be careful when
              modifying limits as it affects all users without custom limits.
            </Text>
            <br /><br />
            <Text type="secondary">
              <strong>AI Providers:</strong><br />
              • <strong>OpenAI</strong> - GPT-4o, DALL-E 3, Sora, Whisper<br />
              • <strong>Qwen</strong> - Text generation only (Alibaba Cloud)
            </Text>
          </Card>
        </Col>
      </Row>
    </div>
  );
}

export default SettingsPage;
