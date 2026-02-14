import { useEffect, useState } from "react";
import {
  Button,
  Spin,
  Tag,
  Card,
  Typography,
  Divider,
  Space,
  message,
  Alert,
  Collapse,
  Empty,
} from "antd";
import {
  ArrowLeftOutlined,
  DownloadOutlined,
  WarningOutlined,
  InfoCircleOutlined,
  ExclamationCircleOutlined,
} from "@ant-design/icons";
import { getContract, downloadReviewedDocx, ContractDetail, ReviewItem } from "../api";

const { Text, Paragraph, Title } = Typography;

interface Props {
  contractId: number;
  onBack: () => void;
}

const severityConfig: Record<string, { color: string; icon: React.ReactNode; label: string }> = {
  critical: { color: "red", icon: <ExclamationCircleOutlined />, label: "必须修改" },
  warning: { color: "orange", icon: <WarningOutlined />, label: "建议修改" },
  info: { color: "blue", icon: <InfoCircleOutlined />, label: "可选优化" },
};

export default function ContractDetailPage({ contractId, onBack }: Props) {
  const [contract, setContract] = useState<ContractDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [downloading, setDownloading] = useState(false);

  useEffect(() => {
    let timer: ReturnType<typeof setInterval>;
    const load = async () => {
      try {
        const res = await getContract(contractId);
        setContract(res.data);
        if (res.data.status === "analyzing") {
          timer = setInterval(async () => {
            const r = await getContract(contractId);
            setContract(r.data);
            if (r.data.status !== "analyzing") clearInterval(timer);
          }, 3000);
        }
      } finally {
        setLoading(false);
      }
    };
    load();
    return () => clearInterval(timer);
  }, [contractId]);

  const handleDownload = async () => {
    setDownloading(true);
    try {
      const res = await downloadReviewedDocx(contractId);
      const blob = new Blob([res.data]);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = contract?.filename?.replace(".docx", "_审查结果.docx") || "reviewed.docx";
      a.click();
      URL.revokeObjectURL(url);
    } catch (e: any) {
      message.error("下载失败: " + (e.response?.data?.detail || e.message));
    } finally {
      setDownloading(false);
    }
  };

  if (loading) return <Spin size="large" style={{ display: "block", margin: "80px auto" }} />;
  if (!contract) return <Empty description="合同不存在" />;

  const reviewsBySeverity = {
    critical: contract.reviews.filter((r) => r.severity === "critical"),
    warning: contract.reviews.filter((r) => r.severity === "warning"),
    info: contract.reviews.filter((r) => r.severity === "info"),
  };

  // Build inline diff view: highlight original text with annotations
  const buildDiffView = () => {
    if (contract.reviews.length === 0) return contract.original_text;

    let text = contract.original_text;
    // Sort reviews by position in text (reverse to preserve indices)
    const sortedReviews = [...contract.reviews]
      .map((r) => ({ ...r, idx: text.indexOf(r.original_text) }))
      .filter((r) => r.idx >= 0)
      .sort((a, b) => b.idx - a.idx);

    const segments: { type: "normal" | "review"; text: string; review?: ReviewItem }[] = [];

    // Build segments from end to start
    let remaining = text;
    const usedReviews: typeof sortedReviews = [];

    for (const r of sortedReviews) {
      const idx = remaining.indexOf(r.original_text);
      if (idx >= 0) {
        usedReviews.push(r);
      }
    }

    // Now build from start
    let cursor = 0;
    const forwardReviews = usedReviews.sort((a, b) => {
      const ai = text.indexOf(a.original_text);
      const bi = text.indexOf(b.original_text);
      return ai - bi;
    });

    for (const r of forwardReviews) {
      const idx = text.indexOf(r.original_text, cursor);
      if (idx < 0) continue;
      if (idx > cursor) {
        segments.push({ type: "normal", text: text.slice(cursor, idx) });
      }
      segments.push({ type: "review", text: r.original_text, review: r });
      cursor = idx + r.original_text.length;
    }
    if (cursor < text.length) {
      segments.push({ type: "normal", text: text.slice(cursor) });
    }

    return segments;
  };

  const diffSegments = buildDiffView();

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={onBack}>
          返回列表
        </Button>
        {contract.status === "completed" && (
          <Button
            type="primary"
            icon={<DownloadOutlined />}
            onClick={handleDownload}
            loading={downloading}
          >
            下载审查标注版
          </Button>
        )}
      </Space>

      {/* Header info */}
      <Card size="small" style={{ marginBottom: 16 }}>
        <Space size="large">
          <Text strong>文件：{contract.filename}</Text>
          <Tag color="blue">{contract.category}</Tag>
          <Tag color={contract.status === "completed" ? "green" : contract.status === "error" ? "red" : "blue"}>
            {contract.status === "completed" ? "已完成" : contract.status === "analyzing" ? "审查中..." : contract.status === "error" ? "错误" : "待审查"}
          </Tag>
          <Text type="secondary">
            发现 {contract.reviews.length} 个问题
            {reviewsBySeverity.critical.length > 0 && (
              <Tag color="red" style={{ marginLeft: 8 }}>{reviewsBySeverity.critical.length} 必须修改</Tag>
            )}
            {reviewsBySeverity.warning.length > 0 && (
              <Tag color="orange" style={{ marginLeft: 4 }}>{reviewsBySeverity.warning.length} 建议修改</Tag>
            )}
          </Text>
        </Space>
      </Card>

      {contract.status === "analyzing" && (
        <Alert message="正在审查中，请稍候..." type="info" showIcon style={{ marginBottom: 16 }} />
      )}

      {contract.error_message && (
        <Alert message="审查出错" description={contract.error_message} type="error" showIcon style={{ marginBottom: 16 }} />
      )}

      {/* Review Items */}
      {contract.reviews.length > 0 && (
        <Card title="审查意见" style={{ marginBottom: 16 }}>
          <Collapse
            defaultActiveKey={contract.reviews.map((_, i) => String(i))}
            items={contract.reviews.map((r, i) => {
              const sev = severityConfig[r.severity] || severityConfig.info;
              return {
                key: String(i),
                label: (
                  <Space>
                    <Tag color={sev.color} icon={sev.icon}>{sev.label}</Tag>
                    <Text>{r.location}</Text>
                  </Space>
                ),
                children: (
                  <div>
                    <div style={{ marginBottom: 12 }}>
                      <Text type="secondary">原文：</Text>
                      <div
                        style={{
                          background: "#fff1f0",
                          border: "1px solid #ffa39e",
                          borderRadius: 4,
                          padding: "8px 12px",
                          marginTop: 4,
                          textDecoration: "line-through",
                          color: "#cf1322",
                        }}
                      >
                        {r.original_text}
                      </div>
                    </div>
                    <div style={{ marginBottom: 12 }}>
                      <Text type="secondary">建议修改为：</Text>
                      <div
                        style={{
                          background: "#f6ffed",
                          border: "1px solid #b7eb8f",
                          borderRadius: 4,
                          padding: "8px 12px",
                          marginTop: 4,
                          color: "#389e0d",
                          fontWeight: 500,
                        }}
                      >
                        {r.suggested_text}
                      </div>
                    </div>
                    <div>
                      <Text type="secondary">修改原因：</Text>
                      <Paragraph style={{ marginTop: 4 }}>{r.reason}</Paragraph>
                    </div>
                  </div>
                ),
              };
            })}
          />
        </Card>
      )}

      {/* Inline diff view */}
      <Card title="合同原文（标注模式）">
        <div style={{ whiteSpace: "pre-wrap", lineHeight: 2, fontSize: 14 }}>
          {Array.isArray(diffSegments) ? (
            diffSegments.map((seg, i) => {
              if (seg.type === "normal") {
                return <span key={i}>{seg.text}</span>;
              }
              const sev = severityConfig[seg.review?.severity || "info"];
              return (
                <span key={i}>
                  <span
                    style={{
                      textDecoration: "line-through",
                      background: "#fff1f0",
                      color: "#cf1322",
                      padding: "0 2px",
                    }}
                  >
                    {seg.text}
                  </span>
                  <span
                    style={{
                      background: "#f6ffed",
                      color: "#389e0d",
                      fontWeight: 600,
                      padding: "0 2px",
                      marginLeft: 2,
                    }}
                  >
                    {seg.review?.suggested_text}
                  </span>
                  <Tag
                    color={sev.color}
                    style={{ fontSize: 11, marginLeft: 4, verticalAlign: "super" }}
                  >
                    {seg.review?.reason?.slice(0, 30)}...
                  </Tag>
                </span>
              );
            })
          ) : (
            <span>{diffSegments}</span>
          )}
        </div>
      </Card>
    </div>
  );
}
