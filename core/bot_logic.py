# core/bot_logic.py
import time
import keyboard  # <--- 1. 匯入 keyboard
import sys       # 用來強制結束
from . import config
from .adb_controller import AdbController
from .image_finder import ImageFinder
from .game_ops import GameOps 
from .state_manager import StateManager
from .debugger import CrashReporter
from .run_state import RunState

class GameBot:
    def __init__(self):

        self.adb = AdbController(adb_path=config.ADB_PATH,
            device_id=config.DEVICE_ID, 
            target_app_package=config.target_app_package)

        self.finder = ImageFinder()
        self.state=RunState()
        self.lose_times = 0
        
        # 初始化操作庫 (把手眼交給它)
        self.ops = GameOps(self.adb, self.finder, self.state)
        self.state_mgr = StateManager()
        self.reporter = CrashReporter(self.adb)
    
    def recover_game_state(self, max_retries=5):
        """ 
        [SOP] 執行完整的錯誤恢復流程 (包含重試機制)
        :param max_retries: 最大重試次數，預設 5 次
        """
        print(f"\n🚑 啟動緊急救援 SOP (最大嘗試次數: {max_retries})")

        for i in range(max_retries):
            current_attempt = i + 1
            print(f"   🔄 [救援嘗試 {current_attempt}/{max_retries}] 執行中...")

            try:
                # 步驟 1: 強制殺掉並重啟 APP (ADB層)
                # (注意：這裡不需要 try-except，因為如果連 ADB 都掛了，通常重試也沒用)
                if current_attempt < max_retries:
                    self.adb.restart_app()
                else:
                    self.adb.restart_emulator()
                    self.adb.restart_app()

                # 步驟 2: 等待遊戲啟動 (Bot層決定時間)
                wait_time = 30
                print(f"      ⏳ 等待遊戲載入 ({wait_time}秒)...")
                time.sleep(float(wait_time))

                # 步驟 3: 嘗試導航回大廳 (Ops層)
                # navigate_back_to_lobby 應該要回傳 True(成功) 或 False(失敗)
                if self.ops.navigate_back_to_lobby():
                    print(f"   ✨ [救援成功] 在第 {current_attempt} 次嘗試成功回到大廳！")
                    return True  # ✅ 成功救回來了，結束這個函式
                else:
                    print(f"      ❌ [失敗] 導航回大廳失敗 (找不到圖或超時)")
                    # 這裡不 return，讓迴圈跑下一次 (也就是再重開一次遊戲)

            except Exception as e:
                # 捕捉所有「預期外」的錯誤 (例如截圖失敗、記憶體不足...)
                print(f"      ⚠️ [異常] 救援過程發生未預期錯誤: {e}")
                # 也不 return，讓迴圈跑下一次

            # 如果還沒達到最後一次，就稍微冷靜一下再重試
            if current_attempt < max_retries:
                print("      ♻️ 準備進行下一次重啟嘗試...")
                time.sleep(5.0)

        # === 如果跑完 for 迴圈都沒有 return True ===
        # 代表救了 3 次都失敗，這時候才真的拋出絕望的錯誤
        print(f"💀 [救援失敗] 已重試 {max_retries} 次仍無法恢復，程式終止。")


        raise Exception("Fatal Error: Game Recovery Failed")



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
        in_lobby, _ = self.finder.find_and_get_pos(screen, "change.png")
        if not in_lobby:
            raise Exception("沒有回到關卡選擇畫面")      
        found, pos = self.finder.find_and_get_pos(screen, "unclear.png")
        
        if found:
            self.adb.tap(pos[0], pos[1])
            return True
        return False

    def run_main_theme(self):
        print("\n🎶 [主旋律] 開始演奏...")
        has_played = False
        
        while True:
            self.state.check_stop()
            # 1. 找任務
            if not self.solve_unclear_mission():
                break # 沒任務了，主旋律結束
            
            has_played = True
            print("   ⚔️ 進入戰鬥流程...")
            time.sleep(5)

            # 2. 戰鬥設定 (呼叫 ops)
            self.ops.click_target("Auto_off.png")
            time.sleep(1.0)
            self.ops.click_target("Auto_on.png", off_x=-231, off_y=-133)

            # 3. 戰鬥監測 (呼叫 ops)
            result = self.ops.wait_for_battle_result("win.png", "lose.png", "draw.png", win_CONFIDENCE=0.4)

            # 4. 結算 (呼叫 ops)
            if result == "win":
                self.ops.clear_settlement("fin_1.png", "fin_2.png", finish_CONFIDENCE = 0.7)
                self.ops.click_target("fin_2.png", threshold = 0.4)
                self.ops.click_target("win_fin.png")
                self.lose_times = 0
                print("===========恭喜通關=============")
            elif result == "lose":
                self.ops.clear_settlement("fin_1.png", "fin_2.png", finish_CONFIDENCE = 0.7)
                self.ops.click_target("fin_2.png", threshold = 0.4) 
                self.ops.wait_for_image("change.png")
                self.lose_times += 1
                print(f"======死亡計數器{self.lose_times}次=======")


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
        if not self.ops.click_target("change.png", timeout=5, threshold=0.4):
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

            if self.ops.click_target(target_img, timeout = 3):
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

        self.ops.wait_for_image("diff_1.png")

        target_img = diff_img

        strict_threshold = 0.8
        
        found = False
        for _ in range(5): # 最多滑 5 頁
            self.state.check_stop()
            if self.ops.click_target(target_img, timeout = 5,  threshold = strict_threshold):
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
        self.adb.wait_for_device_boot()

        print(f"📂 讀取存檔: 從 [難度 {start_diff_idx+1}] 的 [第 {start_pkg_n+1} 關] 開始")
        
        # 直接讀取 config 裡的數字來跑迴圈
        for d_idx, diff_img in enumerate(config.DIFFICULTY_LIST):

            if d_idx < start_diff_idx:
                continue

            print(f"\n📢 ===========================")
            print(f"📢 進入難度 {d_idx + 1} / {len(config.DIFFICULTY_LIST)}")
            print(f"📢 ===========================\n")

            try:
                self.switch_difficulty(diff_img)

            except Exception as e:
                print(f"⚠️ 難度切換失敗 ({e})，嘗試救援...")
                self.recover_game_state()     # 重開並回到大廳
                self.switch_difficulty(diff_img) # 再試一次切換

                #self.restart_game()

            
            current_start_n = start_pkg_n - 1 if d_idx == start_diff_idx else 1

            while current_start_n < config.TOTAL_PACKAGES + 1:
                self.state.check_stop()
                try:
                    print(f"\n=== 執行第 {current_start_n} 號目標 ===")

                    self.run_interlude(n=current_start_n)
                
                    self.run_main_theme()
                
                    self.state.check_stop()

                    self.state_mgr.save_state(d_idx, current_start_n)

                    current_start_n += 1
                    
                except Exception as e:
                    # === 🔥 發生意外 (斷線、閃退、卡住) ===
                    error_msg = str(e)

                    # 錯誤 -> 啟動 SOP
                    print(f"⚠️ 發生錯誤: {error_msg}")
                    print("♻️ 執行救援 SOP...")
                    self.reporter.save_report(e, context=f"Diff_{d_idx}_Level_{current_start_n}")
                    # 步驟 1: 重開遊戲 + 回到大廳 (我們剛剛寫好的功能)
                    self.recover_game_state()

                    
                    # 步驟 2: 確保難度正確
                    # (因為重開後預設可能是別的難度，保險起見再切一次)
                    try:
                        self.switch_difficulty(diff_img)
                    except:
                        pass # 如果已經在該難度可能會報錯，忽略之

                    print(f"🔄 狀態已恢復，準備重試第 {current_start_n} 關...")
                    time.sleep(3)
                    # 這裡沒有 n+=1，所以迴圈會自動重打這一關

            self.ops.click_target("back.png")
            
            print(f"🎉 {config.TOTAL_PACKAGES} 包攻略完畢，切換難度！")

            # 重置存檔：準備進入「下一個難度，第 1 關」
            # 這樣如果在這裡斷掉，下次會從下個難度開頭開始
            if d_idx + 1 < len(config.DIFFICULTY_LIST):
                self.state_mgr.save_state(d_idx + 1, 1)

        self.state_mgr.save_state(0, 1)
        # 函式結束，程式就會自然停止
   