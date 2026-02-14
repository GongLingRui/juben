"""
逻辑一致性检测 API 路由
Logic Consistency Detection API Routes

提供剧本逻辑一致性检测的 RESTful API 接口
"""

from fastapi import APIRouter, HTTPException, Depends, status, BackgroundTasks
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field

from agents.logic_consistency_agent import LogicConsistencyAgent
from utils.agent_dispatch import build_agent_generator


router = APIRouter(prefix="/logic-consistency", tags=["逻辑一致性检测"])


# ============ 请求/响应模型 ============


class ConsistencyCheckRequest(BaseModel):
    """一致性检测请求"""
    story_id: str = Field(..., description="故事ID")
    scan_depth: str = Field(default="all", description="扫描深度: all, recent, chapter_N")
    check_rules: Optional[List[str]] = Field(
        default=None,
        description="要检查的规则列表（可选，默认全部）"
    )
    auto_rollback: bool = Field(
        default=False,
        description="如果检测未通过，是否自动回滚"
    )


class ConsistencyCheckResponse(BaseModel):
    """一致性检测响应"""
    success: bool
    story_id: str
    scan_time: str
    overall_score: float
    passed: bool
    issue_count: int
    critical_issues: int
    high_issues: int
    medium_issues: int
    low_issues: int
    rollback_required: bool
    report_text: Optional[str] = None


class RuleInfo(BaseModel):
    """审计规则信息"""
    rule_id: str
    name: str
    description: str
    category: str
    enabled: bool


# ============ 辅助函数 ============


async def get_logic_agent() -> LogicConsistencyAgent:
    """获取逻辑一致性检测 Agent 实例"""
    try:
        agent = LogicConsistencyAgent()
        return agent
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Agent 初始化失败: {str(e)}",
        )


# ============ API 端点 ============


@router.post("/check", response_model=ConsistencyCheckResponse)
async def check_consistency(
    request: ConsistencyCheckRequest,
    background_tasks: BackgroundTasks,
    agent: LogicConsistencyAgent = Depends(get_logic_agent),
):
    """
    执行逻辑一致性检测

    检测规则：
    - **spatiotemporal**: 时空冲突（同一时间同一角色不能在两个地点）
    - **character_status**: 生命状态（已死亡角色不能有后续行动）
    - **motivation**: 动机缺失（重大事件需要动机支持）
    - **relationship**: 关系一致性（社交关系变化需要合理过渡）
    - **knowledge**: 知识连续性（角色能力/记忆保持一致）
    - **world_rule**: 世界观冲突（情节不能违反世界观规则）
    - **plot_coherence**: 情节连贯性（相邻情节应有因果关系）

    - **story_id**: 故事ID
    - **scan_depth**: 扫描深度（all/recent/chapter_N）
    - **check_rules**: 要检查的规则列表
    - **auto_rollback**: 是否自动回滚（如果未通过）

    返回检测结果和建议
    """
    try:
        request_data = {
            "story_id": request.story_id,
            "scan_depth": request.scan_depth,
            "check_rules": request.check_rules or [],
        }

        # 收集检测结果
        result = None
        issues = []

        async for event in build_agent_generator(agent, request_data, None):
            if event.get("event_type") == "tool_complete":
                result = event["data"]["result"]
                issues = result["report"]["issues"]
            elif event.get("event_type") == "error":
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=event["data"].get("error", "检测失败"),
                )

        if not result:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="检测未能完成",
            )

        report = result["report"]

        # 统计问题
        critical_count = len([i for i in issues if i["severity"] == "critical"])
        high_count = len([i for i in issues if i["severity"] == "high"])
        medium_count = len([i for i in issues if i["severity"] == "medium"])
        low_count = len([i for i in issues if i["severity"] == "low"])

        # 如果需要自动回滚
        if request.auto_rollback and not result["passed"]:
            # 在后台任务中执行回滚
            background_tasks.add_task(
                execute_rollback,
                request.story_id,
                result["score"],
                report["recommendations"],
            )

        return ConsistencyCheckResponse(
            success=True,
            story_id=request.story_id,
            scan_time=report["scan_time"],
            overall_score=result["score"],
            passed=result["passed"],
            issue_count=len(issues),
            critical_issues=critical_count,
            high_issues=high_count,
            medium_issues=medium_count,
            low_issues=low_count,
            rollback_required=result["rollback_required"],
            report_text=result.get("report_text"),
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"一致性检测失败: {str(e)}",
        )


