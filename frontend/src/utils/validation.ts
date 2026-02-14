/**
 * 验证工具函数
 */

/**
 * 验证邮箱地址
 */
export function isValidEmail(email: string): boolean {
  const regex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return regex.test(email);
}

/**
 * 验证 URL
 */
export function isValidUrl(url: string): boolean {
  try {
    new URL(url);
    return true;
  } catch {
    return false;
  }
}

/**
 * 验证手机号（中国大陆）
 */
export function isValidPhoneNumber(phone: string): boolean {
  const regex = /^1[3-9]\d{9}$/;
  return regex.test(phone);
}

/**
 * 验证用户名
 */
export function isValidUsername(username: string): boolean {
  // 4-20位，字母开头，只包含字母、数字、下划线
  const regex = /^[a-zA-Z][a-zA-Z0-9_]{3,19}$/;
  return regex.test(username);
}

/**
 * 验证密码强度
 */
export function validatePassword(password: string): {
  valid: boolean;
  strength: 'weak' | 'medium' | 'strong';
  issues: string[];
} {
  const issues: string[] = [];

  if (password.length < 8) {
    issues.push('密码长度至少8位');
  }

  if (!/[a-z]/.test(password)) {
    issues.push('密码需包含小写字母');
  }

  if (!/[A-Z]/.test(password)) {
    issues.push('密码需包含大写字母');
  }

  if (!/\d/.test(password)) {
    issues.push('密码需包含数字');
  }

  if (!/[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(password)) {
    issues.push('密码需包含特殊字符');
  }

  const valid = issues.length === 0;
  let strength: 'weak' | 'medium' | 'strong' = 'weak';

  if (valid) {
    if (password.length >= 12) {
      strength = 'strong';
    } else {
      strength = 'medium';
    }
  }

  return { valid, strength, issues };
}

/**
 * 验证文件类型
 */
export function isValidFileType(
  file: File,
  allowedTypes: string[]
): boolean {
  return allowedTypes.some(type => file.type.startsWith(type));
}

/**
 * 验证文件大小
 */
export function isValidFileSize(file: File, maxSizeMB: number): boolean {
  const maxSizeBytes = maxSizeMB * 1024 * 1024;
  return file.size <= maxSizeBytes;
}

/**
 * 验证 JSON
 */
export function isValidJson(json: string): boolean {
  try {
    JSON.parse(json);
    return true;
  } catch {
    return false;
  }
}

/**
 * 验证输入不为空
 */
export function isNotEmpty(value: string): boolean {
  return value.trim().length > 0;
}

/**
 * 验证字符串长度
 */
export function isValidLength(
  value: string,
  min: number,
  max: number
): boolean {
  return value.length >= min && value.length <= max;
}

/**
 * 验证范围
 */
export function isInRange(value: number, min: number, max: number): boolean {
  return value >= min && value <= max;
}
