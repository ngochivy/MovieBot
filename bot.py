import discord
from discord import app_commands
import aiohttp
import re
import sqlite3

# ================= CẤU HÌNH CỦA BẠN =================
DISCORD_TOKEN = "MTU3NTQwNTkzMTAxMjAzODc3Nw.GviHbv.kVVvt51oPu7N4RxMwOtrnydW_d3eS-_b-OVKMA"
OMDB_API_KEY = "2b8633c3"
# ====================================================

# Tạo cơ sở dữ liệu lưu điểm của server
conn = sqlite3.connect("reviews.db")
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS ratings 
             (imdb_id TEXT, user_id TEXT, score REAL, PRIMARY KEY (imdb_id, user_id))''')
conn.commit()

class MovieBot(discord.Client):
    def __init__(self):
        super().__init__(intents=discord.Intents.default())
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        await self.tree.sync()

client = MovieBot()

@client.event
async def on_ready():
    print(f"✅ Bot đã sẵn sàng hoạt động với tên: {client.user}")

# Lệnh /review trực tiếp trên Discord
@client.tree.command(name="review", description="Chấm điểm và viết review phim (nhập tên phim hoặc link IMDb)")
@app_commands.describe(
    phim="Tên phim (tiếng Anh) hoặc dán trực tiếp link IMDb",
    diem="Điểm số bạn chấm (từ 1 đến 10)",
    nhan_xet="Cảm nhận / Review của bạn về bộ phim"
)
async def review(interaction: discord.Interaction, phim: str, diem: float, nhan_xet: str):
    if diem < 0 or diem > 10:
        await interaction.response.send_message("❌ Vui lòng chấm điểm trong khoảng từ **0 đến 10**!", ephemeral=True)
        return

    await interaction.response.defer() # Báo Discord chờ bot lấy dữ liệu

    # Kiểm tra xem người dùng nhập link IMDb hay tên phim
    imdb_match = re.search(r"(tt\d+)", phim)
    if imdb_match:
        url = f"http://www.omdbapi.com/?i={imdb_match.group(1)}&apikey={OMDB_API_KEY}"
    else:
        url = f"http://www.omdbapi.com/?t={phim}&apikey={OMDB_API_KEY}"

    # Gọi dữ liệu từ OMDb
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            data = await resp.json()

    if data.get("Response") == "False":
        await interaction.followup.send(f"❌ Không tìm thấy phim **{phim}**. Hãy thử nhập tên tiếng Anh chính xác hoặc dán thẳng link IMDb nhé!")
        return

    # Lấy thông tin phim
    imdb_id = data.get("imdbID")
    title = data.get("Title")
    year = data.get("Year")
    poster = data.get("Poster")
    imdb_rating = data.get("imdbRating", "N/A")
    genre = data.get("Genre", "Đang cập nhật")

    # Lưu điểm của thành viên vào database và tính trung bình cả server
    c.execute("INSERT OR REPLACE INTO ratings (imdb_id, user_id, score) VALUES (?, ?, ?)", 
              (imdb_id, str(interaction.user.id), diem))
    conn.commit()

    c.execute("SELECT AVG(score), COUNT(score) FROM ratings WHERE imdb_id = ?", (imdb_id,))
    avg_score, total_votes = c.fetchone()

    # Tạo thẻ Embed hiển thị cực đẹp
    embed = discord.Embed(
        title=f"🎬 {title} ({year})",
        url=f"https://www.imdb.com/title/{imdb_id}/",
        description=f"**Cảm nhận của {interaction.user.mention}:**\n> {nhan_xet}",
        color=discord.Color.gold()
    )
    embed.add_field(name="⭐ Điểm thành viên chấm", value=f"**{diem}/10**", inline=True)
    embed.add_field(name="🏆 Trung bình Server", value=f"**{avg_score:.1f}/10** ({total_votes} lượt)", inline=True)
    embed.add_field(name="🌐 Điểm IMDb", value=f"{imdb_rating}/10", inline=True)
    embed.add_field(name="🎭 Thể loại", value=genre, inline=False)

    if poster and poster != "N/A":
        embed.set_thumbnail(url=poster) # Hoặc dùng set_image(url=poster) nếu muốn poster to bên dưới

    embed.set_footer(text=f"Review bởi {interaction.user.display_name}", icon_url=interaction.user.display_avatar.url)

    await interaction.followup.send(embed=embed)

client.run(DISCORD_TOKEN)