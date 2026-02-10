export interface ProgramInfo {
  programCode: string;
  id: string; // Program ID (backend returns as "id")
  title: string;
  subTitle: string;
  synopsis: string;
  episodeCount: number;
  releaseDate: string | null;
  contentInformation: string;
  shortener?: string; // Program Shortener
  title_en_shortener?: string; // Title(EN/Shortener) (backend returns as snake_case)
  seasonId?: string | null; // Season ID
}

export interface ProgramListResponse {
  items: ProgramInfo[];
  total: number;
  page: number;
  pageSize: number;
}

