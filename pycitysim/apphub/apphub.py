import base64
from dataclasses import dataclass
from io import BytesIO
from typing import Any, Dict, Optional, List

from PIL.Image import Image
import geojson
import requests
from requests.auth import HTTPBasicAuth

__all__ = ["AppHubClient", "AgentMessage", "UserMessage"]


def _image2base64(image: Image) -> str:
    buffered = BytesIO()
    image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode("utf-8")


@dataclass
class AgentMessage:
    id: int
    """
    发送者Agent ID
    Agent ID of sender
    """
    timestamp: int
    """
    消息时间戳（单位：毫秒）
    Message timestamp (milliseconds)
    """
    content: str
    """
    消息内容
    Message content
    """
    images: Optional[List[Image]]
    """
    消息图片
    Message images
    """
    sub_messages: Optional[List["AgentMessage"]]

    def to_dict(self):
        d = {
            "id": self.id,
            "timestamp": self.timestamp,
            "content": self.content,
        }
        if self.images is not None:
            d["images"] = [_image2base64(image) for image in self.images]
        if self.sub_messages is not None:
            d["subMessages"] = [message.to_dict() for message in self.sub_messages]
        return d


@dataclass
class UserMessage:
    id: int
    """
    发送者User ID对应的Agent ID
    Agent ID corresponding to the sender User ID
    """
    timestamp: int
    """
    消息时间戳（单位：毫秒）
    Message timestamp (milliseconds)
    """
    content: str
    """
    消息内容
    Message content
    """


