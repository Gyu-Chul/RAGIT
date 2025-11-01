"""
Chat API 라우터
단일 책임: Chat 관련 HTTP 요청 처리
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..services.chat_service import ChatRoomService, ChatMessageService
from ..services.repository_service import RepositoryService
from ..services.auth_service import get_current_active_user
from ..schemas.chat import (
    ChatRoomCreate,
    ChatRoomUpdate,
    ChatRoomResponse,
    ChatMessageCreate,
    ChatMessageResponse
)
from ..models.user import User

router = APIRouter(prefix="/api/repositories", tags=["chat"])


# ChatRoom Endpoints

@router.post("/{repo_id}/chat-rooms", response_model=ChatRoomResponse, status_code=status.HTTP_201_CREATED)
def create_chat_room(
    repo_id: str,
    room_data: ChatRoomCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """새로운 ChatRoom 생성"""
    # Repository 접근 권한 확인
    if not RepositoryService.check_user_permission(db, repo_id, str(current_user.id)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this repository"
        )

    # Repository 존재 확인
    repository = RepositoryService.get_repository(db, repo_id)
    if not repository:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found"
        )

    # ChatRoom 생성
    chat_room = ChatRoomService.create_chat_room(db, room_data, str(current_user.id))

    # 응답 생성
    room_dict = {
        "id": str(chat_room.id),
        "name": chat_room.name,
        "repository_id": str(chat_room.repository_id),
        "created_by": str(chat_room.created_by),
        "message_count": chat_room.message_count or 0,
        "last_message": chat_room.last_message,
        "created_at": chat_room.created_at,
        "updated_at": chat_room.updated_at
    }

    return room_dict


@router.get("/{repo_id}/chat-rooms", response_model=List[ChatRoomResponse])
def get_chat_rooms(
    repo_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Repository의 모든 ChatRoom 조회"""
    # Repository 접근 권한 확인
    if not RepositoryService.check_user_permission(db, repo_id, str(current_user.id)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this repository"
        )

    # ChatRoom 목록 조회
    chat_rooms = ChatRoomService.get_repository_chat_rooms(db, repo_id)

    # 응답 생성
    result = []
    for room in chat_rooms:
        room_dict = {
            "id": str(room.id),
            "name": room.name,
            "repository_id": str(room.repository_id),
            "created_by": str(room.created_by),
            "message_count": room.message_count or 0,
            "last_message": room.last_message,
            "created_at": room.created_at,
            "updated_at": room.updated_at
        }
        result.append(room_dict)

    return result


@router.get("/chat-rooms/{room_id}", response_model=ChatRoomResponse)
def get_chat_room(
    room_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """특정 ChatRoom 조회"""
    chat_room = ChatRoomService.get_chat_room(db, room_id)
    if not chat_room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat room not found"
        )

    # Repository 접근 권한 확인
    if not RepositoryService.check_user_permission(
        db, str(chat_room.repository_id), str(current_user.id)
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this chat room"
        )

    # 응답 생성
    room_dict = {
        "id": str(chat_room.id),
        "name": chat_room.name,
        "repository_id": str(chat_room.repository_id),
        "created_by": str(chat_room.created_by),
        "message_count": chat_room.message_count or 0,
        "last_message": chat_room.last_message,
        "created_at": chat_room.created_at,
        "updated_at": chat_room.updated_at
    }

    return room_dict


@router.put("/chat-rooms/{room_id}", response_model=ChatRoomResponse)
def update_chat_room(
    room_id: str,
    room_data: ChatRoomUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """ChatRoom 업데이트"""
    chat_room = ChatRoomService.get_chat_room(db, room_id)
    if not chat_room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat room not found"
        )

    # 생성자만 수정 가능
    if str(chat_room.created_by) != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the creator can update this chat room"
        )

    updated_room = ChatRoomService.update_chat_room(db, room_id, room_data)

    # 응답 생성
    room_dict = {
        "id": str(updated_room.id),
        "name": updated_room.name,
        "repository_id": str(updated_room.repository_id),
        "created_by": str(updated_room.created_by),
        "message_count": updated_room.message_count or 0,
        "last_message": updated_room.last_message,
        "created_at": updated_room.created_at,
        "updated_at": updated_room.updated_at
    }

    return room_dict


