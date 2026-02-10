"use client";

import { useRouter } from "next/navigation";
import { Button, Card, Space, Typography, Row, Col } from "antd";
import { SoundOutlined, FileTextOutlined } from "@ant-design/icons";
import Header from "@/components/layout/Header";
import { useAuth } from "@/hooks/useAuth";

const { Title } = Typography;

export default function MediaToolsPage() {
  const router = useRouter();
  const { user, logout } = useAuth();

  const userEmail = user?.email ?? "";
  const handleLogout = async () => {
    await logout();
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="container mx-auto px-4 py-4 md:py-8">
        <div className="mb-6">
          <Title level={2} className="text-xl md:text-3xl">🎬 媒体工具中心</Title>
          <p className="text-gray-600 text-sm md:text-base mt-2">
            快速访问字幕生成和语音合成工具
          </p>
        </div>

        <Row gutter={[24, 24]}>
          <Col xs={24} md={12}>
            <Card
              hoverable
              className="h-full transition-all duration-300 hover:shadow-lg"
              onClick={() => router.push("/subtitle")}
            >
              <Space direction="vertical" className="w-full" size="large">
                <div className="flex justify-center">
                  <FileTextOutlined className="text-6xl text-purple-600" />
                </div>
                <div className="text-center">
                  <Title level={3} className="!mb-2">多语言字幕生成</Title>
                  <p className="text-gray-600">
                    上传音频/视频，自动识别语音并生成多语言字幕
                  </p>
                </div>
                <Button type="primary" size="large" block className="bg-purple-600 hover:bg-purple-700">
                  进入字幕工具 →
                </Button>
              </Space>
            </Card>
          </Col>

          <Col xs={24} md={12}>
            <Card
              hoverable
              className="h-full transition-all duration-300 hover:shadow-lg"
              onClick={() => router.push("/tts")}
            >
              <Space direction="vertical" className="w-full" size="large">
                <div className="flex justify-center">
                  <SoundOutlined className="text-6xl text-blue-600" />
                </div>
                <div className="text-center">
                  <Title level={3} className="!mb-2">文字转语音 (TTS)</Title>
                  <p className="text-gray-600">
                    将文本转换为自然流畅的语音，支持多种语言和音色
                  </p>
                </div>
                <Button type="primary" size="large" block className="bg-blue-600 hover:bg-blue-700">
                  进入 TTS 工具 →
                </Button>
              </Space>
            </Card>
          </Col>
        </Row>

        <Card className="mt-6 bg-gradient-to-r from-blue-50 to-purple-50">
          <Title level={4}>功能介绍</Title>
          <Row gutter={[16, 16]}>
            <Col xs={24} md={12}>
              <div>
                <h4 className="font-semibold mb-2">📝 字幕生成工具</h4>
                <ul className="text-sm text-gray-600 space-y-1">
                  <li>• 支持音频和视频文件上传</li>
                  <li>• 自动语音识别（ASR）转文字</li>
                  <li>• 多语言翻译（支持 20+ 语言）</li>
                  <li>• 导出 SRT/VTT 格式字幕</li>
                  <li>• 批量处理支持</li>
                </ul>
              </div>
            </Col>
            <Col xs={24} md={12}>
              <div>
                <h4 className="font-semibold mb-2">🎤 TTS 语音合成</h4>
                <ul className="text-sm text-gray-600 space-y-1">
                  <li>• Google Cloud TTS 高质量语音</li>
                  <li>• 多种语言和音色选择</li>
                  <li>• 自定义语速和音调</li>
                  <li>• 批量文本转语音</li>
                  <li>• MP3 格式导出</li>
                </ul>
              </div>
            </Col>
          </Row>
        </Card>
      </div>
    </div>
  );
}

