import re
from abc import ABC
from typing import ClassVar, Any
from ..data import ParseResult
from astrbot.api import logger

class BaseParser:
    """基础解析器类，所有具体的解析器都应该继承自该类，并实现 parse 方法。"""

    _registry: ClassVar[list[type["BaseParser"]]] = []
    """ 存储所有已注册的 Parser 类 """

    keyword: str
    """ 解析器的关键词 """
    patterns: list[re.Pattern[str]]
    """ 解析器的正则表达式列表 """

    def __init__(self, config: dict):
        self.config = config
        pass

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if ABC not in cls.__bases__: # 跳过抽象类
            BaseParser._registry.append(cls)
    
    @classmethod
    def get_registered_parsers(cls) -> list[type["BaseParser"]]:
        """获取所有已注册的 Parser 类"""
        return cls._registry
    
    @classmethod
    def get_keyword(cls) -> str:
        """获取解析器的关键词"""
        return cls.keyword
    
    @classmethod
    def get_patterns(cls) -> list[re.Pattern[str]]:
        """获取解析器的正则表达式列表"""
        return cls.patterns
    
    def _format_count(self, count: int) -> str:
        """格式化数字为K单位"""
        if count >= 1000:
            if count % 1000 == 0:
                return f"{count//1000}K"
            return f"{count/1000:.1f}K"
        return str(count)
    
    
    def _get_request_kwargs(self) -> dict[str, Any]:
        proxy_url = self.config.get("proxy", "")

        proxies: dict[str, str] = {}
        if proxy_url:
            templates = self.config.get("parsers_template", [])
            for template in templates:
                if template.get("__template_key") == self.keyword:
                    if template.get("use_proxy", False):
                        proxies = {"http": proxy_url, "https": proxy_url}
                    break

        timeout = int(self.config.get("common_timeout", 15))

        kwargs: dict[str, Any] = {
            "headers": {"User-Agent": "Mozilla/5.0"},
            "timeout": timeout,
        }
        if proxies:
            logger.debug(f"使用代理 {proxy_url} 访问 {self.keyword} API")
            kwargs["proxies"] = proxies
        return kwargs

    async def parse(self, searched: re.Match[str]) -> ParseResult | None:
        """解析文本，返回解析结果，如果无法解析则返回 None。

        Args:
            text (str): 待解析的文本

        Returns:
            ParseResult | None: 解析结果，如果无法解析则返回 None
        """
        raise NotImplementedError("parse 方法需要在子类中实现")