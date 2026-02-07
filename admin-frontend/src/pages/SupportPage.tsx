import { useEffect, useState, useRef } from 'react';
import {
  Layout,
  List,
  Avatar,
  Badge,
  Input,
  Button,
  Typography,
  message,
  Spin,
  Empty,
  Card,
  Space,
  Tag,
} from 'antd';
import {
  SendOutlined,
  UserOutlined,
  ReloadOutlined,
  MessageOutlined,
} from '@ant-design/icons';
import { supportApi } from '../services/api';
import { useAuthStore } from '../store/authStore';
import dayjs from 'dayjs';
import relativeTime from 'dayjs/plugin/relativeTime';

dayjs.extend(relativeTime);

const { Sider, Content } = Layout;
const { Title, Text } = Typography;
const { TextArea } = Input;

interface Conversation {
  user_id: number;
  user_telegram_id: number;
  username: string | null;
  first_name: string | null;
  last_message: string;
  last_message_at: string;
  unread_count: number;
  has_subscription: boolean;
}

interface Message {
  id: number;
  user_id: number;
  user_telegram_id: number;
  username: string | null;
  first_name: string | null;
  message: string;
  is_from_user: boolean;
  admin_username: string | null;
  is_read: boolean;
  created_at: string;
}

function SupportPage() {
  const [loading, setLoading] = useState(true);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [selectedUserId, setSelectedUserId] = useState<number | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [messagesLoading, setMessagesLoading] = useState(false);
  const [newMessage, setNewMessage] = useState('');
  const [sending, setSending] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetchConversations();
    // Poll for new messages every 10 seconds
    const interval = setInterval(fetchConversations, 10000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (selectedUserId) {
      fetchMessages(selectedUserId);
    }
  }, [selectedUserId]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const fetchConversations = async () => {
    try {
      const response = await supportApi.getConversations();
      setConversations(response.data.conversations);
    } catch (error) {
      console.error('Failed to fetch conversations:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchMessages = async (userId: number) => {
    setMessagesLoading(true);
    try {
      const response = await supportApi.getConversation(userId);
      // API returns array directly, not object with messages field
      setMessages(response.data || []);
    } catch (error) {
      console.error('Failed to fetch messages:', error);
      message.error('Failed to load messages');
    } finally {
      setMessagesLoading(false);
    }
  };

  const handleSendMessage = async () => {
    if (!newMessage.trim() || !selectedUserId) return;

    setSending(true);
    try {
      await supportApi.sendMessage(selectedUserId, newMessage.trim());
      setNewMessage('');
      // Refresh messages
      await fetchMessages(selectedUserId);
      // Refresh conversations to update last message
      await fetchConversations();
      message.success('Message sent');
    } catch (error) {
      console.error('Failed to send message:', error);
      message.error('Failed to send message');
    } finally {
      setSending(false);
    }
  };

  const getUserDisplayName = (conv: Conversation) => {
    if (conv.username) return `@${conv.username}`;
    if (conv.first_name) return conv.first_name;
    return `User ${conv.user_telegram_id}`;
  };

  const selectedConversation = conversations.find(c => c.user_id === selectedUserId);
  const authToken = useAuthStore.getState().token;

  // Build photo URL with auth token for <img src>
  const getPhotoUrl = (fileId: string) => {
    return `/api/support/photo/${fileId}?token=${encodeURIComponent(authToken || '')}`;
  };

  // Parse message to extract photo and text
  const parseMessage = (message: string) => {
    const photoMatch = message.match(/\[PHOTO:([^\]]+)\]/);
    if (photoMatch) {
      const photoFileId = photoMatch[1];
      const textPart = message.replace(/\[PHOTO:[^\]]+\]\n?/, '').trim();
      return { hasPhoto: true, photoFileId, text: textPart };
    }
    return { hasPhoto: false, photoFileId: null, text: message };
  };

  return (
    <div style={{ padding: 0, height: 'calc(100vh - 64px)' }}>
      <Layout style={{ height: '100%', background: '#fff' }}>
        {/* Conversations Sidebar */}
        <Sider width={350} style={{ background: '#fff', borderRight: '1px solid #f0f0f0', overflow: 'auto' }}>
          <div style={{ padding: '16px', borderBottom: '1px solid #f0f0f0', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Title level={4} style={{ margin: 0 }}>
              <MessageOutlined style={{ marginRight: 8 }} />
              Support
            </Title>
            <Button 
              icon={<ReloadOutlined />} 
              onClick={fetchConversations}
              loading={loading}
            />
          </div>
          
          {loading && conversations.length === 0 ? (
            <div style={{ textAlign: 'center', padding: 40 }}>
              <Spin />
            </div>
          ) : conversations.length === 0 ? (
            <Empty 
              description="No support requests" 
              style={{ marginTop: 40 }}
            />
          ) : (
            <List
              dataSource={conversations}
              renderItem={(conv) => (
                <List.Item
                  onClick={() => setSelectedUserId(conv.user_id)}
                  style={{
                    cursor: 'pointer',
                    padding: '12px 16px',
                    background: selectedUserId === conv.user_id ? '#e6f7ff' : 'transparent',
                    borderBottom: '1px solid #f0f0f0',
                  }}
                >
                  <List.Item.Meta
                    avatar={
                      <Badge count={conv.unread_count} offset={[-5, 5]}>
                        <Avatar icon={<UserOutlined />} style={{ backgroundColor: conv.unread_count > 0 ? '#1890ff' : '#ccc' }} />
                      </Badge>
                    }
                    title={
                      <Space>
                        <Text strong>{getUserDisplayName(conv)}</Text>
                        {conv.unread_count > 0 && (
                          <Tag color="blue">{conv.unread_count} new</Tag>
                        )}
                      </Space>
                    }
                    description={
                      <div>
                        <Text 
                          type="secondary" 
                          ellipsis 
                          style={{ display: 'block', maxWidth: 250 }}
                        >
                          {conv.last_message}
                        </Text>
                        <Text type="secondary" style={{ fontSize: 12 }}>
                          {dayjs(conv.last_message_at).fromNow()}
                        </Text>
                      </div>
                    }
                  />
                </List.Item>
              )}
            />
          )}
        </Sider>

        {/* Messages Area */}
        <Content style={{ display: 'flex', flexDirection: 'column', background: '#f5f5f5' }}>
          {selectedUserId ? (
            <>
              {/* Chat Header */}
              <div style={{ 
                padding: '12px 16px', 
                background: '#fff', 
                borderBottom: '1px solid #f0f0f0',
                display: 'flex',
                alignItems: 'center',
                gap: 12
              }}>
                <Avatar icon={<UserOutlined />} />
                <div>
                  <Text strong>{selectedConversation && getUserDisplayName(selectedConversation)}</Text>
                  <br />
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    Telegram ID: {selectedConversation?.user_telegram_id}
                  </Text>
                </div>
              </div>

              {/* Messages */}
              <div style={{ 
                flex: 1, 
                overflow: 'auto', 
                padding: 16,
                display: 'flex',
                flexDirection: 'column',
                gap: 8,
              }}>
                {messagesLoading ? (
                  <div style={{ textAlign: 'center', padding: 40 }}>
                    <Spin />
                  </div>
                ) : messages.length === 0 ? (
                  <Empty description="No messages yet" />
                ) : (
                  messages.map((msg) => {
                    const { hasPhoto, photoFileId, text } = parseMessage(msg.message);
                    return (
                      <div
                        key={msg.id}
                        style={{
                          display: 'flex',
                          justifyContent: !msg.is_from_user ? 'flex-end' : 'flex-start',
                        }}
                      >
                        <Card
                          size="small"
                          style={{
                            maxWidth: '70%',
                            background: !msg.is_from_user ? '#1890ff' : '#fff',
                            borderRadius: 12,
                            border: !msg.is_from_user ? 'none' : '1px solid #f0f0f0',
                          }}
                          bodyStyle={{ padding: '8px 12px' }}
                        >
                          {hasPhoto && photoFileId && (
                            <div style={{ marginBottom: text ? 8 : 0 }}>
                              <img
                                src={getPhotoUrl(photoFileId)}
                                alt="Attached"
                                style={{
                                  maxWidth: '100%',
                                  maxHeight: 300,
                                  borderRadius: 8,
                                  cursor: 'pointer'
                                }}
                                onClick={() => window.open(getPhotoUrl(photoFileId), '_blank')}
                                onError={(e) => {
                                  // Fallback to placeholder if image fails to load
                                  const target = e.target as HTMLImageElement;
                                  target.style.display = 'none';
                                  target.parentElement!.innerHTML = `
                                    <div style="padding: 8px; background: ${!msg.is_from_user ? 'rgba(255,255,255,0.1)' : '#f5f5f5'}; border-radius: 8px; display: flex; align-items: center; gap: 8px;">
                                      <span style="font-size: 24px;">🖼️</span>
                                      <span>Image (expired or unavailable)</span>
                                    </div>
                                  `;
                                }}
                              />
                            </div>
                          )}
                          {text && (
                            <Text style={{ color: !msg.is_from_user ? '#fff' : '#000', whiteSpace: 'pre-wrap' }}>
                              {text}
                            </Text>
                          )}
                          <br />
                          <Text 
                            type="secondary" 
                            style={{ 
                              fontSize: 10, 
                              color: !msg.is_from_user ? 'rgba(255,255,255,0.7)' : undefined 
                            }}
                          >
                            {dayjs(msg.created_at).format('HH:mm')}
                            {!msg.is_from_user && msg.admin_username && ` · ${msg.admin_username}`}
                          </Text>
                        </Card>
                      </div>
                    );
                  })
                )}
                <div ref={messagesEndRef} />
              </div>

              {/* Input Area */}
              <div style={{ 
                padding: 16, 
                background: '#fff',
                borderTop: '1px solid #f0f0f0',
                display: 'flex',
                gap: 8,
              }}>
                <TextArea
                  value={newMessage}
                  onChange={(e) => setNewMessage(e.target.value)}
                  placeholder="Type your reply..."
                  autoSize={{ minRows: 1, maxRows: 4 }}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault();
                      handleSendMessage();
                    }
                  }}
                  style={{ flex: 1 }}
                />
                <Button
                  type="primary"
                  icon={<SendOutlined />}
                  onClick={handleSendMessage}
                  loading={sending}
                  disabled={!newMessage.trim()}
                >
                  Send
                </Button>
              </div>
            </>
          ) : (
            <div style={{ 
              flex: 1, 
              display: 'flex', 
              alignItems: 'center', 
              justifyContent: 'center' 
            }}>
              <Empty 
                description="Select a conversation to start" 
                image={Empty.PRESENTED_IMAGE_SIMPLE}
              />
            </div>
          )}
        </Content>
      </Layout>
    </div>
  );
}

export default SupportPage;
