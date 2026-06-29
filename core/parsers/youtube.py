import re, requests
from .base import BaseParser
from ..data import ParseResult

from astrbot.api import logger

class YoutubeParser(BaseParser):
    """Youtube 链接解析器"""


    keyword = "youtube"
    patterns = [
        re.compile(r"https?://(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]+)"),
        re.compile(r"https?://(?:www\.)?youtu\.be/([a-zA-Z0-9_-]+)"),
    ]
    
    def __init__(self, config: dict):
        super().__init__(config)

    async def parse(self, searched: re.Match[str]) -> ParseResult | None:
        """解析 Youtube 链接，返回视频信息或 None。

        Args:
            text (str): 待解析的文本

        Returns:
            ParseResult | None: 解析结果，如果无法解析则返回 None
        """
        id = searched.group(1)
        parsers_template = self.config.get("parsers_template", [])
        for template in parsers_template:
            if template.get("__template_key") == self.keyword:
                key = template.get("api_key")
                break
        else:
            logger.warning(f"Youtube 解析失败: 未配置 API Key")
            return None
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.163 Safari/537.36'
        }
        try:
            response = requests.get(f"https://www.googleapis.com/youtube/v3/videos?id={id}&key={key}&part=snippet", **self._get_request_kwargs())
            data = response.json()
            if data['pageInfo']['totalResults'] != 0:
                snippet = data['items'][0]['snippet']
                title = snippet['title']
                description = snippet['description']
                channelTitle = snippet['channelTitle']
                thumbnails = snippet['thumbnails']
                publishedAt = snippet['publishedAt']
                tagString = ""
                tags = snippet.get("tags")
                if tags:
                    tagString = ", ".join(tags)
                else:
                    tagString = "无"
                thumbnailUrl = thumbnails['maxres']['url'] if thumbnails['maxres'] else thumbnails['high']['url']
                message_youtube = [
                    f"🎐标题：{title}",
                    f"😃频道：{channelTitle}",
                    f"🌐链接：http://youtu.be/{id}"

                ]
                return ParseResult(
                    image_url=thumbnailUrl,
                    description="\n".join(message_youtube),
                    resource_id=id
                )
            else:
                logger.warning(f"Youtube 解析失败: 无法获取视频信息，可能是无效的链接或视频不存在。")
                return None
        except Exception as e:
            logger.error(f"Youtube 解析失败: {e}")
            return None