import time
import geojson
from pycitysim.apphub import AppHubClient, AgentMessage, UserMessage
import PIL.Image as Image

client = AppHubClient(
    app_hub_url="http://localhost:8080",
    app_id=16,
    app_secret="iYwpLCzvYEjMCBi4D6qLmZS8+OIsYgPD",
)

# 1. 绑定人
agent_id = client.bind_person(1, "张三", Image.open("avatar.jpg"))
print("agent_id:", agent_id)

# 2. 更新地图
client.update_agent_map(
    agent_id,
    [116.397, 39.908],
    geojson.FeatureCollection([]),
    None,
    popup="张三",
)

# 3. 更新消息
client.update_agent_messages(
    agent_id,
    [
        AgentMessage(
            id=agent_id,
            timestamp=int(time.time() * 1000),
            content="你好",
            images=[],
            sub_messages=[
                AgentMessage(
                    id=agent_id,
                    timestamp=int(time.time() * 1000 - 1),
                    content="内心独白：和LLM交流",
                    images=[],
                    sub_messages=[],
                )
            ],
        )
    ],
)

# 4. 获取用户消息
while True:
    user_messages = client.fetch_user_messages(agent_id)
    for user_message in user_messages:
        print("收到用户消息：", user_message)
        if user_message.content == "再见":
            # 5. 释放person
            client.release_agent(agent_id)
            break
    time.sleep(1)
