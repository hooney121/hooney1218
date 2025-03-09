from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
from datetime import datetime, timedelta
import json
import os
import random

app = Flask(__name__)
CORS(app)  # 모바일 앱에서의 API 접근 허용

# 파트너 데이터를 저장할 파일 경로
PARTNERS_FILE = 'partners.json'

class StarbucksScheduler:
    def __init__(self):
        self.shifts = {
            # 오픈조 (관리자 1명, 바리스타 1명)
            "오픈 쉬프트 (06:30-15:30)": {"start": "06:30", "end": "15:30", "type": "관리자", "hours": 9, "positions": ["점장", "부점장", "수퍼바이저"]},
            "오픈 바리스타 (06:30-14:30)": {"start": "06:30", "end": "14:30", "type": "바리스타", "hours": 8},
            
            # 미들조
            "미들 쉬프트1 (09:00-16:30)": {"start": "09:00", "end": "16:30", "type": "관리자", "hours": 7.5, "positions": ["점장", "부점장", "수퍼바이저"]},
            "미들 쉬프트2 (09:30-17:00)": {"start": "09:30", "end": "17:00", "type": "관리자", "hours": 7.5, "positions": ["점장", "부점장", "수퍼바이저"]},
            
            # 마감조 (관리자 1명, 바리스타 2명)
            "마감 쉬프트 (13:00-22:00)": {"start": "13:00", "end": "22:00", "type": "관리자", "hours": 9, "positions": ["점장", "부점장", "수퍼바이저"]},
            "마감 바리스타1 (15:00-22:00)": {"start": "15:00", "end": "22:00", "type": "바리스타", "hours": 7},
            "마감 바리스타2 (15:00-22:00)": {"start": "15:00", "end": "22:00", "type": "바리스타", "hours": 7},
            
            # P 시프트 (4.5시간)
            "P 시프트 (08:00-12:30)": {"start": "08:00", "end": "12:30", "type": "P", "hours": 4.5},
            "P 시프트2 (10:00-14:30)": {"start": "10:00", "end": "14:30", "type": "P", "hours": 4.5},
            
            # 주말 추가 시프트
            "아침 바리스타/쉬프트 (08:00-15:00)": {"start": "08:00", "end": "15:00", "type": "공용", "hours": 7}
        }
        self.days = ["월", "화", "수", "목", "금", "토", "일"]
        self.positions = ["점장", "부점장", "수퍼바이저", "바리스타", "P", "15시간바리스타"]
        self.load_partners()

    def load_partners(self):
        try:
            if os.path.exists(PARTNERS_FILE):
                with open(PARTNERS_FILE, 'r', encoding='utf-8') as f:
                    self.partners = json.load(f)
            else:
                self.partners = {
                    "점장": [],
                    "부점장": [],
                    "수퍼바이저": [],
                    "바리스타": [],
                    "P": [],
                    "15시간바리스타": []
                }
        except Exception as e:
            print(f"파트너 정보 로딩 중 오류 발생: {str(e)}")
            self.partners = {
                "점장": [],
                "부점장": [],
                "수퍼바이저": [],
                "바리스타": [],
                "P": [],
                "15시간바리스타": []
            }

    def save_partners(self):
        try:
            with open(PARTNERS_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.partners, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"파트너 정보 저장 중 오류 발생: {str(e)}")

    def get_schedule(self):
        schedule = {}
        today = datetime.now()
        
        # 파트너가 비어있는지 확인
        total_partners = sum(len(partners) for partners in self.partners.values())
        if total_partners == 0:
            return {}

        # 바리스타 긴 시간 근무 카운트 초기화
        barista_long_shifts = {}  # 각 바리스타의 긴 시간 근무 횟수를 추적
        for barista in self.partners.get("바리스타", []):
            barista_long_shifts[barista] = 0

        # 일주일 시간표 생성
        for i in range(7):
            date = today + timedelta(days=i)
            date_str = date.strftime('%Y-%m-%d')
            day_name = self.days[date.weekday()]
            
            # 각 날짜별 기본 구조 생성
            schedule[date_str] = {
                "day_name": day_name,
                "shifts": {}
            }

            # 모든 시프트 초기화
            for shift_name in self.shifts:
                schedule[date_str]["shifts"][shift_name] = []

            # 관리자 풀 생성
            managers = []
            for position in ["점장", "부점장", "수퍼바이저"]:
                managers.extend(self.partners.get(position, []))
            
            # 바리스타 풀 생성
            baristas = list(self.partners.get("바리스타", []))

            # 평일 스케줄
            if day_name not in ["토", "일"]:
                # 오픈 (관리자 1명, 바리스타 1명)
                if managers:
                    manager = random.choice(managers)
                    schedule[date_str]["shifts"]["오픈 쉬프트 (06:30-15:30)"].append(manager)
                    managers.remove(manager)

                # 오픈 바리스타
                if baristas:
                    # 긴 시간 근무가 3일 미만인 바리스타만 선택
                    available_baristas = [b for b in baristas if barista_long_shifts.get(b, 0) < 3]
                    if available_baristas:
                        barista = random.choice(available_baristas)
                        schedule[date_str]["shifts"]["오픈 바리스타 (06:30-14:30)"].append(barista)
                        baristas.remove(barista)
                        barista_long_shifts[barista] = barista_long_shifts.get(barista, 0) + 1

                # 미들 출근 (1-2명)
                if managers:
                    manager = random.choice(managers)
                    schedule[date_str]["shifts"]["미들 쉬프트1 (09:00-16:30)"].append(manager)
                    managers.remove(manager)

                    if managers and random.choice([True, False]):
                        manager = random.choice(managers)
                        schedule[date_str]["shifts"]["미들 쉬프트2 (09:30-17:00)"].append(manager)
                        managers.remove(manager)

                # 마감 (관리자 1명, 바리스타 2명)
                if managers:
                    manager = random.choice(managers)
                    schedule[date_str]["shifts"]["마감 쉬프트 (13:00-22:00)"].append(manager)
                    managers.remove(manager)

                # 마감 바리스타 2명
                if baristas:
                    # 긴 시간 근무가 3일 미만인 바리스타만 선택
                    available_baristas = [b for b in baristas if barista_long_shifts.get(b, 0) < 3]
                    if available_baristas:
                        barista = random.choice(available_baristas)
                        schedule[date_str]["shifts"]["마감 바리스타1 (15:00-22:00)"].append(barista)
                        baristas.remove(barista)
                        barista_long_shifts[barista] = barista_long_shifts.get(barista, 0) + 1

                        available_baristas = [b for b in baristas if barista_long_shifts.get(b, 0) < 3]
                        if available_baristas:
                            barista = random.choice(available_baristas)
                            schedule[date_str]["shifts"]["마감 바리스타2 (15:00-22:00)"].append(barista)
                            baristas.remove(barista)
                            barista_long_shifts[barista] = barista_long_shifts.get(barista, 0) + 1

                # P 시프트 배정
                p_partners = list(self.partners.get("P", []))
                if p_partners:
                    # P 시프트 1 (오전)
                    if not schedule[date_str]["shifts"]["P 시프트 (08:00-12:30)"]:
                        p_partner = random.choice(p_partners)
                        schedule[date_str]["shifts"]["P 시프트 (08:00-12:30)"].append(p_partner)
                        p_partners.remove(p_partner)

                    # P 시프트 2 (오후)
                    if p_partners and not schedule[date_str]["shifts"]["P 시프트2 (10:00-14:30)"]:
                        p_partner = random.choice(p_partners)
                        schedule[date_str]["shifts"]["P 시프트2 (10:00-14:30)"].append(p_partner)

            # 주말 스케줄
            else:
                # 주말 추가 시프트 배정
                available_partners = managers + baristas  # P 파트너는 제외
                if available_partners and not schedule[date_str]["shifts"]["아침 바리스타/쉬프트 (08:00-15:00)"]:
                    partner = random.choice(available_partners)
                    schedule[date_str]["shifts"]["아침 바리스타/쉬프트 (08:00-15:00)"].append(partner)

        return schedule

# 전역 스케줄러 인스턴스 생성
scheduler = StarbucksScheduler()

@app.route('/')
def index():
    return render_template('third_schedule.html', 
                         partners=scheduler.partners,
                         positions=scheduler.positions)

@app.route('/api/schedule')
def get_schedule():
    return jsonify(scheduler.get_schedule())

@app.route('/api/partners', methods=['GET', 'POST'])
def manage_partners():
    if request.method == 'POST':
        data = request.get_json()
        scheduler.partners = data['partners']
        scheduler.save_partners()
        return jsonify({"status": "success"})
    return jsonify(scheduler.partners)

@app.route('/api/partners/<position>/<name>', methods=['DELETE'])
def delete_partner(position, name):
    if position in scheduler.partners:
        if name in scheduler.partners[position]:
            scheduler.partners[position].remove(name)
            scheduler.save_partners()
            return jsonify({"status": "success"})
    return jsonify({"status": "error", "message": "파트너를 찾을 수 없습니다."}), 404

if __name__ == '__main__':
    print("API 서버를 시작합니다... http://localhost:5000")
    app.run(host='0.0.0.0', debug=True, port=5000) 