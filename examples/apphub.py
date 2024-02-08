import time
import geojson
from pycitysim.apphub import AppHubClient, AgentMessage
import PIL.Image as Image

client = AppHubClient(
    app_hub_url="http://localhost:8080",
    app_id=16,
    app_secret="your app secret",
)

# 1. 绑定人
# 1. Bind person
agent_id = client.bind_person(1, "张三", Image.open("avatar.jpg"))
print("agent_id:", agent_id)

# 2. 更新地图
# 2. Update the map
client.update_agent_map(
    agent_id,
    [116.397, 39.908],
    geojson.FeatureCollection([]),
    None,
    popup="张三",
)

# 3. 更新消息
# 3. Update the message
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
# 4. Get user messages
while True:
    user_messages = client.fetch_user_messages(agent_id)
    for user_message in user_messages:
        print("receive user message: ", user_message)
        if user_message.content == "Goodbye":
            # 5. 释放person
            # 5. Release person
            client.release_agent(agent_id)
            break
    time.sleep(1)
