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
  Alert,
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
  default_text_model: string;
  default_image_model: string;
  default_video_model: string;
  default_voice_model: string;
  default_gigachat_model: string;
  default_ai_provider: string;
  max_context_messages: number;
  context_ttl_seconds: number;
  openai_timeout: number;
}

interface ApiKeysStatus {
  cometapi_configured: boolean;
  gigachat_configured: boolean;
  openai_configured: boolean;
  cometapi_key_preview: string | null;
  openai_key_preview: string | null;
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

  const handleSaveApiKeys = async (values: { cometapi_api_key?: string; gigachat_credentials?: string; openai_api_key?: string }) => {
    setSaving(true);
    try {
      // Only send keys that were actually entered
      const keysToUpdate: { cometapi_api_key?: string; gigachat_credentials?: string; openai_api_key?: string } = {};
      if (values.cometapi_api_key && values.cometapi_api_key.trim()) {
        keysToUpdate.cometapi_api_key = values.cometapi_api_key.trim();
      }
      if (values.gigachat_credentials && values.gigachat_credentials.trim()) {
        keysToUpdate.gigachat_credentials = values.gigachat_credentials.trim();
      }
      if (values.openai_api_key && values.openai_api_key.trim()) {
        keysToUpdate.openai_api_key = values.openai_api_key.trim();
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
          {/* AI Provider Status */}
          <Card 
            title="🤖 AI Provider Configuration" 
            style={{ marginBottom: 24 }}
          >
            <Alert
              message="AI Models Routing via CometAPI"
              description={
                <div>
                  <p><strong>Text/Vision:</strong> Configurable (default: qwen3-max-2026-01-23)</p>
                  <p><strong>Images:</strong> Configurable (default: dall-e-3)</p>
                  <p><strong>Video:</strong> Configurable (default: sora-2)</p>
                  <p><strong>Voice:</strong> Configurable (default: whisper-1)</p>
                  <p><strong>Presentations:</strong> GigaChat (separate API)</p>
                  <p style={{ marginTop: 8, color: '#666' }}>
                    <em>Configure models in the "AI Models Configuration" section below.</em>
                  </p>
                </div>
              }
              type="info"
              showIcon
              style={{ marginBottom: 16 }}
            />
            
            {apiKeysStatus && (
              <div>
                <Divider orientation="left">Provider Status</Divider>
                <Row gutter={16}>
                  <Col span={8}>
                    <Card size="small" style={{ textAlign: 'center' }}>
                      <div style={{ fontSize: 24 }}>
                        {apiKeysStatus.cometapi_configured ? '✅' : '❌'}
                      </div>
                      <Text strong>CometAPI</Text>
                      <br />
                      <Text type="secondary" style={{ fontSize: 10 }}>
                        {apiKeysStatus.cometapi_key_preview || 'Not configured'}
                      </Text>
                    </Card>
                  </Col>
                  <Col span={8}>
                    <Card size="small" style={{ textAlign: 'center' }}>
                      <div style={{ fontSize: 24 }}>
                        {apiKeysStatus.gigachat_configured ? '✅' : '❌'}
                      </div>
                      <Text strong>GigaChat</Text>
                      <br />
                      <Text type="secondary" style={{ fontSize: 10 }}>
                        {apiKeysStatus.gigachat_configured ? 'Configured' : 'Not configured'}
                      </Text>
                    </Card>
                  </Col>
                  <Col span={8}>
                    <Card size="small" style={{ textAlign: 'center' }}>
                      <div style={{ fontSize: 24 }}>
                        {apiKeysStatus.openai_configured ? '✅' : '⚠️'}
                      </div>
                      <Text strong>OpenAI</Text>
                      <br />
                      <Text type="secondary" style={{ fontSize: 10 }}>
                        {apiKeysStatus.openai_key_preview || 'Fallback only'}
                      </Text>
                    </Card>
                  </Col>
                </Row>
              </div>
            )}
          </Card>

          {/* Global Limits */}
          <Card
            title="📊 Global Limits (per user per day)"
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
          <Card title="🤖 Bot Settings">
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
          >
            <Alert
              message="CometAPI is the primary provider"
              description="All text, image, video, and voice operations go through CometAPI. GigaChat is used for presentation generation. OpenAI is a fallback option."
              type="warning"
              showIcon
              style={{ marginBottom: 16 }}
            />
            
            <Form form={apiKeysForm} layout="vertical" onFinish={handleSaveApiKeys}>
              <Form.Item
                name="cometapi_api_key"
                label="CometAPI API Key (Primary)"
                extra="Main provider for text/image/video/voice operations"
              >
                <Input.Password 
                  placeholder="sk-..." 
                  autoComplete="off"
                />
              </Form.Item>
              <Form.Item
                name="gigachat_credentials"
                label="GigaChat Credentials (Base64)"
                extra="For presentation generation. Format: Base64(client_id:client_secret)"
              >
                <Input.Password 
                  placeholder="Base64 encoded credentials" 
                  autoComplete="off"
                />
              </Form.Item>
              <Divider />
              <Form.Item
                name="openai_api_key"
                label="OpenAI API Key (Fallback)"
                extra="Used when CometAPI is not configured"
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

          {/* Model Configuration */}
          <Card title="🎯 AI Models Configuration" style={{ marginBottom: 24 }}>
            <Alert
              message="Configurable Models"
              description="These models are used via CometAPI. You can manually enter model names as they appear in CometAPI (e.g., qwen3-max-2026-01-23)."
              type="info"
              showIcon
              style={{ marginBottom: 16 }}
            />
            <Form form={apiForm} layout="vertical" onFinish={handleSaveApi}>
              <Form.Item
                name="default_text_model"
                label="Text Generation Model"
                rules={[{ required: true }]}
                extra="Model for text/chat (e.g., qwen3-max-2026-01-23, gpt-4o)"
              >
                <Input placeholder="qwen3-max-2026-01-23" />
              </Form.Item>
              <Form.Item
                name="default_image_model"
                label="Image Generation Model"
                rules={[{ required: true }]}
                extra="Model for images (e.g., dall-e-3)"
              >
                <Input placeholder="dall-e-3" />
              </Form.Item>
              <Form.Item
                name="default_video_model"
                label="Video Generation Model"
                rules={[{ required: true }]}
                extra="Model for videos (e.g., sora-2, sora-2-pro)"
              >
                <Input placeholder="sora-2" />
              </Form.Item>
              <Form.Item
                name="default_voice_model"
                label="Speech Recognition Model"
                rules={[{ required: true }]}
                extra="Model for voice (e.g., whisper-1)"
              >
                <Input placeholder="whisper-1" />
              </Form.Item>
              <Form.Item
                name="default_gigachat_model"
                label="GigaChat Model (Presentations)"
                rules={[{ required: true }]}
                extra="GigaChat model for presentations (e.g., GigaChat-2-Max)"
              >
                <Input placeholder="GigaChat-2-Max" />
              </Form.Item>
              <Divider />
              <Form.Item
                name="max_context_messages"
                label="Max Context Messages"
                rules={[{ required: true }]}
                extra="Number of messages to keep in conversation context"
              >
                <InputNumber min={1} max={100} style={{ width: '100%' }} />
              </Form.Item>
              <Form.Item
                name="context_ttl_seconds"
                label="Context TTL (seconds)"
                rules={[{ required: true }]}
                extra="How long to keep conversation context"
              >
                <InputNumber min={60} style={{ width: '100%' }} />
              </Form.Item>
              <Form.Item
                name="openai_timeout"
                label="API Timeout (seconds)"
                rules={[{ required: true }]}
                extra="Timeout for API requests"
              >
                <InputNumber min={30} max={600} style={{ width: '100%' }} />
              </Form.Item>
              <Form.Item>
                <Button type="primary" htmlType="submit" loading={saving}>
                  Save Model & API Settings
                </Button>
              </Form.Item>
            </Form>
          </Card>

          {/* Info Card */}
          <Card title="ℹ️ Provider Information" style={{ marginTop: 24 }}>
            <Text type="secondary">
              <strong>CometAPI</strong> — unified gateway to 500+ AI models including:
              <ul style={{ marginLeft: 20, marginTop: 8 }}>
                <li><strong>Qwen-3-Max</strong> — text generation (multilingual, context-aware)</li>
                <li><strong>DALL-E 3</strong> — high-quality image generation</li>
                <li><strong>Sora 2</strong> — video generation (4-12 seconds)</li>
                <li><strong>Whisper</strong> — speech recognition (25+ languages)</li>
              </ul>
            </Text>
            <br />
            <Text type="secondary">
              <strong>GigaChat</strong> — Sber's AI model:
              <ul style={{ marginLeft: 20, marginTop: 8 }}>
                <li>Excellent Russian language support</li>
                <li>Presentation structure generation</li>
                <li>Requires separate credentials from developers.sber.ru</li>
              </ul>
            </Text>
          </Card>
        </Col>
      </Row>
    </div>
  );
}

export default SettingsPage;
