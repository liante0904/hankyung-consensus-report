# -*- coding:utf-8 -*-
import os
import asyncio
from dotenv import load_dotenv
from utils.telegram_util import sendMarkDownText

load_dotenv()

# 환경 변수 (기존 설정 그대로 사용)
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN_REPORT_ALARM_SECRET')
CHANNEL_ID = os.getenv('TELEGRAM_CHANNEL_ID_HANKYUNG_CONSEN')
IS_DEV = os.getenv('ENV', 'dev') != 'production'
PREFIX = "<b>[DEV TEST]</b> " if IS_DEV else ""

async def test_send():
    print(f"Testing Telegram Format...")
    print(f"Token: {TELEGRAM_BOT_TOKEN[:10]}... / Channel: {CHANNEL_ID}")

    # 가짜 데이터 생성 (요청하신 예시와 동일)
    mock_unsent = [
        {
            'BROKER': '유안타증권',
            'TITLE': '에프에스티(036810) ArF 펠리클 시장 내 독보적 지배력, EUV로 증명할 시간',
            'URL': 'https://consensus.hankyung.com/analysis/view?report_idx=630000',
            'PDF_URL': 'https://consensus.hankyung.com/analysis/view?report_idx=630000',
            'ID': 1
        },
        {
            'BROKER': '메리츠증권',
            'TITLE': 'HD한국조선해양(009540) 1Q26 Preview: 무난한 실적. 미래 향한 투자 시작',
            'URL': 'https://consensus.hankyung.com/analysis/view?report_idx=630001',
            'PDF_URL': 'https://consensus.hankyung.com/analysis/view?report_idx=630001',
            'ID': 2
        },
        {
            'BROKER': '메리츠증권',
            'TITLE': '한국 물가전망: 전쟁 영향은 적어도 3Q까지',
            'URL': 'https://consensus.hankyung.com/analysis/view?report_idx=630002',
            'PDF_URL': 'https://consensus.hankyung.com/analysis/view?report_idx=630002',
            'ID': 3
        }
    ]

    # 1. 증권사별 그룹화 로직 (scrapers/hankyung.py와 동일)
    broker_groups = {}
    for report in mock_unsent:
        broker = report['BROKER']
        if broker not in broker_groups:
            broker_groups[broker] = []
        broker_groups[broker].append(report)

    # 2. 메시지 구성
    send_buffer = ""
    EMOJI_PICK = "👉"
    
    for i, (broker, reports) in enumerate(broker_groups.items()):
        # 첫 번째 그룹이 아니면 앞에 개행 추가
        prefix_newline = "\n" if i > 0 else ""
        broker_header = f"{prefix_newline}●{broker}\n"
        report_list = ""
        for report in reports:
            display_url = report['PDF_URL'] if report.get('PDF_URL') else report['URL']
            report_list += f"{report['TITLE']}\n{EMOJI_PICK}<a href='{display_url}'>링크</a>\n\n"
        
        group_content = f"{broker_header}{report_list}"
        send_buffer += group_content

    # 최종 메시지 구성 (scrapers/hankyung.py의 _send_batch_message 로직 반영)
    prefix_space = f"{PREFIX}\n\n" if PREFIX else ""
    full_message = f"{prefix_space}{send_buffer}".strip()
    
    print("-" * 30)
    print(full_message)
    print("-" * 30)

    # 실제 발송
    await sendMarkDownText(token=TELEGRAM_BOT_TOKEN, chat_id=CHANNEL_ID, sendMessageText=full_message, parse_mode="HTML")
    print("Test message sent successfully!")

if __name__ == "__main__":
    asyncio.run(test_send())
