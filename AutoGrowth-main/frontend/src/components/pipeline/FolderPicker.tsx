"use client";

import { useEffect, useMemo, useState } from "react";
import { Alert, Checkbox, Empty, Input, List, Skeleton, Tag } from "antd";
import { browseDriveFolder } from "@/features/pipeline/api";
import type { FolderBrowseNode, GDriveProgram, PipelineFolder } from "@/features/pipeline/types";

interface FolderPickerProps {
  program?: GDriveProgram | null;
  value: string[];
  onChange: (next: string[]) => void;
  onFoldersLoaded?: (folders: PipelineFolder[]) => void;
}

export function FolderPicker({ program, value, onChange, onFoldersLoaded }: FolderPickerProps) {
  const [folders, setFolders] = useState<PipelineFolder[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string>();
  const [keyword, setKeyword] = useState("");

  useEffect(() => {
    if (!program?.path) {
      setFolders([]);
      onChange([]);
      onFoldersLoaded?.([]);
      return;
    }
    let mounted = true;
    const loadFolders = async () => {
      setLoading(true);
      setError(undefined);
      try {
        const rootId = program.gdrive_id;
        if (!rootId) {
          throw new Error("所选剧集缺少 gdrive_id，无法列出目录");
        }
        const result = await browseDriveFolder({
          driveFolderId: rootId,
          gcsPrefix: program.path,
        });
        if (mounted) {
          setFolders(result);
          onFoldersLoaded?.(result);
          const defaultSelections =
            result
              .filter((folder) => /episode|subtitle/i.test(folder.name))
              .map((folder) => folder.name) ?? [];
          onChange(defaultSelections.length ? defaultSelections : result.map((f) => f.name));
        }
      } catch (err) {
        if (mounted) {
          setError(err instanceof Error ? err.message : "加载目录失败");
        }
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    };
    loadFolders();
    return () => {
      mounted = false;
    };
  }, [program?.path]);

  const filtered = useMemo(() => {
    if (!keyword) return folders;
    return folders.filter((folder) => folder.name.toLowerCase().includes(keyword.toLowerCase()));
  }, [folders, keyword]);

  if (!program) {
    return (
      <Empty
        image={Empty.PRESENTED_IMAGE_SIMPLE}
        description="请选择左侧剧集以查看目录"
        className="py-10"
      />
    );
  }

  if (loading) {
    return <Skeleton active paragraph={{ rows: 5 }} />;
  }

  if (error) {
    return (
      <Alert
        type="error"
        showIcon
        message="加载目录失败"
        description={error}
      />
    );
  }

  if (!folders.length) {
    return (
      <Empty
        image={Empty.PRESENTED_IMAGE_SIMPLE}
        description="未找到可选目录"
        className="py-10"
      />
    );
  }

  return (
    <div className="space-y-4">
      <Input
        allowClear
        value={keyword}
        placeholder="搜索目录"
        onChange={(event) => setKeyword(event.target.value)}
      />
      <Checkbox.Group
        value={value}
        onChange={(vals) => onChange(vals as string[])}
        className="w-full"
      >
        <List
          dataSource={filtered}
          renderItem={(folder) => {
            const total = folder.files_total ?? folder.itemCount;
            const done = folder.files_in_gcs ?? 0;
            return (
              <List.Item className="px-0">
                <label className="flex w-full items-start gap-3">
                  <Checkbox value={folder.name} className="mt-1" />
                  <div className="flex-1 space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-sm">{folder.name}</span>
                      {total != null && (
                        <Tag bordered={false} color={done === total ? "green" : "blue"} className="text-xs">
                          {done}/{total}
                        </Tag>
                      )}
                    </div>
                    <p className="text-xs text-gray-500">
                      ID: {folder.id}
                    </p>
                  </div>
                </label>
              </List.Item>
            );
          }}
        />
      </Checkbox.Group>
    </div>
  );
}

