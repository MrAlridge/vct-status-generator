# src/core/database.py
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

# 从更新后的 config 模块导入
from src.core.config import load_config, get_database_url

logger = logging.getLogger(__name__)

# --- 加载配置并获取数据库 URL ---
# 在模块加载时执行一次，以确保 engine 和 SessionLocal 使用正确的配置
try:
    # 假设 manage.py 或其他入口点已经设置好环境以找到 config.yaml/.env
    # 或者 load_config 有合理的默认路径
    config = load_config()
    DATABASE_URL = get_database_url(config)
    logger.info(f"Database module initialized with URL: {DATABASE_URL[:DATABASE_URL.find('@') + 1]}... (Credentials Hidden)") # Log URL without creds
except Exception as e:
    logger.error(f"Failed to load config or determine database URL during module load: {e}", exc_info=True)
    # 设置一个无效的 URL 或 None，让后续使用时明确失败
    DATABASE_URL = None
    # 或者抛出异常，阻止应用启动？取决于你的错误处理策略
    # raise RuntimeError(f"Database could not be configured: {e}") from e

# --- 创建 SQLAlchemy Engine ---
# 根据 DATABASE_URL 是否成功获取来创建 Engine
if DATABASE_URL:
    # connect_args 用于 SQLite
    connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
    try:
        engine = create_engine(
            DATABASE_URL,
            # echo=True # 在开发时设为 True 可以看到 SQL 语句, 生产环境建议 False
            echo=False,
             connect_args=connect_args
        )
        logger.info("SQLAlchemy engine created successfully.")
    except Exception as e:
        logger.error(f"Failed to create SQLAlchemy engine with URL {DATABASE_URL}: {e}", exc_info=True)
        engine = None # 标记 engine 创建失败
else:
    logger.error("DATABASE_URL not configured. SQLAlchemy engine cannot be created.")
    engine = None

# --- 创建 SessionLocal 类 ---
# 仅当 engine 成功创建时才创建 SessionLocal
if engine:
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    logger.info("SQLAlchemy SessionLocal created.")
else:
    # 提供一个假的 SessionLocal 或 None，以便导入它的代码不会立即失败，
    # 但在尝试使用时会出错。
    logger.error("Engine not available. SessionLocal cannot be created.")
    def SessionLocal(): # Fake SessionLocal to raise error on use
        raise RuntimeError("Database engine not initialized. Cannot create session.")
    # Alternatively: SessionLocal = None

# --- 创建 Base 类 ---
# Base 类本身不依赖于 engine 或 session
Base = declarative_base()
logger.info("SQLAlchemy declarative base created.")

# --- 初始化数据库函数 (创建表) ---
def init_db(drop_all: bool = False):
    """
    使用当前的 engine 和 Base metadata 初始化数据库。
    可选地，先删除所有表。
    """
    if not engine:
        logger.error("Cannot initialize database: Engine is not configured.")
        print("错误：数据库引擎未配置，无法初始化。")
        return
    try:
        logger.info("Initializing database tables...")
        if drop_all:
            logger.warning("Dropping all tables...")
            Base.metadata.drop_all(bind=engine)
            logger.warning("All tables dropped.")
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully (or already exist).")
    except Exception as e:
        logger.error(f"Failed to initialize database tables: {e}", exc_info=True)
        print(f"数据库表初始化失败: {e}")

# --- (可选) FastAPI 依赖函数 ---
def get_db():
    """
    FastAPI dependency to get a DB session.
    确保在使用此函数前 SessionLocal 已成功创建。
    """
    if not callable(SessionLocal) or engine is None:
         # This path shouldn't be hit if engine/SessionLocal failed earlier,
         # but it's a safeguard.
         logger.error("Attempted to get DB session, but SessionLocal is not configured.")
         raise RuntimeError("Database is not configured.")

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()