import cv2
import numpy as np
import subprocess
import sys
from pathlib import Path  # 引入 pathlib

import ctypes
# 告訴 Windows 這是高解析度應用程式，不要自動縮放
try:
    ctypes.windll.user32.SetProcessDPIAware()
except:
    pass

# --- 設定區 ---
# 建議：ADB 路徑若包含中文或空白，使用 r"" raw string 比較安全
ADB_PATH = r"D:\LDPlayer\LDPlayer9\adb.exe"
DEVICE_ID = "127.0.0.1:5565"

# --- 全域變數 ---
click_point = None

# 取得目前腳本所在的資料夾路徑 (關鍵修正)
BASE_DIR = Path(__file__).resolve().parent

def get_screenshot():
    """ 透過 ADB 獲取當前畫面 """
    cmd = [ADB_PATH, "-s", DEVICE_ID, "shell", "screencap", "-p"]
    try:
        # 使用 list 格式傳入 cmd，避免 shell=True 的一些轉義問題
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        screenshot_bytes, err = process.communicate(timeout=10)
        
        # Windows 下替換換行符號
        if  sys.platform == 'win32':
            screenshot_bytes = screenshot_bytes.replace(b'\r\n', b'\n')
            
        if len(screenshot_bytes) < 100: 
            print("截圖資料長度不足，請檢查 ADB 連線")
            return None
        
        image_array = np.frombuffer(screenshot_bytes, np.uint8)
        return cv2.imdecode(image_array, cv2.IMREAD_COLOR)
    except Exception as e:
        print(f"截圖發生錯誤: {e}")
        return None

def mouse_callback(event, x, y, flags, param):
    global click_point
    if event == cv2.EVENT_LBUTTONDOWN:
        click_point = (x, y)
        print(f"收到點擊座標: ({x}, {y}) - 按任意鍵完成計算...")

def read_image_safe(path):
    """ 
    安全的讀取圖片函式 (支援中文路徑) 
    強制讀取為彩色 BGR (3通道)，避免 PNG 透明度導致錯誤
    """
    try:
        # 改用 cv2.IMREAD_COLOR (或寫 1)，強制轉為 3 通道
        return cv2.imdecode(np.fromfile(str(path), dtype=np.uint8), cv2.IMREAD_COLOR)
    except Exception as e:
        print(f"讀取圖片失敗: {e}")
        return None


def main():
    print("=== 現有素材偏移量計算器 (Pathlib版) ===")
    
    # --- 修正 1: 設定預設值與輸入邏輯 ---
    default_name = "win_1.PNG"
    user_input = input(f"請輸入圖片檔名 (直接按 Enter 則使用預設值 '{default_name}'): ").strip()
    
    # 如果使用者沒輸入，就用預設值
    filename = user_input if user_input else default_name
    
    # --- 修正 2: 使用 pathlib 鎖定路徑 ---
    # 這樣寫可以確保程式去「腳本所在的資料夾」找圖片，而不是去「終端機的路徑」找
    target_img_path = BASE_DIR / filename

    print(f"正在搜尋檔案: {target_img_path}")

    if not target_img_path.exists():
        print(f"❌ 錯誤：找不到檔案！")
        print(f"請確認 '{filename}' 是否放在資料夾: {BASE_DIR}")
        return

    # 讀取模板圖片
    template = read_image_safe(target_img_path)
    if template is None:
        print("❌ 圖片讀取失敗，可能是格式不支援。")
        return

    # 2. 獲取截圖
    print("正在擷取模擬器畫面...")
    screen = get_screenshot()
    if screen is None: return

    # 3. 進行匹配
    result = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

    # 4. 計算素材中心點
    h, w = template.shape[:2]
    center_x = max_loc[0] + w // 2
    center_y = max_loc[1] + h // 2

    print("-" * 40)
    print(f"系統已找到素材位置！信心度: {max_val:.2f}")
    
    if max_val < 0.8:
        print("⚠️ 警告：信心度過低，可能找錯圖片了！")

    print(f"素材中心座標 (Center): ({center_x}, {center_y})")
    print("-" * 40)
    print("【操作說明】")
    print("請在跳出的視窗中，點擊您「真正想要點擊的位置」。")
    print("點擊後，按任意鍵離開。")
    print("-" * 40)

    # 5. 繪製視覺輔助
    display_img = screen.copy()
    cv2.rectangle(display_img, max_loc, (max_loc[0] + w, max_loc[1] + h), (0, 255, 0), 2)
    cv2.circle(display_img, (center_x, center_y), 5, (0, 0, 255), -1)
    cv2.putText(display_img, "Template Center", (center_x - 40, center_y - 15), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
    

    # ... (前面的程式碼不用動) ...

    # 定義統一的視窗名稱
    WINDOW_NAME = "Offset Calculator"
    
    # 1. 建立視窗，改用 WINDOW_NORMAL (允許手動縮放視窗大小)
    cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
    
    # 2. 強制設定視窗大小為 1280x720 (或是你可以改成更小的 960x540)
    # 這只會改變「顯示」的大小，不會影響坐標計算的準確度，請放心
    cv2.resizeWindow(WINDOW_NAME, 1280, 720)

    # 3. 把視窗移回左上角 (避免它又跑到螢幕外)
    cv2.moveWindow(WINDOW_NAME, 50, 50)
    
    # 4. 綁定滑鼠事件
    cv2.setMouseCallback(WINDOW_NAME, mouse_callback)

    print(f"視窗已開啟 (顯示模式: {1280}x{720})，請點擊目標位置...")
    print("提示：如果視窗還是太大，可以用滑鼠拖拉視窗邊緣來縮放")

    # ... (後面的 while 迴圈不用動) ...
    while True:
        temp_view = display_img.copy()
        
        # 如果有收到點擊，畫出「新的目標點」
        if click_point:
            tx, ty = click_point
            
            # 畫出你要的【紅色】目標點 (BGR: 0, 0, 255)
            cv2.circle(temp_view, (tx, ty), 5, (0, 0, 255), -1)
            
            # 畫黃色連線
            cv2.line(temp_view, (center_x, center_y), (tx, ty), (0, 255, 255), 2)
            
            # 加上文字座標
            cv2.putText(temp_view, f"Target({tx},{ty})", (tx + 10, ty), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
            
        cv2.imshow(WINDOW_NAME, temp_view)
        
        # 等待按鍵 (每 50 毫秒檢查一次)
        key = cv2.waitKey(50)

        # 檢查視窗是否被按 X 關閉
        if cv2.getWindowProperty(WINDOW_NAME, cv2.WND_PROP_VISIBLE) < 1:
            break
            
        # 按 Esc 離開
        if key == 27: 
            break
            
        # 如果已經點擊過，且按了任意鍵 (例如 Space)，就結束
        if click_point is not None and key != -1:
            break

    cv2.destroyAllWindows()

    

    # 7. 最終計算
    if click_point:
        tx, ty = click_point
        offset_x = tx - center_x
        offset_y = ty - center_y

        print("\n" + "="*30)
        print("🎉 計算結果")
        print("="*30)
        print(f"圖片: {filename}")
        print(f"off_x = {offset_x}")
        print(f"off_y = {offset_y}")
        print("="*30)

if __name__ == "__main__":
    main()