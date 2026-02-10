"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button, Card, Space, Typography } from "antd";
import Header from "@/components/layout/Header";
import StepIndicator from "@/components/layout/StepIndicator";
import ProgramSearch from "@/components/forms/ProgramSearch";
import ProgramList from "@/components/programs/ProgramList";
import { useProgramList } from "@/hooks/useProgramList";
import type { ProgramInfo } from "@/types/api";
import { useAuth } from "@/hooks/useAuth";

const { Title } = Typography;

export default function Home() {
  const router = useRouter();
  const { user, logout } = useAuth();
  const [searchInput, setSearchInput] = useState<string>("");
  const [searchKeyword, setSearchKeyword] = useState<string>("");
  const [selectedProgram, setSelectedProgram] = useState<ProgramInfo | null>(null);
  const pageSize = 20;

  const {
    programs,
    total,
    isLoading,
    isFetching,
    isFetchingNextPage,
    hasNextPage,
    loadMore,
  } = useProgramList({
    pageSize,
    keyword: searchKeyword || undefined,
  });

  const handleSearchSelect = (program: ProgramInfo) => {
    setSelectedProgram(program);
    setSearchInput(program.title);
    setSearchKeyword(program.title);
  };

  const handleProgramSelect = (program: ProgramInfo) => {
    setSelectedProgram(program);
  };

  const handleCreateAd = (program: ProgramInfo) => {
    router.push(`/generate/${program.programCode}`);
  };

  const handleDebouncedKeywordChange = (keyword: string) => {
    setSearchKeyword(keyword);
  };

  const userEmail = user?.email ?? "";
  const handleLogout = async () => {
    await logout();
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <Header currentStep={1} userEmail={userEmail} onLogout={handleLogout} />
      <StepIndicator current={1} />

      <div className="container mx-auto px-4 py-4 md:py-8">
        <div className="mb-4 md:mb-6">
          <Title level={2} className="text-xl md:text-3xl">步骤 1：选择剧目</Title>
          <p className="text-gray-600 text-sm md:text-base mt-2">
            从列表中选择或搜索要投放的剧目，然后点击&ldquo;去创建广告&rdquo;
          </p>
        </div>

        <Card className="mb-6">
          <Space direction="vertical" className="w-full" size="large">
            <div>
              <Title level={4}>搜索剧目</Title>
              <ProgramSearch
                onSelect={handleSearchSelect}
                onKeywordChange={setSearchInput}
                onDebouncedKeywordChange={handleDebouncedKeywordChange}
                placeholder="输入剧目名称、Program Code 或 ID 进行搜索"
                className="w-full"
              />
            </div>

            {selectedProgram && (
              <Card type="inner" className="bg-blue-50">
                <Space direction="vertical" className="w-full">
                  <div className="flex items-center justify-between">
                    <div>
                      <Title level={5} className="!mb-0">
                        {selectedProgram.title}
                      </Title>
                      <span className="text-sm text-gray-600">
                        {selectedProgram.programCode}
                      </span>
                    </div>
                    <Button
                      type="primary"
                      onClick={() => {
                        if (selectedProgram) {
                          handleCreateAd(selectedProgram);
                        }
                      }}
                    >
                      去创建广告
                    </Button>
                  </div>
                </Space>
              </Card>
            )}
          </Space>
        </Card>

        <Card>
          <div className="mb-4 flex items-center justify-between">
            <Title level={4} className="!mb-0">
              剧目列表
            </Title>
            <div className="text-sm text-gray-500">
              已加载 {programs.length}/{total} 个剧目，按上线时间倒序排列
            </div>
          </div>

          <ProgramList
            programs={programs}
            isLoading={isLoading}
            isFetching={isFetching}
            isFetchingNextPage={isFetchingNextPage}
            hasMore={hasNextPage}
            highlightKeyword={searchInput}
            onSelect={handleProgramSelect}
            onAction={(program) => handleCreateAd(program)}
            onLoadMore={loadMore}
            selectedProgramCode={selectedProgram?.programCode}
          />
        </Card>
      </div>
    </div>
  );
}
