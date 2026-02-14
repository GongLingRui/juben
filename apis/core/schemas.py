"""
竖屏短剧策划助手 - 数据模型
 项目的优秀设计
"""
from typing import Dict, Any, List, Optional, Union
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum

# ==================== 基础响应模型 ====================

class BaseResponse(BaseModel):
    """基础响应模型"""
    success: bool = Field(description="请求是否成功")
    message: str = Field(description="响应消息")
    data: Optional[Any] = Field(default=None, description="响应数据")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat(), description="时间戳")

class ErrorResponse(BaseResponse):
    """错误响应模型"""
    success: bool = False
    error_code: Optional[str] = Field(default=None, description="错误代码")
    detail: Optional[str] = Field(default=None, description="错误详情")

# ==================== 聊天相关模型 ====================

class ChatRequest(BaseModel):
    """聊天请求模型"""
    input: str = Field(
        ...,
        description="用户输入",
        min_length=1,
        max_length=50000,
        json_schema_extra={"example": "请帮我创作一个现代都市爱情短剧"}
    )
    user_id: str = Field(
        default="default_user",
        description="用户ID",
        min_length=1,
        max_length=100,
        pattern=r"^[a-zA-Z0-9_-]+$"
    )
    session_id: Optional[str] = Field(
        default=None,
        description="会话ID",
        min_length=1,
        max_length=100
    )
    project_id: Optional[str] = Field(
        default=None,
        description="项目ID",
        min_length=1,
        max_length=100
    )
    model_provider: Optional[str] = Field(
        default=None,
        description="模型提供商 (zhipu, openrouter, openai, local, ollama)",
        json_schema_extra={"enum": ["zhipu", "openrouter", "openai", "local", "ollama"]}
    )
    model: Optional[str] = Field(
        default=None,
        description="模型名称",
        max_length=100
    )
    agent_id: Optional[str] = Field(
        default=None,
        description="Agent ID",
        max_length=100
    )
    history: List[Dict[str, str]] = Field(
        default_factory=list,
        description="历史对话",
        max_length=50
    )
    file_ids: List[str] = Field(
        default_factory=list,
        description="引用的文件ID列表"
    )
    file_refs: str = Field(
        default="auto",
        description="文件引用解析模式(auto/manual/off)"
    )
    auto_mode: bool = Field(
        default=True,
        description="是否自动模式"
    )
    user_selections: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="用户选择数据"
    )
    enable_web_search: bool = Field(default=True, description="是否启用网络搜索")
    enable_knowledge_base: bool = Field(default=True, description="是否启用知识库")
    count: Optional[int] = Field(
        default=5,
        description="搜索结果数量",
        ge=1,
        le=20
    )
    collection: Optional[str] = Field(
        default="script_segments",
        description="知识库集合",
        json_schema_extra={"enum": ["script_segments", "drama_highlights"]}
    )
    top_k: Optional[int] = Field(
        default=5,
        description="知识库检索数量",
        ge=1,
        le=20
    )
    temperature: Optional[float] = Field(
        default=None,
        description="温度参数",
        ge=0.0,
        le=2.0
    )
    max_tokens: Optional[int] = Field(
        default=None,
        description="最大token数",
        ge=1,
        le=32000
    )


class ChatResponse(BaseResponse):
    """聊天响应模型"""
    success: bool = True
    agent_name: str = Field(description="Agent名称")
    response: str = Field(description="AI响应内容")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")
    token_usage: Optional[Dict[str, Any]] = Field(default=None, description="Token使用情况")


class ResumeRequest(BaseModel):
    """断点续传请求模型"""
    message_id: str = Field(..., description="消息ID", min_length=1, max_length=100)
    session_id: str = Field(..., description="会话ID", min_length=1, max_length=100)
    user_id: str = Field(..., description="用户ID", min_length=1, max_length=100, pattern=r"^[a-zA-Z0-9_-]+$")
    from_sequence: int = Field(default=0, description="从哪个序列号开始恢复", ge=0)

# ==================== 流式事件模型 ====================

class EventType(str, Enum):
    """事件类型枚举"""
    MESSAGE = "message"           # 普通消息
    LLM_CHUNK = "llm_chunk"       # LLM内容片段
    THOUGHT = "thought"           # 思考过程
    TOOL_CALL = "tool_call"       # 工具调用开始
    TOOL_RETURN = "tool_return"   # 工具调用返回
    TOOL_PROCESSING = "tool_processing"  # 工具处理中
    ERROR = "error"               # 错误事件
    DONE = "done"                 # 完成信号
    BILLING = "billing"           # 计费信息
    PROGRESS = "progress"         # 进度更新
    SYSTEM = "system"             # 系统消息

