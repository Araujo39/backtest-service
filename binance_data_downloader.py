#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Binance Data Downloader - Download real OHLCV data from Binance Public Data
Source: https://data.binance.vision/
"""

import requests
import zipfile
import io
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
import time

class BinanceDataDownloader:
    """
    Download historical OHLCV data from Binance Public Data.
    
    Data structure:
    - Spot: https://data.binance.vision/?prefix=data/spot/
    - Futures: https://data.binance.vision/?prefix=data/futures/
    
    Available intervals: 1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d, 3d, 1w, 1mo
    """
    
    BASE_URL = "https://data.binance.vision/data"
    
    def __init__(self, market_type='spot', data_type='klines'):
        """
        Args:
            market_type: 'spot' or 'futures'
            data_type: 'klines' (OHLCV candles)
        """
        self.market_type = market_type
        self.data_type = data_type
        self.base_path = Path(f"DATA_{market_type}")
        self.base_path.mkdir(exist_ok=True)
    
    def download_monthly_data(self, symbol, interval, year, month):
        """
        Download one month of data for a symbol.
        
        Example URL:
        https://data.binance.vision/data/spot/monthly/klines/BTCUSDT/1m/BTCUSDT-1m-2024-01.zip
        
        Args:
            symbol: Trading pair (e.g., 'BTCUSDT')
            interval: Timeframe (e.g., '15m', '1h', '1d')
            year: Year (e.g., 2024)
            month: Month (1-12)
        
        Returns:
            DataFrame with columns: [timestamp, open, high, low, close, volume]
        """
        month_str = str(month).zfill(2)
        filename = f"{symbol}-{interval}-{year}-{month_str}.zip"
        
        url = f"{self.BASE_URL}/{self.market_type}/monthly/{self.data_type}/{symbol}/{interval}/{filename}"
        
        print(f"📥 Downloading: {filename}...", end=" ")
        
        try:
            response = requests.get(url, timeout=60)
            response.raise_for_status()
            
            # Extract CSV from ZIP
            with zipfile.ZipFile(io.BytesIO(response.content)) as z:
                csv_filename = filename.replace('.zip', '.csv')
                with z.open(csv_filename) as f:
                    df = pd.read_csv(
                        f,
                        header=None,
                        names=[
                            'timestamp', 'open', 'high', 'low', 'close', 'volume',
                            'close_time', 'quote_volume', 'trades', 
                            'taker_buy_base', 'taker_buy_quote', 'ignore'
                        ]
                    )
            
            # Keep only OHLCV columns
            df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
            
            # Convert timestamp to datetime
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            print(f"✅ ({len(df)} candles)")
            
            return df
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                print(f"❌ Not found")
                return None
            else:
                print(f"❌ HTTP Error: {e}")
                return None
        except Exception as e:
            print(f"❌ Error: {e}")
            return None
    
    def download_symbol_history(
        self, 
        symbol, 
        interval='15m', 
        start_date=None, 
        end_date=None,
        max_candles=None
    ):
        """
        Download historical data for a symbol across multiple months.
        
        Args:
            symbol: Trading pair (e.g., 'BTCUSDT')
            interval: Timeframe (e.g., '15m', '1h', '1d')
            start_date: Start date (datetime or 'YYYY-MM-DD')
            end_date: End date (datetime or 'YYYY-MM-DD')
            max_candles: Maximum number of candles to return (most recent)
        
        Returns:
            DataFrame with combined data
        """
        # Default: Last 6 months
        if end_date is None:
            end_date = datetime.now()
        elif isinstance(end_date, str):
            end_date = datetime.strptime(end_date, '%Y-%m-%d')
        
        if start_date is None:
            start_date = end_date - timedelta(days=180)  # 6 months
        elif isinstance(start_date, str):
            start_date = datetime.strptime(start_date, '%Y-%m-%d')
        
        print(f"\n🔍 Downloading {symbol} ({interval}) from {start_date.date()} to {end_date.date()}")
        print("-" * 80)
        
        all_data = []
        current_date = start_date
        
        while current_date <= end_date:
            df = self.download_monthly_data(
                symbol=symbol,
                interval=interval,
                year=current_date.year,
                month=current_date.month
            )
            
            if df is not None and len(df) > 0:
                all_data.append(df)
            
            # Move to next month
            if current_date.month == 12:
                current_date = current_date.replace(year=current_date.year + 1, month=1)
            else:
                current_date = current_date.replace(month=current_date.month + 1)
            
            # Rate limiting
            time.sleep(0.5)
        
        if not all_data:
            print(f"\n❌ No data found for {symbol}")
            return None
        
        # Combine all months
        combined_df = pd.concat(all_data, ignore_index=True)
        
        # Sort by timestamp
        combined_df = combined_df.sort_values('timestamp').reset_index(drop=True)
        
        # Remove duplicates
        combined_df = combined_df.drop_duplicates(subset='timestamp').reset_index(drop=True)
        
        # Limit to max_candles (most recent)
        if max_candles is not None and len(combined_df) > max_candles:
            combined_df = combined_df.tail(max_candles).reset_index(drop=True)
        
        print(f"\n✅ Total: {len(combined_df)} candles")
        
        return combined_df
    
    def save_symbol_data(self, symbol, interval='15m', max_candles=2000):
        """
        Download and save data for a symbol.
        
        Args:
            symbol: Trading pair (e.g., 'BTCUSDT')
            interval: Timeframe (e.g., '15m')
            max_candles: Maximum number of candles to save
        """
        df = self.download_symbol_history(
            symbol=symbol,
            interval=interval,
            max_candles=max_candles
        )
        
        if df is not None:
            output_file = self.base_path / f"{symbol}.csv"
            df.to_csv(output_file, index=False)
            print(f"💾 Saved to: {output_file} ({len(df)} candles)")
            return True
        
        return False
    
    def download_multiple_symbols(
        self, 
        symbols, 
        interval='15m', 
        max_candles=2000
    ):
        """
        Download data for multiple symbols.
        
        Args:
            symbols: List of trading pairs
            interval: Timeframe
            max_candles: Maximum number of candles per symbol
        """
        print(f"\n{'='*80}")
        print(f"🚀 BINANCE DATA DOWNLOADER")
        print(f"{'='*80}")
        print(f"Market: {self.market_type.upper()}")
        print(f"Interval: {interval}")
        print(f"Symbols: {len(symbols)}")
        print(f"Max candles per symbol: {max_candles}")
        print(f"{'='*80}\n")
        
        results = {
            'success': [],
            'failed': []
        }
        
        for i, symbol in enumerate(symbols):
            print(f"\n[{i+1}/{len(symbols)}] Processing {symbol}...")
            
            try:
                success = self.save_symbol_data(
                    symbol=symbol,
                    interval=interval,
                    max_candles=max_candles
                )
                
                if success:
                    results['success'].append(symbol)
                else:
                    results['failed'].append(symbol)
                    
            except Exception as e:
                print(f"❌ Error processing {symbol}: {e}")
                results['failed'].append(symbol)
            
            # Rate limiting between symbols
            time.sleep(1)
        
        # Summary
        print(f"\n{'='*80}")
        print(f"📊 SUMMARY")
        print(f"{'='*80}")
        print(f"✅ Success: {len(results['success'])} symbols")
        print(f"❌ Failed: {len(results['failed'])} symbols")
        
        if results['failed']:
            print(f"\nFailed symbols: {', '.join(results['failed'])}")
        
        print(f"{'='*80}\n")
        
        return results


def main():
    """
    Example usage: Download real data from Binance.
    """
    # Symbols to download
    symbols = [
        'BTCUSDT',
        'ETHUSDT',
        'BNBUSDT',
        'SOLUSDT',
        'ADAUSDT',
        'ATOMUSDT',
        'AVAXUSDT',
        'DOGEUSDT',
        'MATICUSDT',
        'XRPUSDT'
    ]
    
    # Initialize downloader
    downloader = BinanceDataDownloader(market_type='spot')
    
    # Download data (15m interval, last 2000 candles)
    results = downloader.download_multiple_symbols(
        symbols=symbols,
        interval='15m',
        max_candles=2000
    )
    
    print("✅ Download completed!")
    print(f"📁 Data saved to: {downloader.base_path}/")


if __name__ == "__main__":
    main()
