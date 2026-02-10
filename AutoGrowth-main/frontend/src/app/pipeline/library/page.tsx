"use client";

import { useMemo, useState, useEffect, useCallback } from "react";
import { useZipDownload } from "@/context/ZipDownloadContext";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import {
  Alert,
  Badge,
  Button,
  Card,
  Empty,
  Input,
  List,
  Progress,
  Skeleton,
  Space,
  Tag,
  Tabs,
  Tree,
  Typography,
  message,
} from "antd";
import type { DataNode, EventDataNode, TreeProps } from "antd/es/tree";
import {
  CloseOutlined,
  CloudDownloadOutlined,
  DownloadOutlined,
  FolderOpenOutlined,
  ReloadOutlined,
  SendOutlined,
} from "@ant-design/icons";
import { useMutation, useQuery } from "@tanstack/react-query";
import {
  fetchDownloadLink,
  fetchPipelineFiles,
  requestNasDownload,
  requestZipDownload,
  triggerManualProcess,
} from "@/features/pipeline/api";
import {
  ProgramBrowserTree,
  type ProgramSelection,
} from "@/components/pipeline/ProgramBrowserTree";
import type { PipelineFileNode } from "@/features/pipeline/types";

const { Text } = Typography;

type DownloadTaskStatus = "queued" | "processing" | "ready" | "error";
type DownloadTaskType = "single" | "zip";

interface DownloadTask {
  id: string;
  type: DownloadTaskType;
  label: string;
  status: DownloadTaskStatus;
  progress: number;
  detail?: string;
  createdAt: number;
}

const formatSize = (bytes?: number) => {
  if (!bytes || bytes <= 0) return "-";
  if (bytes < 1024) return `${bytes} B`;
  const units = ["KB", "MB", "GB", "TB"];
  let value = bytes / 1024;
  let idx = 0;
  while (value >= 1024 && idx < units.length - 1) {
    value /= 1024;
    idx += 1;
  }
  return `${value.toFixed(1)} ${units[idx]}`;
};

const formatDate = (iso?: string) => {
  if (!iso) return "-";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toLocaleString();
};

const filterTree = (nodes: PipelineFileNode[], keyword: string): PipelineFileNode[] => {
  if (!keyword) return nodes;
  const lower = keyword.toLowerCase();
  const recurse = (items: PipelineFileNode[]): PipelineFileNode[] =>
    items
      .map((node) => {
        const children = node.children ? recurse(node.children) : undefined;
        const matched = node.name.toLowerCase().includes(lower);
        if (matched || (children && children.length)) {
          return { ...node, children };
        }
        return null;
      })
      .filter(Boolean) as PipelineFileNode[];
  return recurse(nodes);
};

const buildTreeData = (nodes: PipelineFileNode[]): DataNode[] =>
  nodes.map((node) => ({
    key: node.path,
    title: (
      <div className="flex items-center gap-2 truncate">
        <span>{node.name}</span>
        {!node.is_directory && (
          <Tag color="default" bordered={false} className="text-[10px]">
            {formatSize(node.size_bytes)}
          </Tag>
        )}
        {node.language && (
          <Tag color="blue" bordered={false} className="text-[10px]">
            {node.language}
          </Tag>
        )}
      </div>
    ),
    isLeaf: !node.is_directory,
    children: node.children ? buildTreeData(node.children) : undefined,
    className: node.is_directory ? "font-medium" : undefined,
  }));

const flattenNodes = (nodes: PipelineFileNode[]): Record<string, PipelineFileNode> => {
  const map: Record<string, PipelineFileNode> = {};
  const traverse = (items: PipelineFileNode[]) => {
    items.forEach((node) => {
      map[node.path] = node;
      if (node.children?.length) {
        traverse(node.children);
      }
    });
  };
  traverse(nodes);
  return map;
};

const extractProgramCode = (path?: string) => {
  if (!path) return undefined;
  const segments = path.split("/").filter(Boolean);
  if (segments.length < 2) return undefined;
  return segments[1];
};

const createTaskId = () => Math.random().toString(36).slice(2);

