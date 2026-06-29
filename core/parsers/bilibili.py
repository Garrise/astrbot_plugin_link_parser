import re, requests
from typing import Any
from .base import BaseParser
from ..data import ParseResult

from astrbot.api import logger

class BilibiliParser(BaseParser):
    """Bilibili 链接解析器"""


    keyword = "bilibili"
    patterns = [
        re.compile(r"https?://(?:www\.)?bilibili\.com/video/([a-zA-Z0-9]+)"),
        re.compile(r"https?://(?:www\.)?b23\.tv/([a-zA-Z0-9]+)"),
    ]
    
    def __init__(self, config: dict):
        super().__init__(config)

    async def parse(self, searched: re.Match[str]) -> ParseResult | None:
        """解析 Bilibili 链接，返回视频信息或 None。

        Args:
            text (str): 待解析的文本

        Returns:
            ParseResult | None: 解析结果，如果无法解析则返回 None
        """
        
        link = searched.group(0)
        id = searched.group(1)
        
        # 判断是AV号还是BV号
        is_av = id.startswith("av")
        is_bv = id.startswith("BV")
        
        if is_av and not is_bv:
            api_url = f"https://api.bilibili.com/x/web-interface/view?aid={id[2:]}"
        elif is_bv:
            api_url = f"https://api.bilibili.com/x/web-interface/view?bvid={id}"
        else:
            return None
        
        try:
            resp = requests.get(api_url, **self._get_request_kwargs())
            data = resp.json()
            if data["code"] != 0:
                raise ValueError("Bilibili API error")

            video_data = data['data']
            stat_data = video_data['stat']

            description = video_data.get('desc') or video_data.get('dynamic', '')
            if isinstance(description, str) and len(description) > 0:
                description = f"📝 描述：{description[:97]}..." if len(description) > 100 else f"📝 描述：{description}"
            else:
                description = None

            message_b = [
                f"🎐 标题：{video_data['title']}",
                f"😃 UP主：{video_data['owner']['name']}"
            ]
            if description:
                message_b.append(description.replace("\n", ""))

            message_b.extend([
                f"💖 点赞：{self._format_count(stat_data.get('like', 0))}  ",
                f"🪙 投币：{self._format_count(stat_data.get('coin', 0))}  ",
                f"✨ 收藏：{self._format_count(stat_data.get('favorite', 0))}",
                f"🌐 链接：https://www.bilibili.com/video/{id}"
            ])
            return ParseResult(
                image_url=video_data['pic'],
                description="\n".join(message_b),
                resource_id=id
            )

        except Exception as e:
            logger.error(f"Bilibili 解析失败: {e}")
            return None