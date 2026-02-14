"""
Reflexion反思机制 - 从错误中学习，提炼规则
基于事件驱动的反思学习系统
"""
import os
import json
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import hashlib
import uuid

try:
    from ..config.settings import JubenSettings
    from ..utils.logger import JubenLogger
    from ..utils.storage_manager import JubenStorageManager, Note
    from ..utils.llm_client import JubenLLMClient
    from ..utils.vector_store import VectorStore
except ImportError:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    
    from config.settings import JubenSettings
    from utils.logger import JubenLogger
    from utils.storage_manager import JubenStorageManager, Note
    from utils.llm_client import JubenLLMClient
    from utils.vector_store import VectorStore


@dataclass
class FailureEvent:
    """失败事件"""
    id: str
    action: str  # 执行的动作
    expected_result: str  # 期望结果
    actual_result: str  # 实际结果
    failure_reason: str  # 失败原因
    context: Dict[str, Any]  # 上下文信息
    timestamp: str
    severity: str  # low, medium, high
    user_id: str
    session_id: str
    agent_name: str


@dataclass
class ReflectionRule:
    """反思规则"""
    id: str
    rule_name: str
    rule_description: str
    trigger_conditions: List[str]  # 触发条件
    prevention_strategy: str  # 预防策略
    success_examples: List[str]  # 成功案例
    failure_examples: List[str]  # 失败案例
    confidence_score: float  # 0-1
    usage_count: int
    created_at: str
    updated_at: str
    tags: List[str]
    metadata: Dict[str, Any]


@dataclass
class MetaPrompt:
    """元提示"""
    id: str
    prompt_type: str  # failure_analysis, rule_generation, strategy_refinement
    original_prompt: str
    enhanced_prompt: str
    context: Dict[str, Any]
    effectiveness_score: float  # 0-1
    created_at: str
    updated_at: str