class StreamContentType(str, Enum):
    """流式内容类型枚举（用于流式事件的内容分类）- juben剧本创作专用"""

    # ============ 基础类型 ============
    TEXT = "text"                    # 普通文本
    MARKDOWN = "markdown"            # Markdown格式内容
    JSON = "json"                    # JSON结构化数据

    # ============ 思考和分析类 ============
    THOUGHT = "thought"              # Agent的内心思考过程
    PLAN_STEP = "plan_step"          # 执行计划步骤
    INSIGHT = "insight"              # 洞察分析

    # ============ 人物相关 ============
    CHARACTER_PROFILE = "character_profile"       # 人物画像/小传
    CHARACTER_RELATIONSHIP = "character_relationship"  # 人物关系分析

    # ============ 故事结构相关 ============
    STORY_SUMMARY = "story_summary"              # 故事梗概/总结
    STORY_OUTLINE = "story_outline"              # 故事大纲
    STORY_TYPE = "story_type"                    # 故事类型分析
    FIVE_ELEMENTS = "five_elements"              # 故事五元素分析
    SERIES_INFO = "series_info"                  # 系列信息
    SERIES_ANALYSIS = "series_analysis"          # 系列分析

    # ============ 情节相关 ============
    MAJOR_PLOT = "major_plot"                    # 大情节点
    DETAILED_PLOT = "detailed_plot"              # 详细情节点
    DRAMA_ANALYSIS = "drama_analysis"            # 戏剧功能分析
    PLOT_ANALYSIS = "plot_analysis"              # 情节分析

    # ============ 创作相关 ============
    SCRIPT = "script"                            # 剧本内容
    DRAMA_PLAN = "drama_plan"                    # 剧本策划
    PROPOSAL = "proposal"                        # 内容提案

    # ============ 可视化 ============
    MIND_MAP = "mind_map"                        # 思维导图

    # ============ 评估相关 ============
    EVALUATION = "evaluation"                    # 综合评估结果
    SCRIPT_EVALUATION = "script_evaluation"      # 剧本评估
    STORY_EVALUATION = "story_evaluation"        # 故事评估
    OUTLINE_EVALUATION = "outline_evaluation"    # 大纲评估
    IP_EVALUATION = "ip_evaluation"              # IP评估
    NOVEL_SCREENING = "novel_screening"          # 小说筛选
    SCORE_ANALYSIS = "score_analysis"            # 评分分析

    # ============ 工具相关 ============
    SEARCH_RESULT = "search_result"              # 搜索结果（百度/网络）
    KNOWLEDGE_RESULT = "knowledge_result"        # 知识库检索结果
    REFERENCE_RESULT = "reference_result"        # 参考文献结果
    DOCUMENT = "document"                        # 文档生成
    FORMATTED_CONTENT = "formatted_content"      # 格式化输出

    # ============ 系统相关 ============
    SYSTEM_PROGRESS = "system_progress"          # 系统进度提示
    TOOL_RESULT = "tool_result"                  # 工具执行结果
    WORKFLOW_PROGRESS = "workflow_progress"      # 工作流进度
    RESULT_INTEGRATION = "result_integration"    # 结果整合
    TEXT_OPERATION = "text_operation"            # 文本操作（截断/分割）
    BATCH_PROGRESS = "batch_progress"            # 批处理进度

    # ============ 其他 ============
    FINAL_ANSWER = "final_answer"                # 最终整合答案
    ERROR = "error_content"                      # 错误内容

class StreamEvent(BaseModel):
    """🆕 增强版流式事件模型"""
    event_type: EventType = Field(description="事件类型")
    agent_source: Optional[str] = Field(default=None, description="Agent来源（如'ShortDramaPlannerAgent'）")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat(), description="时间戳")

    # 🆕 使用payload结构（与graph项目一致）
    payload: Dict[str, Any] = Field(default_factory=dict, description="事件负载")

    # 兼容旧版本字段
    content: Optional[str] = Field(default=None, description="事件内容（兼容字段）")
    content_type: StreamContentType = Field(default=StreamContentType.TEXT, description="内容类型")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="事件元数据")

    def to_sse_format(self) -> str:
        """转换为SSE格式"""
        # 🆕 使用新的payload结构
        event_data = {
            "event_type": self.event_type.value,
            "agent_source": self.agent_source,
            "timestamp": self.timestamp,
            "payload": {
                "id": self.metadata.get("id"),
                "content_type": self.content_type.value,
                "data": self.content or self.payload.get("data", ""),
                "metadata": self.metadata
            }
        }
        return f"data: {json.dumps(event_data, ensure_ascii=False)}\n\n"

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StreamEvent":
        """从字典创建事件（兼容多种格式）"""
        # 兼容旧格式
        if "event_type" in data:
            return cls(**data)

        # 兼容graph格式
        if "event_type" in data and "payload" in data:
            payload = data["payload"]
            return cls(
                event_type=data["event_type"],
                agent_source=data.get("agent_source"),
                timestamp=data.get("timestamp", datetime.now().isoformat()),
                content=payload.get("data"),
                content_type=payload.get("content_type", StreamContentType.TEXT),
                metadata=payload.get("metadata", {})
            )

        # 默认格式
        return cls(**data)

