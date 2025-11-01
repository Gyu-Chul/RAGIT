"""
Git 관련 작업을 처리하는 서비스
"""

import logging
import os
import shutil
import stat
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, List
from .history_tracker import FunctionHistoryTracker

from .exceptions import (
    RepositoryNotFoundError,
    RepositoryAlreadyExistsError,
    GitCommandError,
    GitTimeoutError,
)
from .types import CloneResult, StatusResult, PullResult, DeleteResult, CommitInfo

logger = logging.getLogger(__name__)


class GitCommandRunner:
    """Git 명령어 실행을 담당하는 클래스"""

    @staticmethod
    def run(command: List[str], cwd: Optional[Path] = None, timeout: int = 300) -> Dict[str, Any]:
        """
        Git 명령어 실행

        Args:
            command: 실행할 명령어 리스트
            cwd: 명령어를 실행할 작업 디렉토리
            timeout: 명령어 타임아웃 (초)

        Returns:
            실행 결과

        Raises:
            GitTimeoutError: 명령어 타임아웃 시
            GitCommandError: 명령어 실행 실패 시
        """
        try:
            result = subprocess.run(
                command,
                cwd=cwd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=timeout,
            )

            if result.returncode != 0:
                logger.error(f"Git command failed: {' '.join(command)}")
                logger.error(f"Error: {result.stderr}")
                raise GitCommandError(result.stderr)

            return {"success": True, "stdout": result.stdout, "stderr": result.stderr}

        except subprocess.TimeoutExpired as e:
            logger.error(f"Git command timed out: {' '.join(command)}")
            raise GitTimeoutError(f"Command timed out after {timeout} seconds") from e

        except Exception as e:
            logger.error(f"Git command error: {str(e)}")
            raise GitCommandError(str(e)) from e


class RepositoryManager:
    """레포지토리 경로 관리를 담당하는 클래스"""

    def __init__(self, base_path: str = "repository") -> None:
        """
        RepositoryManager 초기화

        Args:
            base_path: 레포지토리를 저장할 기본 경로
        """
        # 현재 작업 디렉토리 기준으로 상대 경로 해석
        # Celery worker가 어디서 실행되든 프로젝트 루트의 repository 사용
        if Path(base_path).is_absolute():
            self.base_path: Path = Path(base_path)
        else:
            # 프로젝트 루트 찾기 (pyproject.toml 기준)
            current = Path.cwd()
            while current != current.parent:
                if (current / "pyproject.toml").exists():
                    self.base_path = current / base_path
                    break
                current = current.parent
            else:
                # pyproject.toml을 못 찾으면 현재 디렉토리 기준
                self.base_path = Path(base_path).resolve()

        self.base_path.mkdir(parents=True, exist_ok=True)

    def get_repo_path(self, repo_name: str) -> Path:
        """
        레포지토리 경로 반환

        Args:
            repo_name: 레포지토리 이름

        Returns:
            레포지토리 절대 경로
        """
        return self.base_path / repo_name

    def exists(self, repo_name: str) -> bool:
        """
        레포지토리 존재 여부 확인

        Args:
            repo_name: 레포지토리 이름

        Returns:
            존재 여부
        """
        return self.get_repo_path(repo_name).exists()

    def validate_exists(self, repo_name: str) -> None:
        """
        레포지토리 존재 여부 검증

        Args:
            repo_name: 레포지토리 이름

        Raises:
            RepositoryNotFoundError: 레포지토리가 없을 때
        """
        if not self.exists(repo_name):
            raise RepositoryNotFoundError(f"Repository {repo_name} not found")

    def validate_not_exists(self, repo_name: str) -> None:
        """
        레포지토리 미존재 여부 검증

        Args:
            repo_name: 레포지토리 이름

        Raises:
            RepositoryAlreadyExistsError: 레포지토리가 이미 있을 때
        """
        if self.exists(repo_name):
            raise RepositoryAlreadyExistsError(f"Repository {repo_name} already exists")


