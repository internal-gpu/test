import { useState } from "react";
import { Layout, Menu, theme } from "antd";
import {
  UploadOutlined,
  FileSearchOutlined,
  SettingOutlined,
  AppstoreOutlined,
} from "@ant-design/icons";
import UploadPage from "./pages/UploadPage";
import ContractsPage from "./pages/ContractsPage";
import ContractDetailPage from "./pages/ContractDetailPage";
import SettingsPage from "./pages/SettingsPage";

const { Header, Content, Sider } = Layout;

type Page =
  | { key: "upload" }
  | { key: "contracts" }
  | { key: "detail"; id: number }
  | { key: "settings" };

function App() {
  const [page, setPage] = useState<Page>({ key: "upload" });
  const {
    token: { colorBgContainer, borderRadiusLG },
  } = theme.useToken();

  const menuItems = [
    { key: "upload", icon: <UploadOutlined />, label: "上传合同" },
    { key: "contracts", icon: <FileSearchOutlined />, label: "合同列表" },
    { key: "settings", icon: <SettingOutlined />, label: "系统设置" },
  ];

  const openDetail = (id: number) => setPage({ key: "detail", id });

  return (
    <Layout style={{ minHeight: "100vh" }}>
      <Sider breakpoint="lg" collapsedWidth="0" theme="light">
        <div
          style={{
            height: 64,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontWeight: 700,
            fontSize: 18,
            borderBottom: "1px solid #f0f0f0",
          }}
        >
          <AppstoreOutlined style={{ marginRight: 8 }} />
          合同审查
        </div>
        <Menu
          mode="inline"
          selectedKeys={[page.key === "detail" ? "contracts" : page.key]}
          items={menuItems}
          onClick={({ key }) => setPage({ key: key as any })}
        />
      </Sider>
      <Layout>
        <Header
          style={{
            padding: "0 24px",
            background: colorBgContainer,
            fontSize: 16,
            fontWeight: 600,
            borderBottom: "1px solid #f0f0f0",
            display: "flex",
            alignItems: "center",
          }}
        >
          {{
            upload: "批量上传合同",
            contracts: "合同管理",
            detail: "审查详情",
            settings: "系统设置",
          }[page.key]}
        </Header>
        <Content
          style={{
            margin: 24,
            padding: 24,
            background: colorBgContainer,
            borderRadius: borderRadiusLG,
            overflow: "auto",
          }}
        >
          {page.key === "upload" && (
            <UploadPage onGoToContracts={() => setPage({ key: "contracts" })} />
          )}
          {page.key === "contracts" && (
            <ContractsPage onOpenDetail={openDetail} />
          )}
          {page.key === "detail" && (
            <ContractDetailPage
              contractId={page.id}
              onBack={() => setPage({ key: "contracts" })}
            />
          )}
          {page.key === "settings" && <SettingsPage />}
        </Content>
      </Layout>
    </Layout>
  );
}

export default App;
