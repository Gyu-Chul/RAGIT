"""
RAG Worker 검색 기능만 테스트

사용법:
1. Redis 서버 실행 확인
2. Celery Worker 실행 확인
3. python -m ragit_sdk.tests.ask_question 실행
"""

from celery import Celery
from celery.result import AsyncResult
from typing import List, Optional, TypedDict

# Celery 앱 설정
app = Celery(
    'test_search',
    broker='redis://localhost:6379/0',
    backend='redis://localhost:6379/0'
)


def ask_question() -> None:
    """llm api 전송 테스트"""
    print("\n" + "="*60)
    print("LLM Ask Test")
    print("="*60)

    prompt = """
    아래 코드 컨텍스트를 바탕으로 질문에 답변해 주세요.

    --- 컨텍스트 ---
        ('출처 2:\n- 파일: app/utils/vector_utils.py', "- 모듈 정의: function 'calculate_similarity'", '- 관련성 점수: 0.912345')
    ```python
    def calculate_similarity(vec1, vec2):
        두 벡터 간의 코사인 유사도를 계산합니다.
        return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))
    ```

    ('출처 3:\n- 파일: app/models/user.py', "- 모듈 정의: class 'UserManager'", '- 관련성 점수: 0.8876')
    ```python
    class UserManager:
        def __init__(self, db_session):
            self.session = db_session

        def get_user(self, user_id: int):
            return self.session.query(User).filter_by(id=user_id).first()     
    ```

    ('출처 4:\n- 파일: main.py', "- 모듈 정의: script '__main__'", '- 관련성  점수: 0.7543')
    ```python
    if __name__ == "__main__":
        parser = argparse.ArgumentParser()
        parser.add_argument("--config", default="config.yaml")
        args = parser.parse_args()
        main(args.config)
    ```

    ('출처 5:\n- 파일: app/core/config.py', "- 모듈 정의: module ''", '- 관련 성 점수: None')
    ```python
    # 프로젝트 전역에서 사용되는 상수
    DEFAULT_TIMEOUT = 30
    MAX_RETRIES = 5
    SERVICE_NAME = "RAGIT-CORE"
    ```
        --- 컨텍스트 종료 ---

        질문: What is the arguments of parser?
    """
    use_stream = True

    print(f"\n⏳ Sending task to Celery worker...")

    # Task 전송
    task = app.send_task(
        'rag_worker.tasks.call_llm',
        kwargs={
            'prompt': prompt,
            'use_stream': use_stream,
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
    ask_question()
