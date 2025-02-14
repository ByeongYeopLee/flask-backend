from flask import Flask, request, jsonify
from flask_restful import Api, Resource
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import os
from dotenv import load_dotenv
import pyodbc
from datetime import datetime

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
        "origins": ["*"],  # 모든 출처 허용 (개발 환경용)
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
    marketing_consent = db.Column(db.Boolean, nullable=False, default=False)  # 마케팅 동의 필드 추가
    preferences = db.Column(db.String(500), nullable=True)  # JSON 문자열로 저장될 preferences

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_preferences(self):
        import json
        return json.loads(self.preferences) if self.preferences else []

    def set_preferences(self, preferences):
        import json
        self.preferences = json.dumps(preferences)

class TravelSchedule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # 외래키 (User 모델과 연결)
    title = db.Column(db.String(255), nullable=False)  # 여행 제목
    destination = db.Column(db.String(255), nullable=False)  # 여행지
    start_date = db.Column(db.Date, nullable=False)  # 시작 날짜
    end_date = db.Column(db.Date, nullable=False)  # 종료 날짜
    details = db.Column(db.Text, nullable=True)  # 여행 세부 일정 (JSON 가능)

    user = db.relationship('User', backref=db.backref('schedules', lazy=True))  # 관계 설정


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
        marketing_consent = bool(data.get('marketing_consent', 0))  # 0 또는 1을 boolean으로 변환
        preferences = data.get('preferences', [])  # 기본값 빈 리스트

        # 필수 필드 검증
        if not all([username, password, nickname, birthyear, gender]):
            return {"message": "Missing required fields"}, 400

        # 중복된 사용자 이름이나 닉네임이 있는지 확인
        if User.query.filter_by(username=username).first():
            return {"message": "Username already exists"}, 400
        if User.query.filter_by(nickname=nickname).first():
            return {"message": "Nickname already exists"}, 400

        # 새 사용자 생성
        new_user = User(
            username=username,
            nickname=nickname,
            birthyear=birthyear,
            gender=gender,
            marketing_consent=marketing_consent
        )
        new_user.set_password(password)
        new_user.set_preferences(preferences)
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
                    "gender": user.gender,
                    "marketing_consent": user.marketing_consent,
                    "preferences": user.get_preferences()
                }
            }, 200
        return {"message": "Invalid username or password"}, 401
    
# 사용자 정보 조회 및 수정 API
class UserProfile(Resource):
    def get(self, username):
        """특정 사용자 정보 조회"""
        user = User.query.filter_by(username=username).first()
        if not user:
            return {"message": "User not found"}, 404

        return {
            "username": user.username,
            "nickname": user.nickname,
            "birthyear": user.birthyear,
            "gender": user.gender,
            "marketing_consent": user.marketing_consent,
            "preferences": user.get_preferences()
        }, 200

    def put(self, username):
        """사용자 정보 수정"""
        user = User.query.filter_by(username=username).first()
        if not user:
            return {"message": "User not found"}, 404

        data = request.get_json()

        # 변경 가능한 필드만 업데이트
        if 'nickname' in data:
            if User.query.filter_by(nickname=data['nickname']).first():
                return {"message": "Nickname already exists"}, 400
            user.nickname = data['nickname']
        
        if 'birthyear' in data:
            user.birthyear = data['birthyear']
        
        if 'gender' in data:
            user.gender = data['gender']
        
        if 'marketing_consent' in data:
            user.marketing_consent = bool(data['marketing_consent'])

        if 'preferences' in data:
            user.set_preferences(data['preferences'])

        db.session.commit()
        return {"message": "User information updated successfully"}, 200

# 여행 일정 API
class TravelScheduleResource(Resource):
    def post(self):
        """여행 일정 추가"""
        data = request.get_json()
        username = data.get('username')  # 로그인된 사용자 정보
        user = User.query.filter_by(username=username).first()
        if not user:
            return {"message": "User not found"}, 404

        try:
            new_schedule = TravelSchedule(
                user_id=user.id,
                title=data['title'],
                destination=data['destination'],
                start_date=datetime.strptime(data['start_date'], "%Y-%m-%d").date(),
                end_date=datetime.strptime(data['end_date'], "%Y-%m-%d").date(),
                details=data.get('details', '')  # 여행 상세 정보 (선택 사항)
            )
            db.session.add(new_schedule)
            db.session.commit()
            return {"message": "Travel schedule created successfully", "schedule_id": new_schedule.id}, 201
        except Exception as e:
            return {"message": str(e)}, 400

    def get(self):
        """사용자의 여행 일정 조회"""
        username = request.args.get('username')
        user = User.query.filter_by(username=username).first()
        if not user:
            return {"message": "User not found"}, 404

        schedules = TravelSchedule.query.filter_by(user_id=user.id).all()
        return [{
            "id": schedule.id,
            "title": schedule.title,
            "destination": schedule.destination,
            "start_date": schedule.start_date.strftime("%Y-%m-%d"),
            "end_date": schedule.end_date.strftime("%Y-%m-%d"),
            "details": schedule.details
        } for schedule in schedules], 200


class TravelScheduleDetailResource(Resource):
    def get(self, schedule_id):
        """특정 여행 일정 조회 (로그인한 사용자만 자신의 일정 조회 가능)"""
        username = request.args.get('username')  # 로그인된 사용자 정보
        user = User.query.filter_by(username=username).first()

        if not user:
            return {"message": "User not found"}, 404

        schedule = TravelSchedule.query.get(schedule_id)

        if not schedule:
            return {"message": "Schedule not found"}, 404

        # 🔒 해당 일정이 로그인한 사용자의 일정인지 확인
        if schedule.user_id != user.id:
            return {"message": "Unauthorized access"}, 403

        return {
            "id": schedule.id,
            "title": schedule.title,
            "destination": schedule.destination,
            "start_date": schedule.start_date.strftime("%Y-%m-%d"),
            "end_date": schedule.end_date.strftime("%Y-%m-%d"),
            "details": schedule.details
        }, 200


    def delete(self, schedule_id):
        """여행 일정 삭제 (로그인한 사용자만 자신의 일정 삭제 가능)"""
        username = request.args.get('username')  # 로그인된 사용자 정보
        user = User.query.filter_by(username=username).first()

        if not user:
            return {"message": "User not found"}, 404

        schedule = TravelSchedule.query.get(schedule_id)

        if not schedule:
            return {"message": "Schedule not found"}, 404

        # 🔒 해당 일정이 로그인한 사용자의 일정인지 확인
        if schedule.user_id != user.id:
            return {"message": "Unauthorized access"}, 403

        db.session.delete(schedule)
        db.session.commit()
        return {"message": "Schedule deleted successfully"}, 200


# RESTful API 리소스 추가
api.add_resource(UserRegistration, '/register')
api.add_resource(UserLogin, '/login')
api.add_resource(UserProfile, '/user/<string:username>')
api.add_resource(TravelScheduleResource, '/schedule')  # 전체 일정 조회 및 추가
api.add_resource(TravelScheduleDetailResource, '/schedule/<int:schedule_id>')  # 특정 일정 조회 및 삭제

# 응답 인코딩을 UTF-8로 설정
@app.after_request
def after_request(response):
    response.headers['Content-Type'] = 'application/json; charset=utf-8'
    return response


# 서버 실행
if __name__ == '__main__':
    app.run(debug=True)
