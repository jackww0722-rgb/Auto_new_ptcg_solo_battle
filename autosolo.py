import time
import gc
# 這裡匯入 traceback 是為了萬一報錯可以看到詳細原因
import traceback 
from core import config
from core.bot_logic import GameBot

def main():
    print("=================================")
    print(f"🤖 自動化腳本啟動 (單次任務版)")
    print(f"📱 目標裝置: {config.DEVICE_ID}")
    print(f"📂 圖片目錄: {config.ASSETS_DIR}")
    print("=================================")

    bot = GameBot()

    try:
        # === 核心修改：移除 while True 迴圈 ===
        # 直接呼叫一次主流程，跑完 A1~A13 就會自動往下走
        bot.routine_main()

        print("\n✅ 所有任務已執行完畢，程式即將結束。")

    except KeyboardInterrupt:
        print("\n👋 使用者強制停止腳本")
    except Exception as e:
        print("\n❌ 發生未預期錯誤:")
        traceback.print_exc()
    finally:
        # 不管成功或失敗，最後都停下來讓您看一下結果，不會馬上關視窗
        input("按 Enter 鍵結束程式...")

if __name__ == "__main__":
    main()