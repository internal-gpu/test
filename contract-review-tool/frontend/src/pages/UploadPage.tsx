import { useState } from "react";
import { Upload, Button, message, Card, Space, Alert, List, Tag } from "antd";
import { InboxOutlined, PlayCircleOutlined } from "@ant-design/icons";
import { uploadContracts, startAnalysis } from "../api";

const { Dragger } = Upload;

interface Props {
  onGoToContracts: () => void;
}

export default function UploadPage({ onGoToContracts }: Props) {
  const [fileList, setFileList] = useState<File[]>([]);
  const [uploadedIds, setUploadedIds] = useState<number[]>([]);
  const [uploading, setUploading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [uploadDone, setUploadDone] = useState(false);

  const handleUpload = async () => {
    if (fileList.length === 0) {
      message.warning("请先选择文件");
      return;
    }
    setUploading(true);
    try {
      const res = await uploadContracts(fileList);
      const ids = res.data.uploaded.map((u) => u.id);
      setUploadedIds(ids);
      setUploadDone(true);
      message.success(`成功上传 ${res.data.count} 份合同`);
    } catch (e: any) {
      message.error("上传失败: " + (e.response?.data?.detail || e.message));
    } finally {
      setUploading(false);
    }
  };

  const handleAnalyze = async () => {
    setAnalyzing(true);
    try {
      const res = await startAnalysis(uploadedIds.length > 0 ? uploadedIds : undefined);
      message.success(res.data.message);
      setTimeout(() => onGoToContracts(), 1500);
    } catch (e: any) {
      message.error("启动分析失败: " + (e.response?.data?.detail || e.message));
    } finally {
      setAnalyzing(false);
    }
  };

  return (
    <div style={{ maxWidth: 800, margin: "0 auto" }}>
      <Card title="第一步：选择合同文件" style={{ marginBottom: 16 }}>
        <Dragger
          multiple
          accept=".docx"
          beforeUpload={(file, list) => {
            // Collect all files from this batch
            setFileList((prev) => [...prev, file]);
            return false; // prevent auto upload
          }}
          onRemove={(file) => {
            setFileList((prev) => prev.filter((f) => f.name !== file.name));
          }}
          fileList={fileList.map((f, i) => ({
            uid: `${i}`,
            name: f.name,
            status: "done" as const,
            size: f.size,
          }))}
          disabled={uploadDone}
        >
          <p className="ant-upload-drag-icon">
            <InboxOutlined />
          </p>
          <p className="ant-upload-text">点击或拖拽Word文件到此区域</p>
          <p className="ant-upload-hint">
            支持批量上传 .docx 格式的合同文件
          </p>
        </Dragger>

        <div style={{ marginTop: 16, textAlign: "center" }}>
          <Button
            type="primary"
            onClick={handleUpload}
            loading={uploading}
            disabled={fileList.length === 0 || uploadDone}
            size="large"
          >
            上传 {fileList.length} 个文件
          </Button>
        </div>
      </Card>

      {uploadDone && (
        <Card title="第二步：开始审查">
          <Alert
            message={`已上传 ${uploadedIds.length} 份合同，点击下方按钮开始AI审查`}
            description="系统将逐个分析合同内容，自动分类并给出修改建议。分析过程在后台进行，您可以前往合同列表查看进度。"
            type="info"
            showIcon
            style={{ marginBottom: 16 }}
          />
          <Space>
            <Button
              type="primary"
              icon={<PlayCircleOutlined />}
              onClick={handleAnalyze}
              loading={analyzing}
              size="large"
            >
              确认开始审查
            </Button>
            <Button onClick={onGoToContracts} size="large">
              前往合同列表
            </Button>
          </Space>
        </Card>
      )}
    </div>
  );
}
