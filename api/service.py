from flask import Flask
from api.tronagent import tronagent


app=Flask(__name__)
app.register_blueprint(tronagent,url_prefix='/tronagent')



@app.route('/hello',methods=['POST','GET'])
def hello():
    return "Welcome to the Flask API!"

def run_flask():
    while True:
        try:
            # 启动 Flask 应用
            print("Starting Flask server...")
            app.run(host="0.0.0.0", port=4999, debug=False, use_reloader=False, threaded=True)
        except Exception as e:
            print(f"Flask server crashed with error: {e}")
        finally:
            print("Restarting Flask server in 5 seconds...")
            time.sleep(5)
