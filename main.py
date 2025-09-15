from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from datetime import datetime, timedelta
from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel
import os
import asyncio
import logging
import io

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Creative Trends MVP - Railway Telegram")

# Простые модели данных
Category = Literal["fashion","home","beauty"]

class FeedItem(BaseModel):
    id: str
    category: Category
    media_type: Literal["image","video"]
    media_url: str
    post_url: str
    title: str
    short_desc: str
    visual_elements: List[str]
    views: int
    likes: int
    comments: int
    posted_at: str
    source_channel: str

class PromptReq(BaseModel):
    feed_item_id: str

# Демо данные
CHANNELS = {
    "fashion": ["burimovasasha", "rogov24", "zarina_brand", "limeofficial", "ekonika", "sela_brand", "lichi", "befree_community", "mordorblog", "bymirraa"],
    "beauty": ["goldapple_ru", "glamguruu", "marietells", "sofikshenzdes", "writeforfriends"],
    "home": ["casacozy", "homiesapiens", "home_where", "objectdesigner"]
}

def create_demo_item(cat, ch, i, views):
    return FeedItem(
        id=f"{cat}_{ch}_{i}",
        category=cat,
        media_type="image",
        media_url=f"https://picsum.photos/seed/{cat}-{ch}-{i}/640/854",
        post_url=f"https://t.me/{ch}/{100+i}",
        title=f"{cat.title()} pick {i}",
        short_desc="Trending creative from Telegram",
        visual_elements=["clean backdrop", "soft daylight", "3/4 view"],
        views=views,
        likes=int(views*0.05),
        comments=int(views*0.01),
        posted_at=(datetime.utcnow()-timedelta(hours=i)).isoformat()+"Z",
        source_channel=ch
    )

# Генерируем демо данные
DEMO_FEED = []
for cat, chs in CHANNELS.items():
    for ch in chs:
        for i in range(1, 5):
            DEMO_FEED.append(create_demo_item(cat, ch, i, 12000-i*500))

# Telegram интеграция
class TelegramClient:
    def __init__(self):
        self.api_id = os.getenv("TELEGRAM_API_ID")
        self.api_hash = os.getenv("TELEGRAM_API_HASH")
        self.session_string = os.getenv("TELEGRAM_SESSION")
        self.client = None
        self.lock = asyncio.Lock()
        
    async def connect(self):
        logger.info(f"🔑 TELEGRAM_API_ID: {self.api_id}")
        logger.info(f"🔑 TELEGRAM_API_HASH: {self.api_hash[:10]}..." if self.api_hash else "None")
        logger.info(f"🔑 TELEGRAM_SESSION: {self.session_string[:20]}..." if self.session_string else "None")
        
        if not self.api_id or not self.api_hash or not self.session_string:
            logger.warning("❌ Telegram credentials not found, using demo mode")
            return False
            
        try:
            from telethon import TelegramClient
            from telethon.sessions import StringSession
            
            async with self.lock:
                if not self.client:
                    self.client = TelegramClient(
                        StringSession(self.session_string), 
                        self.api_id, 
                        self.api_hash
                    )
                    await self.client.start()
                    logger.info("✅ Telegram client connected successfully!")
                    return True
        except Exception as e:
            logger.error(f"❌ Failed to connect to Telegram: {e}")
            return False
    
    async def get_channel_posts(self, channel_username: str, limit: int = 50, min_views: int = 10000):
        """Получение постов из канала с фильтрацией по просмотрам"""
        # Временно используем только демо данные для стабильности
        logger.info(f"🎭 Using demo data for {channel_username} (Telegram API temporarily disabled)")
        return self._get_demo_posts(channel_username, limit)
    
    def _get_demo_posts(self, channel_username: str, limit: int):
        """Демо данные для канала с реальными изображениями"""
        logger.info(f"🎭 Generating demo posts for {channel_username}")
        posts = []
        
        # Реальные изображения для демо
        demo_images = [
            "https://images.unsplash.com/photo-1441986300917-64674bd600d8?w=400&h=600&fit=crop",
            "https://images.unsplash.com/photo-1469334031218-e382a71b716b?w=400&h=600&fit=crop", 
            "https://images.unsplash.com/photo-1445205170230-053b83016050?w=400&h=600&fit=crop",
            "https://images.unsplash.com/photo-1441984904996-e0b6ba687e04?w=400&h=600&fit=crop",
            "https://images.unsplash.com/photo-1441986300917-64674bd600d8?w=400&h=600&fit=crop"
        ]
        
        for i in range(min(limit, 5)):
            post_data = {
                'id': f"{channel_username}_demo_{i+1}",
                'channel': channel_username,
                'message_id': i+1,
                'text': f"Demo post from {channel_username} #{i+1} - testing interface with real images",
                'views': 15000 - i*1000,
                'likes': 750 - i*50,
                'comments': 150 - i*10,
                'date': (datetime.now() - timedelta(hours=i)).isoformat(),
                'media_url': demo_images[i % len(demo_images)],
                'post_url': f"https://t.me/{channel_username}/{i+1}"
            }
            posts.append(post_data)
        return posts
    
    def _get_media_url(self, message):
        """Получение URL медиа из сообщения"""
        if message.photo:
            return f"https://picsum.photos/seed/tg-{message.id}/400/600"
        elif message.video:
            return f"https://picsum.photos/seed/tg-video-{message.id}/400/600"
        else:
            return f"https://picsum.photos/seed/tg-default-{message.id}/400/600"

