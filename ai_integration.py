import google.generativeai as genai
import os
import asyncio
# import openai

# Konfigurasi Gemini API
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Jika ingin menggunakan OpenAI, pastikan untuk mengatur kunci API
# openai.api_key = os.getenv("OPENAI_API_KEY")

# Inisialisasi model Generative AI
generation_config = {
    "temperature": 0.7,
    "top_p": 0.9,
    "top_k": 40,
    "max_output_tokens": 1024,
}

safety_settings = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
]

model = genai.GenerativeModel(
    model_name="gemini-2.0-flash",
    generation_config=generation_config,
    safety_settings=safety_settings
)

# KAMUS GLOBAL UNTUK MENYIMPAN RIWAYAT PERCAKAPAN
# Kunci: ID pengguna Discord (atau ID saluran), Nilai: List riwayat pesan
conversation_histories = {}

async def get_gemini_response(user_id: int, prompt: str) -> str:
    """
    Mengirimkan prompt ke Gemini AI dan mendapatkan respons,
    dengan menyimpan dan meneruskan riwayat percakapan.
    """
    try:
        # Dapatkan riwayat percakapan untuk pengguna/saluran ini
        # Jika belum ada, inisialisasi sebagai list kosong
        history = conversation_histories.get(user_id, [])

        # Tambahkan prompt pengguna ke riwayat
        history.append({'role': 'user', 'parts': [prompt]})

        # Buat objek chat dengan riwayat yang ada
        chat = model.start_chat(history=history[:-1]) # history[:-1] berarti riwayat sebelumnya, tanpa prompt yang baru ditambahkan

        # Kirim prompt terbaru
        response = await asyncio.to_thread(chat.send_message, prompt)

        # Tambahkan respons model ke riwayat
        history.append({'role': 'model', 'parts': [response.text]})

        # Perbarui riwayat di kamus global
        conversation_histories[user_id] = history

        return response.text
    except Exception as e:
        print(f"Error getting Gemini response: {e}")
        return "Maaf, ada masalah saat memproses permintaan Anda."

# Opsional: Fungsi untuk mereset riwayat percakapan
async def reset_gemini_history(user_id: int):
    if user_id in conversation_histories:
        del conversation_histories[user_id]
        return True
    return False

# # Tambahkan integrasi opsional dengan OpenAI jika diinginkan.
# async def get_openai_response(prompt: str) -> str:
#     try:
#         response = await openai.ChatCompletion.create(
#             model="gpt-3.5-turbo",
#             messages=[{"role": "user", "content": prompt}],
#             temperature=0.7,
#             max_tokens=1024
#         )
#         return response.choices[0].message.content
#         return "OpenAI response is not implemented yet."
#     except Exception as e:
#         print(f"Error calling OpenAI: {e}")
#         return "Maaf, terjadi masalah saat menghubungi OpenAI. Silakan coba lagi nanti."
    
# async def get_ai_response(prompt: str, use_openai: bool = False) -> str:
#     """
#     Mengirimkan prompt ke AI (Gemini atau OpenAI) dan mengembalikan responsnya.
#     """
#     if use_openai:
#         return await get_openai_response(prompt)
#     else:
#         return await get_gemini_response(prompt)
    
# # Fungsi ini dapat digunakan untuk mengintegrasikan AI ke dalam perintah Discord bot
# async def ai_integration(interaction, prompt: str, use_openai: bool = False):
#     """
#     Mengintegrasikan AI ke dalam perintah Discord bot.
#     """
#     await interaction.response.defer(thinking=True)
    
#     try:
#         response = await get_ai_response(prompt, use_openai)
#         await interaction.followup.send(response)
#     except Exception as e:
#         print(f"Error during AI integration: {e}")
#         await interaction.followup.send("Maaf, terjadi kesalahan saat menghubungi AI. Silakan coba lagi nanti.")
