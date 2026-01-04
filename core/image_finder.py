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