"""
RAG Worker Git Diff 기능만 테스트

사용법:
1. Redis 서버 실행 확인
2. Celery Worker 실행 확인 (아래 '필수 작업'의 Task가 등록된 상태)
3. python -m ragit_sdk.tests.diff_file 실행
"""

from celery import Celery
from celery.result import AsyncResult

# Celery 앱 설정
app = Celery(
    'test_git_diff',
    broker='redis://localhost:6379/0',
    backend='redis://localhost:6379/0'
)


def test_git_diff_service() -> None:
    """git_service.diff_files 호출 테스트"""
    print("\n" + "="*60)
    print("Git Diff Service Test")
    print("="*60)

    # 테스트할 로컬 레포지토리의 '이름(폴더명)'
    # 이 레포지토리는 미리 clone 되어 있어야 함
    repo_name_to_test = "RAGIT"

    print(f"\n⏳ Sending task to Celery worker for repository: '{repo_name_to_test}'")

    # Task 전송: diff_files를 호출하는 task를 실행
    task = app.send_task(
        'rag_worker.tasks.run_git_diff',
        kwargs={
            'repo_name': repo_name_to_test,
        }
    )

    print(f"✅ Task sent! (Task ID: {task.id})")
    print(f"⏳ Waiting for result...\n")

    # 결과 대기
    try:
        # 타임아웃을 넉넉하게 60초로 설정
        result = task.get(timeout=60)

        print("="*60)
        print("📋 Git Diff Result")
        print("="*60)

        if result and result.get('success'):
            print(f"✔️ Success: {result.get('message')}")
            print(f"📄 Changed Files (formatted): {result.get('files')}")
        else:
            print(f"❌ Failed: {result.get('error')}")
        
        print("\nFull response:")
        print(result)

        print("\n" + "="*60)

    except Exception as e:
        print(f"❌ Task failed with an exception: {str(e)}")


if __name__ == "__main__":
    test_git_diff_service()