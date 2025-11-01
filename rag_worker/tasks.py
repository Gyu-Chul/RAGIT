"""
RAG Worker 태스크 정의
"""

import time
from typing import Dict, Any, Union, Optional, List
from .celery_app import app
from .git_service import GitService
from .git_service.types import CloneResult, StatusResult, PullResult, DeleteResult
from .python_parser import RepositoryParserService
from .python_parser.types import RepositoryParseResult
from .vector_db import VectorDBService
from .vector_db.types import EmbeddingResult, SearchResult
from .vector_db.config import DEFAULT_MODEL_KEY
from .ask_question import AskQuestion, PromptGenerator

# 서비스 인스턴스 생성
git_service = GitService()
parser_service = RepositoryParserService()
# embedding_batch_size=4: 메모리 누적 방지, 배치마다 메모리 해제
vector_db_service = VectorDBService(embedding_batch_size=4)
prompt_service = PromptGenerator()
call_service = AskQuestion()

@app.task
def process_document(document_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    문서 처리 태스크

    Args:
        document_data: 처리할 문서 데이터

    Returns:
        처리 결과
    """
    # TODO: 실제 문서 처리 로직 구현
    return {
        "status": "processed",
        "document_id": document_data.get("id"),
        "message": "Document processed successfully"
    }


@app.task
def search_documents(query: str, limit: int = 10) -> Dict[str, Any]:
    """
    문서 검색 태스크

    Args:
        query: 검색 쿼리
        limit: 결과 제한 수

    Returns:
        검색 결과
    """
    # TODO: 실제 검색 로직 구현
    return {
        "query": query,
        "results": [],
        "total": 0,
        "message": "Search completed"
    }


@app.task
def health_check() -> Dict[str, str]:
    """
    헬스 체크 태스크

    Returns:
        상태 정보
    """
    return {"status": "healthy", "service": "rag_worker"}


# 테스트용 기본 태스크
@app.task
def add(x: Union[int, float], y: Union[int, float]) -> Union[int, float]:
    """두 숫자를 더하는 작업"""
    result = x + y
    return result


@app.task
def reverse_string(text: str) -> str:
    """문자열을 뒤집는 작업"""
    result = text[::-1]
    return result


@app.task
def wait_seconds(second: int) -> int:
    """지정된 시간만큼 대기하는 작업"""
    time.sleep(second)
    return second


# Git 관련 작업
@app.task
def git_clone(git_url: str, repo_name: Optional[str] = None) -> CloneResult:
    """
    Git 레포지토리 클론 작업

    Args:
        git_url: Git 레포지토리 URL
        repo_name: 저장할 레포지토리 이름 (선택)

    Returns:
        클론 결과
    """
    return git_service.clone_repository(git_url, repo_name)


@app.task
def git_check_status(repo_name: str) -> StatusResult:
    """
    레포지토리 커밋 상태 확인 작업

    Args:
        repo_name: 레포지토리 이름

    Returns:
        커밋 상태 정보
    """
    return git_service.check_commit_status(repo_name)


@app.task
def git_pull(repo_name: str) -> PullResult:
    """
    레포지토리 pull 작업

    Args:
        repo_name: 레포지토리 이름

    Returns:
        Pull 결과
    """
    return git_service.pull_repository(repo_name)


@app.task
def git_delete(repo_name: str) -> DeleteResult:
    """
    레포지토리 삭제 작업

    Args:
        repo_name: 레포지토리 이름

    Returns:
        삭제 결과
    """
    return git_service.delete_repository(repo_name)


# Python 파싱 관련 작업
@app.task
def parse_repository(repo_name: str, save_json: bool = True) -> RepositoryParseResult:
    """
    레포지토리 내 모든 Python 파일을 파싱하여 청킹

    Args:
        repo_name: 레포지토리 이름
        save_json: JSON 파일로 저장 여부 (기본값: True)

    Returns:
        레포지토리 파싱 결과
    """
    return parser_service.parse_repository(repo_name, save_json)


# Vector DB 관련 작업
@app.task
def embed_documents(
    json_path: str, collection_name: str, model_key: str = DEFAULT_MODEL_KEY
) -> EmbeddingResult:
    """
    JSON 파일의 문서를 임베딩하여 Milvus 컬렉션에 저장

    Args:
        json_path: JSON 파일 경로
        collection_name: 저장할 컬렉션 이름
        model_key: 사용할 임베딩 모델 키 (기본값: DEFAULT_MODEL_KEY)

    Returns:
        임베딩 결과
    """
    return vector_db_service.embed_documents(json_path, collection_name, model_key)


@app.task
def embed_repository(
    repo_name: str, collection_name: str, model_key: str = DEFAULT_MODEL_KEY
) -> EmbeddingResult:
    """
    파싱된 레포지토리 전체를 임베딩하여 Milvus 컬렉션에 저장

    Args:
        repo_name: 레포지토리 이름 (parsed_repository/{repo_name}/ 의 모든 JSON 수집)
        collection_name: 저장할 컬렉션 이름
        model_key: 사용할 임베딩 모델 키 (기본값: DEFAULT_MODEL_KEY)

    Returns:
        임베딩 결과
    """
    return vector_db_service.embed_repository(repo_name, collection_name, model_key)


@app.task
def search_vectors(
    query: str,
    collection_name: str,
    model_key: str = DEFAULT_MODEL_KEY,
    top_k: int = 5,
    filter_expr: Optional[str] = None,
) -> SearchResult:
    """
    하이브리드 검색 수행 (밀집 + 희소 벡터)

    Args:
        query: 검색 쿼리
        collection_name: 검색할 컬렉션 이름
        model_key: 사용할 임베딩 모델 키 (기본값: DEFAULT_MODEL_KEY)
        top_k: 반환할 결과 개수 (기본값: 5)
        filter_expr: 필터 표현식 (선택)

    Returns:
        검색 결과
    """
    return vector_db_service.search(query, collection_name, model_key, top_k, filter_expr)


# Repository 처리 통합 작업
@app.task(name='rag_worker.tasks.process_repository_pipeline')
def process_repository_pipeline(
    repo_id: str,
    git_url: str,
    repo_name: str,
    model_key: str = DEFAULT_MODEL_KEY
) -> Dict[str, Any]:
    """
    Repository 전체 처리 파이프라인
    1. Git clone
    2. Python 파싱 및 청킹
    3. Vector DB 임베딩

    Args:
        repo_id: Repository ID (UUID)
        git_url: Git repository URL
        repo_name: Repository 이름
        model_key: 임베딩 모델 키

    Returns:
        처리 결과
    """
    import os
    import logging
    from pathlib import Path
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    logger = logging.getLogger(__name__)

    # DATABASE_URL 설정
    env_local_path = Path(__file__).parent.parent / '.env.local'
    logger.info(f"🔍 Looking for .env.local at: {env_local_path}")
    logger.info(f"📁 .env.local exists: {env_local_path.exists()}")

    if env_local_path.exists():
        # .env.local 파일을 직접 파싱
        DATABASE_URL = None
        with open(env_local_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line.startswith('DATABASE_URL='):
                    DATABASE_URL = line.split('=', 1)[1]
                    break

        if DATABASE_URL:
            os.environ['DATABASE_URL'] = DATABASE_URL
            logger.info(f"✅ Set DATABASE_URL from .env.local: {DATABASE_URL}")
        else:
            DATABASE_URL = 'postgresql://postgres:postgres@localhost:5432/ragit'
            os.environ['DATABASE_URL'] = DATABASE_URL
            logger.warning(f"⚠️ DATABASE_URL not found in .env.local, using default: {DATABASE_URL}")
    else:
        DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/ragit')
        logger.info(f"⚠️ .env.local not found, using environment: {DATABASE_URL}")

    # DB helper import
    from .db_helper import RepositoryDBHelper

    # 데이터베이스 세션 생성
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    logger.info(f"🔗 Database connection created successfully")

    try:
        # 1. 상태를 'syncing'으로 업데이트
        RepositoryDBHelper.update_repository_status(db, repo_id, "syncing", "pending")

        # 2. Git Clone
        clone_result = git_service.clone_repository(git_url, repo_name)
        if not clone_result['success']:
            error_msg = f"Git clone failed: {clone_result['message']}"
            RepositoryDBHelper.update_repository_status(db, repo_id, "error", "error", error_msg)
            return {
                "success": False,
                "error": error_msg,
                "step": "clone"
            }

        # 3. Python 파일 파싱 및 청킹
        parse_result = parser_service.parse_repository(repo_name, save_json=True)
        if not parse_result['success']:
            error_msg = f"Parsing failed: {parse_result['message']}"
            RepositoryDBHelper.update_repository_status(db, repo_id, "error", "error", error_msg)
            return {
                "success": False,
                "error": error_msg,
                "step": "parse"
            }

        # 파일 개수 업데이트
        file_count = parse_result['total_files']
        RepositoryDBHelper.update_file_count(db, repo_id, file_count)

        # 4. Vector DB 상태를 'syncing'으로 업데이트
        RepositoryDBHelper.update_repository_status(db, repo_id, "syncing", "syncing")

        # 5. Vector DB 임베딩
        collection_name = f"repo_{repo_id.replace('-', '_')}"
        embed_result = vector_db_service.embed_repository(repo_name, collection_name, model_key)

        if not embed_result['success']:
            error_msg = f"Embedding failed: {embed_result['message']}"
            RepositoryDBHelper.update_repository_status(db, repo_id, "active", "error", error_msg)
            return {
                "success": False,
                "error": error_msg,
                "step": "embed",
                "file_count": file_count
            }

        # 6. Collections count 증가
        RepositoryDBHelper.increment_collections_count(db, repo_id)

        # 7. 최종 상태를 'active'로 업데이트
        RepositoryDBHelper.update_repository_status(db, repo_id, "active", "active")

        return {
            "success": True,
            "repo_id": repo_id,
            "repo_name": repo_name,
            "file_count": file_count,
            "total_chunks": parse_result['total_chunks'],
            "collection_name": collection_name,
            "embedded_count": embed_result['inserted_count'],
            "message": "Repository processed successfully"
        }

    except Exception as e:
        # 오류 발생 시 상태 업데이트
        error_msg = f"Unexpected error: {str(e)}"
        RepositoryDBHelper.update_repository_status(db, repo_id, "error", "error", error_msg)
        return {
            "success": False,
            "error": error_msg,
            "step": "unknown"
        }
    finally:
        db.close()


# Chat RAG 작업
@app.task(name='rag_worker.tasks.chat_query')
def chat_query(
    chat_room_id: str,
    repo_id: str,
    user_message: str,
    top_k: int = 5
) -> Dict[str, Any]:
    """
    사용자 메시지에 대한 RAG 기반 응답 생성

    Args:
        chat_room_id: 채팅방 ID
        repo_id: 레포지토리 ID
        user_message: 사용자 메시지
        top_k: 검색할 코드 조각 개수

    Returns:
        응답 결과
    """
    import os
    import logging
    import json
    from pathlib import Path
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    logger = logging.getLogger(__name__)

    # DATABASE_URL 설정 (process_repository_pipeline과 동일한 로직)
    env_local_path = Path(__file__).parent.parent / '.env.local'

    if env_local_path.exists():
        DATABASE_URL = None
        with open(env_local_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line.startswith('DATABASE_URL='):
                    DATABASE_URL = line.split('=', 1)[1]
                    break

        if DATABASE_URL:
            os.environ['DATABASE_URL'] = DATABASE_URL
            logger.info(f"✅ Set DATABASE_URL from .env.local")
        else:
            DATABASE_URL = 'postgresql://postgres:postgres@localhost:5432/ragit'
            os.environ['DATABASE_URL'] = DATABASE_URL
            logger.warning(f"⚠️ DATABASE_URL not found in .env.local, using default")
    else:
        DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/ragit')
        logger.info(f"⚠️ .env.local not found, using environment")

    # DB helper import
    from .db_helper import ChatMessageDBHelper

    # 데이터베이스 세션 생성
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    logger.info(f"🔗 Database connection created successfully")

    try:
        # 1. Vector DB 검색
        collection_name = f"repo_{repo_id.replace('-', '_')}"
        logger.info(f"🔍 Searching vectors in collection: {collection_name}")
        logger.info(f"📝 User query: {user_message}")

        search_result = vector_db_service.search(
            query=user_message,
            collection_name=collection_name,
            model_key=DEFAULT_MODEL_KEY,
            top_k=top_k
        )

        if not search_result['success']:
            logger.error(f"❌ Vector search failed: {search_result.get('error')}")
            # 검색 실패시에도 기본 응답 생성
            bot_response = "죄송합니다. 코드 검색 중 오류가 발생했습니다. 나중에 다시 시도해주세요."
            sources = None
        else:
            logger.info(f"✅ Found {search_result['total_results']} relevant code snippets")

            # 2. 검색 결과를 바탕으로 LLM 응답 생성
            retrieved_codes = search_result['results'][:top_k]

            if retrieved_codes:
                try:
                    # 디버깅: 검색 결과 확인
                    logger.info(f"🔍 Retrieved codes sample:")
                    for i, code in enumerate(retrieved_codes[:2], 1):
                        logger.info(f"  [{i}] {code.get('name')} ({code.get('file_path')})")
                        logger.info(f"      Code length: {len(code.get('code', ''))} chars")
                        logger.info(f"      Has code: {'code' in code}")
                        logger.info(f"      Code preview: {code.get('code', '')[:100]}")

                    # 2-1. PromptGenerator로 프롬프트 생성
                    logger.info(f"📝 Generating prompt from {len(retrieved_codes)} code snippets")
                    prompt = prompt_service.create(docs=retrieved_codes, query=user_message)

                    # 디버깅: 생성된 프롬프트 확인
                    logger.info(f"📄 Generated prompt length: {len(prompt)} chars")
                    logger.info(f"📄 Prompt preview (first 500 chars):\n{prompt[:500]}")

                    # 2-2. AskQuestion으로 LLM 응답 받기
                    logger.info(f"🤖 Calling LLM API...")
                    bot_response = call_service.ask_question(
                        prompt=prompt,
                        use_stream=False,
                        model="gpt-4o-mini",
                        temperature=0.1,
                        max_tokens=2048
                    )
                    logger.info(f"✅ LLM response received")
                    logger.info(f"📝 Response preview: {bot_response[:200]}")

                    # sources를 JSON 문자열로 저장
                    sources = json.dumps([
                        f"{code['file_path']}:{code['start_line']}-{code['end_line']}"
                        for code in retrieved_codes
                    ], ensure_ascii=False)

                except Exception as llm_error:
                    logger.error(f"❌ LLM API call failed: {str(llm_error)}")

                    # API KEY 없음 여부 체크
                    is_api_key_missing = "OPENAI_API_KEY" in str(llm_error)

                    # LLM 호출 실패시 RAG 검색 결과 기반 응답 생성
                    code_summary = []
                    for i, code in enumerate(retrieved_codes, 1):
                        file_info = code.get('file_path', 'Unknown')
                        name_info = code.get('name', 'N/A')
                        if name_info:
                            code_summary.append(f"{i}. **{name_info}** (`{file_info}:{code.get('start_line', 0)}-{code.get('end_line', 0)}`)")
                        else:
                            code_summary.append(f"{i}. `{file_info}:{code.get('start_line', 0)}-{code.get('end_line', 0)}`")

                    if is_api_key_missing:
                        error_msg = "⚠️ **OPENAI_API_KEY가 설정되지 않아 AI 분석을 수행할 수 없습니다.**"
                        instruction_msg = "환경 변수에 OPENAI_API_KEY를 설정하면 AI 기반 코드 분석 결과를 받을 수 있습니다."
                    else:
                        error_msg = "⚠️ **LLM 분석 중 오류가 발생했습니다.**"
                        instruction_msg = f"오류 내용: {str(llm_error)[:100]}"

                    bot_response = f"""질문해주신 내용과 관련된 코드를 찾았습니다.

**🔍 RAG 검색 결과 ({len(retrieved_codes)}개 발견):**

{chr(10).join(code_summary)}

---

{error_msg}

{instruction_msg}

검색된 코드 조각들을 참고하시면 답변을 얻으실 수 있을 것입니다."""

                    sources = json.dumps([
                        f"{code['file_path']}:{code['start_line']}-{code['end_line']}"
                        for code in retrieved_codes
                    ], ensure_ascii=False)
            else:
                bot_response = "질문하신 내용과 관련된 코드를 찾지 못했습니다. 다른 방식으로 질문해주시겠어요?"
                sources = None

        # 3. Bot 메시지를 DB에 저장
        logger.info(f"💾 Saving bot response to database")

        bot_message = ChatMessageDBHelper.create_bot_message(
            db=db,
            chat_room_id=chat_room_id,
            content=bot_response,
            sources=sources
        )

        logger.info(f"✅ Bot message saved with ID: {bot_message['id']}")

        return {
            "success": True,
            "chat_room_id": chat_room_id,
            "bot_message_id": bot_message['id'],
            "retrieved_count": search_result.get('total_results', 0) if search_result['success'] else 0,
            "message": "Chat query processed successfully"
        }

    except Exception as e:
        logger.error(f"❌ Error processing chat query: {str(e)}", exc_info=True)

        # 에러 발생 시에도 에러 메시지를 bot 응답으로 저장
        try:
            ChatMessageDBHelper.create_bot_message(
                db=db,
                chat_room_id=chat_room_id,
                content=f"죄송합니다. 응답 생성 중 오류가 발생했습니다: {str(e)}",
                sources=None
            )
        except:
            pass

        return {
            "success": False,
            "error": str(e),
            "chat_room_id": chat_room_id
        }

    finally:
        db.close()


### ragit_sdk/tests/create_prompt.py
@app.task
def create_prompt(
    docs: List[SearchResult],
    query: str,
) -> str:
    """
    검색 결과를 이용한 프롬프트 생성

    Args:
        SearchResult: 검색 결과
        query: 검색 쿼리

    Returns:
        생성된 프롬프트
    """
    return prompt_service.create(docs, query)

### ragit_sdk/tests/ask_question.py
@app.task
def call_llm(
        prompt: str, 
        use_stream: Optional[bool] = False, 
        model: Optional[str] = "gpt-3.5-turbo", 
        temperature: Optional[float] = 0.1, 
        max_tokens: Optional[int] = 1024,
) -> str:
    """
    검색 결과를 이용한 프롬프트 생성

    Args:
        SearchResult: 검색 결과
        query: 검색 쿼리

    Returns:
        생성된 프롬프트
    """
    return call_service.ask_question(prompt=prompt, use_stream=use_stream, model=model, temperature=temperature, max_tokens=max_tokens)



### ragit_sdk/tests/diff_file.py
@app.task(name='rag_worker.tasks.run_git_diff')
def run_git_diff(repo_name: str):
    """
    GitService의 diff_files 메서드를 테스트
    """
    return git_service.diff_files(repo_name)


### ragit_sdk/tests/embedding.py
@app.task(name='rag_worker.tasks.parse_and_embed_repository')
def parse_and_embed_repository(repo_name: str, collection_name: str, model_key: str, save_json: bool = True):
    """
    레포지토리를 파싱하고, 그 결과를 즉시 Vector DB에 임베딩하는 통합 Test용 Celery Task
    """
    # --- 1단계: 코드 파싱 및 청킹 ---
    parse_result = parser_service.parse_repository(
        repo_name=repo_name,
        save_json=save_json
    )

    if not parse_result.get('success'):
        # 실패 시 에러 정보를 포함하여 즉시 반환
        return {
            "success": False,
            "step": "parse",
            "error": parse_result.get('message'),
            "repo_name": repo_name
        }

    # --- 2단계: Vector DB 임베딩 ---
    embed_result = vector_db_service.embed_repository(
        repo_name=repo_name,
        collection_name=collection_name,
        model_key=model_key
    )

    if not embed_result.get('success'):
        return {
            "success": False,
            "step": "embed",
            "error": embed_result.get('message'),
            "repo_name": repo_name
        }

    # 최종 성공 결과 반환
    return {
        "success": True,
        "repo_name": repo_name,
        "collection_name": collection_name,
        "parsed_files": parse_result.get('total_files'),
        "total_chunks": embed_result.get('total_chunks'),
        "embedded_count": embed_result.get('inserted_count'),
        "message": "Repository parsed and embedded successfully."
    }


# repository 최신 동기화 통합 작업 (update 기능)
@app.task(name='rag_worker.tasks.update_repository_pipeline')
def update_repository_pipeline(
    repo_id: str,
    repo_name: str,
    collection_name: str,
    save_json: bool = True,
    model_key: str = DEFAULT_MODEL_KEY,
) -> Dict[str, Any]:
    """
    Repository 업데이트 최적화 파이프라인
    1. Local vs Remote diff 찾기
    2. Git Pull 로 최신 코드 받기
    3. Vector DB에서 변경된 파일의 기존 데이터 삭제
    4. 레포지토리 전체 재-파싱하여 JSON 파일 최신화
    5. 변경된 JSON 파일만 다시 임베딩
    
    Args:
        repo_id: Repository ID (UUID)
        repo_name: Repository 이름
        collection_name: Vector DB 컬렉션 이름
        save_json: JSON 파일로 저장 여부
        model_key: 임베딩 모델 키

    Returns:
        처리 결과
    """
    import os
    import logging
    from pathlib import Path
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    logger = logging.getLogger(__name__)


    env_local_path = Path(__file__).parent.parent / '.env.local'
    if env_local_path.exists():
        DATABASE_URL = None
        with open(env_local_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line.startswith('DATABASE_URL='):
                    DATABASE_URL = line.split('=', 1)[1]
                    break
        if DATABASE_URL:
            os.environ['DATABASE_URL'] = DATABASE_URL
        else:
            DATABASE_URL = 'postgresql://postgres:postgres@localhost:5432/ragit'
            os.environ['DATABASE_URL'] = DATABASE_URL
    else:
        DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/ragit')
    
    from backend.services.repository_service import RepositoryService

    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    logger.info(f"🔗 [{repo_name}] Database connection created for update pipeline.")

    try:
        # 1. 상태를 'updating'으로 업데이트
        RepositoryService.update_repository_status(db, repo_id, "updating", "pending")

        # 2. PULL 하기 전, 먼저 변경될 파일 목록(diff) 확보
        logger.info(f"[{repo_name}] Step 1: Finding diff...")
        diff_result = git_service.diff_files(repo_name)
        if not diff_result.get('success'):
            RepositoryService.update_repository_status(db, repo_id, "active", "error")
            return {"success": False, "error": f"Failed to get diff: {diff_result.get('error')}", "step": "diff"}
        
        files_to_update = diff_result.get("files", [])
        logger.info(f"[{repo_name}] Found {len(files_to_update)} files to update.")

        # 3. Git Pull 로 로컬 코드 최신화
        logger.info(f"[{repo_name}] Step 2: Pulling latest changes.")
        pull_result = git_service.pull_repository(repo_name)
        if not pull_result.get('success'):
            RepositoryService.update_repository_status(db, repo_id, "error", "error")
            return {"success": False, "error": f"Git pull failed: {pull_result.get('error')}", "step": "pull"}
        
        # 4. Vector DB 상태를 'updating'으로 변경
        RepositoryService.update_repository_status(db, repo_id, "updating", "updating")

        # 5. 확보한 목록으로 Vector DB의 기존 엔티티 삭제
        deleted_count = 0
        if files_to_update:
            num_files_to_delete = len(files_to_update)
            logger.info(f"[{repo_name}] Step 3: Deleting old entities...")
            delete_result = vector_db_service.delete_entities(
                collection_name=collection_name, 
                source_files=files_to_update
            )
            if not delete_result.get('success'):
                RepositoryService.update_repository_status(db, repo_id, "active", "error")
                return {"success": False, "error": f"Failed to delete entities: {delete_result.get('error')}", "step": "delete_entities"}
            deleted_count = num_files_to_delete
            logger.info(f"[{repo_name}] Deleted {deleted_count} old entities.")
        else:
            logger.info(f"[{repo_name}] Step 3: No entities to delete, skipping.")

        # 6. 최신 코드로 레포지토리 전체를 다시 파싱 (JSON 파일들의 내용을 최신으로 업데이트하기 위해 필수)
        logger.info(f"[{repo_name}] Step 4: Re-parsing entire repository to update JSON files.")
        parse_result = parser_service.parse_repository(repo_name, save_json)
        if not parse_result.get('success'):
            RepositoryService.update_repository_status(db, repo_id, "error", "error")
            return {"success": False, "error": f"Parsing failed: {parse_result.get('message')}", "step": "parse"}
        
        file_count = parse_result.get('total_files', 0)
        RepositoryService.update_file_count(db, repo_id, file_count)

        # 7. 변경된 파일 목록(files_to_update)에 해당하는 JSON 파일만 다시 임베딩
        logger.info(f"[{repo_name}] Step 5: Re-embedding only changed files...")
        total_embedded_count = 0
        if files_to_update:
            # 파싱된 JSON 파일이 저장된 기본 경로 (parser_service의 경로 구조에 맞춰야 함)
            parsed_repo_path = Path(f"parsed_repository/{repo_name}")

            for json_filename in files_to_update:
                json_file_path = parsed_repo_path / json_filename
                
                if not json_file_path.exists():
                    logger.warning(f"[{repo_name}] Parsed file {json_file_path} not found. It might have been deleted. Skipping embedding.")
                    continue

                embed_result = vector_db_service.embed_documents(
                    json_path=str(json_file_path),
                    collection_name=collection_name,
                    model_key=model_key
                )
                if not embed_result.get('success'):
                    RepositoryService.update_repository_status(db, repo_id, "active", "error")
                    return {"success": False, "error": f"Embedding failed for {json_filename}", "step": "embed"}
                
                total_embedded_count += embed_result.get('inserted_count', 0)
            
            logger.info(f"[{repo_name}] Re-embedded {total_embedded_count} new chunks from {len(files_to_update)} files.")
        else:
            logger.info(f"[{repo_name}] Step 5: No files to re-embed, skipping.")


        # 8. 최종 상태를 'active'로 업데이트
        RepositoryService.update_repository_status(db, repo_id, "active", "active")
        logger.info(f"[{repo_name}] Update pipeline finished successfully.")

        return {
            "success": True,
            "repo_id": repo_id,
            "repo_name": repo_name,
            "file_count": file_count,
            "deleted_count": deleted_count,
            "embedded_count": total_embedded_count,
            "message": "Repository updated successfully"
        }

    except Exception as e:
        logger.error(f"[{repo_name}] An unexpected error occurred in update pipeline: {e}", exc_info=True)
        # 오류 발생 시 상태 업데이트
        RepositoryService.update_repository_status(db, repo_id, "error", "error")
        return {
            "success": False,
            "error": str(e),
            "step": "unknown"
        }
    finally:
        db.close()
        logger.info(f"[{repo_name}] Database connection closed for update pipeline.")