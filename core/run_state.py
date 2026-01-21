# run_state.py
import keyboard
import time
from .state_manager import StateManager
import datetime

class RunState:
    def __init__(self, run_state:StateManager):
        self.is_paused = False
        self.is_running = True # 預留給完全停止用
        self.state_mgr = run_state
        # 初始化時就開啟監聽
        print("🎮 狀態控制器已啟動 (F12=暫停/恢復)")
        keyboard.add_hotkey('F12', self._toggle)

    def _toggle(self):
        """ 切換暫停狀態 """
        self.is_paused = not self.is_paused
        if self.is_paused:
            print("\n⏸️  [PAUSED] 腳本暫停中... (按 F12 繼續)", flush = True)
            state = self.state_mgr.load_state()
            start_diff_idx = state["diff_index"]
            start_pkg_n = state["package_n"]
            print(f"目前進度 難度{start_diff_idx}, 第{start_pkg_n+1}包")

        else:
            print("\n▶️  [RESUME] 恢復執行...")

    def check_stop(self):
        """ 
        這是給所有工人用的檢查站。
        如果現在是暫停，所有呼叫這個函數的人都會卡在這裡發呆。
        """
        while self.is_paused:
            now = datetime.datetime.now()
            print(f"   暫停中,現在時間{now.strftime('%H:%M')}",end = "\r", flush = True)
            time.sleep(0.2)