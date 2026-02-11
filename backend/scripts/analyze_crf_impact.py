#!/usr/bin/env python3
"""Analyze the impact of different CRF values on quality, file size, and processing time."""

# Current baseline (CRF 23)
BASELINE_CRF = 23
BASELINE_AVG_FILE_SIZE_MB = 22.27  # From actual data
BASELINE_TOTAL_FILES = 610
BASELINE_PROCESSING_TIME_MINUTES = 22.8  # From actual data

# CRF impact factors (based on FFmpeg documentation and empirical data)
# Rule of thumb: CRF每增加6，文件大小约减半；CRF每减少6，文件大小约翻倍
# CRF每减少1，文件大小约增加10-15%；CRF每增加1，文件大小约减少10-15%

def calculate_file_size_ratio(target_crf: int, baseline_crf: int) -> float:
    """Calculate file size ratio for target CRF compared to baseline.
    
    Formula: size_ratio = 2^((baseline_crf - target_crf) / 6)
    This is based on the rule that CRF每增加6，文件大小约减半
    """
    crf_diff = baseline_crf - target_crf
    # More accurate: each CRF point change ≈ 10-15% size change
    # Using 12% per CRF point as average
    size_multiplier = (1.12) ** crf_diff
    return size_multiplier


def calculate_encoding_time_ratio(target_crf: int, baseline_crf: int) -> float:
    """Calculate encoding time ratio for target CRF compared to baseline.
    
    Lower CRF (higher quality) requires more encoding time.
    Rule of thumb: CRF每减少1，编码时间约增加5-10%
    """
    crf_diff = baseline_crf - target_crf
    # Lower CRF = more time (positive diff = more time)
    # Using 7% per CRF point as average
    time_multiplier = (1.07) ** crf_diff
    return time_multiplier


def calculate_quality_score(crf: int) -> str:
    """Calculate quality score based on CRF value."""
    if crf <= 18:
        return "极高 (接近无损)"
    elif crf <= 20:
        return "很高"
    elif crf <= 23:
        return "高 (推荐)"
    elif crf <= 28:
        return "良好"
    else:
        return "可接受"


def analyze_crf_impact(target_crf: int):
    """Analyze the impact of using target CRF instead of baseline."""
    print(f"\n{'=' * 80}")
    print(f"  CRF {target_crf} 影响分析")
    print(f"{'=' * 80}")
    
    # Calculate file size impact
    size_ratio = calculate_file_size_ratio(target_crf, BASELINE_CRF)
    new_avg_file_size_mb = BASELINE_AVG_FILE_SIZE_MB * size_ratio
    new_total_size_gb = (new_avg_file_size_mb * BASELINE_TOTAL_FILES) / 1024
    baseline_total_size_gb = (BASELINE_AVG_FILE_SIZE_MB * BASELINE_TOTAL_FILES) / 1024
    size_change_gb = new_total_size_gb - baseline_total_size_gb
    size_change_percent = (size_ratio - 1) * 100
    
    # Calculate processing time impact
    time_ratio = calculate_encoding_time_ratio(target_crf, BASELINE_CRF)
    new_processing_time_minutes = BASELINE_PROCESSING_TIME_MINUTES * time_ratio
    time_change_minutes = new_processing_time_minutes - BASELINE_PROCESSING_TIME_MINUTES
    time_change_percent = (time_ratio - 1) * 100
    
    # Quality assessment
    quality = calculate_quality_score(target_crf)
    
    print(f"\n📊 文件大小影响:")
    print(f"  当前 (CRF {BASELINE_CRF}):")
    print(f"    平均文件大小: {BASELINE_AVG_FILE_SIZE_MB:.2f} MB")
    print(f"    总大小: {baseline_total_size_gb:.2f} GB")
    print(f"  使用 CRF {target_crf}:")
    print(f"    平均文件大小: {new_avg_file_size_mb:.2f} MB")
    print(f"    总大小: {new_total_size_gb:.2f} GB")
    print(f"    变化: {size_change_gb:+.2f} GB ({size_change_percent:+.1f}%)")
    
    print(f"\n⏱️  处理时间影响:")
    print(f"  当前 (CRF {BASELINE_CRF}):")
    print(f"    处理时间: {BASELINE_PROCESSING_TIME_MINUTES:.1f} 分钟")
    print(f"  使用 CRF {target_crf}:")
    print(f"    处理时间: {new_processing_time_minutes:.1f} 分钟 ({new_processing_time_minutes/60:.2f} 小时)")
    print(f"    变化: {time_change_minutes:+.1f} 分钟 ({time_change_percent:+.1f}%)")
    
    print(f"\n🎨 画质评估:")
    print(f"  当前 (CRF {BASELINE_CRF}): {calculate_quality_score(BASELINE_CRF)}")
    print(f"  使用 CRF {target_crf}: {quality}")
    
    if target_crf < BASELINE_CRF:
        print(f"\n✅ 优势:")
        print(f"    - 画质提升: {BASELINE_CRF - target_crf} 个CRF点")
        print(f"    - 文件大小更接近原始视频")
        print(f"    - 视觉质量明显改善")
        print(f"\n⚠️  劣势:")
        print(f"    - 文件大小增加 {abs(size_change_percent):.1f}%")
        print(f"    - 处理时间增加 {abs(time_change_percent):.1f}%")
        print(f"    - 存储成本增加")
    else:
        print(f"\n✅ 优势:")
        print(f"    - 文件大小减少 {abs(size_change_percent):.1f}%")
        print(f"    - 处理时间减少 {abs(time_change_percent):.1f}%")
        print(f"    - 存储成本降低")
        print(f"\n⚠️  劣势:")
        print(f"    - 画质降低: {target_crf - BASELINE_CRF} 个CRF点")
        print(f"    - 视觉质量可能下降")
    
    return {
        "crf": target_crf,
        "avg_file_size_mb": new_avg_file_size_mb,
        "total_size_gb": new_total_size_gb,
        "size_change_percent": size_change_percent,
        "processing_time_minutes": new_processing_time_minutes,
        "time_change_percent": time_change_percent,
        "quality": quality,
    }


