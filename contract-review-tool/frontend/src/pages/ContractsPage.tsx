import { useEffect, useState, useCallback } from "react";
import {
  Table,
  Tag,
  Space,
  Button,
  Select,
  Input,
  Popconfirm,
  message,
  Card,
  Row,
  Col,
  Statistic,
} from "antd";
import {
  ReloadOutlined,
  DeleteOutlined,
  EyeOutlined,
  PlayCircleOutlined,
  SearchOutlined,
} from "@ant-design/icons";
import {
  listContracts,
  getCategories,
  deleteContract,
  startAnalysis,
  ContractBrief,
  CategoryCount,
} from "../api";

interface Props {
  onOpenDetail: (id: number) => void;
}

const statusMap: Record<string, { color: string; label: string }> = {
  pending: { color: "default", label: "待审查" },
  analyzing: { color: "processing", label: "审查中" },
  completed: { color: "success", label: "已完成" },
  error: { color: "error", label: "错误" },
};

export default function ContractsPage({ onOpenDetail }: Props) {
  const [contracts, setContracts] = useState<ContractBrief[]>([]);
  const [categories, setCategories] = useState<CategoryCount[]>([]);
  const [loading, setLoading] = useState(false);
  const [filterCategory, setFilterCategory] = useState<string | undefined>();
  const [filterStatus, setFilterStatus] = useState<string | undefined>();
  const [searchText, setSearchText] = useState("");
  const [selectedIds, setSelectedIds] = useState<number[]>([]);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [cRes, catRes] = await Promise.all([
        listContracts({
          category: filterCategory,
          status: filterStatus,
          search: searchText || undefined,
        }),
        getCategories(),
      ]);
      setContracts(cRes.data);
      setCategories(catRes.data);
    } finally {
      setLoading(false);
    }
  }, [filterCategory, filterStatus, searchText]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Auto-refresh while any contract is analyzing
  useEffect(() => {
    const hasAnalyzing = contracts.some((c) => c.status === "analyzing");
    if (!hasAnalyzing) return;
    const timer = setInterval(loadData, 3000);
    return () => clearInterval(timer);
  }, [contracts, loadData]);

  const handleDelete = async (id: number) => {
    await deleteContract(id);
    message.success("已删除");
    loadData();
  };

  const handleBatchAnalyze = async () => {
    try {
      const ids = selectedIds.length > 0 ? selectedIds : undefined;
      const res = await startAnalysis(ids);
      message.success(res.data.message);
      setSelectedIds([]);
      loadData();
    } catch (e: any) {
      message.error(e.response?.data?.detail || e.message);
    }
  };

  const columns = [
    {
      title: "文件名",
      dataIndex: "filename",
      key: "filename",
      ellipsis: true,
    },
    {
      title: "分类",
      dataIndex: "category",
      key: "category",
      width: 140,
      render: (cat: string) => <Tag color="blue">{cat}</Tag>,
    },
    {
      title: "状态",
      dataIndex: "status",
      key: "status",
      width: 100,
      render: (s: string) => {
        const info = statusMap[s] || { color: "default", label: s };
        return <Tag color={info.color}>{info.label}</Tag>;
      },
    },
    {
      title: "问题数",
      dataIndex: "review_count",
      key: "review_count",
      width: 80,
      render: (n: number) =>
        n > 0 ? <Tag color="orange">{n}</Tag> : <Tag>0</Tag>,
    },
    {
      title: "上传时间",
      dataIndex: "created_at",
      key: "created_at",
      width: 180,
      render: (t: string) => (t ? new Date(t).toLocaleString("zh-CN") : ""),
    },
    {
      title: "操作",
      key: "action",
      width: 160,
      render: (_: any, record: ContractBrief) => (
        <Space>
          <Button
            type="link"
            icon={<EyeOutlined />}
            onClick={() => onOpenDetail(record.id)}
            disabled={record.status === "pending"}
          >
            查看
          </Button>
          <Popconfirm title="确认删除？" onConfirm={() => handleDelete(record.id)}>
            <Button type="link" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  const total = contracts.length;
  const completed = contracts.filter((c) => c.status === "completed").length;
  const issues = contracts.reduce((sum, c) => sum + c.review_count, 0);

  return (
    <div>
      {/* Stats */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card size="small">
            <Statistic title="合同总数" value={total} />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic title="已完成审查" value={completed} />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic title="发现问题" value={issues} valueStyle={{ color: issues > 0 ? "#cf1322" : undefined }} />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic title="分类数" value={categories.length} />
          </Card>
        </Col>
      </Row>

      {/* Filters */}
      <Space style={{ marginBottom: 16 }} wrap>
        <Select
          placeholder="按分类筛选"
          allowClear
          style={{ width: 160 }}
          value={filterCategory}
          onChange={setFilterCategory}
          options={categories.map((c) => ({
            label: `${c.category} (${c.count})`,
            value: c.category,
          }))}
        />
        <Select
          placeholder="按状态筛选"
          allowClear
          style={{ width: 130 }}
          value={filterStatus}
          onChange={setFilterStatus}
          options={[
            { label: "待审查", value: "pending" },
            { label: "审查中", value: "analyzing" },
            { label: "已完成", value: "completed" },
            { label: "错误", value: "error" },
          ]}
        />
        <Input
          placeholder="搜索文件名"
          prefix={<SearchOutlined />}
          allowClear
          style={{ width: 200 }}
          value={searchText}
          onChange={(e) => setSearchText(e.target.value)}
          onPressEnter={loadData}
        />
        <Button icon={<ReloadOutlined />} onClick={loadData}>
          刷新
        </Button>
        <Button
          type="primary"
          icon={<PlayCircleOutlined />}
          onClick={handleBatchAnalyze}
          disabled={contracts.every((c) => c.status !== "pending")}
        >
          {selectedIds.length > 0
            ? `审查选中 (${selectedIds.length})`
            : "审查全部待审"}
        </Button>
      </Space>

      {/* Category tags */}
      {categories.length > 0 && (
        <div style={{ marginBottom: 12 }}>
          <Tag
            color={!filterCategory ? "blue" : undefined}
            style={{ cursor: "pointer" }}
            onClick={() => setFilterCategory(undefined)}
          >
            全部
          </Tag>
          {categories.map((c) => (
            <Tag
              key={c.category}
              color={filterCategory === c.category ? "blue" : undefined}
              style={{ cursor: "pointer" }}
              onClick={() =>
                setFilterCategory(
                  filterCategory === c.category ? undefined : c.category
                )
              }
            >
              {c.category} ({c.count})
            </Tag>
          ))}
        </div>
      )}

      <Table
        rowKey="id"
        columns={columns}
        dataSource={contracts}
        loading={loading}
        pagination={{ pageSize: 20 }}
        rowSelection={{
          selectedRowKeys: selectedIds,
          onChange: (keys) => setSelectedIds(keys as number[]),
        }}
        size="middle"
      />
    </div>
  );
}