@router.delete("/chat-rooms/{room_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_chat_room(
    room_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """ChatRoom 삭제"""
    chat_room = ChatRoomService.get_chat_room(db, room_id)
    if not chat_room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat room not found"
        )

    # 생성자만 삭제 가능
    if str(chat_room.created_by) != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the creator can delete this chat room"
        )

    success = ChatRoomService.delete_chat_room(db, room_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to delete chat room"
        )


# ChatMessage Endpoints

@router.post("/chat-rooms/{room_id}/messages", response_model=ChatMessageResponse, status_code=status.HTTP_201_CREATED)
def create_message(
    room_id: str,
    message_data: ChatMessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """새로운 ChatMessage 생성"""
    # ChatRoom 존재 확인
    chat_room = ChatRoomService.get_chat_room(db, room_id)
    if not chat_room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat room not found"
        )

    # Repository 접근 권한 확인
    if not RepositoryService.check_user_permission(
        db, str(chat_room.repository_id), str(current_user.id)
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to send messages in this chat room"
        )

    # 메시지 생성
    user_id = str(current_user.id) if message_data.sender_type == "user" else None
    message = ChatMessageService.create_message(db, message_data, user_id)

    # 사용자 메시지인 경우 RAG Worker에 쿼리 전송
    if message_data.sender_type == "user":
        import logging
        logger = logging.getLogger(__name__)

        try:
            from ..core.celery import celery_app

            logger.info(f"🤖 Triggering RAG chat query for message: {message.id}")

            # Celery task 트리거
            task = celery_app.send_task(
                'rag_worker.tasks.chat_query',
                kwargs={
                    'chat_room_id': str(chat_room.id),
                    'repo_id': str(chat_room.repository_id),
                    'user_message': message.content,
                    'top_k': 5
                }
            )

            logger.info(f"✅ RAG task sent. Task ID: {task.id}")

        except Exception as task_error:
            logger.error(f"❌ Failed to trigger RAG task: {str(task_error)}", exc_info=True)
            # Task 실패해도 메시지는 저장되었으므로 계속 진행

    # 응답 생성
    message_dict = {
        "id": str(message.id),
        "chat_room_id": str(message.chat_room_id),
        "sender_id": str(message.sender_id) if message.sender_id else None,
        "sender_type": message.sender_type,
        "content": message.content,
        "sources": message.sources,
        "created_at": message.created_at
    }

    return message_dict


@router.get("/chat-rooms/{room_id}/messages", response_model=List[ChatMessageResponse])
def get_messages(
    room_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """ChatRoom의 모든 메시지 조회"""
    # ChatRoom 존재 확인
    chat_room = ChatRoomService.get_chat_room(db, room_id)
    if not chat_room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat room not found"
        )

    # Repository 접근 권한 확인
    if not RepositoryService.check_user_permission(
        db, str(chat_room.repository_id), str(current_user.id)
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to view messages in this chat room"
        )

    # 메시지 목록 조회
    messages = ChatMessageService.get_chat_room_messages(db, room_id)

    # 응답 생성
    result = []
    for msg in messages:
        message_dict = {
            "id": str(msg.id),
            "chat_room_id": str(msg.chat_room_id),
            "sender_id": str(msg.sender_id) if msg.sender_id else None,
            "sender_type": msg.sender_type,
            "content": msg.content,
            "sources": msg.sources,
            "created_at": msg.created_at
        }
        result.append(message_dict)

    return result


@router.delete("/chat-rooms/messages/{message_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_message(
    message_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """ChatMessage 삭제"""
    message = ChatMessageService.get_message(db, message_id)
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found"
        )

    # 발신자만 삭제 가능
    if message.sender_id and str(message.sender_id) != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the sender can delete this message"
        )

    success = ChatMessageService.delete_message(db, message_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to delete message"
        )


