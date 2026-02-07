import { useState } from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { Layout, Menu, Avatar, Dropdown, theme, Typography, Button, Space } from 'antd';
import {
  DashboardOutlined,
  UserOutlined,
  SettingOutlined,
  OrderedListOutlined,
  LogoutOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  ApiOutlined,
  MessageOutlined,
  CrownOutlined,
  GlobalOutlined,
} from '@ant-design/icons';
import { useAuthStore } from '../store/authStore';
import { useLangStore } from '../store/langStore';

const { Header, Sider, Content } = Layout;
const { Text } = Typography;

function AdminLayout() {
  const [collapsed, setCollapsed] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const { admin, logout } = useAuthStore();
  const { lang, setLang, t } = useLangStore();
  const {
    token: { colorBgContainer },
  } = theme.useToken();

  const menuItems = [
    {
      key: '/',
      icon: <DashboardOutlined />,
      label: t('menu.dashboard'),
    },
    {
      key: '/users',
      icon: <UserOutlined />,
      label: t('menu.users'),
    },
    {
      key: '/support',
      icon: <MessageOutlined />,
      label: t('menu.support'),
    },
    {
      key: '/tasks',
      icon: <OrderedListOutlined />,
      label: t('menu.tasks'),
    },
    {
      key: '/api-usage',
      icon: <ApiOutlined />,
      label: t('menu.api_usage'),
    },
    {
      key: '/subscriptions',
      icon: <CrownOutlined />,
      label: t('menu.subscriptions'),
    },
    {
      key: '/settings',
      icon: <SettingOutlined />,
      label: t('menu.settings'),
    },
  ];

  const userMenuItems = [
    {
      key: 'profile',
      icon: <UserOutlined />,
      label: t('header.profile'),
    },
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: t('header.logout'),
      danger: true,
    },
  ];

  const handleMenuClick = ({ key }: { key: string }) => {
    navigate(key);
  };

  const handleUserMenuClick = ({ key }: { key: string }) => {
    if (key === 'logout') {
      logout();
      navigate('/login');
    }
  };

  const toggleLang = () => {
    setLang(lang === 'en' ? 'ru' : 'en');
  };

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider trigger={null} collapsible collapsed={collapsed}>
        <div
          style={{
            height: 64,
            margin: 16,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <Text
            strong
            style={{
              color: '#fff',
              fontSize: collapsed ? 14 : 18,
              whiteSpace: 'nowrap',
            }}
          >
            {collapsed ? t('header.title_short') : t('header.title')}
          </Text>
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={handleMenuClick}
        />
      </Sider>
      <Layout>
        <Header
          style={{
            padding: '0 24px',
            background: colorBgContainer,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <div
            style={{ cursor: 'pointer' }}
            onClick={() => setCollapsed(!collapsed)}
          >
            {collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
          </div>
          <Space size="middle">
            <Button
              type="text"
              icon={<GlobalOutlined />}
              onClick={toggleLang}
              style={{ fontWeight: 600 }}
            >
              {lang === 'en' ? 'RU' : 'EN'}
            </Button>
            <Dropdown
              menu={{
                items: userMenuItems,
                onClick: handleUserMenuClick,
              }}
              trigger={['click']}
            >
              <div
                style={{
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                }}
              >
                <Avatar icon={<UserOutlined />} />
                <Text>{admin?.username}</Text>
              </div>
            </Dropdown>
          </Space>
        </Header>
        <Content>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
}

export default AdminLayout;
