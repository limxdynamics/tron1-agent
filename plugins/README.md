# 百聆插件

欢迎使用百聆插件的 function call 支持功能！本文档将指导你如何配置和使用这一功能。


## 简介

百聆（Bailing）是一个开源的语音助手，旨在通过集成 ASR、LLM 和 TTS 技术提供类似 GPT-4o 的性能。这个插件现在支持 function call 能力，可以让你通过函数调用扩展其功能。

## 功能

- **动态功能调用**：通过定义函数接口，实现动态调用功能。
- **灵活配置**：支持多种功能配置方式。


## 配置

1. **创建配置文件**：在项目根目录下创建一个名为 `function_calls_config.json` 的配置文件。该文件将用于定义你的 function call 相关配置。

    ```json
   {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "获取某个地点的天气，用户应先提供一个位置，比如用户说杭州天气，参数为：zhejiang/hangzhou，比如用户说北京天气怎么样，参数为：beijing/beijing",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "城市，zhejiang/hangzhou"
                    }
                },
                "required": [
                    "city"
                ]
            }
        }
    }
    ```
   
2. **实现函数逻辑**：在functions文件夹下，实现你的工具逻辑

```python
.....
 
```


3. 当前支持的工具有：

| 函数名                | 描述                                          | 功能                                                       | 示例                                                         |
|-----------------------|-----------------------------------------------|------------------------------------------------------------|--------------------------------------------------------------|
| `get_weather`         | 获取某个地点的天气信息                        | 提供地点名称后，返回该地点的天气情况                       | 用户说：“杭州天气怎么样？” → `zhejiang/hangzhou`             |
| `tron_action`         | tron机器人工具调用                           | 包括ws，工具调用的flow等                                | -                                                            |