@router.post("/code-history", status_code=status.HTTP_200_OK)
def get_code_history(
    request: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """파일 또는 코드의 Git 히스토리 조회"""
    from ..core.celery import celery_app
    import logging
    import json
    from pathlib import Path

    logger = logging.getLogger(__name__)

    # 필수 파라미터 검증
    repo_id = request.get("repo_id")
    file_path = request.get("file_path")
    line_info = request.get("line_info", "")  # "150-200" 형식
    node_name = request.get("node_name")
    node_type = request.get("node_type")

    # track_full_file: True면 파일 전체 추적, False/None이면 특정 노드 추적
    track_full_file = request.get("track_full_file", True)

    if not all([repo_id, file_path]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required parameters: repo_id, file_path"
        )

    # 전체 파일 추적 모드면 node_name, node_type을 None으로 설정
    if track_full_file:
        logger.info(f"📖 Tracking full file history for {file_path}")
        node_name = None
        node_type = None
        start_line = None
        end_line = None
    # 특정 노드 추적 모드
    else:
        # line_info를 파싱하여 start_line, end_line 추출
        start_line = None
        end_line = None
        if line_info:
            try:
                if '-' in line_info:
                    parts = line_info.split('-')
                    start_line = int(parts[0])
                    end_line = int(parts[1]) if len(parts) > 1 else start_line
                else:
                    start_line = int(line_info)
                    end_line = start_line
            except ValueError:
                logger.warning(f"⚠️ Invalid line_info format: {line_info}")

        # node_name이 없으면 parsed_repository에서 찾기
        if not node_name and start_line:
            try:
                # parsed_repository에서 해당 파일의 JSON 읽기
                parsed_dir = Path("parsed_repository") / f"repo_{repo_id.replace('-', '_')}"
                json_file_path = parsed_dir / file_path.replace('.py', '.json')

                logger.info(f"🔍 Looking for parsed JSON at: {json_file_path}")

                if json_file_path.exists():
                    with open(json_file_path, 'r', encoding='utf-8') as f:
                        parsed_data = json.load(f)

                    # start_line과 매칭되는 노드 찾기
                    for item in parsed_data:
                        if item.get('start_line') <= start_line <= item.get('end_line', start_line):
                            item_name = item.get('name', '')
                            item_type = item.get('type', 'function')

                            # 이름이 있는 노드만 사용 (function, async_function, class)
                            if item_name and item_type in ['function', 'async_function', 'class']:
                                node_name = item_name
                                node_type = item_type
                                # 실제 노드의 라인 범위로 업데이트
                                start_line = item.get('start_line')
                                end_line = item.get('end_line')
                                logger.info(f"✅ Found node: {node_name} ({node_type}) at lines {start_line}-{end_line}")
                                break
                            # 이름이 없는 노드 (module, script)의 경우 라인 범위만 사용
                            elif item_type in ['module', 'script']:
                                node_name = ''  # module/script는 이름이 없음
                                node_type = item_type
                                start_line = item.get('start_line')
                                end_line = item.get('end_line')
                                logger.info(f"✅ Found {node_type} at lines {start_line}-{end_line}")
                                break

                if not node_name and not node_type:
                    # 기본값 설정
                    logger.warning(f"⚠️ Could not find node at line {start_line} in {file_path}")
                    node_name = ''
                    node_type = "script"

            except Exception as e:
                logger.error(f"❌ Error finding node name: {str(e)}")
                node_name = ''
                node_type = "script"

        # node_name이 여전히 없으면 기본값
        if not node_name and not node_type:
            node_name = ''
            node_type = 'script'

    # Repository 접근 권한 확인
    if not RepositoryService.check_user_permission(db, repo_id, str(current_user.id)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this repository"
        )

    try:
        # Celery task 호출 (동기적으로 결과 대기)
        task = celery_app.send_task(
            'rag_worker.tasks.get_code_history',
            kwargs={
                'repo_id': repo_id,
                'file_path': file_path,
                'node_name': node_name,
                'node_type': node_type,
                'start_line': start_line,
                'end_line': end_line
            }
        )

        if node_name is None and node_type is None:
            logger.info(f"📖 Getting full file history for {file_path}")
        else:
            logger.info(f"📖 Getting history for {node_type} '{node_name}' in {file_path} (lines {start_line}-{end_line})")

        # 결과 대기 (최대 30초)
        result = task.get(timeout=30)

        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get("error", "Failed to get code history")
            )

        return result

    except Exception as e:
        logger.error(f"❌ Failed to get code history: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get code history: {str(e)}"
        )
