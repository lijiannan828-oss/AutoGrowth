"use client";

import { startTransition, useEffect, useMemo, useState } from "react";
import { Empty, Skeleton, Tree } from "antd";
import type { DataNode, EventDataNode, TreeProps } from "antd/es/tree";
import { useQuery } from "@tanstack/react-query";
import {
  browseDriveFolder,
  fetchPipelineFiles,
  fetchPipelineRoots,
} from "@/features/pipeline/api";
import type { PipelineFileNode } from "@/features/pipeline/types";

export interface ProgramSelection {
  id: string;
  name: string;
  path: string;
  gdriveId: string;
  inGcs: boolean;
  gcsPrefix: string;
}

export interface ProgramBrowserTreeProps {
  mode?: "gdrive" | "gcs";
  gcsScope?: "source" | "processed";
  selectedProgramId?: string; // For GDrive mode
  onSelect?: (program: ProgramSelection | null) => void; // For GDrive mode
  // Props for GCS/Library mode
  checkable?: boolean;
  checkedKeys?: React.Key[];
  onCheck?: TreeProps["onCheck"];
  onNodeSelect?: TreeProps["onSelect"];
  selectedKeys?: React.Key[];
  // Optional: provide initial data for GCS mode (for subdirectory browsing)
  initialGcsData?: PipelineFileNode[];
}

interface ProgramTreeNode extends DataNode {
  dataRef?: {
    id: string; // path for GCS
    label: string;
    path: string;
    gcsPrefix?: string;
    inGcs?: boolean;
    isDirectory?: boolean;
    size?: number;
  };
}

const renderProgramTitle = (name: string, inGcs: boolean, mode: "gdrive" | "gcs" = "gdrive") => (
  <div className="flex items-center gap-2 text-sm">
    {mode === "gdrive" && (
      <span
        className={`inline-block h-2.5 w-2.5 rounded-full ${inGcs ? "bg-green-500" : "bg-gray-400"}`}
        aria-label={inGcs ? "已传输" : "未传输"}
      />
    )}
    <span className="truncate">{name}</span>
  </div>
);

function updateTreeData(
  list: ProgramTreeNode[],
  key: React.Key,
  children: ProgramTreeNode[],
): ProgramTreeNode[] {
  return list.map((node) => {
    if (node.key === key) {
      return {
        ...node,
        children,
      };
    }
    if (node.children) {
      return {
        ...node,
        children: updateTreeData(node.children as ProgramTreeNode[], key, children),
      };
    }
    return node;
  });
}

