"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import clsx from "clsx";
import { ApartmentOutlined, DashboardOutlined, FolderOpenOutlined } from "@ant-design/icons";

const navItems = [
  { label: "传输计划", href: "/pipeline/plan", icon: <ApartmentOutlined /> },
  { label: "任务监控", href: "/pipeline/monitor", icon: <DashboardOutlined /> },
  { label: "资源库", href: "/pipeline/library", icon: <FolderOpenOutlined /> },
];

export function PipelineSubnav() {
  const pathname = usePathname();

  return (
    <div className="border-b border-gray-200 bg-white">
      <div className="flex flex-wrap items-center gap-2 px-4 py-3 md:px-8">
        {navItems.map((item) => {
          const isActive =
            pathname === item.href ||
            (item.href !== "/pipeline" && pathname?.startsWith(item.href));

          return (
            <Link
              key={item.href}
              href={item.href}
              className={clsx(
                "inline-flex items-center gap-2 rounded-full px-4 py-2 text-sm font-medium transition-colors",
                isActive
                  ? "bg-primary/10 text-primary border border-primary/40"
                  : "text-gray-600 border border-transparent hover:bg-gray-100"
              )}
            >
              <span className="text-base">{item.icon}</span>
              {item.label}
            </Link>
          );
        })}
      </div>
    </div>
  );
}


