"""
竖屏短剧策划助手配置管理
基于Pydantic的配置验证和环境变量管理
"""
import os
import yaml
import logging
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)
try:
    from pydantic_settings import BaseSettings
    from pydantic import Field
except ImportError:
    try:
        from pydantic import BaseSettings, Field
    except ImportError:
        # 如果pydantic版本太低，创建简单的模拟类
        class BaseSettings:
            def __init__(self, **kwargs):
                for key, value in kwargs.items():
                    setattr(self, key, value)
        
        class Field:
            def __init__(self, default=None, env=None, description=None, **kwargs):
                self.default = default
                self.env = env
                self.description = description
from pathlib import Path


def get_app_env() -> str:
    """获取当前运行环境"""
    return os.getenv("APP_ENV", "development").lower()


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """深度合并字典"""
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            base[key] = _deep_merge(base[key], value)
        else:
            base[key] = value
    return base


def load_yaml_config(app_env: Optional[str] = None) -> Dict[str, Any]:
    """加载配置文件（支持环境分层）"""
    app_env = app_env or get_app_env()
    base_path = Path(__file__).parent / "config.yaml"
    env_path = Path(__file__).parent / f"config.{app_env}.yaml"

    base_config = {}
    if base_path.exists():
        base_config = yaml.safe_load(base_path.read_text(encoding="utf-8")) or {}

    if env_path.exists():
        env_config = yaml.safe_load(env_path.read_text(encoding="utf-8")) or {}
        base_config = _deep_merge(base_config, env_config)

    return base_config


class ModelSettings(BaseSettings):
    """模型配置基类"""
    api_key: str = Field(..., description="API密钥")
    model: str = Field(default="glm-4.5", description="模型名称")
    base_url: str = Field(default="https://open.bigmodel.cn/api/paas/v4", description="API基础URL")
    temperature: float = Field(default=0.7, description="温度参数")
    max_tokens: int = Field(default=4096, description="最大token数")
    timeout: int = Field(default=30, description="请求超时时间")
    max_retries: int = Field(default=3, description="最大重试次数")


class ZhipuSettings(ModelSettings):
    """智谱AI配置"""
    api_key: str = Field(..., env="ZHIPU_API_KEY", description="智谱API密钥")
    model: str = Field(default="glm-4.5", env="ZHIPU_MODEL", description="智谱模型名称")
    base_url: str = Field(default="https://open.bigmodel.cn/api/paas/v4", env="ZHIPU_BASE_URL", description="智谱API基础URL")
    temperature: float = Field(default=0.7, env="ZHIPU_TEMPERATURE", description="智谱温度参数")
    max_tokens: int = Field(default=4096, env="ZHIPU_MAX_TOKENS", description="智谱最大token数")


class OpenRouterSettings(ModelSettings):
    """OpenRouter配置"""
    api_key: str = Field(..., env="OPENROUTER_API_KEY", description="OpenRouter API密钥")
    model: str = Field(default="meta-llama/llama-3.3-70b-instruct", env="OPENROUTER_MODEL", description="OpenRouter模型名称")
    base_url: str = Field(default="https://openrouter.ai/api/v1", env="OPENROUTER_BASE_URL", description="OpenRouter API基础URL")
    temperature: float = Field(default=0.7, env="OPENROUTER_TEMPERATURE", description="OpenRouter温度参数")
    max_tokens: int = Field(default=4096, env="OPENROUTER_MAX_TOKENS", description="OpenRouter最大token数")


class OpenAISettings(ModelSettings):
    """OpenAI配置"""
    api_key: str = Field(..., env="OPENAI_API_KEY", description="OpenAI API密钥")
    model: str = Field(default="gpt-4o", env="OPENAI_MODEL", description="OpenAI模型名称")
    base_url: str = Field(default="https://api.openai.com/v1", env="OPENAI_BASE_URL", description="OpenAI API基础URL")
    temperature: float = Field(default=0.7, env="OPENAI_TEMPERATURE", description="OpenAI温度参数")
    max_tokens: int = Field(default=4096, env="OPENAI_MAX_TOKENS", description="OpenAI最大token数")


