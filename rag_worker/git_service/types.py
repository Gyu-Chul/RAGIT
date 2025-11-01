"""
Git Service 관련 타입 정의
"""

from typing import TypedDict, Optional


class CommitInfo(TypedDict):
    """커밋 정보 타입"""

    hash: str
    author_name: str
    author_email: str
    message: str
    date: str


class CloneResult(TypedDict):
    """Git Clone 결과 타입"""

    success: bool
    repo_name: str
    repo_path: str
    message: Optional[str]
    error: Optional[str]


class StatusResult(TypedDict):
    """Git Status 결과 타입"""

    success: bool
    repo_name: str
    repo_path: str
    branch: str
    has_changes: bool
    status: str
    latest_commit: Optional[CommitInfo]
    error: Optional[str]


class PullResult(TypedDict):
    """Git Pull 결과 타입"""

    success: bool
    repo_name: str
    repo_path: str
    message: Optional[str]
    error: Optional[str]


class DeleteResult(TypedDict):
    """Git Delete 결과 타입"""

    success: bool
    repo_name: str
    message: Optional[str]
    error: Optional[str]


from dataclasses import dataclass


@dataclass
class CommitChange:
    """Trace History 결과 타입"""

    commit_hash: str    # commit code
    commit_message: str
    author: str
    date: str
    code_before: Optional[str] = None
    code_after: Optional[str] = None
    highlighted_diff: str = ""