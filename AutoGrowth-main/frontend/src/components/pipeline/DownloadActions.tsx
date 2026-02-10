"use client";

import { useState } from "react";
import { Button, Collapse, List, message } from "antd";
import { DownloadOutlined, SendOutlined, FolderOpenOutlined } from "@ant-design/icons";
import { useQuery } from "@tanstack/react-query";
import { fetchDownloadLink, fetchPipelineFiles, requestNasDownload } from "@/features/pipeline/api";

interface DownloadActionsProps {
  dramaName: string;
}

export function DownloadActions({ dramaName }: DownloadActionsProps) {
  const [open, setOpen] = useState(false);
  const filesQuery = useQuery({
    enabled: open,
    queryKey: ["pipeline", "downloads", dramaName],
    queryFn: () => fetchPipelineFiles({ scope: "processed", drama: dramaName }),
  });

  const handleDownload = async (path: string) => {
    try {
      const { url } = await fetchDownloadLink(path);
      if (!url) {
        message.error("未获取到下载链接");
        return;
      }
      window.open(url, "_blank");
    } catch (err) {
      message.error(err instanceof Error ? err.message : "下载链接获取失败");
    }
  };

  const handleNasDownload = async (path: string) => {
    try {
      await requestNasDownload({ drama_name: dramaName, files: [path] });
      message.success("已创建 NAS 下载任务");
    } catch (err) {
      message.error(err instanceof Error ? err.message : "NAS 任务创建失败");
    }
  };

  return (
    <Collapse
      bordered={false}
      items={[
        {
          key: "downloads",
          label: (
            <div className="flex items-center gap-2 text-sm">
              <FolderOpenOutlined />
              <span>查看成品文件</span>
            </div>
          ),
          children: (
            <div className="space-y-3">
              <Button size="small" onClick={() => window.open(`/pipeline/library?program=${encodeURIComponent(dramaName)}`, "_blank")}>
                打开资源库
              </Button>
              <List
                loading={filesQuery.isLoading}
                dataSource={filesQuery.data ?? []}
                locale={{ emptyText: "暂无文件" }}
                renderItem={(item) =>
                  item.is_directory ? null : (
                    <List.Item
                      actions={[
                        <Button
                          key="download"
                          type="link"
                          size="small"
                          icon={<DownloadOutlined />}
                          onClick={() => handleDownload(item.path)}
                        >
                          本地
                        </Button>,
                        <Button
                          key="nas"
                          type="link"
                          size="small"
                          icon={<SendOutlined />}
                          onClick={() => handleNasDownload(item.path)}
                        >
                          NAS
                        </Button>,
                      ]}
                    >
                      <List.Item.Meta
                        title={item.name}
                        description={`${(((item.size_bytes ?? 0) / (1024 * 1024))).toFixed(1)} MB`}
                      />
                    </List.Item>
                  )
                }
              />
            </div>
          ),
        },
      ]}
      activeKey={open ? ["downloads"] : []}
      onChange={(keys) => setOpen(keys.length > 0)}
    />
  );
}