class LocalLLMSettings(ModelSettings):
    """本地模型配置（OpenAI兼容服务）"""
    api_key: str = Field(default="local", env="LOCAL_LLM_API_KEY", description="本地模型API密钥")
    model: str = Field(default="qwen2.5:7b", env="LOCAL_LLM_MODEL", description="本地模型名称")
    base_url: str = Field(default="http://localhost:8000/v1", env="LOCAL_LLM_BASE_URL", description="本地模型API基础URL")
    temperature: float = Field(default=0.7, env="LOCAL_LLM_TEMPERATURE", description="本地模型温度参数")
    max_tokens: int = Field(default=4096, env="LOCAL_LLM_MAX_TOKENS", description="本地模型最大token数")
    timeout: int = Field(default=60, env="LOCAL_LLM_TIMEOUT", description="请求超时时间")
    max_retries: int = Field(default=3, env="LOCAL_LLM_MAX_RETRIES", description="最大重试次数")


class OllamaSettings(BaseSettings):
    """Ollama本地模型配置"""
    model: str = Field(default="qwen2.5:7b", env="OLLAMA_MODEL", description="Ollama模型名称")
    base_url: str = Field(default="http://localhost:11434", env="OLLAMA_BASE_URL", description="Ollama服务地址")
    auto_pull: bool = Field(default=False, env="OLLAMA_AUTO_PULL", description="是否自动拉取模型")
    timeout: int = Field(default=60, env="OLLAMA_TIMEOUT", description="请求超时时间")


class DashScopeSettings(ModelSettings):
    """阿里云DashScope配置（通义千问系列）"""
    api_key: str = Field(..., env="DASHSCOPE_API_KEY", description="DashScope API密钥")
    model: str = Field(default="qwen-turbo", env="DASHSCOPE_MODEL", description="DashScope模型名称（默认使用最便宜的qwen-turbo）")
    base_url: str = Field(default="https://dashscope.aliyuncs.com/compatible-mode/v1", env="DASHSCOPE_BASE_URL", description="DashScope API基础URL")
    temperature: float = Field(default=0.7, env="DASHSCOPE_TEMPERATURE", description="DashScope温度参数")
    max_tokens: int = Field(default=4096, env="DASHSCOPE_MAX_TOKENS", description="DashScope最大token数")


class ASRSettings(BaseSettings):
    """ASR语音识别配置"""
    provider: str = Field(default="local_whisper", env="ASR_PROVIDER", description="ASR提供商")
    model: str = Field(default="small", env="ASR_MODEL", description="ASR模型名称")
    device: str = Field(default="auto", env="ASR_DEVICE", description="ASR设备(auto/cpu/cuda)")
    compute_type: str = Field(default="int8_float16", env="ASR_COMPUTE_TYPE", description="推理精度")
    language: str = Field(default="zh", env="ASR_LANGUAGE", description="默认识别语言")
    download_root: str = Field(default="models/whisper", env="ASR_MODEL_DIR", description="模型下载目录")


class SearchSettings(BaseSettings):
    """搜索配置"""
    enabled: bool = Field(default=True, env="WEB_SEARCH_ENABLED", description="是否启用网络搜索")
    auto_search: bool = Field(default=True, env="AUTO_SEARCH_ENABLED", description="是否自动搜索")
    confidence_threshold: float = Field(default=0.5, env="SEARCH_CONFIDENCE_THRESHOLD", description="搜索置信度阈值")


class KnowledgeBaseSettings(BaseSettings):
    """知识库配置"""
    enabled: bool = Field(default=True, env="KNOWLEDGE_BASE_ENABLED", description="是否启用知识库")
    auto_search: bool = Field(default=True, env="AUTO_KNOWLEDGE_SEARCH_ENABLED", description="是否自动知识库搜索")
    confidence_threshold: float = Field(default=0.5, env="KNOWLEDGE_CONFIDENCE_THRESHOLD", description="知识库搜索置信度阈值")
    
    # 知识库集合配置
    collections: Dict[str, Dict[str, Any]] = Field(
        default_factory=lambda: {
            "script_segments": {
                "name": "script_segments_collection",
                "description": "剧本桥段库",
                "dimension": 768,
                "metric_type": "COSINE",
                "top_k": 5,
                "score_threshold": 0.7
            },
            "drama_highlights": {
                "name": "drama_highlights_collection",
                "description": "短剧高能情节库",
                "dimension": 768,
                "metric_type": "COSINE",
                "top_k": 5,
                "score_threshold": 0.7
            }
        }
    )


