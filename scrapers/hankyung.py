# -*- coding:utf-8 -*- 
import os
import requests
import html
import asyncio
import datetime
import urllib.parse
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
        self.list_url = 'https://consensus.hankyung.com/analysis/list'
        self.prefix = "<b>[DEV]</b> " if is_dev else ""
        logger.info(f"HankyungScraper initialized with prefix: '{self.prefix}'")

    def escape_html(self, text):
        return html.escape(text) if text else ""

    def _parse_report_idx(self, url):
        """URL에서 report_idx 값을 추출"""
        if not url: return None
        try:
            parsed = urllib.parse.urlparse(url)
            params = urllib.parse.parse_qs(parsed.query)
            return params.get('report_idx', [None])[0]
        except Exception:
            return None

    async def _fetch_range_and_insert(self, sdate, edate, page=1, sent_yn='N'):
        """주어진 날짜 범위와 페이지에서 데이터를 긁어서 DB에 저장"""
        source = "HANKYUNG"
        new_count = 0
        url = f"{self.list_url}?sdate={sdate}&edate={edate}&now_page={page}&search_value=&report_type=&pagenum=1000&search_text=&business_code="
        
        try:
            webpage = requests.get(url, verify=False, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36'
            }, timeout=60)
            soup = BeautifulSoup(webpage.content, "html.parser")
            rows = soup.select('div.table_style01 table tbody tr')
            
            if not rows:
                return 0

            for row in rows:
                try:
                    if row.select_one('td.no_data') or "데이터가 없습니다" in row.text:
                        return 0
                    
                    cols = row.select('td')
                    if len(cols) < 6: continue
                    
                    # 1번째 td: 작성일 (REG_DT)
                    reg_dt = cols[0].text.strip()
                    
                    # 3번째 td: 제목 (TITLE)
                    title_el = cols[2].select_one('a')
                    if not title_el: continue
                    title_raw = title_el.text.strip()
                    
                    # 5번째 td: 증권사 (BROKER)
                    broker = cols[4].text.strip()
                    
                    # 6번째 td: 링크 및 IDX 추출
                    link_el = cols[5].select_one('div.link_btn a') or cols[5].select_one('a')
                    if not link_el or 'href' not in link_el.attrs: continue
                    link = 'https://consensus.hankyung.com' + link_el.attrs['href']
                    
                    report_idx = self._parse_report_idx(link)
                    title = self.escape_html(title_raw)
                    
                    # DB 저장 (report_idx 포함)
                    if self.db.insert_report(
                        title=title, 
                        url=link, 
                        pdf_url=link, 
                        source=source, 
                        broker=broker, 
                        reg_dt=reg_dt, 
                        report_idx=report_idx, 
                        sent_yn=sent_yn
                    ):
                        new_count += 1
                except Exception as e:
                    logger.debug(f"Row parsing error: {e}")
                    continue
            
            return new_count
        except Exception as e:
            logger.error(f"Error fetching Hankyung ({sdate}~{edate}, Page {page}): {e}")
            return 0

    async def fetch_historical_data(self):
        """과거 모든 데이터를 연도별로 쪼개서 전체 수집 (1995년부터 현재까지)"""
        current_year = datetime.datetime.now().year
        start_year = 1995 
        
        logger.info(f"Starting TOTAL historical collection from {start_year} to {current_year}")
        
        total_saved = 0
        for year in range(current_year, start_year - 1, -1):
            sdate = f"{year}-01-01"
            edate = f"{year}-12-31"
            if year == current_year:
                edate = datetime.datetime.now().strftime('%Y-%m-%d')
            
            logger.info(f"--- Collecting Year {year} ---")
            
            page = 1
            year_saved = 0
            while True:
                count = await self._fetch_range_and_insert(sdate=sdate, edate=edate, page=page, sent_yn='Y')
                year_saved += count
                total_saved += count
                
                if count == 0:
                    break
                
                logger.info(f"Year {year} Page {page}: {count} items saved. (Total: {total_saved})")
                page += 1
                await asyncio.sleep(0.3)
            
            if year_saved == 0 and year < 2000:
                logger.info(f"No data found in year {year}. Stopping historical search.")
                break
                
            logger.info(f"Finished Year {year}: {year_saved} items saved.")
            
        logger.info(f"ALL historical collection finished. Total {total_saved} items indexed.")

    async def run(self):
        """실시간 데이터 체크 및 발송"""
        today = datetime.datetime.now().strftime('%Y-%m-%d')
        logger.info(f"Checking for new reports today ({today})...")
        await self._fetch_range_and_insert(sdate=today, edate=today, page=1, sent_yn='N')
        
        unsent = self.db.get_unsent_reports()
        if not unsent:
            logger.info("No new reports to send.")
            return

        logger.debug(f"Grouping {len(unsent)} new reports by broker...")
        
        # 1. 증권사별 그룹화
        broker_groups = {}
        for report in unsent:
            broker = report['BROKER']
            if broker not in broker_groups:
                broker_groups[broker] = []
            broker_groups[broker].append(report)

        # 2. 메시지 구성
        send_buffer = ""
        sent_ids = []
        
        for i, (broker, reports) in enumerate(broker_groups.items()):
            # 첫 번째 그룹이 아니면 앞에 개행 추가
            prefix_newline = "\n" if i > 0 else ""
            broker_header = f"{prefix_newline}●{broker}\n"
            report_list = ""
            for report in reports:
                display_url = report['PDF_URL'] if report.get('PDF_URL') else report['URL']
                # 제목에서 종목코드가 이미 포함되어 있을 수 있으므로 그대로 사용
                report_list += f"{report['TITLE']}\n{EMOJI_PICK}<a href='{display_url}'>링크</a>\n\n"
                sent_ids.append(report['ID'])
            
            group_content = f"{broker_header}{report_list}"
            
            # 메시지 길이 제한 체크 (텔레그램 약 4000자)
            if len(send_buffer) + len(group_content) > 3800:
                await self._send_batch_message("", send_buffer)
                send_buffer = ""
            
            send_buffer += group_content
            
        if send_buffer:
            await self._send_batch_message("", send_buffer)
            
        self.db.update_sent_status(sent_ids)
        logger.info(f"Telegram notifications sent for {len(sent_ids)} items.")

    async def _send_batch_message(self, header, body):
        if not body: return
        # header가 비어있으면 body만 전송, prefix 뒤에 한 줄 띄움 (\n\n)
        prefix_space = f"{self.prefix}\n\n" if self.prefix else ""
        full_message = f"{prefix_space}{header}\n{body}" if header else f"{prefix_space}{body}"
        await sendMarkDownText(token=TELEGRAM_BOT_TOKEN, chat_id=CHANNEL_ID, sendMessageText=full_message.strip(), parse_mode="HTML")
L")