@router.get("/rules", response_model=List[RuleInfo])
async def get_audit_rules(
    agent: LogicConsistencyAgent = Depends(get_logic_agent),
):
    """
    获取所有可用的审计规则

    返回规则列表及其描述
    """
    try:
        agent_info = agent.get_agent_info()
        rules = agent_info.get("audit_rules", [])

        rule_descriptions = {
            "spatiotemporal": {
                "name": "时空冲突检测",
                "description": "检查同一时间点，同一角色是否出现在两个不同地点",
                "category": "spatiotemporal",
            },
            "character_status": {
                "name": "角色状态检测",
                "description": "检查已死亡角色是否有后续行动",
                "category": "character_status",
            },
            "motivation": {
                "name": "动机缺失检测",
                "description": "检查重大事件是否缺乏动机支撑",
                "category": "motivation",
            },
            "relationship": {
                "name": "关系一致性检测",
                "description": "检查社交关系变化是否有合理过渡",
                "category": "relationship",
            },
            "knowledge": {
                "name": "知识连续性检测",
                "description": "检查角色能力和记忆是否保持一致",
                "category": "knowledge",
            },
            "world_rule": {
                "name": "世界观冲突检测",
                "description": "检查情节是否违反世界观规则",
                "category": "world_rule",
            },
            "plot_coherence": {
                "name": "情节连贯性检测",
                "description": "检查相邻情节是否有因果关系",
                "category": "plot_coherence",
            },
        }

        rule_list = []
        for rule_id in rules:
            info = rule_descriptions.get(rule_id, {})
            rule_list.append(RuleInfo(
                rule_id=rule_id,
                name=info.get("name", rule_id),
                description=info.get("description", ""),
                category=info.get("category", ""),
                enabled=True,
            ))

        return rule_list

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取审计规则失败: {str(e)}",
        )


@router.get("/scoring", response_model=Dict[str, Any])
async def get_scoring_info(
    agent: LogicConsistencyAgent = Depends(get_logic_agent),
):
    """
    获取评分规则信息

    返回通过标准、严重程度扣分等配置
    """
    try:
        agent_info = agent.get_agent_info()
        scoring = agent_info.get("scoring", {})

        return {
            "passing_score": agent.passing_score,
            "critical_threshold": agent.critical_threshold,
            "rule_weights": agent.rule_weights,
            "severity_penalties": {
                "critical": 25.0,
                "high": 15.0,
                "medium": 8.0,
                "low": 3.0,
                "info": 0.0,
            },
            **scoring,
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取评分信息失败: {str(e)}",
        )


