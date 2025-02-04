import os
import pyodbc
from dotenv import load_dotenv


load_dotenv("templates/.env")
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

# 컬럼 크기 변경 SQL 실행
cursor.execute("ALTER TABLE [user] ALTER COLUMN password_hash VARCHAR(255);")

# 변경사항 반영
conn.commit()
print("Column updated successfully!")

# 연결 닫기
cursor.close()
conn.close()
