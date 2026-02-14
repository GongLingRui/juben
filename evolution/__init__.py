"""
Evolution 模块
包含 Prompt 进化、版本控制和 A/B 测试功能
"""

from evolution.prompt_version_manager import (
    PromptVersion,
    PromptVersionStatus,
    PromptVersionManager,
    ABTestRouter,
    ABTestConfig,
    get_prompt_version_manager,
    get_ab_test_router
)

from evolution.optimizer import (
    EvolutionOptimizer,
    EvolutionTrigger,
    EvolutionResult,
    get_evolution_optimizer
)

__all__ = [
    'PromptVersion',
    'PromptVersionStatus',
    'PromptVersionManager',
    'ABTestRouter',
    'ABTestConfig',
    'EvolutionOptimizer',
    'EvolutionTrigger',
    'EvolutionResult',
    'get_prompt_version_manager',
    'get_ab_test_router',
    'get_evolution_optimizer'
]
