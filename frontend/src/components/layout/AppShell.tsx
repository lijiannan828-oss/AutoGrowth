"use client";

import { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import { Alert, Spin } from "antd";
import { useAuth } from "@/hooks/useAuth";
import { SidebarNav, MobileNavBar } from "@/components/layout/SidebarNav";

const PUBLIC_PATHS = ["/login"];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, loading, error, isFirebaseReady } = useAuth();
  const isPublic = PUBLIC_PATHS.some((path) => pathname?.startsWith(path));
  const allowDevMode = process.env.NODE_ENV === "development";

  useEffect(() => {
    if (!isPublic && !loading && !user) {
      router.replace("/login");
    }
    if (isPublic && user) {
      router.replace("/");
    }
  }, [isPublic, loading, user, router]);

  if (!isFirebaseReady && !allowDevMode) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
        <Alert
          type="error"
          showIcon
          message="缺少 Firebase 配置"
          description="请配置 NEXT_PUBLIC_FIREBASE_* 环境变量后重试。"
        />
      </div>
    );
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <Spin size="large" />
      </div>
    );
  }

  if (isPublic) {
    return <div className="min-h-screen bg-gray-50">{children}</div>;
  }

  if (!user) {
    // 等待上方 useEffect 重定向
    return null;
  }

  return (
    <div className="min-h-screen bg-gray-50 text-gray-900">
      <div className="flex min-h-screen">
        <SidebarNav />
        <div className="flex-1 flex flex-col">
          <MobileNavBar />
          <main className="flex-1">{children}</main>
        </div>
      </div>
      {error && (
        <div className="fixed bottom-4 right-4 max-w-sm">
          <Alert type="warning" message="登录提醒" description={error} showIcon />
        </div>
      )}
    </div>
  );
}

