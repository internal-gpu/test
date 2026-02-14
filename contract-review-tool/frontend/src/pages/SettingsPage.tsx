import { useEffect, useState } from "react";
import { Card, Input, Button, message, Space, Typography, Divider, Alert } from "antd";
import { SaveOutlined } from "@ant-design/icons";
import { getSettings, updateSetting, Settings } from "../api";

const { TextArea } = Input;
const { Text } = Typography;

export default function SettingsPage() {
  const [settings, setSettings] = useState<Settings>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState<string | null>(null);

  useEffect(() => {
    getSettings()
      .then((res) => setSettings(res.data))
      .finally(() => setLoading(false));
  }, []);

  const handleSave = async (key: string) => {
    setSaving(key);
    try {
      await updateSetting(key, settings[key] || "");
      message.success("保存成功");
    } catch (e: any) {
      message.error("保存失败");
    } finally {
      setSaving(null);
    }
  };

  const updateLocal = (key: string, value: string) => {
    setSettings((prev) => ({ ...prev, [key]: value }));
  };

  if (loading) return <div>加载中...</div>;

  return (
    <div style={{ maxWidth: 800, margin: "0 auto" }}>
      <Alert
        message="配置说明"
        description="在此页面配置LLM的API Key、模型和审查Prompt。配置一次后，上传合同时无需重复输入。支持OpenAI兼容的API接口（如OpenAI、Azure、本地部署等）。"
        type="info"
        showIcon
        style={{ marginBottom: 24 }}
      />

      <Card title="API 配置" style={{ marginBottom: 16 }}>
        <div style={{ marginBottom: 16 }}>
          <Text strong>API Key</Text>
          <Input.Password
            value={settings.api_key || ""}
            onChange={(e) => updateLocal("api_key", e.target.value)}
            placeholder="sk-..."
            style={{ marginTop: 4 }}
          />
          <Button
            type="primary"
            size="small"
            icon={<SaveOutlined />}
            onClick={() => handleSave("api_key")}
            loading={saving === "api_key"}
            style={{ marginTop: 8 }}
          >
            保存
          </Button>
        </div>

        <div style={{ marginBottom: 16 }}>
          <Text strong>Base URL（可选，留空使用OpenAI默认）</Text>
          <Input
            value={settings.base_url || ""}
            onChange={(e) => updateLocal("base_url", e.target.value)}
            placeholder="https://api.openai.com/v1"
            style={{ marginTop: 4 }}
          />
          <Button
            type="primary"
            size="small"
            icon={<SaveOutlined />}
            onClick={() => handleSave("base_url")}
            loading={saving === "base_url"}
            style={{ marginTop: 8 }}
          >
            保存
          </Button>
        </div>

        <div>
          <Text strong>模型名称</Text>
          <Input
            value={settings.model || ""}
            onChange={(e) => updateLocal("model", e.target.value)}
            placeholder="gpt-4o"
            style={{ marginTop: 4 }}
          />
          <Button
            type="primary"
            size="small"
            icon={<SaveOutlined />}
            onClick={() => handleSave("model")}
            loading={saving === "model"}
            style={{ marginTop: 8 }}
          >
            保存
          </Button>
        </div>
      </Card>

      <Card title="审查 Prompt" style={{ marginBottom: 16 }}>
        <Text type="secondary" style={{ display: "block", marginBottom: 8 }}>
          合同审查的系统提示词。使用 {"{contract_text}"} 作为合同内容的占位符。
          LLM需要返回JSON数组，每个元素包含 location, original_text, suggested_text, reason, severity 五个字段。
        </Text>
        <TextArea
          value={settings.review_prompt || ""}
          onChange={(e) => updateLocal("review_prompt", e.target.value)}
          rows={12}
          style={{ fontFamily: "monospace", fontSize: 13 }}
        />
        <Button
          type="primary"
          icon={<SaveOutlined />}
          onClick={() => handleSave("review_prompt")}
          loading={saving === "review_prompt"}
          style={{ marginTop: 8 }}
        >
          保存审查Prompt
        </Button>
      </Card>

      <Card title="分类 Prompt">
        <Text type="secondary" style={{ display: "block", marginBottom: 8 }}>
          合同自动分类的提示词。使用 {"{contract_text}"} 作为合同内容占位符。LLM应返回分类名称。
        </Text>
        <TextArea
          value={settings.classify_prompt || ""}
          onChange={(e) => updateLocal("classify_prompt", e.target.value)}
          rows={8}
          style={{ fontFamily: "monospace", fontSize: 13 }}
        />
        <Button
          type="primary"
          icon={<SaveOutlined />}
          onClick={() => handleSave("classify_prompt")}
          loading={saving === "classify_prompt"}
          style={{ marginTop: 8 }}
        >
          保存分类Prompt
        </Button>
      </Card>
    </div>
  );
}
