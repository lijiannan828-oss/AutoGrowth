"use client";

import { Modal, List, Button, Typography, Space } from "antd";
import { DownloadOutlined, ReloadOutlined } from "@ant-design/icons";

const { Text, Paragraph } = Typography;

export interface FailedFile {
  path: string;
  error: string;
}

interface DownloadFailureModalProps {
  open: boolean;
  failedFiles: FailedFile[];
  onClose: () => void;
  onRetry?: (files: FailedFile[]) => void;
  onExportLog?: (files: FailedFile[]) => void;
}

export function DownloadFailureModal({
  open,
  failedFiles,
  onClose,
  onRetry,
  onExportLog,
}: DownloadFailureModalProps) {
  const handleExportLog = () => {
    if (!onExportLog) return;
    
    // Create log content
    const logContent = failedFiles
      .map((file, index) => `${index + 1}. ${file.path}\n   错误: ${file.error}`)
      .join('\n\n');
    
    const fullLog = `下载失败文件列表\n生成时间: ${new Date().toLocaleString('zh-CN')}\n失败数量: ${failedFiles.length}\n\n${logContent}`;
    
    // Create blob and download
    const blob = new Blob([fullLog], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `download-failures-${Date.now()}.txt`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
    
    onExportLog(failedFiles);
  };

  const handleRetry = () => {
    if (onRetry) {
      onRetry(failedFiles);
    }
    onClose();
  };

  return (
    <Modal
      open={open}
      title="下载失败文件列表"
      onCancel={onClose}
      width={800}
      footer={[
        <Button key="close" onClick={onClose}>
          关闭
        </Button>,
        <Button
          key="export"
          icon={<DownloadOutlined />}
          onClick={handleExportLog}
        >
          导出失败日志
        </Button>,
        onRetry && (
          <Button
            key="retry"
            type="primary"
            icon={<ReloadOutlined />}
            onClick={handleRetry}
          >
            重试失败项
          </Button>
        ),
      ].filter(Boolean)}
    >
      <Space direction="vertical" className="w-full" size="middle">
        <Paragraph>
          <Text strong>共 {failedFiles.length} 个文件下载失败</Text>
        </Paragraph>
        
        <List
          bordered
          dataSource={failedFiles}
          pagination={
            failedFiles.length > 20
              ? {
                  pageSize: 20,
                  showSizeChanger: false,
                  showTotal: (total) => `共 ${total} 个失败文件`,
                }
              : false
          }
          renderItem={(item, index) => (
            <List.Item>
              <Space direction="vertical" size="small" className="w-full">
                <Text strong>{index + 1}. {item.path}</Text>
                <Text type="danger" className="text-xs">
                  错误: {item.error}
                </Text>
              </Space>
            </List.Item>
          )}
        />
      </Space>
    </Modal>
  );
}

