import discord
from discord.ext import tasks
import requests
import datetime
import pytz
import feedparser
import os
from flask import Flask
from threading import Thread


import static_ffmpeg
static_ffmpeg.add_paths()

intents = discord.Intents.default()
intents.guilds = True
intents.messages = True
intents.message_content = True
intents.voice_states = True 

client = discord.Client(
    intents=intents,
    max_messages=None,
    member_cache_flags=discord.MemberCacheFlags.none(),
    chunk_guilds_at_startup=False
)

TOKEN = os.getenv("DISCORD_TOKEN")
WEATHER_API_KEY = '89c841ee5f0d489da7011513260309' 


WEATHER_CHANNEL_ID = 1544645144647831644  
NEWS_CHANNEL_ID = 1544886207547187210     

#Thư viện datetime để lấy giờ chuẩn
TIMEZONE = datetime.timezone(datetime.timedelta(hours=7))

# Danh sách 3 bài hát của bạn (đảm bảo các file MP3 này nằm cùng thư mục trên GitHub)
PLAYLIST = [
    {"file": "amthambenem.mp3", "name": "Âm Thầm Bên Em - Sơn Tùng M-TP"},
    {"file": "biw.mp3", "name": "Beautiful In White - Shane Filan"},
    {"file": "cmw.mp3", "name": "Come My Way - Sơn Tùng M-TP"}
]

FFMPEG_OPTIONS = {
    'options': '-vn -loglevel quiet'
}

# Các khung giờ gửi thông báo tự động: 7:00, 12:00, 15:00 và 19:00
report_times = [
    datetime.time(hour=7, minute=0, tzinfo=TIMEZONE),
    datetime.time(hour=12, minute=0, tzinfo=TIMEZONE),
    datetime.time(hour=15, minute=0, tzinfo=TIMEZONE),
    datetime.time(hour=19, minute=0, tzinfo=TIMEZONE)
]

http_session: aiohttp.ClientSession | None = None

music_states = {}

app = Flask('')
import logging
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

@app.route('/')
def home():
    return "Bot is alive and running 24/7!"

def run_flask():
    port = int(os.environ.get("PORT",8080))
    app.run(host='0.0.0.0', port=port, use_reloader=False)

def keep_alive():
    t = Thread(target=run_flask)
    t.start()
# ---------------------------------------------------

async def get_http_session():
    global http_session
    if http_session is None or http_session.closed:
        http_session = aiohttp.ClientSession()
    return http_session

async def get_weather_data(location="Hanoi"):
    try:
        session = await get_http_session()
        url = "https://api.weatherapi.com/v1/current.json"
        params = {"key": WEATHER_API_KEY, "q": location, "lang": "vi"}
     
        if response.status_code == 200:
            data = await response.json()
            city = data["location"]["name"]
            country = data["location"]["country"]
            temp = data["current"]["temp_c"]
            feels_like = data["current"]["feelslike_c"]
            condition = data["current"]["condition"]["text"]
            humidity = data["current"]["humidity"]
            wind_speed = data["current"]["wind_kph"]
            
            return (
                f"📍 **Khu vực:** {city}, {country}\n"
                f"🌡️ **Nhiệt độ:** {temp}°C (Cảm giác như: {feels_like}°C)\n"
                f"🌤️ **Tình trạng:** {condition}\n"
                f"💧 **Độ ẩm:** {humidity}%\n"
                f"🌬️ **Gió:** {wind_speed} km/h"
            )
    except Exception as e:
        print(f"Lỗi kết nối WeatherAPI: {e}")
    return None

def get_latest_news():
    try:
        session = await get_http_session()
        rss_url = "https://vnexpress.net/rss/tin-moi-nhat.rss"
        async with session.get(rss_url) as response:
            if response.status != 200: return []
            xml_content = await response.text()
        feed = await asyncio.to_thread(feadparser.parse, xml_content)
        news_list = [
            f". [{entry.title}]({entry.link})" for entry in feed.entries[:5]
        ]
        
        del feed, xml_content
        gc.collect()
        return news_list
    except Exception as e:
        print(f"Lỗi lấy RSS tin tức: {e}")
        return []

