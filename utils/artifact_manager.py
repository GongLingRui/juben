"""
Artifact 文件管理器
统一管理所有 Agent 输出的文件和 artifacts

功能：
1. 记录所有 Agent 的输出文件
2. 支持文件元数据（Agent、类型、时间、大小）
3. 提供文件查询和过滤
4. 支持文件预览和下载

代码作者：Claude
创建时间：2026年2月7日
"""
import os
import json
import hashlib
import shutil
from typing import Dict, Any, List, Optional, Callable
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from enum import Enum
import logging

try:
    from utils.redis_client import get_redis_client
except ImportError:
    get_redis_client = None


class ArtifactType(Enum):
    """文件类型分类"""
    SCRIPT = "script"                    # 剧本文件
    OUTLINE = "outline"                  # 故事大纲
    CHARACTER = "character"              # 人物档案
    PLOT_POINTS = "plot_points"          # 情节点
    MIND_MAP = "mind_map"                # 思维导图
    OCR_RESULT = "ocr_result"            # OCR 识别结果
    EVALUATION = "evaluation"            # 评测报告
    ANALYSIS = "analysis"                # 分析报告
    MARKDOWN = "markdown"                # Markdown 文档
    JSON = "json"                        # JSON 数据
    IMAGE = "image"                      # 图片文件
    OTHER = "other"                      # 其他


class AgentSource(Enum):
    """Agent 来源"""
    SHORT_DRAMA_CREATOR = "short_drama_creator"
    SHORT_DRAMA_EVALUATION = "short_drama_evaluation"
    STORY_SUMMARY_GENERATOR = "story_summary_generator"
    CHARACTER_PROFILE_GENERATOR = "character_profile_generator"
    MAJOR_PLOT_POINTS = "major_plot_points"
    DETAILED_PLOT_POINTS = "detailed_plot_points"
    MIND_MAP = "mind_map"
    OUTPUT_FORMATTER = "output_formatter"
    OCR_AGENT = "ocr_agent"
    SCRIPT_EVALUATION = "script_evaluation"
    IP_EVALUATION = "ip_evaluation"
    WORKFLOW_ORCHESTRATOR = "workflow_orchestrator"
    OTHER = "other"


@dataclass
class ArtifactMetadata:
    """Artifact 元数据"""
    artifact_id: str                    # 唯一 ID
    filename: str                       # 文件名
    file_path: str                      # 完整文件路径
    file_type: ArtifactType             # 文件类型
    agent_source: AgentSource           # 来源 Agent
    user_id: str                        # 用户 ID
    session_id: str                     # 会话 ID
    project_id: str                     # 项目 ID
    file_size: int                      # 文件大小（字节）
    content_hash: str                   # 内容哈希
    created_at: str                     # 创建时间
    updated_at: str                     # 更新时间
    tags: List[str] = field(default_factory=list)        # 标签
    description: str = ""               # 描述
    parent_id: Optional[str] = None     # 父 artifact ID（用于关联）
    children_ids: List[str] = field(default_factory=list)  # 子 artifact IDs
    preview: Optional[str] = None       # 预览文本（前200字符）
    metadata: Dict[str, Any] = field(default_factory=dict)  # 额外元数据

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        d = asdict(self)
        d['file_type'] = self.file_type.value
        d['agent_source'] = self.agent_source.value
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ArtifactMetadata":
        """从字典创建"""
        return cls(
            artifact_id=data['artifact_id'],
            filename=data['filename'],
            file_path=data['file_path'],
            file_type=ArtifactType(data['file_type']),
            agent_source=AgentSource(data['agent_source']),
            user_id=data['user_id'],
            session_id=data['session_id'],
            project_id=data['project_id'],
            file_size=data['file_size'],
            content_hash=data['content_hash'],
            created_at=data['created_at'],
            updated_at=data['updated_at'],
            tags=data.get('tags', []),
            description=data.get('description', ''),
            parent_id=data.get('parent_id'),
            children_ids=data.get('children_ids', []),
            preview=data.get('preview'),
            metadata=data.get('metadata', {})
        )


