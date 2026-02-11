"""Service for synchronizing Program Info data from Google Sheets to database."""

import logging
from dataclasses import dataclass
from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.program_info import ProgramInfo
from app.schemas.program import ProgramInfo as ProgramInfoSchema
from app.services.google_sheets_service import GoogleSheetsService

logger = logging.getLogger(__name__)


@dataclass
class SyncResult:
    """Result of synchronization operation."""
    created: int = 0
    updated: int = 0
    total: int = 0
    errors: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []


class ProgramSyncService:
    """Service for synchronizing Program Info from Google Sheets to database."""
    
    def __init__(self):
        self.sheets_service = GoogleSheetsService()
    
    async def sync_from_sheets(self, db: AsyncSession) -> SyncResult:
        """
        Synchronize Program Info data from Google Sheets to database.
        
        Args:
            db: Database session
            
        Returns:
            SyncResult: Synchronization statistics
        """
        result = SyncResult()
        
        try:
            # Read data from Google Sheets
            logger.info("Reading Program Info from Google Sheets...")
            sheets_programs = self.sheets_service.get_all_programs()
            result.total = len(sheets_programs)
            logger.info(f"Found {result.total} programs in Google Sheets")
            
            # Read existing data from database
            logger.info("Reading existing Program Info from database...")
            stmt = select(ProgramInfo)
            db_result = await db.execute(stmt)
            db_programs = db_result.scalars().all()
            db_lookup = {p.program_code: p for p in db_programs}
            logger.info(f"Found {len(db_programs)} programs in database")
            
            # Process each program from Sheets
            for sheets_program in sheets_programs:
                try:
                    program_code = sheets_program.program_code
                    
                    if program_code in db_lookup:
                        # Update existing record
                        db_program = db_lookup[program_code]
                        if self._has_changes(db_program, sheets_program):
                            self._update_program(db_program, sheets_program)
                            result.updated += 1
                            logger.debug(f"Updated program: {program_code}")
                    else:
                        # Create new record
                        new_program = self._create_program(sheets_program)
                        db.add(new_program)
                        result.created += 1
                        logger.debug(f"Created program: {program_code}")
                except Exception as e:
                    error_msg = f"Error processing program {sheets_program.program_code}: {str(e)}"
                    logger.error(error_msg)
                    result.errors.append(error_msg)
            
            # Commit changes
            await db.commit()
            logger.info(f"Sync completed: {result.created} created, {result.updated} updated, {len(result.errors)} errors")
            
        except Exception as e:
            await db.rollback()
            error_msg = f"Sync failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            result.errors.append(error_msg)
            raise
        
        return result
    
    def _has_changes(self, db_program: ProgramInfo, sheets_program: ProgramInfoSchema) -> bool:
        """Check if database program differs from sheets program."""
        return (
            db_program.program_id != sheets_program.program_id or
            db_program.title != sheets_program.title or
            db_program.sub_title != sheets_program.sub_title or
            db_program.synopsis != sheets_program.synopsis or
            db_program.episode_count != sheets_program.episode_count or
            db_program.release_date != sheets_program.release_date or
            db_program.content_information != sheets_program.content_information or
            db_program.program_shortner != sheets_program.program_shortner or
            db_program.title_en_shortener != sheets_program.title_en_shortener or
            db_program.season_id != sheets_program.season_id
        )
    
    def _update_program(self, db_program: ProgramInfo, sheets_program: ProgramInfoSchema):
        """Update database program with data from sheets."""
        db_program.program_id = sheets_program.program_id
        db_program.title = sheets_program.title
        db_program.sub_title = sheets_program.sub_title
        db_program.synopsis = sheets_program.synopsis
        db_program.episode_count = sheets_program.episode_count
        db_program.release_date = sheets_program.release_date
        db_program.content_information = sheets_program.content_information
        db_program.program_shortner = sheets_program.program_shortner
        db_program.title_en_shortener = sheets_program.title_en_shortener
        db_program.season_id = sheets_program.season_id
    
    def _create_program(self, sheets_program: ProgramInfoSchema) -> ProgramInfo:
        """Create new ProgramInfo model from sheets data."""
        return ProgramInfo(
            program_code=sheets_program.program_code,
            program_id=sheets_program.program_id,
            title=sheets_program.title,
            sub_title=sheets_program.sub_title,
            synopsis=sheets_program.synopsis,
            episode_count=sheets_program.episode_count,
            release_date=sheets_program.release_date,
            content_information=sheets_program.content_information,
            program_shortner=sheets_program.program_shortner,
            title_en_shortener=sheets_program.title_en_shortener,
            season_id=sheets_program.season_id,
        )

