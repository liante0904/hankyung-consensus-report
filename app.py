# -*- coding:utf-8 -*-
import asyncio
import os
import datetime
from loguru import logger
from dotenv import load_dotenv

from models.database import DatabaseManager
from scrapers.hankyung import HankyungScraper

load_dotenv()

# 실행 환경 감지
IS_DOCKER = os.path.exists("/app")
ENV = os.getenv('ENV', 'dev').lower()
IS_PROD = ENV == 'production'

# 로그 설정
def setup_logging():
    now_date = datetime.datetime.now().strftime("%Y%m%d")
    base_log_dir = "/app/log" if IS_DOCKER else os.path.expanduser("~/log")
    log_dir = os.path.join(base_log_dir, now_date)
    os.makedirs(log_dir, exist_ok=True)
    
    log_file = os.path.join(log_dir, f"{now_date}_hankyung-consensus-report.log")
    logger.add(log_file, rotation="10 MB", retention="10 days", level="INFO", enqueue=True)
    return log_file

async def run_service(scraper):
    """도커 서비스 모드: 무한 루프 (30분 단위 실행)"""
    log_prefix = "" if IS_PROD else "[DEV] "
    interval = 1800
    logger.info(f"{log_prefix}Starting Hankyung Consensus Bot in SERVICE mode")
    
    # 시작 시 과거 데이터 수집 (알림 없이 DB만 채움)
    await scraper.fetch_historical_data()
    
    while True:
        now = datetime.datetime.now()
        seconds_since_hour = (now.minute * 60) + now.second
        wait_seconds = interval - (seconds_since_hour % interval)
        if wait_seconds <= 0: wait_seconds = interval

        logger.info(f"Waiting {int(wait_seconds)}s until next aligned run...")
        await asyncio.sleep(wait_seconds)
        await asyncio.sleep(0.5)

        logger.info(f"--- [Loop Start: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ---")
        try:
            await scraper.run()
            logger.info(f"Scraping completed.")
        except Exception as e:
            logger.error(f"Unexpected error during scraping: {e}")
            await asyncio.sleep(10)

async def run_once(scraper):
    """로컬 태스크 모드: 1회 실행"""
    log_prefix = "" if IS_PROD else "[DEV] "
    logger.info(f"{log_prefix}Starting Hankyung Consensus Bot in TASK mode (Once)")
    try:
        await scraper.fetch_historical_data()
        await scraper.run()
        logger.info("Scraping completed successfully.")
    except Exception as e:
        logger.error(f"Task failed: {e}")

async def main():
    setup_logging()
    
    # DB 파일명 분리 (prod_hankyung_consensus.db / dev_hankyung_consensus.db)
    prefix = 'prod' if IS_PROD else 'dev'
    default_db = f"/app/db/{prefix}_hankyung_consensus.db" if IS_DOCKER else f"./db/{prefix}_hankyung_consensus.db"
    db_path = os.getenv('DB_PATH', default_db)
    
    try:
        db = DatabaseManager(db_path)
        scraper = HankyungScraper(db, is_dev=(not IS_PROD))
        
        if IS_DOCKER:
            await run_service(scraper)
        else:
            await run_once(scraper)
            
    except Exception as e:
        logger.critical(f"Critical Initialization Error: {e}")
        if IS_DOCKER:
            await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
