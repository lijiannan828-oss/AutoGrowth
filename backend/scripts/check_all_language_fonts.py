#!/usr/bin/env python3
"""全面检查所有语种的字体配置"""

import sys
from pathlib import Path

backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from app.workers.process.main import LANGUAGE_FONT_PREFERENCES, normalize_language_key
from google.cloud import storage

# 所有可能使用的语言及其对应的 Noto 字体包
LANGUAGE_TO_FONT_PACKAGE = {
    # CJK (中日韩) - 已安装 fonts-noto-cjk
    "zh": "fonts-noto-cjk",  # 简体中文
    "zh_cn": "fonts-noto-cjk",  # 简体中文
    "zh_tw": "fonts-noto-cjk",  # 繁体中文
    "ja": "fonts-noto-cjk",  # 日语
    "ko": "fonts-nanum",  # 韩语 (使用 nanum)
    
    # 东南亚语言
    "th": "fonts-noto-thai",  # 泰语
    "hi": "fonts-noto-devanagari",  # 印地语
    "id": "fonts-noto-sans",  # 印尼语 (使用通用 Noto Sans)
    "vi": "fonts-noto-sans",  # 越南语 (使用通用 Noto Sans)
    
    # 拉丁语系 - 使用通用 Noto Sans
    "en": "fonts-noto-sans",  # 英语
    "es": "fonts-noto-sans",  # 西班牙语
    "fr": "fonts-noto-sans",  # 法语
    "de": "fonts-noto-sans",  # 德语
    "pt": "fonts-noto-sans",  # 葡萄牙语
    "it": "fonts-noto-sans",  # 意大利语
    
    # 其他语言
    "ar": "fonts-noto-sans-arabic",  # 阿拉伯语
    "ru": "fonts-noto-sans-cyrillic",  # 俄语
}

# 检查实际使用的语言
def find_actual_languages():
    """从 GCS 中查找实际使用的语言"""
    client = storage.Client()
    bucket = client.bucket('vigloo_source')
    
    langs = set()
    count = 0
    for blob in bucket.list_blobs(prefix='', max_results=500):
        if blob.name.endswith('.srt'):
            parts = blob.name.split('/')
            for i, part in enumerate(parts):
                if 'subtitles' in part.lower() and i + 1 < len(parts):
                    lang = parts[i + 1].lower()
                    if lang and lang not in ['final', 'ready', 'completed', 'output', 'subtitles']:
                        langs.add(lang)
                        count += 1
                        if count > 200:
                            break
            if count > 200:
                break
    
    return sorted(langs)

def check_font_configuration():
    """检查字体配置"""
    print("="*80)
    print("全语种字体配置检查")
    print("="*80)
    
    # 1. 检查实际使用的语言
    print("\n1. 实际使用的语言代码 (从 GCS 中查找):")
    actual_langs = find_actual_languages()
    for lang in actual_langs:
        print(f"   - {lang}")
    
    # 2. 检查 LANGUAGE_FONT_PREFERENCES
    print("\n2. LANGUAGE_FONT_PREFERENCES 配置:")
    print("   " + "-"*76)
    for lang, fonts in sorted(LANGUAGE_FONT_PREFERENCES.items()):
        print(f"   {lang:15s}: {fonts}")
    
    # 3. 检查 Dockerfile 中的字体包
    print("\n3. Dockerfile 中安装的字体包:")
    dockerfile_path = backend_path / "app" / "workers" / "process" / "Dockerfile"
    with open(dockerfile_path) as f:
        content = f.read()
        # Extract font packages
        import re
        font_packages = re.findall(r'fonts-[^\s]+', content)
        print("   " + "-"*76)
        for pkg in sorted(set(font_packages)):
            print(f"   - {pkg}")
    
    # 4. 检查每个实际语言的配置
    print("\n4. 每个实际语言的配置检查:")
    print("   " + "-"*76)
    
    missing_font_config = []
    missing_font_package = []
    
    for lang in actual_langs:
        normalized = normalize_language_key(lang)
        has_config = normalized in LANGUAGE_FONT_PREFERENCES
        expected_package = LANGUAGE_TO_FONT_PACKAGE.get(normalized, "fonts-noto-sans")
        has_package = expected_package in content
        
        status_config = "✅" if has_config else "❌"
        status_package = "✅" if has_package else "❌"
        
        print(f"   {lang:20s} -> {normalized:10s} | 字体配置: {status_config:3s} | 字体包: {status_package:3s} ({expected_package})")
        
        if not has_config:
            missing_font_config.append((lang, normalized))
        if not has_package:
            missing_font_package.append((lang, normalized, expected_package))
    
    # 5. 总结问题
    print("\n5. 发现的问题:")
    print("   " + "-"*76)
    
    if missing_font_config:
        print(f"\n   ❌ 缺少字体配置的语言 ({len(missing_font_config)} 个):")
        for lang, normalized in missing_font_config:
            print(f"      - {lang} (标准化后: {normalized})")
    
    if missing_font_package:
        print(f"\n   ❌ 缺少字体包的语言 ({len(missing_font_package)} 个):")
        for lang, normalized, package in missing_font_package:
            print(f"      - {lang} (标准化后: {normalized}) 需要: {package}")
    
    if not missing_font_config and not missing_font_package:
        print("   ✅ 所有语言都有对应的字体配置和字体包")
    
    # 6. 建议的修复
    print("\n6. 建议的修复:")
    print("   " + "-"*76)
    
    if missing_font_config:
        print("\n   需要在 LANGUAGE_FONT_PREFERENCES 中添加:")
        for lang, normalized in missing_font_config:
            # 根据语言选择合适的字体
            if normalized in ['ar']:
                fonts = ['Noto Sans Arabic', 'Noto Sans']
            elif normalized in ['ru']:
                fonts = ['Noto Sans Cyrillic', 'Noto Sans']
            elif normalized in ['id', 'vi']:
                fonts = ['Noto Sans', 'Arial']
            elif normalized in ['fr', 'de', 'pt', 'it']:
                fonts = ['Noto Sans', 'Arial', 'Helvetica']
            else:
                fonts = ['Noto Sans', 'Arial']
            print(f'      "{normalized}": {fonts},')
    
    if missing_font_package:
        print("\n   需要在 Dockerfile 中添加字体包:")
        packages_to_add = sorted(set(pkg for _, _, pkg in missing_font_package))
        for pkg in packages_to_add:
            print(f"      {pkg}")
    
    print("\n" + "="*80)

if __name__ == "__main__":
    check_font_configuration()