class IntentRecognitionSettings(BaseSettings):
    """意图识别配置"""
    enabled: bool = Field(default=True, env="INTENT_RECOGNITION_ENABLED", description="是否启用意图识别")
    confidence_threshold: float = Field(default=0.3, env="INTENT_CONFIDENCE_THRESHOLD", description="意图识别置信度阈值")
    
    # 意图模式配置
    patterns: Dict[str, Dict[str, Any]] = Field(
        default_factory=lambda: {
            "web_search": {
                "keywords": ["最新", "热门", "趋势", "市场", "竞品", "分析", "数据", "统计", "报告", "新闻", "资讯"],
                "patterns": ["最新.*?信息", "市场.*?分析", "竞品.*?对比", "行业.*?趋势", "数据.*?统计"]
            },
            "knowledge_base": {
                "keywords": ["桥段", "情节", "套路", "模板", "技巧", "方法", "创作", "写作", "剧本", "故事", "人物", "对话"],
                "patterns": ["创作.*?技巧", "写作.*?方法", "剧本.*?结构", "人物.*?塑造", "情节.*?设计"]
            },
            "url_extraction": {
                "keywords": ["链接", "网址", "文档", "文件", "资料"],
                "patterns": ["https?://[^\\s]+", "www\\.[^\\s]+", "\\.pdf", "\\.doc", "\\.docx", "\\.txt"]
            },
            "creation_assistance": {
                "keywords": ["策划", "创作", "写作", "剧本", "故事", "人物", "情节", "对话", "大纲", "结构", "主题", "风格", "类型", "题材", "设定"],
                "patterns": ["帮我.*?创作", "如何.*?写", "怎么.*?策划", "创作.*?建议"]
            }
        }
    )


class DramaPlanningSettings(BaseSettings):
    """竖屏短剧策划配置"""
    # 系统提示词配置
    system_prompt_enabled: bool = Field(default=True, env="SYSTEM_PROMPT_ENABLED", description="是否启用系统提示词")
    system_prompt_version: str = Field(default="1.0", env="SYSTEM_PROMPT_VERSION", description="系统提示词版本")
    
    # 工作流程配置
    auto_intent_recognition: bool = Field(default=True, env="AUTO_INTENT_RECOGNITION", description="是否自动意图识别")
    auto_web_search: bool = Field(default=True, env="AUTO_WEB_SEARCH", description="是否自动网络搜索")
    auto_knowledge_search: bool = Field(default=True, env="AUTO_KNOWLEDGE_SEARCH", description="是否自动知识库搜索")
    auto_url_extraction: bool = Field(default=True, env="AUTO_URL_EXTRACTION", description="是否自动URL提取")
    
    # 输出配置
    include_references: bool = Field(default=True, env="INCLUDE_REFERENCES", description="是否包含参考来源")
    include_sources: bool = Field(default=True, env="INCLUDE_SOURCES", description="是否包含来源信息")
    max_response_length: int = Field(default=8192, env="MAX_RESPONSE_LENGTH", description="最大响应长度")
    stream_chunk_size: int = Field(default=100, env="STREAM_CHUNK_SIZE", description="流式输出块大小")


class LoggingSettings(BaseSettings):
    """日志配置"""
    level: str = Field(default="INFO", env="LOG_LEVEL", description="日志级别")
    log_requests: bool = Field(default=True, env="LOG_REQUESTS", description="是否记录请求日志")
    log_responses: bool = Field(default=False, env="LOG_RESPONSES", description="是否记录响应日志")
    log_errors: bool = Field(default=True, env="LOG_ERRORS", description="是否记录错误日志")


