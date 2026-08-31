"""
应用配置模块。

为什么单独抽 config？
- 把「环境变量 / 默认值」集中管理，业务代码只 import settings，不直接读 os.environ
- 阶段 2 起 ingestion、retrieval 都会复用这里的模型路径、Chroma 路径
"""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# rag-backend/ 根目录（app/ 的上一级）
BACKEND_ROOT = Path(__file__).resolve().parent.parent

# ModelScope 下载后的默认本地路径
DEFAULT_LOCAL_EMBEDDING = (
    BACKEND_ROOT / "data/models/models/Xorbits--bge-m3/snapshots/master"
)
DEFAULT_LOCAL_RERANKER = (
    BACKEND_ROOT / "data/models/models/Xorbits--bge-reranker-v2-m3/snapshots/master"
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # LLM（阶段 4）
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com/v1"
    llm_model: str = "deepseek-chat"
    retrieval_confidence_min: float = -5.0  # rerank 分阈值；无结果时仍走 fallback

    # CORS（逗号分隔，* 表示允许所有）
    cors_origins: str = "*"

    # Embedding
    embedding_model: str = "BAAI/bge-m3"

    # Chroma
    chroma_persist_dir: str = "./data/chroma"
    chroma_collection: str = "blog_chunks"

    # 博客数据源（相对于 rag-backend/ 或绝对路径）
    posts_dir: str = "../_posts"

    # 分块参数
    chunk_size: int = 512
    chunk_overlap: int = 64

    # 检索（阶段 3）
    retrieval_top_k: int = 5
    retrieval_candidate_k: int = 15
    hybrid_rrf_k: int = 60
    rerank_batch_size: int = 8
    reranker_model: str = "BAAI/bge-reranker-v2-m3"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = True

    @property
    def chroma_path(self) -> Path:
        """Chroma 持久化绝对路径。"""
        p = Path(self.chroma_persist_dir)
        return p if p.is_absolute() else BACKEND_ROOT / p

    @property
    def embedding_model_path(self) -> str:
        """Embedding 模型路径；优先本地，避免不必要的联网下载。"""
        p = Path(self.embedding_model)
        resolved = p if p.is_absolute() else BACKEND_ROOT / p
        if resolved.is_dir() and (resolved / "config.json").exists():
            return str(resolved)

        if DEFAULT_LOCAL_EMBEDDING.is_dir() and (
            DEFAULT_LOCAL_EMBEDDING / "model.safetensors"
        ).exists():
            return str(DEFAULT_LOCAL_EMBEDDING)

        return self.embedding_model

    @property
    def embedding_is_local(self) -> bool:
        return Path(self.embedding_model_path).is_dir()

    @property
    def reranker_model_path(self) -> str:
        """Reranker 模型路径；优先本地。"""
        p = Path(self.reranker_model)
        resolved = p if p.is_absolute() else BACKEND_ROOT / p
        if resolved.is_dir() and (resolved / "config.json").exists():
            return str(resolved)

        if DEFAULT_LOCAL_RERANKER.is_dir() and (
            (DEFAULT_LOCAL_RERANKER / "model.safetensors").exists()
            or (DEFAULT_LOCAL_RERANKER / "pytorch_model.bin").exists()
        ):
            return str(DEFAULT_LOCAL_RERANKER)

        return self.reranker_model

    @property
    def reranker_is_local(self) -> bool:
        return Path(self.reranker_model_path).is_dir()

    @property
    def posts_path(self) -> Path:
        p = Path(self.posts_dir)
        return p if p.is_absolute() else BACKEND_ROOT / p


settings = Settings()