export default function PipelineLibraryPage() {
  const { startDownload } = useZipDownload();
  const searchParams = useSearchParams();
  const referencedProgram = searchParams.get("program") ?? undefined;
  const [activeTab, setActiveTab] = useState<"processed" | "pending">("processed");
  const [processedSearch, setProcessedSearch] = useState("");
  const [pendingSearch, setPendingSearch] = useState("");
  const [selectedPendingDrama, setSelectedPendingDrama] = useState<string>();
  const [focusedPath, setFocusedPath] = useState<string>();
  const [checkedPaths, setCheckedPaths] = useState<string[]>([]);
  const [pendingCheckedPaths, setPendingCheckedPaths] = useState<string[]>([]);
  const [downloadTasks, setDownloadTasks] = useState<DownloadTask[]>([]);
  const [isStatusPanelVisible, setStatusPanelVisible] = useState(true);

  const {
    data: processedData,
    isLoading: processedLoading,
    refetch: refetchProcessed,
    error: processedError,
  } = useQuery({
    queryKey: ["pipeline", "library", "processed"],
    queryFn: () => fetchPipelineFiles({ scope: "processed" }),
  });

  // 获取所有 source 资源的一级目录（全部资源）
  const {
    data: allSourceDramas,
    isLoading: allSourceLoading,
    refetch: refetchAllSource,
  } = useQuery({
    queryKey: ["pipeline", "library", "all-source"],
    queryFn: () => fetchPipelineFiles({ scope: "source" }),
  });

  // 获取选中剧集的子目录树
  const {
    data: pendingTreeData,
    isLoading: pendingTreeLoading,
    refetch: refetchPendingTree,
  } = useQuery({
    queryKey: ["pipeline", "library", "pending-tree", selectedPendingDrama],
    queryFn: () => fetchPipelineFiles({ scope: "source", drama: selectedPendingDrama! }),
    enabled: Boolean(selectedPendingDrama),
  });

  useEffect(() => {
    if (!referencedProgram || !processedData?.length) {
      return;
    }
    const normalized = processedData
      .map((node) => flattenNodes([node]))
      .reduce((acc, curr) => ({ ...acc, ...curr }), {});
    const match = Object.values(normalized).find((node) => {
      const programCode = extractProgramCode(node.path);
      return programCode && programCode.toLowerCase() === referencedProgram.toLowerCase();
    });
    if (!match) {
      return;
    }
    const timer = window.setTimeout(() => {
      setFocusedPath(match.path);
      setCheckedPaths([match.path]);
    }, 0);
    return () => window.clearTimeout(timer);
  }, [referencedProgram, processedData]);

  const processedTree = useMemo(() => processedData ?? [], [processedData]);
  const processedMap = useMemo(() => flattenNodes(processedTree), [processedTree]);
  const filteredProcessedTree = useMemo(
    () => buildTreeData(filterTree(processedTree, processedSearch)),
    [processedTree, processedSearch],
  );

  const pendingTree = useMemo(() => pendingTreeData ?? [], [pendingTreeData]);
  // 构建完整的路径映射
  // 后端返回的 path 应该是完整路径（如 "KR051P07S01_김대표의 엽기적인 부인/Episodes"）
  // 但我们需要确保所有路径都包含一级目录前缀，以便正确映射
  const pendingMap = useMemo(() => {
    const map: Record<string, PipelineFileNode> = {};
    const traverse = (items: PipelineFileNode[], parentPath?: string) => {
      items.forEach((node) => {
        // 后端返回的 path 应该是完整路径，但我们需要确保它包含一级目录
        let fullPath = node.path;
        if (selectedPendingDrama) {
          // 如果路径不包含一级目录前缀，则添加
          if (!fullPath.startsWith(selectedPendingDrama)) {
            // 如果路径是相对路径（如 "Episodes"），需要添加一级目录前缀
            if (parentPath) {
              fullPath = `${parentPath}/${node.path}`.replace(/\/+/g, "/");
            } else {
              fullPath = `${selectedPendingDrama}/${node.path}`.replace(/\/+/g, "/");
            }
          }
        }
        // 使用完整路径作为 key，并更新 node 的 path
        const updatedNode = { ...node, path: fullPath };
        map[fullPath] = updatedNode;
        if (node.children?.length) {
          traverse(node.children, fullPath);
        }
      });
    };
    traverse(pendingTree, selectedPendingDrama);
    return map;
  }, [pendingTree, selectedPendingDrama]);

  // 同时需要更新 pendingTree 中的路径，确保与 pendingMap 一致
  const normalizedPendingTree = useMemo(() => {
    if (!selectedPendingDrama) return pendingTree;
    const normalizeNode = (node: PipelineFileNode): PipelineFileNode => {
      let fullPath = node.path;
      if (!fullPath.startsWith(selectedPendingDrama)) {
        fullPath = `${selectedPendingDrama}/${node.path}`.replace(/\/+/g, "/");
      }
      return {
        ...node,
        path: fullPath,
        children: node.children?.map(normalizeNode),
      };
    };
    return pendingTree.map(normalizeNode);
  }, [pendingTree, selectedPendingDrama]);

  // 处理所有 source 资源的一级目录，按更新时间排序
  const allSourceDramasList = useMemo(() => {
    const list = allSourceDramas ?? [];
    // 过滤出目录
    const directories = list.filter((item) => item.is_directory);
    // 按更新时间排序（最新的在前），如果没有更新时间则按名称排序
    return directories.sort((a, b) => {
      if (a.updated_at && b.updated_at) {
        return new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime();
      }
      if (a.updated_at) return -1;
      if (b.updated_at) return 1;
      return (a.name || "").localeCompare(b.name || "");
    });
  }, [allSourceDramas]);

  const filteredPendingDramas = useMemo(() => {
    if (!pendingSearch.trim()) {
      return allSourceDramasList;
    }
    const lower = pendingSearch.toLowerCase();
    return allSourceDramasList.filter((item) =>
      item.name?.toLowerCase().includes(lower) ||
      item.path?.toLowerCase().includes(lower)
    );
  }, [allSourceDramasList, pendingSearch]);

  const normalizedCheckedPaths = useMemo(
    () => checkedPaths,
    [checkedPaths],
  );
  const selectedNodes = useMemo(() => {
    return normalizedCheckedPaths
      .map((path) => {
        // 先从 processedMap 中查找
        let node = processedMap[path];
        if (node) {
          return node;
        }
        // 如果找不到，说明是懒加载的子节点，需要构造节点信息
        // 从路径中提取名称和类型
        const pathParts = path.split('/').filter(Boolean);
        const name = pathParts[pathParts.length - 1] || path;
        // 判断是否为目录：如果路径以斜杠结尾，或者是已知的目录结构
        // 这里我们假设如果路径中没有文件扩展名，就是目录
        const isDirectory = !name.includes('.') ||
          (!name.match(/\.(mp4|srt|ass|vtt|mkv|avi|mov|wmv|flv|webm)$/i));

        return {
          name,
          path,
          is_directory: isDirectory,
          size_bytes: undefined,
          updated_at: undefined,
          children: undefined,
        } as PipelineFileNode;
      })
      .filter(Boolean);
  }, [normalizedCheckedPaths, processedMap]);
  const primaryNode = selectedNodes[0] ?? (focusedPath ? processedMap[focusedPath] : null);

  const pendingSelectedNodes = useMemo(() => {
    // 确保路径格式一致：pendingCheckedPaths 中的路径应该与 pendingMap 的 key 匹配
    // 对于懒加载的文件节点，如果 pendingMap 中没有，需要从路径构造节点信息
    return pendingCheckedPaths
      .map((path) => {
        // 如果路径不包含一级目录，尝试添加
        let lookupPath = path;
        if (selectedPendingDrama && !path.startsWith(selectedPendingDrama)) {
          lookupPath = `${selectedPendingDrama}/${path}`.replace(/\/+/g, "/");
        }

        // 先从 pendingMap 中查找
        let node = pendingMap[lookupPath] || pendingMap[path];

        // 如果找不到，说明是懒加载的文件节点，需要构造节点信息
        if (!node) {
          const pathParts = lookupPath.split('/');
          const name = pathParts[pathParts.length - 1];
          const isDirectory = !name.includes('.') || name.endsWith('/');
          node = {
            name,
            path: lookupPath,
            is_directory: isDirectory,
            size_bytes: undefined,
            updated_at: undefined,
            children: undefined,
          };
        }

        return node;
      })
      .filter(Boolean);
  }, [pendingCheckedPaths, pendingMap, selectedPendingDrama]);

  const downloadLinkMutation = useMutation({
    mutationFn: fetchDownloadLink,
    onError: (err: Error) => message.error(err.message ?? "获取下载链接失败"),
  });

  const nasMutation = useMutation({
    mutationFn: requestNasDownload,
    onError: (err: Error) => message.error(err.message ?? "创建 NAS 下载任务失败"),
    onSuccess: () => message.success("✅ NAS 任务已创建，等待本地连接。"),
  });

  const manualProcessMutation = useMutation({
    mutationFn: triggerManualProcess,
    onError: (err: Error) => message.error(err.message ?? "触发压制任务失败"),
    onSuccess: () => {
      message.success("压制任务已提交，请前往任务监控查看");
      setPendingCheckedPaths([]);
    },
  });

  const handleSelect = (
    _keys: React.Key[],
    info: {
      node: EventDataNode<DataNode>;
    },
  ) => {
    const nodeKey = info.node.key as string;
    setFocusedPath(nodeKey);

    // 在已压制tab下，点击节点名称时自动勾选该节点
    if (activeTab === "processed") {
      const currentChecked = new Set(checkedPaths);
      if (currentChecked.has(nodeKey)) {
        // 如果已选中，取消选中
        currentChecked.delete(nodeKey);
      } else {
        // 如果未选中，添加到选中列表
        currentChecked.add(nodeKey);
      }
      setCheckedPaths(Array.from(currentChecked));
    }
  };

  const handleCheck: TreeProps["onCheck"] = (checkedKeys) => {
    const keys = Array.isArray(checkedKeys)
      ? checkedKeys
      : (checkedKeys.checked as React.Key[]);
    const uniq = Array.from(new Set(keys.map((key) => String(key))));
    setCheckedPaths(uniq);
  };

  const resolveSelection = () => {
    if (selectedNodes.length) {
      return selectedNodes;
    }
    return primaryNode ? [primaryNode] : [];
  };

  const addDownloadTask = useCallback(
    (task: Omit<DownloadTask, "createdAt">) => {
      const next: DownloadTask = { ...task, createdAt: Date.now() };
      setDownloadTasks((prev) => [next, ...prev].slice(0, 8));
      setStatusPanelVisible(true);
      return next.id;
    },
    [],
  );

  const updateDownloadTask = useCallback((taskId: string, updates: Partial<DownloadTask>) => {
    setDownloadTasks((prev) =>
      prev.map((task) => (task.id === taskId ? { ...task, ...updates } : task)),
    );
  }, []);

  const removeDownloadTask = useCallback((taskId: string) => {
    setDownloadTasks((prev) => prev.filter((task) => task.id !== taskId));
  }, []);

  const hasProcessingTask = useMemo(
    () => downloadTasks.some((task) => task.status === "processing"),
    [downloadTasks],
  );

  useEffect(() => {
    if (!hasProcessingTask) {
      return;
    }
    const timer = window.setInterval(() => {
      setDownloadTasks((prev) =>
        prev.map((task) => {
          if (task.status !== "processing") {
            return task;
          }
          const delta = task.type === "zip" ? 4 : 12;
          const nextProgress = Math.min(task.progress + delta, 95);
          if (nextProgress === task.progress) {
            return task;
          }
          return { ...task, progress: nextProgress };
        }),
      );
    }, 2000);
    return () => window.clearInterval(timer);
  }, [hasProcessingTask]);

  const handleDownload = async () => {
    console.log("[handleDownload] 开始执行");
    const targets = resolveSelection();
    console.log("[handleDownload] 选中的目标:", targets);
    if (!targets.length) {
      message.warning("请选择至少一个文件或目录");
      return;
    }

    // Determine bucket based on active tab
    const bucket = activeTab === "processed" ? "vigloo_processed" : "vigloo_source";
    console.log("[handleDownload] 使用的bucket:", bucket);

    // 单文件直接下载
    const hasDirectory = targets.some((node) => node.is_directory);
    if (targets.length === 1 && !hasDirectory) {
      console.log("[handleDownload] 单文件下载模式");
      const target = targets[0]!;
      // 构建完整的GCS路径（后端API期望 gs://bucket/path 格式）
      const fullGcsPath = `gs://${bucket}/${target.path}`;
      try {
        const response = await downloadLinkMutation.mutateAsync(fullGcsPath);
        if (response?.url) {
          window.open(response.url, "_blank");
          message.success("下载链接已打开");
        } else {
          message.error("未返回可用下载链接");
        }
      } catch (err) {
        message.error(err instanceof Error ? err.message : "下载链接获取失败");
      }
      return;
    }

    // 多文件或目录：使用 File System Access API 直接下载
    console.log("[handleDownload] 多文件/目录下载模式，调用 startDownload");
    const payload = targets.map((node) => {
      // 确保路径包含完整的 bucket 前缀
      return `gs://${bucket}/${node.path}`;
    });
    console.log("[handleDownload] payload:", payload);
    // Use global context for zip download to persist state across navigation
    try {
      await startDownload(payload, bucket);
      console.log("[handleDownload] startDownload 调用完成");
    } catch (err) {
      console.error("[handleDownload] 下载失败:", err);
      message.error(`下载失败: ${err instanceof Error ? err.message : String(err)}`);
    }
  };

  const handleNasDownload = async () => {
    const targets = resolveSelection();
    if (!targets.length) {
      message.warning("请选择文件或目录");
      return;
    }
    await nasMutation.mutateAsync({
      drama_name: extractProgramCode(targets[0]?.path),
      files: targets.map((node) => node.path),
    });
  };

  const handleManualProcess = async () => {
    if (!selectedPendingDrama) {
      message.warning("请先选择一个资源");
      return;
    }
    if (!pendingSelectedNodes.length) {
      message.warning("请在目录树中勾选需要压制的文件或目录");
      return;
    }
    const prefix = `${selectedPendingDrama}/`;
    const filePaths = pendingSelectedNodes
      .map((node) => {
        if (!node?.path) return "";
        return node.path.startsWith(prefix) ? node.path.slice(prefix.length) : node.path;
      })
      .filter((path) => !!path);
    if (!filePaths.length) {
      message.warning("无法解析所选路径，请重试");
      return;
    }
    await manualProcessMutation.mutateAsync({
      drama_name: selectedPendingDrama,
      file_paths: filePaths,
    });
  };

  const displayNodes = resolveSelection();
  const visibleSelection = displayNodes.slice(0, 5);
  const extraSelectionCount = Math.max(displayNodes.length - visibleSelection.length, 0);
  const selectionCount = displayNodes.length;
  const isDownloadBusy = downloadLinkMutation.isPending;
  const pendingSelectionCount = pendingSelectedNodes.length;

  const selectionCard = (
    <Card
      title="下载确认"
      bordered={false}
      className="shadow-sm border border-gray-100"
      extra={
        <Badge count={selectionCount} showZero color="#1890ff">
          <span className="text-xs text-gray-500">已选</span>
        </Badge>
      }
    >
      {!selectionCount ? (
        <Empty description="请选择左侧的文件或目录" image={Empty.PRESENTED_IMAGE_SIMPLE} />
      ) : (
        <Space direction="vertical" size="middle" className="w-full">
          <List
            dataSource={visibleSelection}
            size="small"
            renderItem={(node) => (
              <List.Item className="px-0">
                <List.Item.Meta
                  avatar={
                    <Tag color={node.is_directory ? "gold" : "green"} bordered={false}>
                      {node.is_directory ? "目录" : "文件"}
                    </Tag>
                  }
                  title={
                    <div className="flex flex-col">
                      <span className="font-medium text-gray-900">{node.name}</span>
                      <Text type="secondary" code className="text-[11px] break-all">
                        {node.path}
                      </Text>
                    </div>
                  }
                  description={
                    <div className="flex flex-wrap gap-3 text-xs text-gray-500">
                      {!node.is_directory && <span>大小：{formatSize(node.size_bytes)}</span>}
                      <span>更新：{formatDate(node.updated_at)}</span>
                      <span>Program：{extractProgramCode(node.path) ?? "-"}</span>
                      {node.language && <span>语种：{node.language}</span>}
                    </div>
                  }
                />
              </List.Item>
            )}
          />
          {extraSelectionCount > 0 && (
            <Text type="secondary" className="text-xs">
              另外 {extraSelectionCount} 个项目将一起下载
            </Text>
          )}
          {selectionCount > 1 && (
            <Alert
              type="info"
              showIcon
              message={`多选模式（${selectionCount} 项）`}
              description="多文件或目录将触发 ZIP 打包任务，您可以在右下角查看打包状态。"
            />
          )}
          <Space wrap>
            <Button
              type="primary"
              icon={<DownloadOutlined />}
              disabled={!selectionCount || isDownloadBusy}
              onClick={handleDownload}
            >
              浏览器下载
            </Button>
            <Button
              icon={<SendOutlined />}
              disabled={!selectionCount || nasMutation.isPending}
              onClick={handleNasDownload}
            >
              下载到 NAS
            </Button>
          </Space>
          <Alert
            type="info"
            showIcon
            message="提示"
            description="单个文件生成签名链接直接下载；多文件或目录会创建 ZIP 任务并在后台打包。"
          />
        </Space>
      )}
    </Card>
  );

  const pendingSelectionCard = (
    <Card
      title="压制任务确认"
      bordered={false}
      className="shadow-sm border border-gray-100"
      extra={
        <Badge count={pendingSelectionCount} showZero color="#722ed1">
          <span className="text-xs text-gray-500">已选</span>
        </Badge>
      }
    >
      {!pendingSelectionCount ? (
        <Empty description="在左侧目录树勾选需要压制的文件或文件夹" image={Empty.PRESENTED_IMAGE_SIMPLE} />
      ) : (
        <Space direction="vertical" size="middle" className="w-full">
          <List
            dataSource={pendingSelectedNodes.slice(0, 6)}
            size="small"
            renderItem={(node) => (
              <List.Item className="px-0">
                <List.Item.Meta
                  avatar={
                    <Tag color={node?.is_directory ? "gold" : "green"} bordered={false}>
                      {node?.is_directory ? "目录" : "文件"}
                    </Tag>
                  }
                  title={<span className="font-medium">{node?.name ?? "-"}</span>}
                  description={
                    <div className="flex flex-col gap-1">
                      <code className="text-xs text-gray-500 break-all">
                        {node?.path ? `gs://vigloo_source/${node.path}` : "-"}
                      </code>
                      {!node?.is_directory && node?.size_bytes && (
                        <Text type="secondary" className="text-xs">
                          大小：{formatSize(node.size_bytes)}
                        </Text>
                      )}
                    </div>
                  }
                />
              </List.Item>
            )}
          />
          {pendingSelectionCount > 6 && (
            <Text type="secondary" className="text-xs">
              还有 {pendingSelectionCount - 6} 项未展示...
            </Text>
          )}
          <div className="flex flex-wrap gap-3">
            <Button
              type="primary"
              icon={<SendOutlined />}
              disabled={!pendingSelectionCount}
              loading={manualProcessMutation.isPending}
              onClick={handleManualProcess}
            >
              压制字幕
            </Button>
            <Button onClick={() => setPendingCheckedPaths([])} disabled={!pendingSelectionCount}>
              清空选择
            </Button>
          </div>
          <Alert
            type="info"
            showIcon
            message="提示：压制任务会直接进入“任务监控”中，按所选路径生成字幕压制。"
          />
        </Space>
      )}
    </Card>
  );

  return (
    <div className="relative flex flex-col gap-6 px-4 py-6 md:px-8 lg:px-10">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <p className="text-xs uppercase font-semibold tracking-widest text-primary">
            Resource Library
          </p>
          <h1 className="text-2xl font-bold text-gray-900">资源库</h1>
          <p className="text-sm text-gray-500 mt-1">
            浏览 GCS 中的已压制/待压制资源，下载成品或补充触发字幕压制。
          </p>
        </div>
        <Space>
          <Link href="/pipeline/monitor">
            <Button icon={<CloudDownloadOutlined />}>返回任务监控</Button>
          </Link>
        </Space>
      </div>

      <Tabs
        activeKey={activeTab}
        onChange={(key) => setActiveTab(key as "processed" | "pending")}
        items={[
          { key: "processed", label: "已压制" },
          { key: "pending", label: "全部资源" },
        ]}
      />

      {activeTab === "processed" ? (
        <div className="grid gap-6 lg:grid-cols-[0.4fr_0.6fr]">
          <Card
            title="已压制内容"
            bordered={false}
            className="shadow-sm border border-gray-100"
            extra={
              <Button
                icon={<ReloadOutlined />}
                size="small"
                loading={processedLoading}
                onClick={() => refetchProcessed()}
              >
                刷新
              </Button>
            }
          >
            <Space direction="vertical" size="middle" className="w-full">
              <Input
                allowClear
                placeholder="搜索 Program Code / 语种 / 文件名"
                prefix={<FolderOpenOutlined className="text-gray-400" />}
                value={processedSearch}
                onChange={(e) => setProcessedSearch(e.target.value)}
              />
              {processedError && (
                <Alert
                  type="error"
                  showIcon
                  message="无法获取已压制资源"
                  description={(processedError as Error)?.message ?? "请稍后重试"}
                />
              )}
              {processedLoading ? (
                <Skeleton active paragraph={{ rows: 6 }} />
              ) : (
                <ProgramBrowserTree
                  mode="gcs"
                  gcsScope="processed"
                  checkable
                  checkedKeys={normalizedCheckedPaths}
                  onCheck={handleCheck}
                  selectedKeys={focusedPath ? [focusedPath] : []}
                  onNodeSelect={handleSelect}
                />
              )}
            </Space>
          </Card>
          {selectionCard}
        </div>
      ) : (
        <div className="grid gap-6">
          <div className="grid gap-6 lg:grid-cols-[0.35fr_0.65fr]">
            <Card
              title="全部资源"
              bordered={false}
              className="shadow-sm border border-gray-100"
              extra={
                <Button
                  icon={<ReloadOutlined />}
                  size="small"
                  loading={allSourceLoading}
                  onClick={() => refetchAllSource()}
                >
                  刷新
                </Button>
              }
            >
              <Space direction="vertical" size="middle" className="w-full">
                <Input
                  allowClear
                  placeholder="搜索 Program Code 或路径"
                  value={pendingSearch}
                  onChange={(e) => setPendingSearch(e.target.value)}
                />
                <List
                  size="small"
                  dataSource={filteredPendingDramas ?? []}
                  loading={allSourceLoading}
                  locale={{
                    emptyText: (
                      <Empty description="暂无资源" image={Empty.PRESENTED_IMAGE_SIMPLE} />
                    ),
                  }}
                  renderItem={(item) => {
                    const dramaName = item.name || item.path || "";
                    const isSelected = selectedPendingDrama === dramaName;
                    return (
                      <List.Item
                        className={`cursor-pointer rounded px-2 py-1 ${isSelected ? "bg-blue-50" : ""
                          }`}
                        onClick={() => {
                          setSelectedPendingDrama(dramaName);
                          setPendingCheckedPaths([]);
                          refetchPendingTree();
                        }}
                      >
                        <div className="flex w-full items-center justify-between">
                          <div className="flex flex-col flex-1 min-w-0">
                            <span className="font-medium text-gray-800 truncate">{dramaName}</span>
                            {item.updated_at && (
                              <Text type="secondary" className="text-xs">
                                {formatDate(item.updated_at)}
                              </Text>
                            )}
                          </div>
                          {isSelected && (
                            <Tag color="blue" bordered={false}>
                              当前
                            </Tag>
                          )}
                        </div>
                      </List.Item>
                    );
                  }}
                />
              </Space>
            </Card>

            <Card
              title={
                <div className="flex items-center gap-2">
                  <span>目录浏览</span>
                  {selectedPendingDrama && (
                    <Tag color="default" bordered={false}>
                      {selectedPendingDrama}
                    </Tag>
                  )}
                </div>
              }
              bordered={false}
              className="shadow-sm border border-gray-100"
              extra={
                <Button
                  icon={<ReloadOutlined />}
                  size="small"
                  disabled={!selectedPendingDrama}
                  loading={pendingTreeLoading}
                  onClick={() => refetchPendingTree()}
                >
                  刷新目录
                </Button>
              }
            >
              {!selectedPendingDrama ? (
                <Empty description="请选择左侧资源后查看目录结构" image={Empty.PRESENTED_IMAGE_SIMPLE} />
              ) : pendingTreeLoading ? (
                <Skeleton active paragraph={{ rows: 6 }} />
              ) : (
                <ProgramBrowserTree
                  mode="gcs"
                  gcsScope="source"
                  checkable
                  checkedKeys={pendingCheckedPaths}
                  onCheck={(keys) => {
                    const arr = Array.isArray(keys)
                      ? keys
                      : (keys.checked as React.Key[]);
                    setPendingCheckedPaths(Array.from(new Set(arr.map((key) => String(key)))));
                  }}
                  selectedKeys={[]}
                  onNodeSelect={() => { }}
                  initialGcsData={normalizedPendingTree}
                />
              )}
            </Card>
          </div>

          {pendingSelectionCard}
        </div>
      )}

      <DownloadStatusPanel
        tasks={downloadTasks}
        visible={isStatusPanelVisible}
        onHide={() => setStatusPanelVisible(false)}
        onShow={() => setStatusPanelVisible(true)}
        onRemove={removeDownloadTask}
      />
    </div>
  );
}