# ==================== 内容类型配置 ====================

class ContentTypeConfig:
    """内容类型配置（用于前端渲染）- juben剧本创作专用"""

    DISPLAY_NAMES = {
        # 基础类型
        StreamContentType.TEXT: "文本",
        StreamContentType.MARKDOWN: "Markdown",
        StreamContentType.JSON: "JSON数据",

        # 思考和分析类
        StreamContentType.THOUGHT: "思考过程",
        StreamContentType.PLAN_STEP: "执行步骤",
        StreamContentType.INSIGHT: "洞察分析",

        # 人物相关
        StreamContentType.CHARACTER_PROFILE: "人物画像",
        StreamContentType.CHARACTER_RELATIONSHIP: "人物关系",

        # 故事结构相关
        StreamContentType.STORY_SUMMARY: "故事梗概",
        StreamContentType.STORY_OUTLINE: "故事大纲",
        StreamContentType.STORY_TYPE: "故事类型",
        StreamContentType.FIVE_ELEMENTS: "故事五元素",
        StreamContentType.SERIES_INFO: "系列信息",
        StreamContentType.SERIES_ANALYSIS: "系列分析",

        # 情节相关
        StreamContentType.MAJOR_PLOT: "大情节点",
        StreamContentType.DETAILED_PLOT: "详细情节点",
        StreamContentType.DRAMA_ANALYSIS: "戏剧功能分析",
        StreamContentType.PLOT_ANALYSIS: "情节分析",

        # 创作相关
        StreamContentType.SCRIPT: "剧本",
        StreamContentType.DRAMA_PLAN: "剧本策划",
        StreamContentType.PROPOSAL: "内容提案",

        # 可视化
        StreamContentType.MIND_MAP: "思维导图",

        # 评估相关
        StreamContentType.EVALUATION: "综合评估",
        StreamContentType.SCRIPT_EVALUATION: "剧本评估",
        StreamContentType.STORY_EVALUATION: "故事评估",
        StreamContentType.OUTLINE_EVALUATION: "大纲评估",
        StreamContentType.IP_EVALUATION: "IP评估",
        StreamContentType.NOVEL_SCREENING: "小说筛选",
        StreamContentType.SCORE_ANALYSIS: "评分分析",

        # 工具相关
        StreamContentType.SEARCH_RESULT: "搜索结果",
        StreamContentType.KNOWLEDGE_RESULT: "知识库结果",
        StreamContentType.REFERENCE_RESULT: "参考文献",
        StreamContentType.DOCUMENT: "文档生成",
        StreamContentType.FORMATTED_CONTENT: "格式化输出",

        # 系统相关
        StreamContentType.SYSTEM_PROGRESS: "系统进度",
        StreamContentType.TOOL_RESULT: "工具结果",
        StreamContentType.WORKFLOW_PROGRESS: "工作流进度",
        StreamContentType.RESULT_INTEGRATION: "结果整合",
        StreamContentType.TEXT_OPERATION: "文本操作",
        StreamContentType.BATCH_PROGRESS: "批处理进度",

        # 其他
        StreamContentType.FINAL_ANSWER: "最终答案",
        StreamContentType.ERROR: "错误",
    }

    ICONS = {
        # 基础类型
        StreamContentType.TEXT: "📝",
        StreamContentType.MARKDOWN: "📖",
        StreamContentType.JSON: "{}",

        # 思考和分析类
        StreamContentType.THOUGHT: "🧠",
        StreamContentType.PLAN_STEP: "📋",
        StreamContentType.INSIGHT: "💡",

        # 人物相关
        StreamContentType.CHARACTER_PROFILE: "👤",
        StreamContentType.CHARACTER_RELATIONSHIP: "🔗",

        # 故事结构相关
        StreamContentType.STORY_SUMMARY: "📜",
        StreamContentType.STORY_OUTLINE: "📕",
        StreamContentType.STORY_TYPE: "🏷️",
        StreamContentType.FIVE_ELEMENTS: "🎨",
        StreamContentType.SERIES_INFO: "ℹ️",
        StreamContentType.SERIES_ANALYSIS: "📊",

        # 情节相关
        StreamContentType.MAJOR_PLOT: "🎬",
        StreamContentType.DETAILED_PLOT: "🎞️",
        StreamContentType.DRAMA_ANALYSIS: "🎪",
        StreamContentType.PLOT_ANALYSIS: "🔍",

        # 创作相关
        StreamContentType.SCRIPT: "🎭",
        StreamContentType.DRAMA_PLAN: "📝",
        StreamContentType.PROPOSAL: "📄",

        # 可视化
        StreamContentType.MIND_MAP: "🕸️",

        # 评估相关
        StreamContentType.EVALUATION: "⭐",
        StreamContentType.SCRIPT_EVALUATION: "🎯",
        StreamContentType.STORY_EVALUATION: "📈",
        StreamContentType.OUTLINE_EVALUATION: "📋",
        StreamContentType.IP_EVALUATION: "💎",
        StreamContentType.NOVEL_SCREENING: "🔎",
        StreamContentType.SCORE_ANALYSIS: "📊",

        # 工具相关
        StreamContentType.SEARCH_RESULT: "🔍",
        StreamContentType.KNOWLEDGE_RESULT: "📚",
        StreamContentType.REFERENCE_RESULT: "📖",
        StreamContentType.DOCUMENT: "📄",
        StreamContentType.FORMATTED_CONTENT: "✨",

        # 系统相关
        StreamContentType.SYSTEM_PROGRESS: "⚙️",
        StreamContentType.TOOL_RESULT: "🔧",
        StreamContentType.WORKFLOW_PROGRESS: "🔄",
        StreamContentType.RESULT_INTEGRATION: "🔀",
        StreamContentType.TEXT_OPERATION: "✂️",
        StreamContentType.BATCH_PROGRESS: "📦",

        # 其他
        StreamContentType.FINAL_ANSWER: "✅",
        StreamContentType.ERROR: "❌",
    }

    COLORS = {
        # 基础类型
        StreamContentType.TEXT: "gray",
        StreamContentType.MARKDOWN: "gray",
        StreamContentType.JSON: "slate",

        # 思考和分析类
        StreamContentType.THOUGHT: "blue",
        StreamContentType.PLAN_STEP: "purple",
        StreamContentType.INSIGHT: "yellow",

        # 人物相关
        StreamContentType.CHARACTER_PROFILE: "indigo",
        StreamContentType.CHARACTER_RELATIONSHIP: "pink",

        # 故事结构相关
        StreamContentType.STORY_SUMMARY: "amber",
        StreamContentType.STORY_OUTLINE: "orange",
        StreamContentType.STORY_TYPE: "stone",
        StreamContentType.FIVE_ELEMENTS: "violet",
        StreamContentType.SERIES_INFO: "cyan",
        StreamContentType.SERIES_ANALYSIS: "teal",

        # 情节相关
        StreamContentType.MAJOR_PLOT: "red",
        StreamContentType.DETAILED_PLOT: "rose",
        StreamContentType.DRAMA_ANALYSIS: "crimson",
        StreamContentType.PLOT_ANALYSIS: "scarlet",

        # 创作相关
        StreamContentType.SCRIPT: "emerald",
        StreamContentType.DRAMA_PLAN: "green",
        StreamContentType.PROPOSAL: "lime",

        # 可视化
        StreamContentType.MIND_MAP: "sky",

        # 评估相关
        StreamContentType.EVALUATION: "orange",
        StreamContentType.SCRIPT_EVALUATION: "amber",
        StreamContentType.STORY_EVALUATION: "yellow",
        StreamContentType.OUTLINE_EVALUATION: "gold",
        StreamContentType.IP_EVALUATION: "fuchsia",
        StreamContentType.NOVEL_SCREENING: "violet",
        StreamContentType.SCORE_ANALYSIS: "indigo",

        # 工具相关
        StreamContentType.SEARCH_RESULT: "blue",
        StreamContentType.KNOWLEDGE_RESULT: "cyan",
        StreamContentType.REFERENCE_RESULT: "teal",
        StreamContentType.DOCUMENT: "stone",
        StreamContentType.FORMATTED_CONTENT: "zinc",

        # 系统相关
        StreamContentType.SYSTEM_PROGRESS: "gray",
        StreamContentType.TOOL_RESULT: "slate",
        StreamContentType.WORKFLOW_PROGRESS: "cool",
        StreamContentType.RESULT_INTEGRATION: "neutral",
        StreamContentType.TEXT_OPERATION: "zinc",
        StreamContentType.BATCH_PROGRESS: "warm",

        # 其他
        StreamContentType.FINAL_ANSWER: "emerald",
        StreamContentType.ERROR: "red",
    }

