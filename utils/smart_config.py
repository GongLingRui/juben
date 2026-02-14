"""
智能配置系统 -  
提供智能配置管理、动态配置、配置验证和配置热更新
"""
import asyncio
import json
import yaml
import os
from typing import Dict, Any, List, Optional, Union, Callable, Type, TypeVar
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
import threading
from pathlib import Path

from .logger import JubenLogger
from .connection_pool_manager import get_connection_pool_manager


class ConfigSource(Enum):
    """配置源"""
    ENV = "env"           # 环境变量
    FILE = "file"         # 文件
    DATABASE = "database" # 数据库
    REMOTE = "remote"     # 远程配置


class ConfigType(Enum):
    """配置类型"""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    LIST = "list"
    DICT = "dict"
    JSON = "json"


@dataclass
class ConfigItem:
    """配置项"""
    key: str
    value: Any
    config_type: ConfigType
    source: ConfigSource
    description: str = ""
    default_value: Any = None
    required: bool = False
    validation_rules: List[str] = field(default_factory=list)
    last_updated: datetime = field(default_factory=datetime.now)
    is_sensitive: bool = False


@dataclass
class ConfigSection:
    """配置节"""
    name: str
    items: Dict[str, ConfigItem] = field(default_factory=dict)
    description: str = ""
    last_updated: datetime = field(default_factory=datetime.now)


T = TypeVar('T')