export function ProgramBrowserTree({
  mode = "gdrive",
  gcsScope = "processed",
  selectedProgramId,
  selectedKeys: propsSelectedKeys,
  onSelect,
  checkable,
  checkedKeys,
  onCheck,
  onNodeSelect,
  initialGcsData,
}: ProgramBrowserTreeProps) {
  const { data: roots, isLoading: rootsLoading } = useQuery({
    queryKey: ["pipeline", "gdrive-roots"],
    queryFn: fetchPipelineRoots,
    enabled: mode === "gdrive",
  });

  const { data: gcsRoots, isLoading: gcsLoading } = useQuery({
    queryKey: ["pipeline", "gcs-roots", gcsScope],
    queryFn: () => fetchPipelineFiles({ scope: gcsScope }),
    enabled: mode === "gcs" && !initialGcsData,
  });

  const [treeData, setTreeData] = useState<ProgramTreeNode[]>([]);
  const [expandedKeys, setExpandedKeys] = useState<React.Key[]>([]);

  useEffect(() => {
    if (mode === "gdrive") {
      if (!roots) return;
      startTransition(() => {
        setTreeData(
          roots.map((root) => ({
            key: root.folder_id,
            title: renderProgramTitle(root.label, false, mode),
            selectable: false,
            disableCheckbox: true,
            // Use undefined instead of [] to indicate lazy loading
            // Ant Design Tree will trigger loadData when user expands the node
            children: undefined,
            isLeaf: false,
            dataRef: {
              id: root.folder_id,
              label: root.label,
              path: root.label,
              gcsPrefix: "",
            },
          })),
        );
      });
    } else if (mode === "gcs") {
      // Use initialGcsData if provided, otherwise use gcsRoots
      const dataSource = initialGcsData ?? gcsRoots;
      if (!dataSource) return;
      startTransition(() => {
        setTreeData(
          dataSource.map((node) => {
            // 确保路径是完整的，后端返回的 path 应该是完整路径
            const fullPath = node.path;
            return {
              key: fullPath,
              title: renderProgramTitle(node.name, false, mode),
              isLeaf: !node.is_directory,
              selectable: true,
              disableCheckbox: !checkable,
              dataRef: {
                id: fullPath,
                label: node.name,
                path: fullPath,
                isDirectory: node.is_directory,
                size: node.size_bytes,
              },
            };
          }),
        );
      });
    }
  }, [roots, gcsRoots, initialGcsData, mode, checkable, gcsScope]);

  const selectedKeys = useMemo(
    () => propsSelectedKeys ?? (selectedProgramId ? [selectedProgramId] : []),
    [selectedProgramId, propsSelectedKeys],
  );

  const handleLoadData = async (node: EventDataNode<ProgramTreeNode>) => {
    console.log("[ProgramBrowserTree] handleLoadData called", { 
      nodeKey: node.key, 
      hasChildren: !!node.children?.length,
      nodeTitle: node.title,
      dataRef: (node as ProgramTreeNode).dataRef
    });
    
    if (node.children && node.children.length) {
      // If node already has children, just expand it
      console.log("[ProgramBrowserTree] Node already has children, just expanding");
      setExpandedKeys((prev) =>
        prev.includes(node.key) ? prev : [...prev, node.key],
      );
      return;
    }
    const dataRef = (node as ProgramTreeNode).dataRef;
    if (!dataRef) {
      console.warn("[ProgramBrowserTree] No dataRef found for node", node);
      return;
    }
    
    console.log("[ProgramBrowserTree] Loading children for node", { nodeKey: node.key, dataRef, mode });

    let mapped: ProgramTreeNode[] = [];

    if (mode === "gdrive") {
      const children = await browseDriveFolder({
        driveFolderId: dataRef.id,
        gcsPrefix: dataRef.gcsPrefix,
      });
      mapped = children.map((folder) => ({
        key: folder.id,
        title: renderProgramTitle(folder.name, folder.in_gcs, mode),
        isLeaf: !folder.has_children,
        selectable: true,
        disableCheckbox: true,
        dataRef: {
          id: folder.id,
          label: folder.name,
          path: dataRef.path ? `${dataRef.path}/${folder.name}` : folder.name,
          gcsPrefix: dataRef.gcsPrefix
            ? `${dataRef.gcsPrefix}/${folder.name}`
            : folder.name,
          inGcs: folder.in_gcs,
        },
      }));
    } else {
      // GCS Mode
      const prefix = dataRef.path;
      const children = await fetchPipelineFiles({
        scope: gcsScope,
        drama: prefix,
      });

      mapped = children.map((file) => {
        // 后端返回的 path 应该是完整路径（如 "KR051P07S01_김대표의 엽기적인 부인/Episodes/subfolder"）
        // 但我们需要确保它是完整的
        let fullPath = file.path;
        
        // 如果后端返回的路径不是以当前前缀开头，说明是相对路径，需要拼接
        if (!fullPath.startsWith(prefix)) {
          fullPath = `${prefix}/${file.path}`.replace(/\/+/g, "/");
        }
        
        // 确保路径是完整的（去除开头的斜杠）
        fullPath = fullPath.replace(/^\/+/, "");
        
        return {
          key: fullPath,
          title: renderProgramTitle(file.name, false, mode),
          isLeaf: !file.is_directory,
          selectable: true,
          disableCheckbox: !checkable,
          dataRef: {
            id: fullPath,
            label: file.name,
            path: fullPath,
            isDirectory: file.is_directory,
            size: file.size_bytes,
          },
        };
      });
    }

    setTreeData((prev) => updateTreeData(prev, node.key, mapped));
    // Expand the node after loading its children
    setExpandedKeys((prev) =>
      prev.includes(node.key) ? prev : [...prev, node.key],
    );
  };

  const handleSelect: TreeProps["onSelect"] = (keys, info) => {
    if (onNodeSelect) {
      onNodeSelect(keys, info);
    }

    if (mode === "gdrive" && onSelect) {
      const dataRef = (info.node as ProgramTreeNode).dataRef;
      if (!dataRef) {
        onSelect(null);
        return;
      }
      // 允许选择非叶子节点（剧集节点），只要它有 dataRef
      // 剧集节点通常是根节点的直接子节点，不是叶子节点
      // 只有当节点是根节点（selectable: false）时才不选择
      if (info.node.selectable === false) {
        onSelect(null);
        return;
      }
      onSelect({
        id: dataRef.id,
        name: dataRef.label,
        path: dataRef.path,
        gdriveId: dataRef.id,
        inGcs: Boolean(dataRef.inGcs),
        gcsPrefix: dataRef.gcsPrefix ?? dataRef.label,
      });
    }
  };

  const isLoading = mode === "gdrive" ? rootsLoading : (initialGcsData ? false : gcsLoading);

  if (isLoading) {
    return <Skeleton active paragraph={{ rows: 8 }} />;
  }

  if (!treeData.length) {
    return (
      <Empty
        description={mode === "gdrive" ? "未配置 GDrive 根目录" : "暂无文件"}
        image={Empty.PRESENTED_IMAGE_SIMPLE}
      />
    );
  }

  return (
    <Tree
      className="max-h-[520px] overflow-y-auto pr-2"
      treeData={treeData}
      loadData={handleLoadData}
      expandedKeys={expandedKeys}
      onExpand={(keys) => setExpandedKeys(keys as React.Key[])}
      showLine
      selectable
      blockNode
      selectedKeys={selectedKeys}
      onSelect={handleSelect}
      checkable={checkable}
      checkedKeys={checkedKeys}
      onCheck={onCheck}
    />
  );
}
