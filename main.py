import re

from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger, AstrBotConfig
from astrbot.core.message.components import At, Image, Json, Plain

from .core.utils import extract_json_url
from .core.parsers.base import BaseParser
from .core.bounse import Debouncer

@register("Link Parser", "Garrise", "聚合链接解析插件", "1.0.0")
class ParserPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config
        self.debouncer = Debouncer(config.get("debounce_interval", 300))
        self.patterns_list: list[tuple[str, re.Pattern[str]]] = []
        self.parsers_map: dict[str, BaseParser] = {}

    async def initialize(self):
        """可选择实现异步的插件初始化方法，当实例化该插件类之后会自动调用该方法。"""
        self._register_parsers()

    def _get_enabled_platforms(self) -> list[str]:
        """获取启用的解析平台"""
        templates = self.config.get("parsers_template", [])
        enabled_platforms = []
        for template in templates:
            if template.get("enable", False):
                enabled_platforms.append(template.get("__template_key"))
        return enabled_platforms

    def _register_parsers(self):
        registered_parsers = BaseParser.get_registered_parsers()
        enabled_platforms = self._get_enabled_platforms()
        for parser_cls in registered_parsers:
            keyword = parser_cls.get_keyword()
            if keyword in enabled_platforms:
                parser_instance = parser_cls(self.config)
                self.parsers_map[keyword] = parser_instance
                for pattern in parser_cls.get_patterns():
                    self.patterns_list.append((keyword, pattern))
                logger.info(f"已注册解析器: {keyword}")
            else:
                logger.info(f"解析器 {keyword} 未启用，跳过注册")

    # 匹配链接
    def _match_link(self, text: str) -> tuple[str, re.Match[str]] | None:
        for keyword, pattern in self.patterns_list:
            match = pattern.search(text)
            if match:
                return keyword, match
        return None

    # 消息入口
    @filter.event_message_type(filter.EventMessageType.ALL)
    async def on_message(self, event: AstrMessageEvent):
        umo = event.unified_msg_origin

        # 仅解析群聊消息
        is_group = umo.split(":")[1] == "GroupMessage"
        if not is_group:
            return
        group_id = umo.split(":")[2]

        # 白名单
        whitelist = self.config.get("whitelist", None)
        if whitelist and group_id not in whitelist:
            return
        
        # 黑名单
        blacklist = self.config.get("blacklist", None)
        if blacklist and group_id in blacklist:
            return
        
        # 消息链
        chain = event.get_messages()
        if not chain:
            return

        seg1 = chain[0]
        text = event.message_str

        # 卡片解析：解析Json组件，提取URL
        if isinstance(seg1, Json):
            text = extract_json_url(seg1.data)
            logger.debug(f"解析Json组件: {text}")

        if not text:
            return
        
        # 匹配链接
        keyword, searched = self._match_link(text) or (None, None)
        if not keyword or not searched:
            return
        logger.info(f"匹配到链接: {searched.group(0)}，使用解析器: {keyword}")
        
        # # 基于link的防抖
        # link = searched.group(0)
        # if self.debouncer.hit_link(event.session_id, link):
        #     logger.debug(f"防抖命中: {link}")
        #     return
        
        # 解析
        result = await self.parsers_map[keyword].parse(searched)
        if not result:
            logger.error(f"解析失败: {text}")
            return
        image_url, description, resource_id = result.image_url, result.description, result.resource_id

        # 基于resource_id的防抖
        if resource_id and self.debouncer.hit_resource(event.session_id, resource_id):
            logger.debug(f"防抖命中: {resource_id}")
            return
        
        # 组装并回复消息
        chain = [Image.fromURL(image_url), Plain(text=description)]
        logger.info(f"组装回复消息: {chain}")
        yield event.chain_result(chain=chain)
    async def terminate(self):
        """可选择实现异步的插件销毁方法，当插件被卸载/停用时会调用。"""
