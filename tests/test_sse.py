"""测试SSE响应格式"""
import asyncio
import aiohttp
import json
import logging

logger = logging.getLogger(__name__)

async def test_sse():
    async with aiohttp.ClientSession() as session:
        async with session.post(
            'http://localhost:8000/juben/chat',
            json={
                'input': '你好',
                'user_id': 'test_user',
                'enable_web_search': False,
                'enable_knowledge_base': False
            }
        ) as resp:
            logger.info(f"Status: {resp.status}")
            logger.info(f"Headers: {dict(resp.headers)}")
            logger.info("\n=== SSE Response ===")

            count = 0
            async for line in resp.content:
                text = line.decode('utf-8', errors='ignore')
                logger.info(text)
                count += 1
                if count >= 50:  # 只显示前50行
                    logger.info("\n... (truncated)")
                    break

if __name__ == '__main__':
    asyncio.run(test_sse())
