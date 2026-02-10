import type { Metadata } from "next";
import { ConfigProvider, theme as antdTheme } from "antd";
import { Geist, Geist_Mono } from "next/font/google";
import "antd/dist/reset.css";
import "./globals.css";
import { Providers } from "@/lib/providers";
import { AppShell } from "@/components/layout/AppShell";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "短剧投放命名与链接自动化生成器",
  description: "内部投放命名与 OneLink 生成工具",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-Hans">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      >
        <Providers>
          <ConfigProvider
            theme={{
              algorithm: antdTheme.defaultAlgorithm,
              token: {
                fontFamily: "var(--font-geist-sans)",
              },
            }}
          >
            <AppShell>{children}</AppShell>
          </ConfigProvider>
        </Providers>
      </body>
    </html>
  );
}