# ==================== 旧版模型（保留兼容性） ====================

class ContentType(str, Enum):
    """🚫 旧版内容类型（已弃用，请使用StreamContentType）"""
    TEXT = "text"
    MARKDOWN = "markdown"
    JSON = "json"
    HTML = "html"

# ==================== Agent相关模型 ====================

class AgentInfo(BaseModel):
    """Agent信息模型"""
    name: str = Field(description="Agent名称")
    type: str = Field(description="Agent类型")
    description: str = Field(description="Agent描述")
    category: str = Field(description="Agent分类")
    features: List[str] = Field(description="功能特点")
    status: str = Field(description="运行状态")
    capabilities: List[str] = Field(description="能力列表")
    examples: List[str] = Field(description="使用示例")

class AgentListResponse(BaseResponse):
    """Agent列表响应模型"""
    success: bool = True
    agents: List[AgentInfo] = Field(description="Agent列表")
    total: int = Field(description="总数")

# ==================== 健康检查模型 ====================

class HealthResponse(BaseResponse):
    """健康检查响应模型"""
    success: bool = True
    status: str = Field(description="服务状态")
    version: str = Field(description="服务版本")
    uptime: str = Field(description="运行时间")
    dependencies: Dict[str, bool] = Field(description="依赖服务状态")

