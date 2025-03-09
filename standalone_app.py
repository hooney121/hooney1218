import sys
import json
import os
import random
from datetime import datetime, timedelta
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QHBoxLayout, QTabWidget, QPushButton, QLabel, 
                           QLineEdit, QComboBox, QScrollArea, QMessageBox,
                           QFrame, QSizePolicy)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont, QIcon, QPixmap, QColor, QPalette

# 애플리케이션 경로 관련 함수
def get_app_path():
    """실행 파일 또는 스크립트의 경로를 반환"""
    if getattr(sys, 'frozen', False):
        # 실행 파일로 실행 중인 경우
        return os.path.dirname(sys.executable)
    else:
        # 스크립트로 실행 중인 경우
        return os.path.dirname(os.path.abspath(__file__))

# 서버 기능 통합 (third.py에서 가져온 기능)
class StarbucksScheduler:
    def __init__(self):
        self.days = ["월", "화", "수", "목", "금", "토", "일"]
        self.shifts = {
            # 오픈조
            "오픈 쉬프트 (06:30-15:30)": {"start": "06:30", "end": "15:30", "type": "관리자", "hours": 9, "positions": ["점장", "부점장", "수퍼바이저"]},
            "오픈 바리스타 (06:30-14:30)": {"start": "06:30", "end": "14:30", "type": "바리스타", "hours": 8, "positions": ["바리스타"]},
            
            # 미들조
            "미들 쉬프트1 (09:00-16:30)": {"start": "09:00", "end": "16:30", "type": "관리자", "hours": 7.5, "positions": ["점장", "부점장", "수퍼바이저"]},
            "미들 쉬프트2 (09:30-17:00)": {"start": "09:30", "end": "17:00", "type": "관리자", "hours": 7.5, "positions": ["점장", "부점장", "수퍼바이저"]},
            
            # 마감조
            "마감 쉬프트 (13:00-22:00)": {"start": "13:00", "end": "22:00", "type": "관리자", "hours": 9, "positions": ["점장", "부점장", "수퍼바이저"]},
            "마감 바리스타1 (15:00-22:00)": {"start": "15:00", "end": "22:00", "type": "바리스타", "hours": 7, "positions": ["바리스타"]},
            "마감 바리스타2 (15:00-22:00)": {"start": "15:00", "end": "22:00", "type": "바리스타", "hours": 7, "positions": ["바리스타"]},
            
            # P 파트 타임
            "P 시프트 (08:00-12:30)": {"start": "08:00", "end": "12:30", "type": "P", "hours": 4.5, "positions": ["P"]},
            "P 시프트2 (10:00-14:30)": {"start": "10:00", "end": "14:30", "type": "P", "hours": 4.5, "positions": ["P"]},
            
            # 주말 전용
            "아침 바리스타/쉬프트 (08:00-15:00)": {"start": "08:00", "end": "15:00", "type": "all", "hours": 7, "positions": ["점장", "부점장", "수퍼바이저", "바리스타"]},
        }
        
        # 기본 파트너 데이터 구조
        self.partners = {
            "점장": [],
            "부점장": [],
            "수퍼바이저": [],
            "바리스타": [],
            "P": [],
            "15시간바리스타": []
        }
        
        # 파일에서 파트너 데이터 로드
        self.data_file = os.path.join(get_app_path(), "partners.json")
        self.load_partners()
        
    def load_partners(self):
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    self.partners = json.load(f)
            else:
                # 파일이 없는 경우 기본 파트너 구조 유지
                print(f"파트너 데이터 파일이 없습니다. 새 파일을 생성합니다: {self.data_file}")
                self.save_partners()  # 기본 구조로 파일 생성
        except Exception as e:
            print(f"파트너 데이터 로드 실패: {e}")
            # 오류 발생 시 기본 구조 유지
    
    def save_partners(self):
        try:
            # 파일 저장 전 디렉토리 확인
            directory = os.path.dirname(self.data_file)
            if directory and not os.path.exists(directory):
                os.makedirs(directory)
                
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(self.partners, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"파트너 데이터 저장 실패: {e}")
            # 오류 메시지 표시 (콘솔에만)
            # 사용자에게 오류 표시하려면 QMessageBox 사용 필요

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

                # P 시프트 (1-2명)
                p_partners = list(self.partners.get("P", []))
                if p_partners:
                    p_partner = random.choice(p_partners)
                    schedule[date_str]["shifts"]["P 시프트 (08:00-12:30)"].append(p_partner)
                    p_partners.remove(p_partner)
                    
                    if p_partners and random.choice([True, False]):
                        p_partner = random.choice(p_partners)
                        schedule[date_str]["shifts"]["P 시프트2 (10:00-14:30)"].append(p_partner)

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

            # 주말 스케줄
            else:
                # 주말은 다른 스케줄링 로직 적용
                all_partners = []
                for position in ["점장", "부점장", "수퍼바이저", "바리스타"]:
                    all_partners.extend(self.partners.get(position, []))
                
                # 근무 인원 결정 (토요일: 3-4명, 일요일: 2-3명)
                num_workers = 4 if day_name == "토" else 3
                num_workers = min(num_workers, len(all_partners))  # 가용 인원보다 많이 배정하지 않도록
                
                # 랜덤하게 인원 배정
                if all_partners:
                    selected_partners = random.sample(all_partners, num_workers)
                    for i, partner in enumerate(selected_partners):
                        if i == 0:  # 첫 번째 인원은 오픈 매니저
                            schedule[date_str]["shifts"]["오픈 쉬프트 (06:30-15:30)"].append(partner)
                        elif i == 1:  # 두 번째 인원은 마감 매니저
                            schedule[date_str]["shifts"]["마감 쉬프트 (13:00-22:00)"].append(partner)
                        else:  # 나머지는 중간 시간대
                            schedule[date_str]["shifts"]["아침 바리스타/쉬프트 (08:00-15:00)"].append(partner)
        
        return schedule