# Создаем экземпляр Telegram клиента
telegram_client = TelegramClient()

# API endpoints
@app.get("/")
def read_root():
    return {"message": "Creative Trends MVP", "status": "working", "platform": "Railway"}

@app.get("/health")
def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.get("/feed")
def get_feed(category: Category, min_views: int = 10000, page: int = 1):
    items = [x for x in DEMO_FEED if x.category == category and x.views >= min_views]
    items.sort(key=lambda x: (-x.views, -(x.likes+x.comments)/max(1,x.views)))
    page_size = 12
    start = (page-1) * page_size
    result = items[start:start+page_size]
    return {"items": result, "total": len(items)}

@app.get("/telegram/channels/{category}")
async def get_channel_posts(category: str, limit: int = 50):
    logger.info(f"📱 Getting posts for category: {category}")
    
    if category not in CHANNELS:
        return {"error": "Invalid category", "posts": []}
    
    # Подключаемся к Telegram если еще не подключены
    await telegram_client.connect()
    
    all_posts = []
    for channel in CHANNELS[category]:
        try:
            posts = await telegram_client.get_channel_posts(
                channel, 
                limit=limit//len(CHANNELS[category]),
                min_views=10000
            )
            all_posts.extend(posts)
        except Exception as e:
            logger.error(f"❌ Error getting posts from {channel}: {e}")
            continue
    
    # Сортируем по просмотрам
    all_posts.sort(key=lambda x: x['views'], reverse=True)
    
    logger.info(f"✅ Returning {len(all_posts)} posts for category {category}")
    return {
        "category": category,
        "posts": all_posts[:limit],
        "total": len(all_posts)
    }

