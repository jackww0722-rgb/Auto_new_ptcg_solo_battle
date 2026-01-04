from pathlib import Path
import json


# --- 參數設定 ---
CONFIDENCE = 0.6
SCROLL_WAIT = 2.0
LOOP_DELAY = 1.0

# --- 路徑設定 (改用 Pathlib) ---
# 1. 取得這隻檔案 (config.py) 的絕對路徑
CURRENT_FILE = Path(__file__).resolve()

# 2. 取得 core 資料夾 (config.py 的父層)
CORE_DIR = CURRENT_FILE.parent

# 3. 取得專案根目錄 (core 的父層 -> AutoBot)
ROOT_DIR = CORE_DIR.parent

# 4. 定義 assets 資料夾路徑
ASSETS_DIR = ROOT_DIR / "assets"


TOTAL_PACKAGES=13
START_AT=1

DIFFICULTY_LIST = ["diff_1.png", "diff_2.png", "diff_3.png", "diff_4.png"]
STATE_FILE = "bot_state.json"



# --- ADB 環境設定 ---
# 這裡維持原始字串即可，因為 subprocess 接收字串指令最穩定
ADB_PATH = r"adb"
DEVICE_ID = None

CONFIG_FILE =  ROOT_DIR / "config.json"
if CONFIG_FILE.exists():
    try:
        # 使用 pathlib 的讀取方法，簡潔有力
        content = CONFIG_FILE.read_text(encoding="utf-8")
        data = json.loads(content)
        
        # 讀取設定
        ADB_PATH = data.get("adb_path", ADB_PATH)
        DEVICE_ID = data.get("device_ID", DEVICE_ID)
        
        print(f"✅ 已載入外部設定 (Path: {CONFIG_FILE.resolve()})")
    except Exception as e:
        print(f"⚠️ 讀取 config.json 失敗: {e} (將使用預設值)")
else:
    print("ℹ️ 找不到 config.json，使用程式內建預設值。")




def get_image_path(filename):
    """
    組合檔名並回傳字串路徑
    (為了讓 OpenCV 能讀取，最後轉為 str 是最保險的做法)
    """
    target_path = ASSETS_DIR / filename
    return str(target_path)

# --- 測試用 (如果您直接執行這個檔案，會印出路徑檢查對不對) ---
if __name__ == "__main__":
    print(f"專案根目錄: {ROOT_DIR}")
    print(f"素材目錄: {ASSETS_DIR}")
    print(f"測試圖片路徑: {get_image_path('target_A.png')}")