"""
智能安全系统 -  
提供智能安全、威胁检测、访问控制和数据保护
"""
import asyncio
import hashlib
import hmac
import secrets
import time
from typing import Dict, Any, List, Optional, Union, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import jwt
import bcrypt
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

from .logger import JubenLogger
from .connection_pool_manager import get_connection_pool_manager


class SecurityLevel(Enum):
    """安全级别"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ThreatType(Enum):
    """威胁类型"""
    BRUTE_FORCE = "brute_force"
    SQL_INJECTION = "sql_injection"
    XSS = "xss"
    CSRF = "csrf"
    DDoS = "ddos"
    MALWARE = "malware"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    DATA_BREACH = "data_breach"


class AccessLevel(Enum):
    """访问级别"""
    READ = "read"
    WRITE = "write"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"


@dataclass
class SecurityEvent:
    """安全事件"""
    event_id: str
    event_type: str
    threat_type: ThreatType
    severity: SecurityLevel
    source_ip: str
    user_id: Optional[str]
    timestamp: datetime
    description: str
    details: Dict[str, Any] = field(default_factory=dict)
    resolved: bool = False
    resolved_at: Optional[datetime] = None


@dataclass
class AccessControl:
    """访问控制"""
    user_id: str
    resource: str
    access_level: AccessLevel
    granted_at: datetime
    expires_at: Optional[datetime] = None
    granted_by: Optional[str] = None


@dataclass
class SecurityPolicy:
    """安全策略"""
    name: str
    description: str
    rules: List[Dict[str, Any]]
    enabled: bool = True
    priority: int = 0


class SmartSecurity:
    """智能安全系统"""
    
    def __init__(self):
        self.logger = JubenLogger("smart_security")
        
        # 安全配置
        self.security_level = SecurityLevel.MEDIUM
        self.encryption_enabled = True
        self.audit_enabled = True
        self.threat_detection_enabled = True
        
        # 加密密钥
        self.encryption_key: Optional[bytes] = None
        self.jwt_secret: Optional[str] = None
        self.hmac_secret: Optional[str] = None
        
        # 安全事件
        self.security_events: List[SecurityEvent] = []
        self.threat_patterns: Dict[str, List[str]] = {}
        self.blocked_ips: List[str] = []
        self.blocked_users: List[str] = []
        
        # 访问控制
        self.access_controls: List[AccessControl] = []
        self.permissions: Dict[str, List[str]] = {}
        self.roles: Dict[str, List[str]] = {}
        
        # 安全策略
        self.security_policies: List[SecurityPolicy] = []
        self.policy_engine_enabled = True
        
        # 威胁检测
        self.threat_detectors: Dict[ThreatType, Callable] = {}
        self.anomaly_detectors: List[Callable] = []
        
        # 安全统计
        self.security_stats: Dict[str, Any] = {}
        self.performance_monitor = None
        
        # 安全回调
        self.security_callbacks: List[Callable] = []
        self.alert_callbacks: List[Callable] = []
        
        self.logger.info("🔒 智能安全系统初始化完成")
    
    async def initialize(self):
        """初始化安全系统"""
        try:
            # 生成加密密钥
            await self._generate_encryption_keys()
            
            # 加载安全策略
            await self._load_security_policies()
            
            # 初始化威胁检测器
            await self._initialize_threat_detectors()
            
            # 启动安全监控
            if self.threat_detection_enabled:
                await self._start_security_monitoring()
            
            self.logger.info("✅ 智能安全系统初始化完成")
            
        except Exception as e:
            self.logger.error(f"❌ 初始化安全系统失败: {e}")
    
    async def _generate_encryption_keys(self):
        """生成加密密钥"""
        try:
            # 生成Fernet密钥
            self.encryption_key = Fernet.generate_key()
            
            # 生成JWT密钥
            self.jwt_secret = secrets.token_urlsafe(32)
            
            # 生成HMAC密钥
            self.hmac_secret = secrets.token_urlsafe(32)
            
            self.logger.info("✅ 加密密钥已生成")
            
        except Exception as e:
            self.logger.error(f"❌ 生成加密密钥失败: {e}")
    
    async def _load_security_policies(self):
        """加载安全策略"""
        try:
            # 默认安全策略
            default_policies = [
                SecurityPolicy(
                    name="brute_force_protection",
                    description="暴力破解保护",
                    rules=[
                        {"type": "rate_limit", "max_attempts": 5, "window": 300},
                        {"type": "ip_block", "duration": 3600}
                    ],
                    priority=1
                ),
                SecurityPolicy(
                    name="sql_injection_protection",
                    description="SQL注入保护",
                    rules=[
                        {"type": "pattern_detection", "patterns": ["'", "union", "select", "drop"]},
                        {"type": "input_validation", "max_length": 1000}
                    ],
                    priority=2
                ),
                SecurityPolicy(
                    name="xss_protection",
                    description="XSS保护",
                    rules=[
                        {"type": "pattern_detection", "patterns": ["<script", "javascript:", "onclick"]},
                        {"type": "input_sanitization", "allowed_tags": []}
                    ],
                    priority=3
                )
            ]
            
            self.security_policies.extend(default_policies)
            
            self.logger.info(f"✅ 安全策略已加载: {len(default_policies)} 个")
            
        except Exception as e:
            self.logger.error(f"❌ 加载安全策略失败: {e}")
    
    async def _initialize_threat_detectors(self):
        """初始化威胁检测器"""
        try:
            # 暴力破解检测器
            self.threat_detectors[ThreatType.BRUTE_FORCE] = self._detect_brute_force
            
            # SQL注入检测器
            self.threat_detectors[ThreatType.SQL_INJECTION] = self._detect_sql_injection
            
            # XSS检测器
            self.threat_detectors[ThreatType.XSS] = self._detect_xss
            
            # CSRF检测器
            self.threat_detectors[ThreatType.CSRF] = self._detect_csrf
            
            # DDoS检测器
            self.threat_detectors[ThreatType.DDoS] = self._detect_ddos
            
            self.logger.info(f"✅ 威胁检测器已初始化: {len(self.threat_detectors)} 个")
            
        except Exception as e:
            self.logger.error(f"❌ 初始化威胁检测器失败: {e}")
    
    async def _start_security_monitoring(self):
        """启动安全监控"""
        try:
            # 启动威胁检测任务
            task = asyncio.create_task(self._threat_detection_task())
            asyncio.create_task(task)
            
            # 启动异常检测任务
            task = asyncio.create_task(self._anomaly_detection_task())
            asyncio.create_task(task)
            
            # 启动安全清理任务
            task = asyncio.create_task(self._security_cleanup_task())
            asyncio.create_task(task)
            
            self.logger.info("✅ 安全监控已启动")
            
        except Exception as e:
            self.logger.error(f"❌ 启动安全监控失败: {e}")
    
    async def _threat_detection_task(self):
        """威胁检测任务"""
        try:
            while True:
                await asyncio.sleep(30)  # 每30秒检查一次
                
                # 检查安全事件
                await self._analyze_security_events()
                
                # 更新威胁模式
                await self._update_threat_patterns()
                
        except asyncio.CancelledError:
            self.logger.info("🔍 威胁检测任务已取消")
        except Exception as e:
            self.logger.error(f"❌ 威胁检测任务失败: {e}")
    
    async def _anomaly_detection_task(self):
        """异常检测任务"""
        try:
            while True:
                await asyncio.sleep(60)  # 每分钟检查一次
                
                # 检测异常行为
                await self._detect_anomalies()
                
        except asyncio.CancelledError:
            self.logger.info("🔍 异常检测任务已取消")
        except Exception as e:
            self.logger.error(f"❌ 异常检测任务失败: {e}")
    
    async def _security_cleanup_task(self):
        """安全清理任务"""
        try:
            while True:
                await asyncio.sleep(3600)  # 每小时清理一次
                
                # 清理过期事件
                await self._cleanup_expired_events()
                
                # 清理过期访问控制
                await self._cleanup_expired_access_controls()
                
        except asyncio.CancelledError:
            self.logger.info("🧹 安全清理任务已取消")
        except Exception as e:
            self.logger.error(f"❌ 安全清理任务失败: {e}")
    
    async def _analyze_security_events(self):
        """分析安全事件"""
        try:
            # 分析最近的安全事件
            recent_events = [
                event for event in self.security_events
                if event.timestamp > datetime.now() - timedelta(hours=1)
            ]
            
            # 统计威胁类型
            threat_counts = {}
            for event in recent_events:
                threat_type = event.threat_type.value
                threat_counts[threat_type] = threat_counts.get(threat_type, 0) + 1
            
            # 更新安全统计
            self.security_stats['recent_threats'] = threat_counts
            self.security_stats['total_events'] = len(self.security_events)
            self.security_stats['blocked_ips'] = len(self.blocked_ips)
            self.security_stats['blocked_users'] = len(self.blocked_users)
            
        except Exception as e:
            self.logger.error(f"❌ 分析安全事件失败: {e}")
    
    async def _update_threat_patterns(self):
        """更新威胁模式"""
        try:
            # 分析威胁模式
            for threat_type in ThreatType:
                if threat_type in self.threat_detectors:
                    detector = self.threat_detectors[threat_type]
                    patterns = await detector()
                    if patterns:
                        self.threat_patterns[threat_type.value] = patterns
            
        except Exception as e:
            self.logger.error(f"❌ 更新威胁模式失败: {e}")
    
    async def _detect_anomalies(self):
        """检测异常行为"""
        try:
            # 检测异常登录
            await self._detect_anomalous_logins()
            
            # 检测异常访问模式
            await self._detect_anomalous_access_patterns()
            
            # 检测异常数据访问
            await self._detect_anomalous_data_access()
            
        except Exception as e:
            self.logger.error(f"❌ 检测异常行为失败: {e}")
    
    async def _detect_anomalous_logins(self):
        """检测异常登录"""
        try:
            # 检测来自不同地理位置的登录
            # 检测异常时间登录
            # 检测异常设备登录
            pass
            
        except Exception as e:
            self.logger.error(f"❌ 检测异常登录失败: {e}")
    
    async def _detect_anomalous_access_patterns(self):
        """检测异常访问模式"""
        try:
            # 检测异常访问频率
            # 检测异常访问路径
            # 检测异常访问时间
            pass
            
        except Exception as e:
            self.logger.error(f"❌ 检测异常访问模式失败: {e}")
    
    async def _detect_anomalous_data_access(self):
        """检测异常数据访问"""
        try:
            # 检测异常数据访问量
            # 检测异常数据访问时间
            # 检测异常数据访问模式
            pass
            
        except Exception as e:
            self.logger.error(f"❌ 检测异常数据访问失败: {e}")
    
    async def _detect_brute_force(self) -> List[str]:
        """检测暴力破解"""
        try:
            patterns = []
            
            # 检测多次失败登录
            failed_logins = {}
            for event in self.security_events:
                if event.threat_type == ThreatType.BRUTE_FORCE:
                    source_ip = event.source_ip
                    failed_logins[source_ip] = failed_logins.get(source_ip, 0) + 1
            
            # 识别暴力破解模式
            for source_ip, count in failed_logins.items():
                if count >= 5:  # 5次以上失败登录
                    patterns.append(f"brute_force_{source_ip}_{count}")
            
            return patterns
            
        except Exception as e:
            self.logger.error(f"❌ 检测暴力破解失败: {e}")
            return []
    
    async def _detect_sql_injection(self) -> List[str]:
        """检测SQL注入"""
        try:
            patterns = []
            
            # SQL注入模式
            sql_patterns = [
                "'", "union", "select", "drop", "insert", "update", "delete",
                "or 1=1", "and 1=1", "/*", "*/", "--", ";"
            ]
            
            # 检测SQL注入尝试
            for event in self.security_events:
                if event.threat_type == ThreatType.SQL_INJECTION:
                    for pattern in sql_patterns:
                        if pattern in event.description.lower():
                            patterns.append(f"sql_injection_{pattern}")
            
            return patterns
            
        except Exception as e:
            self.logger.error(f"❌ 检测SQL注入失败: {e}")
            return []
    
    async def _detect_xss(self) -> List[str]:
        """检测XSS"""
        try:
            patterns = []
            
            # XSS模式
            xss_patterns = [
                "<script", "javascript:", "onclick", "onload", "onerror",
                "alert(", "document.cookie", "window.location"
            ]
            
            # 检测XSS尝试
            for event in self.security_events:
                if event.threat_type == ThreatType.XSS:
                    for pattern in xss_patterns:
                        if pattern in event.description.lower():
                            patterns.append(f"xss_{pattern}")
            
            return patterns
            
        except Exception as e:
            self.logger.error(f"❌ 检测XSS失败: {e}")
            return []
    
    async def _detect_csrf(self) -> List[str]:
        """检测CSRF"""
        try:
            patterns = []
            
            # CSRF检测逻辑
            # 检查Referer头
            # 检查CSRF令牌
            # 检查请求来源
            
            return patterns
            
        except Exception as e:
            self.logger.error(f"❌ 检测CSRF失败: {e}")
            return []
    
    async def _detect_ddos(self) -> List[str]:
        """检测DDoS"""
        try:
            patterns = []
            
            # 检测高频率请求
            # 检测异常流量模式
            # 检测分布式攻击
            
            return patterns
            
        except Exception as e:
            self.logger.error(f"❌ 检测DDoS失败: {e}")
            return []
    
    async def _cleanup_expired_events(self):
        """清理过期事件"""
        try:
            cutoff_time = datetime.now() - timedelta(days=30)
            
            # 清理过期事件
            self.security_events = [
                event for event in self.security_events
                if event.timestamp > cutoff_time
            ]
            
            self.logger.info("🧹 过期安全事件已清理")
            
        except Exception as e:
            self.logger.error(f"❌ 清理过期事件失败: {e}")
    
    async def _cleanup_expired_access_controls(self):
        """清理过期访问控制"""
        try:
            current_time = datetime.now()
            
            # 清理过期访问控制
            self.access_controls = [
                ac for ac in self.access_controls
                if ac.expires_at is None or ac.expires_at > current_time
            ]
            
            self.logger.info("🧹 过期访问控制已清理")
            
        except Exception as e:
            self.logger.error(f"❌ 清理过期访问控制失败: {e}")
    
    def hash_password(self, password: str) -> str:
        """哈希密码"""
        try:
            salt = bcrypt.gensalt()
            hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
            return hashed.decode('utf-8')
            
        except Exception as e:
            self.logger.error(f"❌ 哈希密码失败: {e}")
            return ""
    
    def verify_password(self, password: str, hashed: str) -> bool:
        """验证密码"""
        try:
            return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
            
        except Exception as e:
            self.logger.error(f"❌ 验证密码失败: {e}")
            return False
    
    def generate_jwt_token(self, payload: Dict[str, Any], expires_in: int = 3600) -> str:
        """生成JWT令牌"""
        try:
            if not self.jwt_secret:
                raise ValueError("JWT密钥未设置")
            
            payload['exp'] = datetime.utcnow() + timedelta(seconds=expires_in)
            payload['iat'] = datetime.utcnow()
            
            token = jwt.encode(payload, self.jwt_secret, algorithm='HS256')
            return token
            
        except Exception as e:
            self.logger.error(f"❌ 生成JWT令牌失败: {e}")
            return ""
    
    def verify_jwt_token(self, token: str) -> Optional[Dict[str, Any]]:
        """验证JWT令牌"""
        try:
            if not self.jwt_secret:
                raise ValueError("JWT密钥未设置")
            
            payload = jwt.decode(token, self.jwt_secret, algorithms=['HS256'])
            return payload
            
        except jwt.ExpiredSignatureError:
            self.logger.warning("⚠️ JWT令牌已过期")
            return None
        except jwt.InvalidTokenError:
            self.logger.warning("⚠️ JWT令牌无效")
            return None
        except Exception as e:
            self.logger.error(f"❌ 验证JWT令牌失败: {e}")
            return None
    
    def encrypt_data(self, data: str) -> str:
        """加密数据"""
        try:
            if not self.encryption_key:
                raise ValueError("加密密钥未设置")
            
            fernet = Fernet(self.encryption_key)
            encrypted = fernet.encrypt(data.encode('utf-8'))
            return base64.b64encode(encrypted).decode('utf-8')
            
        except Exception as e:
            self.logger.error(f"❌ 加密数据失败: {e}")
            return ""
    
    def decrypt_data(self, encrypted_data: str) -> str:
        """解密数据"""
        try:
            if not self.encryption_key:
                raise ValueError("加密密钥未设置")
            
            fernet = Fernet(self.encryption_key)
            encrypted_bytes = base64.b64decode(encrypted_data.encode('utf-8'))
            decrypted = fernet.decrypt(encrypted_bytes)
            return decrypted.decode('utf-8')
            
        except Exception as e:
            self.logger.error(f"❌ 解密数据失败: {e}")
            return ""
    
    def generate_hmac(self, data: str) -> str:
        """生成HMAC"""
        try:
            if not self.hmac_secret:
                raise ValueError("HMAC密钥未设置")
            
            hmac_obj = hmac.new(
                self.hmac_secret.encode('utf-8'),
                data.encode('utf-8'),
                hashlib.sha256
            )
            return hmac_obj.hexdigest()
            
        except Exception as e:
            self.logger.error(f"❌ 生成HMAC失败: {e}")
            return ""
    
    def verify_hmac(self, data: str, hmac_value: str) -> bool:
        """验证HMAC"""
        try:
            expected_hmac = self.generate_hmac(data)
            return hmac.compare_digest(expected_hmac, hmac_value)
            
        except Exception as e:
            self.logger.error(f"❌ 验证HMAC失败: {e}")
            return False
    
    def record_security_event(
        self,
        event_type: str,
        threat_type: ThreatType,
        severity: SecurityLevel,
        source_ip: str,
        description: str,
        user_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """记录安全事件"""
        try:
            event = SecurityEvent(
                event_id=secrets.token_urlsafe(16),
                event_type=event_type,
                threat_type=threat_type,
                severity=severity,
                source_ip=source_ip,
                user_id=user_id,
                timestamp=datetime.now(),
                description=description,
                details=details or {}
            )
            
            self.security_events.append(event)
            
            # 触发安全回调
            asyncio.create_task(self._trigger_security_callbacks(event))
            
            # 检查是否需要阻止
            if severity in [SecurityLevel.HIGH, SecurityLevel.CRITICAL]:
                self._handle_critical_security_event(event)
            
            self.logger.warning(f"🚨 安全事件已记录: {event_type} - {description}")
            
        except Exception as e:
            self.logger.error(f"❌ 记录安全事件失败: {e}")
    
    def _handle_critical_security_event(self, event: SecurityEvent):
        """处理严重安全事件"""
        try:
            # 阻止IP
            if event.source_ip not in self.blocked_ips:
                self.blocked_ips.append(event.source_ip)
                self.logger.warning(f"🚫 IP已阻止: {event.source_ip}")
            
            # 阻止用户
            if event.user_id and event.user_id not in self.blocked_users:
                self.blocked_users.append(event.user_id)
                self.logger.warning(f"🚫 用户已阻止: {event.user_id}")
            
        except Exception as e:
            self.logger.error(f"❌ 处理严重安全事件失败: {e}")
    
    async def _trigger_security_callbacks(self, event: SecurityEvent):
        """触发安全回调"""
        try:
            for callback in self.security_callbacks:
                try:
                    await callback(event)
                except Exception as e:
                    self.logger.error(f"❌ 安全回调执行失败: {e}")
            
        except Exception as e:
            self.logger.error(f"❌ 触发安全回调失败: {e}")
    
    def is_ip_blocked(self, ip: str) -> bool:
        """检查IP是否被阻止"""
        return ip in self.blocked_ips
    
    def is_user_blocked(self, user_id: str) -> bool:
        """检查用户是否被阻止"""
        return user_id in self.blocked_users
    
    def block_ip(self, ip: str, duration: int = 3600):
        """阻止IP"""
        try:
            if ip not in self.blocked_ips:
                self.blocked_ips.append(ip)
                self.logger.warning(f"🚫 IP已阻止: {ip}")
            
        except Exception as e:
            self.logger.error(f"❌ 阻止IP失败: {e}")
    
    def unblock_ip(self, ip: str):
        """解封IP"""
        try:
            if ip in self.blocked_ips:
                self.blocked_ips.remove(ip)
                self.logger.info(f"✅ IP已解封: {ip}")
            
        except Exception as e:
            self.logger.error(f"❌ 解封IP失败: {e}")
    
    def block_user(self, user_id: str):
        """阻止用户"""
        try:
            if user_id not in self.blocked_users:
                self.blocked_users.append(user_id)
                self.logger.warning(f"🚫 用户已阻止: {user_id}")
            
        except Exception as e:
            self.logger.error(f"❌ 阻止用户失败: {e}")
    
    def unblock_user(self, user_id: str):
        """解封用户"""
        try:
            if user_id in self.blocked_users:
                self.blocked_users.remove(user_id)
                self.logger.info(f"✅ 用户已解封: {user_id}")
            
        except Exception as e:
            self.logger.error(f"❌ 解封用户失败: {e}")
    
    def add_security_callback(self, callback: Callable):
        """添加安全回调"""
        try:
            self.security_callbacks.append(callback)
            self.logger.info("✅ 安全回调已添加")
            
        except Exception as e:
            self.logger.error(f"❌ 添加安全回调失败: {e}")
    
    def add_alert_callback(self, callback: Callable):
        """添加告警回调"""
        try:
            self.alert_callbacks.append(callback)
            self.logger.info("✅ 告警回调已添加")
            
        except Exception as e:
            self.logger.error(f"❌ 添加告警回调失败: {e}")
    
    def get_security_stats(self) -> Dict[str, Any]:
        """获取安全统计"""
        try:
            return {
                'security_level': self.security_level.value,
                'encryption_enabled': self.encryption_enabled,
                'audit_enabled': self.audit_enabled,
                'threat_detection_enabled': self.threat_detection_enabled,
                'total_events': len(self.security_events),
                'blocked_ips': len(self.blocked_ips),
                'blocked_users': len(self.blocked_users),
                'threat_patterns': len(self.threat_patterns),
                'access_controls': len(self.access_controls),
                'security_policies': len(self.security_policies),
                'threat_detectors': len(self.threat_detectors),
                'security_callbacks': len(self.security_callbacks),
                'alert_callbacks': len(self.alert_callbacks),
                'stats': self.security_stats
            }
            
        except Exception as e:
            self.logger.error(f"❌ 获取安全统计失败: {e}")
            return {'error': str(e)}


# 全局智能安全实例
smart_security = SmartSecurity()


def get_smart_security() -> SmartSecurity:
    """获取智能安全实例"""
    return smart_security
