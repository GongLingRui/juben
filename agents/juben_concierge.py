"""
Juben Concierge - 竖屏短剧策划接待员
 的concierge设计，专门用于竖屏短剧策划的用户交互和需求理解

核心功能：
1. 用户需求理解和分析
2. 智能任务路由和委派
3. 上下文管理和对话维护
4. 多模态内容处理
5. 实时反馈和状态更新
"""
import asyncio
import json
import re
from typing import AsyncGenerator, Dict, Any, List, Optional, Union, Tuple
from datetime import datetime
import uuid

from .base_juben_agent import BaseJubenAgent
from .juben_orchestrator import JubenOrchestrator
from ..utils.logger import JubenLogger
from ..utils.intent_recognition import IntentRecognizer
from ..utils.url_extractor import URLExtractor
from ..utils.multimodal_processor import MultimodalProcessor


class AgentInitializationError(Exception):
    """Agent 初始化错误"""
    pass


class JubenConcierge(BaseJubenAgent):
    """
    竖屏短剧策划接待员
    
    核心职责：
    1. 🎯 需求理解：深度解析用户意图和创作需求
    2. 🔄 任务路由：智能判断并委派给合适的Agent
    3. 📝 上下文管理：维护对话历史和用户偏好
    4. 🎬 多模态处理：处理文件、图片等多媒体内容
    5. 🤝 用户体验：提供友好的交互和实时反馈
    """
    
    def __init__(self, model_provider: str = "zhipu"):
        """初始化接待员"""
        super().__init__("juben_concierge", model_provider)

        # 初始化组件 - 添加错误处理
        try:
            self.intent_recognizer = IntentRecognizer()
        except Exception as e:
            self.logger.warning(f"IntentRecognizer 初始化失败: {e}")
            self.intent_recognizer = None

        try:
            self.url_extractor = URLExtractor()
        except Exception as e:
            self.logger.warning(f"URLExtractor 初始化失败: {e}")
            self.url_extractor = None

        try:
            self.multimodal_processor = MultimodalProcessor()
        except Exception as e:
            self.logger.warning(f"MultimodalProcessor 初始化失败: {e}")
            self.multimodal_processor = None

        try:
            self.orchestrator = JubenOrchestrator(model_provider)
        except Exception as e:
            self.logger.error(f"JubenOrchestrator 初始化失败: {e}")
            raise AgentInitializationError(f"Failed to initialize orchestrator: {e}")

        # 对话状态管理 - 使用 LRU 缓存防止内存泄漏
        from collections import OrderedDict
        self.conversation_states = OrderedDict()  # 会话状态缓存
        self.user_preferences = OrderedDict()     # 用户偏好缓存
        self._max_conversation_states = 1000  # 最大会话状态数
        self._max_user_preferences = 5000      # 最大用户偏好数

        # 文件处理限制
        self._max_files_per_request = 20       # 单次请求最大文件数
        self._max_file_size = 100 * 1024 * 1024  # 单个文件最大 100MB

        # 任务路由配置
        self.task_routing_rules = {
            "story_analysis": ["分析", "评估", "ip", "故事分析", "剧本分析"],
            "story_creation": ["创作", "编写", "创作故事", "写故事", "故事创作"],
            "character_development": ["角色", "人物", "角色设定", "人物关系"],
            "plot_development": ["情节", "情节点", "结构", "情节设计"],
            "drama_evaluation": ["评估", "评价", "短剧评估", "剧本评估"],
            "series_analysis": ["剧集", "系列", "已播", "剧集分析"]
        }

        self.logger.info("🎭 Juben接待员初始化完成")
        self.logger.info(f"🔧 支持的任务类型: {list(self.task_routing_rules.keys())}")
        multimodal_enabled = self.multimodal_processor is not None and self.multimodal_processor.is_enabled()
        self.logger.info(f"📝 多模态处理: {'启用' if multimodal_enabled else '禁用'}")
    
    async def process_request(
        self, 
        request_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        处理用户请求
        
        Args:
            request_data: 请求数据
            context: 上下文信息
            
        Yields:
            Dict: 流式响应事件
        """
        user_id = request_data.get("user_id", "unknown")
        session_id = request_data.get("session_id", "unknown")
        query = request_data.get("query", "")
        file_ids = request_data.get("file_ids", [])
        
        # 初始化Token累加器
        await self.initialize_token_accumulator(user_id, session_id)
        
        try:
            self.logger.info(f"🎭 开始处理用户请求: {query[:100]}...")
            
            # 发送接待开始事件
            yield await self._emit_event(
                "concierge_start",
                f"开始分析用户需求: {query}",
                {"user_id": user_id, "session_id": session_id, "status": "analyzing"}
            )
            
            # 获取或创建会话状态
            conversation_state = await self._get_or_create_conversation_state(user_id, session_id)
            
            # 处理多模态内容
            multimodal_results = []
            if file_ids:
                yield await self._emit_event(
                    "multimodal_processing",
                    "正在处理上传的文件...",
                    {"file_count": len(file_ids), "status": "processing"}
                )
                
                multimodal_results = await self._process_multimodal_content(
                    file_ids, user_id, session_id, query
                )
                
                if multimodal_results:
                    yield await self._emit_event(
                        "multimodal_complete",
                        f"文件处理完成，共分析 {len(multimodal_results)} 个文件",
                        {"results": multimodal_results, "status": "completed"}
                    )
            
            # 意图识别和任务分析
            intent_analysis = await self._analyze_user_intent(query, conversation_state, multimodal_results)
            
            yield await self._emit_event(
                "intent_analysis",
                f"需求分析完成: {intent_analysis['intent_type']}",
                {"intent_analysis": intent_analysis, "status": "analyzed"}
            )
            
            # 根据意图决定处理方式
            if intent_analysis["requires_orchestrator"]:
                # 复杂任务，委派给编排器
                yield await self._emit_event(
                    "orchestrator_delegation",
                    "检测到复杂任务，正在委派给专业编排器...",
                    {"task_type": intent_analysis["task_type"], "status": "delegating"}
                )
                
                # 构建编排器请求
                orchestrator_request = {
                    "instruction": query,
                    "user_id": user_id,
                    "session_id": session_id,
                    "intent_analysis": intent_analysis,
                    "multimodal_results": multimodal_results,
                    "context": conversation_state
                }
                
                # 委派给编排器
                async for event in self.orchestrator.process_request(orchestrator_request):
                    yield event
                
            else:
                # 简单任务，直接处理
                response = await self._handle_simple_request(
                    query, intent_analysis, conversation_state, multimodal_results
                )
                
                yield await self._emit_event(
                    "concierge_response",
                    response,
                    {"response_type": "direct", "intent_type": intent_analysis["intent_type"]}
                )
            
            # 更新对话状态
            await self._update_conversation_state(
                user_id, session_id, query, intent_analysis, multimodal_results
            )
            
            # 保存对话记录到文件系统
            await self._save_conversation_record(
                user_id, session_id, query, intent_analysis, multimodal_results
            )
            
            self.logger.info(f"✅ 用户请求处理完成: {user_id}:{session_id}")
            
        except Exception as e:
            self.logger.error(f"❌ 处理用户请求失败: {e}")
            yield await self._emit_event(
                "concierge_error",
                f"处理请求时发生错误: {str(e)}",
                {"error_type": "concierge_failed", "error": str(e)}
            )
            raise
    
    def _manage_lru_cache(self, cache: OrderedDict, max_size: int) -> None:
        """管理 LRU 缓存大小"""
        while len(cache) > max_size:
            cache.popitem(last=False)  # 移除最旧的项

    async def _get_or_create_conversation_state(
        self,
        user_id: str,
        session_id: str
    ) -> Dict[str, Any]:
        """获取或创建会话状态（使用 LRU 缓存）"""
        state_key = f"{user_id}:{session_id}"

        if state_key not in self.conversation_states:
            # 检查缓存大小
            self._manage_lru_cache(self.conversation_states, self._max_conversation_states)

            # 创建新的会话状态
            self.conversation_states[state_key] = {
                "user_id": user_id,
                "session_id": session_id,
                "created_at": datetime.now().isoformat(),
                "conversation_history": [],
                "user_preferences": {},
                "context_data": {},
                "multimodal_context": []
            }

            self.logger.info(f"📝 创建新会话状态: {state_key}")
        else:
            # 移到末尾（最近使用）
            self.conversation_states.move_to_end(state_key)

        return self.conversation_states[state_key]
    
    async def _process_multimodal_content(
        self,
        file_ids: List[str],
        user_id: str,
        session_id: str,
        query: str
    ) -> List[Dict[str, Any]]:
        """处理多模态内容"""
        if self.multimodal_processor is None:
            self.logger.warning("⚠️ 多模态处理器未初始化")
            return []

        if not self.multimodal_processor.is_enabled():
            self.logger.warning("⚠️ 多模态处理器未启用")
            return []
        
        try:
            results = []
            for file_id in file_ids:
                self.logger.info(f"🎬 处理文件: {file_id}")
                
                # 调用多模态处理器
                result = await self.multimodal_processor.process_file(
                    file_id=file_id,
                    user_id=user_id,
                    session_id=session_id,
                    instruction=query
                )
                
                if result:
                    results.append(result)
                    self.logger.info(f"✅ 文件处理完成: {file_id}")
                else:
                    self.logger.warning(f"⚠️ 文件处理失败: {file_id}")
            
            return results
            
        except Exception as e:
            self.logger.error(f"❌ 多模态内容处理失败: {e}")
            return []
    
    # ==================== 新增核心功能方法 ====================
    
    async def should_use_multimodal_processing(self, user_id: str, session_id: str, instruction: str) -> bool:
        """检测是否需要多模态处理"""
        return await self.multimodal_processor.should_use_multimodal_processing(user_id, session_id, instruction)
    
    async def process_multimodal_files(
        self, 
        user_id: str, 
        session_id: str, 
        instruction: str
    ) -> List[Dict[str, Any]]:
        """
        🎯 Concierge 专用：处理多模态文件并生成分析结果
        
        这是整个 Juben 系统中唯一的多模态处理入口。
        会分析文件内容并将结果文本化，供后续 Agent 使用。
        
        Returns:
            List[Dict]: 文件分析结果列表，每个包含 file_ref, analysis_result, file_type 等
        """
        # 使用公共多模态处理器
        analysis_results = await self.multimodal_processor.process_multimodal_files(
            user_id, session_id, instruction, agent_name="concierge"
        )
        
        # 转换为 Concierge 期望的格式
        formatted_results = []
        for result in analysis_results:
            formatted_results.append({
                "file_ref": result.get("ref_name", ""),
                "file_name": result.get("file_info", {}).get("original_filename", ""),
                "file_type": result.get("file_type", "unknown"),
                "analysis_result": result.get("analysis", "").strip(),
                "file_info": result.get("file_info", {})
            })
        
        return formatted_results
    
    async def save_file_analysis_as_notes(
        self, 
        analysis_results: List[Dict[str, Any]], 
        user_id: str, 
        session_id: str
    ) -> List[str]:
        """
        将文件分析结果保存为 Notes
        
        Returns:
            List[str]: 保存成功的 note 名称列表
        """
        if not analysis_results:
            return []
        
        # 处理两种格式的结果：
        # 1. process_multimodal_files 返回的格式（有file_ref, analysis_result字段）
        # 2. _process_file_ids_directly 返回的格式（有ref_name, analysis字段）
        processor_results = []
        for result in analysis_results:
            # 统一字段名
            ref_name = result.get("file_ref") or result.get("ref_name", "")
            analysis = result.get("analysis_result") or result.get("analysis", "")
            file_info = result.get("file_info", {})
            file_type = result.get("file_type", "unknown")
            
            if ref_name and analysis:
                processor_results.append({
                    "ref_name": ref_name,
                    "analysis": analysis,
                    "file_info": file_info,
                    "file_type": file_type
                })
        
        # 保存为Notes
        saved_notes = []
        for result in processor_results:
            try:
                note_id = await self.create_note(
                    user_id=user_id,
                    session_id=session_id,
                    title=f"文件分析: {result['file_info'].get('original_filename', 'unknown')}",
                    content=result['analysis'],
                    note_type="file_analysis",
                    tags=["文件分析", result['file_type']]
                )
                if note_id:
                    saved_notes.append(note_id)
            except Exception as e:
                self.logger.error(f"❌ 保存文件分析Note失败: {e}")
        
        return saved_notes
    
    async def _process_file_ids_directly(
        self,
        user_id: str,
        session_id: str,
        file_ids: List[str],
        instruction: str
    ) -> List[Dict[str, Any]]:
        """
        🎯 直接处理文件ID列表，不走文本引用流程

        直接从数据库获取文件信息，调用多模态分析，返回结果
        """
        if not file_ids:
            return []

        if self.multimodal_processor is None or not self.multimodal_processor.is_enabled():
            self.logger.warning("⚠️ 多模态处理未启用，跳过文件处理")
            return []

        # 文件数量限制
        if len(file_ids) > self._max_files_per_request:
            self.logger.warning(f"⚠️ 文件数量超过限制: {len(file_ids)} > {self._max_files_per_request}")
            file_ids = file_ids[:self._max_files_per_request]

        try:
            self.logger.info(f"🎯 直接处理{len(file_ids)}个文件ID")

            # 从数据库获取文件信息
            file_infos = await self._get_file_infos_from_db(file_ids)
            if not file_infos:
                self.logger.warning("⚠️ 未找到文件信息")
                return []

            # 处理每个文件
            results = []
            for file_info in file_infos:
                try:
                    # 文件大小检查
                    file_size = file_info.get('size', 0)
                    if file_size > self._max_file_size:
                        self.logger.warning(f"⚠️ 文件过大: {file_info.get('filename', 'unknown')} ({file_size} bytes)")
                        continue

                    result = await self._process_single_file_directly(
                        file_info, user_id, session_id, instruction
                    )
                    if result:
                        results.append(result)
                except Exception as e:
                    self.logger.error(f"❌ 处理文件失败: {file_info.get('filename', 'unknown')}, {e}")
                    continue

            self.logger.info(f"✅ 直接文件处理完成: {len(results)}个文件")
            return results

        except Exception as e:
            self.logger.error(f"❌ 直接文件处理失败: {e}")
            return []
    
    async def _get_file_infos_from_db(self, file_ids: List[str]) -> List[Dict[str, Any]]:
        """从数据库获取文件信息"""
        try:
            # 这里应该从数据库获取文件信息
            # 暂时返回模拟数据
            file_infos = []
            for file_id in file_ids:
                file_infos.append({
                    "file_id": file_id,
                    "filename": f"file_{file_id}.txt",
                    "file_path": f"/tmp/file_{file_id}",
                    "file_type": "document"
                })
            return file_infos
        except Exception as e:
            self.logger.error(f"❌ 获取文件信息失败: {e}")
            return []
    
    async def _process_single_file_directly(
        self,
        file_info: Dict[str, Any],
        user_id: str,
        session_id: str,
        instruction: str
    ) -> Optional[Dict[str, Any]]:
        """处理单个文件"""
        try:
            file_id = file_info.get("file_id")
            filename = file_info.get("filename", "unknown")
            
            # 调用多模态处理器分析文件
            result = await self.multimodal_processor.process_file(
                file_id=file_id,
                user_id=user_id,
                session_id=session_id,
                instruction=instruction
            )
            
            if result:
                # 添加文件信息
                result["file_info"] = file_info
                result["file_id"] = file_id
                result["filename"] = filename
                
                self.logger.info(f"✅ 文件处理完成: {filename}")
                return result
            else:
                self.logger.warning(f"⚠️ 文件处理失败: {filename}")
                return None
                
        except Exception as e:
            self.logger.error(f"❌ 处理单个文件失败: {e}")
            return None
    
    async def extract_notes_from_conversation(
        self,
        user_id: str,
        session_id: str,
        conversation_history: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """从对话历史中提取Notes"""
        try:
            if not conversation_history:
                return []
            
            # 构建提取提示词
            extraction_prompt = f"""
            请从以下对话历史中提取有价值的信息，创建结构化的Notes：
            
            对话历史:
            {json.dumps(conversation_history[-10:], ensure_ascii=False, indent=2)}
            
            请提取以下类型的信息：
            1. 用户偏好和需求
            2. 重要的决策和选择
            3. 关键的业务信息
            4. 技术要求和限制
            5. 时间线和里程碑
            
            请以JSON格式返回提取的Notes列表。
            """
            
            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": extraction_prompt}
            ]
            
            # 调用LLM提取
            response = await self._call_llm(messages, user_id=user_id, session_id=session_id)
            
            # 解析响应
            try:
                extracted_notes = json.loads(response)
                if isinstance(extracted_notes, list):
                    # 保存提取的Notes
                    saved_notes = []
                    for note_data in extracted_notes:
                        note_id = await self.create_note(
                            user_id=user_id,
                            session_id=session_id,
                            title=note_data.get("title", "提取的Note"),
                            content=note_data.get("content", ""),
                            note_type=note_data.get("type", "extracted"),
                            tags=note_data.get("tags", [])
                        )
                        if note_id:
                            saved_notes.append(note_id)
                    
                    self.logger.info(f"✅ 从对话中提取了{len(saved_notes)}个Notes")
                    return saved_notes
            except json.JSONDecodeError:
                self.logger.warning("⚠️ 无法解析提取的Notes")
            
            return []
            
        except Exception as e:
            self.logger.error(f"❌ 从对话提取Notes失败: {e}")
            return []
    
    async def analyze_user_preferences(
        self,
        user_id: str,
        session_id: str,
        conversation_history: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """分析用户偏好"""
        try:
            if not conversation_history:
                return {}
            
            # 构建分析提示词
            analysis_prompt = f"""
            请分析以下用户对话历史，识别用户的偏好和特点：
            
            对话历史:
            {json.dumps(conversation_history[-20:], ensure_ascii=False, indent=2)}
            
            请分析并返回以下信息：
            1. 用户的工作风格偏好
            2. 沟通方式偏好
            3. 技术偏好
            4. 时间偏好
            5. 质量要求偏好
            
            请以JSON格式返回分析结果。
            """
            
            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": analysis_prompt}
            ]
            
            # 调用LLM分析
            response = await self._call_llm(messages, user_id=user_id, session_id=session_id)
            
            # 解析响应
            try:
                preferences = json.loads(response)
                if isinstance(preferences, dict):
                    # 保存用户偏好
                    await self._save_user_preferences(user_id, session_id, preferences)
                    self.logger.info(f"✅ 用户偏好分析完成")
                    return preferences
            except json.JSONDecodeError:
                self.logger.warning("⚠️ 无法解析用户偏好")
            
            return {}
            
        except Exception as e:
            self.logger.error(f"❌ 分析用户偏好失败: {e}")
            return {}
    
    async def _save_user_preferences(
        self,
        user_id: str,
        session_id: str,
        preferences: Dict[str, Any]
    ):
        """保存用户偏好"""
        try:
            # 更新内存中的用户偏好
            state_key = f"{user_id}:{session_id}"
            if state_key in self.conversation_states:
                self.conversation_states[state_key]["user_preferences"] = preferences
            
            # 保存到持久化存储
            await self.storage.save_user_preferences(user_id, session_id, preferences)
            
        except Exception as e:
            self.logger.error(f"❌ 保存用户偏好失败: {e}")
    
    async def get_user_preferences(
        self,
        user_id: str,
        session_id: str
    ) -> Dict[str, Any]:
        """获取用户偏好"""
        try:
            # 先从内存获取
            state_key = f"{user_id}:{session_id}"
            if state_key in self.conversation_states:
                return self.conversation_states[state_key].get("user_preferences", {})
            
            # 从持久化存储获取
            preferences = await self.storage.get_user_preferences(user_id, session_id)
            return preferences or {}
            
        except Exception as e:
            self.logger.error(f"❌ 获取用户偏好失败: {e}")
            return {}
    
    async def optimize_conversation_context(
        self,
        user_id: str,
        session_id: str,
        current_query: str
    ) -> str:
        """优化对话上下文"""
        try:
            # 获取对话历史
            conversation_history = await self.get_conversation_history(user_id, session_id, limit=10)
            
            # 获取用户偏好
            user_preferences = await self.get_user_preferences(user_id, session_id)
            
            # 获取相关Notes
            relevant_notes = await self.get_notes(
                user_id=user_id,
                session_id=session_id,
                limit=5
            )
            
            # 构建优化后的上下文
            optimized_context = f"""
## 当前查询
{current_query}

## 对话历史摘要
{json.dumps(conversation_history[-5:], ensure_ascii=False, indent=2)}

## 用户偏好
{json.dumps(user_preferences, ensure_ascii=False, indent=2)}

## 相关Notes
{json.dumps([note.get('title', '') for note in relevant_notes], ensure_ascii=False)}

## 上下文优化建议
基于以上信息，请为用户提供个性化的响应。
"""
            
            return optimized_context
            
        except Exception as e:
            self.logger.error(f"❌ 优化对话上下文失败: {e}")
            return f"## 当前查询\n{current_query}"
    
    async def handle_user_feedback(
        self,
        user_id: str,
        session_id: str,
        feedback: Dict[str, Any]
    ) -> Dict[str, Any]:
        """处理用户反馈"""
        try:
            feedback_type = feedback.get("type", "general")
            feedback_content = feedback.get("content", "")
            feedback_rating = feedback.get("rating", 0)
            
            # 记录反馈
            feedback_record = {
                "user_id": user_id,
                "session_id": session_id,
                "feedback_type": feedback_type,
                "feedback_content": feedback_content,
                "feedback_rating": feedback_rating,
                "timestamp": datetime.now().isoformat()
            }
            
            # 保存反馈
            await self.storage.save_feedback(feedback_record)
            
            # 根据反馈调整策略
            if feedback_rating < 3:
                # 负面反馈，需要改进
                await self._handle_negative_feedback(user_id, session_id, feedback)
            elif feedback_rating >= 4:
                # 正面反馈，可以强化相关行为
                await self._handle_positive_feedback(user_id, session_id, feedback)
            
            self.logger.info(f"✅ 用户反馈处理完成: 类型={feedback_type}, 评分={feedback_rating}")
            
            return {
                "status": "success",
                "message": "反馈已记录并处理",
                "feedback_id": feedback_record.get("id")
            }
            
        except Exception as e:
            self.logger.error(f"❌ 处理用户反馈失败: {e}")
            return {
                "status": "error",
                "message": f"处理反馈失败: {str(e)}"
            }
    
    async def _handle_negative_feedback(
        self,
        user_id: str,
        session_id: str,
        feedback: Dict[str, Any]
    ):
        """处理负面反馈"""
        try:
            # 分析负面反馈原因
            feedback_content = feedback.get("content", "")
            
            # 创建改进建议Note
            improvement_note = await self.create_note(
                user_id=user_id,
                session_id=session_id,
                title="用户反馈改进建议",
                content=f"负面反馈: {feedback_content}\n\n改进建议:\n1. 分析用户不满意的具体原因\n2. 调整响应策略\n3. 优化用户体验",
                note_type="improvement",
                tags=["反馈", "改进"]
            )
            
            # 更新用户偏好，避免类似问题
            current_preferences = await self.get_user_preferences(user_id, session_id)
            current_preferences["avoid_patterns"] = current_preferences.get("avoid_patterns", [])
            current_preferences["avoid_patterns"].append(feedback_content)
            
            await self._save_user_preferences(user_id, session_id, current_preferences)
            
        except Exception as e:
            self.logger.error(f"❌ 处理负面反馈失败: {e}")
    
    async def _handle_positive_feedback(
        self,
        user_id: str,
        session_id: str,
        feedback: Dict[str, Any]
    ):
        """处理正面反馈"""
        try:
            # 记录成功模式
            feedback_content = feedback.get("content", "")
            
            # 创建成功模式Note
            success_note = await self.create_note(
                user_id=user_id,
                session_id=session_id,
                title="成功模式记录",
                content=f"正面反馈: {feedback_content}\n\n成功要素:\n1. 用户满意的方法\n2. 有效的沟通方式\n3. 高质量的输出",
                note_type="success_pattern",
                tags=["反馈", "成功"]
            )
            
            # 更新用户偏好，强化成功模式
            current_preferences = await self.get_user_preferences(user_id, session_id)
            current_preferences["success_patterns"] = current_preferences.get("success_patterns", [])
            current_preferences["success_patterns"].append(feedback_content)
            
            await self._save_user_preferences(user_id, session_id, current_preferences)
            
        except Exception as e:
            self.logger.error(f"❌ 处理正面反馈失败: {e}")
    
    async def generate_conversation_summary(
        self,
        user_id: str,
        session_id: str
    ) -> str:
        """生成对话摘要"""
        try:
            # 获取对话历史
            conversation_history = await self.get_conversation_history(user_id, session_id, limit=20)
            
            if not conversation_history:
                return "暂无对话历史"
            
            # 构建摘要提示词
            summary_prompt = f"""
            请为以下对话历史生成一个简洁的摘要：
            
            对话历史:
            {json.dumps(conversation_history, ensure_ascii=False, indent=2)}
            
            请包含以下内容：
            1. 主要讨论话题
            2. 关键决策和结论
            3. 用户需求和偏好
            4. 待办事项和后续行动
            
            请用简洁的语言总结，不超过200字。
            """
            
            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": summary_prompt}
            ]
            
            # 调用LLM生成摘要
            summary = await self._call_llm(messages, user_id=user_id, session_id=session_id)
            
            # 保存摘要为Note
            await self.create_note(
                user_id=user_id,
                session_id=session_id,
                title=f"对话摘要 - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                content=summary,
                note_type="summary",
                tags=["摘要", "对话"]
            )
            
            self.logger.info(f"✅ 对话摘要生成完成")
            return summary
            
        except Exception as e:
            self.logger.error(f"❌ 生成对话摘要失败: {e}")
            return "摘要生成失败"
    
    async def get_conversation_insights(
        self,
        user_id: str,
        session_id: str
    ) -> Dict[str, Any]:
        """获取对话洞察"""
        try:
            # 获取对话历史
            conversation_history = await self.get_conversation_history(user_id, session_id, limit=50)
            
            # 获取用户偏好
            user_preferences = await self.get_user_preferences(user_id, session_id)
            
            # 获取相关Notes
            notes = await self.get_notes(user_id=user_id, session_id=session_id, limit=10)
            
            # 分析对话模式
            insights = {
                "total_conversations": len(conversation_history),
                "user_preferences": user_preferences,
                "notes_count": len(notes),
                "conversation_topics": self._extract_conversation_topics(conversation_history),
                "user_satisfaction": self._analyze_user_satisfaction(conversation_history),
                "recommendations": self._generate_recommendations(user_preferences, conversation_history)
            }
            
            return insights
            
        except Exception as e:
            self.logger.error(f"❌ 获取对话洞察失败: {e}")
            return {"error": str(e)}
    
    def _extract_conversation_topics(self, conversation_history: List[Dict[str, Any]]) -> List[str]:
        """提取对话话题"""
        topics = set()
        for conversation in conversation_history:
            query = conversation.get("user_query", "")
            intent = conversation.get("intent_analysis", {})
            task_type = intent.get("task_type", "")
            if task_type:
                topics.add(task_type)
        return list(topics)
    
    def _analyze_user_satisfaction(self, conversation_history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """分析用户满意度"""
        # 简单的满意度分析逻辑
        total_conversations = len(conversation_history)
        if total_conversations == 0:
            return {"score": 0, "level": "unknown"}
        
        # 基于对话长度和内容分析满意度
        avg_query_length = sum(len(conv.get("user_query", "")) for conv in conversation_history) / total_conversations
        
        if avg_query_length > 50:
            satisfaction_score = 0.8
            level = "high"
        elif avg_query_length > 20:
            satisfaction_score = 0.6
            level = "medium"
        else:
            satisfaction_score = 0.4
            level = "low"
        
        return {
            "score": satisfaction_score,
            "level": level,
            "avg_query_length": avg_query_length
        }
    
    def _generate_recommendations(
        self,
        user_preferences: Dict[str, Any],
        conversation_history: List[Dict[str, Any]]
    ) -> List[str]:
        """生成推荐建议"""
        recommendations = []
        
        # 基于用户偏好生成推荐
        if user_preferences.get("work_style") == "detailed":
            recommendations.append("提供更详细的分析报告")
        
        if user_preferences.get("communication_style") == "formal":
            recommendations.append("使用更正式的语言风格")
        
        # 基于对话历史生成推荐
        if len(conversation_history) > 10:
            recommendations.append("考虑创建工作流模板以提高效率")
        
        return recommendations
    
    async def _analyze_user_intent(
        self, 
        query: str, 
        conversation_state: Dict[str, Any],
        multimodal_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        分析用户意图
        
        Args:
            query: 用户查询
            conversation_state: 会话状态
            multimodal_results: 多模态处理结果
            
        Returns:
            Dict: 意图分析结果
        """
        try:
            # 构建分析提示词
            analysis_prompt = f"""
            请分析以下竖屏短剧策划相关的用户请求，判断用户的具体需求和意图：

            用户查询: {query}
            
            会话历史: {json.dumps(conversation_state.get('conversation_history', [])[-3:], ensure_ascii=False)}
            
            多模态内容: {len(multimodal_results)} 个文件已处理
            
            请分析并返回JSON格式的结果，包含以下字段：
            1. intent_type: 意图类型 (simple_query, complex_task, file_analysis, conversation_continue)
            2. task_type: 任务类型 (story_analysis, story_creation, character_development, plot_development, drama_evaluation, series_analysis)
            3. requires_orchestrator: 是否需要编排器处理 (true/false)
            4. confidence: 分析置信度 (0-1)
            5. key_requirements: 关键需求列表
            6. suggested_workflow: 建议的工作流类型
            """
            
            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": analysis_prompt}
            ]
            
            # 调用LLM分析
            response = await self._call_llm(messages, user_id="system", session_id="intent_analysis")
            
            # 解析响应
            try:
                intent_analysis = json.loads(response)
            except json.JSONDecodeError:
                # 如果解析失败，使用默认分析
                intent_analysis = self._fallback_intent_analysis(query)
            
            # 验证和补充分析结果
            intent_analysis = self._validate_intent_analysis(intent_analysis, query)
            
            self.logger.info(f"🎯 意图分析完成: {intent_analysis['intent_type']} -> {intent_analysis['task_type']}")
            
            return intent_analysis
            
        except Exception as e:
            self.logger.error(f"❌ 意图分析失败: {e}")
            return self._fallback_intent_analysis(query)
    
    def _fallback_intent_analysis(self, query: str) -> Dict[str, Any]:
        """回退意图分析"""
        query_lower = query.lower()
        
        # 基于关键词的简单分析
        for task_type, keywords in self.task_routing_rules.items():
            if any(keyword in query_lower for keyword in keywords):
                return {
                    "intent_type": "complex_task",
                    "task_type": task_type,
                    "requires_orchestrator": True,
                    "confidence": 0.7,
                    "key_requirements": [query],
                    "suggested_workflow": task_type
                }
        
        # 默认分析
        return {
            "intent_type": "simple_query",
            "task_type": "story_analysis",
            "requires_orchestrator": False,
            "confidence": 0.5,
            "key_requirements": [query],
            "suggested_workflow": "story_analysis"
        }
    
    def _validate_intent_analysis(self, analysis: Dict[str, Any], query: str) -> Dict[str, Any]:
        """验证和补充意图分析结果"""
        # 确保必要字段存在
        required_fields = ["intent_type", "task_type", "requires_orchestrator", "confidence"]
        for field in required_fields:
            if field not in analysis:
                if field == "intent_type":
                    analysis[field] = "simple_query"
                elif field == "task_type":
                    analysis[field] = "story_analysis"
                elif field == "requires_orchestrator":
                    analysis[field] = False
                elif field == "confidence":
                    analysis[field] = 0.5
        
        # 验证任务类型
        if analysis["task_type"] not in self.task_routing_rules:
            analysis["task_type"] = "story_analysis"
        
        # 补充缺失字段
        if "key_requirements" not in analysis:
            analysis["key_requirements"] = [query]
        
        if "suggested_workflow" not in analysis:
            analysis["suggested_workflow"] = analysis["task_type"]
        
        return analysis
    
    async def _handle_simple_request(
        self, 
        query: str, 
        intent_analysis: Dict[str, Any],
        conversation_state: Dict[str, Any],
        multimodal_results: List[Dict[str, Any]]
    ) -> str:
        """处理简单请求"""
        try:
            # 构建简单响应提示词
            response_prompt = f"""
            请基于以下信息，为用户提供专业的竖屏短剧策划建议：

            用户查询: {query}
            意图类型: {intent_analysis['intent_type']}
            任务类型: {intent_analysis['task_type']}
            
            多模态内容: {len(multimodal_results)} 个文件已分析
            
            请提供：
            1. 针对性的专业建议
            2. 具体的实施步骤
            3. 注意事项和最佳实践
            4. 如需进一步分析，请说明需要什么信息
            
            请以友好、专业的语调回答。
            """
            
            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": response_prompt}
            ]
            
            # 调用LLM生成响应
            response = await self._call_llm(messages, user_id="system", session_id="simple_response")
            
            return response
            
        except Exception as e:
            self.logger.error(f"❌ 简单请求处理失败: {e}")
            return f"抱歉，处理您的请求时遇到问题：{str(e)}。请稍后重试或提供更多详细信息。"
    
    async def _update_conversation_state(
        self, 
        user_id: str, 
        session_id: str, 
        query: str, 
        intent_analysis: Dict[str, Any],
        multimodal_results: List[Dict[str, Any]]
    ):
        """更新对话状态"""
        state_key = f"{user_id}:{session_id}"
        
        if state_key in self.conversation_states:
            state = self.conversation_states[state_key]
            
            # 添加对话历史
            state["conversation_history"].append({
                "timestamp": datetime.now().isoformat(),
                "user_query": query,
                "intent_analysis": intent_analysis,
                "multimodal_count": len(multimodal_results)
            })
            
            # 保持历史记录在合理范围内
            if len(state["conversation_history"]) > 20:
                state["conversation_history"] = state["conversation_history"][-20:]
            
            # 更新多模态上下文
            if multimodal_results:
                state["multimodal_context"].extend(multimodal_results)
            
            self.logger.info(f"📝 更新对话状态: {state_key}, 历史记录: {len(state['conversation_history'])}")
    
    async def _save_conversation_record(
        self, 
        user_id: str, 
        session_id: str, 
        query: str, 
        intent_analysis: Dict[str, Any],
        multimodal_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """保存对话记录到文件系统"""
        try:
            # 构建对话记录
            conversation_record = {
                "user_id": user_id,
                "session_id": session_id,
                "query": query,
                "intent_analysis": intent_analysis,
                "multimodal_results": multimodal_results,
                "timestamp": datetime.now().isoformat(),
                "agent_name": self.agent_name
            }
            
            # 保存到文件系统
            save_result = await self.auto_save_output(
                output_content=conversation_record,
                user_id=user_id,
                session_id=session_id,
                file_type="json",
                metadata={
                    "conversation_type": "user_interaction",
                    "intent_type": intent_analysis.get("intent_type", "unknown"),
                    "task_type": intent_analysis.get("task_type", "unknown"),
                    "multimodal_count": len(multimodal_results),
                    "concierge_version": "1.0"
                }
            )
            
            if save_result.get("success"):
                self.logger.info(f"💾 对话记录保存成功: {user_id}:{session_id}")
            else:
                self.logger.error(f"❌ 对话记录保存失败: {save_result.get('error')}")
            
            return save_result
            
        except Exception as e:
            self.logger.error(f"❌ 保存对话记录失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_conversation_history(
        self, 
        user_id: str, 
        session_id: str, 
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """获取对话历史"""
        state_key = f"{user_id}:{session_id}"
        
        if state_key in self.conversation_states:
            history = self.conversation_states[state_key]["conversation_history"]
            return history[-limit:] if limit > 0 else history
        
        return []
    
    async def clear_conversation_state(self, user_id: str, session_id: str) -> bool:
        """清除对话状态"""
        state_key = f"{user_id}:{session_id}"
        
        if state_key in self.conversation_states:
            del self.conversation_states[state_key]
            self.logger.info(f"🗑️ 清除对话状态: {state_key}")
            return True
        
        return False
    
    def get_agent_info(self) -> Dict[str, Any]:
        """获取Agent信息"""
        base_info = super().get_agent_info()
        base_info.update({
            "concierge_type": "juben_planning",
            "supported_task_types": list(self.task_routing_rules.keys()),
            "multimodal_enabled": self.multimodal_processor.is_enabled(),
            "active_conversations": len(self.conversation_states)
        })
        return base_info