@app.post("/prompts/generate")
def gen_prompts(req: PromptReq):
    parts = req.feed_item_id.split('_')
    if len(parts) >= 3 and parts[1] == 'demo':
        channel_username = parts[0]
        message_id = int(parts[2])
    elif len(parts) >= 2:
        channel_username = parts[0]
        message_id = int(parts[1])
    else:
        raise HTTPException(400, "Invalid feed_item_id format")

    item = next((x for x in DEMO_FEED if x.id == req.feed_item_id), None)
    if not item:
        category = next((cat for cat, chs in CHANNELS.items() if channel_username in chs), "fashion")
        item = create_demo_item(category, channel_username, message_id, 10000)
        item.title = f"Post from {channel_username}"
        item.short_desc = f"Content from {channel_username} message {message_id}"
        item.media_url = f"https://picsum.photos/seed/{channel_username}-{message_id}/640/854"
        item.post_url = f"https://t.me/{channel_username}/{message_id}"

    prompt_ready = f"Minimalist {item.category} product in clean studio, soft lighting, editorial style"
    prompt_template = f"Minimalist {{product.class}} in {{product.color}} {{material}}, clean backdrop, soft daylight, editorial style"
    negative = "blurry, low quality, distorted, text, watermark"
    
    return {
        "prompt_ready": prompt_ready,
        "prompt_template": prompt_template,
        "negative_prompt": negative
    }

@app.post("/creative/generate")
async def creative_generate(prompt: Optional[str] = None):
    return {
        "variants": [
            {"url": "https://picsum.photos/seed/demo1/768/1024"},
            {"url": "https://picsum.photos/seed/demo2/768/1024"},
            {"url": "https://picsum.photos/seed/demo3/768/1024"},
        ],
        "seed": 12345,
        "provider": "demo"
    }

@app.get("/photo/{channel}/{message_id}")
async def get_photo(channel: str, message_id: int):
    """Получение фото из Telegram через прокси"""
    # Временно возвращаем демо изображение для стабильности
    try:
        import requests
        # Используем Unsplash для демо изображений
        demo_url = f"https://images.unsplash.com/photo-1441986300917-64674bd600d8?w=400&h=600&fit=crop&seed={channel}_{message_id}"
        response = requests.get(demo_url)
        
        if response.status_code == 200:
            return StreamingResponse(
                io.BytesIO(response.content),
                media_type="image/jpeg",
                headers={"Cache-Control": "public, max-age=3600"}
            )
        else:
            raise HTTPException(404, "Demo photo not found")
            
    except Exception as e:
        logger.error(f"❌ Error getting demo photo: {e}")
        raise HTTPException(500, f"Error getting demo photo: {str(e)}")

