export const formatRelativeTime = (iso?: string) => {
  if (!iso) return "未知";
  const diff = Date.now() - new Date(iso).getTime();
  if (Number.isNaN(diff)) return "未知";
  const minutes = Math.floor(diff / 60000);
  if (minutes < 1) return "刚刚";
  if (minutes < 60) return `${minutes} 分钟前`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} 小时前`;
  const days = Math.floor(hours / 24);
  return `${days} 天前`;
};