class ArtifactFileManager:
    """
    Artifact 文件管理器

    负责：
    1. 保存 Agent 输出文件
    2. 记录文件元数据
    3. 提供文件查询接口
    4. 支持文件关联和层级结构
    """

    def __init__(self, base_dir: str = "artifacts"):
        """
        初始化文件管理器

        Args:
            base_dir: Artifact 存储基础目录
        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

        # 创建子目录
        self.scripts_dir = self.base_dir / "scripts"
        self.outlines_dir = self.base_dir / "outlines"
        self.characters_dir = self.base_dir / "characters"
        self.plot_points_dir = self.base_dir / "plot_points"
        self.mind_maps_dir = self.base_dir / "mind_maps"
        self.ocr_results_dir = self.base_dir / "ocr_results"
        self.evaluations_dir = self.base_dir / "evaluations"
        self.analyses_dir = self.base_dir / "analyses"
        self.workflows_dir = self.base_dir / "workflows"
        self.others_dir = self.base_dir / "others"

        for dir_path in [
            self.scripts_dir, self.outlines_dir, self.characters_dir,
            self.plot_points_dir, self.mind_maps_dir, self.ocr_results_dir,
            self.evaluations_dir, self.analyses_dir, self.workflows_dir, self.others_dir
        ]:
            dir_path.mkdir(parents=True, exist_ok=True)

        # 元数据存储
        self.metadata_file = self.base_dir / ".metadata.json"
        self.metadata: Dict[str, ArtifactMetadata] = {}
        self._load_metadata()

        self.logger = logging.getLogger(__name__)

    def _load_metadata(self):
        """加载元数据"""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for artifact_id, metadata in data.items():
                        self.metadata[artifact_id] = ArtifactMetadata.from_dict(metadata)
                self.logger.info(f"已加载 {len(self.metadata)} 个 artifact 元数据")
            except Exception as e:
                self.logger.error(f"加载元数据失败: {e}")
                self.metadata = {}

    def _save_metadata(self):
        """保存元数据"""
        try:
            data = {
                artifact_id: metadata.to_dict()
                for artifact_id, metadata in self.metadata.items()
            }
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"保存元数据失败: {e}")

    def _get_file_hash(self, content: bytes) -> str:
        """计算文件哈希"""
        return hashlib.sha256(content).hexdigest()

    def _generate_artifact_id(self) -> str:
        """生成 artifact ID"""
        return f"art_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{os.urandom(4).hex()}"

    def _get_directory_for_type(self, file_type: ArtifactType) -> Path:
        """根据类型获取存储目录"""
        type_dirs = {
            ArtifactType.SCRIPT: self.scripts_dir,
            ArtifactType.OUTLINE: self.outlines_dir,
            ArtifactType.CHARACTER: self.characters_dir,
            ArtifactType.PLOT_POINTS: self.plot_points_dir,
            ArtifactType.MIND_MAP: self.mind_maps_dir,
            ArtifactType.OCR_RESULT: self.ocr_results_dir,
            ArtifactType.EVALUATION: self.evaluations_dir,
            ArtifactType.ANALYSIS: self.analyses_dir,
            ArtifactType.OTHER: self.others_dir,
        }

        # 工作流相关文件特殊处理
        if file_type == ArtifactType.MARKDOWN:
            return self.workflows_dir
        if file_type == ArtifactType.JSON:
            return self.workflows_dir
        if file_type == ArtifactType.IMAGE:
            return self.mind_maps_dir

        return type_dirs.get(file_type, self.others_dir)

    def save_artifact(
        self,
        content: str | bytes,
        filename: str,
        file_type: ArtifactType,
        agent_source: AgentSource,
        user_id: str,
        session_id: str,
        project_id: str,
        description: str = "",
        tags: List[str] = None,
        parent_id: str = None,
        metadata: Dict[str, Any] = None
    ) -> ArtifactMetadata:
        """
        保存 Artifact

        Args:
            content: 文件内容
            filename: 文件名
            file_type: 文件类型
            agent_source: 来源 Agent
            user_id: 用户 ID
            session_id: 会话 ID
            project_id: 项目 ID
            description: 描述
            tags: 标签
            parent_id: 父 artifact ID
            metadata: 额外元数据

        Returns:
            ArtifactMetadata: Artifact 元数据
        """
        try:
            # 生成 artifact ID
            artifact_id = self._generate_artifact_id()

            # 获取存储目录
            target_dir = self._get_directory_for_type(file_type)

            # 确保文件名唯一
            base_filename = Path(filename).stem
            file_ext = Path(filename).suffix
            unique_filename = f"{artifact_id}_{base_filename}{file_ext}"
            file_path = target_dir / unique_filename

            # 保存文件
            if isinstance(content, str):
                content_bytes = content.encode('utf-8')
                preview = content[:200] if len(content) > 200 else content
            else:
                content_bytes = content
                preview = None

            with open(file_path, 'wb') as f:
                f.write(content_bytes)

            # 计算哈希
            content_hash = self._get_file_hash(content_bytes)

            # 创建元数据
            artifact_metadata = ArtifactMetadata(
                artifact_id=artifact_id,
                filename=unique_filename,
                file_path=str(file_path),
                file_type=file_type,
                agent_source=agent_source,
                user_id=user_id,
                session_id=session_id,
                project_id=project_id,
                file_size=len(content_bytes),
                content_hash=content_hash,
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat(),
                tags=tags or [],
                description=description,
                parent_id=parent_id,
                preview=preview,
                metadata=metadata or {}
            )

            # 保存元数据
            self.metadata[artifact_id] = artifact_metadata
            self._save_metadata()

            # 更新父级的子 ID 列表
            if parent_id and parent_id in self.metadata:
                self.metadata[parent_id].children_ids.append(artifact_id)
                self._save_metadata()

            self.logger.info(f"✅ Artifact 已保存: {artifact_id} ({filename})")

            return artifact_metadata

        except Exception as e:
            self.logger.error(f"保存 Artifact 失败: {e}")
            raise

    def get_artifact(self, artifact_id: str) -> Optional[ArtifactMetadata]:
        """
        获取 Artifact 元数据

        Args:
            artifact_id: Artifact ID

        Returns:
            ArtifactMetadata: Artifact 元数据，不存在返回 None
        """
        return self.metadata.get(artifact_id)

    def get_artifact_content(self, artifact_id: str) -> Optional[str]:
        """
        获取 Artifact 内容

        Args:
            artifact_id: Artifact ID

        Returns:
            str: 文件内容
        """
        artifact = self.get_artifact(artifact_id)
        if not artifact:
            return None

        try:
            with open(artifact.file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            self.logger.error(f"读取 Artifact 内容失败: {e}")
            return None

    def delete_artifact(self, artifact_id: str) -> bool:
        """
        删除 Artifact

        Args:
            artifact_id: Artifact ID

        Returns:
            bool: 是否成功
        """
        artifact = self.get_artifact(artifact_id)
        if not artifact:
            return False

        try:
            # 删除文件
            if os.path.exists(artifact.file_path):
                os.remove(artifact.file_path)

            # 删除元数据
            del self.metadata[artifact_id]
            self._save_metadata()

            # 从父级的子列表中移除
            if artifact.parent_id and artifact.parent_id in self.metadata:
                parent = self.metadata[artifact.parent_id]
                if artifact_id in parent.children_ids:
                    parent.children_ids.remove(artifact_id)
                self._save_metadata()

            self.logger.info(f"🗑️ Artifact 已删除: {artifact_id}")
            return True

        except Exception as e:
            self.logger.error(f"删除 Artifact 失败: {e}")
            return False

    def list_artifacts(
        self,
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
        agent_source: Optional[AgentSource] = None,
        file_type: Optional[ArtifactType] = None,
        tags: Optional[List[str]] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[ArtifactMetadata]:
        """
        列出 Artifacts

        Args:
            user_id: 用户 ID 过滤
            project_id: 项目 ID 过滤
            agent_source: Agent 来源过滤
            file_type: 文件类型过滤
            tags: 标签过滤
            limit: 返回数量限制
            offset: 偏移量

        Returns:
            List[ArtifactMetadata]: Artifact 元数据列表
        """
        artifacts = list(self.metadata.values())

        # 应用过滤条件
        if user_id:
            artifacts = [a for a in artifacts if a.user_id == user_id]
        if project_id:
            artifacts = [a for a in artifacts if a.project_id == project_id]
        if agent_source:
            artifacts = [a for a in artifacts if a.agent_source == agent_source]
        if file_type:
            artifacts = [a for a in artifacts if a.file_type == file_type]
        if tags:
            artifacts = [a for a in artifacts if any(tag in a.tags for tag in tags)]

        # 排序：按创建时间倒序
        artifacts.sort(key=lambda a: a.created_at, reverse=True)

        # 分页
        return artifacts[offset:offset + limit]

    def get_artifact_tree(
        self,
        project_id: str,
        root_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        获取 Artifact 树形结构

        Args:
            project_id: 项目 ID
            root_id: 根节点 ID（可选）

        Returns:
            List[Dict]: 树形结构
        """
        artifacts = self.list_artifacts(project_id=project_id, limit=10000)

        # 构建父子关系映射
        children_map: Dict[str, List[ArtifactMetadata]] = {}
        root_artifacts = []

        for artifact in artifacts:
            if artifact.parent_id is None:
                root_artifacts.append(artifact)
            else:
                if artifact.parent_id not in children_map:
                    children_map[artifact.parent_id] = []
                children_map[artifact.parent_id].append(artifact)

        # 递归构建树
        def build_tree(artifact: ArtifactMetadata) -> Dict[str, Any]:
            children = children_map.get(artifact.artifact_id, [])
            return {
                "artifact": artifact.to_dict(),
                "children": [build_tree(child) for child in children]
            }

        return [build_tree(root) for root in root_artifacts]

    def get_statistics(self) -> Dict[str, Any]:
        """
        获取文件统计信息

        Returns:
            Dict: 统计信息
        """
        artifacts = list(self.metadata.values())

        # 按类型统计
        type_counts = {}
        for artifact in artifacts:
            type_name = artifact.file_type.value
            type_counts[type_name] = type_counts.get(type_name, 0) + 1

        # 按 Agent 统计
        agent_counts = {}
        for artifact in artifacts:
            agent_name = artifact.agent_source.value
            agent_counts[agent_name] = agent_counts.get(agent_name, 0) + 1

        # 文件大小统计
        total_size = sum(a.file_size for a in artifacts)
        avg_size = total_size / len(artifacts) if artifacts else 0

        # 时间范围
        if artifacts:
            dates = [a.created_at for a in artifacts]
            date_objects = [datetime.fromisoformat(d) for d in dates]
            oldest = min(date_objects).isoformat()
            newest = max(date_objects).isoformat()
        else:
            oldest = None
            newest = None

        return {
            "total_artifacts": len(artifacts),
            "type_counts": type_counts,
            "agent_counts": agent_counts,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / 1024 / 1024, 2),
            "avg_size_bytes": round(avg_size, 2),
            "oldest_artifact": oldest,
            "newest_artifact": newest
        }

    def cleanup_old_artifacts(self, days: int = 30) -> int:
        """
        清理旧 Artifacts

        Args:
            days: 保留天数

        Returns:
            int: 删除数量
        """
        cutoff_date = datetime.now() - timedelta(days=days)
        deleted_count = 0

        artifacts_to_delete = [
            artifact_id for artifact_id, artifact in self.metadata.items()
            if datetime.fromisoformat(artifact.created_at) < cutoff_date
        ]

        for artifact_id in artifacts_to_delete:
            if self.delete_artifact(artifact_id):
                deleted_count += 1

        self.logger.info(f"🗑️ 清理了 {deleted_count} 个旧 Artifacts（超过 {days} 天）")

        return deleted_count


# ==================== 全局单例 ====================

_artifact_manager: Optional[ArtifactFileManager] = None


def get_artifact_manager() -> ArtifactFileManager:
    """获取 Artifact 文件管理器单例"""
    global _artifact_manager
    if _artifact_manager is None:
        _artifact_manager = ArtifactFileManager()
    return _artifact_manager


def register_agent_output(
    content: str | bytes,
    filename: str,
    file_type: ArtifactType,
    agent_source: AgentSource,
    user_id: str = "system",
    session_id: str = "default",
    project_id: str = "default",
    **kwargs
) -> str:
    """
    注册 Agent 输出（便捷函数）

    Args:
        content: 文件内容
        filename: 文件名
        file_type: 文件类型
        agent_source: Agent 来源
        user_id: 用户 ID
        session_id: 会话 ID
        project_id: 项目 ID
        **kwargs: 其他参数

    Returns:
        str: Artifact ID
    """
    manager = get_artifact_manager()
    metadata = manager.save_artifact(
        content=content,
        filename=filename,
        file_type=file_type,
        agent_source=agent_source,
        user_id=user_id,
        session_id=session_id,
        project_id=project_id,
        **kwargs
    )
    return metadata.artifact_id