# ==================== 统计信息模型 ====================

class StatsResponse(BaseResponse):
    """统计信息响应模型"""
    success: bool = True
    total_sessions: int = Field(description="总会话数")
    total_messages: int = Field(description="总消息数")
    active_agents: int = Field(description="活跃Agent数")
    avg_response_time: float = Field(description="平均响应时间")
    system_uptime: float = Field(description="系统运行时间")

# ==================== 设置相关模型 ====================

class SettingsResponse(BaseResponse):
    """设置响应模型"""
    success: bool = True
    settings: Dict[str, Any] = Field(description="设置信息")

class UpdateSettingsRequest(BaseModel):
    """更新设置请求模型"""
    settings: Dict[str, Any] = Field(description="要更新的设置")

# ==================== 文件上传模型 ====================

class FileUploadResponse(BaseResponse):
    """文件上传响应模型"""
    success: bool = True
    file_id: str = Field(description="文件ID")
    filename: str = Field(description="文件名")
    file_size: int = Field(description="文件大小")
    file_type: str = Field(description="文件类型")
    upload_time: str = Field(description="上传时间")

# ==================== 知识库相关模型 ====================

class KnowledgeSearchRequest(BaseModel):
    """知识库搜索请求模型"""
    query: str = Field(description="搜索查询")
    collection: str = Field(default="script_segments", description="集合名称")
    top_k: int = Field(default=5, description="返回数量")
    filter: Optional[Dict[str, Any]] = Field(default=None, description="过滤条件")

class KnowledgeSearchResponse(BaseResponse):
    """知识库搜索响应模型"""
    success: bool = True
    results: List[Dict[str, Any]] = Field(description="搜索结果")
    total: int = Field(description="结果总数")
    query: str = Field(description="查询内容")

# ==================== 网络搜索模型 ====================

class WebSearchRequest(BaseModel):
    """网络搜索请求模型"""
    query: str = Field(description="搜索查询")
    count: int = Field(default=5, description="结果数量")
    language: str = Field(default="zh", description="搜索语言")
    region: str = Field(default="cn", description="搜索区域")

class WebSearchResponse(BaseResponse):
    """网络搜索响应模型"""
    success: bool = True
    results: List[Dict[str, Any]] = Field(description="搜索结果")
    total: int = Field(description="结果总数")
    query: str = Field(description="查询内容")

# ==================== 评估相关模型 ====================

class EvaluationRequest(BaseModel):
    """评估请求模型"""
    content: str = Field(description="要评估的内容")
    evaluation_type: str = Field(default="comprehensive", description="评估类型")
    criteria: Optional[List[str]] = Field(default=None, description="评估标准")

class EvaluationResponse(BaseResponse):
    """评估响应模型"""
    success: bool = True
    score: float = Field(description="总体评分")
    scores: Dict[str, float] = Field(description="各项评分")
    feedback: str = Field(description="反馈意见")
    suggestions: List[str] = Field(description="改进建议")

# ==================== 导出相关模型 ====================

class ExportFormat(str, Enum):
    """导出格式枚举"""
    JSON = "json"
    TXT = "txt"
    MD = "md"
    PDF = "pdf"

class ExportRequest(BaseModel):
    """导出请求模型"""
    session_id: str = Field(description="会话ID")
    format: ExportFormat = Field(description="导出格式")
    include_metadata: bool = Field(default=True, description="是否包含元数据")

