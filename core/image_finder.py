import cv2
import numpy as np
from . import config

class ImageFinder:
    def __init__(self):
        pass

    def cv2_imread_safe(self, file_path):
        """ 
        [工具] 解決 Windows 路徑含有中文或特殊字元無法讀取的問題 
        這是 find_and_get_pos 需要呼叫的幫手函式
        """
        try:
            # 先用 numpy 讀取原始數據 (避開路徑編碼問題)
            img_array = np.fromfile(str(file_path), dtype=np.uint8)
            # 再解碼成圖片
            img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
            return img
        except Exception as e:
            print(f"⚠️ 讀取圖片失敗: {file_path} | 錯誤: {e}")
            return None

    def find_and_get_pos(self, screen, template_name, threshold=config.CONFIDENCE):
        """ 
        主要找圖邏輯，包含完整的防呆機制 
        """
        # 1. 組合完整路徑
        template_path = config.ASSETS_DIR / template_name
        
        # 2. 呼叫上面的安全讀取法 (這行原本報錯，因為找不到上面的函式)
        template = self.cv2_imread_safe(template_path)
        
        # 3. 防呆檢查：圖片讀取失敗
        if template is None:
            print(f"❌ [Error] 找不到或無法讀取圖片: {template_path}")
            return False, None

        # 4. 防呆檢查：螢幕截圖失敗
        if screen is None:
             print("❌ [Error] 螢幕截圖失敗 (Screen is None)，請檢查 ADB 連線")
             return False, None

        # 5. 防呆檢查：尺寸不合
        # (一定要在確認 template 不是 None 之後才能做)
        if template.shape[0] > screen.shape[0] or template.shape[1] > screen.shape[1]:
            # print(f"⚠️ [Warning] 圖片比螢幕大: {template_name}")
            return False, None

        # 6. 開始匹配
        result = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
        
        if max_val >= threshold:
            h, w = template.shape[:2]
            center_x = max_loc[0] + w // 2
            center_y = max_loc[1] + h // 2
            return True, (center_x, center_y)
            
        return False, None
    
    def find_text_button(self, screen, template_name, threshold=0.7):
        """
        [專門找文字] 使用二值化 (Binarization) 處理
        這能有效解決「字體顏色太淡」或「背景半透明」的問題
        """
        # 1. 讀取模板 (強制轉灰階)
        template_path = config.ASSETS_DIR / template_name
        if not template_path.exists():
            print(f"❌ 找不到模板: {template_name}")
            return False, None
            
        template = cv2.imread(str(template_path), cv2.IMREAD_GRAYSCALE)
        
        # 2. 將螢幕截圖也轉灰階
        screen_gray = cv2.cvtColor(screen, cv2.COLOR_BGR2GRAY)

        # === 🔥 關鍵魔法：二值化處理 ===
        # 設定一個切分點 (例如 180)，低於這個亮度(字體)變 255(白)，高於這個亮度(背景)變 0(黑)
        # THRESH_BINARY_INV 代表「反向」，讓深色字體變亮，淺色背景變暗
        _, screen_bin = cv2.threshold(screen_gray, 180, 255, cv2.THRESH_BINARY_INV)
        _, template_bin = cv2.threshold(template, 180, 255, cv2.THRESH_BINARY_INV)

        # (Debug用) 如果您想看處理完長怎樣，可以把這行打開存下來看
        # cv2.imwrite(f"debug_bin_{template_name}", screen_bin)

        # 3. 進行匹配
        result = cv2.matchTemplate(screen_bin, template_bin, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

        if max_val >= threshold:
            # 計算中心點
            h, w = template.shape
            center_x = max_loc[0] + w // 2
            center_y = max_loc[1] + h // 2
            print(f"   🔍 [TextMode] 找到 {template_name} (信心度: {max_val:.2f})")
            return True, (center_x, center_y)
        else:
            return False, None