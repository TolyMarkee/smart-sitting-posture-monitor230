# 数据库连接（启动时自动建库建表）

from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

USER = "root"
PASSWORD = "Wj686866"
HOST = "localhost"
PORT = 3306
DB_NAME = "smart_posture"

# 1. 先连接 MySQL（不指定数据库），自动创建数据库
def ensure_database():
    url = f"mysql+pymysql://{USER}:{PASSWORD}@{HOST}:{PORT}"
    engine = create_engine(url, pool_pre_ping=True)
    with engine.connect() as conn:
        conn.execute(text(f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}` "
                          "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"))
        conn.commit()
    engine.dispose()

# 2. 执行建库
ensure_database()

# 3. 连接到目标数据库
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
