import requests
from datetime import datetime
from plugins.registry import register_function, ToolType
from plugins.registry import ActionResponse, Action

@register_function('GetWeather', ToolType.WAIT)
def GetWeather(**kwargs):
    """
    "获取某个地点的天气，用户应先提供一个位置，\n比如用户说杭州天气，参数为：zhejiang/hangzhou，\n\n比如用户说北京天气怎么样，参数为：beijing/beijing",
    city : 城市，zhejiang/hangzhou
    """
    city=kwargs.get("city",None)
    if not city:
        city=get_current_city()
    if not city:
        return ActionResponse(Action.REQLLM, "无法获取当前城市，请求失败", "请求失败")
    url = "https://v2.xxapi.cn/api/weather?city="+city
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36'
    }
    response = requests.get(url, headers=headers)

    if response.status_code!=200:
        return ActionResponse(Action.REQLLM, None, "请求失败")
    response=response.json()
    # 获取当前日期和时间
    now = datetime.now()

    # 获取当前日期的周几（0=周一，6=周日）
    weekday = now.weekday()
    date_format = now.strftime("%-m月%-d日")  # Linux/Mac格式
    # 将数字转换为周几的名称
    weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    current_weekday = weekdays[weekday]
    return ActionResponse(Action.REQLLM, f"今天{date_format},{current_weekday},天气信息为：{response}", None)


def get_current_city():
    try:
        # 使用 ipinfo.io 服务
        response = requests.get("https://ipinfo.io/json")
        response.raise_for_status()
        data = response.json()
        city = data.get("city")
        return city
    except requests.exceptions.RequestException as e:
        return None
if __name__ == "__main__":
    GetWeather(**{'city': None})