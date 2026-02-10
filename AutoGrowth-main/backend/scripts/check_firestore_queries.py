#!/usr/bin/env python3
"""Check Firestore queries for index requirements.

This script scans Python files for Firestore queries and identifies
queries that require composite indexes.
"""

import re
import sys
from pathlib import Path
from typing import List, Tuple

def find_firestore_queries(file_path: Path) -> List[Tuple[int, str, str]]:
    """Find Firestore queries in a Python file.
    
    Returns:
        List of (line_number, query_pattern, context) tuples
    """
    queries = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.split('\n')
        
        # Check for multi-line queries (where + order_by pattern)
        # Look for patterns like: .where(...).order_by(...) or order_by after where
        pattern = r'\.where\([^)]+\)\s*\.order_by\([^)]+\)'
        for match in re.finditer(pattern, content, re.MULTILINE):
            line_num = content[:match.start()].count('\n') + 1
            query_line = match.group(0)
            
            # Get context (3 lines before and after)
            context_start = max(0, line_num - 4)
            context_end = min(len(lines), line_num + 3)
            context_lines = lines[context_start:context_end]
            context = '\n'.join(f"{context_start + i + 1:4d}| {line}" for i, line in enumerate(context_lines))
            
            queries.append((line_num, query_line, context))
        
        # Also check for separate where and order_by calls (multi-line)
        # Look for patterns where where() and order_by() are on different lines
        for i in range(len(lines)):
            line = lines[i]
            if '.where(' in line:
                # Check next 10 lines for order_by
                next_lines_text = '\n'.join(lines[i:min(i+10, len(lines))])
                if '.order_by(' in next_lines_text:
                    # Extract the query pattern
                    query_pattern = line.strip()
                    # Find order_by line
                    for j in range(i+1, min(i+10, len(lines))):
                        if '.order_by(' in lines[j]:
                            query_pattern += ' ... ' + lines[j].strip()
                            break
                    
                    context_start = max(0, i - 2)
                    context_end = min(len(lines), i + 8)
                    context_lines = lines[context_start:context_end]
                    context = '\n'.join(f"{context_start + j + 1:4d}| {line}" for j, line in enumerate(context_lines))
                    queries.append((i + 1, query_pattern, context))
                    break  # Avoid duplicate matches
    
    except Exception as exc:
        print(f"⚠️  Error reading {file_path}: {exc}", file=sys.stderr)
    
    return queries

def check_index_requirements(queries: List[Tuple[int, str, str]]) -> List[dict]:
    """Check if queries require composite indexes.
    
    Returns:
        List of query requirements
    """
    requirements = []
    
    for line_num, query_line, context in queries:
        # Extract fields from query
        where_matches = re.findall(r'\.where\(["\']([^"\']+)["\']', query_line)
        order_by_matches = re.findall(r'\.order_by\(["\']([^"\']+)["\']', query_line)
        
        if where_matches and order_by_matches:
            # Check if where and order_by use different fields
            where_fields = set(where_matches)
            order_by_fields = set(order_by_matches)
            
            if where_fields != order_by_fields:
                requirements.append({
                    'line': line_num,
                    'query': query_line,
                    'context': context,
                    'where_fields': list(where_fields),
                    'order_by_fields': list(order_by_fields),
                    'requires_index': True,
                })
    
    return requirements

def check_index_config(requirements: List[dict], indexes_file: Path) -> List[dict]:
    """Check if indexes are configured in firestore.indexes.json.
    
    Returns:
        List of requirements with index status
    """
    if not indexes_file.exists():
        for req in requirements:
            req['index_configured'] = False
            req['index_status'] = 'not_found'
        return requirements
    
    try:
        import json
        with open(indexes_file, 'r') as f:
            indexes_data = json.load(f)
        
        indexes = indexes_data.get('indexes', [])
        
        for req in requirements:
            # Check if index exists
            index_found = False
            for idx in indexes:
                fields = idx.get('fields', [])
                field_paths = [f.get('fieldPath') for f in fields]
                
                # Check if all required fields are in index
                required_fields = set(req['where_fields'] + req['order_by_fields'])
                if required_fields.issubset(set(field_paths)):
                    index_found = True
                    break
            
            req['index_configured'] = index_found
            req['index_status'] = 'configured' if index_found else 'missing'
    
    except Exception as exc:
        print(f"⚠️  Error reading indexes file: {exc}", file=sys.stderr)
        for req in requirements:
            req['index_configured'] = False
            req['index_status'] = 'error'
    
    return requirements

def main():
    """Main function."""
    if len(sys.argv) > 1:
        target_paths = [Path(p) for p in sys.argv[1:]]
    else:
        # Default: check backend/app directory
        backend_path = Path(__file__).parent.parent
        target_paths = list(backend_path.glob('**/*.py'))
    
    print("=" * 80)
    print("  Firestore 查询索引检查")
    print("=" * 80)
    print()
    
    all_requirements = []
    
    for file_path in target_paths:
        if not file_path.is_file():
            continue
        
        queries = find_firestore_queries(file_path)
        if queries:
            requirements = check_index_requirements(queries)
            if requirements:
                all_requirements.extend([
                    {**req, 'file': str(file_path)}
                    for req in requirements
                ])
    
    if not all_requirements:
        print("✅ 未发现需要索引的查询模式")
        return 0
    
    # Check index configuration
    indexes_file = Path(__file__).parent.parent.parent / 'firestore.indexes.json'
    all_requirements = check_index_config(all_requirements, indexes_file)
    
    print(f"⚠️  发现 {len(all_requirements)} 个需要索引的查询:")
    print()
    
    for req in all_requirements:
        print(f"文件: {req['file']}")
        print(f"行号: {req['line']}")
        print(f"查询: {req['query']}")
        print(f"Where 字段: {req['where_fields']}")
        print(f"Order By 字段: {req['order_by_fields']}")
        print(f"索引配置: {'✅ 已配置' if req['index_configured'] else '❌ 未配置'}")
        print()
        
        if not req['index_configured']:
            print("💡 建议:")
            print("  1. 添加索引到 firestore.indexes.json")
            print("  2. 部署索引: firebase deploy --only firestore:indexes")
            print("  3. 添加回退方案（如果索引未就绪）")
            print()
    
    # Summary
    configured_count = sum(1 for req in all_requirements if req['index_configured'])
    missing_count = len(all_requirements) - configured_count
    
    print("=" * 80)
    print("  总结")
    print("=" * 80)
    print(f"总查询数: {len(all_requirements)}")
    print(f"已配置索引: {configured_count}")
    print(f"未配置索引: {missing_count}")
    print()
    
    if missing_count > 0:
        print("❌ 发现未配置索引的查询，请添加索引配置")
        return 1
    else:
        print("✅ 所有查询的索引都已配置")
        return 0

if __name__ == "__main__":
    sys.exit(main())