class QuotaSettings(BaseSettings):
    """
    🆕 Token配额配置

    支持按用户级别设置每日Token使用配额
    """
    enabled: bool = Field(default=True, env="QUOTA_ENABLED", description="是否启用配额限制")

    # 默认配额（按用户等级）
    free_daily_quota: int = Field(default=100000, env="FREE_DAILY_QUOTA", description="免费用户每日配额")
    basic_daily_quota: int = Field(default=500000, env="BASIC_DAILY_QUOTA", description="基础用户每日配额")
    pro_daily_quota: int = Field(default=2000000, env="PRO_DAILY_QUOTA", description="专业用户每日配额")
    enterprise_daily_quota: int = Field(default=10000000, env="ENTERPRISE_DAILY_QUOTA", description="企业用户每日配额")

    # 配额检查行为
    quota_check_mode: str = Field(default="soft", env="QUOTA_CHECK_MODE", description="配额检查模式: soft(警告), hard(阻止)")

    # 智谱AI价格（元/1K tokens，2025年价格）
    zhipu_prices: Dict[str, float] = Field(
        default_factory=lambda: {
            "glm-4-flash": 0.0001,      # 输入: 0.0001元/1K tokens
            "glm-4-plus": 0.0025,      # 输入: 0.0025元/1K tokens
            "glm-4-0520": 0.0001,       # 输入: 0.0001元/1K tokens
            "glm-4-air": 0.001,        # 输入: 0.001元/1K tokens
            "glm-3-turbo": 0.00005,     # 输入: 0.00005元/1K tokens
            "completion_multiplier": 2.0   # 输出价格是输入的倍数
        }
    )

    # 用户等级映射
    user_level_mapping: Dict[str, str] = Field(
        default_factory=lambda: {
            "free": "free_daily_quota",
            "basic": "basic_daily_quota",
            "pro": "pro_daily_quota",
            "enterprise": "enterprise_daily_quota"
        }
    )

    # Redis存储配置
    redis_key_prefix: str = Field(default="quota", env="QUOTA_REDIS_PREFIX", description="Redis键前缀")
    daily_ttl: int = Field(default=86400 * 2, env="QUOTA_DAILY_TTL", description="每日数据过期时间（秒）")


class PerformanceSettings(BaseSettings):
    """性能配置"""
    timeout: int = Field(default=30, env="PERFORMANCE_TIMEOUT", description="请求超时时间")
    max_retries: int = Field(default=3, env="PERFORMANCE_MAX_RETRIES", description="最大重试次数")
    connection_pool_size: int = Field(default=10, env="CONNECTION_POOL_SIZE", description="连接池大小")
    enable_caching: bool = Field(default=True, env="ENABLE_CACHING", description="是否启用缓存")
    cache_ttl: int = Field(default=3600, env="CACHE_TTL", description="缓存生存时间")


