"""
RAG Worker 레포지토리 업데이트 파이프라인 테스트

사용법:
1. Redis 서버 실행 확인
2. Celery Worker 실행 확인 (parse_and_embed_repository Task가 등록된 상태)
3. 아래 INPUT 값을 수정한 후, python -m ragit_sdk.tests.test_update_pipeline.py 실행
"""

from celery import Celery

# Celery 앱 설정
app = Celery(
    'test_update_pipeline',
    broker='redis://localhost:6379/0',
    backend='redis://localhost:6379/0'
)


def test_update_pipeline() -> None:
    """레포지토리를 업데이트하는 전체 파이프라인 Task를 테스트합니다."""
    print("\n" + "="*60)
    print("Repository Update Pipeline Test")
    print("="*60)

    # ==================== INPUT ====================

    # 1. DB에 저장된 레포지토리의 ID (UUID)
    # 실제로는 DB에서 가져오겠지만, 테스트용으로 하드코딩합니다.
    repo_id = "f47ac10b-58cc-4372-a567-0e02b2c3d479"

    # 2. 로컬에 clone된 레포지토리의 이름(폴더명)
    repo_name_to_process = "Test_Repo"

    # 3. Vector DB에 생성/사용할 컬렉션의 이름
    collection_name = "Test_Repo"

    # 4. 사용할 임베딩 모델의 키
    model_key = "sfr-code-400m"
    # ===============================================

    print(f"📌 Repository ID: {repo_id}")
    print(f"📌 Repository Name: {repo_name_to_process}")
    print(f"📌 Collection Name: {collection_name}")
    print(f"\n⏳ Sending task to Celery worker...")

    # update_repository_pipeline Task 전송
    task = app.send_task(
        'rag_worker.tasks.update_repository_pipeline',
        kwargs={
            'repo_id': repo_id,
            'repo_name': repo_name_to_process,
            'collection_name': collection_name,
            'model_key': model_key
        }
    )

    print(f"✅ Task sent! (Task ID: {task.id})")
    print(f"⏳ Waiting for pipeline result... (시간이 다소 걸릴 수 있습니다)\n")

    # 결과 대기 (타임아웃을 넉넉하게 설정)
    try:
        result = task.get(timeout=1200) # 20분 대기

        print("="*60)
        print("📋 Pipeline Result")
        print("="*60)

        if result and result.get('success'):
            print(f"✔️ Success: {result.get('message')}")
            print(f"✔️ DB Records Deleted: {result.get('deleted_count')}")
            print(f"✔️ New Chunks Embedded: {result.get('embedded_count')}")
        else:
            print(f"❌ Failed at step: '{result.get('step')}'")
            print(f"❌ Reason: {result.get('error')}")

        print("\nFull response:")
        print(result)

        print("\n" + "="*60)

    except Exception as e:
        print(f"❌ Task failed with an exception: {str(e)}")


if __name__ == "__main__":
    test_update_pipeline()