"""Google Sheets service for reading Program Info data."""

from datetime import date
from typing import List

import gspread
from gspread.exceptions import APIError, SpreadsheetNotFound

from app.core.config import settings
from app.core.google_sheets import get_gspread_client
from app.schemas.program import ProgramInfo


class GoogleSheetsService:
    """Service for reading program data from Google Sheets."""
    
    def __init__(self):
        self.client: gspread.Client | None = None
        self.sheet_id = settings.google_sheets_id
        if not self.sheet_id:
            raise ValueError("GOOGLE_SHEETS_ID not configured")
    
    def _get_client(self) -> gspread.Client:
        """Get or create gspread client."""
        if self.client is None:
            self.client = get_gspread_client()
        return self.client
    
    def _get_spreadsheet(self) -> gspread.Spreadsheet:
        """Open the Program Info spreadsheet."""
        client = self._get_client()
        try:
            return client.open_by_key(self.sheet_id)
        except SpreadsheetNotFound:
            raise ValueError(f"Spreadsheet {self.sheet_id} not found or not accessible")
    
    # Supported language sheets
    LANGUAGE_SHEETS = ["KO", "EN", "ZH-HANT", "ZH-HANS"]

    def _read_sheet_by_name(self, spreadsheet: gspread.Spreadsheet, sheet_name: str) -> List[dict]:
        """Read data from a specific worksheet by name."""
        try:
            sheet = spreadsheet.worksheet(sheet_name)
            records = sheet.get_all_records()
            return records
        except gspread.exceptions.WorksheetNotFound:
            raise ValueError(f"Sheet '{sheet_name}' not found")
        except APIError as e:
            raise ValueError(f"Error reading '{sheet_name}' sheet: {e}")

    def _read_en_sheet(self, spreadsheet: gspread.Spreadsheet) -> List[dict]:
        """Read data from 'EN' sheet (supports both 'EN' and 'En' for compatibility)."""
        try:
            # Try 'EN' first (new format), then 'En' (old format)
            try:
                sheet = spreadsheet.worksheet("EN")
            except gspread.exceptions.WorksheetNotFound:
                sheet = spreadsheet.worksheet("En")
            records = sheet.get_all_records()
            return records
        except gspread.exceptions.WorksheetNotFound:
            raise ValueError("Sheet 'EN' or 'En' not found")
        except APIError as e:
            raise ValueError(f"Error reading 'EN' sheet: {e}")
    
    def _read_shortener_sheet(self, spreadsheet: gspread.Spreadsheet) -> List[dict]:
        """Read data from 'Shortener' sheet."""
        try:
            sheet = spreadsheet.worksheet("Shortener")
            records = sheet.get_all_records()
            return records
        except gspread.exceptions.WorksheetNotFound:
            # Shortener sheet is optional, return empty list if not found
            return []
        except APIError as e:
            # Log warning but don't fail - shortener is optional
            print(f"Warning: Error reading 'Shortener' sheet: {e}")
            return []
    
    def get_all_programs(self) -> List[ProgramInfo]:
        """
        Fetch all programs from Google Sheets.

        Reads from 'EN' sheet which contains all program data including:
        programCode, id, title, subTitle, synopsis, episodeCount, releaseDate, etc.
        """
        spreadsheet = self._get_spreadsheet()

        # Read from EN sheet (contains all fields in new format)
        en_records = self._read_en_sheet(spreadsheet)

        # Read from Shortener sheet (optional)
        shortener_records = self._read_shortener_sheet(spreadsheet)

        # Create a lookup map for Shortener sheet data by ProgramCode
        shortener_lookup: dict[str, str] = {}
        for record in shortener_records:
            program_code_raw = record.get("programCode", "")
            program_code = str(program_code_raw).strip() if program_code_raw is not None else ""
            if not program_code:
                continue

            # Try both "Title (Shortner)" and "Title (Shortener)" for compatibility
            title_shortner = (
                record.get("Title (Shortner)", "") or
                record.get("Title (Shortener)", "") or
                record.get("title (Shortner)", "") or
                record.get("title (Shortener)", "")
            )
            if title_shortner:
                shortener_lookup[program_code] = str(title_shortner).strip()

        def _as_str(record: dict, key: str) -> str:
            value = record.get(key, "")
            return str(value).strip() if value is not None else ""

        # Build programs from EN sheet records
        programs = []
        for record in en_records:
            program_code = _as_str(record, "programCode")
            program_id = _as_str(record, "id")

            if not program_code or not program_id:
                continue

            title = _as_str(record, "title")
            sub_title = _as_str(record, "subTitle")
            synopsis = _as_str(record, "synopsis")
            content_information = _as_str(record, "contentInformation")

            # Parse seasonId
            season_id_raw = record.get("seasonId", "")
            if season_id_raw is not None:
                season_id_str = str(season_id_raw).strip()
                season_id = season_id_str if season_id_str else None
            else:
                season_id = None

            # Parse episode count
            episode_count_str = _as_str(record, "episodeCount")
            try:
                episode_count = int(episode_count_str) if episode_count_str else 0
            except (ValueError, TypeError):
                episode_count = 0

            # Parse release date
            release_date_str = _as_str(record, "releaseDate")
            release_date = None
            if release_date_str:
                try:
                    release_date = date.fromisoformat(release_date_str)
                except ValueError:
                    release_date = None

            # Get Shortener from Shortener sheet
            program_shortner = shortener_lookup.get(program_code, "")

            # Title(EN/Shortener): use shortener if available, otherwise use title
            title_en_shortener = program_shortner if program_shortner else title

            programs.append(
                ProgramInfo(
                    program_code=program_code,
                    program_id=program_id,
                    title=title,
                    sub_title=sub_title,
                    synopsis=synopsis,
                    episode_count=episode_count,
                    release_date=release_date,
                    content_information=content_information,
                    program_shortner=program_shortner,
                    title_en_shortener=title_en_shortener,
                    season_id=season_id,
                )
            )

        return programs
    
    def get_programs_by_language(self, language: str) -> List[dict]:
        """
        Fetch all programs from a specific language sheet.

        Args:
            language: Language code (KO, EN, ZH-HANT, ZH-HANS)

        Returns:
            List of raw program records from the specified language sheet
        """
        language_upper = language.upper()
        if language_upper not in self.LANGUAGE_SHEETS:
            raise ValueError(f"Unsupported language: {language}. Supported: {self.LANGUAGE_SHEETS}")

        spreadsheet = self._get_spreadsheet()
        return self._read_sheet_by_name(spreadsheet, language_upper)

    def get_all_languages_data(self) -> dict[str, List[dict]]:
        """
        Fetch all programs from all language sheets.

        Returns:
            Dictionary with language code as key and list of records as value.
            Example: {"KO": [...], "EN": [...], "ZH-HANT": [...], "ZH-HANS": [...]}
        """
        spreadsheet = self._get_spreadsheet()
        result: dict[str, List[dict]] = {}

        for lang in self.LANGUAGE_SHEETS:
            try:
                records = self._read_sheet_by_name(spreadsheet, lang)
                result[lang] = records
                print(f"Read {len(records)} records from {lang} sheet")
            except ValueError as e:
                print(f"Warning: Could not read {lang} sheet: {e}")
                result[lang] = []

        return result

    def search_programs(self, query: str) -> List[ProgramInfo]:
        """
        Search programs by ProgramCode or Title.

        Args:
            query: Search keyword (case-insensitive partial match)

        Returns:
            List of matching ProgramInfo
        """
        all_programs = self.get_all_programs()
        query_lower = query.lower().strip()

        if not query_lower:
            return all_programs

        results = []
        for program in all_programs:
            if (
                query_lower in program.program_code.lower()
                or query_lower in program.title.lower()
            ):
                results.append(program)

        return results
