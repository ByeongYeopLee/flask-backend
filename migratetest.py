import os
import pyodbc
from dotenv import load_dotenv

load_dotenv()

# Azure SQL DB 연결 정보
server = os.getenv('DB_SERVER')
database = os.getenv('DB_NAME')
username = os.getenv('DB_USERNAME')
password = os.getenv('DB_PASSWORD')
driver = '{ODBC Driver 17 for SQL Server}'

# 연결 설정
conn = pyodbc.connect(
    f'DRIVER={driver};SERVER={server};PORT=1433;DATABASE={database};UID={username};PWD={password}'
)
cursor = conn.cursor()

try:
    # 기존 테이블 삭제
    cursor.execute("IF OBJECT_ID('user', 'U') IS NOT NULL DROP TABLE [user];")
    conn.commit()
    print("Existing table deleted successfully!")

    # 새로운 테이블 생성
    cursor.execute("""
        CREATE TABLE [user] (
            id INT IDENTITY(1,1) PRIMARY KEY,
            username NVARCHAR(80) NOT NULL UNIQUE,
            password_hash NVARCHAR(255) NOT NULL,
            nickname NVARCHAR(80) NOT NULL UNIQUE,
            birthyear INT NOT NULL,
            gender NVARCHAR(10) NOT NULL,
            marketing_consent BIT NOT NULL DEFAULT 0  -- 마케팅 수신 동의 여부 (기본값: 0)
        );
    """)
    conn.commit()
    print("New table created successfully!")

except Exception as e:
    print(f"Error: {e}")

# 연결 닫기
cursor.close()
conn.close()
