# Introduction
这是一个对CISL实验室的部分项目集成的项目仓库，构建一个面向老年人的安卓端工具。

# 核心模块
## 数据库
app/repositories: 数据库操作的抽象层，使用ORM或者原始的SQL进行数据库交互。

app/services: 业务逻辑的实现层。处理核心业务流程，调用repositories进行数据操作。例如get_user_by_id(user_id)...

app/data_models: 数据模型定义，包含数据库表结构和业务对象定义。例如包括
    User(用户, 包含user_id, user_name, user_gender, user_age, user_education,  user_created_at, device_id)
    Device(用户使用的设备, 包含device_id, device_name(e.g., "Honor 80"), Android_version(e.g., "13"))
    Activity(user使用device时的所有操作记录, 包含device_id, action_type, position, UI_element, action_time, app_name, app_package_name, screenshot_path)
    Preference(用户的偏好信息, 包括user_id, preference_type, preference_value) preference_type in {"app_usage", "interest", ""}
    Conversation(用户与AI的对话记录, 包括 user_id, session_id, speaker("user", "assistant"), message, created_at)
    ModelResponse(agent_id, agent_content, to_user_id, created_at)

## 智能体
app/agent: 包含基础agent和其他agent的实现，其中，
    Base_Agent: 基础agent，包含agent的抽象基类和基础实现。包含agent的初始化(OpenAI API format, system_prompt, model_name, endpoint)
    Intent_and_Content_Parser_Agent: 给定输入:用户utterance(可能为空), Screenshot, action on screenshot, 智能体需要对此综合进行分析, 分析内容包括:
        - 用户是否在浏览文本或者视频内容(call for 有害内容识别&虚假识别&回忆识别,各是一个单独的接口, 返回识别结果(boolen) 和 提醒描述(string))
        - 行为是否具有偏好信息(call for store in memory for later use, parameter: preference_type, preference_description)
        - 是否存在内容发布行为(call for 隐私保护内容审查, parameter: content, 返回 隐私审查提醒(string))
        - 用户当前是否需要情感支持(call for 情感支持)
        返回: {
            "scanning_text_or_video": bool, # if true, do harmful_content_detection & fake_content_detection & reminance_content_detection
            "user_preference": {
                "has_user_preference": bool, # if true, do memory_storage
                "preference_type": str,
                "preference_description": str
            },
            "content_release": {
                "has_content_release": bool, # if true, do privacy_protection_content_review
                "content_release_reminder": str, # 隐私审查提醒,包括例如"您要发布的XXX可能涉及个人隐私, 请谨慎考虑"
            }
            "need_emotion_support": bool # if true, do emotion_support
        }
    Memory_Agent: 管理用户的长期记忆(对话历史总结(例如每进行10次对话, 总结一次对话历史, 并存储到memory中)、偏好信息(time-based))和短期记忆(当前对话上下文)。每次对话都根据preference_type, preference_description, 检索memory。如果当前存在偏好信息，才进行存储。
    Response_Generator: 给定输入: 用户utterance, memory(chat history, preference), 生成：
    - reply_sentence: 回复给用户的内容。（在system prompt中阐明需要考虑用户的年龄身份, 在回复中可以适当介绍用户可能不明白的名词或者网络用词、网络梗）
    - action_list: 代理操作(如果有的话, 例如click, swipe等)。

Agent调用关系:
    Intent_and_Content_Parser_Agent -> Memory_Agent -> Response_Generator
                                    -> Functions ->
    最终呈现给用户的结果包含三个部分:
    - 回复给用户的内容
    - 代理操作(如果有的话, 例如click, swipe等)
    - 在用户界面提醒的内容，例如"您要发布的XXX可能涉及个人隐私, 请谨慎考虑"等
    此外，除呈现给用户外，还涉及Memory_Agent的内容管理
    所有结果都会存储到数据库中

## 数据选型
- Web框架 (Python后端):FastAPI
- 数据库 (MongoDB+Motor+...)
- 通信协议: RESTful API