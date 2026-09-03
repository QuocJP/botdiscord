import discord
from discord.ext import tasks
import requests
import datetime
import pytz
import feedparser
import random

# Kích hoạt static_ffmpeg để tự động cung cấp bộ giải mã âm thanh
import static_ffmpeg
static_ffmpeg.add_paths()

intents = discord.Intents.default()
intents.guilds = True
intents.messages = True
intents.message_content = True
intents.voice_states = True  # Bật quyền quản lý Voice Channel

client = discord.Client(intents=intents)

# ================= CẤU HÌNH THÔNG TIN BOT =================
TOKEN = 'MTU0NDE4ODMyNjExMjc4ODQ4MA.GvZRxH.RHL2jFawQet41Ug2IL3E6b2jr9WbmFuU_c5uDc'
WEATHER_API_KEY = '89c841ee5f0d489da7011513260309' # WeatherAPI key của bạn

# Thay ID các kênh nhận thông báo tự động của bạn vào đây:
WEATHER_CHANNEL_ID = 1544645144647831644  # ID kênh nhận tin THỜI TIẾT tự động
NEWS_CHANNEL_ID = 1544886207547187210     # ID kênh nhận tin TỨC tự động
# ========================================================

TIMEZONE = pytz.timezone('Asia/Ho_Chi_Minh')

# Danh sách 3 bài hát của bạn
PLAYLIST = [
    {"file": "amthambenem.mp3", "name": "Âm Thầm Bên Em - Sơn Tùng M-TP"},
    {"file": "biw.mp3", "name": "Beautiful In White - Shane Filan"},
    {"file": "cmw.mp3", "name": "Come My Way - Sơn Tùng M-TP"}
]

# Các khung giờ gửi thông báo tự động: 7:00, 12:00, 15:00 và 19:00
report_times = [
    datetime.time(hour=7, minute=0, tzinfo=TIMEZONE),
    datetime.time(hour=12, minute=0, tzinfo=TIMEZONE),
    datetime.time(hour=15, minute=0, tzinfo=TIMEZONE),
    datetime.time(hour=19, minute=0, tzinfo=TIMEZONE)
]

def get_weather_data(location="Hanoi"):
    """Hàm lấy dữ liệu thời tiết từ WeatherAPI.com"""
    try:
        url = f"https://api.weatherapi.com/v1/current.json?key={WEATHER_API_KEY}&q={location}&lang=vi"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            city = data["location"]["name"]
            country = data["location"]["country"]
            temp = data["current"]["temp_c"]
            feels_like = data["current"]["feelslike_c"]
            condition = data["current"]["condition"]["text"]
            humidity = data["current"]["humidity"]
            wind_speed = data["current"]["wind_kph"]
            
            report = (
                f"📍 **Khu vực:** {city}, {country}\n"
                f"🌡️ **Nhiệt độ:** {temp}°C (Cảm giác như: {feels_like}°C)\n"
                f"🌤️ **Tình trạng:** {condition}\n"
                f"💧 **Độ ẩm:** {humidity}%\n"
                f"🌬️ **Gió:** {wind_speed} km/h"
            )
            return report
    except Exception as e:
        print(f"Lỗi kết nối WeatherAPI: {e}")
    return None

def get_latest_news():
    """Hàm lấy top 5 tin tức mới nhất từ RSS VnExpress"""
    try:
        rss_url = "https://vnexpress.net/rss/tin-moi-nhat.rss"
        feed = feedparser.parse(rss_url)
        
        news_list = []
        for entry in feed.entries[:5]:
            title = entry.title
            link = entry.link
            news_list.append(f"• [{title}]({link})")
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
        weather_text = get_weather_data("Hanoi")
        if weather_text:
            await weather_channel.send(f"🤖 **[TỰ ĐỘNG] Dự báo thời tiết Hà Nội lúc {current_time}**:\n{weather_text}")

    news_channel = client.get_channel(NEWS_CHANNEL_ID)
    if news_channel:
        news_items = get_latest_news()
        if news_items:
            news_msg = f"📰 **[TỰ ĐỘNG] Top 5 tin tức mới nhất lúc {current_time}:**\n" + "\n".join(news_items)
            await news_channel.send(news_msg)

@send_scheduled_reports.before_loop
async def before_send_reports():
    await client.wait_until_ready()

@client.event
async def on_ready():
    print(f'Bot đã đăng nhập thành công với tên {client.user}')
    if not send_scheduled_reports.is_running():
        send_scheduled_reports.start()

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
        
        try:
            voice_client = message.guild.voice_client
            if voice_client is not None:
                if voice_client.channel != voice_channel:
                    await voice_client.move_to(voice_channel)
            else:
                voice_client = await voice_channel.connect()

            if voice_client.is_playing():
                voice_client.stop()

            # Biến lưu chỉ số bài hát hiện tại (bắt đầu từ bài 0)
            current_index = [0]

            def play_next(error):
                if error:
                    print(f"Lỗi phát nhạc: {error}")
                
                # Kiểm tra nếu bot vẫn đang ở trong voice channel
                if not voice_client.is_connected():
                    return

                # Chuyển sang bài tiếp theo (quay vòng từ 0 -> 1 -> 2 -> 0...)
                current_index[0] = (current_index[0] + 1) % len(PLAYLIST)
                next_song = PLAYLIST[current_index[0]]

                try:
                    next_source = discord.FFmpegPCMAudio(next_song["file"])
                    voice_client.play(next_source, after=play_next)
                    print(f"Đang tự động chuyển sang bài: {next_song['name']}")
                except Exception as e:
                    print(f"Không thể phát bài tiếp theo: {e}")

            # Phát bài đầu tiên ngay khi nhận lệnh
            first_song = PLAYLIST[0]
            source = discord.FFmpegPCMAudio(first_song["file"])
            voice_client.play(source, after=play_next)

            await message.channel.send(f"🎶 Đang phát danh sách vòng lặp 3 bài hát liên tục! Bắt đầu với: **{first_song['name']}**")
            
        except Exception as e:
            await message.channel.send(f"⚠️ Không thể phát nhạc: {e}")

    # Lệnh dừng phát nhạc và rời voice
    elif content.lower() == '.dungnhac':
        if message.guild.voice_client:
            await message.guild.voice_client.disconnect()
            await message.channel.send("⏹️ Đã dừng phát nhạc và rời khỏi kênh thoại!")
        else:
            await message.channel.send("⚠️ Bot không ở trong kênh thoại nào cả!")

client.run(TOKEN)