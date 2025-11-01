import requests
from typing import List, Dict, Any, Optional
from datetime import datetime
import json
import os

class APIService:
    def __init__(self, base_url: str = None, auth_service=None):
        self.base_url = base_url or os.getenv("GATEWAY_URL", "http://localhost:8080")
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json"
        })
        self.auth_service = auth_service

    def _parse_datetime(self, dt_str: str) -> datetime:
        """ISO 문자열을 datetime 객체로 변환"""
        try:
            # ISO 형식 파싱
            if 'T' in dt_str:
                # ISO 8601 형식 (2024-01-01T12:00:00 또는 2024-01-01T12:00:00.123456)
                if '.' in dt_str:
                    return datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
                else:
                    return datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
            else:
                # 단순 날짜 형식
                return datetime.fromisoformat(dt_str)
        except:
            # 파싱 실패 시 현재 시간 반환
            return datetime.now()

    def _convert_datetime_fields(self, data: Any, datetime_fields: List[str] = None) -> Any:
        """데이터의 datetime 필드들을 문자열에서 datetime 객체로 변환"""
        if datetime_fields is None:
            datetime_fields = ['created_at', 'last_sync', 'joined_at', 'timestamp']

        if isinstance(data, dict):
            for field in datetime_fields:
                if field in data and isinstance(data[field], str):
                    data[field] = self._parse_datetime(data[field])
            return data
        elif isinstance(data, list):
            return [self._convert_datetime_fields(item, datetime_fields) for item in data]
        else:
            return data

    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """Make HTTP request to the gateway API"""
        url = f"{self.base_url}{endpoint}"
        print(f"DEBUG: Making {method} request to {url}")  # Debug logging

        # Authorization 헤더 추가
        headers = {"Content-Type": "application/json"}
        if self.auth_service:
            token = self.auth_service.get_token()
            if token:
                headers["Authorization"] = f"Bearer {token}"
                print(f"DEBUG: Added Authorization header with token")

        try:
            timeout = 10  # 10 second timeout
            if method.upper() == "GET":
                response = self.session.get(url, headers=headers, timeout=timeout)
            elif method.upper() == "POST":
                response = self.session.post(url, headers=headers, json=data, timeout=timeout)
            elif method.upper() == "PUT":
                response = self.session.put(url, headers=headers, json=data, timeout=timeout)
            elif method.upper() == "DELETE":
                response = self.session.delete(url, headers=headers, timeout=timeout)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            print(f"DEBUG: Response status: {response.status_code}")  # Debug logging
            response.raise_for_status()
            return response.json()
        except requests.exceptions.ConnectionError as e:
            print(f"DEBUG: Connection error to {url}: {e}")  # Debug logging
            raise Exception(f"Gateway server is not available at {url}. Connection error: {e}")
        except requests.exceptions.Timeout as e:
            print(f"DEBUG: Timeout error to {url}: {e}")  # Debug logging
            raise Exception(f"Gateway server timeout at {url}")
        except requests.exceptions.HTTPError as e:
            print(f"DEBUG: HTTP error: {e}")  # Debug logging
            try:
                error_detail = response.json()
                print(f"DEBUG: Error detail: {error_detail}")
                raise Exception(f"API request failed: {error_detail.get('detail', str(e))}")
            except:
                raise Exception(f"API request failed: {e}")
        except Exception as e:
            print(f"DEBUG: Unexpected error: {e}")  # Debug logging
            raise Exception(f"Unexpected error: {e}")

    def get_repositories(self) -> List[Dict[str, Any]]:
        """Get all repositories"""
        try:
            data = self._make_request("GET", "/api/repositories")
            return self._convert_datetime_fields(data)
        except Exception:
            # API가 구현되지 않은 경우 더미 데이터 반환
            return []

    def get_repository(self, repo_id: str) -> Dict[str, Any]:
        """Get a specific repository by ID"""
        data = self._make_request("GET", f"/api/repositories/{repo_id}")
        return self._convert_datetime_fields(data)

    def create_repository(self, name: str, url: str, description: str = None, is_public: bool = False) -> Dict[str, Any]:
        """Create a new repository"""
        data = {
            "name": name,
            "url": url,
            "description": description if description else None,
            "is_public": is_public
        }
        print(f"DEBUG: Creating repository with data: {data}")
        response = self._make_request("POST", "/api/repositories", data)
        return self._convert_datetime_fields(response)

    def get_repository_status(self, repo_id: str) -> Dict[str, Any]:
        """Get repository processing status"""
        data = self._make_request("GET", f"/api/repositories/{repo_id}/status")
        return self._convert_datetime_fields(data)

    def get_chat_rooms(self, repo_id: str) -> List[Dict[str, Any]]:
        """Get chat rooms for a repository"""
        try:
            data = self._make_request("GET", f"/api/repositories/{repo_id}/chat-rooms")
            return self._convert_datetime_fields(data)
        except Exception:
            # API가 구현되지 않은 경우 더미 데이터 반환
            return []

    def get_messages(self, chat_room_id: str) -> List[Dict[str, Any]]:
        """Get messages for a chat room"""
        messages = self._make_request("GET", f"/api/repositories/chat-rooms/{chat_room_id}/messages")
        return self._convert_datetime_fields(messages)

    def add_message(self, chat_room_id: str, sender_type: str, content: str) -> Dict[str, Any]:
        """Add a new message to a chat room"""
        data = {
            "chat_room_id": chat_room_id,
            "sender_type": sender_type,
            "content": content
        }
        response = self._make_request("POST", f"/api/repositories/chat-rooms/{chat_room_id}/messages", data)
        return self._convert_datetime_fields(response)

    def create_chat_room(self, name: str, repo_id: str) -> Dict[str, Any]:
        """Create a new chat room"""
        data = {
            "name": name,
            "repository_id": repo_id
        }
        room = self._make_request("POST", f"/api/repositories/{repo_id}/chat-rooms", data)
        return self._convert_datetime_fields(room)

    def get_vectordb_collections(self, repo_id: str) -> List[Dict[str, Any]]:
        """Get vector database collections for a repository"""
        return self._make_request("GET", f"/repositories/{repo_id}/vectordb/collections")

    def get_repository_members(self, repo_id: str) -> List[Dict[str, Any]]:
        """Get members of a repository"""
        members = self._make_request("GET", f"/api/repositories/{repo_id}/members")
        return self._convert_datetime_fields(members)

    def add_repository_member(self, repo_id: str, user_id: str, role: str = "member") -> Dict[str, Any]:
        """Add a member to a repository"""
        data = {
            "user_id": user_id,
            "role": role
        }
        response = self._make_request("POST", f"/api/repositories/{repo_id}/members", data)
        return self._convert_datetime_fields(response)

    def update_member_role(self, repo_id: str, member_id: str, role: str) -> Dict[str, Any]:
        """Update a member's role"""
        data = {"role": role}
        response = self._make_request("PUT", f"/api/repositories/{repo_id}/members/{member_id}", data)
        return self._convert_datetime_fields(response)

    def remove_repository_member(self, repo_id: str, member_id: str) -> bool:
        """Remove a member from a repository"""
        try:
            self._make_request("DELETE", f"/api/repositories/{repo_id}/members/{member_id}")
            return True
        except Exception:
            return False

    def get_user_active_chats_count(self, user_email: str) -> int:
        """Get the count of active chat rooms for a user"""
        try:
            response = self._make_request("GET", f"/users/{user_email}/active-chats-count")
            return response.get("count", 0)
        except Exception:
            # API가 구현되지 않은 경우 더미 데이터 반환
            return 0

    def get_user_recent_activity(self, user_email: str) -> List[Dict[str, Any]]:
        """Get recent activity for a user"""
        try:
            response = self._make_request("GET", f"/users/{user_email}/recent-activity")
            return response.get("activities", [])
        except Exception:
            # API가 구현되지 않은 경우 더미 데이터 반환
            return []

    def search_user_by_email(self, email: str) -> Dict[str, Any]:
        """Search user by email"""
        return self._make_request("GET", f"/auth/users/search?email={email}")

    async def get_code_history(self, repo_id: str, file_path: str, line_info: str = None, node_name: str = None, node_type: str = "function") -> Dict[str, Any]:
        """Get code history for a specific node in a file"""
        try:
            data = {
                "repo_id": repo_id,
                "file_path": file_path,
                "node_type": node_type
            }

            # line_info가 있으면 추가 (백엔드에서 node_name을 자동으로 찾도록)
            if line_info:
                data["line_info"] = line_info

            # node_name이 명시적으로 제공되면 추가
            if node_name:
                data["node_name"] = node_name
            # 동기 함수를 비동기로 래핑
            import asyncio
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self._make_request("POST", "/api/repositories/code-history", data)
            )
            return response
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "history": []
            }

# Global instance - will be initialized with auth_service in app.py
api_service = None

def init_api_service(auth_service):
    """Initialize global api_service with auth_service"""
    global api_service
    api_service = APIService(auth_service=auth_service)