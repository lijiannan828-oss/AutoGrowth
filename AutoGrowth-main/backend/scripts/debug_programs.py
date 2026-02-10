import asyncio
from app.core.database import get_session, create_engine_with_connector
from app.repositories.program_repository import ProgramRepository

async def main():
    await create_engine_with_connector()
    async with get_session() as db:
        repo = ProgramRepository(db)
        try:
            res = await repo.list_programs(page=1, page_size=5, keyword=None)
            print("OK:", res.model_dump())
        except Exception as e:
            import traceback
            print("ERROR:", repr(e))
            traceback.print_exc()

asyncio.run(main())