class ExportResponse(BaseResponse):
    """导出响应模型"""
    success: bool = True
    download_url: str = Field(description="下载链接")
    filename: str = Field(description="文件名")
    file_size: int = Field(description="文件大小")
    expires_at: str = Field(description="过期时间")


# ==================== 项目管理模型 ====================

class ProjectStatus(str, Enum):
    """项目状态枚举"""
    ACTIVE = "active"           # 活跃项目
    ARCHIVED = "archived"       # 已归档
    DELETED = "deleted"         # 已删除
    COMPLETED = "completed"     # 已完成

class FileType(str, Enum):
    """文件类型枚举"""
    CONVERSATION = "conversation"     # 对话记录
    DRAMA_PLANNING = "drama_planning" # 剧本策划
    CHARACTER_PROFILE = "character_profile"  # 人物小传
    SCRIPT = "script"                # 剧本
    PLOT_POINTS = "plot_points"      # 情节点
    EVALUATION = "evaluation"        # 评估
    NOTE = "note"                    # 笔记
    REFERENCE = "reference"          # 参考资料
    EXPORT = "export"                # 导出文件
    OTHER = "other"                  # 其他

class Project(BaseModel):
    """项目模型"""
    id: str = Field(description="项目唯一ID")
    name: str = Field(description="项目名称")
    description: Optional[str] = Field(default="", description="项目描述")
    user_id: str = Field(description="用户ID")
    created_at: datetime = Field(description="创建时间")
    updated_at: datetime = Field(description="更新时间")
    status: ProjectStatus = Field(default=ProjectStatus.ACTIVE, description="项目状态")
    tags: List[str] = Field(default_factory=list, description="标签列表")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")
    file_count: int = Field(default=0, description="文件数量")

class ProjectFile(BaseModel):
    """项目文件模型"""
    id: str = Field(description="文件ID")
    project_id: str = Field(description="项目ID")
    filename: str = Field(description="文件名")
    file_type: FileType = Field(description="文件类型")
    agent_source: Optional[str] = Field(default=None, description="来源Agent")
    content: Any = Field(default=None, description="文件内容")
    tags: List[str] = Field(default_factory=list, description="标签列表")
    created_at: datetime = Field(description="创建时间")
    updated_at: datetime = Field(description="更新时间")
    file_size: int = Field(default=0, description="文件大小(字节)")
    version: int = Field(default=1, description="版本号")

class ProjectCreateRequest(BaseModel):
    """创建项目请求模型"""
    name: str = Field(description="项目名称", min_length=1, max_length=200)
    description: Optional[str] = Field(default="", description="项目描述")
    tags: List[str] = Field(default_factory=list, description="标签列表")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")

class ProjectUpdateRequest(BaseModel):
    """更新项目请求模型"""
    name: Optional[str] = Field(default=None, description="项目名称")
    description: Optional[str] = Field(default=None, description="项目描述")
    status: Optional[ProjectStatus] = Field(default=None, description="项目状态")
    tags: Optional[List[str]] = Field(default=None, description="标签列表")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="元数据")

class ProjectMember(BaseModel):
    """项目成员"""
    user_id: str = Field(description="用户ID")
    role: str = Field(default="member", description="成员角色")
    display_name: Optional[str] = Field(default=None, description="显示名称")

class ProjectMemberUpdateRequest(BaseModel):
    """更新项目成员请求"""
    role: Optional[str] = None
    display_name: Optional[str] = None

class ProjectListResponse(BaseResponse):
    """项目列表响应模型"""
    success: bool = True
    projects: List[Project] = Field(description="项目列表")
    total: int = Field(description="项目总数")
    page: int = Field(default=1, description="当前页码")
    page_size: int = Field(default=20, description="每页数量")

class ProjectDetailResponse(BaseResponse):
    """项目详情响应模型"""
    success: bool = True
    project: Project = Field(description="项目信息")
    files: List[ProjectFile] = Field(default_factory=list, description="项目文件列表")

class ProjectFileCreateRequest(BaseModel):
    """创建项目文件请求模型"""
    filename: str = Field(description="文件名")
    file_type: FileType = Field(description="文件类型")
    content: Any = Field(description="文件内容")
    agent_source: Optional[str] = Field(default=None, description="来源Agent")
    tags: List[str] = Field(default_factory=list, description="标签列表")

class ProjectFileUpdateRequest(BaseModel):
    """更新项目文件请求模型"""
    filename: Optional[str] = Field(default=None, description="文件名")
    content: Optional[Any] = Field(default=None, description="文件内容")
    tags: Optional[List[str]] = Field(default=None, description="标签列表")