@router.post("/story/{story_id}/fix-issues")
async def fix_consistency_issues(
    story_id: str,
    issue_ids: List[str] = Body(..., embed=True),
    agent: LogicConsistencyAgent = Depends(get_logic_agent),
):
    """
    批量修复一致性问题（实验性功能）

    - **issue_ids**: 要修复的问题ID列表

    注意：此功能使用 LLM 生成修复建议，需要人工审核
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="自动修复功能尚未实现，请手动修复问题",
    )


# ============ 辅助函数 ============


async def execute_rollback(
    story_id: str,
    score: float,
    recommendations: List[str],
):
    """
    执行回滚操作

    Args:
        story_id: 故事ID
        score: 检测分数
        recommendations: 修复建议
    """
    try:
        from utils.storage_manager import StorageManager
        storage = StorageManager()

        # 获取最近的快照
        snapshot = await storage.get_latest_snapshot(story_id)

        if not snapshot:
            logger.warning(f"未找到故事 {story_id} 的快照，无法回滚")
            return

        # 恢复快照
        await storage.restore_snapshot(story_id, snapshot["snapshot_id"])

        logger.info(f"故事 {story_id} 已回滚到快照 {snapshot['snapshot_id']}")

    except Exception as e:
        logger.error(f"回滚失败: {e}")


# ============ FastAPI 导入 ============


from fastapi import Body


# ============ 示例和测试 ============


@router.get("/example/report")
async def get_example_report():
    """
    获取示例检测报告

    用于演示和测试
    """
    from agents.logic_consistency_agent import (
        ConsistencyReport,
        ConsistencyIssue,
        IssueSeverity,
        IssueCategory,
    )

    example_report = ConsistencyReport(
        story_id="example_story",
        scan_time=datetime.now(timezone.utc).isoformat(),
        overall_score=62.5,
        passed=False,
        issues=[
            ConsistencyIssue(
                issue_id="spatial_001_example",
                category=IssueCategory.SPATIOTEMPORAL,
                severity=IssueSeverity.CRITICAL,
                title="角色出现在两个不同地点",
                description="角色「林萧」在第 5 章同时出现在京城和白云山",
                location="第 5 章",
                affected_elements=["char_001", "plot_005", "plot_006"],
                suggested_fix="调整情节顺序，使角色有时间在不同地点间移动",
                confidence=0.95,
            ),
            ConsistencyIssue(
                issue_id="status_001_example",
                category=IssueCategory.CHARACTER_STATUS,
                severity=IssueSeverity.CRITICAL,
                title="已死亡角色有后续行动",
                description="角色「黑风」在第 8 章死亡，但在第 10 章仍有行动",
                location="第 8-10 章",
                affected_elements=["char_003", "plot_010"],
                suggested_fix="删除死亡后的行动，或修改为「假死」",
                confidence=1.0,
            ),
            ConsistencyIssue(
                issue_id="motivation_001_example",
                category=IssueCategory.MOTIVATION,
                severity=IssueSeverity.HIGH,
                title="重大情节缺乏动机支撑",
                description="情节「血战暗夜谷」重要性为 95，但缺乏角色动机",
                location="第 10 章",
                affected_elements=["plot_010"],
                suggested_fix="为相关角色添加复仇或保护动机",
                confidence=0.75,
            ),
        ],
        statistics={
            "spatial_checks": 1,
            "status_checks": 1,
            "motivation_checks": 1,
        },
        recommendations=[
            "发现 2 个严重逻辑冲突，必须优先修复",
            "部分重大情节缺乏动机支撑，建议补充角色动机",
        ],
    )

    return {
        "report": example_report.__dict__,
        "report_text": await _generate_example_readable_report(example_report),
    }


async def _generate_example_readable_report(report: ConsistencyReport) -> str:
    """生成示例报告文本"""
    lines = [
        "# 剧本逻辑一致性检测报告（示例）",
        "",
        f"**故事ID**: {report.story_id}",
        f"**检测时间**: {report.scan_time}",
        f"**总体分数**: {report.overall_score:.2f}",
        f"**检测结果**: {'✅ 通过' if report.passed else '❌ 未通过'}",
        "",
        "## 问题概览",
        "",
        f"- 总问题数: {len(report.issues)}",
        f"  - 严重: {len([i for i in report.issues if i.severity == IssueSeverity.CRITICAL])}",
        f"  - 高优先级: {len([i for i in report.issues if i.severity == IssueSeverity.HIGH])}",
        "",
        "## 严重问题",
        "",
    ]

    for idx, issue in enumerate(report.issues, 1):
        lines.append(f"### {idx}. {issue.title}")
        lines.append("")
        lines.append(f"**类别**: {issue.category.value}")
        lines.append(f"**位置**: {issue.location}")
        lines.append(f"**描述**: {issue.description}")
        if issue.suggested_fix:
            lines.append(f"**修复建议**: {issue.suggested_fix}")
        lines.append("")

    lines.extend([
        "## ❌ 检测未通过",
        "",
        f"总体分数 ({report.overall_score:.2f}) 低于通过标准 (80.00)",
        "",
        "### 建议:",
        "1. 优先修复严重和高优先级问题",
        "2. 修复后重新检测",
        "3. 可以使用「回滚」功能恢复到上一版本",
    ])

    return "\n".join(lines)
