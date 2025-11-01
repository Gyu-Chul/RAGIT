"""
Milvus 컬렉션 관리 클래스
"""

import logging
from typing import List, Optional, Dict, Any
from pymilvus import (
    MilvusClient,
    DataType,
    FieldSchema,
    CollectionSchema,
    Collection,
    connections,
)

from .config import MILVUS_URI
from .exceptions import (
    CollectionNotFoundError,
    CollectionAlreadyExistsError,
    ConnectionError as VectorDBConnectionError,
)
from .types import CollectionInfo, CollectionCreateResult, CollectionDeleteResult

logger = logging.getLogger(__name__)


class MilvusConnectionManager:
    """Milvus 연결 관리 클래스"""

    _client: Optional[MilvusClient] = None

    @classmethod
    def get_client(cls) -> MilvusClient:
        """
        Milvus 클라이언트 반환 (싱글톤 패턴)

        Returns:
            MilvusClient 인스턴스

        Raises:
            VectorDBConnectionError: 연결 실패 시
        """
        if cls._client is None:
            try:
                cls._client = MilvusClient(uri=MILVUS_URI)
                logger.info("✅ Milvus 클라이언트 연결 성공")
            except Exception as e:
                logger.error(f"❌ Milvus 연결 실패: {e}")
                raise VectorDBConnectionError(f"Failed to connect to Milvus: {e}") from e

        return cls._client

    @classmethod
    def ensure_connection(cls) -> None:
        """
        PyMilvus 기본 연결 보장

        Raises:
            VectorDBConnectionError: 연결 실패 시
        """
        try:
            connections.connect(alias="default", uri=MILVUS_URI)
        except Exception as e:
            if "alias default already exists" not in str(e):
                logger.error(f"❌ PyMilvus 연결 실패: {e}")
                raise VectorDBConnectionError(f"Failed to establish connection: {e}") from e