class ProjectExportRequest(BaseModel):
    """项目导出请求模型"""
    format: ExportFormat = Field(description="导出格式")
    include_files: bool = Field(default=True, description="是否包含文件")
    file_types: Optional[List[FileType]] = Field(default=None, description="要包含的文件类型")

class ProjectSearchRequest(BaseModel):
    """项目搜索请求模型"""
    query: Optional[str] = Field(default=None, description="搜索关键词")
    tags: Optional[List[str]] = Field(default=None, description="标签过滤")
    status: Optional[ProjectStatus] = Field(default=None, description="状态过滤")
    date_from: Optional[datetime] = Field(default=None, description="起始日期")
    date_to: Optional[datetime] = Field(default=None, description="结束日期")
    page: int = Field(default=1, description="页码")
    page_size: int = Field(default=20, description="每页数量")

class ProjectDuplicateRequest(BaseModel):
    """项目复制请求模型"""
    new_name: str = Field(description="新项目名称", min_length=1, max_length=200)
    new_description: Optional[str] = Field(default=None, description="新项目描述（留空则复制原描述）")
    include_files: bool = Field(default=True, description="是否复制项目文件")
    file_types: Optional[List[FileType]] = Field(default=None, description="要复制的文件类型")

class ProjectTemplateRequest(BaseModel):
    """项目模板请求模型"""
    template_name: str = Field(description="模板名称", min_length=1, max_length=200)
    template_description: Optional[str] = Field(default="", description="模板描述")
    category: Optional[str] = Field(default=None, description="模板分类", max_length=50)
    include_files: bool = Field(default=True, description="是否包含文件")
    is_public: bool = Field(default=False, description="是否为公共模板")

class ProjectFromTemplateRequest(BaseModel):
    """从模板创建项目请求模型"""
    template_id: str = Field(description="模板ID", min_length=1, max_length=100)
    project_name: str = Field(description="新项目名称", min_length=1, max_length=200)
    project_description: Optional[str] = Field(default="", description="项目描述")
    include_files: bool = Field(default=True, description="是否包含模板文件")
    tags: List[str] = Field(default_factory=list, description="项目标签")

class ProjectRestoreRequest(BaseModel):
    """项目恢复请求模型"""
    new_name: Optional[str] = Field(default=None, description="新项目名称（留空则使用原名称）")
    restore_files: bool = Field(default=True, description="是否恢复文件")


# ==================== Notes系统相关模型（）====================

class InteractionType(str, Enum):
    """交互类型枚举"""
    FULL_ANALYSIS = "full_analysis"
    QUICK_SUGGESTION = "quick_suggestion"
    WRITE_SCRIPT = "write_script"
    EVALUATE = "evaluate"
    PLAN = "plan"
    DRAMA_CONTINUE = "drama_continue"
    DRAMA_SELECT = "drama_select"

class NoteContentType(str, Enum):
    """Note内容类型枚举（用于Agent输出分类）- 与StreamContentType保持一致"""

    # 基础类型
    TEXT = "text"
    MARKDOWN = "markdown"
    JSON = "json"

    # 思考和分析类
    THOUGHT = "thought"
    PLAN_STEP = "plan_step"
    INSIGHT = "insight"

    # 人物相关
    CHARACTER_PROFILE = "character_profile"
    CHARACTER_RELATIONSHIP = "character_relationship"

    # 故事结构相关
    STORY_SUMMARY = "story_summary"
    STORY_OUTLINE = "story_outline"
    STORY_TYPE = "story_type"
    FIVE_ELEMENTS = "five_elements"
    SERIES_INFO = "series_info"
    SERIES_ANALYSIS = "series_analysis"

    # 情节相关
    MAJOR_PLOT = "major_plot"
    DETAILED_PLOT = "detailed_plot"
    DRAMA_ANALYSIS = "drama_analysis"
    PLOT_ANALYSIS = "plot_analysis"

    # 创作相关
    SCRIPT = "script"
    DRAMA_PLAN = "drama_plan"
    PROPOSAL = "proposal"

    # 可视化
    MIND_MAP = "mind_map"

    # 评估相关
    EVALUATION = "evaluation"
    SCRIPT_EVALUATION = "script_evaluation"
    STORY_EVALUATION = "story_evaluation"
    OUTLINE_EVALUATION = "outline_evaluation"
    IP_EVALUATION = "ip_evaluation"
    NOVEL_SCREENING = "novel_screening"
    SCORE_ANALYSIS = "score_analysis"

    # 工具相关
    SEARCH_RESULT = "search_result"
    KNOWLEDGE_RESULT = "knowledge_result"
    REFERENCE_RESULT = "reference_result"
    DOCUMENT = "document"
    FORMATTED_CONTENT = "formatted_content"

    # 系统相关
    SYSTEM_PROGRESS = "system_progress"
    TOOL_RESULT = "tool_result"
    WORKFLOW_PROGRESS = "workflow_progress"
    RESULT_INTEGRATION = "result_integration"
    TEXT_OPERATION = "text_operation"
    BATCH_PROGRESS = "batch_progress"

    # 其他
    FINAL_ANSWER = "final_answer"
    ERROR = "error_content"

