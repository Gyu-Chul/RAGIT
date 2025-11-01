"""
RAG Worker 검색 기능만 테스트

사용법:
1. Redis 서버 실행 확인
2. Celery Worker 실행 확인
3. python -m ragit_sdk.tests.create_prompt 실행
"""

from celery import Celery
from celery.result import AsyncResult
from typing import List, Optional, TypedDict


class SearchResultItem(TypedDict):
    """검색 결과 아이템"""

    code: str
    file_path: str
    name: str
    start_line: int
    end_line: int
    type: str
    _source_file: str
    score: Optional[float]


# Celery 앱 설정
app = Celery(
    'test_search',
    broker='redis://localhost:6379/0',
    backend='redis://localhost:6379/0'
)


def test_create_prompt() -> None:
    """create prompt 테스트"""
    print("\n" + "="*60)
    print("Create Prompt Test")
    print("="*60)

    search_results: List[SearchResultItem] = [
        {
            "code": "def calculate_similarity(vec1, vec2):\n    \"\"\"두 벡터 간의 코사인 유사도를 계산합니다.\"\"\"\n    return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))",
            "file_path": "app/utils/vector_utils.py",
            "name": "calculate_similarity",
            "start_line": 25,
            "end_line": 28,
            "type": "function",
            "_source_file": "/usr/src/app/utils/vector_utils.py",
            "score": 0.912345
        },
        {
            "code": "class UserManager:\n    def __init__(self, db_session):\n        self.session = db_session\n\n    def get_user(self, user_id: int):\n        return self.session.query(User).filter_by(id=user_id).first()",
            "file_path": "app/models/user.py",
            "name": "UserManager",
            "start_line": 12,
            "end_line": 18,
            "type": "class",
            "_source_file": "/usr/src/app/models/user.py",
            "score": 0.8876
        },
        {
            "code": "if __name__ == \"__main__\":\n    parser = argparse.ArgumentParser()\n    parser.add_argument(\"--config\", default=\"config.yaml\")\n    args = parser.parse_args()\n    main(args.config)",
            "file_path": "main.py",
            "name": "__main__",
            "start_line": 102,
            "end_line": 106,
            "type": "script",
            "_source_file": "/usr/src/main.py",
            "score": 0.7543
        },
        {
            "code": "# 프로젝트 전역에서 사용되는 상수\nDEFAULT_TIMEOUT = 30\nMAX_RETRIES = 5\nSERVICE_NAME = \"RAGIT-CORE\"",
            "file_path": "app/core/config.py",
            "name": "", # 특정 함수나 클래스에 속하지 않는 경우
            "start_line": 5,
            "end_line": 7,
            "type": "module", # 모듈 레벨의 코드
            "_source_file": "/usr/src/app/core/config.py",
            "score": None # score 값이 없는 경우
        }
    ]

    query = "How to export data to JSON?"

    print(f"\n📌 Input dummy data[0]: {search_results[0]}")
    print(f"📌 Query: {query}")
    print(f"\n⏳ Sending task to Celery worker...")

    # Task 전송
    task = app.send_task(
        'rag_worker.tasks.create_prompt',
        kwargs={
            'docs': search_results,
            'query': query
        }
    )

    print(f"✅ Task sent! (Task ID: {task.id})")
    print(f"⏳ Waiting for result...\n")

    # 결과 대기
    try:
        result = task.get(timeout=60)

        print("="*60)
        print("📋 Search Result")
        print("="*60)

        print(result)


        print("\n" + "="*60)

    except Exception as e:
        print(f"❌ Task failed: {str(e)}")


if __name__ == "__main__":
    test_create_prompt()
