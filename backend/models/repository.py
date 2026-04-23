from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime, timezone

def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _make_aware(v):
    if isinstance(v, datetime) and v.tzinfo is None:
        return v.replace(tzinfo=timezone.utc)
    return v

class ImportRequest(BaseModel):
    github_url: str
    branch: str = "main"


class ImportResponse(BaseModel):
    repo_id: str
    name: str
    file_count: int
    message: str
    status: Literal["ready", "pending", "failed"] = "ready"


# ── NEW: Sync response model ───────────────────────────────────────────────────
class SyncResponse(BaseModel):
    repo_id: str
    name: str
    added: int = 0
    modified: int = 0
    deleted: int = 0
    reanalyzed: int = 0
    message: str
    status: Literal["synced", "no_changes", "failed"] = "synced"
    # File-level diff for the frontend SyncDiffPanel
    added_files: List[str] = Field(default_factory=list)
    modified_files: List[str] = Field(default_factory=list)
    removed_files: List[str] = Field(default_factory=list)



class ExplainRequest(BaseModel):
    repo_id: str
    file_path: str


class ExplainResponse(BaseModel):
    file_path: str
    explanation: str
    dependencies: List[str] = Field(default_factory=list)
    cached: bool = False

class NodeData(BaseModel):
    label: str
    file_path: Optional[str] = None
    language: Optional[str] = "text"
    category: str = "other"
    sub_category: str = "other"
    node_color: str = "#6B7280"
    lines: int = 0
    imports: List[str] = Field(default_factory=list)
    exports: List[str] = Field(default_factory=list)
    is_circular: bool = False
    folder: str = "."
    github_url: str = ""
    is_dead: bool = False
    complexity_score: int = 1
    dependency_depth: int = -1
    is_dead_code: bool = False
    is_test_file: bool = False
    is_tested: bool = False
    analysis_status: str = "pending"


class GraphNode(BaseModel):
    id: str
    type: str = "codeNode"
    position: Dict[str, float] = Field(
        default_factory=lambda: {"x": 0.0, "y": 0.0}
    )
    data: NodeData


class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    animated: bool = False
    style: Dict[str, Any] = Field(default_factory=dict)
    is_circular: bool = False


class GraphResponse(BaseModel):
    repo_id: str
    nodes: List[GraphNode] = Field(default_factory=list)
    edges: List[GraphEdge] = Field(default_factory=list)
    circular_paths: List[List[str]] = Field(default_factory=list)
    is_semantic: bool = False


class RepositoryDoc(BaseModel):
    repo_id: str
    name: str
    owner: str
    branch: str
    file_count: int

    imported_at: datetime = Field(default_factory=_utcnow)
    github_url: str
    unique_key: str

    # Import pipeline state
    status: Literal["ready", "pending", "failed"] = "ready"
    error_message: Optional[str] = None

    # ── NEW: sync tracking fields ──────────────────────────────────────────
    # Stored as the HEAD commit SHA of the branch at time of last import/sync.
    # Used to detect whether the repo has changed since last sync.
    last_commit_sha: Optional[str] = None
    last_synced_at: Optional[datetime] = None

    @field_validator("imported_at", mode="before")
    @classmethod
    def make_aware(cls, v):
        return _make_aware(v)


class FileDoc(BaseModel):
    repo_id: str
    path: str
    name: str
    extension: str
    content: str
    size: int
    category: str = "other"
    language: str
    github_url: str = ""
    imports: List[str] = Field(default_factory=list)
    exports: List[str] = Field(default_factory=list)
    status: Literal["pending", "analyzed", "failed"] = "pending"
    analysis_error: Optional[str] = None

    # ── NEW: content hash for change detection ─────────────────────────────
    # MD5 of file content stored at import/sync time. On next sync we compare
    # the hash of the freshly downloaded file against this stored value to
    # detect modifications without doing a full text diff.
    content_hash: Optional[str] = None


class RepoSummary(BaseModel):
    model_config = {"populate_by_name": True}

    repo_id: str
    name: str
    owner: str = "unknown"
    branch: str = "main"
    file_count: int = 0

    imported_at: datetime = Field(default_factory=_utcnow)
    github_url: str = ""

    status: Literal["ready", "pending", "failed"] = "ready"
    error_message: Optional[str] = None

    # ── NEW: exposed in repo list for sync button state ────────────────────
    last_commit_sha: Optional[str] = None
    last_synced_at: Optional[datetime] = None

    @field_validator("imported_at", mode="before")
    @classmethod
    def make_aware(cls, v):
        return _make_aware(v)


class ChatMessage(BaseModel):
    role: str
    content: str


class ComponentChatRequest(BaseModel):
    repo_id: str
    file_path: str
    query: str
    history: List[ChatMessage] = Field(default_factory=list)


class RepoChatRequest(BaseModel):
    query: str
    history: List[ChatMessage] = Field(default_factory=list)