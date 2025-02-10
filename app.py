from flask import Flask, request, jsonify
from flask_restful import Api, Resource
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import os
from dotenv import load_dotenv
import pyodbc

# .env 파일 로드
load_dotenv()

server = os.getenv('DB_SERVER')
database = os.getenv('DB_NAME')
username = os.getenv('DB_USERNAME')
password = os.getenv('DB_PASSWORD')
driver = '{ODBC Driver 17 for SQL Server}'
port = 1433

# pyodbc 연결 인코딩 설정
pyodbc.pooling = False  # 한글 깨짐 방지
connection_string = f"DRIVER={driver};SERVER={server},{port};DATABASE={database};UID={username};PWD={password};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"

app = Flask(__name__)

# CORS 설정을 더 구체적으로 지정
CORS(app, resources={
    r"/*": {
        "origins": ["http://localhost:3000"],  # React Native 앱의 개발 서버 주소
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})

app.config['SQLALCHEMY_DATABASE_URI'] = f"mssql+pyodbc:///?odbc_connect={connection_string}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
api = Api(app)


# 모델 정의
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    nickname = db.Column(db.String(80), unique=True, nullable=False)
    birthyear = db.Column(db.Integer, nullable=False)  # 출생연도
    gender = db.Column(db.String(10), nullable=False)  # 성별

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


# 데이터베이스 테이블 생성 (첫 실행 시)
try:
    with app.app_context():
        db.create_all()
except Exception as e:
    print(f"Error creating database tables: {e}")


# 회원가입 API
class UserRegistration(Resource):
    def post(self):
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        nickname = data.get('nickname')
        birthyear = data.get('birthyear')  # 출생연도 (YYYY 형식)
        gender = data.get('gender')  # 성별

        # 필수 필드 검증
        if not all([username, password, nickname, birthyear, gender]):
            return {"message": "Missing required fields"}, 400

        # 중복된 사용자 이름이나 닉네임이 있는지 확인
        if User.query.filter_by(username=username).first():
            return {"message": "Username already exists"}, 400
        if User.query.filter_by(nickname=nickname).first():
            return {"message": "Nickname already exists"}, 400

        # 새 사용자 생성
        new_user = User(username=username, nickname=nickname, birthyear=birthyear, gender=gender)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        return {"message": "User created successfully"}, 201


# 로그인 API
class UserLogin(Resource):
    def post(self):
        data = request.get_json()
        user = User.query.filter_by(username=data['username']).first()

        if user and user.check_password(data['password']):
            return {
                "message": "Logged in successfully",
                "user_info": {
                    "username": user.username,
                    "nickname": user.nickname,
                    "birthyear": user.birthyear,
                    "gender": user.gender
                }
            }, 200
        return {"message": "Invalid username or password"}, 401


# RESTful API 리소스 추가
api.add_resource(UserRegistration, '/register')
api.add_resource(UserLogin, '/login')


# 응답 인코딩을 UTF-8로 설정
@app.after_request
def after_request(response):
    response.headers['Content-Type'] = 'application/json; charset=utf-8'
    return response


# 서버 실행
if __name__ == '__main__':
    app.run(debug=True)