interface DownloadStatusPanelProps {
  tasks: DownloadTask[];
  visible: boolean;
  onHide: () => void;
  onShow: () => void;
  onRemove: (taskId: string) => void;
}

function DownloadStatusPanel({
  tasks,
  visible,
  onHide,
  onShow,
  onRemove,
}: DownloadStatusPanelProps) {
  if (!tasks.length) {
    return null;
  }

  const statusText: Record<DownloadTaskStatus, string> = {
    queued: "排队中",
    processing: "进行中",
    ready: "已完成",
    error: "失败",
  };

  const mapProgressStatus = (status: DownloadTaskStatus) => {
    if (status === "ready") return "success" as const;
    if (status === "error") return "exception" as const;
    return "active" as const;
  };

  if (!visible) {
    return (
      <Button
        type="primary"
        shape="round"
        className="fixed bottom-5 right-5 z-40 shadow-lg"
        onClick={onShow}
      >
        下载任务 ({tasks.length})
      </Button>
    );
  }

  return (
    <div className="fixed bottom-5 right-5 z-40 w-80 drop-shadow-2xl">
      <Card
        size="small"
        title={
          <span className="font-semibold text-gray-800">
            下载任务
            <Badge count={tasks.length} color="#722ed1" style={{ marginLeft: 8 }} />
          </span>
        }
        extra={
          <Button type="text" size="small" icon={<CloseOutlined />} onClick={onHide} />
        }
        styles={{ body: { maxHeight: 320, overflowY: "auto", paddingRight: 8 } }}
      >
        <Space direction="vertical" size="middle" className="w-full">
          {tasks.map((task) => (
            <div key={task.id} className="flex gap-3 rounded-md border border-gray-100 p-2">
              <Progress
                type="circle"
                width={46}
                percent={task.progress}
                status={mapProgressStatus(task.status)}
              />
              <div className="flex-1">
                <div className="flex items-center justify-between text-sm font-semibold">
                  <span className="truncate">{task.label}</span>
                  <Tag color={task.type === "zip" ? "geekblue" : "green"} bordered={false}>
                    {task.type === "zip" ? "ZIP" : "单个"}
                  </Tag>
                </div>
                <div className="text-xs text-gray-500">
                  {statusText[task.status]} · {task.detail ?? "正在处理..."}
                </div>
                <Text type="secondary" className="text-[10px]">
                  {new Date(task.createdAt).toLocaleTimeString()}
                </Text>
              </div>
              <Button
                type="text"
                size="small"
                icon={<CloseOutlined />}
                onClick={() => onRemove(task.id)}
              />
            </div>
          ))}
        </Space>
      </Card>
    </div>
  );
}

