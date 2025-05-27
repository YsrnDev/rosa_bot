import os
import google.generativeai as genai
import asyncio
from data_retrieval import get_current_crypto_price, get_current_stock_forex_price

# Configure Gemini API
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# ==========================================================
# DAFTARKAN TOOLS (ALAT) UNTUK GEMINI AI
# ==========================================================
tools_for_gemini = [
    genai.protos.FunctionDeclaration(
        name="get_current_crypto_price",
        description="Mengambil harga penutupan terakhir dari berbagai aset cryptocurrency dari Binance. Dapat memahami simbol singkat seperti 'BTC', 'PEPE', 'TRUMP', atau format lengkap 'BTCUSDT', dan akan secara otomatis mencoba menemukan pasangan yang benar (misalnya dengan USDT atau BUSD).",
        parameters=genai.protos.Schema(
            type="OBJECT",
            properties={
                "symbol": genai.protos.Schema(type="STRING", description="Simbol aset crypto (misal: 'BTC', 'ETH', 'PEPE', 'TRUMP', 'XRP', 'DOGE', atau 'BTCUSDT').")
            },
            required=["symbol"]
        ),
    ),
    genai.protos.FunctionDeclaration(
        name="get_current_stock_forex_price",
        description="Mengambil harga penutupan terakhir dari saham, forex, metals, atau energi. Bisa memahami simbol umum seperti 'EURUSD' (untuk forex), 'GOLD' (untuk emas), 'OIL' (untuk minyak), 'GOOG' (untuk saham).", # <--- DESKRIPSI BARU
        parameters=genai.protos.Schema(
            type="OBJECT",
            properties={
                "symbol": genai.protos.Schema(type="STRING", description="Simbol aset (misal: 'GOOG', 'EURUSD', 'GOLD', 'CL=F').") # <--- DESKRIPSI BARU
            },
            required=["symbol"]
        ),
    ),
]

model = genai.GenerativeModel('gemini-2.0-flash', tools=tools_for_gemini)

conversation_histories = {}


async def get_gemini_response(user_id: int, prompt: str) -> str:
    try:
        history = conversation_histories.get(user_id, [])
        history.append({'role': 'user', 'parts': [prompt]})
        chat = model.start_chat(history=history[:-1])
        
        # Kirim prompt terbaru
        response = await asyncio.to_thread(chat.send_message, prompt)

        # ==========================================================
        # LOGIKA PENANGANAN TOOL USE
        # ==========================================================
        # Buat daftar untuk menyimpan semua function_responses jika ada banyak panggilan
        function_responses_parts = []
        
        if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
            # Periksa setiap bagian dari respons AI
            for part in response.candidates[0].content.parts:
                if part.function_call:
                    function_call = part.function_call
                    function_name = function_call.name
                    function_args = {key: value for key, value in function_call.args.items()}
                    
                    print(f"AI meminta untuk memanggil fungsi: {function_name} dengan argumen: {function_args}")

                    function_result = None
                    if function_name == "get_current_crypto_price":
                        function_result = await get_current_crypto_price(**function_args)
                    elif function_name == "get_current_stock_forex_price":
                        function_result = await get_current_stock_forex_price(**function_args)
                    else:
                        function_result = "Fungsi tidak dikenali atau tidak didukung."
                    
                    print(f"Hasil fungsi: {function_result}")

                    # Tambahkan hasil fungsi ke dalam daftar function_responses_parts
                    function_responses_parts.append(
                        genai.protos.Part(function_response=genai.protos.FunctionResponse(
                            name=function_name,
                            response={
                                "result": function_result
                            }
                        ))
                    )
            
            # Jika ada function_calls yang perlu direspons
            if function_responses_parts:
                # Tambahkan giliran AI yang meminta fungsi ke riwayat
                history.append({'role': 'model', 'parts': response.candidates[0].content.parts}) # Simpan permintaan fungsi AI di history

                # Tambahkan respons dari tool call ke riwayat
                history.append({'role': 'tool', 'parts': function_responses_parts}) # <--- PENTING: role='tool'

                # Kirim riwayat yang diperbarui kembali ke AI untuk mendapatkan respons akhir
                # send_message berikutnya harus berupa tool response
                final_response_gemini = await asyncio.to_thread(chat.send_message, function_responses_parts) # <--- Kirim list of Parts

                # Tambahkan respons final dari AI ke riwayat sebelum menyimpan
                history.append({'role': 'model', 'parts': [final_response_gemini.text]})
                
                conversation_histories[user_id] = history
                return final_response_gemini.text
        
        # Jika tidak ada pemanggilan fungsi, kembalikan respons asli AI
        # atau jika respons.candidates[0].content atau respons.candidates[0].content.parts tidak ada
        history.append({'role': 'model', 'parts': [response.text]})
        conversation_histories[user_id] = history
        return response.text

    except Exception as e:
        print(f"Error getting Gemini response: {e}")
        return "Maaf, ada masalah saat memproses permintaan Anda."

async def reset_gemini_history(user_id: int):
    if user_id in conversation_histories:
        del conversation_histories[user_id]
        return True
    return False