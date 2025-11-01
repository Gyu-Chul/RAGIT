import os
from typing import List, Optional

import git
from tree_sitter import Parser
from tree_sitter_languages import get_parser, get_language
import diff_match_patch as dmp_module

from .types import CommitChange

class GitHistoryManager:
    """Git 저장소와의 상호작용을 관리합니다."""
    def __init__(self, repo_path: str):
        if not os.path.isdir(repo_path):
            raise FileNotFoundError(f"저장소 경로를 찾을 수 없습니다: {repo_path}")
        self.repo = git.Repo(repo_path)

    def get_file_history(self, file_path: str) -> List[git.Commit]:
        """특정 파일에 대한 모든 커밋 기록을 최신순으로 반환합니다."""
        return list(self.repo.iter_commits(paths=file_path))

    def get_file_content_at_commit(self, commit_hash: str, file_path: str) -> Optional[str]:
        """특정 커밋 시점의 파일 내용을 문자열로 반환합니다."""
        import logging
        logger = logging.getLogger(__name__)

        try:
            commit = self.repo.commit(commit_hash)
            blob = commit.tree / file_path
            raw_data = blob.data_stream.read()

            # 여러 인코딩 시도
            encodings = ['utf-8', 'cp949', 'euc-kr', 'latin-1']
            for encoding in encodings:
                try:
                    content = raw_data.decode(encoding)
                    logger.debug(f"   📄 {commit_hash[:7]}:{file_path} → {len(content)} bytes ({encoding})")
                    return content
                except (UnicodeDecodeError, LookupError):
                    continue

            # 모든 인코딩 실패 시 오류 무시하고 디코딩
            content = raw_data.decode('utf-8', errors='replace')
            logger.debug(f"   📄 {commit_hash[:7]}:{file_path} → {len(content)} bytes (utf-8 with errors replaced)")
            return content

        except (KeyError, ValueError) as e:
            logger.debug(f"   ❌ {commit_hash[:7]}:{file_path} → Error: {e}")
            return None
        except Exception as e:
            logger.warning(f"   ⚠️  {commit_hash[:7]}:{file_path} → Unexpected error: {e}")
            return None


class CodeParser:
    """tree-sitter를 사용하여 코드 구조를 분석합니다."""
    def __init__(self, language_name='python'):
        self.parser = get_parser(language_name)
        self.language = get_language(language_name)

        # 쿼리들을 딕셔너리로 관리하여 확장성 확보
        self.QUERIES = {
            'function': """
                (function_definition
                  name: (identifier) @node.name
                  (#eq? @node.name "{}")) @node.def
            """,
            'async_function': """
                (function_definition
                  name: (identifier) @node.name
                  (#eq? @node.name "{}")) @node.def
            """,
            'class': """
                (class_definition
                  name: (identifier) @node.name
                  (#eq? @node.name "{}")) @node.def
            """,
            'module': """
                (module) @node.def
            """,
            'script': """
                (module) @node.def
            """
        }

    def find_node_body(self, source_code: str, node_name: str, node_type: str = 'function', start_line: Optional[int] = None, end_line: Optional[int] = None) -> Optional[str]:
        """소스코드에서 특정 이름과 유형(함수/클래스)의 노드 본문을 추출합니다.

        Args:
            source_code: 소스 코드
            node_name: 노드 이름 (module/script의 경우 무시됨)
            node_type: 노드 타입
            start_line: 시작 라인 (module/script의 경우 사용)
            end_line: 종료 라인 (module/script의 경우 사용)
        """
        if node_type not in self.QUERIES:
            print(f"오류: 지원하지 않는 노드 유형입니다: {node_type}")
            return None

        # module과 script 타입은 라인 범위 기반으로 처리
        if node_type in ['module', 'script']:
            if start_line is not None and end_line is not None:
                lines = source_code.splitlines(keepends=True)
                # 라인 번호는 1-based이므로 변환
                return ''.join(lines[start_line - 1:end_line]).rstrip('\n')
            else:
                # 라인 범위가 없으면 전체 파일 반환
                return source_code.rstrip('\n')

        # 노드 유형에 맞는 쿼리를 선택하여 포맷팅
        query_str = self.QUERIES[node_type].format(node_name)

        tree = self.parser.parse(bytes(source_code, "utf8"))
        query = self.language.query(query_str)
        captures = query.captures(tree.root_node)

        for node, _ in captures:
            if node.type in ['function_definition', 'class_definition']:
                return node.text.decode('utf-8')
        return None
    

class DiffGenerator:
    """두 텍스트 간의 차이점을 생성하고 시각화합니다."""
    def __init__(self):
        self.dmp = dmp_module.diff_match_patch()

    def generate_highlighted_diff(self, text1: str, text2: str) -> str:
        """두 코드 블럭의 차이점을 줄 단위로 비교하여 +,- 로 표현합니다."""

        # 1. 두 텍스트를 줄 단위로 변환하고 고유 문자로 매핑합니다.
        a = self.dmp.diff_linesToChars(text1, text2)
        line_text1, line_text2, line_array = a

        # 2. 고유 문자를 기준으로 Diff를 수행합니다.
        diffs = self.dmp.diff_main(line_text1, line_text2, False)

        # 3. Diff 결과를 다시 원래의 줄 텍스트로 복원합니다.
        self.dmp.diff_charsToLines(diffs, line_array)

        # 4. 결과 시각화
        result = []
        for op, data in diffs:
            lines = data.splitlines(True)
            for line in lines:
                if not line.strip(): continue
                if op == self.dmp.DIFF_INSERT:
                    result.append(f"+ {line}")
                elif op == self.dmp.DIFF_DELETE:
                    result.append(f"- {line}")
                elif op == self.dmp.DIFF_EQUAL:
                    result.append(f"  {line}")
        return "".join(result)


