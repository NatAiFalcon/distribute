"""

--- 작성일 :2024.05.03 송인용 ---

도커 컨테이너가 보니까 죽어 있다.
로그상으로는 별 문제가 없던데 일단 적어도 컨테이너가 돌아가는동안은 수집은 문제 없으니 사용하다가 언제 메모리 이슈라도 발생하는건지 체크해봐야한다.
기존 OpenARK 연동한 footprint도 시간 지나면 죽길래 이번 프젝에서 별도로 만들어서 사용했던것도 있는데, 어쩌면 갑자기 죽는 이유 분석하다보면 기존 footprint 돌연사 문제도 해결 가능할거 같다.

--- 작성일 :2024.04.30 송인용 ---

해당 코드는 24.04.30 부터 움직이는 UWB tag 정보를 계속 수집하기 위해 Docker Container로 돌아가도록 함

--- 작성일 :2024.04.29 송인용 ---

웹소켓 이벤트 처리기:
on_message: 서버로부터 메시지를 받으면 JSON 형태로 파싱하고, 태그 ID 및 위치 데이터(X, Y 좌표)를 추출하여 처리한다
on_error: 웹소켓 에러 발생 시 에러 메시지를 출력한다.
on_close: 웹소켓 연결이 종료되면 자동으로 재연결을 시도한다.
on_open: 웹소켓 연결이 성공하면 서버에 데이터 구독 요청을 인증키랑 함께 보낸다.

스케줄링 및 재연결 관리:
ensure_scheduler_running: 스케줄러가 활성 상태인지 확인하고 필요하면 시작합니다.
start_scheduler: 일정 시간 간격으로 평균을 계산하는 타이머를 설정합니다.
reconnect 및 run_forever: 웹소켓 연결이 끊기거나 에러가 발생했을 때 자동으로 재연결을 시도합니다.

데이터 관리 및 평균 계산:

평균 필터 테스트로 calculate_average 메서드를 호출하여 저장된 데이터의 평균을 계산하고, 평균에서 벗어나는 이상치를 제거하고 이때 numpy를 사용하여 평균과 표준편차를 계산하는 작업을 같이 구현해서 사용해봤다.
근데 그렇게 유의미한거 같지도 않고 빠르게 EKF 작업으로 넘어갈려고 그 이상 개발은 진행하지 않았다.

"""

import websocket
import time
import json
from collections import defaultdict # 일반 dict 가 달리 키가 없으면 자동 생성
import threading
import numpy as np
import os
import signal
from dotenv import load_dotenv
"""
데이터 처리 로직은 UWB_gateway로 이전, 해당 코드는 오르지 데이터 적재만

"""

load_dotenv()

class SewioWebSocketClient_v2:

    def __init__(self, url, data_callback=None):
        config_path = os.getenv('CONFIG_PATH', 'config.json')
        with open(config_path, 'r') as file:
            self.config = json.load(file)
        self.url = url
        self.reconnect_delay = os.getenv('RECONNECT_DELAY') # 재연결 시도 간격(초)
        self.lock = threading.Lock()
        self.data_callback = data_callback # DB 저장용 콜백함수
        self.running = True

        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

    def signal_handler(self, sig, frame):
        print('Signal received:', sig)
        self.stop()

    def on_message(self, ws, message):


        data = json.loads(message)

        tag_id = data["body"]["id"]
        posX = float(data["body"]["datastreams"][0]["current_value"].replace('%', ''))
        posY = float(data["body"]["datastreams"][1]["current_value"].replace('%', ''))
        timestamp = data["body"]["datastreams"][0]["at"]
                # extended_tag_position 존재 여부 확인 및 처리
        if "extended_tag_position" in data["body"]:
            anchor_info = json.dumps(data["body"]["extended_tag_position"])
        else:
            anchor_info = json.dumps({})

        #print(f"posX : {posX}, posY : {posY}") ###
        # 좌표를 담는 코드
        temp_filename = "../shared/temp" + str(tag_id)
        f = open(temp_filename + ".txt", 'w')
        data = f"position_{posX}_{posY}_tagid_{tag_id}"
        f.write(data)
        f.close()

        self.data_callback(tag_id, posX, posY, timestamp, anchor_info)

    def on_error(self, ws, error):
        print("Error:", error)

    def on_close(self, ws, close_status_code, close_msg):
        print("### closed WebSocket###")

    def on_open(self, ws):
        print("Opened connection")
        x_apikey = os.getenv('X_APIKEY')

        subscribe_message = f'{{"headers": {{"X-ApiKey": "{str(x_apikey)}"}}, "method": "subscribe", "resource": "/feeds/"}}'

        ws.send(subscribe_message)

    def stop(self):
        self.running = False
        if self.ws:
            self.ws.close()
        print("WebSocket client has been stopped.")


    def run_forever(self):
        print("run_forever")
        while self.running:
            try:
                self.ws = websocket.WebSocketApp(self.url,
                                                on_open=self.on_open,
                                                on_message=self.on_message,
                                                on_error=self.on_error,
                                                on_close=self.on_close)
                self.ws.run_forever()
            except Exception as e:
                print(f"Error: {e}")
            if self.running:
                print("Attempting to reconnect in {} seconds...".format(os.getenv('RECONNECT_DELAY')))
                time.sleep(int(os.getenv('RECONNECT_DELAY')))  # 재연결 전 딜레이


"""
WebSocket 기반 Raw Data
calc_avg = True  # 평균값 계산후 전송 기능을 활성화
store_db = True  # 데이터베이스에 저장용 데이터 전송을 활성화

""" 
