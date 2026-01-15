# run_state.py
import keyboard
import time

class RunState:
    def __init__(self):
        self.is_paused = False
        self.is_running = True # 預留給完全停止用
        
        # 初始化時就開啟監聽
        print("🎮 狀態控制器已啟動 (F12=暫停/恢復)")
        keyboard.add_hotkey('F12', self._toggle)

    def _toggle(self):
        """ 切換暫停狀態 """
        self.is_paused = not self.is_paused
        if self.is_paused:
            print("\n⏸️  [PAUSED] 腳本暫停中... (按 F12 繼續)")
        else:
            print("\n▶️  [RESUME] 恢復執行...")

    def check_stop(self):
        """ 
        這是給所有工人用的檢查站。
        如果現在是暫停，所有呼叫這個函數的人都會卡在這裡發呆。
        """
        while self.is_paused:
            time.sleep(0.2)