class ReflexionMechanism:
    """Reflexion反思机制"""
    
    def __init__(self, model_provider: str = "zhipu"):
        """
        初始化反思机制
        
        Args:
            model_provider: 模型提供商
        """
        self.config = JubenSettings()
        self.logger = JubenLogger("ReflexionMechanism", level=self.config.log_level)
        self.storage_manager = JubenStorageManager()
        self.llm_client = JubenLLMClient(model_provider)
        self.vector_store = VectorStore()
        
        # 反思状态
        self.failure_events: Dict[str, FailureEvent] = {}
        self.reflection_rules: Dict[str, ReflectionRule] = {}
        self.meta_prompts: Dict[str, MetaPrompt] = {}
        
        # 反思配置
        self.reflection_config = {
            "auto_reflection": True,
            "failure_threshold": 3,  # 3次失败后触发反思
            "rule_confidence_threshold": 0.7,  # 规则置信度阈值
            "meta_prompt_effectiveness_threshold": 0.8,  # 元提示有效性阈值
            "max_rules_per_category": 50,  # 每类别最大规则数
            "reflection_interval_hours": 24  # 反思间隔（小时）
        }
        
        self.logger.info("Reflexion反思机制初始化完成")
    
    async def initialize(self):
        """初始化反思机制"""
        try:
            await self.storage_manager.initialize()
            await self.vector_store.initialize()
            self.logger.info("✅ Reflexion反思机制初始化成功")
        except Exception as e:
            self.logger.error(f"❌ Reflexion反思机制初始化失败: {e}")
            raise
    
    async def detect_failure(
        self,
        action: str,
        expected_result: str,
        actual_result: str,
        context: Dict[str, Any],
        user_id: str,
        session_id: str,
        agent_name: str
    ) -> Optional[FailureEvent]:
        """
        检测失败事件
        
        Args:
            action: 执行的动作
            expected_result: 期望结果
            actual_result: 实际结果
            context: 上下文信息
            user_id: 用户ID
            session_id: 会话ID
            agent_name: Agent名称
            
        Returns:
            失败事件对象（如果检测到失败）
        """
        try:
            # 分析结果差异
            failure_analysis = await self._analyze_failure(
                action, expected_result, actual_result, context
            )
            
            if not failure_analysis['is_failure']:
                return None
            
            # 创建失败事件
            failure_event = FailureEvent(
                id=str(uuid.uuid4()),
                action=action,
                expected_result=expected_result,
                actual_result=actual_result,
                failure_reason=failure_analysis['reason'],
                context=context,
                timestamp=datetime.now().isoformat(),
                severity=failure_analysis['severity'],
                user_id=user_id,
                session_id=session_id,
                agent_name=agent_name
            )
            
            # 存储失败事件
            self.failure_events[failure_event.id] = failure_event
            
            # 触发反思流程
            await self._trigger_reflection(failure_event)
            
            self.logger.info(f"🔍 检测到失败事件: {failure_event.id}")
            return failure_event
            
        except Exception as e:
            self.logger.error(f"失败检测失败: {e}")
            return None
    
    async def _analyze_failure(
        self,
        action: str,
        expected_result: str,
        actual_result: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """分析失败原因"""
        try:
            # 构建失败分析提示词
            prompt = self._build_failure_analysis_prompt(
                action, expected_result, actual_result, context
            )
            
            # 调用LLM分析
            response = await self.llm_client.generate_response(
                prompt=prompt,
                max_tokens=1000,
                temperature=0.3
            )
            
            if response and response.get('content'):
                # 解析分析结果
                return self._parse_failure_analysis(response['content'])
            else:
                # 使用简单分析
                return self._simple_failure_analysis(
                    action, expected_result, actual_result
                )
                
        except Exception as e:
            self.logger.error(f"失败分析失败: {e}")
            return {
                'is_failure': True,
                'reason': f'分析失败: {str(e)}',
                'severity': 'medium'
            }
    
    def _build_failure_analysis_prompt(
        self,
        action: str,
        expected_result: str,
        actual_result: str,
        context: Dict[str, Any]
    ) -> str:
        """构建失败分析提示词"""
        prompt = f"""
你是一个专业的失败分析专家，需要分析AI系统的失败情况并确定失败原因。

## 失败信息
- **执行动作**: {action}
- **期望结果**: {expected_result}
- **实际结果**: {actual_result}
- **上下文**: {json.dumps(context, ensure_ascii=False, indent=2)}

## 分析任务
请分析以上情况是否构成失败，并确定：

1. **是否失败**: 判断实际结果是否与期望结果存在显著差异
2. **失败原因**: 分析导致失败的根本原因
3. **严重程度**: 评估失败的严重程度（low/medium/high）

## 输出格式
请按照以下JSON格式输出：

```json
{{
    "is_failure": true/false,
    "reason": "失败原因分析",
    "severity": "low/medium/high",
    "suggestions": ["改进建议1", "改进建议2"],
    "prevention_strategies": ["预防策略1", "预防策略2"]
}}
```

请确保分析准确、深入，并提供有价值的改进建议。
"""
        
        return prompt
    
    def _parse_failure_analysis(self, llm_response: str) -> Dict[str, Any]:
        """解析失败分析结果"""
        try:
            # 尝试从响应中提取JSON
            import re
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', llm_response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
                return json.loads(json_str)
            else:
                # 如果没有找到JSON，使用简单解析
                return self._simple_parse_failure_analysis(llm_response)
        except Exception as e:
            self.logger.error(f"解析失败分析结果失败: {e}")
            return self._simple_parse_failure_analysis(llm_response)
    
    def _simple_parse_failure_analysis(self, response: str) -> Dict[str, Any]:
        """简单解析失败分析结果"""
        # 基于关键词的简单分析
        if "失败" in response or "错误" in response or "不正确" in response:
            return {
                'is_failure': True,
                'reason': response[:200],
                'severity': 'medium',
                'suggestions': ['检查输入参数', '优化处理逻辑'],
                'prevention_strategies': ['增加验证', '改进错误处理']
            }
        else:
            return {
                'is_failure': False,
                'reason': '结果符合预期',
                'severity': 'low',
                'suggestions': [],
                'prevention_strategies': []
            }
    
    def _simple_failure_analysis(
        self,
        action: str,
        expected_result: str,
        actual_result: str
    ) -> Dict[str, Any]:
        """简单失败分析（备用方案）"""
        # 简单的字符串比较
        if expected_result.lower() != actual_result.lower():
            return {
                'is_failure': True,
                'reason': f'期望结果与实际结果不匹配',
                'severity': 'medium',
                'suggestions': ['检查结果处理逻辑'],
                'prevention_strategies': ['增加结果验证']
            }
        else:
            return {
                'is_failure': False,
                'reason': '结果匹配',
                'severity': 'low',
                'suggestions': [],
                'prevention_strategies': []
            }
    
    async def _trigger_reflection(self, failure_event: FailureEvent):
        """触发反思流程"""
        try:
            self.logger.info(f"🔄 触发反思流程: {failure_event.id}")
            
            # 1. 生成元提示
            meta_prompt = await self._generate_meta_prompt(failure_event)
            if meta_prompt:
                self.meta_prompts[meta_prompt.id] = meta_prompt
                self.logger.info(f"📝 生成元提示: {meta_prompt.id}")
            
            # 2. 生成反思规则
            reflection_rule = await self._generate_reflection_rule(failure_event, meta_prompt)
            if reflection_rule:
                self.reflection_rules[reflection_rule.id] = reflection_rule
                self.logger.info(f"📋 生成反思规则: {reflection_rule.id}")
            
            # 3. 存储到持久化存储
            await self._store_reflection_data(failure_event, meta_prompt, reflection_rule)
            
            self.logger.info(f"✅ 反思流程完成: {failure_event.id}")
            
        except Exception as e:
            self.logger.error(f"反思流程失败: {e}")
    
    async def _generate_meta_prompt(self, failure_event: FailureEvent) -> Optional[MetaPrompt]:
        """生成元提示"""
        try:
            # 构建元提示生成提示词
            prompt = self._build_meta_prompt_generation_prompt(failure_event)
            
            # 调用LLM生成元提示
            response = await self.llm_client.generate_response(
                prompt=prompt,
                max_tokens=1500,
                temperature=0.5
            )
            
            if response and response.get('content'):
                # 解析生成的元提示
                meta_prompt_data = self._parse_meta_prompt_response(response['content'])
                
                meta_prompt = MetaPrompt(
                    id=str(uuid.uuid4()),
                    prompt_type="failure_analysis",
                    original_prompt=failure_event.action,
                    enhanced_prompt=meta_prompt_data['enhanced_prompt'],
                    context={
                        'failure_event_id': failure_event.id,
                        'action': failure_event.action,
                        'failure_reason': failure_event.failure_reason
                    },
                    effectiveness_score=0.5,  # 初始分数
                    created_at=datetime.now().isoformat(),
                    updated_at=datetime.now().isoformat()
                )
                
                return meta_prompt
                
        except Exception as e:
            self.logger.error(f"生成元提示失败: {e}")
            return None
    
    def _build_meta_prompt_generation_prompt(self, failure_event: FailureEvent) -> str:
        """构建元提示生成提示词"""
        prompt = f"""
你是一个专业的元提示生成专家，需要从失败事件中生成可复用的元提示。

## 失败事件信息
- **动作**: {failure_event.action}
- **期望结果**: {failure_event.expected_result}
- **实际结果**: {failure_event.actual_result}
- **失败原因**: {failure_event.failure_reason}
- **严重程度**: {failure_event.severity}
- **上下文**: {json.dumps(failure_event.context, ensure_ascii=False, indent=2)}

## 任务要求
基于以上失败事件，生成一个可复用的元提示，用于：
1. **预防类似失败**: 提供预防策略
2. **改进处理逻辑**: 优化执行流程
3. **增强错误处理**: 提高系统鲁棒性

## 输出格式
请按照以下JSON格式输出：

```json
{{
    "enhanced_prompt": "增强后的提示词内容",
    "prevention_strategies": ["预防策略1", "预防策略2"],
    "improvement_suggestions": ["改进建议1", "改进建议2"],
    "error_handling_enhancements": ["错误处理增强1", "错误处理增强2"]
}}
```

请确保生成的元提示具有通用性、可操作性和有效性。
"""
        
        return prompt
    
    def _parse_meta_prompt_response(self, llm_response: str) -> Dict[str, Any]:
        """解析元提示响应"""
        try:
            import re
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', llm_response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
                return json.loads(json_str)
            else:
                return {
                    'enhanced_prompt': llm_response,
                    'prevention_strategies': ['增加验证', '改进错误处理'],
                    'improvement_suggestions': ['优化逻辑', '增强鲁棒性'],
                    'error_handling_enhancements': ['添加异常处理', '增加重试机制']
                }
        except Exception as e:
            self.logger.error(f"解析元提示响应失败: {e}")
            return {
                'enhanced_prompt': llm_response,
                'prevention_strategies': [],
                'improvement_suggestions': [],
                'error_handling_enhancements': []
            }
    
    async def _generate_reflection_rule(
        self, 
        failure_event: FailureEvent, 
        meta_prompt: Optional[MetaPrompt]
    ) -> Optional[ReflectionRule]:
        """生成反思规则"""
        try:
            # 构建规则生成提示词
            prompt = self._build_rule_generation_prompt(failure_event, meta_prompt)
            
            # 调用LLM生成规则
            response = await self.llm_client.generate_response(
                prompt=prompt,
                max_tokens=2000,
                temperature=0.4
            )
            
            if response and response.get('content'):
                # 解析生成的规则
                rule_data = self._parse_rule_response(response['content'])
                
                reflection_rule = ReflectionRule(
                    id=str(uuid.uuid4()),
                    rule_name=rule_data['rule_name'],
                    rule_description=rule_data['rule_description'],
                    trigger_conditions=rule_data['trigger_conditions'],
                    prevention_strategy=rule_data['prevention_strategy'],
                    success_examples=rule_data['success_examples'],
                    failure_examples=[failure_event.action],
                    confidence_score=0.7,  # 初始置信度
                    usage_count=0,
                    created_at=datetime.now().isoformat(),
                    updated_at=datetime.now().isoformat(),
                    tags=['reflexion', 'auto_generated'],
                    metadata={
                        'failure_event_id': failure_event.id,
                        'meta_prompt_id': meta_prompt.id if meta_prompt else None,
                        'generation_method': 'llm_generated'
                    }
                )
                
                return reflection_rule
                
        except Exception as e:
            self.logger.error(f"生成反思规则失败: {e}")
            return None
    
    def _build_rule_generation_prompt(
        self, 
        failure_event: FailureEvent, 
        meta_prompt: Optional[MetaPrompt]
    ) -> str:
        """构建规则生成提示词"""
        prompt = f"""
你是一个专业的规则生成专家，需要从失败事件中提炼可复用的规则。

## 失败事件信息
- **动作**: {failure_event.action}
- **期望结果**: {failure_event.expected_result}
- **实际结果**: {failure_event.actual_result}
- **失败原因**: {failure_event.failure_reason}
- **严重程度**: {failure_event.severity}

## 元提示信息
{f"增强提示: {meta_prompt.enhanced_prompt}" if meta_prompt else "无元提示"}

## 任务要求
基于以上信息，生成一个可复用的反思规则，包括：

1. **规则名称**: 简洁明了的规则名称
2. **规则描述**: 详细的规则描述
3. **触发条件**: 什么情况下应用此规则
4. **预防策略**: 如何预防类似失败
5. **成功案例**: 规则应用的成功示例
6. **失败案例**: 规则应用的失败示例

## 输出格式
请按照以下JSON格式输出：

```json
{{
    "rule_name": "规则名称",
    "rule_description": "规则详细描述",
    "trigger_conditions": ["触发条件1", "触发条件2"],
    "prevention_strategy": "预防策略描述",
    "success_examples": ["成功案例1", "成功案例2"],
    "failure_examples": ["失败案例1", "失败案例2"]
}}
```

请确保规则具有通用性、可操作性和有效性。
"""
        
        return prompt
    
    def _parse_rule_response(self, llm_response: str) -> Dict[str, Any]:
        """解析规则响应"""
        try:
            import re
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', llm_response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
                return json.loads(json_str)
            else:
                return {
                    'rule_name': '通用失败预防规则',
                    'rule_description': '基于失败事件生成的预防规则',
                    'trigger_conditions': ['检测到失败'],
                    'prevention_strategy': '增加验证和错误处理',
                    'success_examples': ['成功案例'],
                    'failure_examples': ['失败案例']
                }
        except Exception as e:
            self.logger.error(f"解析规则响应失败: {e}")
            return {
                'rule_name': '默认规则',
                'rule_description': '默认规则描述',
                'trigger_conditions': ['默认条件'],
                'prevention_strategy': '默认策略',
                'success_examples': [],
                'failure_examples': []
            }
    
    async def _store_reflection_data(
        self,
        failure_event: FailureEvent,
        meta_prompt: Optional[MetaPrompt],
        reflection_rule: Optional[ReflectionRule]
    ):
        """存储反思数据"""
        try:
            # 存储失败事件
            note = Note(
                id=failure_event.id,
                user_id=failure_event.user_id,
                title=f"失败事件_{failure_event.action}",
                content=json.dumps(asdict(failure_event), ensure_ascii=False, indent=2),
                note_type="failure_event",
                tags=['reflexion', 'failure'],
                metadata={
                    'action': failure_event.action,
                    'severity': failure_event.severity,
                    'timestamp': failure_event.timestamp
                }
            )
            await self.storage_manager.save_note(note)
            
            # 存储元提示
            if meta_prompt:
                meta_note = Note(
                    id=meta_prompt.id,
                    user_id=failure_event.user_id,
                    title=f"元提示_{meta_prompt.prompt_type}",
                    content=meta_prompt.enhanced_prompt,
                    note_type="meta_prompt",
                    tags=['reflexion', 'meta_prompt'],
                    metadata={
                        'prompt_type': meta_prompt.prompt_type,
                        'effectiveness_score': meta_prompt.effectiveness_score,
                        'failure_event_id': failure_event.id
                    }
                )
                await self.storage_manager.save_note(meta_note)
            
            # 存储反思规则
            if reflection_rule:
                rule_note = Note(
                    id=reflection_rule.id,
                    user_id=failure_event.user_id,
                    title=f"反思规则_{reflection_rule.rule_name}",
                    content=reflection_rule.rule_description,
                    note_type="reflection_rule",
                    tags=['reflexion', 'rule'],
                    metadata={
                        'rule_name': reflection_rule.rule_name,
                        'confidence_score': reflection_rule.confidence_score,
                        'usage_count': reflection_rule.usage_count,
                        'failure_event_id': failure_event.id
                    }
                )
                await self.storage_manager.save_note(rule_note)
            
            self.logger.info("💾 反思数据已存储")
            
        except Exception as e:
            self.logger.error(f"存储反思数据失败: {e}")
    
    async def get_applicable_rules(
        self, 
        action: str, 
        context: Dict[str, Any]
    ) -> List[ReflectionRule]:
        """获取适用的反思规则"""
        try:
            applicable_rules = []
            
            for rule in self.reflection_rules.values():
                # 检查触发条件
                if self._check_rule_conditions(rule, action, context):
                    applicable_rules.append(rule)
            
            # 按置信度排序
            applicable_rules.sort(key=lambda x: x.confidence_score, reverse=True)
            
            self.logger.info(f"🔍 找到 {len(applicable_rules)} 个适用规则")
            return applicable_rules
            
        except Exception as e:
            self.logger.error(f"获取适用规则失败: {e}")
            return []
    
    def _check_rule_conditions(
        self, 
        rule: ReflectionRule, 
        action: str, 
        context: Dict[str, Any]
    ) -> bool:
        """检查规则条件"""
        try:
            for condition in rule.trigger_conditions:
                if condition.lower() in action.lower():
                    return True
                if condition.lower() in str(context).lower():
                    return True
            return False
        except Exception as e:
            self.logger.error(f"检查规则条件失败: {e}")
            return False
    
    async def get_reflection_summary(self, user_id: str) -> Dict[str, Any]:
        """获取反思摘要"""
        try:
            # 统计失败事件
            user_failures = [
                event for event in self.failure_events.values()
                if event.user_id == user_id
            ]
            
            # 统计反思规则
            user_rules = [
                rule for rule in self.reflection_rules.values()
                if rule.metadata.get('user_id') == user_id
            ]
            
            # 统计元提示
            user_meta_prompts = [
                prompt for prompt in self.meta_prompts.values()
                if prompt.context.get('failure_event_id') in [f.id for f in user_failures]
            ]
            
            summary = {
                "user_id": user_id,
                "total_failures": len(user_failures),
                "total_rules": len(user_rules),
                "total_meta_prompts": len(user_meta_prompts),
                "failure_severity_distribution": {},
                "rule_confidence_distribution": {},
                "recent_failures": [],
                "top_rules": [],
                "created_at": datetime.now().isoformat()
            }
            
            # 统计失败严重程度分布
            for failure in user_failures:
                severity = failure.severity
                summary["failure_severity_distribution"][severity] = \
                    summary["failure_severity_distribution"].get(severity, 0) + 1
            
            # 统计规则置信度分布
            for rule in user_rules:
                confidence_range = f"{int(rule.confidence_score * 10) * 10}%"
                summary["rule_confidence_distribution"][confidence_range] = \
                    summary["rule_confidence_distribution"].get(confidence_range, 0) + 1
            
            # 最近失败事件
            recent_failures = sorted(
                user_failures, 
                key=lambda x: x.timestamp, 
                reverse=True
            )[:5]
            summary["recent_failures"] = [
                {
                    "id": f.id,
                    "action": f.action,
                    "severity": f.severity,
                    "timestamp": f.timestamp
                }
                for f in recent_failures
            ]
            
            # 热门规则
            top_rules = sorted(
                user_rules,
                key=lambda x: (x.confidence_score, x.usage_count),
                reverse=True
            )[:5]
            summary["top_rules"] = [
                {
                    "id": r.id,
                    "name": r.rule_name,
                    "confidence": r.confidence_score,
                    "usage_count": r.usage_count
                }
                for r in top_rules
            ]
            
            return summary
            
        except Exception as e:
            self.logger.error(f"获取反思摘要失败: {e}")
            return {"error": str(e)}


# 全局反思机制实例
_global_reflexion = None

def get_reflexion_mechanism() -> ReflexionMechanism:
    """获取全局反思机制"""
    global _global_reflexion
    if _global_reflexion is None:
        _global_reflexion = ReflexionMechanism()
    return _global_reflexion


async def detect_failure(
    action: str,
    expected_result: str,
    actual_result: str,
    context: Dict[str, Any],
    user_id: str,
    session_id: str,
    agent_name: str
) -> Optional[FailureEvent]:
    """检测失败（便捷函数）"""
    mechanism = get_reflexion_mechanism()
    await mechanism.initialize()
    return await mechanism.detect_failure(
        action, expected_result, actual_result, context, user_id, session_id, agent_name
    )


def main():
    """主函数 - 用于测试和演示"""
    import sys
    
    # 设置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 创建反思机制
    mechanism = ReflexionMechanism()
    
    # 模拟失败检测测试
    logger.info("Reflexion反思机制测试完成")
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
