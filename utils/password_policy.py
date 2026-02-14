"""
密码策略验证器

实施强密码策略和密码历史管理
"""
import re
import secrets
import string
from typing import List, Optional, Tuple
from datetime import datetime, timedelta

from utils.logger import get_logger
from utils.constants import PasswordPolicyConstants

logger = get_logger("PasswordPolicy")


class PasswordValidationError(Exception):
    """密码验证错误"""
    pass


class PasswordPolicyValidator:
    """
    密码策略验证器

    功能：
    1. 密码复杂度验证
    2. 密码历史管理
    3. 密码过期检测
    4. 密码强度评分
    5. 安全密码生成
    """

    def __init__(self):
        self._password_history: dict[str, List[dict]] = {}  # user_id -> [{hash, timestamp}]

    def validate_password(
        self,
        password: str,
        user_id: Optional[str] = None,
        check_history: bool = True
    ) -> Tuple[bool, Optional[str]]:
        """
        验证密码符合策略

        Args:
            password: 密码
            user_id: 用户 ID（用于检查历史）
            check_history: 是否检查密码历史

        Returns:
            (是否有效, 错误消息)
        """
        # 检查长度
        if len(password) < PasswordPolicyConstants.MIN_PASSWORD_LENGTH:
            return False, f"密码长度不能少于 {PasswordPolicyConstants.MIN_PASSWORD_LENGTH} 位"

        if len(password) > PasswordPolicyConstants.MAX_PASSWORD_LENGTH:
            return False, f"密码长度不能超过 {PasswordPolicyConstants.MAX_PASSWORD_LENGTH} 位"

        # 检查复杂度
        if PasswordPolicyConstants.REQUIRE_UPPERCASE and not re.search(r'[A-Z]', password):
            return False, "密码必须包含至少一个大写字母"

        if PasswordPolicyConstants.REQUIRE_LOWERCASE and not re.search(r'[a-z]', password):
            return False, "密码必须包含至少一个小写字母"

        if PasswordPolicyConstants.REQUIRE_DIGIT and not re.search(r'\d', password):
            return False, "密码必须包含至少一个数字"

        if PasswordPolicyConstants.REQUIRE_SPECIAL_CHAR:
            has_special = any(c in PasswordPolicyConstants.SPECIAL_CHARS for c in password)
            if not has_special:
                return False, f"密码必须包含至少一个特殊字符 ({PasswordPolicyConstants.SPECIAL_CHARS})"

        # 检查常见弱密码
        if self._is_common_password(password):
            return False, "密码过于常见，请使用更复杂的密码"

        # 检查密码历史
        if check_history and user_id:
            is_reused, days_ago = self._is_password_reused(user_id, password)
            if is_reused:
                if days_ago < PasswordPolicyConstants.PASSWORD_REUSE_DAYS:
                    return False, f"不能使用 {PasswordPolicyConstants.PASSWORD_REUSE_DAYS} 天内使用过的密码"

        return True, None

    def _is_common_password(self, password: str) -> bool:
        """检查是否为常见弱密码"""
        common_passwords = [
            "password", "123456", "12345678", "qwerty", "abc123",
            "monkey", "1234567", "letmein", "trustno1", "dragon",
            "baseball", "111111", "iloveyou", "master", "sunshine",
            "ashley", "bailey", "passw0rd", "shadow", "123123",
            "654321", "superman", "qazwsx", "michael", "password1"
        ]

        return password.lower() in common_passwords

    def _is_password_reused(
        self,
        user_id: str,
        password: str
    ) -> Tuple[bool, int]:
        """
        检查密码是否被重复使用

        Returns:
            (是否重复, 距上次使用的天数)
        """
        if user_id not in self._password_history:
            return False, 0

        password_hash = self._hash_password(password)
        now = datetime.now()

        for entry in self._password_history[user_id]:
            if entry["hash"] == password_hash:
                days_ago = (now - entry["timestamp"]).days
                return True, days_ago

        return False, 0

    def _hash_password(self, password: str) -> str:
        """哈希密码（用于历史记录，非存储）"""
        import hashlib
        return hashlib.sha256(password.encode()).hexdigest()

    def add_to_history(self, user_id: str, password_hash: str):
        """
        将密码添加到历史记录

        Args:
            user_id: 用户 ID
            password_hash: 已哈希的密码
        """
        if user_id not in self._password_history:
            self._password_history[user_id] = []

        self._password_history[user_id].append({
            "hash": password_hash,
            "timestamp": datetime.now()
        })

        # 只保留最近 N 个密码
        if len(self._password_history[user_id]) > PasswordPolicyConstants.PASSWORD_HISTORY_COUNT:
            self._password_history[user_id] = self._password_history[user_id][-PasswordPolicyConstants.PASSWORD_HISTORY_COUNT:]

    def check_password_expired(self, last_change_date: datetime) -> Tuple[bool, Optional[int]]:
        """
        检查密码是否过期

        Args:
            last_change_date: 上次密码修改日期

        Returns:
            (是否过期, 距离过期的天数)
        """
        now = datetime.now()
        days_since_change = (now - last_change_date).days
        days_until_expire = PasswordPolicyConstants.PASSWORD_EXPIRE_DAYS - days_since_change

        if days_until_expire <= 0:
            return True, 0
        elif days_until_expire <= PasswordPolicyConstants.PASSWORD_EXPIRE_WARNING_DAYS:
            # 即将过期
            return True, days_until_expire

        return False, days_until_expire

    def generate_password(
        self,
        length: Optional[int] = None,
        include_uppercase: bool = True,
        include_lowercase: bool = True,
        include_digits: bool = True,
        include_special: bool = True,
        exclude_ambiguous: bool = True
    ) -> str:
        """
        生成安全的随机密码

        Args:
            length: 密码长度
            include_uppercase: 包含大写字母
            include_lowercase: 包含小写字母
            include_digits: 包含数字
            include_special: 包含特殊字符
            exclude_ambiguous: 排除易混淆字符 (0OIl1)

        Returns:
            生成的密码
        """
        length = length or PasswordPolicyConstants.RECOMMENDED_PASSWORD_LENGTH

        # 字符集
        chars = ""
        if include_lowercase:
            chars += string.ascii_lowercase
        if include_uppercase:
            chars += string.ascii_uppercase
        if include_digits:
            chars += string.digits
        if include_special:
            chars += PasswordPolicyConstants.SPECIAL_CHARS

        if exclude_ambiguous:
            ambiguous = "0OIl1"
            chars = "".join(c for c in chars if c not in ambiguous)

        if not chars:
            chars = string.ascii_letters + string.digits

        # 生成密码
        password = "".join(secrets.choice(chars) for _ in range(length))

        # 确保满足所有要求
        if include_uppercase and not re.search(r'[A-Z]', password):
            password = self._ensure_char_type(password, string.ascii_uppercase)
        if include_lowercase and not re.search(r'[a-z]', password):
            password = self._ensure_char_type(password, string.ascii_lowercase)
        if include_digits and not re.search(r'\d', password):
            password = self._ensure_char_type(password, string.digits)
        if include_special and not any(c in PasswordPolicyConstants.SPECIAL_CHARS for c in password):
            password = self._ensure_char_type(password, PasswordPolicyConstants.SPECIAL_CHARS)

        return password

    def _ensure_char_type(self, password: str, char_set: str) -> str:
        """确保密码包含指定类型的字符"""
        password_list = list(password)
        # 随机替换一个字符
        idx = secrets.randbelow(len(password_list))
        password_list[idx] = secrets.choice(char_set)
        return "".join(password_list)

    def get_password_strength(self, password: str) -> dict:
        """
        获取密码强度评分

        Returns:
            包含强度信息的字典
        """
        score = 0
        feedback = []

        # 长度评分
        length_score = min(len(password) * 4, 40)
        score += length_score

        # 字符类型评分
        has_upper = bool(re.search(r'[A-Z]', password))
        has_lower = bool(re.search(r'[a-z]', password))
        has_digit = bool(re.search(r'\d', password))
        has_special = bool(re.search(r'[^A-Za-z0-9]', password))

        type_count = sum([has_upper, has_lower, has_digit, has_special])
        score += type_count * 10

        # 复杂度加分
        if type_count == 4:
            score += 20
        elif type_count == 3:
            score += 10

        # 常见密码扣分
        if self._is_common_password(password):
            score = max(0, score - 50)
            feedback.append("这是一个常见弱密码")

        # 确定强度等级
        if score < 30:
            strength = "weak"
            level = 1
        elif score < 60:
            strength = "fair"
            level = 2
        elif score < 80:
            strength = "good"
            level = 3
        else:
            strength = "strong"
            level = 4

        return {
            "score": min(score, 100),
            "strength": strength,
            "level": level,
            "feedback": feedback
        }

    def generate_reset_token(self) -> str:
        """生成密码重置令牌"""
        return secrets.token_urlsafe(32)

    def validate_reset_token(self, token: str, max_age_seconds: Optional[int] = None) -> bool:
        """
        验证重置令牌格式

        Args:
            token: 重置令牌
            max_age_seconds: 最大有效期（秒）

        Returns:
            是否有效
        """
        if not token:
            return False

        # 基本格式检查
        try:
            # URL-safe base64 应该是 43 个字符（32 字节）
            if len(token) < 32:
                return False
        except Exception:
            return False

        return True


# 全局密码策略验证器实例
_password_validator: Optional[PasswordPolicyValidator] = None


def get_password_validator() -> PasswordPolicyValidator:
    """获取密码策略验证器单例"""
    global _password_validator
    if _password_validator is None:
        _password_validator = PasswordPolicyValidator()
    return _password_validator
