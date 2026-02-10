"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { Alert, Button, Card, Space, Typography } from "antd";
import { GoogleOutlined } from "@ant-design/icons";
import { useAuth } from "@/hooks/useAuth";

const { Title, Paragraph } = Typography;
const isDevEnvironment = process.env.NODE_ENV === "development";

export default function LoginPage() {
  const router = useRouter();
  const { user, loading, error, signInWithGoogle, loginWithDevToken } = useAuth();

  useEffect(() => {
    if (!loading && user) {
      router.replace("/");
    }
  }, [user, loading, router]);

  const handleDevLogin = async () => {
    await loginWithDevToken();
    router.replace("/");
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4">
      <Card className="w-full max-w-md shadow-lg">
        <Space direction="vertical" size="large" className="w-full">
          <div className="text-center space-y-2">
            <Title level={3} className="!mb-0">
              登录 AutoGrowth 控制面板
            </Title>
            <Paragraph type="secondary">
              使用公司授权的 Google 账号登录后，即可访问命名工具与资源流水线。
            </Paragraph>
          </div>

          {error && (
            <Alert type="error" message="登录配置问题" description={error} showIcon />
          )}

          <Button
            type="primary"
            block
            icon={<GoogleOutlined />}
            size="large"
            loading={loading}
            onClick={signInWithGoogle}
          >
            使用 Google 登录
          </Button>

          {isDevEnvironment && (
            <Button block onClick={handleDevLogin} icon={<span>👨‍💻</span>}>
              开发模式一键登录
            </Button>
          )}
        </Space>
      </Card>
    </div>
  );
}