def main():
    """Main analysis function."""
    print("=" * 80)
    print("  CRF 参数影响分析")
    print("=" * 80)
    print(f"\n基准数据 (CRF {BASELINE_CRF}):")
    print(f"  平均文件大小: {BASELINE_AVG_FILE_SIZE_MB:.2f} MB")
    print(f"  总文件数: {BASELINE_TOTAL_FILES}")
    print(f"  总大小: {(BASELINE_AVG_FILE_SIZE_MB * BASELINE_TOTAL_FILES) / 1024:.2f} GB")
    print(f"  处理时间: {BASELINE_PROCESSING_TIME_MINUTES:.1f} 分钟")
    print(f"  画质: {calculate_quality_score(BASELINE_CRF)}")
    
    # Analyze CRF 18
    crf18_result = analyze_crf_impact(18)
    
    # Analyze CRF 20
    crf20_result = analyze_crf_impact(20)
    
    # Compare all options
    baseline_total_size_gb = (BASELINE_AVG_FILE_SIZE_MB * BASELINE_TOTAL_FILES) / 1024
    print(f"\n{'=' * 80}")
    print("  对比总结")
    print(f"{'=' * 80}")
    print(f"\n{'CRF':<6} {'平均文件大小':<15} {'总大小':<12} {'处理时间':<15} {'画质':<20}")
    print("-" * 80)
    print(f"{BASELINE_CRF:<6} {BASELINE_AVG_FILE_SIZE_MB:>8.2f} MB    {baseline_total_size_gb:>8.2f} GB    {BASELINE_PROCESSING_TIME_MINUTES:>8.1f} 分钟    {calculate_quality_score(BASELINE_CRF):<20}")
    print(f"{20:<6} {crf20_result['avg_file_size_mb']:>8.2f} MB    {crf20_result['total_size_gb']:>8.2f} GB    {crf20_result['processing_time_minutes']:>8.1f} 分钟    {crf20_result['quality']:<20}")
    print(f"{18:<6} {crf18_result['avg_file_size_mb']:>8.2f} MB    {crf18_result['total_size_gb']:>8.2f} GB    {crf18_result['processing_time_minutes']:>8.1f} 分钟    {crf18_result['quality']:<20}")
    
    print(f"\n💡 建议:")
    print(f"  CRF 23 (当前):")
    print(f"    - 适合: 平衡质量和文件大小，处理速度快")
    print(f"    - 文件大小: 适中 ({BASELINE_AVG_FILE_SIZE_MB:.2f} MB/文件)")
    print(f"    - 处理时间: 最快 ({BASELINE_PROCESSING_TIME_MINUTES:.1f} 分钟)")
    print()
    print(f"  CRF 20:")
    print(f"    - 适合: 需要更高质量，可接受文件大小和处理时间增加")
    print(f"    - 文件大小: 增加 {abs(crf20_result['size_change_percent']):.1f}%")
    print(f"    - 处理时间: 增加 {abs(crf20_result['time_change_percent']):.1f}%")
    print()
    print(f"  CRF 18:")
    print(f"    - 适合: 需要极高画质，文件大小和处理时间不是主要考虑")
    print(f"    - 文件大小: 增加 {abs(crf18_result['size_change_percent']):.1f}%")
    print(f"    - 处理时间: 增加 {abs(crf18_result['time_change_percent']):.1f}%")
    
    print(f"\n📝 注意事项:")
    print(f"  - 以上估算基于经验公式，实际结果可能因视频内容而异")
    print(f"  - CRF值对文件大小的影响: 每减少1，文件大小约增加10-15%")
    print(f"  - CRF值对编码时间的影响: 每减少1，编码时间约增加5-10%")
    print(f"  - 画质差异: CRF 18 vs 23 的视觉差异通常很小，但在大屏幕上可能明显")
    print(f"  - 建议: 先用小样本测试，确认画质和文件大小是否符合预期")


if __name__ == "__main__":
    main()

