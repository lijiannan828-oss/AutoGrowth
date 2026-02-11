"use client";

import { Empty, Skeleton, Tree } from "antd";
import type { DataNode, EventDataNode, TreeProps } from "antd/es/tree";
import { startTransition, useEffect, useMemo, useState } from "react";
import { browseDriveFolder } from "@/features/pipeline/api";
import type { ProgramSelection } from "./ProgramBrowserTree";
import type { FolderBrowseNode, SelectedFolderNode } from "@/features/pipeline/types";

interface DirectoryTreeSelectorProps {
  program?: ProgramSelection | null;
  value: SelectedFolderNode[];
  onChange: (next: SelectedFolderNode[]) => void;
}

interface FolderTreeNode extends DataNode {
  dataRef?: {
    id: string;
    name: string;
    path: string;
    gcsPrefix: string;
    inGcs?: boolean;
  };
}

type TreeKey = string | number;

const renderFolderTitle = (name: string, inGcs: boolean) => (
  <div className="flex items-center gap-2 text-sm">
    <span
      className={`inline-block h-2.5 w-2.5 rounded-full ${inGcs ? "bg-green-500" : "bg-gray-400"}`}
      aria-label={inGcs ? "已传输" : "未传输"}
    />
    <span className="truncate">{name}</span>
  </div>
);

function updateTreeData(list: FolderTreeNode[], key: TreeKey, children: FolderTreeNode[]): FolderTreeNode[] {
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
        children: updateTreeData(node.children as FolderTreeNode[], key, children),
      };
    }
    return node;
  });
}

function mapToTreeNodes(
  parentMeta: { path: string; gcsPrefix: string },
  folders: FolderBrowseNode[],
): FolderTreeNode[] {
  return folders.map((folder) => {
    const nextPath = `${parentMeta.path}/${folder.name}`;
    const nextPrefix = parentMeta.gcsPrefix
      ? `${parentMeta.gcsPrefix}/${folder.name}`
      : folder.name;
    return {
      key: folder.id,
      title: renderFolderTitle(folder.name, folder.in_gcs),
      isLeaf: !folder.has_children,
      checkable: true,
      dataRef: {
        id: folder.id,
        name: folder.name,
        path: nextPath,
        gcsPrefix: nextPrefix,
        inGcs: folder.in_gcs,
      },
    };
  });
}

export function DirectoryTreeSelector({ program, value, onChange }: DirectoryTreeSelectorProps) {
  const [treeData, setTreeData] = useState<FolderTreeNode[]>([]);
  const [initializing, setInitializing] = useState(false);
  const [expandedKeys, setExpandedKeys] = useState<TreeKey[]>([]);

  useEffect(() => {
    startTransition(() => {
      if (!program) {
        setTreeData([]);
        setExpandedKeys([]);
        onChange([]);
        return;
      }
      const rootNode: FolderTreeNode = {
        key: program.id,
        title: program.name,
        selectable: false,
        disableCheckbox: true,
        children: [],
        dataRef: {
          id: program.id,
          name: program.name,
          path: program.name,
          gcsPrefix: program.gcsPrefix,
        },
      };
      setTreeData([rootNode]);
      setExpandedKeys([program.id]);
      setInitializing(true);
      browseDriveFolder({
        driveFolderId: program.id,
        gcsPrefix: program.gcsPrefix,
      })
        .then((folders) => {
          startTransition(() => {
            setTreeData((prev) => {
              const children = mapToTreeNodes({ path: program.name, gcsPrefix: program.gcsPrefix }, folders);
              setExpandedKeys([program.id, ...children.map((child) => child.key as TreeKey)]);
              return updateTreeData(prev, program.id, children);
            });
          });
        })
        .finally(() => {
          startTransition(() => setInitializing(false));
        });
      onChange([]);
    });
  }, [program, onChange]);

  const checkedKeys = useMemo(() => value.map((folder) => folder.id), [value]);

  const handleLoadData = async (node: EventDataNode<FolderTreeNode>) => {
    if (!program) return;
    if (node.children && node.children.length) {
      setExpandedKeys((prev) =>
        prev.includes(node.key as TreeKey) ? prev : [...prev, node.key as TreeKey],
      );
      return;
    }
    const dataRef = (node as FolderTreeNode).dataRef;
    if (!dataRef) return;
    const folders = await browseDriveFolder({
      driveFolderId: dataRef.id,
      gcsPrefix: dataRef.gcsPrefix,
    });
    const children = mapToTreeNodes({ path: dataRef.path, gcsPrefix: dataRef.gcsPrefix }, folders);
    setTreeData((prev) => updateTreeData(prev, node.key as TreeKey, children));
    setExpandedKeys((prev) =>
      prev.includes(node.key as TreeKey) ? prev : [...prev, node.key as TreeKey],
    );
  };

  const handleCheck: TreeProps["onCheck"] = (_keys, info) => {
    const nodes = (info.checkedNodes as FolderTreeNode[])
      .filter((node) => node.checkable !== false && node.dataRef)
      .map((node) => node.dataRef!) as SelectedFolderNode[];
    onChange(nodes);
  };

  if (!program) {
    return (
      <Empty
        image={Empty.PRESENTED_IMAGE_SIMPLE}
        description="请选择左侧剧集以查看目录"
        className="py-10"
      />
    );
  }

  if (initializing) {
    return <Skeleton active paragraph={{ rows: 5 }} />;
  }

  return (
    <Tree
      checkable
      selectable={false}
      treeData={treeData}
      loadData={handleLoadData}
      checkedKeys={checkedKeys}
      onCheck={handleCheck}
      expandedKeys={expandedKeys}
      onExpand={(keys) => setExpandedKeys(keys as TreeKey[])}
      showLine
      className="max-h-[480px] overflow-y-auto pr-2"
    />
  );
}


