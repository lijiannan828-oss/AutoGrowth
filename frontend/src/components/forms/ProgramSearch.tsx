"use client";

import { useEffect, useMemo } from "react";
import { SearchOutlined } from "@ant-design/icons";
import type { AutoCompleteProps } from "antd";
import { AutoComplete, Input, Spin } from "antd";

import { useProgramSearch } from "@/hooks/useProgramSearch";
import type { ProgramInfo } from "@/types/api";

export interface ProgramSearchProps {
  onSelect: (program: ProgramInfo) => void;
  onKeywordChange?: (keyword: string) => void;
  onDebouncedKeywordChange?: (keyword: string) => void;
  value?: string;
  placeholder?: string;
  className?: string;
  autoFocus?: boolean;
}

type AutoCompleteOption = NonNullable<AutoCompleteProps["options"]>[number] & {
  program?: ProgramInfo;
};

const ProgramSearch = ({
  onSelect,
  onKeywordChange,
  onDebouncedKeywordChange,
  value = "",
  placeholder = "搜索剧目（标题、Program Code 或 ID）",
  className,
  autoFocus,
}: ProgramSearchProps) => {
  const {
    keyword,
    debouncedKeyword,
    setKeyword,
    options,
    results,
    isFetching,
    isLoading,
    isError,
    error,
  } = useProgramSearch(value);

  const autoCompleteOptions: AutoCompleteProps["options"] = useMemo(
    () =>
      options.map((option) => ({
        value: option.value,
        label: option.label,
        program: option.program,
      })),
    [options],
  );

  const handleSelect = (_value: string, option: AutoCompleteOption) => {
    const program = option.program ?? results.find((item) => item.programCode === _value);
    if (program) {
      onSelect(program);
      setKeyword(`${program.title} (${program.programCode})`);
    }
  };

  const handleChange = (nextKeyword: string) => {
    setKeyword(nextKeyword);
    onKeywordChange?.(nextKeyword);
  };

  // Notify parent when debounced keyword changes (用于列表过滤)
  useEffect(() => {
    onDebouncedKeywordChange?.(debouncedKeyword);
  }, [debouncedKeyword, onDebouncedKeywordChange]);

  const notFoundContent = useMemo(() => {
    if (isLoading || isFetching) {
      return (
        <div className="py-4 text-center">
          <Spin size="small" />
        </div>
      );
    }

    if (isError) {
      return (
        <div className="py-2 text-center text-sm text-red-500">
          {error?.message ?? "搜索失败，请稍后重试"}
        </div>
      );
    }

    return <div className="py-2 text-center text-sm text-gray-500">暂无匹配结果</div>;
  }, [isError, isFetching, isLoading, error]);

  return (
    <AutoComplete
      className={className}
      value={keyword}
      options={autoCompleteOptions}
      onChange={handleChange}
      onSearch={handleChange}
      onSelect={handleSelect}
      filterOption={false}
      notFoundContent={notFoundContent}
      classNames={{ popup: { root: "program-search-dropdown" } }}
    >
      <Input
        allowClear
        size="large"
        prefix={<SearchOutlined />}
        placeholder={placeholder}
        autoFocus={autoFocus}
      />
    </AutoComplete>
  );
};

export default ProgramSearch;

