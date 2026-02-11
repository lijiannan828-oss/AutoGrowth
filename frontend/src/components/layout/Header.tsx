"use client";

import { Button, Space, Typography } from "antd";
import { LogoutOutlined, UserOutlined } from "@ant-design/icons";

const { Text } = Typography;

export interface HeaderProps {
  currentStep?: 1 | 2 | 3;
  userEmail?: string;
  onLogout?: () => void;
}

export default function Header({
  currentStep,
  userEmail,
  onLogout,
}: HeaderProps) {
  return (
    <header className="bg-white border-b border-gray-200 sticky top-0 z-50 shadow-sm">
      <div className="container mx-auto px-4 py-3 md:py-4">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-2 md:gap-0">
          {/* Logo and Title */}
          <div className="flex items-center justify-between md:justify-start space-x-2 md:space-x-4">
            <Typography.Title level={4} className="!mb-0 text-base md:text-lg">
              短剧投放命名与链接自动化生成器
            </Typography.Title>
            {currentStep && (
              <Text type="secondary" className="text-xs md:text-sm whitespace-nowrap">
                步骤 {currentStep}/3
              </Text>
            )}
          </div>

          {/* User Info and Actions */}
          <div className="flex items-center justify-end space-x-2 md:space-x-4">
            {userEmail && (
              <Space size="small" className="hidden sm:flex">
                <UserOutlined />
                <Text type="secondary" className="text-xs md:text-sm truncate max-w-[150px] md:max-w-none">
                  {userEmail}
                </Text>
              </Space>
            )}
            {onLogout && (
              <Button
                type="text"
                icon={<LogoutOutlined />}
                onClick={onLogout}
                size="small"
                className="text-xs md:text-sm"
              >
                <span className="hidden sm:inline">登出</span>
              </Button>
            )}
          </div>
        </div>
      </div>
    </header>
  );
}

