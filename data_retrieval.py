import pandas as pd
import ccxt.async_support as ccxt
import yfinance as yf
import asyncio
import os
from datetime import datetime, timedelta

async def get_binance_klines(symbol: str, timeframe: str, limit: int = 500) -> pd.DataFrame:
    exchange = ccxt.binance({
        'apiKey': os.getenv('BINANCE_API_KEY'),
        'secret': os.getenv('BINANCE_API_SECRET'),
        'enableRateLimit': True,
    })
    try:
        # ccxt memerlukan symbol dalam format 'BTC/USDT'
        # Ubah BTCUSDT menjadi BTC/USDT
        if 'USDT' in symbol:
            base_currency = symbol.replace('USDT', '')
            formatted_symbol = f"{base_currency}/USDT"
        elif 'BUSD' in symbol:
            base_currency = symbol.replace('BUSD', '')
            formatted_symbol = f"{base_currency}/BUSD"
        else:
            formatted_symbol = symbol # Biarkan seperti apa adanya jika tidak cocok

        ohlcv = await exchange.fetch_ohlcv(formatted_symbol, timeframe, limit=limit)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        df.columns = [col.lower() for col in df.columns]
        return df
    except ccxt.NetworkError as e:
        print(f"Network error with Binance API: {e}")
        return pd.DataFrame()
    except ccxt.ExchangeError as e:
        # Tangani error spesifik jika symbol tidak ditemukan di Binance
        if "symbol is invalid" in str(e).lower() or "not found" in str(e).lower():
            print(f"Symbol {symbol} not found on Binance or is invalid.")
            return pd.DataFrame()
        print(f"Exchange error with Binance API for {symbol}: {e}")
        return pd.DataFrame()
    except Exception as e:
        print(f"An unexpected error occurred with Binance API: {e}")
        return pd.DataFrame()
    finally:
        await exchange.close()

# Fungsi get_yfinance_data (MODIFIKASI PENTING DI SINI)
async def get_yfinance_data(symbol: str, timeframe: str) -> pd.DataFrame:
    symbol = symbol.upper()
    try:
        interval_map = {
            "1m": "1m", "2m": "2m", "5m": "5m", "15m": "15m", "30m": "30m", "60m": "60m", "90m": "90m",
            "1h": "60m",
            "4h": "60m",
            "1d": "1d", "5d": "5d", "1wk": "1wk", "1mo": "1mo", "3mo": "3mo"
        }
        yf_interval = interval_map.get(timeframe)
        if not yf_interval:
            print(f"Invalid timeframe for yfinance: {timeframe}")
            return pd.DataFrame()        

        # Tentukan periode berdasarkan interval Yahoo Finance
        if yf_interval == "1m":
            # 1-minute data hanya tersedia untuk 7 hari terakhir
            fetch_period = "7d"
        elif yf_interval in ["2m", "5m", "15m", "30m", "60m", "90m"]:
            # Intraday data lainnya biasanya tersedia untuk 60 hari terakhir
            fetch_period = "60d"
        else:
            # Untuk daily, weekly, monthly, bisa ambil periode yang lebih panjang
            fetch_period = "1y" # Atau "max" jika ingin semua data yang tersedia

        # Inisialisasi objek Ticker untuk simbol
        ticker = yf.Ticker(symbol)
        
        # Siapkan argumen untuk metode .history()
        history_args = {
            'interval': yf_interval,
            'period': fetch_period
        }

        # Panggil ticker.history() menggunakan asyncio.to_thread
        df = await asyncio.to_thread(ticker.history, **history_args)

        if df.empty:
            print(f"No data fetched for {symbol} from Yahoo Finance using ticker.history.")
            return pd.DataFrame()

        # Pastikan kolom adalah lowercase
        df.columns = [col.lower() for col in df.columns]
        df.index.name = 'timestamp'
        return df
    except Exception as e:
        print(f"Error fetching yfinance data for {symbol}: {e}")
        return pd.DataFrame()
    
