"""Program repository for reading from database."""

from datetime import date
from typing import List, Optional

from sqlalchemy import or_, select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.program_info import ProgramInfo as ProgramInfoModel
from app.schemas.program import ProgramInfo, ProgramListResponse
from app.services.google_sheets_service import GoogleSheetsService
from app.core.config import settings


class ProgramRepository:
    """Repository for program data from database."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_all_programs(self, use_cache: bool = True) -> List[ProgramInfo]:
        """
        Get all programs from database.
        
        Args:
            use_cache: Ignored (kept for API compatibility)
        
        Returns:
            List of all ProgramInfo
        """
        stmt = select(ProgramInfoModel).order_by(
            ProgramInfoModel.release_date.desc().nulls_last(),
            ProgramInfoModel.updated_at.desc()
        )
        result = await self.db.execute(stmt)
        db_programs = result.scalars().all()
        items = [self._db_to_schema(p) for p in db_programs]

        # Fallback to Google Sheets when DB is empty and Sheets is configured
        if not items and settings.google_sheets_id:
            try:
                sheets = GoogleSheetsService()
                items = sheets.get_all_programs()
            except Exception as e:
                # Log and keep empty list; upstream can decide how to handle
                print(f"Sheets fallback failed in get_all_programs: {e}")
        return items
    
    async def list_programs(
        self,
        page: int = 1,
        page_size: int = 20,
        keyword: str | None = None,
        use_cache: bool = True,
    ) -> ProgramListResponse:
        """Return paginated and sorted program list from database."""

        if page < 1:
            page = 1
        if page_size < 1:
            page_size = 20

        # Build base query
        stmt = select(ProgramInfoModel)
        
        # Add keyword filter if provided
        if keyword:
            keyword_lower = keyword.lower().strip()
            stmt = stmt.where(
                or_(
                    ProgramInfoModel.program_code.ilike(f"%{keyword_lower}%"),
                    ProgramInfoModel.title.ilike(f"%{keyword_lower}%"),
                    ProgramInfoModel.program_id.ilike(f"%{keyword_lower}%"),
                )
            )
        
        # Get total count
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar_one()
        
        # Add ordering and pagination
        stmt = stmt.order_by(
            ProgramInfoModel.release_date.desc().nulls_last(),
            ProgramInfoModel.updated_at.desc()
        ).offset((page - 1) * page_size).limit(page_size)
        
        # Execute query
        result = await self.db.execute(stmt)
        db_programs = result.scalars().all()
        
        # Convert to schemas
        items = [self._db_to_schema(p) for p in db_programs]

        # Fallback to Sheets if DB has no items
        if not items and total == 0 and settings.google_sheets_id:
            try:
                sheets = GoogleSheetsService()
                all_items = sheets.get_all_programs()
                total = len(all_items)
                start = max((page - 1) * page_size, 0)
                end = start + page_size
                items = all_items[start:end]
            except Exception as e:
                print(f"Sheets fallback failed in list_programs: {e}")

        return ProgramListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
        )

    async def search_programs(self, query: str, use_cache: bool = True) -> List[ProgramInfo]:
        """
        Search programs by query from database.
        
        Args:
            query: Search keyword
            use_cache: Ignored (kept for API compatibility)
        
        Returns:
            List of matching ProgramInfo
        """
        query_lower = query.lower().strip()
        if not query_lower:
            return await self.get_all_programs()
        
        stmt = select(ProgramInfoModel).where(
            or_(
                ProgramInfoModel.program_code.ilike(f"%{query_lower}%"),
                ProgramInfoModel.title.ilike(f"%{query_lower}%"),
                ProgramInfoModel.program_id.ilike(f"%{query_lower}%"),
            )
        ).order_by(
            ProgramInfoModel.release_date.desc().nulls_last(),
            ProgramInfoModel.updated_at.desc()
        )
        
        result = await self.db.execute(stmt)
        db_programs = result.scalars().all()
        
        items = [self._db_to_schema(p) for p in db_programs]
        if not items and settings.google_sheets_id:
            try:
                sheets = GoogleSheetsService()
                items = sheets.search_programs(query_lower)
            except Exception as e:
                print(f"Sheets fallback failed in search_programs: {e}")
        return items
    
    async def get_program_by_code(self, program_code: str, use_cache: bool = True) -> Optional[ProgramInfo]:
        """
        Get a single program by ProgramCode from database.
        
        Args:
            program_code: Program Code to search for
            use_cache: Ignored (kept for API compatibility)
        
        Returns:
            ProgramInfo if found, None otherwise
        """
        stmt = select(ProgramInfoModel).where(ProgramInfoModel.program_code == program_code)
        result = await self.db.execute(stmt)
        db_program = result.scalar_one_or_none()
        
        if db_program is None:
            return None
        
        return self._db_to_schema(db_program)
    
    def _db_to_schema(self, db_program: ProgramInfoModel) -> ProgramInfo:
        """Convert database model to Pydantic schema."""
        return ProgramInfo(
            program_code=db_program.program_code,
            program_id=db_program.program_id,
            title=db_program.title,
            sub_title=db_program.sub_title,
            synopsis=db_program.synopsis,
            episode_count=db_program.episode_count,
            release_date=db_program.release_date,
            content_information=db_program.content_information,
            program_shortner=db_program.program_shortner,
            title_en_shortener=db_program.title_en_shortener,
            season_id=db_program.season_id,
        )
