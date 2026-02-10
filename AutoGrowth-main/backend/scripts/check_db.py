import asyncio
from sqlalchemy import text
from app.core.database import create_engine_with_connector


async def main() -> None:
    await create_engine_with_connector()
    from app.core.database import engine
    async with engine.begin() as conn:
        res = await conn.execute(
            text(
                """
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = 'public' 
                  AND table_name IN ('program_info','generation_history','user','program_cache');
                """
            )
        )
        rows = res.fetchall()
        print("Tables:", [r[0] for r in rows])
        try:
            res2 = await conn.execute(text("SELECT count(*) FROM program_info"))
            print("program_info count:", res2.scalar())
        except Exception as e:
            print("program_info count error:", e)


if __name__ == "__main__":
    asyncio.run(main())