class CollectionManager:
    """Milvus 컬렉션 관리 클래스"""

    def __init__(self) -> None:
        """CollectionManager 초기화"""
        self.client: MilvusClient = MilvusConnectionManager.get_client()

    def exists(self, collection_name: str) -> bool:
        """
        컬렉션 존재 여부 확인

        Args:
            collection_name: 컬렉션 이름

        Returns:
            존재 여부
        """
        return self.client.has_collection(collection_name)

    def validate_exists(self, collection_name: str) -> None:
        """
        컬렉션 존재 여부 검증

        Args:
            collection_name: 컬렉션 이름

        Raises:
            CollectionNotFoundError: 컬렉션이 없을 때
        """
        if not self.exists(collection_name):
            raise CollectionNotFoundError(f"Collection '{collection_name}' not found")

    def validate_not_exists(self, collection_name: str) -> None:
        """
        컬렉션 미존재 여부 검증

        Args:
            collection_name: 컬렉션 이름

        Raises:
            CollectionAlreadyExistsError: 컬렉션이 이미 있을 때
        """
        if self.exists(collection_name):
            raise CollectionAlreadyExistsError(f"Collection '{collection_name}' already exists")

    def create_collection(
        self, collection_name: str, dim: int, description: Optional[str] = None
    ) -> CollectionCreateResult:
        """
        하이브리드 검색용 컬렉션 생성

        Args:
            collection_name: 컬렉션 이름
            dim: 밀집 벡터 차원
            description: 컬렉션 설명

        Returns:
            생성 결과
        """
        try:
            # 이미 존재하는지 확인
            self.validate_not_exists(collection_name)

            analyzer_params: dict = {"type": "english"}

            # 스키마 정의
            fields: List[FieldSchema] = [
                FieldSchema(name="pk", dtype=DataType.INT64, is_primary=True, auto_id=True),
                FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=65_535),
                FieldSchema(name="dense", dtype=DataType.FLOAT_VECTOR, dim=dim),
                FieldSchema(name="sparse", dtype=DataType.SPARSE_FLOAT_VECTOR),
                FieldSchema(name="file_path", dtype=DataType.VARCHAR, max_length=1024),
                FieldSchema(name="name", dtype=DataType.VARCHAR, max_length=1024),
                FieldSchema(name="start_line", dtype=DataType.INT64),
                FieldSchema(name="end_line", dtype=DataType.INT64),
                FieldSchema(
                    name="type",
                    dtype=DataType.VARCHAR,
                    max_length=256,
                    enable_analyzer=True,
                    analyzer_params=analyzer_params,
                    enable_match=True,
                ),
                FieldSchema(
                    name="_source_file",
                    dtype=DataType.VARCHAR,
                    max_length=1024,
                    enable_analyzer=True,
                    enable_match=True,
                    analyzer_params=analyzer_params,
                ),
            ]

            schema: CollectionSchema = CollectionSchema(
                fields=fields,
                description=description or "Optimized hybrid search collection",
                enable_dynamic_field=True,
            )

            # 컬렉션 생성
            logger.info(f"Creating collection: {collection_name}")
            self.client.create_collection(
                collection_name=collection_name,
                schema=schema,
                consistency_level="Strong",
            )

            # 인덱스 생성
            self._create_indexes(collection_name)

            logger.info(f"✅ Collection '{collection_name}' created successfully")
            return CollectionCreateResult(
                success=True,
                collection_name=collection_name,
                message=f"Collection '{collection_name}' created successfully",
                error=None,
            )

        except (CollectionAlreadyExistsError, Exception) as e:
            logger.error(f"Failed to create collection: {e}")
            return CollectionCreateResult(
                success=False,
                collection_name=collection_name,
                message=None,
                error=str(e),
            )

    def _create_indexes(self, collection_name: str) -> None:
        """
        컬렉션에 인덱스 생성 (내부 메서드)

        Args:
            collection_name: 컬렉션 이름
        """
        logger.info(f"Creating indexes for collection: {collection_name}")

        # 인덱스 파라미터 준비
        index_params = self.client.prepare_index_params()

        # Dense 벡터 인덱스
        index_params.add_index(
            field_name="dense",
            index_type="HNSW",
            metric_type="COSINE",
            params={"M": 16, "efConstruction": 256},
        )

        # Sparse 벡터 인덱스

        index_params.add_index(
            field_name="sparse",
            index_type="SPARSE_WAND",
            metric_type="IP",
            params={"drop_ratio_build": 0.2},
        )


        # 스칼라 필드 인덱스
        index_params.add_index(field_name="file_path")
        index_params.add_index(field_name="type")
        index_params.add_index(field_name="name")
        index_params.add_index(field_name="start_line")
        index_params.add_index(field_name="end_line")
        index_params.add_index(field_name="_source_file")


        # 인덱스 생성
        

        self.client.create_index(collection_name=collection_name, index_params=index_params)


        logger.info(f"✅ Indexes created for collection: {collection_name}")

    def delete_collection(self, collection_name: str) -> CollectionDeleteResult:
        """
        컬렉션 삭제

        Args:
            collection_name: 컬렉션 이름

        Returns:
            삭제 결과
        """
        try:
            # 존재 확인
            self.validate_exists(collection_name)

            # 삭제
            logger.info(f"Deleting collection: {collection_name}")
            self.client.drop_collection(collection_name)

            logger.info(f"✅ Collection '{collection_name}' deleted successfully")
            return CollectionDeleteResult(
                success=True,
                collection_name=collection_name,
                message=f"Collection '{collection_name}' deleted successfully",
                error=None,
            )

        except (CollectionNotFoundError, Exception) as e:
            logger.error(f"Failed to delete collection: {e}")
            return CollectionDeleteResult(
                success=False,
                collection_name=collection_name,
                message=None,
                error=str(e),
            )

    def list_collections(self) -> List[CollectionInfo]:
        """
        모든 컬렉션 목록 조회

        Returns:
            컬렉션 정보 리스트
        """
        try:
            MilvusConnectionManager.ensure_connection()

            collection_names: List[str] = self.client.list_collections()
            collections: List[CollectionInfo] = []

            for name in collection_names:
                try:
                    collection = Collection(name)
                    collection.load()

                    # 엔티티 수 조회
                    count_result = collection.query(expr="pk > 0", output_fields=["count(*)"])
                    count: int = count_result[0]["count(*)"] if count_result else 0

                    # 설명 가져오기
                    desc = collection.description if hasattr(collection, "description") else ""

                    collections.append(
                        CollectionInfo(name=name, num_entities=count, description=desc)
                    )

                except Exception as e:
                    logger.warning(f"Failed to get info for collection '{name}': {e}")
                    collections.append(
                        CollectionInfo(name=name, num_entities=0, description=f"Error: {e}")
                    )

            return collections

        except Exception as e:
            logger.error(f"Failed to list collections: {e}")
            return []

    def get_entity_count(self, collection_name: str) -> int:
        """
        컬렉션의 엔티티 수 조회

        Args:
            collection_name: 컬렉션 이름

        Returns:
            엔티티 수

        Raises:
            CollectionNotFoundError: 컬렉션이 없을 때
        """
        try:
            self.validate_exists(collection_name)
            MilvusConnectionManager.ensure_connection()

            collection = Collection(collection_name)
            collection.load()

            count_result = collection.query(expr="pk > 0", output_fields=["count(*)"])
            return count_result[0]["count(*)"] if count_result else 0

        except Exception as e:
            logger.error(f"Failed to get entity count: {e}")
            raise CollectionNotFoundError(f"Failed to get entity count: {e}") from e
        
    def delete_entities_by_source_files(
        self, collection_name: str, source_files: List[str]
    ) -> Dict[str, Any]:
        """
        _source_file 필드를 기준으로 특정 파일들에 해당하는 모든 엔티티를 삭제

        Args:
            collection_name: 컬렉션 이름
            source_files: 삭제할 엔티티들의 원본 파일명 리스트

        Returns:
            삭제 결과 딕셔너리
        """
        try:
            # 1. 컬렉션 존재 여부 확인
            self.validate_exists(collection_name)
            self.client.load_collection(collection_name=collection_name)

            # 2. 삭제할 파일 목록이 비어있으면 작업을 수행하지 않고 성공 반환
            if not source_files:
                logger.info(f"[{collection_name}] No source files provided for deletion. Skipping.")
                return {"success": True, "deleted_count": 0, "message": "No files to delete."}

            # 3. Milvus의 'IN' 연산자를 사용하는 필터 표현식 생성
            formatted_files = [f"'{f}'" for f in source_files]
            filter_expr = f"_source_file IN [{', '.join(formatted_files)}]"
            
            logger.info(f"[{collection_name}] Deleting entities with filter: {filter_expr}")

            # 4. 삭제 실행
            # MilvusClient.delete는 삭제된 pk 리스트 또는 MutationResult 객체를 반환합니다.
            delete_result = self.client.delete(
                collection_name=collection_name,
                filter=filter_expr,
            )
            
            # delete_result에서 삭제된 개수를 확인 (pymilvus 버전에 따라 다를 수 있음)
            deleted_count = delete_result.delete_count if hasattr(delete_result, 'delete_count') else -1

            logger.info(f"✅ [{collection_name}] Successfully deleted entities. Count: {deleted_count}")
            
            return {
                "success": True,
                "deleted_count": deleted_count,
                "message": f"Successfully deleted entities from {len(source_files)} source files.",
            }

        except (CollectionNotFoundError, Exception) as e:
            logger.error(f"[{collection_name}] Failed to delete entities: {e}")
            return {
                "success": False,
                "deleted_count": 0,
                "error": str(e),
            }
        finally:
            # 작업이 끝나면 컬렉션을 메모리에서 해제하여 리소스를 절약
            if self.exists(collection_name):
                logger.info(f"[{collection_name}] Releasing collection from memory.")
                self.client.release_collection(collection_name=collection_name)
