# core/game_ops.py
import time
import keyboard
from dataclasses import dataclass
from . import config
from .image_finder import ImageFinder
from .adb_controller import AdbController
from .run_state import RunState
from typing import Optional, Tuple
import contextlib
import io

@dataclass
class CriticalEvent:
    trigger_img: str
    action_img: str
    desc: str

class GameOps:
    def __init__(self, adb:AdbController, finder:ImageFinder, run_state:RunState):
        # 接收外部傳進來的手和眼
        self.adb = adb
        self.finder = finder
        self.state = run_state



    CRITICAL_EVENTS = [
            CriticalEvent(
                trigger_img="resume_battle.png",
                action_img="resume_battle_cancel.png",
                desc="取消續戰",
            ),
            CriticalEvent(
                trigger_img="UI_error.png",
                action_img="UI_error_cancel.png",
                desc="模擬器 UI 錯誤",
            ),
        ]

    # --- 基礎工具 ---
    def swipe_to_bottom(self, count=5):
        """
        [工具] 快速連續往下滑動 (模擬手指快速撥動)
        :param count: 滑動次數 (預設 5 次，通常夠滑到底了)
        """
        
        for _ in range(count):
            # (500, 900) -> (500, 200)
            # 手指從下往上滑 = 畫面往下捲
            # duration=150 = 快速撥動 (會有慣性)
            self.state.check_stop()
            self.adb.swipe(500, 900, 500, 200, duration=500)
            
            # ⚠️ 重要：短暫休息，避免指令連發導致失效
            time.sleep(0.5) 
        
        # 滑完後，因為有慣性，畫面可能還在動
        # 多等一下讓畫面完全靜止，這樣接下來的截圖才不會模糊
        print("   🛑 等待畫面靜止...")
        time.sleep(1.5)


    def click_target(self, img_name, off_x=0, off_y=0, timeout=30, threshold=0.8):  #等待並點擊
        """
        [升級版] 偵測圖片並點擊 (支援等待模式)
        :param img_name: 圖片檔名
        :param off_x, off_y: 偏移量
        :param timeout: 等待超時時間 (秒)。
        填 0 = 看一眼沒看到就走 (即時模式)。
        填 10 = 最多等 10 秒，期間一出現就點 (等待模式)。
        """
        self.state.check_stop()

        print(f"🔍 尋找目標 {img_name}...")
        
        start_time = time.time() # 紀錄開始時間

        while True:
            # 1. 截圖
            screen = self.adb.get_screenshot()
            
            if screen is not None:
                # 2. 找圖
                found, pos = self.finder.find_and_get_pos(screen, img_name, threshold=threshold)
                
                if found:
                    cx, cy = pos
                    final_x = cx + off_x
                    final_y = cy + off_y
                    
                    print(f"   ✅ 發現目標！")
                    self.adb.tap(final_x, final_y)
                    return True # 任務完成，跳出

            # 3. 檢查是否超時
            elapsed_time = time.time() - start_time
            if elapsed_time > timeout:
                # 時間到了還沒找到
                if timeout > 0:
                    print(f"   ⌛ 等待超時 ({timeout}s)，未發現 {img_name}")
                return False

            # 4. 還沒超時，休息一下再試 (避免 CPU 飆高)
            time.sleep(1.0)


    def clear_settlement(self, confirm_img, finish_condition_img, max_retry=30, finish_CONFIDENCE = 0.8):
        """
        [智慧結算 2.0] 
        1. 先等待確認按鈕出現 (避免讀取太久導致次數耗盡)
        2. 出現後才開始連續點擊，直到結束畫面出現
        
        :param initial_timeout: 初始等待時間 (秒)，預設 60 秒等待結算載入
        """
        print(f"🏁 [結算流程] 啟動！等待 {confirm_img} 出現...")

        # --- 階段一：等待畫面載入 ---
        #       
        if self.wait_for_image(confirm_img):
            print("✅ 結算畫面已載入，開始連續點擊流程！")
            

        # --- 階段二：開始執行點擊 (您的原始邏輯) ---

        print(f"   -> 瘋狂點擊確認")      
        for i in range(max_retry):
            self.state.check_stop()
            screen = self.adb.get_screenshot()
            
            # 點擊確認    
            if self.click_target(confirm_img, timeout=5):
                time.sleep(1) # 點擊後稍微快一點
            else:
                time.sleep(1)

            # 檢查結束條件
            is_finished, _ = self.finder.find_text_button(screen, finish_condition_img, threshold = finish_CONFIDENCE)
            if is_finished:             
                return True


        print("⚠️ 警告：超過點擊次數上限，仍未回到首頁")
        return False
    

    def wait_for_battle_result(self, win_img, lose_img, draw_img, timeout=1200, win_CONFIDENCE = config.CONFIDENCE):
        """
        [智慧戰鬥監測]
        持續檢查畫面，直到出現結果。
        - 看到 WIN -> 點擊它 -> 回傳 "win"
        - 看到 LOSE -> 不動作 -> 回傳 "lose"
        """
        print(f"⚔️ 戰鬥監測中")
        time.sleep(10)
        start_time = time.time()
        
        while (elapsed := time.time() - start_time) < timeout:
            self.state.check_stop()

            print(f"     已等待{elapsed:.1f}秒", end = "\r", flush=True)
            screen = self.adb.get_screenshot()
            if screen is None: continue
            
            # --- 情況 A: 贏了 (Win) ---
            is_win = False

            with contextlib.redirect_stdout(io.StringIO()): 
                is_win = self.click_target(img_name = win_img, timeout = 5, threshold = win_CONFIDENCE)

            if is_win: # 關鍵動作：贏了就點下去！
                print(f"🎉 偵測到勝利 ({win_img})！")                                
                time.sleep(1.0) # 點完稍微等一下，確保遊戲接收到
                
                return "win"

            # --- 情況 B: 輸了 (Lose) ---
            is_lose, _ = self.finder.find_and_get_pos(screen, lose_img)
            is_draw, _ = self.finder.find_and_get_pos(screen, draw_img)


            if is_lose or is_draw:
                print(f"💀 偵測到失敗 ({lose_img}) -> 僅記錄，不點擊")
                
                # 關鍵動作：輸了不點擊，直接回傳
                return "lose"
            

            
            # 都沒看到，休息一下再看
            time.sleep(10.0)
            
        print("⚠️ 戰鬥監測超時")
        return None
    

    def wait_for_image(self, target_img, timeout=30):
        """
        [工具] 單純等待某張圖片出現 (不做任何點擊)
        :param timeout: 最多等幾秒，預設 10 秒
        :return: True (有等到) / False (超時沒等到)
        """
        print(f"   ⏳ [Ops] 等待圖片出現: {target_img} ...")
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            # 1. 檢查緊急停止
            self.state.check_stop()
            
            # 2. 截圖並找圖
            screen = self.adb.get_screenshot()
            found, _ = self.finder.find_and_get_pos(screen, target_img)
            
            if found:
                print(f"   ✅ 看到 {target_img} 了！")
                return True
            
            # 3. 稍微睡一下再檢查
            time.sleep(0.5)
            
        print(f"   ⚠️ 等待 {target_img} 超時 ({timeout}s)")
        return False


    def navigate_back_to_lobby(self):
        """ [技能] 從標題畫面一路點回大廳 (包含特殊事件等待) """
        try:
            print("      👆 [Ops] 正在嘗試從標題畫面回到大廳...")
            
            # 1. 檢查標題畫面
            if not self.click_target("title_screen.png", timeout=300):
                print("      ❌ 未偵測到標題畫面")
                return False

            # 2. 點擊進入
            
            time.sleep(5.0)

            # === 🔥 新增：處理「只能等待」的特殊事件 ===
            # 設定一個檢查迴圈，假設最多等 2 分鐘 (120秒)
            wait_limit = 120 
            start_wait = time.time()


            
            while time.time() - start_wait < wait_limit: #找大廳
                print("正在尋找大廳...")
                screenshot = self.adb.get_screenshot()

                has_lobby, lobby_pos = self.finder.find_text_button(screenshot, "battle_1.png")

                # === 情境：什麼問題都沒有 直接進戰鬥流程 ===
                if has_lobby:
                    self.adb.tap(*lobby_pos)
                    if self.click_target("battle_2.png", timeout = 5):
                        time.sleep(1)
                        self.click_target("battle_3.png", timeout = 5)
                        return True
                     
                # === 情境：特殊事件 ===
                if self.handle_critical_events(screenshot):
                    continue                
                
                
            print("      ❌ 等待超時：無法回到大廳")
            return False

        except Exception as e:
            print(f"      ⚠️ [OpsError] 導航過程出錯: {e}")
            return False


    def handle_critical_events(self, screenshot) -> bool:
        for event in self.CRITICAL_EVENTS:
            happen_error,_ = self.finder.find_and_get_pos(screenshot, event.trigger_img, threshold=0.5)
            if happen_error:
                print(f"⚠️ 偵測到{event.desc}")
                self.click_target(event.action_img)
                time.sleep(2)
                return True
        return False