class AppHubClient:
    """
    AppHub客户端
    AppHub client

    # 操作流程
    # Operating procedures

    1. 初始化AppHubClient，填入从前端获得的app_id和app_secret
    1. Initialize AppHubClient, fill in the app_id and app_secret obtained from the front end    
    2. 调用bind_person/bind_org绑定模拟器内的人，获得agent_id
    2. Call bind_person/bind_org to bind the person in the simulator, and obtain the agent_id
    3. 调用update_agent_map更新agent的地图内容，以改变agent在地图上的显示
    3. Call update_agent_map to update the agent's map content, to change the agent's display on the map
    4. 调用update_agent_messages更新agent的消息内容，以改变agent的消息内容
    4. Call update_agent_messages to update the agent's message content, to change the agent's message content
    5. 定期调用fetch_user_message获取用户发送给agent的消息，并进行处理
    5. Call fetch_user_message regularly to obtain the messages sent by the user to the agent, and process them
    6. 如果不再使用agent，调用release_agent释放agent，以允许其他app绑定
    6. If the agent is no longer used, call release_agent to release the agent to allow other apps to bind.
    """

    def __init__(
        self,
        app_hub_url: str,
        app_id: int,
        app_secret: str,
        proxies: Optional[dict] = None,
    ):
        """
        Args:
        - app_id: app ID，从前端注册页面获取。app ID, obtained from the frontend registration page.
        - app_secret: app secret，从前端注册页面获取。app secret, obtained from the frontend registration page.
        """
        self.app_hub_url = app_hub_url
        self.app_id = app_id
        self.app_secret = app_secret
        self.proxies = proxies
        self.agents = {}  # agent_id -> agent (bind body)

        self._auth = HTTPBasicAuth(str(app_id), app_secret)

    def _bind(self, foreign_id: int, type: str, name: str, avatar: Image) -> int:
        body = {
            "type": type,
            "name": name,
            "avatar": _image2base64(avatar),
            "foreignID": foreign_id,
        }
        res = requests.post(
            self.app_hub_url + "/agents",
            json=body,
            auth=self._auth,
            proxies=self.proxies,
            timeout=5000
        )
        if res.status_code != 200:
            raise Exception(f"[{res.status_code}] AppHub bind failed: " + res.text)
        data = res.json()
        agent_id = data["data"]["id"]
        self.agents[agent_id] = body
        return agent_id

    def bind_person(self, person_id: int, name: str, avatar: Image):
        """
        绑定模拟器内的人，只有绑定的person才能被访问
        Bind person in the simulator. Only bound person can be accessed

        Args:
        - person_id: 模拟器内的人的ID。The ID of the person in the simulator.
        - name: 人的名字（前端显示）。Person's name (displayed on the front end).
        - avatar: 人的头像（前端显示）。Person's avatar (displayed on the front end).

        Returns:
        - agent_id: 绑定后的agent ID。the bound agent ID.

        Raises:
        - Exception: 绑定失败。Binding failed.
        """
        return self._bind(person_id, "person", name, avatar)

    def bind_org(self, org_id: int, name: str, avatar: Image):
        """
        绑定模拟器内的组织，只有绑定的org才能被访问
        Bind the organization in the simulator. Only the bound org can be accessed

        Args:
        - org_id: 模拟器内的组织的ID。ID of the organization in the simulator
        - name: 组织的名字（前端显示）。Organization's name (displayed on the front end).
        - avatar: 组织的头像（前端显示）。Organization's avatar (displayed on the front end).

        Returns:
        - agent_id: 绑定后的agent ID。the bound agent ID.

        Raises:
        - Exception: 绑定失败。Binding failed.
        """
        return self._bind(org_id, "org", name, avatar)
    
    def bind_func(self, name:str, avatar:Image):
        """
        插入非模拟器相关的智能体——func类型智能体

        Args:
        - name (str): 该智能体的名字
        - avatar (Image): 该智能体的头像
        """
        return self._bind(-1, "func", name, avatar)

    def release_agent(self, agent_id: int) -> bool:
        """
        释放agent(person/org), 释放后agent将不再被访问并允许其他app绑定
        Release the agent (person/org). After the release, the agent will no longer be accessed and allows other apps to bind.

        Args:
        - agent_id: agent的ID。ID of the agent.

        Returns:
        - bool: 是否成功。whether succeed.
        """
        res = requests.delete(
            self.app_hub_url + "/agents/" + str(agent_id),
            auth=self._auth,
            proxies=self.proxies,
            timeout=5000
        )
        return res.status_code == 200

    def update_agent_map(
        self,
        agent_id: int,
        lnglat: List[float],
        geojsons: Optional[geojson.FeatureCollection] = None,
        street_view: Optional[Image] = None,
        popup: Optional[str] = None,
    ):
        """
        更新agent的地图内容
        Update the agent’s map content

        Args:
        - agent_id: agent的ID。ID of the agent.
        - lnglat: 经纬度，格式为 [lng, lat]。Latitude and longitude in [lng, lat].
        - geojsons: geojson FeatureCollection，用于在地图上显示点线面。geojson FeatureCollection, used to display points, lines and polygons on the map.
        - street_view: 街景图片。Street view images.
        - popup: 弹出框内容。Pop-up box content.

        Raises:
        - Exception: 更新失败。Updating failed.
        """

        body: Dict[str, Any] = {
            "lnglat": lnglat,
        }
        if geojsons is not None:
            body["geojsons"] = geojsons
        if street_view is not None:
            body["streetView"] = _image2base64(street_view)
        if popup is not None:
            body["popup"] = popup

        res = requests.put(
            self.app_hub_url + "/agents/" + str(agent_id) + "/map",
            json=body,
            auth=self._auth,
            proxies=self.proxies,
            timeout=5000
        )
        if res.status_code != 200:
            raise Exception(
                f"[{res.status_code}] AppHub update map failed: " + res.text
            )

    def update_agent_messages(self, agent_id: int, messages: List[AgentMessage]):
        """
        更新agent的消息
        Update agent's messages

        Args:
        - agent_id: agent的ID。ID of the agent.
        - messages: 消息列表（注意顺序，最新的消息在最后）。Message list (note the order, the latest message at the end).

        Raises:
        - Exception: 更新失败。Updating failed.
        """
        res = requests.put(
            self.app_hub_url + "/agents/" + str(agent_id) + "/messages",
            json={"messages": [message.to_dict() for message in messages]},
            auth=self._auth,
            proxies=self.proxies,
            timeout=5000
        )
        if res.status_code != 200:
            raise Exception(
                f"[{res.status_code}] AppHub update messages failed: " + res.text
            )

    def fetch_user_messages(
        self,
        agent_id: int,
    ) -> List[UserMessage]:
        """
        获取用户发送给agent的消息
        Fetch the message sent by the user to the agent

        Args:
        - agent_id: agent的ID。ID of the agent.

        Returns:
        - messages: 消息列表。Message list.

        Raises:
        - Exception: 获取失败。Fetching failed.
        """
        res = requests.post(
            self.app_hub_url + "/agents/" + str(agent_id) + "/fetch-user-messages",
            auth=self._auth,
            proxies=self.proxies,
            timeout=5000
        )
        if res.status_code != 200:
            raise Exception(
                f"[{res.status_code}] AppHub fetch messages failed: " + res.text
            )
        data = res.json()
        return [UserMessage(**message) for message in data["data"]]
