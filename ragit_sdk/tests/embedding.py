"""
RAG Worker 파싱 및 임베딩 전체 파이프라인 테스트

사용법:
1. Redis 서버 실행 확인
2. Celery Worker 실행 확인 (parse_and_embed_repository Task가 등록된 상태)
3. 아래 INPUT 값을 수정한 후, python -m ragit_sdk.tests.embedding.py 실행
"""

from celery import Celery

# Celery 앱 설정
app = Celery(
    'test_full_pipeline',
    broker='redis://localhost:6379/0',
    backend='redis://localhost:6379/0'
)


def test_parse_and_embed() -> None:
    """레포지토리를 파싱하고 임베딩하는 전체 파이프라인 Task를 테스트"""
    print("\n" + "="*60)
    print("Parse and Embed Repository Test")
    print("="*60)

    # ==================== INPUT ====================

    # 1. 로컬에 clone된 레포지토리의 이름(폴더명)
    repo_name_to_process = "Test_Repo"

    # 2. Vector DB에 생성/사용할 컬렉션의 이름
    collection_name = "Test_Repo"

    # 3. 사용할 임베딩 모델의 키
    model_key = "sfr-code-400m" # 예시 모델 키
    # ===============================================

    print(f"📌 Repository Name: {repo_name_to_process}")
    print(f"📌 Collection Name: {collection_name}")
    print(f"📌 Model Key: {model_key}")
    print(f"\n⏳ Sending task to Celery worker...")

    # 통합 Task 전송
    task = app.send_task(
        'rag_worker.tasks.parse_and_embed_repository',
        kwargs={
            'repo_name': repo_name_to_process,
            'collection_name': collection_name,
            'model_key': model_key
        }
    )

    print(f"✅ Task sent! (Task ID: {task.id})")
    print(f"⏳ Waiting for pipeline result... (시간이 다소 걸릴 수 있습니다)\n")

    # 결과 대기 (파싱+임베딩은 시간이 걸릴 수 있으므로 timeout을 넉넉하게 설정)
    try:
        result = task.get(timeout=1200) # 20분 대기

        print("="*60)
        print("📋 Pipeline Result")
        print("="*60)

        if result and result.get('success'):
            print(f"✔️ Success: {result.get('message')}")
            print(f"✔️ Parsed Files: {result.get('parsed_files')}")
            print(f"✔️ Embedded Chunks: {result.get('embedded_count')}")
        else:
            print(f"❌ Failed at step: '{result.get('step')}'")
            print(f"❌ Reason: {result.get('error')}")

        print("\nFull response:")
        print(result)

        print("\n" + "="*60)

    except Exception as e:
        print(f"❌ Task failed with an exception: {str(e)}")


if __name__ == "__main__":
    test_parse_and_embed()