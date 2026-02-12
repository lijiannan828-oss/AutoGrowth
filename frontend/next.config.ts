// deploy trigger: 2026-02-12
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // 允许外部设备访问开发服务器
  allowedDevOrigins: ["*"],

  // 启用独立输出模式（用于 Docker 部署）
  output: 'standalone',

  // API 代理配置 - 根据环境变量决定后端地址
  async rewrites() {
    const backendUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    return [
      {
        source: '/api/v1/:path*',
        destination: `${backendUrl}/api/v1/:path*`,
      },
    ];
  },
};

export default nextConfig;
