import random
def generate_action(num_moves=None):
    def generate_random_move():
        action_type = random.choice(["stand", "sit", "twist"])
        if action_type == "stand":
            return {
                "function_name": "TronAction",
                "args": {"stand": {}}
            }
        elif action_type == "sit":
            return {
                "function_name": "TronAction",
                "args": {"sit": {}}
            }
        elif action_type == "twist":
            return {
                "function_name": "TronAction",
                "args": {
                    "twist": {
                        "x": random.uniform(-1, 1),
                        "y": random.uniform(-1, 1),
                        "z": random.uniform(-1, 1),
                        "step": random.randint(1, 3)
                    }
                }
            }

    # 随机生成舞蹈动作的数量，控制在15个以内
    if num_moves is None:
        num_moves = random.randint(5, 15)
    action_moves = [generate_random_move() for _ in range(num_moves)]
    return action_moves
def find_color(string):
    string=string.lower()
    effect=1
    if any(i in string for i in ["red","红"]):
        effect=1
    if any(i in string for i in ["green","绿"]):
        effect=2
    if any(i in string for i in ["blue","蓝"]):
        effect=3
    if any(i in string for i in ["cyan","青"]):
        effect=4
    if any(i in string for i in ["purple","紫"]):
        effect=5
    if any(i in string for i in ["yellow","黄"]):
        effect=6
    if any(i in string for i in ["white","白"]):
        effect=7
    if any(i in string for i in ["低频","low freqency","slow","慢"]):
        return effect+7
    if any(i in string for i in ["高频","gihgh freqency","fast","快"]):
        return effect+14
    return effect