class NoteCreateRequest(BaseModel):
    """Note创建请求模型"""
    user_id: str = Field(..., description="用户ID", min_length=1, max_length=100, pattern=r"^[a-zA-Z0-9_-]+$")
    session_id: str = Field(..., description="会话ID", min_length=1, max_length=100)
    action: str = Field(..., description="Agent动作类型（如character_profile_generator）", min_length=1, max_length=100)
    name: str = Field(..., description="Note名称（唯一标识，如character1）", min_length=1, max_length=100)
    context: str = Field(..., description="Note内容", min_length=1, max_length=100000)
    title: Optional[str] = Field(default=None, description="Note标题", max_length=500)
    cover_title: Optional[str] = Field(default=None, description="封面标题", max_length=200)
    content_type: Optional[NoteContentType] = Field(default=None, description="内容类型")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="元数据")

class NoteUpdateRequest(BaseModel):
    """Note更新请求模型"""
    select_status: Optional[int] = Field(default=None, description="选择状态（0未选择，1已选择）", ge=0, le=1)
    user_comment: Optional[str] = Field(default=None, description="用户评论", max_length=5000)
    content: Optional[str] = Field(default=None, description="更新内容", max_length=100000)

class NoteListResponse(BaseResponse):
    """Note列表响应模型"""
    success: bool = True
    notes: List[Dict[str, Any]] = Field(default_factory=list, description="Note列表")
    total_count: int = Field(default=0, description="总数量")
    grouped_by_action: Dict[str, List[Dict[str, Any]]] = Field(default_factory=dict, description="按action分组")

class NoteSelectRequest(BaseModel):
    """批量Note选择请求模型"""
    user_id: str = Field(..., description="用户ID")
    session_id: str = Field(..., description="会话ID")
    selections: List[Dict[str, Any]] = Field(..., description="选择列表，格式: [{'action': 'character_profile_generator', 'name': 'character1', 'selected': True, 'user_comment': '...'}]")

class NoteExportRequest(BaseModel):
    """Note导出请求模型"""
    user_id: str = Field(..., description="用户ID")
    session_id: str = Field(..., description="会话ID")
    export_format: ExportFormat = Field(default=ExportFormat.TXT, description="导出格式")
    content_types: Optional[List[NoteContentType]] = Field(default=None, description="要导出的内容类型")
    include_user_comments: bool = Field(default=True, description="是否包含用户评论")

class NoteExportResponse(BaseResponse):
    """Note导出响应模型"""
    success: bool = True
    export_format: ExportFormat = Field(..., description="导出格式")
    total_items: int = Field(default=0, description="导出项目总数")
    content_summary: Dict[str, int] = Field(default_factory=dict, description="各类型内容统计")
    exported_data: str = Field(default="", description="导出数据")
    filename: str = Field(default="", description="建议文件名")

# ==================== 用户选择相关模型 ====================

class UserSelections(BaseModel):
    """用户选择数据模型（用于后续请求）"""
    character_profiles: List[Dict[str, Any]] = Field(default_factory=list, description="选择的人物小传")
    character_relationships: List[Dict[str, Any]] = Field(default_factory=list, description="选择的人物关系")
    plot_points: List[Dict[str, Any]] = Field(default_factory=list, description="选择的情节点")
    story_outlines: List[Dict[str, Any]] = Field(default_factory=list, description="选择的故事大纲")
    scripts: List[Dict[str, Any]] = Field(default_factory=list, description="选择的剧本")
    evaluations: List[Dict[str, Any]] = Field(default_factory=list, description="选择的评估")
    task_context: Optional[str] = Field(default=None, description="任务上下文")

# ==================== 增强的聊天请求模型 ====================

class EnhancedChatRequest(ChatRequest):
    """增强的聊天请求模型（支持Notes引用）"""
    interaction_type: InteractionType = Field(default=InteractionType.FULL_ANALYSIS, description="交互类型")
    drama_selections: Optional[UserSelections] = Field(default=None, description="用户选择的Notes数据")
    references: Optional[List[str]] = Field(default_factory=list, description="引用的Notes ID列表（如@character1）")
    auto_select: bool = Field(default=False, description="是否自动选择")