class SmartConfig:
    """智能配置系统"""
    
    def __init__(self):
        self.logger = JubenLogger("smart_config")
        
        # 配置存储
        self.configs: Dict[str, ConfigItem] = {}
        self.sections: Dict[str, ConfigSection] = {}
        
        # 配置源
        self.sources: Dict[ConfigSource, Dict[str, Any]] = {
            ConfigSource.ENV: {},
            ConfigSource.FILE: {},
            ConfigSource.DATABASE: {},
            ConfigSource.REMOTE: {}
        }
        
        # 配置验证
        self.validators: Dict[str, Callable] = {}
        self.validation_rules: Dict[str, List[str]] = {}
        
        # 配置更新
        self.update_callbacks: Dict[str, List[Callable]] = {}
        self.watchers: Dict[str, List[Callable]] = {}
        
        # 配置缓存
        self.cache: Dict[str, Any] = {}
        self.cache_ttl: Dict[str, datetime] = {}
        self.default_cache_ttl = 300  # 5分钟
        
        # 配置热更新
        self.hot_reload_enabled = True
        self.watch_files: List[str] = []
        self.watch_tasks: List[asyncio.Task] = []
        
        # 配置加密
        self.encryption_enabled = False
        self.encryption_key: Optional[str] = None
        
        self.logger.info("⚙️ 智能配置系统初始化完成")
    
    async def initialize(self):
        """初始化配置系统"""
        try:
            # 加载默认配置
            await self._load_default_configs()
            
            # 加载环境变量配置
            await self._load_env_configs()
            
            # 加载文件配置
            await self._load_file_configs()
            
            # 启动配置监控
            if self.hot_reload_enabled:
                await self._start_config_watchers()
            
            self.logger.info("✅ 智能配置系统初始化完成")
            
        except Exception as e:
            self.logger.error(f"❌ 初始化配置系统失败: {e}")
    
    async def _load_default_configs(self):
        """加载默认配置"""
        try:
            # 系统默认配置
            default_configs = {
                'app.name': ConfigItem(
                    key='app.name',
                    value='JubenAI',
                    config_type=ConfigType.STRING,
                    source=ConfigSource.ENV,
                    description='应用名称',
                    required=True
                ),
                'app.version': ConfigItem(
                    key='app.version',
                    value='1.0.0',
                    config_type=ConfigType.STRING,
                    source=ConfigSource.ENV,
                    description='应用版本',
                    required=True
                ),
                'app.debug': ConfigItem(
                    key='app.debug',
                    value=False,
                    config_type=ConfigType.BOOLEAN,
                    source=ConfigSource.ENV,
                    description='调试模式',
                    default_value=False
                ),
                'app.log_level': ConfigItem(
                    key='app.log_level',
                    value='INFO',
                    config_type=ConfigType.STRING,
                    source=ConfigSource.ENV,
                    description='日志级别',
                    default_value='INFO'
                ),
                'database.url': ConfigItem(
                    key='database.url',
                    value='',
                    config_type=ConfigType.STRING,
                    source=ConfigSource.ENV,
                    description='数据库连接URL',
                    required=True,
                    is_sensitive=True
                ),
                'redis.url': ConfigItem(
                    key='redis.url',
                    value='redis://localhost:6379',
                    config_type=ConfigType.STRING,
                    source=ConfigSource.ENV,
                    description='Redis连接URL',
                    default_value='redis://localhost:6379'
                ),
                'llm.api_key': ConfigItem(
                    key='llm.api_key',
                    value='',
                    config_type=ConfigType.STRING,
                    source=ConfigSource.ENV,
                    description='LLM API密钥',
                    required=True,
                    is_sensitive=True
                ),
                'llm.model': ConfigItem(
                    key='llm.model',
                    value='gpt-3.5-turbo',
                    config_type=ConfigType.STRING,
                    source=ConfigSource.ENV,
                    description='LLM模型',
                    default_value='gpt-3.5-turbo'
                ),
                'llm.temperature': ConfigItem(
                    key='llm.temperature',
                    value=0.7,
                    config_type=ConfigType.FLOAT,
                    source=ConfigSource.ENV,
                    description='LLM温度',
                    default_value=0.7
                ),
                'llm.max_tokens': ConfigItem(
                    key='llm.max_tokens',
                    value=2000,
                    config_type=ConfigType.INTEGER,
                    source=ConfigSource.ENV,
                    description='LLM最大令牌数',
                    default_value=2000
                )
            }
            
            for key, config_item in default_configs.items():
                self.configs[key] = config_item
            
            self.logger.info(f"✅ 默认配置已加载: {len(default_configs)} 项")
            
        except Exception as e:
            self.logger.error(f"❌ 加载默认配置失败: {e}")
    
    async def _load_env_configs(self):
        """加载环境变量配置"""
        try:
            # 从环境变量加载配置
            for key, config_item in self.configs.items():
                env_key = key.upper().replace('.', '_')
                env_value = os.getenv(env_key)
                
                if env_value is not None:
                    # 转换类型
                    converted_value = self._convert_value(env_value, config_item.config_type)
                    if converted_value is not None:
                        config_item.value = converted_value
                        config_item.source = ConfigSource.ENV
                        config_item.last_updated = datetime.now()
            
            self.logger.info("✅ 环境变量配置已加载")
            
        except Exception as e:
            self.logger.error(f"❌ 加载环境变量配置失败: {e}")
    
    async def _load_file_configs(self):
        """加载文件配置"""
        try:
            # 配置文件路径
            config_files = [
                'config.json',
                'config.yaml',
                'config.yml',
                'juben_config.json',
                'juben_config.yaml'
            ]
            
            for config_file in config_files:
                if os.path.exists(config_file):
                    await self._load_config_file(config_file)
                    break
            
            self.logger.info("✅ 文件配置已加载")
            
        except Exception as e:
            self.logger.error(f"❌ 加载文件配置失败: {e}")
    
    async def _load_config_file(self, file_path: str):
        """加载配置文件"""
        try:
            # 🔒 安全验证：检查路径是否安全
            if not self._is_safe_path(file_path):
                self.logger.error(f"❌ 不安全的配置文件路径: {file_path}")
                return

            with open(file_path, 'r', encoding='utf-8') as f:
                if file_path.endswith('.json'):
                    config_data = json.load(f)
                elif file_path.endswith(('.yaml', '.yml')):
                    config_data = yaml.safe_load(f)
                else:
                    self.logger.warning(f"⚠️ 不支持的配置文件格式: {file_path}")
                    return

            # 🔒 验证配置数据结构
            if not isinstance(config_data, dict):
                self.logger.error(f"❌ 配置文件格式错误: {file_path} (应为字典)")
                return

            # 保存当前配置（用于回滚）
            old_configs = {}
            for key, config_item in self.configs.items():
                if config_item.source == ConfigSource.FILE:
                    old_configs[key] = config_item.value

            try:
                # 更新配置
                await self._update_configs_from_data(config_data, ConfigSource.FILE)

                # 🔒 验证新加载的配置
                validation_failed = False
                for key, value in config_data.items():
                    if not self._validate_config(key, value):
                        self.logger.error(f"❌ 配置验证失败: {key}={value}")
                        validation_failed = True
                        break

                if validation_failed:
                    # 回滚到旧配置
                    self.logger.warning(f"⚠️ 配置验证失败，回滚到旧配置: {file_path}")
                    await self._update_configs_from_data(old_configs, ConfigSource.FILE)
                    return

                # 添加到监控列表
                if file_path not in self.watch_files:
                    self.watch_files.append(file_path)

                self.logger.info(f"✅ 配置文件已加载并验证: {file_path}")

            except Exception as e:
                # 发生错误时回滚
                self.logger.error(f"❌ 加载配置文件时出错，回滚: {e}")
                await self._update_configs_from_data(old_configs, ConfigSource.FILE)
                raise

        except Exception as e:
            self.logger.error(f"❌ 加载配置文件失败: {file_path}: {e}")
    
    async def _update_configs_from_data(self, data: Dict[str, Any], source: ConfigSource):
        """从数据更新配置"""
        try:
            for key, value in data.items():
                if key in self.configs:
                    config_item = self.configs[key]
                    config_item.value = value
                    config_item.source = source
                    config_item.last_updated = datetime.now()
                else:
                    # 创建新的配置项
                    config_type = self._infer_config_type(value)
                    config_item = ConfigItem(
                        key=key,
                        value=value,
                        config_type=config_type,
                        source=source,
                        description=f"从{source.value}加载的配置"
                    )
                    self.configs[key] = config_item
                
                # 触发更新回调
                await self._trigger_update_callbacks(key, value)
            
        except Exception as e:
            self.logger.error(f"❌ 从数据更新配置失败: {e}")
    
    def _convert_value(self, value: str, config_type: ConfigType) -> Any:
        """
        转换值类型

        Args:
            value: 要转换的值
            config_type: 目标类型

        Returns:
            转换后的值，如果转换失败则返回该类型的默认值
        """
        try:
            if config_type == ConfigType.STRING:
                return str(value)
            elif config_type == ConfigType.INTEGER:
                return int(value)
            elif config_type == ConfigType.FLOAT:
                return float(value)
            elif config_type == ConfigType.BOOLEAN:
                return value.lower() in ('true', '1', 'yes', 'on')
            elif config_type == ConfigType.LIST:
                return json.loads(value) if value.startswith('[') else value.split(',')
            elif config_type == ConfigType.DICT:
                return json.loads(value) if value.startswith('{') else {}
            elif config_type == ConfigType.JSON:
                return json.loads(value)
            else:
                return str(value)

        except (ValueError, json.JSONDecodeError) as e:
            self.logger.warning(f"⚠️ 转换值类型失败: {value} -> {config_type.value}: {e}")
            # 返回该类型的默认值而不是 None
            return self._get_default_for_type(config_type)
        except Exception as e:
            self.logger.error(f"❌ 转换值类型时发生意外错误: {e}")
            return self._get_default_for_type(config_type)

    def _get_default_for_type(self, config_type: ConfigType) -> Any:
        """
        获取配置类型的默认值

        Args:
            config_type: 配置类型

        Returns:
            该类型的默认值
        """
        defaults = {
            ConfigType.STRING: "",
            ConfigType.INTEGER: 0,
            ConfigType.FLOAT: 0.0,
            ConfigType.BOOLEAN: False,
            ConfigType.LIST: [],
            ConfigType.DICT: {},
            ConfigType.JSON: {},
        }
        return defaults.get(config_type, "")
    
    def _infer_config_type(self, value: Any) -> ConfigType:
        """推断配置类型"""
        try:
            if isinstance(value, str):
                return ConfigType.STRING
            elif isinstance(value, int):
                return ConfigType.INTEGER
            elif isinstance(value, float):
                return ConfigType.FLOAT
            elif isinstance(value, bool):
                return ConfigType.BOOLEAN
            elif isinstance(value, list):
                return ConfigType.LIST
            elif isinstance(value, dict):
                return ConfigType.DICT
            else:
                return ConfigType.STRING
                
        except Exception as e:
            self.logger.error(f"❌ 推断配置类型失败: {e}")
            return ConfigType.STRING
    
    def get(self, key: str, default: Any = None, use_cache: bool = True) -> Any:
        """获取配置值"""
        try:
            # 检查缓存
            if use_cache and key in self.cache:
                cache_ttl = self.cache_ttl.get(key)
                if cache_ttl and datetime.now() < cache_ttl:
                    return self.cache[key]
            
            # 获取配置值
            if key in self.configs:
                value = self.configs[key].value
                
                # 更新缓存
                if use_cache:
                    self.cache[key] = value
                    self.cache_ttl[key] = datetime.now() + timedelta(seconds=self.default_cache_ttl)
                
                return value
            
            return default
            
        except Exception as e:
            self.logger.error(f"❌ 获取配置失败: {e}")
            return default
    
    def get_section(self, section_name: str) -> Dict[str, Any]:
        """获取配置节"""
        try:
            section_configs = {}
            
            for key, config_item in self.configs.items():
                if key.startswith(f"{section_name}."):
                    section_key = key[len(f"{section_name}."):]
                    section_configs[section_key] = config_item.value
            
            return section_configs
            
        except Exception as e:
            self.logger.error(f"❌ 获取配置节失败: {e}")
            return {}
    
    def set(self, key: str, value: Any, source: ConfigSource = ConfigSource.ENV) -> bool:
        """设置配置值"""
        try:
            # 验证配置
            if not self._validate_config(key, value):
                return False
            
            # 更新配置
            if key in self.configs:
                config_item = self.configs[key]
                config_item.value = value
                config_item.source = source
                config_item.last_updated = datetime.now()
            else:
                config_type = self._infer_config_type(value)
                config_item = ConfigItem(
                    key=key,
                    value=value,
                    config_type=config_type,
                    source=source,
                    description=f"动态设置的配置"
                )
                self.configs[key] = config_item
            
            # 清除缓存
            if key in self.cache:
                del self.cache[key]
                del self.cache_ttl[key]
            
            # 触发更新回调
            asyncio.create_task(self._trigger_update_callbacks(key, value))
            
            self.logger.info(f"✅ 配置已设置: {key} = {value}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 设置配置失败: {e}")
            return False
    
    def _validate_config(self, key: str, value: Any) -> bool:
        """验证配置"""
        try:
            # 检查必填配置
            if key in self.configs:
                config_item = self.configs[key]
                if config_item.required and value is None:
                    self.logger.error(f"❌ 必填配置为空: {key}")
                    return False
            
            # 执行自定义验证
            if key in self.validators:
                validator = self.validators[key]
                if not validator(value):
                    self.logger.error(f"❌ 配置验证失败: {key}")
                    return False
            
            # 执行验证规则
            if key in self.validation_rules:
                rules = self.validation_rules[key]
                for rule in rules:
                    if not self._apply_validation_rule(rule, value):
                        self.logger.error(f"❌ 配置验证规则失败: {key} - {rule}")
                        return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 验证配置失败: {e}")
            return False
    
    def _apply_validation_rule(self, rule: str, value: Any) -> bool:
        """应用验证规则"""
        try:
            if rule.startswith('min:'):
                min_value = float(rule.split(':')[1])
                return float(value) >= min_value
            elif rule.startswith('max:'):
                max_value = float(rule.split(':')[1])
                return float(value) <= max_value
            elif rule.startswith('min_length:'):
                min_length = int(rule.split(':')[1])
                return len(str(value)) >= min_length
            elif rule.startswith('max_length:'):
                max_length = int(rule.split(':')[1])
                return len(str(value)) <= max_length
            elif rule.startswith('pattern:'):
                pattern = rule.split(':', 1)[1]
                import re
                return bool(re.match(pattern, str(value)))
            elif rule.startswith('in:'):
                allowed_values = rule.split(':')[1].split(',')
                return str(value) in allowed_values
            else:
                return True
                
        except Exception as e:
            self.logger.error(f"❌ 应用验证规则失败: {e}")
            return False
    
    async def _trigger_update_callbacks(self, key: str, value: Any):
        """触发更新回调"""
        try:
            if key in self.update_callbacks:
                for callback in self.update_callbacks[key]:
                    try:
                        await callback(key, value)
                    except Exception as e:
                        self.logger.error(f"❌ 配置更新回调失败: {e}")
            
        except Exception as e:
            self.logger.error(f"❌ 触发更新回调失败: {e}")
    
    def add_validator(self, key: str, validator: Callable):
        """添加验证器"""
        try:
            self.validators[key] = validator
            self.logger.info(f"✅ 验证器已添加: {key}")
            
        except Exception as e:
            self.logger.error(f"❌ 添加验证器失败: {e}")
    
    def add_validation_rule(self, key: str, rule: str):
        """添加验证规则"""
        try:
            if key not in self.validation_rules:
                self.validation_rules[key] = []
            self.validation_rules[key].append(rule)
            self.logger.info(f"✅ 验证规则已添加: {key} - {rule}")
            
        except Exception as e:
            self.logger.error(f"❌ 添加验证规则失败: {e}")
    
    def add_update_callback(self, key: str, callback: Callable):
        """添加更新回调"""
        try:
            if key not in self.update_callbacks:
                self.update_callbacks[key] = []
            self.update_callbacks[key].append(callback)
            self.logger.info(f"✅ 更新回调已添加: {key}")
            
        except Exception as e:
            self.logger.error(f"❌ 添加更新回调失败: {e}")
    
    def add_watcher(self, key: str, callback: Callable):
        """添加配置监控"""
        try:
            if key not in self.watchers:
                self.watchers[key] = []
            self.watchers[key].append(callback)
            self.logger.info(f"✅ 配置监控已添加: {key}")
            
        except Exception as e:
            self.logger.error(f"❌ 添加配置监控失败: {e}")
    
    async def _start_config_watchers(self):
        """启动配置监控"""
        try:
            if not self.watch_files:
                return
            
            # 监控文件变化
            for file_path in self.watch_files:
                task = asyncio.create_task(self._watch_file(file_path))
                self.watch_tasks.append(task)
            
            self.logger.info(f"✅ 配置监控已启动: {len(self.watch_files)} 个文件")
            
        except Exception as e:
            self.logger.error(f"❌ 启动配置监控失败: {e}")
    
    async def _watch_file(self, file_path: str):
        """监控文件变化"""
        try:
            # 🔒 安全验证：检查路径是否在允许的目录中
            if not self._is_safe_path(file_path):
                self.logger.error(f"❌ 不安全的文件路径: {file_path}")
                return

            last_modified = 0

            while True:
                await asyncio.sleep(5)  # 每5秒检查一次

                try:
                    # 再次验证路径（防止TOCTOU攻击）
                    if not self._is_safe_path(file_path):
                        self.logger.error(f"❌ 文件路径不再安全: {file_path}")
                        break

                    current_modified = os.path.getmtime(file_path)

                    if current_modified > last_modified:
                        last_modified = current_modified

                        # 重新加载配置文件
                        await self._load_config_file(file_path)

                        self.logger.info(f"🔄 配置文件已更新: {file_path}")

                except FileNotFoundError:
                    self.logger.warning(f"⚠️ 配置文件不存在: {file_path}")
                    break
                except Exception as e:
                    self.logger.error(f"❌ 监控文件失败: {file_path}: {e}")

        except asyncio.CancelledError:
            self.logger.info(f"📁 文件监控已取消: {file_path}")
        except Exception as e:
            self.logger.error(f"❌ 文件监控失败: {file_path}: {e}")

    def _is_safe_path(self, file_path: str) -> bool:
        """
        检查文件路径是否安全（防止路径遍历攻击）

        Args:
            file_path: 要检查的文件路径

        Returns:
            bool: 路径是否安全
        """
        try:
            # 规范化路径
            resolved_path = Path(file_path).resolve()

            # 定义允许的配置目录白名单
            allowed_directories = [
                Path.cwd(),  # 当前工作目录
                Path("/etc/juben"),  # 系统配置目录（如果存在）
                Path.home() / ".config" / "juben",  # 用户配置目录
                Path("config").resolve(),  # 项目配置目录
            ]

            # 检查路径是否在允许的目录中
            for allowed_dir in allowed_directories:
                try:
                    resolved_allowed = allowed_dir.resolve()
                    # 检查路径是否以允许的目录开头
                    if str(resolved_path).startswith(str(resolved_allowed)):
                        return True
                except Exception:
                    continue

            self.logger.warning(f"⚠️ 文件路径不在允许的目录中: {file_path}")
            return False

        except Exception as e:
            self.logger.error(f"❌ 检查路径安全性失败: {e}")
            return False
    
    def get_config_stats(self) -> Dict[str, Any]:
        """获取配置统计"""
        try:
            # 统计配置源
            source_stats = {}
            for config_item in self.configs.values():
                source = config_item.source.value
                source_stats[source] = source_stats.get(source, 0) + 1
            
            # 统计配置类型
            type_stats = {}
            for config_item in self.configs.values():
                config_type = config_item.config_type.value
                type_stats[config_type] = type_stats.get(config_type, 0) + 1
            
            return {
                'total_configs': len(self.configs),
                'source_stats': source_stats,
                'type_stats': type_stats,
                'hot_reload_enabled': self.hot_reload_enabled,
                'watch_files': len(self.watch_files),
                'watch_tasks': len(self.watch_tasks),
                'validators': len(self.validators),
                'validation_rules': len(self.validation_rules),
                'update_callbacks': len(self.update_callbacks),
                'watchers': len(self.watchers),
                'cache_size': len(self.cache),
                'encryption_enabled': self.encryption_enabled
            }
            
        except Exception as e:
            self.logger.error(f"❌ 获取配置统计失败: {e}")
            return {'error': str(e)}


# 全局智能配置实例
smart_config = SmartConfig()


def get_smart_config() -> SmartConfig:
    """获取智能配置实例"""
    return smart_config
