"""
系统管理工具
整合性能监控、Agent检测、LangSmith监控等功能
"""
import os
import sys
import asyncio
import logging
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import argparse

logger = logging.getLogger(__name__)

try:
    from ..config.settings import JubenSettings
    from ..utils.logger import JubenLogger
    from ..utils.performance_monitor import get_performance_monitor, start_global_monitoring, stop_global_monitoring
    from ..utils.agent_detector import AgentDetector
    from ..utils.prompt_converter import PromptConverter
    from ..utils.langsmith_client import LangSmithTracer
except ImportError:
    # 处理相对导入问题
    current_dir = Path(__file__).parent.parent
    sys.path.insert(0, str(current_dir))
    
    from config.settings import JubenSettings
    from utils.logger import JubenLogger
    from utils.performance_monitor import get_performance_monitor, start_global_monitoring, stop_global_monitoring
    from utils.agent_detector import AgentDetector
    from utils.prompt_converter import PromptConverter
    from utils.langsmith_client import LangSmithTracer


class SystemManager:
    """系统管理器"""
    
    def __init__(self):
        """初始化系统管理器"""
        self.config = JubenSettings()
        self.logger = JubenLogger("SystemManager", level=self.config.log_level)
        
        # 初始化各个组件
        self.performance_monitor = get_performance_monitor()
        self.agent_detector = AgentDetector()
        self.prompt_converter = PromptConverter()
        self.langsmith_tracer = LangSmithTracer(True)
        
        self.logger.info("系统管理器初始化完成")
    
    async def run_full_system_check(self) -> Dict[str, Any]:
        """
        运行完整的系统检查
        
        Returns:
            Dict[str, Any]: 检查结果
        """
        self.logger.info("开始运行完整系统检查...")
        
        results = {
            "timestamp": datetime.now().isoformat(),
            "system_status": {},
            "agent_status": {},
            "performance_status": {},
            "langsmith_status": {},
            "prompts_status": {},
            "recommendations": []
        }
        
        try:
            # 1. 检查系统配置
            results["system_status"] = await self._check_system_config()
            
            # 2. 检测所有Agent
            results["agent_status"] = await self._check_all_agents()
            
            # 3. 检查性能监控
            results["performance_status"] = await self._check_performance_monitoring()
            
            # 4. 检查LangSmith连接
            results["langsmith_status"] = await self._check_langsmith_connection()
            
            # 5. 检查系统提示词
            results["prompts_status"] = await self._check_system_prompts()
            
            # 6. 生成建议
            results["recommendations"] = self._generate_system_recommendations(results)
            
            self.logger.info("系统检查完成")
            return results
            
        except Exception as e:
            self.logger.error(f"系统检查失败: {e}")
            results["error"] = str(e)
            return results
    
    async def _check_system_config(self) -> Dict[str, Any]:
        """检查系统配置"""
        try:
            config_status = {
                "config_loaded": True,
                "default_provider": self.config.default_provider,
                "available_providers": self.config.get_available_providers(),
                "log_level": self.config.log_level,
                "debug_mode": self.config.debug
            }
            
            # 检查环境变量
            env_vars = {
                "ZHIPU_API_KEY": bool(os.getenv("ZHIPU_API_KEY")),
                "LANGCHAIN_API_KEY": bool(os.getenv("LANGCHAIN_API_KEY")),
                "OPENAI_API_KEY": bool(os.getenv("OPENAI_API_KEY")),
                "OPENROUTER_API_KEY": bool(os.getenv("OPENROUTER_API_KEY"))
            }
            
            config_status["environment_variables"] = env_vars
            
            return config_status
            
        except Exception as e:
            return {
                "config_loaded": False,
                "error": str(e)
            }
    
    async def _check_all_agents(self) -> Dict[str, Any]:
        """检查所有Agent"""
        try:
            # 检测所有Agent
            detection_results = self.agent_detector.detect_all_agents()
            
            # 生成检测报告
            report = self.agent_detector.generate_detection_report()
            
            return {
                "detection_completed": True,
                "total_agents": report["summary"]["total_agents"],
                "available_agents": report["summary"]["available_agents"],
                "healthy_agents": report["summary"]["healthy_agents"],
                "availability_rate": report["summary"]["availability_rate"],
                "health_rate": report["summary"]["health_rate"],
                "agent_details": report["agent_details"],
                "tool_statistics": report["tool_statistics"]
            }
            
        except Exception as e:
            return {
                "detection_completed": False,
                "error": str(e)
            }
    
    async def _check_performance_monitoring(self) -> Dict[str, Any]:
        """检查性能监控"""
        try:
            performance_summary = self.performance_monitor.get_performance_summary()
            
            return {
                "monitoring_active": True,
                "summary": performance_summary,
                "agent_health": {
                    name: health.to_dict() 
                    for name, health in self.performance_monitor.get_all_agent_health().items()
                }
            }
            
        except Exception as e:
            return {
                "monitoring_active": False,
                "error": str(e)
            }
    
    async def _check_langsmith_connection(self) -> Dict[str, Any]:
        """检查LangSmith连接"""
        try:
            # 检查API密钥
            api_key = os.getenv("LANGCHAIN_API_KEY")
            if not api_key:
                return {
                    "connected": False,
                    "error": "LANGCHAIN_API_KEY未设置"
                }
            
            # 验证API密钥格式
            if not api_key.startswith(('lsv2_pt_', 'ls__')):
                return {
                    "connected": False,
                    "error": "LANGCHAIN_API_KEY格式不正确"
                }
            
            # 检查LangSmith追踪器状态
            tracer_status = {
                "tracer_initialized": self.langsmith_tracer.enable_tracing,
                "project_name": self.langsmith_tracer.project_name,
                "api_key_set": bool(api_key)
            }
            
            return {
                "connected": True,
                "status": tracer_status
            }
            
        except Exception as e:
            return {
                "connected": False,
                "error": str(e)
            }
    
    async def _check_system_prompts(self) -> Dict[str, Any]:
        """检查系统提示词"""
        try:
            prompts_dir = Path(__file__).parent.parent / "prompts"
            python_prompts_dir = prompts_dir / "python_prompts"
            
            # 检查txt文件
            txt_files = list(prompts_dir.glob("*.txt"))
            python_files = list(python_prompts_dir.glob("*_system.py")) if python_prompts_dir.exists() else []
            
            return {
                "txt_files_count": len(txt_files),
                "python_files_count": len(python_files),
                "conversion_needed": len(txt_files) > 0,
                "conversion_completed": len(python_files) > 0
            }
            
        except Exception as e:
            return {
                "error": str(e)
            }
    
    def _generate_system_recommendations(self, results: Dict[str, Any]) -> List[str]:
        """生成系统建议"""
        recommendations = []
        
        # 检查配置建议
        system_status = results.get("system_status", {})
        if not system_status.get("config_loaded", False):
            recommendations.append("修复系统配置加载问题")
        
        env_vars = system_status.get("environment_variables", {})
        if not env_vars.get("ZHIPU_API_KEY", False):
            recommendations.append("设置ZHIPU_API_KEY环境变量")
        if not env_vars.get("LANGCHAIN_API_KEY", False):
            recommendations.append("设置LANGCHAIN_API_KEY环境变量")
        
        # 检查Agent建议
        agent_status = results.get("agent_status", {})
        if agent_status.get("availability_rate", 1.0) < 0.8:
            recommendations.append("修复不可用的Agent以提高系统可用性")
        
        if agent_status.get("health_rate", 1.0) < 0.7:
            recommendations.append("优化Agent性能以提高健康度")
        
        # 检查LangSmith建议
        langsmith_status = results.get("langsmith_status", {})
        if not langsmith_status.get("connected", False):
            recommendations.append("配置LangSmith连接以启用追踪功能")
        
        # 检查提示词建议
        prompts_status = results.get("prompts_status", {})
        if prompts_status.get("conversion_needed", False) and not prompts_status.get("conversion_completed", False):
            recommendations.append("将txt格式的系统提示词转换为python格式")
        
        # 检查性能监控建议
        performance_status = results.get("performance_status", {})
        if not performance_status.get("monitoring_active", False):
            recommendations.append("启动性能监控以跟踪系统性能")
        
        if not recommendations:
            recommendations.append("系统运行正常，无需修复")
        
        return recommendations
    
    async def start_monitoring(self, interval: int = 60):
        """启动系统监控"""
        try:
            start_global_monitoring(interval)
            self.logger.info(f"系统监控已启动，间隔: {interval}秒")
            return True
        except Exception as e:
            self.logger.error(f"启动系统监控失败: {e}")
            return False
    
    async def stop_monitoring(self):
        """停止系统监控"""
        try:
            stop_global_monitoring()
            self.logger.info("系统监控已停止")
            return True
        except Exception as e:
            self.logger.error(f"停止系统监控失败: {e}")
            return False
    
    async def convert_prompts(self) -> Dict[str, Any]:
        """转换系统提示词"""
        try:
            results = self.prompt_converter.convert_all_txt_to_python()
            success_count = sum(1 for success in results.values() if success)
            
            return {
                "conversion_completed": True,
                "total_files": len(results),
                "successful_conversions": success_count,
                "results": results
            }
        except Exception as e:
            return {
                "conversion_completed": False,
                "error": str(e)
            }
    
    async def test_agent(self, agent_name: str, test_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """测试单个Agent"""
        try:
            result = await self.agent_detector.test_agent_functionality(agent_name, test_data)
            return result
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def save_system_report(self, report: Dict[str, Any], output_file: str = None):
        """保存系统报告"""
        try:
            if output_file is None:
                reports_dir = Path(__file__).parent.parent / "logs" / "system_reports"
                reports_dir.mkdir(parents=True, exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_file = reports_dir / f"system_report_{timestamp}.json"
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"系统报告已保存: {output_file}")
            return str(output_file)
            
        except Exception as e:
            self.logger.error(f"保存系统报告失败: {e}")
            return None


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="系统管理工具")
    parser.add_argument("--action", choices=["check", "monitor", "convert", "test"], default="check",
                       help="执行的操作")
    parser.add_argument("--agent", help="要测试的Agent名称")
    parser.add_argument("--interval", type=int, default=60, help="监控间隔（秒）")
    parser.add_argument("--output", help="输出文件路径")
    
    args = parser.parse_args()
    
    # 设置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 创建系统管理器
    system_manager = SystemManager()
    
    try:
        if args.action == "check":
            logger.info("运行完整系统检查...")
            report = await system_manager.run_full_system_check()

            # 显示报告摘要
            logger.info("=== 系统检查报告 ===")
            logger.info(f"检查时间: {report['timestamp']}")

            # 系统状态
            system_status = report.get("system_status", {})
            logger.info(f"系统配置: {'✅ 正常' if system_status.get('config_loaded') else '❌ 异常'}")

            # Agent状态
            agent_status = report.get("agent_status", {})
            if agent_status.get("detection_completed"):
                logger.info(f"Agent状态: {agent_status['available_agents']}/{agent_status['total_agents']} 可用")
                logger.info(f"健康度: {agent_status['health_rate']:.2%}")

            # LangSmith状态
            langsmith_status = report.get("langsmith_status", {})
            logger.info(f"LangSmith: {'✅ 已连接' if langsmith_status.get('connected') else '❌ 未连接'}")

            # 性能监控状态
            performance_status = report.get("performance_status", {})
            logger.info(f"性能监控: {'✅ 活跃' if performance_status.get('monitoring_active') else '❌ 未启动'}")

            # 建议
            recommendations = report.get("recommendations", [])
            if recommendations:
                logger.info("改进建议:")
                for i, rec in enumerate(recommendations, 1):
                    logger.info(f"{i}. {rec}")

            # 保存报告
            output_file = system_manager.save_system_report(report, args.output)
            if output_file:
                logger.info(f"详细报告已保存: {output_file}")

        elif args.action == "monitor":
            logger.info(f"启动系统监控，间隔: {args.interval}秒")
            success = await system_manager.start_monitoring(args.interval)
            if success:
                logger.info("监控已启动，按Ctrl+C停止")
                try:
                    while True:
                        await asyncio.sleep(1)
                except KeyboardInterrupt:
                    logger.info("停止监控...")
                    await system_manager.stop_monitoring()
                    logger.info("监控已停止")
            else:
                logger.error("启动监控失败")

        elif args.action == "convert":
            logger.info("转换系统提示词...")
            result = await system_manager.convert_prompts()
            if result.get("conversion_completed"):
                logger.info(f"转换完成: {result['successful_conversions']}/{result['total_files']} 个文件成功")
            else:
                logger.error(f"转换失败: {result.get('error')}")

        elif args.action == "test":
            if not args.agent:
                logger.error("请指定要测试的Agent名称 (--agent)")
                return False

            logger.info(f"测试Agent: {args.agent}")
            result = await system_manager.test_agent(args.agent)
            if result.get("success"):
                logger.info(f"✅ 测试成功")
                logger.info(f"响应时间: {result.get('response_time', 'N/A')}秒")
                logger.info(f"响应内容: {result.get('response', 'N/A')[:200]}...")
            else:
                logger.error(f"❌ 测试失败: {result.get('error')}")

        return True

    except Exception as e:
        logger.error(f"操作失败: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
