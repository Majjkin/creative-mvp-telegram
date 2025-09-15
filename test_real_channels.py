#!/usr/bin/env python3
"""
Тест реальных каналов Telegram
"""
import asyncio
import os
from telethon import TelegramClient
from telethon.sessions import StringSession
from dotenv import load_dotenv

load_dotenv()

async def test_real_channels():
    """Тестируем реальные каналы"""
    
    # Получаем credentials
    api_id = os.getenv("TELEGRAM_API_ID")
    api_hash = os.getenv("TELEGRAM_API_HASH")
    session_string = os.getenv("TELEGRAM_SESSION")
    
    if not all([api_id, api_hash, session_string]):
        print("❌ Missing Telegram credentials")
        return
    
    # Создаем клиент
    client = TelegramClient(
        StringSession(session_string),
        int(api_id),
        api_hash
    )
    
    try:
        await client.start()
        print("✅ Connected to Telegram")
        
        # Тестируем реальные каналы
        test_channels = [
            "rogov24",
            "burimovasasha", 
            "zarina_brand",
            "goldapple_ru",
            "glamguruu",
            "casacozy",
            "homiesapiens"
        ]
        
        working_channels = []
        broken_channels = []
        
        for channel in test_channels:
            try:
                entity = await client.get_entity(channel)
                print(f"✅ {channel}: {entity.title} (ID: {entity.id}, Subscribers: {getattr(entity, 'participants_count', 'N/A')})")
                working_channels.append(channel)
                
                # Проверяем есть ли посты с фото
                photo_count = 0
                async for message in client.iter_messages(entity, limit=10):
                    if message.photo:
                        photo_count += 1
                        if photo_count >= 3:  # Достаточно для теста
                            break
                
                print(f"   📸 Found {photo_count} posts with photos")
                
            except Exception as e:
                print(f"❌ {channel}: {e}")
                broken_channels.append(channel)
        
        print(f"\n📊 SUMMARY:")
        print(f"✅ Working channels: {len(working_channels)}")
        print(f"❌ Broken channels: {len(broken_channels)}")
        
        if working_channels:
            print(f"\n✅ WORKING CHANNELS:")
            for ch in working_channels:
                print(f"  - {ch}")
        
        if broken_channels:
            print(f"\n❌ BROKEN CHANNELS:")
            for ch in broken_channels:
                print(f"  - {ch}")
                
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await client.disconnect()

if __name__ == "__main__":
    asyncio.run(test_real_channels())