class FunctionHistoryTracker:
    """함수의 변경 이력을 추적하는 메인 클래스입니다."""
    def __init__(self, repo_path: str):
        self.git_manager = GitHistoryManager(repo_path)
        self.parser = CodeParser('python')
        self.diff_generator = DiffGenerator()

    def trace_history(self, file_path: str, node_name: Optional[str] = None, node_type: Optional[str] = None, start_line: Optional[int] = None, end_line: Optional[int] = None) -> List[CommitChange]:
        """주어진 파일 또는 함수/클래스/모듈의 변경 이력을 추적하여 CommitChange 리스트로 반환합니다.

        Args:
            file_path: 파일 경로
            node_name: 노드 이름 (None이면 전체 파일 추적)
            node_type: 노드 타입 (None이면 전체 파일 추적)
            start_line: 시작 라인 (module/script의 경우 사용)
            end_line: 종료 라인 (module/script의 경우 사용)
        """
        import logging
        logger = logging.getLogger(__name__)

        commits = self.git_manager.get_file_history(file_path)
        if not commits:
            return []

        logger.info(f"📊 Found {len(commits)} commits for {file_path}")
        for idx, commit in enumerate(commits):
            logger.info(f"  [{idx}] {commit.hexsha[:7]} - {commit.message.strip()[:50]}")

        history = []
        is_full_file = node_type is None or node_name is None

        # 최신 커밋부터 부모 커밋과 비교하며 역순으로 진행
        for i in range(len(commits) - 1):
            current_commit = commits[i]
            parent_commit = commits[i+1]

            current_content = self.git_manager.get_file_content_at_commit(current_commit.hexsha, file_path)
            parent_content = self.git_manager.get_file_content_at_commit(parent_commit.hexsha, file_path)

            logger.info(f"🔍 Comparing [{i}] {current_commit.hexsha[:7]} vs [{i+1}] {parent_commit.hexsha[:7]}")
            logger.info(f"   Current content: {'EXISTS (' + str(len(current_content)) + ' bytes)' if current_content is not None else 'NONE'}")
            logger.info(f"   Parent content: {'EXISTS (' + str(len(parent_content)) + ' bytes)' if parent_content is not None else 'NONE'}")

            # 전체 파일 모드
            if is_full_file:
                code_after = current_content
                code_before = parent_content
            # 특정 노드 추적 모드
            else:
                code_after = self.parser.find_node_body(current_content, node_name, node_type, start_line, end_line) if current_content is not None else None
                code_before = self.parser.find_node_body(parent_content, node_name, node_type, start_line, end_line) if parent_content is not None else None

            # 둘 다 None이면 건너뜀
            if code_after is None and code_before is None:
                logger.info(f"   ⏭️  Skipped (both None)")
                continue

            if code_after != code_before:
                logger.info(f"   ✅ Change detected, adding to history")
                diff = self.diff_generator.generate_highlighted_diff(code_before or "", code_after or "")

                change = CommitChange(
                    commit_hash=current_commit.hexsha[:7],
                    commit_message=current_commit.message.strip(),
                    author=current_commit.author.name,
                    date=current_commit.committed_datetime.strftime("%Y-%m-%d %H:%M:%S"),
                    code_before=code_before,
                    code_after=code_after,
                    highlighted_diff=diff
                )
                history.append(change)
            else:
                logger.info(f"   ⏭️  Skipped (no change)")

        # 최초 커밋 처리
        first_commit = commits[-1]
        logger.info(f"🔍 Processing first commit: {first_commit.hexsha[:7]}")
        first_content = self.git_manager.get_file_content_at_commit(first_commit.hexsha, file_path)
        logger.info(f"   First commit content: {'EXISTS (' + str(len(first_content)) + ' bytes)' if first_content is not None else 'NONE'}")

        if is_full_file:
            first_code = first_content
        else:
            first_code = self.parser.find_node_body(first_content, node_name, node_type, start_line, end_line) if first_content is not None else None

        if first_code is not None and not any(c.code_before == first_code for c in history):
             logger.info(f"   ✅ Adding first commit to history (file creation)")
             diff = self.diff_generator.generate_highlighted_diff("", first_code)
             change = CommitChange(
                    commit_hash=first_commit.hexsha[:7],
                    commit_message=first_commit.message.strip(),
                    author=first_commit.author.name,
                    date=first_commit.committed_datetime.strftime("%Y-%m-%d %H:%M:%S"),
                    code_before=None, # 최초 생성
                    code_after=first_code,
                    highlighted_diff=diff
                )
             history.append(change)
        else:
             logger.info(f"   ⏭️  Skipped first commit (already in history or no content)")

        logger.info(f"✅ Total history entries: {len(history)}")
        return history # 최신 변경이 위로 오도록 순서 유지

