"""
工作流版本控制系统

实现工作流的版本管理、分支、合并和回滚功能
"""
import json
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass, field, asdict
from enum import Enum
import hashlib
import asyncio

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.logger import JubenLogger
from utils.database_client import fetch_one, fetch_all, execute

logger = JubenLogger("workflow_version_control")


class WorkflowStatus(Enum):
    """工作流状态"""
    DRAFT = "draft"           # 草稿
    ACTIVE = "active"         # 活跃
    ARCHIVED = "archived"     # 已归档
    DEPRECATED = "deprecated" # 已弃用


class VersionStatus(Enum):
    """版本状态"""
    DRAFT = "draft"           # 草稿版本
    PUBLISHED = "published"   # 已发布
    STAGED = "staged"         # 预发布
    ROLLED_BACK = "rolled_back"  # 已回滚


@dataclass
class WorkflowStep:
    """工作流步骤"""
    step_id: str
    agent_name: str
    agent_config: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    condition: Optional[str] = None
    retry_config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowDefinition:
    """工作流定义"""
    name: str
    description: str
    steps: List[WorkflowStep] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    timeout: int = 300
    retry_policy: str = "exponential"

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "description": self.description,
            "steps": [
                {
                    "step_id": s.step_id,
                    "agent_name": s.agent_name,
                    "agent_config": s.agent_config,
                    "dependencies": s.dependencies,
                    "condition": s.condition,
                    "retry_config": s.retry_config
                }
                for s in self.steps
            ],
            "metadata": self.metadata,
            "timeout": self.timeout,
            "retry_policy": self.retry_policy
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkflowDefinition":
        """从字典创建"""
        steps = [
            WorkflowStep(
                step_id=s["step_id"],
                agent_name=s["agent_name"],
                agent_config=s.get("agent_config", {}),
                dependencies=s.get("dependencies", []),
                condition=s.get("condition"),
                retry_config=s.get("retry_config", {})
            )
            for s in data.get("steps", [])
        ]

        return cls(
            name=data["name"],
            description=data["description"],
            steps=steps,
            metadata=data.get("metadata", {}),
            timeout=data.get("timeout", 300),
            retry_policy=data.get("retry_policy", "exponential")
        )


@dataclass
class WorkflowVersion:
    """工作流版本"""
    version_id: str
    workflow_id: str
    version_number: str
    definition: WorkflowDefinition
    status: VersionStatus = VersionStatus.DRAFT
    created_at: float = field(default_factory=time.time)
    created_by: Optional[str] = None
    parent_version_id: Optional[str] = None
    commit_message: Optional[str] = None
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "version_id": self.version_id,
            "workflow_id": self.workflow_id,
            "version_number": self.version_number,
            "definition": self.definition.to_dict(),
            "status": self.status.value,
            "created_at": self.created_at,
            "created_at_iso": datetime.fromtimestamp(self.created_at).isoformat(),
            "created_by": self.created_by,
            "parent_version_id": self.parent_version_id,
            "commit_message": self.commit_message,
            "tags": self.tags
        }


@dataclass
class WorkflowBranch:
    """工作流分支"""
    branch_id: str
    workflow_id: str
    branch_name: str
    head_version_id: str
    created_at: float = field(default_factory=time.time)
    created_by: Optional[str] = None
    is_default: bool = False