class GitService:
    """Git 작업을 처리하는 서비스 클래스"""

    def __init__(self, base_repository_path: str = "repository") -> None:
        """
        GitService 초기화

        Args:
            base_repository_path: 레포지토리를 저장할 기본 경로
        """
        self.repo_manager: RepositoryManager = RepositoryManager(base_repository_path)
        self.command_runner: GitCommandRunner = GitCommandRunner()

    def clone_repository(self, git_url: str, repo_name: Optional[str] = None) -> CloneResult:
        """
        Git 레포지토리 클론

        Args:
            git_url: Git 레포지토리 URL
            repo_name: 저장할 레포지토리 이름 (없으면 URL에서 추출)

        Returns:
            클론 결과
        """
        try:
            # repo_name이 없으면 URL에서 추출
            if not repo_name:
                repo_name = git_url.split("/")[-1].replace(".git", "")

            # 이미 존재하는지 확인
            self.repo_manager.validate_not_exists(repo_name)

            repo_path = self.repo_manager.get_repo_path(repo_name)

            # Git clone 실행
            logger.info(f"Cloning repository: {git_url} -> {repo_name}")
            self.command_runner.run(["git", "clone", git_url, str(repo_path)])

            logger.info(f"Repository cloned successfully: {repo_name}")
            return CloneResult(
                success=True,
                repo_name=repo_name,
                repo_path=str(repo_path),
                message="Repository cloned successfully",
                error=None,
            )

        except (RepositoryAlreadyExistsError, GitCommandError, GitTimeoutError) as e:
            error_msg = str(e)

            # Git이 설치되지 않은 경우 더 명확한 메시지 제공
            if "지정된 파일을 찾을 수 없습니다" in error_msg or "No such file or directory" in error_msg:
                error_msg = "Git이 설치되어 있지 않거나 PATH에 등록되지 않았습니다. Git을 설치한 후 다시 시도해주세요."

            logger.error(f"Clone repository error: {error_msg}")
            return CloneResult(
                success=False,
                repo_name=repo_name or "",
                repo_path="",
                message=error_msg,
                error=error_msg,
            )

    def check_commit_status(self, repo_name: str) -> StatusResult:
        """
        레포지토리 커밋 상태 확인

        Args:
            repo_name: 레포지토리 이름

        Returns:
            커밋 상태 정보
        """
        try:
            # 레포지토리 존재 확인
            self.repo_manager.validate_exists(repo_name)
            repo_path = self.repo_manager.get_repo_path(repo_name)

            # git status 실행
            status_result = self.command_runner.run(["git", "status", "--porcelain"], cwd=repo_path)

            # 최신 커밋 정보 가져오기
            log_result = self.command_runner.run(
                ["git", "log", "-1", "--pretty=format:%H|%an|%ae|%s|%ci"],
                cwd=repo_path,
            )

            # 브랜치 정보 가져오기
            branch_result = self.command_runner.run(["git", "branch", "--show-current"], cwd=repo_path)

            # 최신 커밋 정보 파싱
            commit_info: Optional[CommitInfo] = None
            if log_result["stdout"].strip():
                parts = log_result["stdout"].strip().split("|")
                if len(parts) == 5:
                    commit_info = CommitInfo(
                        hash=parts[0],
                        author_name=parts[1],
                        author_email=parts[2],
                        message=parts[3],
                        date=parts[4],
                    )

            return StatusResult(
                success=True,
                repo_name=repo_name,
                repo_path=str(repo_path),
                branch=branch_result["stdout"].strip(),
                has_changes=bool(status_result["stdout"].strip()),
                status=status_result["stdout"],
                latest_commit=commit_info,
                error=None,
            )

        except (RepositoryNotFoundError, GitCommandError, GitTimeoutError) as e:
            logger.error(f"Check commit status error: {str(e)}")
            return StatusResult(
                success=False,
                repo_name=repo_name,
                repo_path="",
                branch="",
                has_changes=False,
                status="",
                latest_commit=None,
                error=str(e),
            )

    def pull_repository(self, repo_name: str) -> PullResult:
        """
        레포지토리 pull (업데이트)

        Args:
            repo_name: 레포지토리 이름

        Returns:
            Pull 결과
        """
        try:
            # 레포지토리 존재 확인
            self.repo_manager.validate_exists(repo_name)
            repo_path = self.repo_manager.get_repo_path(repo_name)

            # git pull 실행
            logger.info(f"Pulling repository: {repo_name}")
            self.command_runner.run(["git", "checkout", "main"], cwd=repo_path)
            result = self.command_runner.run(["git", "pull"], cwd=repo_path)

            logger.info(f"Repository pulled successfully: {repo_name}")
            return PullResult(
                success=True,
                repo_name=repo_name,
                repo_path=str(repo_path),
                message=result["stdout"],
                error=None,
            )

        except (RepositoryNotFoundError, GitCommandError, GitTimeoutError) as e:
            logger.error(f"Pull repository error: {str(e)}")
            return PullResult(
                success=False, repo_name=repo_name, repo_path="", message=None, error=str(e)
            )

    def delete_repository(self, repo_name: str) -> DeleteResult:
        """
        레포지토리 삭제

        Args:
            repo_name: 레포지토리 이름

        Returns:
            삭제 결과
        """
        try:
            # 레포지토리 존재 확인
            self.repo_manager.validate_exists(repo_name)
            repo_path = self.repo_manager.get_repo_path(repo_name)

            # 디렉토리 삭제 (Windows 읽기 전용 파일 처리)
            logger.info(f"Deleting repository: {repo_name}")

            def remove_readonly(func: Any, path: str, exc_info: Any) -> None:
                """읽기 전용 파일 삭제를 위한 에러 핸들러"""
                os.chmod(path, stat.S_IWRITE)
                func(path)

            shutil.rmtree(repo_path, onerror=remove_readonly)

            logger.info(f"Repository deleted successfully: {repo_name}")
            return DeleteResult(
                success=True,
                repo_name=repo_name,
                message=f"Repository {repo_name} deleted successfully",
                error=None,
            )

        except (RepositoryNotFoundError, Exception) as e:
            logger.error(f"Delete repository error: {str(e)}")
            return DeleteResult(success=False, repo_name=repo_name, message=None, error=str(e))
    

    def _format_source_file(self, file_paths: List[str]) -> List[str]:
        """
        파일 경로 리스트의 확장자만 '.json'으로 변경 (경로 유지)
        예: ['src/api/utils.py'] -> ['src/api/utils.json']
        """
        return [str(Path(p).with_suffix(".json")) for p in file_paths]

    def diff_files(self, repo_name: str) -> Dict[str, Any]:
        """
        로컬 저장소의 현재 상태와 'origin/main'을 비교하여 변경된 파일 목록을 포맷에 맞게 반환합니다.

        Args:
            repo_name: 레포지토리 이름

        Returns:
            diff 결과 (성공 여부, 포맷팅된 파일 목록, 메시지/에러)
        """
        try:
            # 1. 레포지토리 경로 확인
            self.repo_manager.validate_exists(repo_name)
            repo_path = self.repo_manager.get_repo_path(repo_name)
            logger.info(f"[{repo_name}] Starting diff check against origin/main.")

            # 2. 원격 저장소의 최신 정보를 가져옴 (fetch)
            logger.info(f"[{repo_name}] Fetching remote repository updates.")
            self.command_runner.run(["git", "fetch"], cwd=repo_path)
            
            # 3. HEAD (현재 로컬)와 'origin/main'을 비교하여 변경된 파일 목록을 가져옴
            logger.info(f"[{repo_name}] Comparing local HEAD with origin/main.")
            diff_result = self.command_runner.run(
                ["git", "diff", "--name-only", "HEAD", "origin/main"],
                cwd=repo_path
            )

            # 4. 결과를 파싱하여 리스트로 변환
            stdout = diff_result["stdout"]
            raw_changed_files = stdout.strip().split('\n') if stdout.strip() else []
            
            # 5. 새로운 포맷팅 메서드를 호출하여 파일명 리스트를 변환
            formatted_files = self._format_source_file(raw_changed_files)
            
            logger.info(f"[{repo_name}] Found and formatted {len(formatted_files)} changed files.")

            return {
                "success": True,
                "files": formatted_files, # 포맷팅된 파일 리스트를 반환
                "message": f"Found {len(formatted_files)} changed files between local and remote."
            }

        except (RepositoryNotFoundError, GitCommandError, GitTimeoutError) as e:
            logger.error(f"Diff files error in {repo_name}: {str(e)}")
            return {
                "success": False,
                "files": [],
                "error": str(e)
            }



