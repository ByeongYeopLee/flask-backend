import hashlib
import os
import pyodbc
from dotenv import load_dotenv

load_dotenv()

server = os.getenv('DB_SERVER')
database = os.getenv('DB_NAME')
username = os.getenv('DB_USERNAME')
password = os.getenv('DB_PASSWORD')
driver = '{ODBC Driver 17 for SQL Server}'

conn_string = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server};DATABASE={database};UID={username};PWD={password}"

try:
    conn = pyodbc.connect(conn_string)
    print("✅ 데이터베이스 연결 성공!")
    conn.close()
except Exception as e:
    print("❌ 데이터베이스 연결 실패:", e)
