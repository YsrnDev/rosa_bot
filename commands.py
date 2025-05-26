import discord
import asyncio
import os
from discord import app_commands
from discord.ext import commands
from ai_integration import get_gemini_response, reset_gemini_history
from data_retrieval import get_binance_klines, get_yfinance_data # Akan menambahkan fungsi untuk crypto, metals, dan energy
from smc_analysis import analyze_smc
from chart_generator import generate_chart
from smc_analysis import analyze_smc

def setup_commands(bot: commands.Bot):

    # Perintah /halo
    @bot.tree.command(name="halo", description="Memberikan salam.")
    async def halo(interaction: discord.Interaction):
        await interaction.response.send_message("Halo! Saya ROSA, siap membantu analisis pasar Anda. Ketik `/help` untuk melihat daftar perintah.")

    # Perintah /help
    @bot.tree.command(name="help", description="Mencantumkan perintah yang tersedia.")
    async def help_command(interaction: discord.Interaction):
        help_text = """
        **Daftar Perintah ROSA:**

        * `/halo`: Memberikan salam.
        * `/help`: Menampilkan daftar perintah ini.
        * `/rosa <jenis_aset> <simbol> <timeframe>`: Melakukan analisis pasar menggunakan Smart Money Concept.
            * `jenis_aset`: `crypto`, `forex`, `metals`, `energy`
            * `simbol`: Contoh: `BTCUSDT` (crypto), `EURUSD` (forex), `XAUUSD` (metals), `CL=F` (energy)
            * `timeframe`: Contoh: `1m`, `5m`, `15m`, `30m`, `1h`, `4h`, `1d`, `1w`, `1M`
            * Contoh: `/rosa crypto BTCUSDT 1h`
        * `/tanya <pertanyaan>`: Mengajukan pertanyaan terbuka kepada Gemini AI.
            * Contoh: `/tanya Apa itu inflasi?`
        """
        await interaction.response.send_message(help_text, ephemeral=True) # ephemeral=True agar hanya user yang melihat

  # Perintah /rosa
    @bot.tree.command(name="rosa", description="Melakukan analisis pasar SMC.")
    @app_commands.describe(
        jenis_aset="Jenis aset (crypto, forex, metals, energy)",
        simbol="Simbol aset (misalnya BTCUSDT, EURUSD=X, GC=F)",
        timeframe="Jangka waktu (misalnya 1h, 4h, 1d)"
    )
    async def rosa(interaction: discord.Interaction, jenis_aset: str, simbol: str, timeframe: str):
        await interaction.response.defer(thinking=True) # Menunjukkan bot sedang berpikir

        jenis_aset = jenis_aset.lower()
        simbol = simbol.upper()
        timeframe = timeframe.lower()

        data = None
        if jenis_aset == "crypto":
            data = await get_binance_klines(simbol, timeframe)
        elif jenis_aset in ["forex", "metals", "energy"]:
            data = await get_yfinance_data(simbol, timeframe)
        else:
            await interaction.followup.send(f"Jenis aset '{jenis_aset}' tidak didukung. Pilihan yang valid: `crypto`, `forex`, `metals`, `energy`.")
            return

        if data is None or data.empty:
            await interaction.followup.send(f"Gagal mendapatkan data untuk `{simbol}` pada timeframe `{timeframe}`. Pastikan simbol dan timeframe benar, dan coba format simbol `yfinance` yang tepat (misalnya `EURUSD=X` untuk forex, `GC=F` untuk emas).")
            return

        try:
            # Perbarui panggilan analyze_smc untuk mendapatkan data analisis dan teks
            analysis_text, smc_indicators = analyze_smc(data, simbol, timeframe)
            
            # Teruskan data SMC ke generate_chart
            chart_file_path = generate_chart(data, simbol, timeframe, smc_indicators)

            if chart_file_path and os.path.exists(chart_file_path):
                file = discord.File(chart_file_path, filename=f"{simbol}_{timeframe}_chart.png")
                await interaction.followup.send(content=analysis_text, file=file)
                os.remove(chart_file_path)
            else:
                await interaction.followup.send(content=f"Analisis untuk {simbol} ({timeframe}):\n\n{analysis_text}\n\nGagal menghasilkan grafik atau grafik tidak ditemukan.")

        except Exception as e:
            print(f"Error during SMC analysis or chart generation for {simbol} {timeframe}: {e}")
            await interaction.followup.send(f"Terjadi kesalahan saat menganalisis {simbol} ({timeframe}). Silakan coba lagi nanti. Detail error: `{e}`")

   # Perintah /tanya
    @bot.tree.command(name="tanya", description="Mengajukan pertanyaan terbuka kepada Gemini AI.")
    @app_commands.describe(
        pertanyaan="Pertanyaan yang ingin Anda ajukan kepada AI."
    )
    async def tanya(interaction: discord.Interaction, pertanyaan: str):
        await interaction.response.defer(thinking=True) # Menunjukkan bot sedang berpikir

        # Gunakan ID pengguna sebagai kunci untuk riwayat percakapan
        user_id = interaction.user.id

        try:
            # Panggil fungsi dengan user_id
            response_text = await get_gemini_response(user_id, pertanyaan)
            await interaction.followup.send(response_text)
        except Exception as e:
            print(f"Error handling /tanya command: {e}")
            await interaction.followup.send("Maaf, terjadi kesalahan saat mencoba menjawab pertanyaan Anda. Silakan coba lagi nanti.")

    # Opsional: Tambahkan perintah untuk mereset riwayat percakapan AI
    @bot.tree.command(name="reset_tanya", description="Mereset riwayat percakapan Anda dengan Gemini AI.")
    async def reset_tanya(interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)
        user_id = interaction.user.id
        if await reset_gemini_history(user_id):
            await interaction.followup.send("Riwayat percakapan Anda dengan Gemini AI telah direset.")
        else:
            await interaction.followup.send("Anda tidak memiliki riwayat percakapan aktif untuk direset.")
