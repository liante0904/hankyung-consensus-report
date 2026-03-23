# -*- coding:utf-8 -*- 
import os
import requests
import html
import asyncio
from bs4 import BeautifulSoup
from loguru import logger
from dotenv import load_dotenv

from models.database import DatabaseManager
from utils.telegram_util import sendMarkDownText

load_dotenv()

# 환경 변수
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN_REPORT_ALARM_SECRET')
CHANNEL_ID = os.getenv('TELEGRAM_CHANNEL_ID_HANKYUNG_CONSEN')

EMOJI_PICK = "👉"

class HankyungScraper:
    def __init__(self, db: DatabaseManager, is_dev: bool = False):
        self.db = db
        self.target_url = 'https://consensus.hankyung.com/analysis/list?search_date=today&search_text=&pagenum=1000'
        self.prefix = "<b>[DEV]</b> " if is_dev else ""
        logger.info(f"HankyungScraper initialized with prefix: '{self.prefix}'")

    def escape_html(self, text):
        return html.escape(text) if text else ""

    async def _send_batch_message(self, header, body):
        if not body: return
        full_message = f"{self.prefix}{header}\n{body}"
        await sendMarkDownText(token=TELEGRAM_BOT_TOKEN, chat_id=CHANNEL_ID, sendMessageText=full_message, parse_mode="HTML")

    async def run(self):
        source = "HANKYUNG"
        header = "● 한경컨센서스"
        try:
            logger.info(f"Fetching Hankyung Consensus: {self.target_url}")
            webpage = requests.get(self.target_url, verify=False, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36'
            })
            soup = BeautifulSoup(webpage.content, "html.parser")
            rows = soup.select('#contents > div.table_style01 > table > tbody > tr')
            if not rows: return
            send_buffer = ""
            for row in rows:
                try:
                    title_raw = row.select_one('td.text_l > a').text.strip()
                    link = 'https://consensus.hankyung.com' + row.select_one('td:nth-child(6) > div > a').attrs['href']
                    broker = row.select_one('td:nth-child(5)').text.strip()
                    title = self.escape_html(title_raw)
                    if self.db.insert_report(title=title, url=link, source=source, broker=broker):
                        logger.info(f"New Hankyung Report: {title} ({broker})")
                        send_buffer += f"<b>{title}</b> ({broker})\n{EMOJI_PICK} <a href='{link}'>링크</a>\n\n"
                        if len(send_buffer) >= 3000:
                            await self._send_batch_message(header, send_buffer)
                            send_buffer = ""
                except Exception:
                    continue
            if send_buffer:
                await self._send_batch_message(header, send_buffer)
        except Exception as e:
            logger.error(f"Error fetching Hankyung: {e}")
