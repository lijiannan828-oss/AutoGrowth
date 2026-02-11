"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { HomeOutlined, DeploymentUnitOutlined, BranchesOutlined, PlayCircleOutlined, SoundOutlined, FileTextOutlined } from "@ant-design/icons";
import clsx from "clsx";

interface NavItem {
  label: string;
  href: string;
  icon: React.ReactNode;
}

const navItems: NavItem[] = [
  {
    label: "命名工具",
    href: "/",
    icon: <HomeOutlined />,
  },
  {
    label: "资源流水线",
    href: "/pipeline",
    icon: <DeploymentUnitOutlined />,
  },
  {
    label: "AI 裂变素材生成",
    href: "/fission",
    icon: <BranchesOutlined />,
  },
  {
    label: "AI 视频生成（待开发）",
    href: "/ai-video",
    icon: <PlayCircleOutlined />,
  },
  {
    label: "AI 多语言字幕生成",
    href: "/subtitle",
    icon: <FileTextOutlined />,
  },
  {
    label: "AI 文字转语音",
    href: "/text-to-speech",
    icon: <SoundOutlined />,
  },
];

export function SidebarNav() {
  const pathname = usePathname();

  return (
    <aside className="hidden md:flex md:w-64 lg:w-72 border-r border-gray-200 bg-white/90 backdrop-blur-sm">
      <nav className="flex-1 py-8 px-6 space-y-6">
        <div>
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-widest mb-4">
            控制面板
          </p>
          <ul className="space-y-1">
            {navItems.map((item) => {
              const isActive =
                pathname === item.href || (item.href !== "/" && pathname?.startsWith(item.href));

              return (
                <li key={item.href}>
                  <Link
                    href={item.href}
                    className={clsx(
                      "flex items-center space-x-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                      isActive
                        ? "bg-primary/10 text-primary"
                        : "text-gray-600 hover:text-primary hover:bg-gray-100"
                    )}
                  >
                    <span className="text-base">{item.icon}</span>
                    <span>{item.label}</span>
                  </Link>
                </li>
              );
            })}
          </ul>
        </div>
        <div className="rounded-lg border border-dashed border-gray-200 bg-gray-50 px-4 py-3 text-xs text-gray-500">
          <p className="font-medium text-gray-700">提示</p>
          <p>选择上方模块切换命名工具或资源流水线。</p>
        </div>
      </nav>
    </aside>
  );
}

export function MobileNavBar() {
  const pathname = usePathname();

  return (
    <nav className="md:hidden border-b border-gray-200 bg-white/80 backdrop-blur-sm sticky top-0 z-40">
      <ul className="flex items-center justify-around px-2 py-2 text-sm font-medium">
        {navItems.map((item) => {
          const isActive =
            pathname === item.href || (item.href !== "/" && pathname?.startsWith(item.href));

          return (
            <li key={item.href}>
              <Link
                href={item.href}
                className={clsx(
                  "flex flex-col items-center space-y-1 px-3 py-1 rounded-md",
                  isActive ? "text-primary" : "text-gray-500"
                )}
              >
                <span className="text-base">{item.icon}</span>
                <span>{item.label}</span>
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}