@app.get("/ui", response_class=HTMLResponse)
def ui():
    return """<!doctype html>
<html>
<head>
    <meta charset="utf-8">
    <title>Creative Trends MVP</title>
    <style>
        body { font-family: system-ui; margin: 16px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; }
        .g { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
        .c { border: 1px solid #ddd; border-radius: 12px; overflow: hidden; background: white; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
        .btn { padding: 8px 16px; border: 1px solid #111; background: #111; color: #fff; border-radius: 8px; cursor: pointer; text-decoration: none; display: inline-block; margin: 4px; }
        .btn:hover { background: #333; }
        .small { color: #666; font-size: 12px; }
        textarea { width: 100%; height: 90px; margin-top: 6px; border: 1px solid #ddd; border-radius: 4px; padding: 8px; }
        .header { background: white; padding: 20px; border-radius: 12px; margin-bottom: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
        .controls { background: white; padding: 20px; border-radius: 12px; margin-bottom: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
        .generation { background: white; padding: 20px; border-radius: 12px; margin-bottom: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
        img { width: 100%; aspect-ratio: 3/4; object-fit: cover; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎨 Creative Trends MVP</h1>
            <p>Railway Platform - Working! 🚀</p>
        </div>
        
        <div class="controls">
            <h2>📱 Feed</h2>
            <select id="cat">
                <option value="home">Home</option>
                <option value="fashion">Fashion</option>
                <option value="beauty">Beauty</option>
            </select>
            <button class="btn" onclick="loadRealFeed()">Load Posts</button>
            <a class="btn" href="/docs" target="_blank">API Docs</a>
            <div id="feed" class="g" style="margin-top: 20px;"></div>
        </div>
        
        <div class="generation">
            <h3>🎯 Generation</h3>
            <label class="small">Prompt</label>
            <textarea id="prompt" placeholder="Enter your prompt here..."></textarea>
            <label class="small">Template</label>
            <textarea id="template" placeholder="Template will appear here..."></textarea>
            <label class="small">Negative</label>
            <textarea id="negative" placeholder="Negative prompt will appear here..."></textarea>
            <input id="file" type="file" accept="image/*" style="margin: 8px 0;">
            <button class="btn" onclick="gen()">Generate Images</button>
            <div id="vars" class="g" style="margin-top: 20px;"></div>
        </div>
    </div>

    <script>
        async function loadRealFeed() {
            const category = document.getElementById('cat').value;
            console.log('Loading data for category:', category);
            
            try {
                const response = await fetch(`/telegram/channels/${category}`);
                const data = await response.json();
                console.log('Received data:', data);
                
                const feed = document.getElementById('feed');
                feed.innerHTML = '';
                
                if (data.posts && data.posts.length > 0) {
                    data.posts.forEach(post => {
                        const card = document.createElement('div');
                        card.className = 'c';
                        card.innerHTML = `
                            <img src="${post.media_url || 'https://via.placeholder.com/400x600'}" alt="Post image">
                            <div style="padding: 16px;">
                                <div style="font-weight: bold; margin-bottom: 8px;">${post.text ? post.text.substring(0, 50) + '...' : 'No text'}</div>
                                <div class="small">👁 ${post.views || 0} ❤️ ${post.likes || 0} 💬 ${post.comments || 0}</div>
                                <div style="margin-top: 12px;">
                                    <button class="btn" onclick="p('${post.id}')">Prompt</button>
                                    <a class="btn" style="background: #fff; color: #111;" target="_blank" href="${post.post_url}">Post</a>
                                </div>
                            </div>
                        `;
                        feed.appendChild(card);
                    });
                } else {
                    feed.innerHTML = '<div style="text-align: center; padding: 40px; color: #666;">No posts for this category</div>';
                }
            } catch (error) {
                console.error('Error loading data:', error);
                document.getElementById('feed').innerHTML = '<div style="text-align: center; padding: 40px; color: #e74c3c;">Error loading data</div>';
            }
        }

        async function p(id) {
            try {
                const response = await fetch('/prompts/generate', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({feed_item_id: id})
                });
                const data = await response.json();
                
                document.getElementById('prompt').value = data.prompt_ready || '';
                document.getElementById('template').value = data.prompt_template || '';
                document.getElementById('negative').value = data.negative_prompt || '';
                
                window.scrollTo({top: document.body.scrollHeight, behavior: 'smooth'});
            } catch (error) {
                console.error('Error generating prompt:', error);
            }
        }

        async function gen() {
            try {
                const formData = new FormData();
                const file = document.getElementById('file').files[0];
                if (file) formData.append('image_file', file);
                
                const prompt = document.getElementById('prompt').value;
                if (prompt) formData.append('prompt', prompt);
                
                const response = await fetch('/creative/generate', {
                    method: 'POST',
                    body: formData
                });
                const data = await response.json();
                
                const vars = document.getElementById('vars');
                vars.innerHTML = '';
                
                if (data.variants && data.variants.length > 0) {
                    data.variants.forEach(variant => {
                        const el = document.createElement('div');
                        el.className = 'c';
                        el.innerHTML = `<img src="${variant.url}" alt="Generated image">`;
                        vars.appendChild(el);
                    });
                }
            } catch (error) {
                console.error('Error generating images:', error);
            }
        }

        // Load initial data
        loadRealFeed();
    </script>
</body>
</html>"""

if __name__ == "__main__":
    import uvicorn
    port = 8000  # Fixed port for Railway
    print(f"🚀 Starting Creative Trends MVP Server on Railway...")
    print(f"📍 Server will be available at: http://0.0.0.0:{port}")
    print(f"🌐 UI will be available at: http://0.0.0.0:{port}/ui")
    print(f"📚 API docs will be available at: http://0.0.0.0:{port}/docs")
    uvicorn.run(app, host="0.0.0.0", port=port)
