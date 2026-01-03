# core/bot_logic.py
import time
import keyboard  # <--- 1. 匯入 keyboard
import sys       # 用來強制結束
from . import config
from .adb_controller import AdbController
from .image_finder import ImageFinder
from .game_ops import GameOps  # <--- 匯入新夥伴
from .state_manager import StateManager

class GameBot:
    def __init__(self):
        self.adb = AdbController()
        self.finder = ImageFinder()
        self.lose_times = 0
        
        # 初始化操作庫 (把手眼交給它)
        self.ops = GameOps(self.adb, self.finder)
        self.state_mgr = StateManager()
        
        # --- 2. 緊急停止設定 ---
        self.is_running = True  # 旗標：預設為「跑動中」
        
        # 設定 F12 為緊急停止鍵 (您可以改成其他鍵，如 'q', 'esc')
        print("🛡️ 緊急停止監聽中... (隨時按下 F12 可終止程式)")
        keyboard.add_hotkey('F12', self.emergency_stop)
    
    def emergency_stop(self):
        """ 當按下 F12 時會觸發此函式 """
        print("\n\n🛑 !!! 緊急停止觸發 (USER STOP) !!! 🛑")
        self.is_running = False  # 關閉旗標

    def check_stop(self):
        """ 
        [檢查點] 在做大事之前呼叫這個
        如果發現旗標已經變成 False，就拋出例外結束程式 
        """
        if not self.is_running:
            print("🛑 程式依指令停止運作。")
            # 拋出一個自訂錯誤，讓程式直接跳到 main 的 except 區塊
            raise Exception("Emergency Stop")

    # ============================
    # 🎵 第一部分：主旋律
    # ============================
    def solve_unclear_mission(self):
        """ [單次任務邏輯] """
        # 使用 self.ops 來執行動作
        # 1. 滑到底
        self.ops.swipe_to_bottom(count=5)
        
        # 2. 找圖
        screen = self.adb.get_screenshot()
        found, pos = self.finder.find_and_get_pos(screen, "unclear.png")
        
        if found:
            self.adb.tap(pos[0], pos[1])
            return True
        return False

    def run_main_theme(self):
        print("\n🎶 [主旋律] 開始演奏...")
        has_played = False
        
        while True:
            self.check_stop()
            # 1. 找任務
            if not self.solve_unclear_mission():
                break # 沒任務了，主旋律結束
            
            has_played = True
            print("   ⚔️ 進入戰鬥流程...")
            time.sleep(10)

            # 2. 戰鬥設定 (呼叫 ops)
            self.ops.click_target("Auto_off.png")
            time.sleep(1.0)
            self.ops.click_target("Auto_on.png", off_x=-231, off_y=-133)

            # 3. 戰鬥監測 (呼叫 ops)
            result = self.ops.wait_for_battle_result("win.png", "lose.png", "draw.png")

            # 4. 結算 (呼叫 ops)
            if result == "win":
                self.ops.clear_settlement("fin_1.png", "fin_2.png")
                self.ops.clear_settlement("fin_2.png", "fin_3.png")
                self.ops.click_target("fin_3.png")
                self.lose_times=0
            elif result == "lose":
                self.ops.clear_settlement("fin_1.png", "fin_2.png")
                self.ops.clear_settlement("fin_2.png", "fin_4.png")
                self.ops.click_target("fin_4.png")
                self.ops.wait_for_image("change.png")
                self.lose_times += 1
                print(f"已失敗{self.lose_times}次")


            else:
                raise Exception("Battle Timeout")
            
            time.sleep(3)

        return has_played


    # ==========================================
    # 🎹 第二部分：間奏 (接收 n 作為參數)
    # ==========================================
    def run_interlude(self, n):
        """
        間奏：根據次數 n 執行不同動作
        :param n: 當前是第幾回合 (1, 2, 3...)
        """
        print(f"\n🎹 [間奏] 進入第 {n} 回合的切換流程...")
        
        # 1. 點擊 "change.png"
        # 這裡假設一定要點到，所以設一點 timeout
        if not self.ops.click_target("change.png", timeout=5):
            raise Exception("⚠️ 找不到 change 按鈕，跳過間奏")

        time.sleep(2.0) # 等待切換介面

        if n >= 12:
            if self.ops.click_target("B.png"):
                print("成功切換至B卡包 咩咖咩咖")
        else:
            if self.ops.click_target("A.png"):
                print("成功切換至A卡包")


        time.sleep(1.0)

        # (進階版寫法：邊滑邊找，而不是滑到底才找)
        target_img = f"A{n}.png"
        
        # 使用我們之前討論過的「捲動搜尋」邏輯
        # 假設 game_ops 裡有 scroll_and_find_click
        # 或者直接在這裡寫一個小迴圈
        found = False
        for _ in range(7): # 最多滑 5 頁

            if self.ops.click_target(target_img):
                found = True
                print(f"   ✅ 成功點選 {target_img}")
                break
            
            # 沒找到，滑一下
            self.adb.swipe(500, 800, 500, 400, duration=500)
            time.sleep(3.0)
            
        if not found:
            raise Exception("❌ 滑了 5 頁還是沒看到 {target_img}")
        
        print("🎹 間奏結束，準備回到主旋律。\n")
        time.sleep(3.0)
    
    # ==========================================
    # 間章
    # =========================================
    def switch_difficulty(self, diff_img):
        """ [動作] 切換難度 """
        print(f"🔄 正在切換難度目標: {diff_img}")

        self.ops.click_target("back.png")

        self.ops.wait_for_image("diff_1.png")

        target_img = diff_img

        strict_threshold = 0.8
        
        found = False
        for _ in range(5): # 最多滑 5 頁
            self.check_stop()
            if self.ops.click_target(target_img, threshold = strict_threshold):
                found = True
                break
            
            # 沒找到，滑一下
            self.adb.swipe(500, 800, 500, 400, duration=500)
            time.sleep(5.0)
            
        if not found:
            raise Exception("❌ 滑了 5 頁還是沒看到 {target_img}")

        
        # 這裡寫切換難度的邏輯，例如：
        # 1. 回到首頁
        # 2. 點擊難度選單
        # 3. 點擊該難度的圖片

        


    # ==========================================
    # 🎼 總指揮
    # ==========================================
    def routine_main(self):
        # 1. 讀取上次進度
        state = self.state_mgr.load_state()
        start_diff_idx = state["diff_index"]
        start_pkg_n = state["package_n"]

        print(f"📂 讀取存檔: 從 [難度 {start_diff_idx+1}] 的 [第 {start_pkg_n} 關] 開始")
        
        # 直接讀取 config 裡的數字來跑迴圈
        for d_idx, diff_img in enumerate(config.DIFFICULTY_LIST):

            if d_idx < start_diff_idx:
                continue

            print(f"\n📢 ===========================")
            print(f"📢 進入難度 {d_idx + 1} / {len(config.DIFFICULTY_LIST)}")
            print(f"📢 ===========================\n")

            self.switch_difficulty(diff_img)
            current_start_n = start_pkg_n if d_idx == start_diff_idx else 1

            for n in range(current_start_n, config.TOTAL_PACKAGES + 1):
                self.check_stop()

                print(f"\n=== 執行第 {n-1} 號目標 ===")
            
                
                self.run_main_theme()
            
                self.check_stop()

                self.run_interlude(n)

                self.state_mgr.save_state(d_idx, n + 1)

            
            print(f"🎉 全部 {config.TOTAL_PACKAGES} 輪執行完畢，腳本結束！")

            # 重置存檔：準備進入「下一個難度，第 1 關」
            # 這樣如果在這裡斷掉，下次會從下個難度開頭開始
            if d_idx + 1 < len(config.DIFFICULTY_LIST):
                self.state_mgr.save_state(d_idx + 1, 1)

        self.state_mgr.save_state(0, 1)
        # 函式結束，程式就會自然停止
   