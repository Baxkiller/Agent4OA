# 测试OpenAI API密钥是否有效

from openai import OpenAI

client = OpenAI(api_key="")

print(client.api_key)

response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {"role": "user", "content": "Hello, how are you?"}
    ]
)

print(response)