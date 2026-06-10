# 数据库连接（启动时自动建库建表）
import os

from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# 测试模式：使用内存 SQLite，避免依赖 MySQL
TESTING = os.environ.get("PYTEST_RUNNING") == "1"

USER = "root"
PASSWORD = "Wj686866"
HOST = "localhost"
PORT = 3306
DB_NAME = "smart_posture"

if TESTING:
    SQLALCHEMY_DATABASE_URL = "sqlite:///./test_tmp.db"
    engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
else:
    def ensure_database():
        url = f"mysql+pymysql://{USER}:{PASSWORD}@{HOST}:{PORT}"
        eng = create_engine(url, pool_pre_ping=True)
        with eng.connect() as conn:
            conn.execute(text(f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}` "
                              "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"))
            conn.commit()
        eng.dispose()

    ensure_database()
    SQLALCHEMY_DATABASE_URL = f"mysql+pymysql://{USER}:{PASSWORD}@{HOST}:{PORT}/{DB_NAME}"
    engine = create_engine(SQLALCHEMY_DATABASE_URL, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
