"""
Repository API 라우터
단일 책임: Repository 관련 HTTP 요청 처리
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..services.repository_service import RepositoryService, RepositoryMemberService
from ..services.auth_service import get_current_active_user
from ..schemas.repository import (
    RepositoryCreate,
    RepositoryUpdate,
    RepositoryResponse,
    RepositoryMemberCreate,
    RepositoryMemberUpdate,
    RepositoryMemberResponse,
    RepositoryWithMembers
)
from ..models.user import User

router = APIRouter(prefix="/api/repositories", tags=["repositories"])


@router.post("/", response_model=RepositoryResponse, status_code=status.HTTP_201_CREATED)
def create_repository(
    repo_data: RepositoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """새로운 Repository 생성"""
    import logging
    logger = logging.getLogger(__name__)

    try:
        logger.info(f"Creating repository: name={repo_data.name}, url={repo_data.url}, owner={current_user.username}")
        repository = RepositoryService.create_repository(db, repo_data, str(current_user.id))

        # Celery Task 비동기 트리거 - Repository 처리 파이프라인
        try:
            from ..core.celery import celery_app

            # Redis 연결 확인
            logger.info(f"Celery broker: {celery_app.conf.broker_url}")
            logger.info(f"Triggering Celery task for repository: {repository.id}")

            # Celery를 통해 task 전송 (기본 celery queue 사용)
            task = celery_app.send_task(
                'rag_worker.tasks.process_repository_pipeline',
                kwargs={
                    'repo_id': str(repository.id),
                    'git_url': repository.url,
                    'repo_name': repository.name
                }
            )
            logger.info(f"✅ Celery task sent to default queue. Task ID: {task.id}")
        except Exception as task_error:
            logger.error(f"❌ Failed to trigger Celery task: {str(task_error)}", exc_info=True)
            # Task 실패해도 repository는 생성되었으므로 계속 진행

        # owner 정보를 포함한 응답 생성
        repo_dict = {
            "id": str(repository.id),
            "name": repository.name,
            "description": repository.description,
            "url": repository.url,
            "is_public": repository.is_public,
            "owner_id": str(repository.owner_id),
            "owner": current_user.username,
            "stars": repository.stars or 0,
            "language": repository.language,
            "status": repository.status,
            "vectordb_status": repository.vectordb_status,
            "error_message": repository.error_message,
            "collections_count": repository.collections_count or 0,
            "file_count": repository.file_count or 0,
            "created_at": repository.created_at,
            "updated_at": repository.updated_at,
            "last_sync": repository.last_sync
        }

        return repo_dict
    except Exception as e:
        logger.error(f"Failed to create repository: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create repository: {str(e)}"
        )


@router.get("/", response_model=List[RepositoryResponse])
def get_repositories(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """현재 사용자가 접근 가능한 모든 Repository 조회"""
    repositories = RepositoryService.get_user_repositories(db, str(current_user.id))

    # owner 정보를 포함한 응답 생성
    result = []
    for repo in repositories:
        repo_dict = {
            "id": str(repo.id),
            "name": repo.name,
            "description": repo.description,
            "url": repo.url,
            "is_public": repo.is_public,
            "owner_id": str(repo.owner_id),
            "owner": repo.owner.username if repo.owner else "Unknown",
            "stars": repo.stars or 0,
            "language": repo.language,
            "status": repo.status,
            "vectordb_status": repo.vectordb_status,
            "error_message": repo.error_message,
            "collections_count": repo.collections_count or 0,
            "file_count": repo.file_count or 0,
            "created_at": repo.created_at,
            "updated_at": repo.updated_at,
            "last_sync": repo.last_sync
        }
        result.append(repo_dict)

    return result


@router.get("/{repo_id}", response_model=RepositoryResponse)
def get_repository(
    repo_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """특정 Repository 조회"""
    if not RepositoryService.check_user_permission(db, repo_id, str(current_user.id)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this repository"
        )

    repository = RepositoryService.get_repository(db, repo_id)
    if not repository:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found"
        )

    # owner 정보를 포함한 응답 생성
    repo_dict = {
        "id": str(repository.id),
        "name": repository.name,
        "description": repository.description,
        "url": repository.url,
        "is_public": repository.is_public,
        "owner_id": str(repository.owner_id),
        "owner": repository.owner.username if repository.owner else "Unknown",
        "stars": repository.stars or 0,
        "language": repository.language,
        "status": repository.status,
        "vectordb_status": repository.vectordb_status,
        "error_message": repository.error_message,
        "collections_count": repository.collections_count or 0,
        "file_count": repository.file_count or 0,
        "created_at": repository.created_at,
        "updated_at": repository.updated_at,
        "last_sync": repository.last_sync
    }

    return repo_dict


@router.get("/{repo_id}/status")
def get_repository_status(
    repo_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Repository 처리 상태 조회"""
    if not RepositoryService.check_user_permission(db, repo_id, str(current_user.id)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this repository"
        )

    repository = RepositoryService.get_repository(db, repo_id)
    if not repository:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found"
        )

    return {
        "repo_id": str(repository.id),
        "status": repository.status,
        "vectordb_status": repository.vectordb_status,
        "error_message": repository.error_message,
        "file_count": repository.file_count,
        "last_sync": repository.last_sync
    }


