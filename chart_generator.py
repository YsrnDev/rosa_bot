import pandas as pd
import mplfinance as mpf
import os
import numpy as np

# Untuk visualisasi SMC yang lebih kompleks, Anda mungkin perlu membuat `addplot` khusus
# atau memproses data SMC untuk menghasilkan garis atau area yang akan diplot.

def generate_chart(df: pd.DataFrame, symbol: str, timeframe: str, smc_data: dict = None) -> str:
    """
    Menghasilkan grafik candlestick dan menyimpannya sebagai gambar,
    dengan opsi untuk menambahkan indikator SMC.
    """
    if df.empty:
        return ""
    
    max_candles_to_plot = 250
    if len(df) > max_candles_to_plot:
        df = df.tail(max_candles_to_plot)
        # Anda juga perlu memotong data SMC agar sesuai dengan df yang sudah dipotong
        if smc_data:
            for key in smc_data:
                if isinstance(smc_data[key], pd.DataFrame):
                    smc_data[key] = smc_data[key].tail(max_candles_to_plot)
                elif isinstance(smc_data[key], pd.Series):
                    smc_data[key] = smc_data[key].tail(max_candles_to_plot)


    filename = f"chart_{symbol}_{timeframe}.png"
    filepath = os.path.join(os.getcwd(), filename)

    mc = mpf.make_marketcolors(up='g', down='r', inherit=True)
    # s = mpf.make_mpf_style(marketcolors=mc, gridcolor='gray', figcolor='whitesmoke', y_on_right=True)
    binance_dark = {
        "base_mpl_style": "dark_background",
        "marketcolors": {
            "candle": {"up": "#3dc985", "down": "#ef4f60"},  
            "edge": {"up": "#3dc985", "down": "#ef4f60"},  
            "wick": {"up": "#3dc985", "down": "#ef4f60"},  
            "ohlc": {"up": "green", "down": "red"},
            "volume": {"up": "#247252", "down": "#82333f"},  
            "vcedge": {"up": "green", "down": "red"},  
            "vcdopcod": False,
            "alpha": 1,
        },
        "mavcolors": ("#ad7739", "#a63ab2", "#62b8ba"),
        "facecolor": "#1b1f24",
        "gridcolor": "#2c2e31",
        "gridstyle": "--",
        "y_on_right": True,
        "rc": {
            "axes.grid": True,
            "axes.grid.axis": "y",
            "axes.edgecolor": "#474d56",
            "axes.titlecolor": "red",
            "figure.facecolor": "#161a1e",
            "figure.titlesize": "x-large",
            "figure.titleweight": "semibold",
        },
        "base_mpf_style": "binance-dark",
    }

    addplots = []

    if smc_data:
        # Contoh: Menambahkan FVG ke grafik
        fvg = smc_data.get("fvg")
        if fvg is not None and not fvg.empty:
            # Filter FVG yang belum dimitigasi atau FVG terakhir
            unmitigated_fvg = fvg[(fvg["MitigatedIndex"].isna()) | (fvg.index == fvg.index.max())]

            for idx, row in unmitigated_fvg.iterrows():
                if np.isnan(row["FVG"]):
                    continue
                
                color = 'blue' if row["FVG"] == 1 else 'red'
                
                # Buat rectangles untuk FVG
                # Anda perlu menentukan koordinat (x, y, width, height)
                # Untuk FVG, ini biasanya area antara Top dan Bottom

                # mplfinance.make_addplot supports plotting lines. For rectangles,
                # you might need to draw them over the plot using matplotlib directly
                # or find a workaround with fill_between if you want to stick to addplot.
                # Here's a simplified approach for FVG as lines or area:

                # Option 1: Plot FVG Top/Bottom as dashed lines
                if row["FVG"] == 1: # Bullish FVG
                    addplots.append(mpf.make_addplot(pd.Series(row['Top'], index=df.index), color=color, linestyle='--', width=0.7, panel=0))
                    addplots.append(mpf.make_addplot(pd.Series(row['Bottom'], index=df.index), color=color, linestyle='--', width=0.7, panel=0))
                elif row["FVG"] == -1: # Bearish FVG
                    addplots.append(mpf.make_addplot(pd.Series(row['Top'], index=df.index), color=color, linestyle='--', width=0.7, panel=0))
                    addplots.append(mpf.make_addplot(pd.Series(row['Bottom'], index=df.index), color=color, linestyle='--', width=0.7, panel=0))
                
                # Option 2 (lebih kompleks): Isi area FVG. Ini memerlukan matplotlib axes
                # yang dapat diakses melalui `ax=` parameter plot.
                # Untuk fungsionalitas ini, kita mungkin perlu memodifikasi cara plot dipanggil
                # atau menggunakan pendekatan yang lebih canggih dengan `matplotlib.pyplot.figure`
                # dan `add_axes` untuk kontrol yang lebih granular.

        # Contoh: Menambahkan Order Block ke grafik
        ob = smc_data.get("ob")
        if ob is not None and not ob.empty:
            unmitigated_ob = ob[ob["MitigatedIndex"].isna()].dropna(subset=["OB"])
            for idx, row in unmitigated_ob.iterrows():
                if np.isnan(row["OB"]):
                    continue
                color = 'green' if row["OB"] == 1 else 'red'
                # OBs juga bisa digambar sebagai garis horizontal atau area
                addplots.append(mpf.make_addplot(pd.Series(row['Top'], index=df.index), color=color, linestyle=':', width=1.0, panel=0))
                addplots.append(mpf.make_addplot(pd.Series(row['Bottom'], index=df.index), color=color, linestyle=':', width=1.0, panel=0))

        # TODO: Tambahkan visualisasi untuk BOS/CHoCH, Liquidity, Swing Highs/Lows
        # Ini bisa menjadi tanda panah, garis, atau area kecil di grafik.
        # Misalnya untuk Swing Highs/Lows:
        swing_hl_data = smc_data.get("swing_hl")
        if swing_hl_data is not None and not swing_hl_data.empty:
            swing_points = swing_hl_data.dropna(subset=["HighLow"])
            for idx, row in swing_points.iterrows():
                if row["HighLow"] == 1: # Swing High
                    # Plot point atau tanda di level Swing High
                    addplots.append(mpf.make_addplot(pd.Series(row['Level'], index=df.index), scatter=True, marker='v', color='purple', markersize=100, panel=0))
                elif row["HighLow"] == -1: # Swing Low
                    # Plot point atau tanda di level Swing Low
                    addplots.append(mpf.make_addplot(pd.Series(row['Level'], index=df.index), scatter=True, marker='^', color='orange', markersize=100, panel=0))


    try:
        mpf.plot(df, type='candle', style=binance_dark, title=f"{symbol} {timeframe}", 
                 update_width_config=dict(candle_linewidth=0.5, candle_width=0.5),
                 ylabel='Harga', savefig=filepath, figscale=1.5, addplot=addplots)
        return filepath
    except Exception as e:
        print(f"Error generating chart for {symbol} {timeframe}: {e}")
        return ""
    