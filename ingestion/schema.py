from pydantic import BaseModel, Field
from typing import List, Dict, Optional

class CaseDocument(BaseModel):
    doc_id: str
    case_name: str
    citation: str
    court: str
    court_level: int  # 1 = Supreme Court, 2 = Circuit Court, 3 = District Court, 4 = Administrative
    jurisdiction: str
    date_decided: str  # YYYY-MM-DD
    judges: List[str] = Field(default_factory=list)
    opinion_text: str
    headnotes: List[str] = Field(default_factory=list)
    citations_out: List[str] = Field(default_factory=list)  # doc_ids cited by this case
    practice_areas: List[str] = Field(default_factory=list)
    treatment_signals: Dict[str, List[str]] = Field(default_factory=dict) # e.g. {"followed_by": [], "overruled_by": []}

class SearchResult(BaseModel):
    doc_id: str
    case_name: str
    citation: str
    court: str
    court_level: int
    date_decided: str
    is_overruled: bool
    is_caution: bool = False
    overruled_by: List[str]
    score: float
    score_breakdown: Dict[str, float]
    snippet: str

class SearchResponse(BaseModel):
    results: List[SearchResult]
    total_results: int
    query_time_ms: float
    page: int = 1
    page_size: int = 10
    total_pages: int = 1
