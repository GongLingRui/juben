"""
输出归档服务
统一写入：agent_output_storage / project_files / artifacts
"""
from typing import Any, Dict, Optional, Union
from datetime import datetime

from utils.artifact_manager import get_artifact_manager, ArtifactType, AgentSource


class OutputArchiveService:
    def __init__(self, logger, output_storage, project_manager, agent_id: str):
        self.logger = logger
        self.output_storage = output_storage
        self.project_manager = project_manager
        self.agent_id = agent_id

    def _map_output_tag_to_artifact_type(self, output_tag: str) -> ArtifactType:
        mapping = {
            "drama_planning": ArtifactType.OUTLINE,
            "drama_creation": ArtifactType.SCRIPT,
            "drama_evaluation": ArtifactType.EVALUATION,
            "novel_screening": ArtifactType.EVALUATION,
            "story_analysis": ArtifactType.ANALYSIS,
            "character_development": ArtifactType.CHARACTER,
            "plot_development": ArtifactType.PLOT_POINTS,
            "series_analysis": ArtifactType.ANALYSIS,
        }
        return mapping.get(output_tag, ArtifactType.OTHER)

    def _map_agent_source(self) -> AgentSource:
        try:
            return AgentSource(self.agent_id)
        except Exception:
            return AgentSource.OTHER

    async def save_all(
        self,
        output_content: Union[str, Dict[str, Any]],
        output_tag: str,
        user_id: str,
        session_id: str,
        metadata: Optional[Dict[str, Any]] = None,
        filename_hint: Optional[str] = None
    ) -> Dict[str, Any]:
        result = {"outputs": {}, "artifacts": None, "project_file": None}

        # 1) 旧输出存储
        storage_result = await self.output_storage.save_agent_output(
            agent_name=self.agent_id,
            output_content=output_content,
            output_tag=output_tag,
            user_id=user_id,
            session_id=session_id,
            file_type="json",
            metadata=metadata,
            auto_export=True
        )
        result["outputs"] = storage_result

        # 2) Project files（复用 BaseJubenAgent 逻辑时由调用方处理）

        # 3) Artifacts
        try:
            manager = get_artifact_manager()
            filename = filename_hint or f"{output_tag}_{self.agent_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            artifact = manager.save_artifact(
                content=output_content if isinstance(output_content, str) else str(output_content),
                filename=filename,
                file_type=self._map_output_tag_to_artifact_type(output_tag),
                agent_source=self._map_agent_source(),
                user_id=user_id,
                session_id=session_id,
                project_id=metadata.get("project_id") if metadata else "default_project",
                description=f"{output_tag} 输出",
                tags=metadata.get("tags") if metadata else [],
                metadata=metadata or {},
            )
            result["artifacts"] = artifact.to_dict() if artifact else None
        except Exception as e:
            self.logger.warning(f"⚠️ Artifact归档失败: {e}")

        return result
