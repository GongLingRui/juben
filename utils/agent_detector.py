"""
Agent检测工具
检测各个agent的功能是否正确，工具是否可用
"""
import os
import sys
import inspect
import importlib
import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Union
from dataclasses import dataclass, asdict
from datetime import datetime
import traceback

logger = logging.getLogger(__name__)

try:
    from ..config.settings import JubenSettings
    from ..utils.logger import JubenLogger
    from ..utils.performance_monitor import get_performance_monitor
except ImportError:
    # 处理相对导入问题
    current_dir = Path(__file__).parent.parent
    sys.path.insert(0, str(current_dir))
    
    from config.settings import JubenSettings
    from utils.logger import JubenLogger
    from utils.performance_monitor import get_performance_monitor


@dataclass
class AgentCheckResult:
    """Agent检测结果"""
    agent_name: str
    agent_class: str
    is_available: bool
    has_required_methods: bool
    system_prompt_loaded: bool
    tools_status: Dict[str, bool]
    errors: List[str]
    warnings: List[str]
    performance_score: float
    last_check_time: str
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)


@dataclass
class ToolCheckResult:
    """工具检测结果"""
    tool_name: str
    is_available: bool
    error_message: Optional[str] = None
    response_time: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)


class AgentDetector:
    """Agent检测器"""
    
    def __init__(self):
        """初始化Agent检测器"""
        self.config = JubenSettings()
        self.logger = JubenLogger("AgentDetector", level=self.config.log_level)
        self.performance_monitor = get_performance_monitor()
        
        # 检测结果存储
        self.check_results: Dict[str, AgentCheckResult] = {}
        self.tool_check_results: Dict[str, Dict[str, ToolCheckResult]] = {}
        
        # 必需的Agent方法
        self.required_methods = [
            "process_request",
            "get_agent_info",
            "_call_llm",
            "_load_system_prompt"
        ]
        
        # 可选的工具方法
        self.optional_tools = [
            "_search_web",
            "_search_knowledge_base",
            "_emit_event",
            "save_agent_output",
            "auto_save_output"
        ]
        
        self.logger.info("Agent检测器初始化完成")
    
    def detect_all_agents(self, agents_dir: str = None) -> Dict[str, AgentCheckResult]:
        """
        检测所有Agent
        
        Args:
            agents_dir: Agent目录路径
            
        Returns:
            Dict[str, AgentCheckResult]: 检测结果
        """
        if agents_dir is None:
            agents_dir = Path(__file__).parent.parent / "agents"
        
        agents_dir = Path(agents_dir)
        
        if not agents_dir.exists():
            self.logger.error(f"Agent目录不存在: {agents_dir}")
            return {}
        
        self.logger.info(f"开始检测Agent目录: {agents_dir}")
        
        # 查找所有Agent文件
        agent_files = list(agents_dir.glob("*_agent.py"))
        
        if not agent_files:
            self.logger.warning("未找到任何Agent文件")
            return {}
        
        self.logger.info(f"找到{len(agent_files)}个Agent文件")
        
        # 检测每个Agent
        for agent_file in agent_files:
            try:
                result = self.detect_single_agent(agent_file)
                self.check_results[result.agent_name] = result
                
                if result.is_available:
                    self.logger.info(f"✅ Agent检测成功: {result.agent_name}")
                else:
                    self.logger.error(f"❌ Agent检测失败: {result.agent_name}")
                    
            except Exception as e:
                self.logger.error(f"❌ Agent检测异常 {agent_file.name}: {e}")
                # 创建失败结果
                agent_name = agent_file.stem
                self.check_results[agent_name] = AgentCheckResult(
                    agent_name=agent_name,
                    agent_class="",
                    is_available=False,
                    has_required_methods=False,
                    system_prompt_loaded=False,
                    tools_status={},
                    errors=[f"检测异常: {str(e)}"],
                    warnings=[],
                    performance_score=0.0,
                    last_check_time=datetime.now().isoformat()
                )
        
        return self.check_results
    
    def detect_single_agent(self, agent_file: Path) -> AgentCheckResult:
        """
        检测单个Agent
        
        Args:
            agent_file: Agent文件路径
            
        Returns:
            AgentCheckResult: 检测结果
        """
        agent_name = agent_file.stem
        errors = []
        warnings = []
        tools_status = {}
        
        try:
            # 导入Agent模块
            module_name = f"agents.{agent_name}"
            spec = importlib.util.spec_from_file_location(module_name, agent_file)
            if spec is None or spec.loader is None:
                raise ImportError(f"无法加载模块: {module_name}")
            
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # 查找Agent类
            agent_class = self._find_agent_class(module)
            if not agent_class:
                raise ValueError("未找到Agent类")
            
            # 检查必需方法
            has_required_methods = self._check_required_methods(agent_class)
            if not has_required_methods:
                errors.append("缺少必需的方法")
            
            # 检查系统提示词
            system_prompt_loaded = self._check_system_prompt(agent_name)
            if not system_prompt_loaded:
                warnings.append("系统提示词未加载")
            
            # 检查工具可用性
            tools_status = self._check_agent_tools(agent_class, agent_name)
            
            # 计算性能分数
            performance_score = self._calculate_performance_score(
                has_required_methods, system_prompt_loaded, tools_status
            )
            
            # 判断Agent是否可用
            is_available = (
                has_required_methods and 
                len([status for status in tools_status.values() if status]) > 0
            )
            
            return AgentCheckResult(
                agent_name=agent_name,
                agent_class=agent_class.__name__,
                is_available=is_available,
                has_required_methods=has_required_methods,
                system_prompt_loaded=system_prompt_loaded,
                tools_status=tools_status,
                errors=errors,
                warnings=warnings,
                performance_score=performance_score,
                last_check_time=datetime.now().isoformat()
            )
            
        except Exception as e:
            errors.append(f"检测失败: {str(e)}")
            return AgentCheckResult(
                agent_name=agent_name,
                agent_class="",
                is_available=False,
                has_required_methods=False,
                system_prompt_loaded=False,
                tools_status={},
                errors=errors,
                warnings=warnings,
                performance_score=0.0,
                last_check_time=datetime.now().isoformat()
            )
    
    def _find_agent_class(self, module) -> Optional[type]:
        """查找Agent类"""
        for name, obj in inspect.getmembers(module):
            if (inspect.isclass(obj) and 
                not name.startswith('_') and 
                'Agent' in name and
                obj.__module__ == module.__name__):
                return obj
        return None
    
    def _check_required_methods(self, agent_class: type) -> bool:
        """检查必需方法"""
        try:
            for method_name in self.required_methods:
                if not hasattr(agent_class, method_name):
                    self.logger.warning(f"缺少必需方法: {method_name}")
                    return False
                
                method = getattr(agent_class, method_name)
                if not callable(method):
                    self.logger.warning(f"方法不可调用: {method_name}")
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"检查必需方法失败: {e}")
            return False
    
    def _check_system_prompt(self, agent_name: str) -> bool:
        """检查系统提示词"""
        try:
            # 检查txt文件
            txt_file = Path(__file__).parent.parent / "prompts" / f"{agent_name}_system.txt"
            if txt_file.exists():
                return True
            
            # 检查python文件
            python_file = Path(__file__).parent.parent / "prompts" / "python_prompts" / f"{agent_name}_system.py"
            if python_file.exists():
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"检查系统提示词失败 {agent_name}: {e}")
            return False
    
    def _check_agent_tools(self, agent_class: type, agent_name: str) -> Dict[str, bool]:
        """检查Agent工具"""
        tools_status = {}
        
        # 检查可选工具方法
        for tool_name in self.optional_tools:
            try:
                has_tool = hasattr(agent_class, tool_name)
                if has_tool:
                    method = getattr(agent_class, tool_name)
                    is_callable = callable(method)
                    tools_status[tool_name] = is_callable
                else:
                    tools_status[tool_name] = False
                    
            except Exception as e:
                self.logger.error(f"检查工具失败 {tool_name}: {e}")
                tools_status[tool_name] = False
        
        # 检查特定Agent的工具
        specific_tools = self._get_specific_agent_tools(agent_name)
        for tool_name in specific_tools:
            try:
                has_tool = hasattr(agent_class, tool_name)
                tools_status[tool_name] = has_tool and callable(getattr(agent_class, tool_name))
            except Exception as e:
                self.logger.error(f"检查特定工具失败 {tool_name}: {e}")
                tools_status[tool_name] = False
        
        return tools_status
    
    def _get_specific_agent_tools(self, agent_name: str) -> List[str]:
        """获取特定Agent的工具列表"""
        specific_tools_map = {
            "websearch_agent": ["search_web", "search_knowledge"],
            "knowledge_agent": ["search_knowledge_base", "retrieve_documents"],
            "file_reference_agent": ["extract_file_content", "process_documents"],
            "text_splitter_agent": ["split_text", "chunk_text"],
            "text_truncator_agent": ["truncate_text", "smart_truncate"],
            "output_formatter_agent": ["format_output", "structure_response"],
            "drama_analysis_agent": ["analyze_drama", "extract_plot_points"],
            "story_evaluation_agent": ["evaluate_story", "score_analysis"],
            "character_profile_agent": ["generate_profile", "analyze_character"],
            "plot_points_agent": ["extract_plot_points", "analyze_structure"]
        }
        
        return specific_tools_map.get(agent_name, [])
    
    def _calculate_performance_score(
        self, 
        has_required_methods: bool, 
        system_prompt_loaded: bool, 
        tools_status: Dict[str, bool]
    ) -> float:
        """计算性能分数"""
        score = 0.0
        
        # 必需方法权重40%
        if has_required_methods:
            score += 0.4
        
        # 系统提示词权重20%
        if system_prompt_loaded:
            score += 0.2
        
        # 工具可用性权重40%
        available_tools = sum(1 for status in tools_status.values() if status)
        total_tools = len(tools_status)
        if total_tools > 0:
            score += 0.4 * (available_tools / total_tools)
        
        return score
    
    async def test_agent_functionality(self, agent_name: str, test_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        测试Agent功能
        
        Args:
            agent_name: Agent名称
            test_data: 测试数据
            
        Returns:
            Dict[str, Any]: 测试结果
        """
        if test_data is None:
            test_data = {"input": "测试输入", "user_id": "test_user", "session_id": "test_session"}
        
        try:
            # 导入Agent
            agent_module = importlib.import_module(f"agents.{agent_name}")
            agent_class = self._find_agent_class(agent_module)
            
            if not agent_class:
                return {
                    "success": False,
                    "error": "未找到Agent类",
                    "response_time": None
                }
            
            # 创建Agent实例
            start_time = datetime.now()
            agent_instance = agent_class(agent_name)
            
            # 测试process_request方法
            if hasattr(agent_instance, 'process_request'):
                # 使用asyncio运行异步方法
                if asyncio.iscoroutinefunction(agent_instance.process_request):
                    response = await agent_instance.process_request(test_data)
                else:
                    response = agent_instance.process_request(test_data)
                
                end_time = datetime.now()
                response_time = (end_time - start_time).total_seconds()
                
                return {
                    "success": True,
                    "response": str(response)[:500] + "..." if len(str(response)) > 500 else str(response),
                    "response_time": response_time,
                    "agent_info": agent_instance.get_agent_info() if hasattr(agent_instance, 'get_agent_info') else None
                }
            else:
                return {
                    "success": False,
                    "error": "Agent没有process_request方法",
                    "response_time": None
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "traceback": traceback.format_exc(),
                "response_time": None
            }
    
    def generate_detection_report(self) -> Dict[str, Any]:
        """生成检测报告"""
        try:
            total_agents = len(self.check_results)
            available_agents = sum(1 for result in self.check_results.values() if result.is_available)
            healthy_agents = sum(1 for result in self.check_results.values() if result.performance_score >= 0.7)
            
            # 按性能分数排序
            sorted_agents = sorted(
                self.check_results.values(),
                key=lambda x: x.performance_score,
                reverse=True
            )
            
            # 统计工具可用性
            tool_stats = {}
            for result in self.check_results.values():
                for tool_name, is_available in result.tools_status.items():
                    if tool_name not in tool_stats:
                        tool_stats[tool_name] = {"available": 0, "total": 0}
                    tool_stats[tool_name]["total"] += 1
                    if is_available:
                        tool_stats[tool_name]["available"] += 1
            
            report = {
                "timestamp": datetime.now().isoformat(),
                "summary": {
                    "total_agents": total_agents,
                    "available_agents": available_agents,
                    "healthy_agents": healthy_agents,
                    "availability_rate": available_agents / total_agents if total_agents > 0 else 0,
                    "health_rate": healthy_agents / total_agents if total_agents > 0 else 0
                },
                "agent_details": [result.to_dict() for result in sorted_agents],
                "tool_statistics": {
                    tool_name: {
                        "availability_rate": stats["available"] / stats["total"] if stats["total"] > 0 else 0,
                        "available_count": stats["available"],
                        "total_count": stats["total"]
                    }
                    for tool_name, stats in tool_stats.items()
                },
                "recommendations": self._generate_recommendations()
            }
            
            return report
            
        except Exception as e:
            self.logger.error(f"生成检测报告失败: {e}")
            return {"error": str(e)}
    
    def _generate_recommendations(self) -> List[str]:
        """生成改进建议"""
        recommendations = []
        
        # 分析检测结果
        unavailable_agents = [name for name, result in self.check_results.items() if not result.is_available]
        low_score_agents = [name for name, result in self.check_results.items() if result.performance_score < 0.5]
        missing_prompts = [name for name, result in self.check_results.items() if not result.system_prompt_loaded]
        
        if unavailable_agents:
            recommendations.append(f"修复不可用的Agent: {', '.join(unavailable_agents)}")
        
        if low_score_agents:
            recommendations.append(f"优化低分Agent: {', '.join(low_score_agents)}")
        
        if missing_prompts:
            recommendations.append(f"为以下Agent添加系统提示词: {', '.join(missing_prompts)}")
        
        # 检查工具可用性
        tool_issues = []
        for result in self.check_results.values():
            for tool_name, is_available in result.tools_status.items():
                if not is_available and tool_name in self.optional_tools:
                    tool_issues.append(f"{result.agent_name}.{tool_name}")
        
        if tool_issues:
            recommendations.append(f"修复不可用的工具: {', '.join(tool_issues[:5])}")  # 只显示前5个
        
        if not recommendations:
            recommendations.append("所有Agent运行正常，无需修复")
        
        return recommendations
    
    def save_detection_report(self, report: Dict[str, Any], output_file: str = None):
        """保存检测报告"""
        try:
            if output_file is None:
                reports_dir = Path(__file__).parent.parent / "logs" / "detection_reports"
                reports_dir.mkdir(parents=True, exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_file = reports_dir / f"agent_detection_report_{timestamp}.json"
            
            import json
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"检测报告已保存: {output_file}")
            
        except Exception as e:
            self.logger.error(f"保存检测报告失败: {e}")


async def main():
    """主函数 - 用于测试和演示"""
    # 设置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 创建Agent检测器
    detector = AgentDetector()

    logger.info("开始检测所有Agent...")

    # 检测所有Agent
    results = detector.detect_all_agents()

    logger.info(f"检测完成，共检测{len(results)}个Agent")

    # 显示检测结果
    for agent_name, result in results.items():
        status = "✅ 可用" if result.is_available else "❌ 不可用"
        logger.info(f"{agent_name}: {status} (分数: {result.performance_score:.2f})")

        if result.errors:
            logger.error(f"  错误: {', '.join(result.errors)}")
        if result.warnings:
            logger.warning(f"  警告: {', '.join(result.warnings)}")

    # 生成检测报告
    logger.info("生成检测报告...")
    report = detector.generate_detection_report()

    logger.info("报告摘要:")
    logger.info(f"总Agent数: {report['summary']['total_agents']}")
    logger.info(f"可用Agent数: {report['summary']['available_agents']}")
    logger.info(f"健康Agent数: {report['summary']['healthy_agents']}")
    logger.info(f"可用率: {report['summary']['availability_rate']:.2%}")
    logger.info(f"健康率: {report['summary']['health_rate']:.2%}")

    # 显示建议
    logger.info("改进建议:")
    for i, recommendation in enumerate(report['recommendations'], 1):
        logger.info(f"{i}. {recommendation}")

    # 保存报告
    detector.save_detection_report(report)

    logger.info("Agent检测完成")
    return True


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