# 定义关键词和对应的解析规则
base_action_keywords = {
    "stand": [{"function_name": "TronAction", "args": {"stand": {}}}],
    "sit": [{"function_name": "TronAction", "args": {"sit": {}}}],
    "move": [{"function_name": "TronAction", "args": {"twist": {"x": random.uniform(0.8, 1), "y": 0, "z": 0, "step": 1}}}],
    "left": [{"function_name": "TronAction", "args": {"twist": {"x": 0,  "y": random.uniform(0.8, 1), "z": 0, "step": 1}}}],
    "right": [{"function_name": "TronAction", "args": {"twist": {"x": 0, "y": random.uniform(-1, -0.8), "z": 0, "step": 1}}}],
    "backward": [{"function_name": "TronAction", "args": {"twist": {"x": random.uniform(-1, -0.8), "y": 0, "z": 0, "step": 1}}}],
    "forward": [{"function_name": "TronAction", "args": {"twist": {"x": random.uniform(0.8, 1), "y": 0, "z": 0, "step": 1}}}],
    "turn left": [{"function_name": "TronAction", "args": {"twist": {"x": 0, "y": 0, "z": random.uniform(0.8, 1), "step": 1}}}],
    "turn right": [{"function_name": "TronAction", "args": {"twist": {"x": 0, "y": 0, "z": random.uniform(-1, -0.8), "step": 1}}}],
    "move left": [{"function_name": "TronAction", "args": {"twist": {"x": random.uniform(-1, -0.8), "y": random.uniform(-1,-0.8), "z": random.uniform(0.7, 1), "step": 1}}}],
    "move right": [{"function_name": "TronAction", "args": {"twist": {"x": random.uniform(-1, -0.8), "y": random.uniform(0.8, 1), "z": random.uniform(-1, -0.7), "step": 1}}}],
    "circles":[{"function_name": "TronAction", "args": {"twist": {"x": 0, "y": 0, "z": 1, "step": 10}}}],
    "circle":[{"function_name": "TronAction", "args": {"twist": {"x": 0, "y": 0, "z": 1, "step": 10}}}],
    "站起来": [{"function_name": "TronAction", "args": {"stand": {}}}],
    "起立": [{"function_name": "TronAction", "args": {"stand": {}}}],
    "坐下": [{"function_name": "TronAction", "args": {"sit": {}}}],
    "蹲": [{"function_name": "TronAction", "args": {"sit": {}}}],
    "向左走": [{"function_name": "TronAction", "args": {"twist": {"x": 0,  "y": random.uniform(0.8, 1), "z": 0, "step": 1}}}],
    "往左走": [{"function_name": "TronAction", "args": {"twist": {"x": 0,  "y": random.uniform(0.8, 1), "z": 0, "step": 1}}}],
    "向左移": [{"function_name": "TronAction", "args": {"twist": {"x": 0,  "y": random.uniform(0.8, 1), "z": 0, "step": 1}}}],
    "往左移": [{"function_name": "TronAction", "args": {"twist": {"x": 0,  "y": random.uniform(0.8, 1), "z": 0, "step": 1}}}],
    "向右走": [{"function_name": "TronAction", "args": {"twist": {"x": 0, "y": random.uniform(-1, -0.8), "z": 0, "step": 1}}}],
    "往右走": [{"function_name": "TronAction", "args": {"twist": {"x": 0, "y": random.uniform(-1, -0.8), "z": 0, "step": 1}}}],
    "向右移": [{"function_name": "TronAction", "args": {"twist": {"x": 0, "y": random.uniform(-1, -0.8), "z": 0, "step": 1}}}],
    "往右移": [{"function_name": "TronAction", "args": {"twist": {"x": 0, "y": random.uniform(-1, -0.8), "z": 0, "step": 1}}}],
    "向左平移": [{"function_name": "TronAction", "args": {"twist": {"x": 0,  "y": random.uniform(0.8, 1), "z": 0, "step": 1}}}],
    "左平移": [{"function_name": "TronAction", "args": {"twist": {"x": 0,  "y": random.uniform(0.8, 1), "z": 0, "step": 1}}}],
    "往左平移": [{"function_name": "TronAction", "args": {"twist": {"x": 0,  "y": random.uniform(0.8, 1), "z": 0, "step": 1}}}],
    "向右平移": [{"function_name": "TronAction", "args": {"twist": {"x": 0,  "y": random.uniform(-1, -0.8), "z": 0, "step": 1}}}],
    "右平移": [{"function_name": "TronAction", "args": {"twist": {"x": 0,  "y": random.uniform(-1, -0.8), "z": 0, "step": 1}}}],
    "往右平移": [{"function_name": "TronAction", "args": {"twist": {"x": 0,  "y": random.uniform(-1, -0.8), "z": 0, "step": 1}}}],
    "向后退": [{"function_name": "TronAction", "args": {"twist": {"x": random.uniform(-1, -0.8), "y": 0, "z": 0, "step": 1}}}],
    "退后": [{"function_name": "TronAction", "args": {"twist": {"x": random.uniform(-1, -0.8), "y": 0, "z": 0, "step": 1}}}],
    "往后退": [{"function_name": "TronAction", "args": {"twist": {"x": random.uniform(-1, -0.8), "y": 0, "z": 0, "step": 1}}}],
    "向后走": [{"function_name": "TronAction", "args": {"twist": {"x": random.uniform(-1, -0.8), "y": 0, "z": 0, "step": 1}}}],
    "往后走": [{"function_name": "TronAction", "args": {"twist": {"x": random.uniform(-1, -0.8), "y": 0, "z": 0, "step": 1}}}],
    "向前走": [{"function_name": "TronAction", "args": {"twist": {"x": random.uniform(0.8, 1), "y": 0, "z": 0, "step": 1}}}],
    "往前走": [{"function_name": "TronAction", "args": {"twist": {"x": random.uniform(0.8, 1), "y": 0, "z": 0, "step": 1}}}],
    "前进": [{"function_name": "TronAction", "args": {"twist": {"x": random.uniform(0.8, 1), "y": 0, "z": 0, "step": 1}}}],
    "往左转": [{"function_name": "TronAction", "args": {"twist": {"x": 0, "y": 0, "z": random.uniform(0.6, 1), "step": 5}}}],
    "向左转": [{"function_name": "TronAction", "args": {"twist": {"x": 0, "y": 0, "z": random.uniform(0.6, 1), "step": 5}}}],
    "左转": [{"function_name": "TronAction", "args": {"twist": {"x": 0, "y": 0, "z": random.uniform(0.6, 1), "step": 5}}}],
    "往右转": [{"function_name": "TronAction", "args": {"twist": {"x": 0, "y": 0, "z": random.uniform(-1, -0.6), "step": 5}}}],
    "往后转": [{"function_name": "TronAction", "args": {"twist": {"x": 0, "y": 0, "z": 1, "step": 5}}}],
    "向后转": [{"function_name": "TronAction", "args": {"twist": {"x": 0, "y": 0, "z": 1, "step": 5}}}],
    "右转": [{"function_name": "TronAction", "args": {"twist": {"x": 0, "y": 0, "z": random.uniform(-1, -0.6), "step": 3}}}],
    "向右转": [{"function_name": "TronAction", "args": {"twist": {"x": 0, "y": 0, "z": random.uniform(-1, -0.6), "step": 3}}}],
    "圈":[{"function_name": "TronAction", "args": {"twist": {"x": 0, "y": 0, "z": 1, "step": 10}}}],
    "圈半":[{"function_name": "TronAction", "args": {"twist": {"x": 0, "y": 0, "z": 1, "step": 10}}},{"function_name": "TronAction", "args": {"twist": {"x": 0, "y": 0, "z": 0.5, "step": 5}}}],
    "半圈":[{"function_name": "TronAction", "args": {"twist": {"x": 0, "y": 0, "z": 0.5, "step": 5}}}],
    "升高":[{"function_name": "TronAction", "args": {"height": {"direction": 1}}}],
    "身高":[{"function_name": "TronAction", "args": {"height": {"direction": 1}}}],
    "增高":[{"function_name": "TronAction", "args": {"height": {"direction": 1}}}],
    "降低":[{"function_name": "TronAction", "args": {"height": {"direction": -1}}}],
    "下降":[{"function_name": "TronAction", "args": {"height": {"direction": -1}}}],
    "灯光":[{"function_name": "TronAction", "args": {"light": {"effect": 1}}}],
    "stand": [{"function_name": "TronAction", "args": {"stand": {}}}],
    "sit": [{"function_name": "TronAction", "args": {"sit": {}}}],
    "move forward": [{"function_name": "TronAction", "args": {"twist": {"x": random.uniform(0.8, 1), "y": 0, "z": 0, "step": 1}}}],
    "move backward": [{"function_name": "TronAction", "args": {"twist": {"x": random.uniform(-1, -0.8), "y": 0, "z": 0, "step": 1}}}],
    "turn left": [{"function_name": "TronAction", "args": {"twist": {"x": 0, "y": 0, "z": random.uniform(0.8, 1), "step": 1}}}],
    "turn right": [{"function_name": "TronAction", "args": {"twist": {"x": 0, "y": 0, "z": random.uniform(-1, -0.8), "step": 1}}}],
    "move left": [{"function_name": "TronAction", "args": {"twist": {"x": random.uniform(-1, -0.8), "y": 0, "z": random.uniform(0.7, 1), "step": 1}}}],
    "move right": [{"function_name": "TronAction", "args": {"twist": {"x": random.uniform(-1, -0.8), "y": 0, "z": random.uniform(-1, -0.7), "step": 1}}}],
}

# 定义身份询问关键词
identity_keywords = {
    "你是谁": ["asset/who_zh.wav"],
    "介绍自己":["asset/who_zh.wav"],
    "自我介绍":["asset/who_zh.wav"],
    "介绍一下你自己":["asset/who_zh.wav"],
    "介绍一下自己":["asset/who_zh.wav"],
    "who are you": ["asset/who_en.wav"],
}

what_keywords = {
    "可以干什么": ["asset/what_zh.wav"],
    "什么功能": ["asset/what_zh.wav"],
    "哪些功能": ["asset/what_zh.wav"],
    "你的功能": ["asset/what_zh.wav"],
    "what can you do": ["asset/what_en.wav"],
}
undo_keywords = {
    "unknow": [random.choice(["asset/undo_zh.wav","asset/noise_zh.wav"])],
}

action_keywords = {
    "随便什么动作":generate_action(num_moves=1),
    "随便做个动作":generate_action(num_moves=1),
}
