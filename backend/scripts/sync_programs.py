"""Script to perform initial Program Info sync from Google Sheets to database."""

import asyncio
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from app.core.database import create_engine_with_connector, get_session
from app.services.program_sync_service import ProgramSyncService


async def main():
    """Main sync function."""
    print("=" * 60)
    print("Program Info 数据同步脚本")
    print("=" * 60)
    
    try:
        # Initialize database connection
        print("\n🔌 初始化数据库连接...")
        await create_engine_with_connector()
        print("✅ 数据库连接成功")
        
        # Perform sync
        print("\n📊 开始同步数据...")
        sync_service = ProgramSyncService()
        
        async with get_session() as db:
            result = await sync_service.sync_from_sheets(db)
        
        # Display results
        print("\n" + "=" * 60)
        print("✅ 同步完成！")
        print("=" * 60)
        print(f"📈 统计信息:")
        print(f"  - 总记录数: {result.total}")
        print(f"  - 新增记录: {result.created}")
        print(f"  - 更新记录: {result.updated}")
        if result.errors:
            print(f"  - 错误数量: {len(result.errors)}")
            print("\n⚠️  错误详情:")
            for error in result.errors:
                print(f"    - {error}")
        else:
            print("  - 错误数量: 0")
        print("=" * 60)
        
        return 0
        
    except Exception as e:
        print(f"\n❌ 同步失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

