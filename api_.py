from api import service
import threading
import time

if __name__=="__main__":
    # threading.Thread(target=service.run_flask()).start()
    # 创建并启动一个线程来运行 Flask 应用
    flask_thread = threading.Thread(target=service.run_flask)
    flask_thread.daemon = True  # 设置为守护线程，以便主程序退出时线程也会退出
    flask_thread.start()

    # 主线程可以执行其他任务或等待
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Exiting program...")