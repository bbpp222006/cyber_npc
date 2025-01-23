import asyncio
from logging import getLogger
import json
import base64
import re

logger = getLogger('llm')

async def read_ebook(main_queue: asyncio.Queue, main_task_queue: asyncio.Queue):
    """
    读取电子书并处理
    """
    await asyncio.sleep(5)
    logger.info("读书模块启动成功")
    
    with open("/root/prj/cyber_npc/play_tools/read_ebook/books/test.txt", "r", encoding="utf-8") as f:
        lines = f.readlines()
        
        sentence = ""
        for line in lines:
            line = line.strip()
            if len(sentence)>100:
                logger.info(f"读书模块读取到句子: {sentence}")
                await main_queue.put({
                    "type": "ebook",
                    "text": f"\"\"\"\n{sentence}\n\"\"\"",
                })
                logger.info(f"读书模块发送消息: \"\"\"\n{sentence}\n\"\"\"")
                sentence = ""
                await main_task_queue.get()
                logger.info(f"开始阅读下一段")
            else:
                sentence += line + "\n"
                

        # logger.info(f"text_audio消息已完成播放: {sentence}")