# Tác vụ tự động gửi theo khung giờ
@tasks.loop(time=report_times)
async def send_scheduled_reports():
    current_time = datetime.datetime.now(TIMEZONE).strftime('%H:%M')
    weather_channel = client.get_channel(WEATHER_CHANNEL_ID)
    if weather_channel:
        weather_text = await get_weather_data("Hanoi")
        if weather_text:
            await weather_channel.send(f"🤖 **[TỰ ĐỘNG] Dự báo thời tiết Hà Nội lúc {current_time}**:\n{weather_text}")

    news_channel = client.get_channel(NEWS_CHANNEL_ID)
    if news_channel:
        news_items = await get_latest_news()
        if news_items:
            news_msg = f"📰 **[TỰ ĐỘNG] Top 5 tin tức mới nhất lúc {current_time}:**\n" + "\n".join(news_items)
            await news_channel.send(news_msg)
    gc.collect()

@send_scheduled_reports.before_loop
async def before_send_reports():
    await client.wait_until_ready()

@client.event
async def on_ready():
    print(f'Bot đã đăng nhập thành công với tên {client.user}')
    if not send_scheduled_reports.is_running():
        send_scheduled_reports.start()

def play_song_loop(guild_id: int, voice_client: discord.VoiceClient):
    state = music_state.get(guild_id)
    if not state or not state.get("active") or note voice_client.is-connected():return
    song = PLAYLIST[state["index"]]
    try:
        source = discord.FFmpegPCMAudio(song["file"], **FFMPEG_OPTIONS)
    except Exception as e:
        return

    def after_track(error):
        source.cleanup()
        if error:print(f"Lỗi: {error}")
        current_state = music_state.get(guild_id)
        if not current_state or not current_state.get("active") or nte voice_client.is_connected():return
        current_state["index"] = (current_state["index"] + 1) % len(PLAYLIST)
        play_song_loop(guild_id, voice_client)
    voice_client.play(source, after=after_track)

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    content = message.content.strip()

    # Lệnh tra cứu thời tiết
    if content.lower().startswith('.thoitiet'):
        parts = content.split(maxsplit=1)
        location = parts[1] if len(parts) > 1 else "Hanoi"
        weather_text = get_weather_data(location)
        current_time = datetime.datetime.now(TIMEZONE).strftime('%H:%M')

        if weather_text:
            await message.channel.send(f"🤖 **Thông tin thời tiết lúc {current_time}**:\n{weather_text}")
        else:
            await message.channel.send(f"⚠️ Không tìm thấy thông tin cho địa điểm `{location}`.")

    # Lệnh xem tin tức
    elif content.lower() == '.tintuc':
        news_items = get_latest_news()
        if news_items:
            news_msg = "📰 **Top 5 tin tức mới nhất từ VnExpress:**\n" + "\n".join(news_items)
            await message.channel.send(news_msg)
        else:
            await message.channel.send("⚠️ Hiện tại không thể tải được danh sách tin tức.")

    # Lệnh phát nhạc luân phiên không ngừng 3 bài
    elif content.lower() == '.choinhac':
        if not message.author.voice or not message.author.voice.channel:
            await message.channel.send("⚠️ Bạn cần phải vào một kênh thoại trước đã nhé!")
            return

        voice_channel = message.author.voice.channel
        guild_id = message.guild.id
        
        try:
            voice_client = message.guild.voice_client
            if voice_client is not None:
                if guild_id in music_states: music_states[guild_id]["active"] = False
                if voice_client.is_playing(): voice_client.stop()
                if voice_client.channel != voice_channel: await voice_client.move_to(voice_channel)
            else:
                voice_client = await voice_channel.connect()

            music_states[guild_id] = {"index": 0 "active": True"}
            play_song_Loop(guild_id, voice_client)
        
            await message.channel.send(f"🎶 Đang phát danh sách vòng lặp 3 bài hát liên tục! Bắt đầu với: **{PLAYLIST[0]['name']}**")
        except Exception as e:
            await message.channel.send(f"⚠️ Không thể phát nhạc: {e}")

    # Lệnh dừng phát nhạc và rời voice
    elif content.lower() == '.dungnhac':
        if message.guild.voice_client:
            guild_id = message.guild.id
            if guild_id in music_states: music_states[guild_id]["active"] = False
            message.guild.voice_client.stop()
            await message.guild.voice_client.disconnect()
            gc.collect()
            await message.channel.send("⏹️ Đã dừng phát nhạc và rời khỏi kênh thoại!")
        else:
            await message.channel.send("⚠️ Bot không ở trong kênh thoại nào cả!")

# Khởi chạy Flask server ngầm trước, sau đó chạy Bot Discord
if __name__ == "__main__":
    keep_alive()
    if TOKEN:
        client.run(TOKEN, log_handler=None)
    else:
        print("⚠️ LỖI: Chưa cấu hình biến môi trường DISCORD_TOKEN trên Render!")