async def get_current_crypto_price(symbol: str) -> str:
    """
    Mengambil harga penutupan terakhir dari aset crypto dari Binance.
    Mendukung simbol singkat seperti 'BTC', 'PEPE', 'TRUMP', yang akan dikonversi ke 'BTCUSDT', 'PEPEUSDT', 'TRUMPUSDT'.
    Secara otomatis mencoba menambahkan 'USDT' atau 'BUSD' jika simbol tidak lengkap.
    """
    symbol_upper = symbol.upper()
    potential_symbols = []

    # Case 1: Simbol sudah dalam format lengkap (e.g., BTCUSDT, DOGEBUSD)
    if symbol_upper.endswith('USDT') or symbol_upper.endswith('BUSD'):
        potential_symbols.append(symbol_upper)
    else:
        # Case 2: Simbol adalah singkatan (e.g., BTC, PEPE, TRUMP)
        # Prioritaskan USDT, lalu BUSD
        potential_symbols.append(f"{symbol_upper}USDT")
        potential_symbols.append(f"{symbol_upper}BUSD")
        
        # Tambahkan simbol asli sebagai fallback (jika ada pasar non-stablecoin yang langka)
        potential_symbols.append(symbol_upper)

    for binance_symbol_try in potential_symbols:
        df = await get_binance_klines(binance_symbol_try, '1m', limit=1)
        if not df.empty:
            price = df['close'].iloc[-1]
            # Berikan respons yang jelas, menggunakan simbol yang dikenali pengguna
            return f"Harga penutupan terakhir {symbol_upper} ({binance_symbol_try}) adalah ${price:.8f}." # Gunakan .8f untuk presisi crypto
    
    return f"Tidak dapat mengambil harga saat ini untuk {symbol_upper}. Mungkin simbolnya salah atau tidak tersedia di Binance."

async def get_current_stock_forex_price(symbol: str, timeframe: str = "1d") -> str:
    symbol_upper = symbol.upper()
    yahoo_symbol = symbol_upper

    # Pemetaan untuk Forex (jika tidak ada =X, tambahkan)
    # Coba deteksi pasangan forex umum
    if len(symbol_upper) == 6 and (symbol_upper.endswith('USD') or symbol_upper.endswith('JPY') or symbol_upper.endswith('GBP') or symbol_upper.endswith('EUR')):
        if '=' not in symbol_upper:
            yahoo_symbol = f"{symbol_upper}=X"
    elif '=' not in symbol_upper and (symbol_upper.endswith('USD') or symbol_upper.endswith('JPY')):
        # Ini bisa menangani kasus seperti 'USDJPY' atau 'EURUSD' tanpa =X
        yahoo_symbol = f"{symbol_upper}=X"

    # Pemetaan untuk Metals/Energy
    elif symbol_upper in ['GOLD', 'XAUUSD', 'EMAS']:
        yahoo_symbol = 'GC=F' # Gold futures
    elif symbol_upper in ['SILVER', 'XAGUSD', 'PERAK']:
        yahoo_symbol = 'SI=F' # Silver futures
    elif symbol_upper in ['OIL', 'CRUDE OIL', 'WTI', 'MINYAK']:
        yahoo_symbol = 'CL=F' # Crude oil futures
    elif symbol_upper in ['NATURAL GAS', 'NGAS', 'GAS ALAM']:
        yahoo_symbol = 'NG=F' # Natural Gas futures
    elif symbol_upper in ['SPX', 'S&P500']:
        yahoo_symbol = '^GSPC' # S&P 500 Index

    df = await get_yfinance_data(yahoo_symbol, timeframe)
    if not df.empty:
        price = df['close'].iloc[-1]
        return f"Harga penutupan terakhir {symbol_upper} ({yahoo_symbol}) adalah ${price:.2f}."
    return f"Tidak dapat mengambil harga saat ini untuk {symbol_upper} ({yahoo_symbol}). Mungkin simbolnya salah atau tidak tersedia di Yahoo Finance."