"""
Python 파일 파싱 및 청킹 서비스
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

from .parser import PythonASTParser
from .file_scanner import FileScanner
from .types import ChunkEntry, ParseResult, RepositoryParseResult
from .exceptions import InvalidRepositoryError

logger = logging.getLogger(__name__)


class PythonChunker:
    """Python 파일을 청킹하는 클래스"""

    def __init__(self) -> None:
        """PythonChunker 초기화"""
        self.parser: PythonASTParser = PythonASTParser()

    def chunk_file(self, file_path: Path) -> ParseResult:
        """
        단일 Python 파일을 청킹

        Args:
            file_path: 파싱할 Python 파일 경로

        Returns:
            파싱 결과
        """
        try:
            chunks = self.parser.parse_file(file_path)

            return ParseResult(
                success=True,
                file_path=str(file_path),
                chunks=chunks,
                error=None,
            )

        except Exception as e:
            logger.warning(f"Failed to parse file {file_path}: {str(e)}")
            return ParseResult(
                success=False,
                file_path=str(file_path),
                chunks=[],
                error=str(e),
            )


class RepositoryParserService:
    """레포지토리 전체를 파싱하는 서비스 클래스"""

    def __init__(self, base_repository_path: str = "repository") -> None:
        """
        RepositoryParserService 초기화

        Args:
            base_repository_path: 레포지토리 기본 경로
        """
        # 프로젝트 루트 찾기
        if Path(base_repository_path).is_absolute():
            self.base_path: Path = Path(base_repository_path)
        else:
            current = Path.cwd()
            while current != current.parent:
                if (current / "pyproject.toml").exists():
                    self.base_path = current / base_repository_path
                    break
                current = current.parent
            else:
                self.base_path = Path(base_repository_path).resolve()

        self.file_scanner: FileScanner = FileScanner()
        self.chunker: PythonChunker = PythonChunker()

    def get_repo_path(self, repo_name: str) -> Path:
        """
        레포지토리 경로 반환

        Args:
            repo_name: 레포지토리 이름

        Returns:
            레포지토리 경로
        """
        return self.base_path / repo_name

    def get_output_path(self, repo_name: str) -> Path:
        """
        파싱 결과 출력 경로 반환

        Args:
            repo_name: 레포지토리 이름

        Returns:
            출력 경로
        """
        # parsed_repository/{repo_name}/ 구조
        output_base = self.base_path.parent / "parsed_repository"
        return output_base / repo_name

    def parse_repository(self, repo_name: str, save_json: bool = True) -> RepositoryParseResult:
        """
        레포지토리 전체를 파싱하여 청킹

        Args:
            repo_name: 레포지토리 이름
            save_json: JSON 파일로 저장 여부

        Returns:
            레포지토리 파싱 결과
        """
        try:
            repo_path = self.get_repo_path(repo_name)

            # 레포지토리 존재 확인
            if not repo_path.exists():
                raise InvalidRepositoryError(f"Repository {repo_name} not found at {repo_path}")

            # Python 파일 스캔
            logger.info(f"Scanning repository: {repo_name}")
            python_files = self.file_scanner.scan_repository(repo_path)

            if not python_files:
                logger.warning(f"No Python files found in repository: {repo_name}")
                return RepositoryParseResult(
                    success=True,
                    repo_name=repo_name,
                    repo_path=str(repo_path),
                    total_files=0,
                    parsed_files=0,
                    failed_files=0,
                    total_chunks=0,
                    output_path="",
                    files=[],
                    error=None,
                )

            # 각 파일 파싱
            logger.info(f"Parsing {len(python_files)} Python files...")
            parse_results: List[ParseResult] = []
            total_chunks = 0

            for py_file in python_files:
                result = self.chunker.chunk_file(py_file)
                parse_results.append(result)

                if result["success"]:
                    total_chunks += len(result["chunks"])

                    # JSON 저장
                    if save_json:
                        self._save_chunks_to_json(py_file, result["chunks"], repo_path, repo_name)

            # 통계 계산
            parsed_files = sum(1 for r in parse_results if r["success"])
            failed_files = len(parse_results) - parsed_files

            output_path = str(self.get_output_path(repo_name)) if save_json else ""

            logger.info(
                f"Repository parsing completed: {repo_name} "
                f"(Parsed: {parsed_files}/{len(python_files)}, Chunks: {total_chunks})"
            )

            return RepositoryParseResult(
                success=True,
                repo_name=repo_name,
                repo_path=str(repo_path),
                total_files=len(python_files),
                parsed_files=parsed_files,
                failed_files=failed_files,
                total_chunks=total_chunks,
                output_path=output_path,
                files=parse_results,
                error=None,
            )

        except Exception as e:
            logger.error(f"Repository parsing error: {str(e)}")
            return RepositoryParseResult(
                success=False,
                repo_name=repo_name,
                repo_path=str(self.get_repo_path(repo_name)),
                total_files=0,
                parsed_files=0,
                failed_files=0,
                total_chunks=0,
                output_path="",
                files=[],
                error=str(e),
            )

    def _save_chunks_to_json(
        self, file_path: Path, chunks: List[ChunkEntry], repo_path: Path, repo_name: str
    ) -> None:
        """
        청킹 결과를 JSON 파일로 저장

        Args:
            file_path: 원본 파일 경로
            chunks: 청킹 결과
            repo_path: 레포지토리 경로
            repo_name: 레포지토리 이름
        """
        try:
            # 상대 경로 계산
            relative_path = file_path.relative_to(repo_path)
            relative_path_str = str(relative_path).replace('\\', '/')

            # chunks의 file_path를 상대 경로로 변환
            chunks_with_relative_path = []
            for chunk in chunks:
                chunk_dict = dict(chunk) if isinstance(chunk, dict) else chunk
                chunk_dict['file_path'] = relative_path_str
                chunks_with_relative_path.append(chunk_dict)

            # 출력 경로 생성
            output_base = self.get_output_path(repo_name)
            output_file = output_base / relative_path.with_suffix(".json")

            # 디렉토리 생성
            output_file.parent.mkdir(parents=True, exist_ok=True)

            # JSON 저장
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(chunks_with_relative_path, f, ensure_ascii=False, indent=2)

            logger.debug(f"Saved chunks to {output_file}")

        except Exception as e:
            logger.error(f"Failed to save chunks for {file_path}: {str(e)}")
