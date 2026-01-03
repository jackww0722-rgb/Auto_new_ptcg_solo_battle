import cv2
import numpy as np
import os
from . import config

class ImageFinder:
    def find_and_get_pos(self, screen_img, template_name, threshold=config.CONFIDENCE):
        """
        在畫面中找圖
        :return: (True/False, (x, y)) 回傳中心點座標
        """
        path = config.get_image_path(template_name)
        if not os.path.exists(path):
            print(f"⚠️ 找不到素材檔案: {template_name}")
            return False, None

        template = cv2.imread(path)
        
        # 尺寸防呆
        if template.shape[0] > screen_img.shape[0] or template.shape[1] > screen_img.shape[1]:
            return False, None

        result = cv2.matchTemplate(screen_img, template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)

        if max_val >= threshold:
            h, w = template.shape[:2]
            cx = max_loc[0] + w // 2
            cy = max_loc[1] + h // 2
            return True, (cx, cy)
        
        return False, None