import pandas as pd
import yfinance as yf
import investpy
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import pytz
import traceback

# --- 設定項目 ---

# 1. Googleスプレッドシートの設定
# Google Cloud Platformでダウンロードした認証キーファイル（JSON）のパス
CREDENTIALS_FILE = 'ここに認証キーファイル名を入力.json' 
# 共有設定したGoogleスプレッドシートの名前
SPREADSHEET_NAME = 'ここにスプレッドシート名を入力' 
# スプレッドシート内のワークシート名
WORKSHEET_NAME = 'シート1' 

# 2. 収集対象のシンボル定義
# Yahoo Financeから取得する指標
YF_TICKERS = {
    '米ドル': 'JPY=X',
    'ユーロ': 'EURJPY=X',
    '豪ドル': 'AUDJPY=X',
    '日経平均': '^N225',
    'TOPIX': '^TOPX',
    'NYダウ': '^DJI',
    'REIT': '^TREIT',
    '八十二': '8359.T',
    '原油': 'CL=F',
    'S&P500': '^GSPC',
}

# investing.comから取得する指標
INVESTPY_BONDS = {
    'JGB10Y': 'Japan 10Y',
}

# 3. スプレッドシートの列の順番
# この順番通りにデータが並べられます
COLUMN_ORDER = [
    '日付', '曜日', '米ドル', 'ユーロ', '豪ドル', '日経平均', 'TOPIX', 
    'NYダウ', 'JGB10Y', 'REIT', '八十二', '原油', 'S&P500'
]


def get_latest_close_price(ticker_data, ticker):
    """ yfinanceのデータフレームから最新の終値を取得する """
    try:
        # 'Close'列の最後の有効な値を取得
        return ticker_data['Close'][ticker].iloc[-1]
    except (KeyError, IndexError):
        # データが取得できなかった場合
        return None

def fetch_financial_data():
    """ 各金融データを取得して辞書形式で返す """
    print("データ取得処理を開始します...")
    
    results = {}
    
    # --- Yahoo Financeからデータを取得 ---
    try:
        print(f"Yahoo Financeから {len(YF_TICKERS)} 件のデータを取得中...")
        yf_data = yf.download(list(YF_TICKERS.values()), period='5d', progress=False)
        for name, ticker in YF_TICKERS.items():
            price = get_latest_close_price(yf_data, ticker)
            results[name] = price
            print(f"  - {name}: {price}")
    except Exception as e:
        print(f"[エラー] Yahoo Financeからのデータ取得に失敗しました: {e}")

    # --- investing.comからデータを取得 ---
    try:
        print(f"investing.comから {len(INVESTPY_BONDS)} 件のデータを取得中...")
        today_str = datetime.now().strftime('%d/%m/%Y')
        from_date_str = (datetime.now() - pd.Timedelta(days=7)).strftime('%d/%m/%Y')
        
        for name, bond_name in INVESTPY_BONDS.items():
            bond_data = investpy.get_bond_historical_data(
                bond=bond_name, from_date=from_date_str, to_date=today_str
            )
            price = bond_data['Close'].iloc[-1]
            results[name] = price
            print(f"  - {name}: {price}")
    except Exception as e:
        print(f"[エラー] investing.comからのデータ取得に失敗しました: {e}")

    # --- 日付と曜日を追加 ---
    jst = pytz.timezone('Asia/Tokyo')
    today = datetime.now(jst)
    results['日付'] = today.strftime('%Y/%m/%d')
    results['曜日'] = ['月', '火', '水', '木', '金', '土', '日'][today.weekday()]
    
    print("データ取得完了。")
    return results

def write_to_spreadsheet(data):
    """ 取得したデータをスプレッドシートに書き込む """
    try:
        print("スプレッドシートへの書き込み処理を開始します...")
        # 認証処理
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
        client = gspread.authorize(creds)
        
        # シートを開く
        spreadsheet = client.open(SPREADSHEET_NAME)
        worksheet = spreadsheet.worksheet(WORKSHEET_NAME)
        
        # 指定された順番で1行分のデータを作成
        new_row = [data.get(col_name) for col_name in COLUMN_ORDER]
        
        # 最終行に追記
        worksheet.append_row(new_row)
        
        print("スプレッドシートへの書き込みが正常に完了しました。")
        print(f"書き込まれたデータ: {new_row}")
        
    except Exception as e:
        print(f"[エラー] スプレッドシートへの書き込み中にエラーが発生しました。")
        print(traceback.format_exc())

# --- メイン処理 ---
if __name__ == '__main__':
    print("--- 投資指標自動収集システム ---")
    financial_data = fetch_financial_data()
    
    if financial_data:
        write_to_spreadsheet(financial_data)
    else:
        print("取得できるデータがなかったため、処理を終了します。")
        
    print("--- 処理終了 ---")
