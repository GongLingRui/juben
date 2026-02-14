"""统一缓存策略配置"""
import os
from utils.multi_level_cache import CacheConfig


def get_cache_config() -> CacheConfig:
    return CacheConfig(
        l1_max_size=int(os.getenv("CACHE_L1_MAX_SIZE", "1000")),
        l1_ttl=float(os.getenv("CACHE_L1_TTL", "300")),
        l2_ttl=float(os.getenv("CACHE_L2_TTL", "3600")),
        l2_prefix=os.getenv("CACHE_L2_PREFIX", "juben:cache:"),
        l3_enabled=os.getenv("CACHE_L3_ENABLED", "true").lower() == "true",
        l3_table=os.getenv("CACHE_L3_TABLE", "cache_store"),
        key_prefix=os.getenv("CACHE_KEY_PREFIX", ""),
        serialize=os.getenv("CACHE_SERIALIZE", "json"),
    )
