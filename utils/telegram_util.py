# -*- coding:utf-8 -*-
import aiohttp
from loguru import logger

async def sendMarkDownText(token, chat_id, sendMessageText, parse_mode="Markdown"):
    """
    텔레그램 메시지 발송 유틸리티 (Async)
    """
    if not token or not chat_id or not sendMessageText:
        logger.error("Telegram token, chat_id or message is missing.")
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": sendMessageText,
        "parse_mode": parse_mode,
        "disable_web_page_preview": True
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                if response.status != 200:
                    res_text = await response.text()
                    logger.error(f"Telegram API Error: {response.status} - {res_text}")
                else:
                    logger.debug(f"Message sent to {chat_id}")
    except Exception as e:
        logger.exception(f"Exception while sending telegram message: {e}")
