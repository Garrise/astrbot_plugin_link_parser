import re, requests
from urllib.parse import urlparse
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
            # 短链测试
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            try:
                # 1. 阻止重定向以获取原始长链
                response = requests.head(
                    link, headers=headers, allow_redirects=False, timeout=5
                )

                if response.status_code not in (301, 302):
                    logger.error(f"短链解析失败，响应状态码: {response.status_code}")
                    return None  # 如果不是重定向响应，则返回 None

                long_url = response.headers.get("Location")
                if not long_url:
                    logger.error(f"短链解析失败，响应头中未找到 Location")
                    return None

                # 2. 提取 URL 中的路径部分进行匹配
                parsed_url = urlparse(long_url)
                path = parsed_url.path  # 例如 "/video/BV11x411a7yX/" 或 "/video/av170001/"

                # 3. 正则匹配 BV 号或 av 号
                # 匹配 BV 号 (以 BV 开头，后面跟着10位字母或数字)
                bv_match = re.search(r"(BV[a-zA-Z0-9]{10})", path)
                # 匹配 av 号 (以 av 开头，后面跟着纯数字)
                av_match = re.search(r"(av\d+)", path, re.IGNORECASE)
                if bv_match:
                    bv_id = bv_match.group(1)
                    api_url = f"https://api.bilibili.com/x/web-interface/view?bvid={bv_id}"
                elif av_match:
                    av_id = av_match.group(1).lower()  # 转为小写格式
                    # 根据你的要求：aid={id[2:]} 也就是去掉开头的 'av'，只留数字
                    api_url = f"https://api.bilibili.com/x/web-interface/view?aid={av_id[2:]}"
                else:
                    logger.error(f"无法从长链中提取 BV 号或 av 号: {long_url}")
                    return None

            except requests.exceptions.RequestException as e:
                logger.error(f"请求短链解析失败: {e}")
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