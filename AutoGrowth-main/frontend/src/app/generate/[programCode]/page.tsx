"use client";

import { useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { Button, Card, Space, Typography } from "antd";
import { ArrowLeftOutlined } from "@ant-design/icons";
import Header from "@/components/layout/Header";
import StepIndicator from "@/components/layout/StepIndicator";
import StrategyForm from "@/components/forms/StrategyForm";
import ResultDisplay from "@/components/output/ResultDisplay";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import type { ProgramInfo } from "@/types/api";
import type { StrategyFormData } from "@/types/form";
import type { GenerationResponse } from "@/types/generation";
import { useAuth } from "@/hooks/useAuth";
import { generateAdSetName, generateAdName } from "@/lib/naming-service";

const { Title } = Typography;

export default function GeneratePage() {
  const params = useParams();
  const router = useRouter();
  const { user, logout } = useAuth();
  const programCode = params.programCode as string;
  const formRef = useRef<HTMLDivElement>(null);
  const resultRef = useRef<HTMLDivElement>(null);
  const [showResults, setShowResults] = useState(false);

  // 离线模式开关 - 设为 true 时直接使用 mock 数据，不调用 API
  const OFFLINE_MODE = false;

  // Mock 数据，用于离线开发
  const mockProgram: ProgramInfo = {
    programCode: programCode,
    id: "12345678", // Mock 剧集ID
    title: "Test Drama Title", // 使用英文标题
    subTitle: "This is a mock drama for testing",
    synopsis: "",
    episodeCount: 10,
    releaseDate: new Date().toISOString(),
    contentInformation: "",
  };

  // 获取剧目信息
  const { data: program, isLoading, isError, error } = useQuery<ProgramInfo | undefined>({
    queryKey: ["program", programCode],
    queryFn: async () => {
      // 离线模式直接返回 mock 数据
      if (OFFLINE_MODE) {
        return mockProgram;
      }
      try {
        const response = await apiClient.get<{
          items: ProgramInfo[];
          total: number;
          page: number;
          pageSize: number;
        }>(`/data/programs?keyword=${encodeURIComponent(programCode)}&pageSize=100`);
        const programs = response.data.items || [];
        return programs.find((p) => p.programCode === programCode);
      } catch (err) {
        console.error("Failed to fetch program, using mock data:", err);
        // 返回 mock 数据而不是抛出错误
        return mockProgram;
      }
    },
    enabled: !!programCode,
    retry: 0, // 不重试，直接使用 mock 数据
  });

  // 自动滚动到表单区域
  useEffect(() => {
    if (program && formRef.current) {
      // 延迟滚动，确保 DOM 已渲染
      setTimeout(() => {
        formRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
      }, 100);
    }
  }, [program]);

  // 前端生成状态
  const [isGenerating, setIsGenerating] = useState(false);
  const [generationData, setGenerationData] = useState<GenerationResponse | null>(null);
  const [generationError, setGenerationError] = useState<Error | null>(null);

  const handleFormSubmit = async (data: StrategyFormData) => {
    // Reset previous results
    setGenerationData(null);
    setGenerationError(null);
    setShowResults(false);
    setIsGenerating(true);

    try {
      // 生成广告组名称
      const adSetName = generateAdSetName({
        country: data.adset.country,
        language: data.adset.language,
        mediaSource: data.adset.mediaSource,
        os: data.adset.os,
        optimizer: data.adset.optimizer,
        date: data.adset.date,
        dramaId: data.adset.dramaId,
        event: data.adset.event,
        optional: data.adset.optional,
      });

      // 生成广告名称
      const adResults = data.ads.map((ad) => {
        const adName = generateAdName({
          dramaId: ad.dramaId,
          language: ad.language,
          team: ad.team,
          designer: ad.designer,
          date: ad.date,
          creativeType: ad.creativeType,
          number: ad.number,
          optional: ad.optional,
        });

        return { adName };
      });

      // 设置生成结果
      setGenerationData({
        adSetName,
        adResults,
      });
      setShowResults(true);

      // Scroll to results
      setTimeout(() => {
        resultRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
      }, 100);
    } catch (error) {
      console.error("Generation failed:", error);
      setGenerationError(error instanceof Error ? error : new Error("生成失败"));
    } finally {
      setIsGenerating(false);
    }
  };

  const handleBack = () => {
    router.push("/");
  };

  const loggedInUser = user?.email ?? "";
  const userEmail = loggedInUser;
  const handleLogout = async () => {
    await logout();
  };

  // Determine current step based on whether results are shown
  const currentStep = showResults && generationData ? 3 : 2;

  return (
    <div className="min-h-screen bg-gray-50">
      <Header currentStep={currentStep} userEmail={userEmail} onLogout={handleLogout} />
      <StepIndicator current={currentStep} />

      <div className="container mx-auto px-4 py-4 md:py-8">
        <Button
          icon={<ArrowLeftOutlined />}
          onClick={handleBack}
          className="mb-4"
          size="small"
        >
          <span className="hidden sm:inline">返回剧目列表</span>
          <span className="sm:hidden">返回</span>
        </Button>

        {isLoading ? (
          <Card>
            <div className="py-8 text-center">加载中...</div>
          </Card>
        ) : isError ? (
          <Card>
            <div className="py-8 text-center">
              <Typography.Text type="danger">
                加载剧目信息失败: {error instanceof Error ? error.message : "未知错误"}
              </Typography.Text>
            </div>
          </Card>
        ) : program ? (
          <Space direction="vertical" className="w-full" size="large">
            <div>
              <Title level={2} className="!mb-2 text-xl md:text-3xl">
                步骤 2：填写策略
              </Title>
              <p className="text-gray-600 mb-4 text-sm md:text-base">
                为选中的剧目配置 Campaign、Ad Set 和 Ad 参数
              </p>
            </div>

            <Card>
              <Space direction="vertical" className="w-full" size="small">
                <Title level={4} className="!mb-0">
                  {program.title}
                </Title>
                <Typography.Text type="secondary" className="font-mono">
                  {program.programCode}
                </Typography.Text>
                {program.subTitle && (
                  <Typography.Text className="text-gray-600">
                    {program.subTitle}
                  </Typography.Text>
                )}
              </Space>
            </Card>

            <div ref={formRef}>
              <StrategyForm
                loggedInUser={loggedInUser}
                programId={program.id}
                onSubmit={handleFormSubmit}
              />
            </div>

            {/* Results Display */}
            {(showResults || isGenerating || generationError) && (
              <div ref={resultRef} className="mt-8">
                <ResultDisplay
                  data={generationData || null}
                  isLoading={isGenerating}
                  error={generationError || null}
                />
              </div>
            )}
          </Space>
        ) : (
          <Card>
            <div className="py-8 text-center">
              <Typography.Text type="danger">
                未找到剧目信息：{programCode}
              </Typography.Text>
            </div>
          </Card>
        )}
      </div>
    </div>
  );
}

