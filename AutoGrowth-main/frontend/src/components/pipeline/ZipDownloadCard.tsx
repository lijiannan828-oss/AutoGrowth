"use client";

import { Card, Progress, Button, Typography, Badge } from "antd";
import { 
  CloseOutlined, 
  MinusOutlined, 
  ExpandAltOutlined, 
  DownloadOutlined,
  LoadingOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined
} from "@ant-design/icons";
import { useZipDownload } from "@/context/ZipDownloadContext";

const { Text } = Typography;

export function ZipDownloadCard() {
  const { 
    isVisible, 
    activeTaskCount,
    latestTask,
    isMinimized, 
    closeCard, 
    minimizeCard
  } = useZipDownload();

  if (!isVisible || !latestTask) return null;

  const { status, statusMessage, zipUrl, progress = 0, speedBps, estimatedSeconds, downloadedBytes, totalBytes } = latestTask;
  
  // 判断当前阶段：File System Access API 只有下载阶段
  // 下载阶段：PROCESSING 状态且包含"下载"
  const isDownloading = status === "PROCESSING" && (
    statusMessage.includes("下载") || 
    statusMessage.includes("download") ||
    progress > 0
  );
  const isPackaging = false; // File System Access API 不需要打包
  const isUploading = false; // File System Access API 不需要上传

  // Minimized View
  if (isMinimized) {
    return (
      <div className="fixed bottom-4 right-4 z-[9999] shadow-lg animate-fade-in" style={{ position: 'fixed' }}>
        <Badge count={activeTaskCount} offset={[-5, 5]}>
          <Button 
            type="primary" 
            shape="circle" 
            size="large" 
            icon={status === "PROCESSING" ? <LoadingOutlined /> : <DownloadOutlined />}
            onClick={minimizeCard}
            className="shadow-md"
          />
        </Badge>
        {status === "COMPLETE" && (
          <div className="absolute -top-1 -right-1 w-3 h-3 bg-green-500 rounded-full border-2 border-white" />
        )}
      </div>
    );
  }

  // Full Card View
  return (
    <Card 
      className="fixed bottom-4 right-4 z-[9999] w-80 shadow-xl border-gray-200 animate-slide-up"
      style={{ position: 'fixed' }}
      size="small"
      title={
        <div className="flex items-center gap-2 text-sm">
          {status === "PROCESSING" && <LoadingOutlined className="text-blue-500" />}
          {status === "COMPLETE" && <CheckCircleOutlined className="text-green-500" />}
          {status === "FAILED" && <ExclamationCircleOutlined className="text-red-500" />}
          <span>文件下载任务</span>
          {activeTaskCount > 1 && (
            <Badge count={activeTaskCount} style={{ backgroundColor: '#1890ff' }} />
          )}
        </div>
      }
      extra={
        <div className="flex gap-1">
          <Button 
            type="text" 
            size="small" 
            icon={<MinusOutlined />} 
            onClick={minimizeCard} 
          />
          <Button 
            type="text" 
            size="small" 
            icon={<CloseOutlined />} 
            onClick={closeCard} 
          />
        </div>
      }
    >
      <div className="flex gap-3 items-start">
        {/* 圆形进度条 - 小尺寸，显示在左侧 */}
        <div className="flex-shrink-0">
          <Progress
            type="circle"
            percent={progress}
            status={status === "FAILED" ? "exception" : status === "COMPLETE" ? "success" : "active"}
            size={64}
            strokeWidth={6}
            format={() => `${progress}%`}
          />
        </div>

        {/* 状态信息 - 显示在右侧 */}
        <div className="flex-1 min-w-0">
          <Text className="text-sm font-medium block mb-1">
            {status === "QUEUED" && "排队中..."}
            {status === "PROCESSING" && isDownloading && "下载中..."}
            {status === "PROCESSING" && isPackaging && "打包中..."}
            {status === "PROCESSING" && isUploading && "上传中..."}
            {status === "PROCESSING" && !isDownloading && !isPackaging && !isUploading && "处理中..."}
            {status === "COMPLETE" && "完成"}
            {status === "FAILED" && "失败"}
          </Text>
          <Text type="secondary" className="text-xs block truncate mb-1">
            {statusMessage}
          </Text>
          
          {/* 下载速度和预计时间 */}
          {status === "PROCESSING" && isDownloading && (speedBps || estimatedSeconds !== undefined) && (
            <div className="text-xs text-gray-500 space-y-0.5">
              {speedBps && speedBps > 0 && (
                <div>
                  速度: <span className="font-medium">{(speedBps / (1024 * 1024)).toFixed(1)} MB/s</span>
                </div>
              )}
              {estimatedSeconds !== undefined && estimatedSeconds !== null && (
                <div>
                  预计剩余: <span className="font-medium">
                    {estimatedSeconds < 60 
                      ? `${estimatedSeconds} 秒`
                      : estimatedSeconds < 3600
                      ? `${Math.floor(estimatedSeconds / 60)} 分钟 ${estimatedSeconds % 60} 秒`
                      : `${Math.floor(estimatedSeconds / 3600)} 小时 ${Math.floor((estimatedSeconds % 3600) / 60)} 分钟`
                    }
                  </span>
                </div>
              )}
              {downloadedBytes !== undefined && totalBytes !== undefined && totalBytes > 0 && (
                <div>
                  已下载: <span className="font-medium">
                    {(downloadedBytes / (1024 * 1024)).toFixed(1)} MB / {(totalBytes / (1024 * 1024)).toFixed(1)} MB
                  </span>
                </div>
              )}
            </div>
          )}
        </div>

        {/* 操作按钮 - File System Access API 不需要下载按钮，文件已直接写入本地 */}
        
        {status === "FAILED" && (
          <div className="bg-red-50 p-2 rounded text-xs text-red-600 break-words w-full">
            {statusMessage}
          </div>
        )}
      </div>
    </Card>
  );
}