#################### history tracker 실행 예시
# if __name__ == "__main__":
#     REPO_PATH = "./RAGIT"  # 분석할 Git 저장소 경로 (clone된 원본 소스코드)
#     FILE_PATH_TO_TRACE = "rag_worker/ask_question/ask_question.py" # 실제 파일 경로
#     # --- 추적 대상 설정 ---
#     NODE_TO_TRACE = "AskQuestion"  # 추적할 클래스 또는 함수 이름
#     NODE_TYPE_TO_TRACE = "class"   # 'function' 또는 'class'

#     # 실행
#     tracker = FunctionHistoryTracker(REPO_PATH)
#     function_history = tracker.trace_history(FILE_PATH_TO_TRACE, NODE_TO_TRACE, NODE_TYPE_TO_TRACE)

#     # 결과 출력
#     if not function_history:
#         print("해당 함수의 변경 이력을 찾지 못했습니다.")
#     else:
#         print(f"'{NODE_TO_TRACE}' 함수의 변경 이력 (총 {len(function_history)}회 변경)")
#         print("="*60)
#         for change in function_history:
#             print(f"Commit: {change.commit_hash} by {change.author} on {change.date}")
#             print(f"Message: {change.commit_message}\n")
#             print("--- Diff ---")
#             print(change.highlighted_diff)
#             print("="*60)