# UI 클래스
class StarbucksSchedulerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        # 스케줄러 인스턴스 생성
        try:
            self.scheduler = StarbucksScheduler()
        except Exception as e:
            QMessageBox.critical(self, "초기화 오류", f"애플리케이션 초기화 중 오류가 발생했습니다.\n오류 내용: {str(e)}")
            sys.exit(1)
        
        # 기본 창 설정
        self.setWindowTitle('스타벅스 스케줄러')
        self.setGeometry(100, 100, 1200, 800)
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f8f9fa;
            }
            QTabWidget::pane {
                border: 1px solid #ddd;
                border-radius: 8px;
                background: white;
            }
            QTabBar::tab {
                background: #f0f0f0;
                border: 1px solid #ddd;
                border-bottom: none;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                padding: 10px 20px;
                color: #555;
                font-weight: bold;
            }
            QTabBar::tab:selected {
                background: #00704A;
                color: white;
            }
            QPushButton {
                background-color: #00704A;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 15px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #005a3c;
            }
            QPushButton:pressed {
                background-color: #004a31;
            }
            QLineEdit, QComboBox {
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 8px;
                background: white;
            }
            QLineEdit:focus, QComboBox:focus {
                border: 1px solid #00704A;
            }
            QScrollArea {
                border: none;
                background: transparent;
            }
            QLabel {
                color: #333;
            }
        """)
        
        # 메인 위젯 설정
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        
        # 헤더 추가
        header = QWidget()
        header_layout = QHBoxLayout(header)
        header.setStyleSheet("background-color: #00704A; border-radius: 8px; margin-bottom: 10px;")
        
        # 스타벅스 로고 URL - 나중에 로컬 이미지로 대체 가능
        logo_label = QLabel()
        logo_label.setFixedSize(50, 50)
        logo_label.setStyleSheet("background-color: transparent;")
        # 로고 경로에 따라 수정 필요
        try:
            logo = QPixmap("starbucks_logo.png")
            logo_label.setPixmap(logo.scaled(50, 50, Qt.AspectRatioMode.KeepAspectRatio))
        except:
            # 로고가 없으면 텍스트로 대체
            logo_label.setText("☕")
            logo_label.setStyleSheet("color: white; font-size: 30px; background-color: transparent;")
        
        title_label = QLabel("스타벅스 스케줄러")
        title_label.setStyleSheet("color: white; font-size: 22px; font-weight: bold; background-color: transparent;")
        
        header_layout.addWidget(logo_label)
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        
        layout.addWidget(header)
        
        # 탭 위젯 생성
        tabs = QTabWidget()
        layout.addWidget(tabs)
        
        # 파트너 관리 탭
        partner_tab = QWidget()
        partner_layout = QVBoxLayout(partner_tab)
        partner_layout.setContentsMargins(20, 20, 20, 20)
        partner_layout.setSpacing(15)
        
        # 파트너 추가 섹션 - 카드 스타일
        add_section = QFrame()
        add_section.setFrameShape(QFrame.Shape.StyledPanel)
        add_section.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 8px;
                border: 1px solid #e0e0e0;
            }
        """)
        add_layout = QVBoxLayout(add_section)
        
        add_title = QLabel("파트너 추가")
        add_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #00704A; margin-bottom: 10px;")
        add_layout.addWidget(add_title)
        
        input_layout = QHBoxLayout()
        
        self.position_combo = QComboBox()
        self.position_combo.addItems(['점장', '부점장', '수퍼바이저', '바리스타', 'P', '15시간바리스타'])
        self.position_combo.setFixedHeight(38)
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText('파트너 이름')
        self.name_input.setFixedHeight(38)
        self.name_input.returnPressed.connect(self.add_partner)
        
        add_button = QPushButton('추가')
        add_button.setFixedHeight(38)
        add_button.clicked.connect(self.add_partner)
        
        input_layout.addWidget(self.position_combo, 1)
        input_layout.addWidget(self.name_input, 2)
        input_layout.addWidget(add_button, 1)
        
        add_layout.addLayout(input_layout)
        partner_layout.addWidget(add_section)
        
        # 파트너 목록 섹션 - 카드 스타일
        partner_list_card = QFrame()
        partner_list_card.setFrameShape(QFrame.Shape.StyledPanel)
        partner_list_card.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 8px;
                border: 1px solid #e0e0e0;
            }
        """)
        partner_list_layout = QVBoxLayout(partner_list_card)
        
        list_title = QLabel("파트너 목록")
        list_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #00704A; margin-bottom: 10px;")
        partner_list_layout.addWidget(list_title)
        
        # 파트너 목록 스크롤 영역
        self.partner_list = QWidget()
        self.partner_list_layout = QVBoxLayout(self.partner_list)
        self.partner_list_layout.setSpacing(10)
        
        scroll = QScrollArea()
        scroll.setWidget(self.partner_list)
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
            }
        """)
        
        partner_list_layout.addWidget(scroll)
        partner_layout.addWidget(partner_list_card)
        
        # 스케줄 탭
        schedule_tab = QWidget()
        schedule_layout = QVBoxLayout(schedule_tab)
        schedule_layout.setContentsMargins(20, 20, 20, 20)
        schedule_layout.setSpacing(15)
        
        # 스케줄 제어 섹션 - 카드 스타일
        control_section = QFrame()
        control_section.setFrameShape(QFrame.Shape.StyledPanel)
        control_section.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 8px;
                border: 1px solid #e0e0e0;
            }
        """)
        control_layout = QVBoxLayout(control_section)
        
        control_title = QLabel("스케줄 관리")
        control_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #00704A; margin-bottom: 10px;")
        control_layout.addWidget(control_title)
        
        refresh_button = QPushButton('스케줄 새로 생성')
        refresh_button.setFixedHeight(38)
        refresh_button.setIcon(QIcon.fromTheme("view-refresh"))
        refresh_button.clicked.connect(self.refresh_schedule)
        control_layout.addWidget(refresh_button)
        
        schedule_layout.addWidget(control_section)
        
        # 스케줄 표시 영역 - 카드 스타일
        schedule_card = QFrame()
        schedule_card.setFrameShape(QFrame.Shape.StyledPanel)
        schedule_card.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 8px;
                border: 1px solid #e0e0e0;
            }
        """)
        schedule_card_layout = QVBoxLayout(schedule_card)
        
        card_title = QLabel("주간 스케줄")
        card_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #00704A; margin-bottom: 10px;")
        schedule_card_layout.addWidget(card_title)
        
        # 스케줄 목록 스크롤 영역
        self.schedule_widget = QWidget()
        self.schedule_layout = QVBoxLayout(self.schedule_widget)
        self.schedule_layout.setSpacing(15)
        
        schedule_scroll = QScrollArea()
        schedule_scroll.setWidget(self.schedule_widget)
        schedule_scroll.setWidgetResizable(True)
        schedule_scroll.setStyleSheet("""
            QScrollArea {
                border: none;
            }
        """)
        
        schedule_card_layout.addWidget(schedule_scroll)
        schedule_layout.addWidget(schedule_card)
        
        # 탭 추가
        tabs.addTab(partner_tab, '파트너 관리')
        tabs.addTab(schedule_tab, '스케줄')
        
        # 초기 데이터 로드
        self.load_partners()
        self.load_schedule()

    def add_partner(self):
        position = self.position_combo.currentText()
        name = self.name_input.text().strip()
        
        if not name:
            QMessageBox.warning(self, '경고', '파트너 이름을 입력해주세요.')
            return
            
        # 파트너 추가
        if position not in self.scheduler.partners:
            self.scheduler.partners[position] = []
        
        if name not in self.scheduler.partners[position]:
            self.scheduler.partners[position].append(name)
            try:
                self.scheduler.save_partners()
                self.load_partners()
                self.name_input.clear()
            except Exception as e:
                QMessageBox.warning(self, '오류', f'파트너 정보 저장 중 오류가 발생했습니다.\n오류 내용: {str(e)}')
        else:
            QMessageBox.warning(self, '경고', '이미 존재하는 파트너입니다.')

    def load_partners(self):
        try:
            self.update_partner_list(self.scheduler.partners)
        except Exception as e:
            QMessageBox.warning(self, '오류', f'파트너 목록 로드 중 오류가 발생했습니다.\n오류 내용: {str(e)}')

    def update_partner_list(self, partners):
        # 기존 위젯 삭제
        for i in reversed(range(self.partner_list_layout.count())): 
            self.partner_list_layout.itemAt(i).widget().setParent(None)
        
        # 각 포지션별 파트너 표시
        for position in ['점장', '부점장', '수퍼바이저', '바리스타', 'P', '15시간바리스타']:
            if position in partners and partners[position]:
                # 포지션 카드
                position_card = QFrame()
                position_card.setFrameShape(QFrame.Shape.StyledPanel)
                
                # 포지션별 색상 설정
                position_colors = {
                    '점장': '#00704A',
                    '부점장': '#1e88e5',
                    '수퍼바이저': '#7cb342',
                    '바리스타': '#ff9800',
                    'P': '#e91e63',
                    '15시간바리스타': '#9c27b0'
                }
                
                border_color = position_colors.get(position, '#00704A')
                
                position_card.setStyleSheet(f"""
                    QFrame {{
                        background-color: white;
                        border-left: 4px solid {border_color};
                        border-radius: 4px;
                        padding: 8px;
                        margin: 5px 0;
                    }}
                """)
                
                position_layout = QVBoxLayout(position_card)
                position_layout.setContentsMargins(10, 10, 10, 10)
                
                # 포지션 레이블
                position_label = QLabel(f'{position}')
                position_label.setStyleSheet(f"font-weight: bold; color: {border_color}; font-size: 14px;")
                position_layout.addWidget(position_label)
                
                # 파트너 목록
                for partner in partners[position]:
                    partner_widget = QWidget()
                    partner_layout = QHBoxLayout(partner_widget)
                    partner_layout.setContentsMargins(10, 5, 10, 5)
                    
                    name_label = QLabel(partner)
                    partner_layout.addWidget(name_label)
                    
                    delete_button = QPushButton('삭제')
                    delete_button.setFixedWidth(60)
                    delete_button.setStyleSheet("""
                        QPushButton {
                            background-color: #f44336;
                            padding: 5px;
                        }
                        QPushButton:hover {
                            background-color: #d32f2f;
                        }
                    """)
                    delete_button.clicked.connect(
                        lambda checked, p=partner, pos=position: self.delete_partner(p, pos))
                    partner_layout.addWidget(delete_button)
                    
                    position_layout.addWidget(partner_widget)
                
                self.partner_list_layout.addWidget(position_card)

    def delete_partner(self, partner, position):
        if position in self.scheduler.partners and partner in self.scheduler.partners[position]:
            self.scheduler.partners[position].remove(partner)
            try:
                self.scheduler.save_partners()
                self.load_partners()
            except Exception as e:
                QMessageBox.warning(self, '오류', f'파트너 삭제 중 오류가 발생했습니다.\n오류 내용: {str(e)}')

    def load_schedule(self):
        schedule = self.scheduler.get_schedule()
        self.update_schedule_view(schedule)

    def refresh_schedule(self):
        self.load_schedule()

    def update_schedule_view(self, schedule):
        # 기존 스케줄 위젯 삭제
        for i in reversed(range(self.schedule_layout.count())): 
            self.schedule_layout.itemAt(i).widget().setParent(None)
        
        # 각 날짜별 스케줄 표시
        for date, day_schedule in schedule.items():
            date_card = QFrame()
            date_card.setFrameShape(QFrame.Shape.StyledPanel)
            date_card.setStyleSheet("""
                QFrame {
                    background-color: white;
                    border-radius: 8px;
                    margin: 5px 0;
                    border: 1px solid #e0e0e0;
                }
            """)
            
            date_layout = QVBoxLayout(date_card)
            date_layout.setContentsMargins(15, 15, 15, 15)
            date_layout.setSpacing(10)
            
            # 날짜 헤더
            day_colors = {
                "월": "#4285F4", "화": "#EA4335", "수": "#FBBC05", 
                "목": "#34A853", "금": "#8F9091", "토": "#0066CC", "일": "#D50000"
            }
            day_color = day_colors.get(day_schedule['day_name'], "#333333")
            
            date_header = QWidget()
            date_header_layout = QHBoxLayout(date_header)
            date_header_layout.setContentsMargins(0, 0, 0, 0)
            
            date_label = QLabel(f"{date}")
            date_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #333;")
            
            day_label = QLabel(f"{day_schedule['day_name']}")
            day_label.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {day_color}; margin-left: 5px;")
            
            date_header_layout.addWidget(date_label)
            date_header_layout.addWidget(day_label)
            date_header_layout.addStretch()
            
            date_layout.addWidget(date_header)
            
            # 구분선
            separator = QFrame()
            separator.setFrameShape(QFrame.Shape.HLine)
            separator.setStyleSheet("background-color: #e0e0e0;")
            date_layout.addWidget(separator)
            
            shifts = day_schedule['shifts']
            
            # 시프트 섹션 - 카드 스타일로 표시
            shift_sections = [
                # 제목, 배경색, 테두리색, 시프트 목록
                ("오픈 출근자", "#e8f5e9", "#43a047", [
                    ("관리자", "오픈 쉬프트 (06:30-15:30)"),
                    ("바리스타", "오픈 바리스타 (06:30-14:30)")
                ]),
                ("미들 출근자", "#fff8e1", "#ffb300", [
                    ("관리자", ["미들 쉬프트1 (09:00-16:30)", "미들 쉬프트2 (09:30-17:00)"]),
                    ("P", ["P 시프트 (08:00-12:30)", "P 시프트2 (10:00-14:30)"])
                ]),
                ("마감 출근자", "#ffebee", "#e53935", [
                    ("관리자", "마감 쉬프트 (13:00-22:00)"),
                    ("바리스타", ["마감 바리스타1 (15:00-22:00)", "마감 바리스타2 (15:00-22:00)"])
                ])
            ]
            
            # 주말인 경우 추가 섹션
            if day_schedule['day_name'] in ["토", "일"]:
                shift_sections.append(
                    ("주말 추가 출근자", "#e8eaf6", "#3f51b5", [
                        ("추가 인원", "아침 바리스타/쉬프트 (08:00-15:00)")
                    ])
                )
            
            for title, bg_color, border_color, shift_groups in shift_sections:
                has_shifts = False
                
                # 시프트 섹션 컨테이너
                section_card = QFrame()
                section_card.setFrameShape(QFrame.Shape.StyledPanel)
                section_card.setStyleSheet(f"""
                    QFrame {{
                        background-color: {bg_color};
                        border-left: 4px solid {border_color};
                        border-radius: 4px;
                        padding: 8px;
                    }}
                """)
                
                section_layout = QVBoxLayout(section_card)
                section_layout.setContentsMargins(10, 10, 10, 10)
                section_layout.setSpacing(8)
                
                # 섹션 제목
                section_title = QLabel(title)
                section_title.setStyleSheet(f"font-weight: bold; color: {border_color}; font-size: 14px;")
                section_layout.addWidget(section_title)
                
                # 각 직무별 시프트
                for role, shift_keys in shift_groups:
                    if not isinstance(shift_keys, list):
                        shift_keys = [shift_keys]
                    
                    partners_with_times = []
                    for shift_key in shift_keys:
                        if shifts[shift_key]:
                            has_shifts = True
                            shift_time = shift_key.split('(')[1].split(')')[0]
                            for partner in shifts[shift_key]:
                                partners_with_times.append(f"{partner} ({shift_time})")
                    
                    if partners_with_times:
                        role_layout = QHBoxLayout()
                        role_label = QLabel(f"{role}:")
                        role_label.setStyleSheet("font-weight: bold;")
                        role_label.setFixedWidth(70)
                        
                        partners_label = QLabel(", ".join(partners_with_times))
                        partners_label.setWordWrap(True)
                        
                        role_layout.addWidget(role_label)
                        role_layout.addWidget(partners_label)
                        section_layout.addLayout(role_layout)
                
                # 시프트가 있는 경우에만 추가
                if has_shifts:
                    date_layout.addWidget(section_card)
            
            self.schedule_layout.addWidget(date_card)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    # 앱 스타일 설정
    app.setStyle('Fusion')
    
    window = StarbucksSchedulerApp()
    window.show()
    sys.exit(app.exec()) 