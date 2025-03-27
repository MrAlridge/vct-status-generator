from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import declarative_base

# 从 config 模块导入配置好的数据库 URL
from .config import DATABASE_URL

# 创建 SQLAlchemy 引擎
# echo=True 会打印所有执行的 SQL 语句，便于调试，生产环境通常关闭 (echo=False)
engine = create_engine(DATABASE_URL, echo=True, future=True)

# 创建 SessionLocal 类，用于创建数据库会话
# expire_on_commit=False 防止在提交后访问对象时需要重新从数据库加载
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)

# 创建 Base 类，我们的 ORM 模型将继承这个类
Base = declarative_base()

# 数据库会话函数（与FastAPI/Flask一起使用）
def get_db():
    """
    数据库会话依赖项，用于 Web 框架。
    它会创建一个新的数据库会话，在请求处理完成后关闭它。
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 数据库初始化函数（表创建）
def init_db():
    """
    根据定义的 ORM 模型创建所有数据库表。
    """
    # !!! 在调用 create_all 之前导入所有模型 !!!
    from . import models # 这会导入 src/core/models.py

    print("正在初始化数据库...")
    # create_all 会查找所有继承自 Base 的类并创建对应的表
    Base.metadata.create_all(bind=engine)
    print("数据库初始化完成。")

# 你可以在这里添加一个简单的函数来测试连接
def test_connection():
    """尝试连接到数据库。"""
    try:
        # 尝试建立连接
        connection = engine.connect()
        print("数据库连接成功！")
        connection.close()
        return True
    except Exception as e:
        print(f"数据库连接失败: {e}")
        return False
    