@router.post("/{repo_id}/sync")
def sync_repository(
    repo_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Repository를 원격 저장소와 동기화하여 최신 변경사항 반영"""
    import logging
    logger = logging.getLogger(__name__)

    # 권한 확인
    if not RepositoryService.check_user_permission(db, repo_id, str(current_user.id), "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to sync this repository"
        )

    # Repository 조회
    repository = RepositoryService.get_repository(db, repo_id)
    if not repository:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found"
        )

    # 이미 동기화 중인지 확인
    if repository.status in ["syncing", "updating", "pending"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Repository is already being processed (status: {repository.status})"
        )

    try:
        logger.info(f"Starting sync for repository: {repository.name} (ID: {repo_id})")

        # Celery Task 비동기 트리거 - Repository 업데이트 파이프라인
        try:
            from ..core.celery import celery_app

            logger.info(f"Celery broker: {celery_app.conf.broker_url}")
            logger.info(f"Triggering update_repository_pipeline task for repository: {repository.id}")

            # Collection name 생성 (repo_id에서 하이픈 제거)
            collection_name = f"repo_{str(repository.id).replace('-', '_')}"

            # Celery를 통해 update task 전송
            task = celery_app.send_task(
                'rag_worker.tasks.update_repository_pipeline',
                kwargs={
                    'repo_id': str(repository.id),
                    'repo_name': repository.name,
                    'collection_name': collection_name,
                    'save_json': True,
                    'model_key': 'text-embedding-3-small'  # 기본 임베딩 모델
                }
            )
            logger.info(f"✅ Celery update task sent. Task ID: {task.id}")

        except Exception as task_error:
            logger.error(f"❌ Failed to trigger Celery update task: {str(task_error)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to start sync task: {str(task_error)}"
            )

        return {
            "success": True,
            "message": f"Repository sync started for '{repository.name}'",
            "task_id": task.id,
            "repo_id": str(repository.id)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to sync repository: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sync repository: {str(e)}"
        )


@router.put("/{repo_id}", response_model=RepositoryResponse)
def update_repository(
    repo_id: str,
    repo_data: RepositoryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Repository 정보 업데이트"""
    if not RepositoryService.check_user_permission(db, repo_id, str(current_user.id), "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to update this repository"
        )

    repository = RepositoryService.update_repository(db, repo_id, repo_data)
    if not repository:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found"
        )

    # owner 정보를 포함한 응답 생성
    repo_dict = {
        "id": str(repository.id),
        "name": repository.name,
        "description": repository.description,
        "url": repository.url,
        "is_public": repository.is_public,
        "owner_id": str(repository.owner_id),
        "owner": repository.owner.username if repository.owner else "Unknown",
        "stars": repository.stars or 0,
        "language": repository.language,
        "status": repository.status,
        "vectordb_status": repository.vectordb_status,
        "error_message": repository.error_message,
        "collections_count": repository.collections_count or 0,
        "file_count": repository.file_count or 0,
        "created_at": repository.created_at,
        "updated_at": repository.updated_at,
        "last_sync": repository.last_sync
    }

    return repo_dict


@router.delete("/{repo_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_repository(
    repo_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Repository 삭제 (소유자만 가능)"""
    repository = RepositoryService.get_repository(db, repo_id)
    if not repository:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found"
        )
    
    if str(repository.owner_id) != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the owner can delete this repository"
        )
    
    success = RepositoryService.delete_repository(db, repo_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to delete repository"
        )


@router.get("/{repo_id}/members", response_model=List[RepositoryMemberResponse])
def get_repository_members(
    repo_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Repository의 모든 멤버 조회"""
    if not RepositoryService.check_user_permission(db, repo_id, str(current_user.id)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to view members"
        )
    
    members = RepositoryMemberService.get_repository_members(db, repo_id)
    
    result = []
    for member in members:
        member_dict = {
            "id": str(member.id),
            "repository_id": str(member.repository_id),
            "user_id": str(member.user_id),
            "role": member.role,
            "joined_at": member.joined_at,
            "username": member.user.username if member.user else None,
            "email": member.user.email if member.user else None
        }
        result.append(member_dict)
    
    return result


@router.post("/{repo_id}/members", response_model=RepositoryMemberResponse, status_code=status.HTTP_201_CREATED)
def add_repository_member(
    repo_id: str,
    member_data: RepositoryMemberCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Repository에 멤버 추가"""
    if not RepositoryService.check_user_permission(db, repo_id, str(current_user.id), "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to add members"
        )
    
    existing_member = RepositoryMemberService.get_member_by_user(db, repo_id, member_data.user_id)
    if existing_member:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already a member of this repository"
        )
    
    member = RepositoryMemberService.add_member(db, repo_id, member_data)
    return member


@router.put("/{repo_id}/members/{member_id}", response_model=RepositoryMemberResponse)
def update_repository_member_role(
    repo_id: str,
    member_id: str,
    role_data: RepositoryMemberUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Repository 멤버 역할 업데이트"""
    if not RepositoryService.check_user_permission(db, repo_id, str(current_user.id), "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to update member roles"
        )

    member = RepositoryMemberService.update_member_role(db, member_id, role_data)
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found"
        )

    return member


@router.delete("/{repo_id}/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_repository_member(
    repo_id: str,
    member_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Repository에서 멤버 제거"""
    if not RepositoryService.check_user_permission(db, repo_id, str(current_user.id), "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to remove members"
        )

    success = RepositoryMemberService.remove_member(db, member_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found"
        )
