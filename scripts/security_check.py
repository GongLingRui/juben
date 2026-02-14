#!/usr/bin/env python3
"""
安全检查脚本 - 在提交代码前检查敏感信息
运行: python scripts/security_check.py
"""
import os
import re
import sys
from pathlib import Path
from typing import List, Tuple

# 需要检查的敏感模式
SENSITIVE_PATTERNS = [
    r'sk-[a-zA-Z0-9]{48}',  # OpenAI API key
    r'sess-[a-zA-Z0-9]{40}',  # OpenAI session key
    r'AKLT[a-zA-Z0-9]{48}',  # 阿里云密钥
    r'LTAI[a-zA-Z0-9]{48}',  # 阿里云密钥
    r'gpt_:[a-zA-Z0-9]{48}',  # OpenAI GPT key
    r'oaic[a-zA-Z0-9]{32}',  # OpenAI OAuth
]

# 需要忽略的目录和文件
IGNORE_DIRS = {
    'node_modules',
    'venv',
    '__pycache__',
    '.git',
    'dist',
    'build',
    '.pytest_cache',
}


def should_ignore_file(file_path: Path) -> bool:
    """判断文件是否应该被忽略"""
    # 检查目录
    for part in file_path.parts:
        if part in IGNORE_DIRS:
            return True

    # 检查特定文件名
    if file_path.name in {'.env', '.env.local', '.gitignore'}:
        return True

    return False


def check_file_for_secrets(file_path: Path) -> List[Tuple[int, str, str]]:
    """检查文件中是否包含敏感信息"""
    issues = []

    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line_num, line in enumerate(f, 1):
                for pattern in SENSITIVE_PATTERNS:
                    matches = re.finditer(pattern, line, re.IGNORECASE)
                    for match in matches:
                        # 排除注释
                        if line.strip().startswith('#'):
                            continue
                        # 排除示例值
                        if any(x in match.group().lower() for x in ['your-', 'example', 'test', 'mock', 'fake', 'xxx', 'localhost']):
                            continue
                        issues.append((line_num, line.strip(), match.group()))
    except Exception as e:
        print(f"警告: 无法读取文件 {file_path}: {e}")

    return issues


def scan_directory(directory: Path, extensions: List[str]) -> List[Tuple[Path, List]]:
    """扫描目录查找敏感信息"""
    results = []

    for ext in extensions:
        for file_path in directory.rglob(f'*{ext}'):
            if should_ignore_file(file_path):
                continue

            issues = check_file_for_secrets(file_path)
            if issues:
                results.append((file_path, issues))

    return results


def main():
    """主函数"""
    print("🔍 开始安全检查...\n")

    # 获取项目根目录
    script_dir = Path(__file__).parent
    project_root = script_dir.parent

    # 检查的文件扩展名
    CODE_EXTENSIONS = ['.py', '.js', '.jsx', '.ts', '.tsx', '.yaml', '.yml', '.json']

    print(f"📂 扫描目录: {project_root}")
    print(f"📝 检查文件类型: {', '.join(CODE_EXTENSIONS)}\n")

    # 扫描代码
    results = scan_directory(project_root, CODE_EXTENSIONS)

    if not results:
        print("✅ 安全检查通过！未发现敏感信息。")
        return 0

    # 报告问题
    print(f"⚠️  发现 {len(results)} 个文件可能包含敏感信息:\n")

    for file_path, issues in results:
        # 只显示相对于项目根目录的路径
        rel_path = file_path.relative_to(project_root)
        print(f"📄 {rel_path}")
        print("-" * 80)

        # 只显示前3个问题
        for line_num, line, match in issues[:3]:
            print(f"  行 {line_num}: {line[:80]}")
            print(f"  匹配: {match}")
            print()

        if len(issues) > 3:
            print(f"  ... 还有 {len(issues) - 3} 个问题")
            print()

    print("\n" + "=" * 80)
    print("⚠️  请检查并修复以上问题后再提交代码！")
    print("\n💡 提示:")
    print("  1. 将敏感信息移到 .env 文件（已在 .gitignore 中）")
    print("  2. 使用环境变量引用（如 ${API_KEY}）")
    print("  3. 确保真实密钥不提交到代码库")
    print("\n")

    return 1


if __name__ == '__main__':
    sys.exit(main())
