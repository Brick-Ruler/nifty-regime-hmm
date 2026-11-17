"""
Data Ingestion Module for Nifty 50 and India VIX
=================================================
This script downloads daily historical data for:
1. Nifty 50 Index (^NSEI)
2. India VIX (^INDIAVIX)

It cleans the data, aligns dates, computes daily returns and volatility,
and saves the result to a CSV file for our regime model.
"""

import os
import pandas as pd
import numpy as np
import yfinance as yf

def fetch_indian_market_data(start_date="2012-01-01", end_date=None, output_path="nifty_vix_data.csv"):
    print(f"Downloading Nifty 50 (^NSEI) and India VIX (^INDIAVIX) from {start_date}...")
    
    # Download data from Yahoo Finance
    nifty = yf.download("^NSEI", start=start_date, end=end_date, progress=False, auto_adjust=True)
    vix = yf.download("^INDIAVIX", start=start_date, end=end_date, progress=False, auto_adjust=True)
    
    # Extract Close prices (flatten columns if MultiIndex)
    if isinstance(nifty.columns, pd.MultiIndex):
        nifty_close = nifty['Close']['^NSEI'] if '^NSEI' in nifty['Close'] else nifty['Close'].iloc[:, 0]
        nifty_high = nifty['High']['^NSEI'] if '^NSEI' in nifty['High'] else nifty['High'].iloc[:, 0]
        nifty_low = nifty['Low']['^NSEI'] if '^NSEI' in nifty['Low'] else nifty['Low'].iloc[:, 0]
    else:
        nifty_close = nifty['Close']
        nifty_high = nifty['High']
        nifty_low = nifty['Low']

    if isinstance(vix.columns, pd.MultiIndex):
        vix_close = vix['Close']['^INDIAVIX'] if '^INDIAVIX' in vix['Close'] else vix['Close'].iloc[:, 0]
    else:
        vix_close = vix['Close']
        
    # Combine into a single DataFrame aligned on date
    df = pd.DataFrame({
        'nifty_close': nifty_close,
        'nifty_high': nifty_high,
        'nifty_low': nifty_low,
        'vix_close': vix_close
    }).dropna()

    # Feature Engineering (The "Clues")
    # 1. Daily percentage return (%)
    df['nifty_pct_return'] = df['nifty_close'].pct_change() * 100.0
    
    # 2. Daily log return (standard in quantitative finance)
    df['nifty_log_return'] = np.log(df['nifty_close'] / df['nifty_close'].shift(1))
    
    # 3. Daily change in India VIX (points)
    df['vix_change'] = df['vix_close'].diff()
    
    # 4. Daily percentage change in India VIX (%)
    df['vix_pct_change'] = df['vix_close'].pct_change() * 100.0
    
    # 5. 20-Day Realized Annualized Volatility (%)
    # (FRM concept: Daily standard deviation scaled to annual by sqrt(252 trading days))
    df['realized_vol_20d'] = df['nifty_pct_return'].rolling(window=20).std() * np.sqrt(252)

    # Drop the first 20 rows that now have NaN due to rolling window
    df = df.dropna()
    
    # Save to disk
    df.to_csv(output_path)
    print(f"Data saved successfully to {output_path}!")
    print(f"Total Trading Days: {len(df)}")
    print(f"Date Range: {df.index[0].strftime('%Y-%m-%d')} to {df.index[-1].strftime('%Y-%m-%d')}")
    print("\nSample Preview (First 5 Days):")
    print(df[['nifty_close', 'vix_close', 'nifty_pct_return', 'vix_pct_change']].head())
    
    return df

if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    csv_file = os.path.join(script_dir, "nifty_vix_data.csv")
    fetch_indian_market_data(output_path=csv_file)
