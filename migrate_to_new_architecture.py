#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
竖屏短剧策划助手 - 架构迁移脚本
帮助用户从旧架构迁移到新架构
"""
import os
import shutil
import sys
from pathlib import Path
import logging

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def backup_old_files():
    """备份旧文件"""
    logger.info("开始备份旧文件...")
    
    backup_dir = Path("backup_old_architecture")
    backup_dir.mkdir(exist_ok=True)
    
    # 需要备份的文件
    files_to_backup = [
        "api_routes.py",
        "start_juben.py",
        "config.yaml",
        ".env",
        "base_juben_agent.py",
        "short_drama_planner_agent.py",
        "settings.py",
        "model_config.py",
        "openrouter_models.py",
        "tavily_search_client.py",
        "knowledge_base_client.py",
        "intent_recognition.py",
        "frontend_integration.py"
    ]
    
    for file_name in files_to_backup:
        old_file = Path(file_name)
        if old_file.exists():
            backup_file = backup_dir / file_name
            shutil.copy2(old_file, backup_file)
            logger.info(f"备份文件: {file_name} -> {backup_file}")
    
    logger.info(f"备份完成，文件保存在: {backup_dir.absolute()}")


def setup_new_environment():
    """设置新环境"""
    logger.info("开始设置新环境...")
    
    # 复制新的环境变量文件
    if Path("env.new").exists():
        if Path(".env").exists():
            logger.info("备份现有.env文件")
            shutil.copy2(".env", ".env.backup")
        
        shutil.copy2("env.new", ".env")
        logger.info("已设置新的环境变量文件")
    
    # 复制新的配置文件
    if Path("config.yaml.new").exists():
        if Path("config.yaml").exists():
            logger.info("备份现有config.yaml文件")
            shutil.copy2("config.yaml", "config.yaml.backup")
        
        shutil.copy2("config.yaml.new", "config.yaml")
        logger.info("已设置新的配置文件")
    
    logger.info("新环境设置完成")


def create_required_directories():
    """创建必需的目录"""
    logger.info("创建必需的目录...")
    
    directories = [
        "agents",
        "prompts", 
        "config",
        "utils",
        "logs"
    ]
    
    for directory in directories:
        dir_path = Path(directory)
        if not dir_path.exists():
            dir_path.mkdir(exist_ok=True)
            logger.info(f"创建目录: {directory}")
        else:
            logger.info(f"目录已存在: {directory}")
    
    logger.info("目录创建完成")


def install_dependencies():
    """安装依赖"""
    logger.info("检查并安装依赖...")
    
    required_packages = [
        "fastapi",
        "uvicorn",
        "pydantic",
        "python-dotenv",
        "aiohttp",
        "zhipuai"
    ]
    
    for package in required_packages:
        try:
            __import__(package.replace("-", "_"))
            logger.info(f"✓ {package} 已安装")
        except ImportError:
            logger.warning(f"✗ {package} 未安装，请运行: pip install {package}")
    
    logger.info("依赖检查完成")


def verify_new_architecture():
    """验证新架构"""
    logger.info("验证新架构...")
    
    required_files = [
        "agents/__init__.py",
        "agents/base_juben_agent.py",
        "agents/short_drama_planner_agent.py",
        "config/__init__.py",
        "config/settings.py",
        "prompts/short_drama_planner_system.txt",
        "utils/__init__.py",
        "utils/zhipu_search.py",
        "utils/knowledge_base_client.py",
        "utils/llm_client.py",
        "utils/logger.py",
        "utils/intent_recognition.py",
        "utils/url_extractor.py",
        "api_routes_new.py",
        "start_juben_new.py"
    ]
    
    missing_files = []
    for file_path in required_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)
    
    if missing_files:
        logger.error("以下文件缺失:")
        for file_path in missing_files:
            logger.error(f"  - {file_path}")
        return False
    
    logger.info("✓ 新架构文件验证通过")
    return True


def show_migration_summary():
    """显示迁移摘要"""
    logger.info("=" * 60)
    logger.info("竖屏短剧策划助手 - 架构迁移完成")
    logger.info("=" * 60)
    
    logger.info("新架构特性:")
    logger.info("✓  架构设计")
    logger.info("✓ 智谱AI搜索集成")
    logger.info("✓ 多模型支持 (智谱AI、OpenRouter、OpenAI)")
    logger.info("✓ 智能意图识别")
    logger.info("✓ 知识库RAG检索")
    logger.info("✓ URL内容提取")
    logger.info("✓ 流式输出支持")
    logger.info("✓ 完整的日志系统")
    logger.info("✓ 生产级配置管理")
    
    logger.info("\n启动新服务:")
    logger.info("python start_juben_new.py")
    
    logger.info("\nAPI文档:")
    logger.info("http://localhost:8000/docs")
    
    logger.info("\n配置文件:")
    logger.info("- 环境变量: .env")
    logger.info("- 系统配置: config.yaml")
    
    logger.info("\n重要提醒:")
    logger.info("1. 请检查.env文件中的API Key配置")
    logger.info("2. 旧文件已备份到backup_old_architecture目录")
    logger.info("3. 新架构使用智谱AI作为主要搜索和LLM提供商")
    logger.info("4. 已移除tavily_search和langsmith依赖")
    
    logger.info("=" * 60)


def main():
    """主函数"""
    logger.info("开始竖屏短剧策划助手架构迁移...")
    
    try:
        # 1. 备份旧文件
        backup_old_files()
        
        # 2. 创建必需目录
        create_required_directories()
        
        # 3. 设置新环境
        setup_new_environment()
        
        # 4. 安装依赖
        install_dependencies()
        
        # 5. 验证新架构
        if not verify_new_architecture():
            logger.error("新架构验证失败，请检查文件完整性")
            sys.exit(1)
        
        # 6. 显示迁移摘要
        show_migration_summary()
        
        logger.info("架构迁移成功完成！")
        
    except Exception as e:
        logger.error(f"迁移过程中发生错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
