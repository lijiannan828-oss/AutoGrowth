// 统一的页面样式常量
export const pageStyles = {
  // 页面容器
  container: {
    padding: "24px",
    maxWidth: "1400px",
    margin: "0 auto",
    minHeight: "calc(100vh - 64px)",
    background: "#f5f7fa",
  },
  
  // 页面标题
  pageTitle: {
    fontSize: "28px",
    fontWeight: 600,
    marginBottom: "24px",
    color: "#1a1a2e",
    display: "flex",
    alignItems: "center",
    gap: "12px",
  },
  
  // 两栏布局
  twoColumnGrid: {
    display: "grid",
    gridTemplateColumns: "1fr 1fr",
    gap: "24px",
  },
  
  // 卡片样式
  card: {
    borderRadius: "12px",
    boxShadow: "0 2px 8px rgba(0,0,0,0.06)",
  },
  
  // 卡片标题
  cardTitle: {
    fontSize: "18px",
    fontWeight: 600,
    color: "#1a1a2e",
  },
  
  // 上传区域
  uploadArea: {
    border: "2px dashed #d9d9d9",
    borderRadius: "12px",
    padding: "32px",
    textAlign: "center" as const,
    background: "#fafafa",
    cursor: "pointer",
    transition: "all 0.3s",
  },
  
  uploadAreaHover: {
    border: "2px dashed #1890ff",
    background: "#e6f7ff",
  },
  
  // 任务列表项
  taskItem: {
    padding: "16px",
    borderRadius: "8px",
    background: "#fff",
    marginBottom: "12px",
    border: "1px solid #f0f0f0",
    transition: "all 0.3s",
  },
  
  // 状态标签颜色
  statusColors: {
    pending: { bg: "#f0f0f0", text: "#666", label: "等待中" },
    processing: { bg: "#e6f7ff", text: "#1890ff", label: "处理中" },
    completed: { bg: "#f6ffed", text: "#52c41a", label: "已完成" },
    failed: { bg: "#fff2f0", text: "#ff4d4f", label: "失败" },
  },
  
  // 主按钮渐变
  primaryButton: {
    background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
    border: "none",
    height: "44px",
    fontSize: "16px",
    fontWeight: 500,
  },
  
  // 次要按钮
  secondaryButton: {
    height: "36px",
    borderRadius: "6px",
  },
  
  // 提示文字
  helpText: {
    fontSize: "13px",
    color: "#8c8c8c",
    marginTop: "8px",
  },
  
  // 进度条
  progressBar: {
    height: "8px",
    borderRadius: "4px",
  },
  
  // 空状态
  emptyState: {
    padding: "48px 24px",
    textAlign: "center" as const,
    color: "#8c8c8c",
  },
  
  // 错误提示
  errorBox: {
    background: "#fff2f0",
    border: "1px solid #ffccc7",
    borderRadius: "8px",
    padding: "12px 16px",
    color: "#ff4d4f",
    fontSize: "14px",
  },
  
  // 成功提示
  successBox: {
    background: "#f6ffed",
    border: "1px solid #b7eb8f",
    borderRadius: "8px",
    padding: "12px 16px",
    color: "#52c41a",
    fontSize: "14px",
  },
};

// 主题色
export const themeColors = {
  primary: "#667eea",
  secondary: "#764ba2",
  success: "#52c41a",
  warning: "#faad14",
  error: "#ff4d4f",
  info: "#1890ff",
  textPrimary: "#1a1a2e",
  textSecondary: "#666",
  textMuted: "#8c8c8c",
  border: "#f0f0f0",
  background: "#f5f7fa",
};

