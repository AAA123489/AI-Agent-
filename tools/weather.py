"""天气查询工具 —— 基于高德地图开放平台天气 API。

免费额度：5000 次/天，注册即用，无需实名。
文档：https://lbs.amap.com/api/webservice/guide/api/weatherinfo
"""

import os

import aiohttp

# 高德天气 API Key，优先从环境变量读取
AMAP_KEY = os.getenv("AMAP_KEY", "38731adf1da4ebcbc45927972a8f3c16")


async def get_weather(city: str) -> str:
    """查询指定城市的实时天气信息。

    参数:
        city: 城市名称或行政区划代码，例如「北京」「110000」

    返回:
        格式化的天气信息字符串
    """
    url = "https://restapi.amap.com/v3/weather/weatherInfo"
    params = {
        "key": AMAP_KEY,
        "city": city,
        "extensions": "all",  # all = 实时天气 + 4天预报
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as resp:
            if resp.status != 200:
                return f"无法获取{city}的天气信息（HTTP {resp.status}），请检查城市名称是否正确。"
            data = await resp.json()

    # 高德返回格式:
    #   base: {"status": "1", "lives": [...]}      — 实时天气
    #   all:  {"status": "1", "forecasts": [...]}  — 4天预报
    if data.get("status") != "1":
        return f"查询{city}天气失败: {data.get('info', '未知错误')}"

    try:
        result = ""

        # 实时天气（extensions=base 时返回）
        lives = data.get("lives", [])
        if lives:
            live = lives[0]
            result = (
                f"{city}当前天气：{live['weather']}，"
                f"温度{live['temperature']}°C，湿度{live['humidity']}%，"
                f"风向{live['winddirection']}，风力{live['windpower']}级。"
            )

        # 预报（extensions=all 时返回）
        forecasts = data.get("forecasts", [])
        if forecasts:
            casts = forecasts[0].get("casts", [])
            if casts:
                # casts[0] = 今天预报
                today = casts[0]
                result = (
                    f"{city}今天天气：{today['dayweather']}转{today['nightweather']}，"
                    f"白天{today['daytemp']}°C，夜间{today['nighttemp']}°C，"
                    f"风力{today['daypower']}级。"
                )
                # casts[1] = 明天预报
                if len(casts) >= 2:
                    tomorrow = casts[1]
                    result += (
                        f"\n明天（{tomorrow['date']}）："
                        f"白天{tomorrow['dayweather']}、{tomorrow['daytemp']}°C，"
                        f"夜间{tomorrow['nightweather']}、{tomorrow['nighttemp']}°C，"
                        f"风力{tomorrow['daypower']}级。"
                    )

        return result
    except (KeyError, IndexError):
        return f"成功获取了{city}的天气数据，但解析失败。"


GET_WEATHER_SCHEMA = {
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "获取指定城市的实时天气信息，包括天气状况、温度、湿度、风向和风力。当用户询问天气时使用。",
        "parameters": {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "城市名称，例如「北京」「上海」「杭州」",
                }
            },
            "required": ["city"],
        },
    },
}