class WorkflowVersionControl:
    """
    工作流版本控制系统

    功能：
    1. 创建工作流
    2. 版本管理
    3. 分支管理
    4. 版本比较
    5. 回滚
    6. 标签管理
    """

    def __init__(self):
        """初始化版本控制系统"""
        self._cache: Dict[str, WorkflowDefinition] = {}
        logger.info("✅ 工作流版本控制系统初始化完成")

    def _generate_id(self, prefix: str) -> str:
        """生成唯一ID"""
        timestamp = int(time.time() * 1000)
        random_part = hashlib.md5(f"{timestamp}{prefix}".encode()).hexdigest()[:8]
        return f"{prefix}_{timestamp}_{random_part}"

    def _generate_version_number(self, parent_version: Optional[str] = None) -> str:
        """生成版本号"""
        if parent_version:
            # 从父版本递增
            parts = parent_version.split(".")
            if len(parts) == 3:
                major, minor, patch = parts
                return f"{major}.{minor}.{int(patch) + 1}"

        return "1.0.0"

    async def create_workflow(
        self,
        name: str,
        description: str,
        created_by: Optional[str] = None
    ) -> str:
        """
        创建新工作流

        Args:
            name: 工作流名称
            description: 描述
            created_by: 创建者

        Returns:
            str: 工作流ID
        """
        workflow_id = self._generate_id("wf")

        # 创建初始版本
        version_id = self._generate_id("v")

        definition = WorkflowDefinition(
            name=name,
            description=description,
            steps=[],
            metadata={"created": True}
        )

        version = WorkflowVersion(
            version_id=version_id,
            workflow_id=workflow_id,
            version_number="1.0.0",
            definition=definition,
            status=VersionStatus.PUBLISHED,
            created_by=created_by,
            commit_message="Initial version"
        )

        # 创建主分支
        branch = WorkflowBranch(
            branch_id=self._generate_id("br"),
            workflow_id=workflow_id,
            branch_name="main",
            head_version_id=version_id,
            created_by=created_by,
            is_default=True
        )

        try:
            await execute(
                """
                INSERT INTO workflows (
                    workflow_id, name, description, status, created_by, created_at
                ) VALUES ($1, $2, $3, $4, $5, $6)
                """,
                workflow_id,
                name,
                description,
                WorkflowStatus.ACTIVE.value,
                created_by,
                datetime.utcnow().isoformat(),
            )

            await execute(
                """
                INSERT INTO workflow_versions (
                    version_id, workflow_id, version_number, definition, status, created_at,
                    created_by, parent_version_id, commit_message, tags
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                """,
                version.version_id,
                version.workflow_id,
                version.version_number,
                version.definition.to_dict(),
                version.status.value,
                datetime.fromtimestamp(version.created_at).isoformat(),
                version.created_by,
                version.parent_version_id,
                version.commit_message,
                version.tags,
            )

            await execute(
                """
                INSERT INTO workflow_branches (
                    branch_id, workflow_id, branch_name, head_version_id,
                    created_by, is_default, created_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                """,
                branch.branch_id,
                workflow_id,
                branch.branch_name,
                branch.head_version_id,
                branch.created_by,
                branch.is_default,
                datetime.fromtimestamp(branch.created_at).isoformat(),
            )

            logger.info(f"✅ 创建工作流: {workflow_id}")
            return workflow_id

        except Exception as e:
            logger.error(f"❌ 创建工作流失败: {e}")
            raise

    async def save_version(
        self,
        workflow_id: str,
        definition: WorkflowDefinition,
        branch_name: str = "main",
        commit_message: Optional[str] = None,
        created_by: Optional[str] = None
    ) -> str:
        """
        保存新版本

        Args:
            workflow_id: 工作流ID
            definition: 工作流定义
            branch_name: 分支名称
            commit_message: 提交消息
            created_by: 创建者

        Returns:
            str: 版本ID
        """
        try:
            # 获取分支
            branch_data = await fetch_one(
                """
                SELECT branch_id, head_version_id
                FROM workflow_branches
                WHERE workflow_id = $1 AND branch_name = $2
                """,
                workflow_id,
                branch_name,
            )

            if not branch_data:
                # 创建新分支
                branch_id = self._generate_id("br")
                parent_version_id = None
            else:
                branch_id = branch_data["branch_id"]
                parent_version_id = branch_data["head_version_id"]

            # 生成版本号和ID
            version_number = self._generate_version_number(parent_version_id)
            version_id = self._generate_id("v")

            # 创建版本
            version = WorkflowVersion(
                version_id=version_id,
                workflow_id=workflow_id,
                version_number=version_number,
                definition=definition,
                status=VersionStatus.DRAFT,
                created_by=created_by,
                parent_version_id=parent_version_id,
                commit_message=commit_message
            )

            # 保存版本
            await execute(
                """
                INSERT INTO workflow_versions (
                    version_id, workflow_id, version_number, definition, status, created_at,
                    created_by, parent_version_id, commit_message, tags
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                """,
                version.version_id,
                version.workflow_id,
                version.version_number,
                version.definition.to_dict(),
                version.status.value,
                datetime.fromtimestamp(version.created_at).isoformat(),
                version.created_by,
                version.parent_version_id,
                version.commit_message,
                version.tags,
            )

            # 更新分支
            await execute(
                """
                UPDATE workflow_branches
                SET head_version_id = $1
                WHERE branch_id = $2
                """,
                version_id,
                branch_id,
            )

            # 缓存更新
            self._cache[workflow_id] = definition

            logger.info(f"✅ 保存版本: {workflow_id} v{version_number}")
            return version_id

        except Exception as e:
            logger.error(f"❌ 保存版本失败: {e}")
            raise

    async def get_version(
        self,
        workflow_id: str,
        version_number: Optional[str] = None,
        branch_name: Optional[str] = None
    ) -> Optional[WorkflowVersion]:
        """
        获取工作流版本

        Args:
            workflow_id: 工作流ID
            version_number: 版本号
            branch_name: 分支名称

        Returns:
            WorkflowVersion: 版本信息
        """
        try:
            data = None
            if version_number:
                data = await fetch_one(
                    """
                    SELECT * FROM workflow_versions
                    WHERE workflow_id = $1 AND version_number = $2
                    """,
                    workflow_id,
                    version_number,
                )
            elif branch_name:
                branch = await fetch_one(
                    """
                    SELECT head_version_id FROM workflow_branches
                    WHERE workflow_id = $1 AND branch_name = $2
                    """,
                    workflow_id,
                    branch_name,
                )
                if not branch:
                    return None
                data = await fetch_one(
                    """
                    SELECT * FROM workflow_versions
                    WHERE version_id = $1
                    """,
                    branch["head_version_id"],
                )
            else:
                data = await fetch_one(
                    """
                    SELECT * FROM workflow_versions
                    WHERE workflow_id = $1
                    ORDER BY created_at DESC
                    LIMIT 1
                    """,
                    workflow_id,
                )

            if not data:
                return None

            # 构建版本对象
            definition = WorkflowDefinition.from_dict(
                json.loads(data["definition"]) if isinstance(data["definition"], str) else data["definition"]
            )

            return WorkflowVersion(
                version_id=data["version_id"],
                workflow_id=data["workflow_id"],
                version_number=data["version_number"],
                definition=definition,
                status=VersionStatus(data["status"]),
                created_at=datetime.fromisoformat(str(data["created_at"])).timestamp(),
                created_by=data.get("created_by"),
                parent_version_id=data.get("parent_version_id"),
                commit_message=data.get("commit_message"),
                tags=json.loads(data.get("tags") or "[]") if isinstance(data.get("tags"), str) else data.get("tags", [])
            )

        except Exception as e:
            logger.error(f"❌ 获取版本失败: {e}")
            return None

    async def compare_versions(
        self,
        workflow_id: str,
        version1: str,
        version2: str
    ) -> Dict[str, Any]:
        """
        比较两个版本

        Args:
            workflow_id: 工作流ID
            version1: 版本1
            version2: 版本2

        Returns:
            Dict: 比较结果
        """
        v1 = await self.get_version(workflow_id, version1)
        v2 = await self.get_version(workflow_id, version2)

        if not v1 or not v2:
            return {"error": "版本不存在"}

        # 比较步骤
        steps1 = {s.step_id: s for s in v1.definition.steps}
        steps2 = {s.step_id: s for s in v2.definition.steps}

        added = set(steps2.keys()) - set(steps1.keys())
        removed = set(steps1.keys()) - set(steps2.keys())
        modified = set()

        for step_id in set(steps1.keys()) & set(steps2.keys()):
            s1 = steps1[step_id]
            s2 = steps2[step_id]
            if (
                s1.agent_name != s2.agent_name or
                s1.agent_config != s2.agent_config or
                s1.dependencies != s2.dependencies
            ):
                modified.add(step_id)

        return {
            "workflow_id": workflow_id,
            "version1": version1,
            "version2": version2,
            "added_steps": list(added),
            "removed_steps": list(removed),
            "modified_steps": list(modified),
            "metadata_changes": {
                "name_changed": v1.definition.name != v2.definition.name,
                "description_changed": v1.definition.description != v2.definition.description,
                "timeout_changed": v1.definition.timeout != v2.definition.timeout
            }
        }

    async def create_branch(
        self,
        workflow_id: str,
        branch_name: str,
        from_version: str,
        created_by: Optional[str] = None
    ) -> str:
        """
        创建分支

        Args:
            workflow_id: 工作流ID
            branch_name: 分支名称
            from_version: 基于哪个版本
            created_by: 创建者

        Returns:
            str: 分支ID
        """
        try:
            branch_id = self._generate_id("br")

            await execute(
                """
                INSERT INTO workflow_branches (
                    branch_id, workflow_id, branch_name, head_version_id,
                    created_by, is_default, created_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                """,
                branch_id,
                workflow_id,
                branch_name,
                from_version,
                created_by,
                False,
                datetime.utcnow().isoformat(),
            )

            logger.info(f"✅ 创建分支: {branch_name}")
            return branch_id

        except Exception as e:
            logger.error(f"❌ 创建分支失败: {e}")
            raise

    async def merge_branch(
        self,
        workflow_id: str,
        source_branch: str,
        target_branch: str = "main",
        created_by: Optional[str] = None
    ) -> str:
        """
        合并分支

        Args:
            workflow_id: 工作流ID
            source_branch: 源分支
            target_branch: 目标分支
            created_by: 创建者

        Returns:
            str: 新版本ID
        """
        try:
            # 获取源分支的最新版本
            source_version = await self.get_version(workflow_id, branch_name=source_branch)
            if not source_version:
                raise ValueError(f"源分支 {source_branch} 不存在")

            # 创建合并后的新版本
            version_id = await self.save_version(
                workflow_id=workflow_id,
                definition=source_version.definition,
                branch_name=target_branch,
                commit_message=f"Merged {source_branch} into {target_branch}",
                created_by=created_by
            )

            logger.info(f"✅ 合并分支: {source_branch} -> {target_branch}")
            return version_id

        except Exception as e:
            logger.error(f"❌ 合并分支失败: {e}")
            raise

    async def rollback(
        self,
        workflow_id: str,
        to_version: str,
        created_by: Optional[str] = None
    ) -> str:
        """
        回滚到指定版本

        Args:
            workflow_id: 工作流ID
            to_version: 目标版本
            created_by: 操作者

        Returns:
            str: 新版本ID
        """
        try:
            # 获取目标版本
            target_version = await self.get_version(workflow_id, to_version)
            if not target_version:
                raise ValueError(f"版本 {to_version} 不存在")

            # 创建回滚版本
            version_id = await self.save_version(
                workflow_id=workflow_id,
                definition=target_version.definition,
                commit_message=f"Rollback to version {to_version}",
                created_by=created_by
            )

            logger.info(f"✅ 回滚到版本: {to_version}")
            return version_id

        except Exception as e:
            logger.error(f"❌ 回滚失败: {e}")
            raise

    async def add_tag(
        self,
        workflow_id: str,
        version_number: str,
        tag: str
    ) -> bool:
        """
        为版本添加标签

        Args:
            workflow_id: 工作流ID
            version_number: 版本号
            tag: 标签

        Returns:
            bool: 是否成功
        """
        try:
            row = await fetch_one(
                """
                SELECT tags FROM workflow_versions
                WHERE workflow_id = $1 AND version_number = $2
                """,
                workflow_id,
                version_number,
            )
            if not row:
                return False

            current_tags = row.get("tags", [])
            if isinstance(current_tags, str):
                current_tags = json.loads(current_tags or "[]")
            if tag not in current_tags:
                current_tags.append(tag)
            await execute(
                """
                UPDATE workflow_versions
                SET tags = $1
                WHERE workflow_id = $2 AND version_number = $3
                """,
                current_tags,
                workflow_id,
                version_number,
            )

            logger.info(f"✅ 添加标签: {version_number} -> {tag}")
            return True

        except Exception as e:
            logger.error(f"❌ 添加标签失败: {e}")
            return False

    async def list_versions(
        self,
        workflow_id: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        列出版本历史

        Args:
            workflow_id: 工作流ID
            limit: 返回数量限制

        Returns:
            List[Dict]: 版本列表
        """
        try:
            rows = await fetch_all(
                """
                SELECT * FROM workflow_versions
                WHERE workflow_id = $1
                ORDER BY created_at DESC
                LIMIT $2
                """,
                workflow_id,
                limit,
            )
            for row in rows:
                if isinstance(row.get("definition"), str):
                    row["definition"] = json.loads(row["definition"])
                if isinstance(row.get("tags"), str):
                    row["tags"] = json.loads(row["tags"])
            return rows

        except Exception as e:
            logger.error(f"❌ 列出版本失败: {e}")
            return []

    async def list_branches(
        self,
        workflow_id: str
    ) -> List[Dict[str, Any]]:
        """
        列出分支

        Args:
            workflow_id: 工作流ID

        Returns:
            List[Dict]: 分支列表
        """
        try:
            return await fetch_all(
                """
                SELECT * FROM workflow_branches
                WHERE workflow_id = $1
                """,
                workflow_id,
            )

        except Exception as e:
            logger.error(f"❌ 列出分支失败: {e}")
            return []


# 全局实例
_global_workflow_vcs: Optional[WorkflowVersionControl] = None


def get_workflow_vcs() -> WorkflowVersionControl:
    """获取全局工作流版本控制实例"""
    global _global_workflow_vcs

    if _global_workflow_vcs is None:
        _global_workflow_vcs = WorkflowVersionControl()

    return _global_workflow_vcs


if __name__ == "__main__":
    # 测试代码
    async def test_workflow_vcs():
        """测试工作流版本控制"""
        vcs = WorkflowVersionControl()

        # 创建工作流
        workflow_id = await vcs.create_workflow(
            name="test_workflow",
            description="测试工作流",
            created_by="test_user"
        )

        logger.info(f"✅ 创建工作流: {workflow_id}")

        # 保存版本
        definition = WorkflowDefinition(
            name="test_workflow",
            description="测试工作流",
            steps=[
                WorkflowStep(
                    step_id="step1",
                    agent_name="test_agent",
                    agent_config={"param": "value"}
                )
            ]
        )

        version_id = await vcs.save_version(
            workflow_id=workflow_id,
            definition=definition,
            commit_message="Add test step",
            created_by="test_user"
        )

        logger.info(f"✅ 保存版本: {version_id}")

        # 列出版本
        versions = await vcs.list_versions(workflow_id)
        logger.info(f"✅ 版本历史: {len(versions)} 个版本")

    asyncio.run(test_workflow_vcs())