class JubenSettings(BaseSettings):
    """竖屏短剧策划助手主配置"""
    
    # 应用配置
    app_name: str = Field(default="竖屏短剧策划助手", env="APP_NAME", description="应用名称")
    app_version: str = Field(default="1.0.0", env="APP_VERSION", description="应用版本")
    debug: bool = Field(default=False, env="DEBUG", description="调试模式")
    log_level: str = Field(default="INFO", env="LOG_LEVEL", description="日志级别")
    
    # 默认模型提供商
    default_provider: str = Field(default="dashscope", env="DEFAULT_MODEL_PROVIDER", description="默认模型提供商（阿里云DashScope）")

    # 模型配置
    dashscope: Optional[DashScopeSettings] = None
    zhipu: Optional[ZhipuSettings] = None
    openrouter: Optional[OpenRouterSettings] = None
    openai: Optional[OpenAISettings] = None
    local: Optional[LocalLLMSettings] = None
    ollama: Optional[OllamaSettings] = None
    asr: ASRSettings = Field(default_factory=ASRSettings)
    
    # 功能配置
    search: SearchSettings = Field(default_factory=SearchSettings)
    knowledge_base: KnowledgeBaseSettings = Field(default_factory=KnowledgeBaseSettings)
    intent_recognition: IntentRecognitionSettings = Field(default_factory=IntentRecognitionSettings)
    drama_planning: DramaPlanningSettings = Field(default_factory=DramaPlanningSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    performance: PerformanceSettings = Field(default_factory=PerformanceSettings)
    quota: QuotaSettings = Field(default_factory=QuotaSettings)

    # 上下文组织配置（Agent上下文增强）
    context_pack_enabled: bool = Field(default=True, env="CONTEXT_PACK_ENABLED", description="是否启用上下文打包")
    context_pack_max_chars: int = Field(default=2000, env="CONTEXT_PACK_MAX_CHARS", description="上下文打包最大字符数")
    context_tail_max_chars: int = Field(default=600, env="CONTEXT_TAIL_MAX_CHARS", description="上下文尾部摘要最大字符数")
    context_middle_term_limit: int = Field(default=5, env="CONTEXT_MIDDLE_TERM_LIMIT", description="中期记忆条数")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"  # 忽略额外的配置项
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._load_model_configs()
    
    def _load_model_configs(self):
        """加载模型配置"""
        # DashScope配置（阿里云）
        if os.getenv("DASHSCOPE_API_KEY"):
            try:
                self.dashscope = DashScopeSettings()
            except Exception:
                pass  # 忽略配置错误

        # 智谱配置
        if os.getenv("ZHIPU_API_KEY"):
            try:
                self.zhipu = ZhipuSettings()
            except Exception:
                pass  # 忽略配置错误

        # OpenRouter配置
        if os.getenv("OPENROUTER_API_KEY"):
            try:
                self.openrouter = OpenRouterSettings()
            except Exception:
                pass  # 忽略配置错误

        # OpenAI配置
        if os.getenv("OPENAI_API_KEY"):
            try:
                self.openai = OpenAISettings()
            except Exception:
                pass  # 忽略配置错误

        # 本地OpenAI兼容配置
        if os.getenv("LOCAL_LLM_BASE_URL") or os.getenv("LOCAL_LLM_MODEL"):
            try:
                self.local = LocalLLMSettings()
            except Exception:
                pass

        # Ollama配置
        if os.getenv("OLLAMA_BASE_URL") or os.getenv("OLLAMA_MODEL"):
            try:
                self.ollama = OllamaSettings()
            except Exception:
                pass
    
    def get_available_providers(self) -> List[str]:
        """获取可用的模型提供商列表"""
        providers = []
        if self.dashscope:
            providers.append("dashscope")
        if self.zhipu:
            providers.append("zhipu")
        if self.openrouter:
            providers.append("openrouter")
        if self.openai:
            providers.append("openai")
        if self.local:
            providers.append("local")
        if self.ollama:
            providers.append("ollama")
        return providers
    
    def get_model_config(self, provider: str) -> Optional[ModelSettings]:
        """获取指定提供商的配置"""
        config_map = {
            "dashscope": self.dashscope,
            "zhipu": self.zhipu,
            "openrouter": self.openrouter,
            "openai": self.openai,
            "local": self.local
        }
        return config_map.get(provider)
    
    def get_default_provider(self) -> str:
        """获取默认提供商"""
        available = self.get_available_providers()
        if self.default_provider in available:
            return self.default_provider
        return available[0] if available else "zhipu"
    
    def load_from_yaml(self, yaml_path: str):
        """从YAML文件加载配置"""
        try:
            with open(yaml_path, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)
            
            # 更新配置
            for key, value in config_data.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            
        except Exception as e:
            logger.error(f"加载YAML配置失败: {e}")
    
    def to_dict(self) -> Dict[str, Any]:
        """将配置转换为字典"""
        return {
            "app_name": self.app_name,
            "app_version": self.app_version,
            "debug": self.debug,
            "log_level": self.log_level,
            "default_provider": self.default_provider,
            "available_providers": self.get_available_providers(),
            "search": self.search.dict(),
            "knowledge_base": self.knowledge_base.dict(),
            "intent_recognition": self.intent_recognition.dict(),
            "drama_planning": self.drama_planning.dict(),
            "logging": self.logging.dict(),
            "performance": self.performance.dict(),
            "quota": self.quota.dict()
        }


# 全局配置实例
juben_settings = JubenSettings()
