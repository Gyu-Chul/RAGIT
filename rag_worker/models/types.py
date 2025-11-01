"""
데이터베이스 커스텀 타입 정의
단일 책임: 데이터베이스 타입 정의만 담당
"""

import uuid
from typing import Any, Optional
from sqlalchemy.types import TypeDecorator, CHAR
from sqlalchemy.dialects.postgresql import UUID as PostgreSQL_UUID


class GUID(TypeDecorator):
    """
    플랫폼 독립적인 GUID 타입
    PostgreSQL에서는 UUID 타입을 사용하고, 다른 DB에서는 CHAR(32)를 사용
    """
    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect: Any) -> Any:
        """방언별 구현 로드"""
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(PostgreSQL_UUID(as_uuid=True))
        else:
            return dialect.type_descriptor(CHAR(32))

    def process_bind_param(self, value: Optional[Any], dialect: Any) -> Optional[Any]:
        """바인딩 파라미터 처리"""
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return str(value) if not isinstance(value, uuid.UUID) else value
        else:
            if not isinstance(value, uuid.UUID):
                return "%.32x" % uuid.UUID(value).int
            else:
                return "%.32x" % value.int

    def process_result_value(self, value: Optional[Any], dialect: Any) -> Optional[uuid.UUID]:
        """결과 값 처리"""
        if value is None:
            return value
        else:
            if not isinstance(value, uuid.UUID):
                return uuid.UUID(value)
            else:
                return value
