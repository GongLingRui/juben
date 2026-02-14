/**
 * 内容类型配置
 * 与后端 apis/core/schemas.py 中的 ContentTypeConfig 保持一致
 * juben剧本创作专用类型系统
 */

// 内容类型枚举（与后端一致）
export enum StreamContentType {
  // ============ 基础类型 ============
  TEXT = "text",
  MARKDOWN = "markdown",
  JSON = "json",

  // ============ 思考和分析类 ============
  THOUGHT = "thought",
  PLAN_STEP = "plan_step",
  INSIGHT = "insight",

  // ============ 人物相关 ============
  CHARACTER_PROFILE = "character_profile",
  CHARACTER_RELATIONSHIP = "character_relationship",

  // ============ 故事结构相关 ============
  STORY_SUMMARY = "story_summary",
  STORY_OUTLINE = "story_outline",
  STORY_TYPE = "story_type",
  FIVE_ELEMENTS = "five_elements",
  SERIES_INFO = "series_info",
  SERIES_ANALYSIS = "series_analysis",

  // ============ 情节相关 ============
  MAJOR_PLOT = "major_plot",
  DETAILED_PLOT = "detailed_plot",
  DRAMA_ANALYSIS = "drama_analysis",
  PLOT_ANALYSIS = "plot_analysis",

  // ============ 创作相关 ============
  SCRIPT = "script",
  DRAMA_PLAN = "drama_plan",
  PROPOSAL = "proposal",

  // ============ 可视化 ============
  MIND_MAP = "mind_map",

  // ============ 评估相关 ============
  EVALUATION = "evaluation",
  SCRIPT_EVALUATION = "script_evaluation",
  STORY_EVALUATION = "story_evaluation",
  OUTLINE_EVALUATION = "outline_evaluation",
  IP_EVALUATION = "ip_evaluation",
  NOVEL_SCREENING = "novel_screening",
  SCORE_ANALYSIS = "score_analysis",

  // ============ 工具相关 ============
  SEARCH_RESULT = "search_result",
  KNOWLEDGE_RESULT = "knowledge_result",
  REFERENCE_RESULT = "reference_result",
  DOCUMENT = "document",
  FORMATTED_CONTENT = "formatted_content",

  // ============ 系统相关 ============
  SYSTEM_PROGRESS = "system_progress",
  TOOL_RESULT = "tool_result",
  WORKFLOW_PROGRESS = "workflow_progress",
  RESULT_INTEGRATION = "result_integration",
  TEXT_OPERATION = "text_operation",
  BATCH_PROGRESS = "batch_progress",

  // ============ 其他 ============
  FINAL_ANSWER = "final_answer",
  ERROR = "error_content",
}

// 内容类型显示名称
export const CONTENT_TYPE_DISPLAY_NAMES: Record<StreamContentType, string> = {
  // 基础类型
  [StreamContentType.TEXT]: "文本",
  [StreamContentType.MARKDOWN]: "Markdown",
  [StreamContentType.JSON]: "JSON数据",

  // 思考和分析类
  [StreamContentType.THOUGHT]: "思考过程",
  [StreamContentType.PLAN_STEP]: "执行步骤",
  [StreamContentType.INSIGHT]: "洞察分析",

  // 人物相关
  [StreamContentType.CHARACTER_PROFILE]: "人物画像",
  [StreamContentType.CHARACTER_RELATIONSHIP]: "人物关系",

  // 故事结构相关
  [StreamContentType.STORY_SUMMARY]: "故事梗概",
  [StreamContentType.STORY_OUTLINE]: "故事大纲",
  [StreamContentType.STORY_TYPE]: "故事类型",
  [StreamContentType.FIVE_ELEMENTS]: "故事五元素",
  [StreamContentType.SERIES_INFO]: "系列信息",
  [StreamContentType.SERIES_ANALYSIS]: "系列分析",

  // 情节相关
  [StreamContentType.MAJOR_PLOT]: "大情节点",
  [StreamContentType.DETAILED_PLOT]: "详细情节点",
  [StreamContentType.DRAMA_ANALYSIS]: "戏剧功能分析",
  [StreamContentType.PLOT_ANALYSIS]: "情节分析",

  // 创作相关
  [StreamContentType.SCRIPT]: "剧本",
  [StreamContentType.DRAMA_PLAN]: "剧本策划",
  [StreamContentType.PROPOSAL]: "内容提案",

  // 可视化
  [StreamContentType.MIND_MAP]: "思维导图",

  // 评估相关
  [StreamContentType.EVALUATION]: "综合评估",
  [StreamContentType.SCRIPT_EVALUATION]: "剧本评估",
  [StreamContentType.STORY_EVALUATION]: "故事评估",
  [StreamContentType.OUTLINE_EVALUATION]: "大纲评估",
  [StreamContentType.IP_EVALUATION]: "IP评估",
  [StreamContentType.NOVEL_SCREENING]: "小说筛选",
  [StreamContentType.SCORE_ANALYSIS]: "评分分析",

  // 工具相关
  [StreamContentType.SEARCH_RESULT]: "搜索结果",
  [StreamContentType.KNOWLEDGE_RESULT]: "知识库结果",
  [StreamContentType.REFERENCE_RESULT]: "参考文献",
  [StreamContentType.DOCUMENT]: "文档生成",
  [StreamContentType.FORMATTED_CONTENT]: "格式化输出",

  // 系统相关
  [StreamContentType.SYSTEM_PROGRESS]: "系统进度",
  [StreamContentType.TOOL_RESULT]: "工具结果",
  [StreamContentType.WORKFLOW_PROGRESS]: "工作流进度",
  [StreamContentType.RESULT_INTEGRATION]: "结果整合",
  [StreamContentType.TEXT_OPERATION]: "文本操作",
  [StreamContentType.BATCH_PROGRESS]: "批处理进度",

  // 其他
  [StreamContentType.FINAL_ANSWER]: "最终答案",
  [StreamContentType.ERROR]: "错误",
};

// 内容类型图标
export const CONTENT_TYPE_ICONS: Record<StreamContentType, string> = {
  // 基础类型
  [StreamContentType.TEXT]: "📝",
  [StreamContentType.MARKDOWN]: "📖",
  [StreamContentType.JSON]: "{}",

  // 思考和分析类
  [StreamContentType.THOUGHT]: "🧠",
  [StreamContentType.PLAN_STEP]: "📋",
  [StreamContentType.INSIGHT]: "💡",

  // 人物相关
  [StreamContentType.CHARACTER_PROFILE]: "👤",
  [StreamContentType.CHARACTER_RELATIONSHIP]: "🔗",

  // 故事结构相关
  [StreamContentType.STORY_SUMMARY]: "📜",
  [StreamContentType.STORY_OUTLINE]: "📕",
  [StreamContentType.STORY_TYPE]: "🏷️",
  [StreamContentType.FIVE_ELEMENTS]: "🎨",
  [StreamContentType.SERIES_INFO]: "ℹ️",
  [StreamContentType.SERIES_ANALYSIS]: "📊",

  // 情节相关
  [StreamContentType.MAJOR_PLOT]: "🎬",
  [StreamContentType.DETAILED_PLOT]: "🎞️",
  [StreamContentType.DRAMA_ANALYSIS]: "🎪",
  [StreamContentType.PLOT_ANALYSIS]: "🔍",

  // 创作相关
  [StreamContentType.SCRIPT]: "🎭",
  [StreamContentType.DRAMA_PLAN]: "📝",
  [StreamContentType.PROPOSAL]: "📄",

  // 可视化
  [StreamContentType.MIND_MAP]: "🕸️",

  // 评估相关
  [StreamContentType.EVALUATION]: "⭐",
  [StreamContentType.SCRIPT_EVALUATION]: "🎯",
  [StreamContentType.STORY_EVALUATION]: "📈",
  [StreamContentType.OUTLINE_EVALUATION]: "📋",
  [StreamContentType.IP_EVALUATION]: "💎",
  [StreamContentType.NOVEL_SCREENING]: "🔎",
  [StreamContentType.SCORE_ANALYSIS]: "📊",

  // 工具相关
  [StreamContentType.SEARCH_RESULT]: "🔍",
  [StreamContentType.KNOWLEDGE_RESULT]: "📚",
  [StreamContentType.REFERENCE_RESULT]: "📖",
  [StreamContentType.DOCUMENT]: "📄",
  [StreamContentType.FORMATTED_CONTENT]: "✨",

  // 系统相关
  [StreamContentType.SYSTEM_PROGRESS]: "⚙️",
  [StreamContentType.TOOL_RESULT]: "🔧",
  [StreamContentType.WORKFLOW_PROGRESS]: "🔄",
  [StreamContentType.RESULT_INTEGRATION]: "🔀",
  [StreamContentType.TEXT_OPERATION]: "✂️",
  [StreamContentType.BATCH_PROGRESS]: "📦",

  // 其他
  [StreamContentType.FINAL_ANSWER]: "✅",
  [StreamContentType.ERROR]: "❌",
};

// 内容类型颜色（Tailwind类）
export const CONTENT_TYPE_COLORS: Record<StreamContentType, {
  bg: string;
  text: string;
  border: string;
}> = {
  // 基础类型
  [StreamContentType.TEXT]: {
    bg: "bg-gray-50",
    text: "text-gray-900",
    border: "border-gray-200",
  },
  [StreamContentType.MARKDOWN]: {
    bg: "bg-gray-50",
    text: "text-gray-900",
    border: "border-gray-200",
  },
  [StreamContentType.JSON]: {
    bg: "bg-slate-50",
    text: "text-slate-900",
    border: "border-slate-200",
  },

  // 思考和分析类
  [StreamContentType.THOUGHT]: {
    bg: "bg-blue-50",
    text: "text-blue-900",
    border: "border-blue-200",
  },
  [StreamContentType.PLAN_STEP]: {
    bg: "bg-purple-50",
    text: "text-purple-900",
    border: "border-purple-200",
  },
  [StreamContentType.INSIGHT]: {
    bg: "bg-yellow-50",
    text: "text-yellow-900",
    border: "border-yellow-200",
  },

  // 人物相关
  [StreamContentType.CHARACTER_PROFILE]: {
    bg: "bg-indigo-50",
    text: "text-indigo-900",
    border: "border-indigo-200",
  },
  [StreamContentType.CHARACTER_RELATIONSHIP]: {
    bg: "bg-pink-50",
    text: "text-pink-900",
    border: "border-pink-200",
  },

  // 故事结构相关
  [StreamContentType.STORY_SUMMARY]: {
    bg: "bg-amber-50",
    text: "text-amber-900",
    border: "border-amber-200",
  },
  [StreamContentType.STORY_OUTLINE]: {
    bg: "bg-orange-50",
    text: "text-orange-900",
    border: "border-orange-200",
  },
  [StreamContentType.STORY_TYPE]: {
    bg: "bg-stone-50",
    text: "text-stone-900",
    border: "border-stone-200",
  },
  [StreamContentType.FIVE_ELEMENTS]: {
    bg: "bg-violet-50",
    text: "text-violet-900",
    border: "border-violet-200",
  },
  [StreamContentType.SERIES_INFO]: {
    bg: "bg-cyan-50",
    text: "text-cyan-900",
    border: "border-cyan-200",
  },
  [StreamContentType.SERIES_ANALYSIS]: {
    bg: "bg-teal-50",
    text: "text-teal-900",
    border: "border-teal-200",
  },

  // 情节相关
  [StreamContentType.MAJOR_PLOT]: {
    bg: "bg-red-50",
    text: "text-red-900",
    border: "border-red-200",
  },
  [StreamContentType.DETAILED_PLOT]: {
    bg: "bg-rose-50",
    text: "text-rose-900",
    border: "border-rose-200",
  },
  [StreamContentType.DRAMA_ANALYSIS]: {
    bg: "bg-crimson-50",
    text: "text-crimson-900",
    border: "border-crimson-200",
  },
  [StreamContentType.PLOT_ANALYSIS]: {
    bg: "bg-scarlet-50",
    text: "text-scarlet-900",
    border: "border-scarlet-200",
  },

  // 创作相关
  [StreamContentType.SCRIPT]: {
    bg: "bg-emerald-50",
    text: "text-emerald-900",
    border: "border-emerald-200",
  },
  [StreamContentType.DRAMA_PLAN]: {
    bg: "bg-green-50",
    text: "text-green-900",
    border: "border-green-200",
  },
  [StreamContentType.PROPOSAL]: {
    bg: "bg-lime-50",
    text: "text-lime-900",
    border: "border-lime-200",
  },

  // 可视化
  [StreamContentType.MIND_MAP]: {
    bg: "bg-sky-50",
    text: "text-sky-900",
    border: "border-sky-200",
  },

  // 评估相关
  [StreamContentType.EVALUATION]: {
    bg: "bg-orange-50",
    text: "text-orange-900",
    border: "border-orange-200",
  },
  [StreamContentType.SCRIPT_EVALUATION]: {
    bg: "bg-amber-50",
    text: "text-amber-900",
    border: "border-amber-200",
  },
  [StreamContentType.STORY_EVALUATION]: {
    bg: "bg-yellow-50",
    text: "text-yellow-900",
    border: "border-yellow-200",
  },
  [StreamContentType.OUTLINE_EVALUATION]: {
    bg: "bg-gold-50",
    text: "text-gold-900",
    border: "border-gold-200",
  },
  [StreamContentType.IP_EVALUATION]: {
    bg: "bg-fuchsia-50",
    text: "text-fuchsia-900",
    border: "border-fuchsia-200",
  },
  [StreamContentType.NOVEL_SCREENING]: {
    bg: "bg-violet-50",
    text: "text-violet-900",
    border: "border-violet-200",
  },
  [StreamContentType.SCORE_ANALYSIS]: {
    bg: "bg-indigo-50",
    text: "text-indigo-900",
    border: "border-indigo-200",
  },

  // 工具相关
  [StreamContentType.SEARCH_RESULT]: {
    bg: "bg-blue-50",
    text: "text-blue-900",
    border: "border-blue-200",
  },
  [StreamContentType.KNOWLEDGE_RESULT]: {
    bg: "bg-cyan-50",
    text: "text-cyan-900",
    border: "border-cyan-200",
  },
  [StreamContentType.REFERENCE_RESULT]: {
    bg: "bg-teal-50",
    text: "text-teal-900",
    border: "border-teal-200",
  },
  [StreamContentType.DOCUMENT]: {
    bg: "bg-stone-50",
    text: "text-stone-900",
    border: "border-stone-200",
  },
  [StreamContentType.FORMATTED_CONTENT]: {
    bg: "bg-zinc-50",
    text: "text-zinc-900",
    border: "border-zinc-200",
  },

  // 系统相关
  [StreamContentType.SYSTEM_PROGRESS]: {
    bg: "bg-gray-50",
    text: "text-gray-900",
    border: "border-gray-200",
  },
  [StreamContentType.TOOL_RESULT]: {
    bg: "bg-slate-50",
    text: "text-slate-900",
    border: "border-slate-200",
  },
  [StreamContentType.WORKFLOW_PROGRESS]: {
    bg: "bg-cool-50",
    text: "text-cool-900",
    border: "border-cool-200",
  },
  [StreamContentType.RESULT_INTEGRATION]: {
    bg: "bg-neutral-50",
    text: "text-neutral-900",
    border: "border-neutral-200",
  },
  [StreamContentType.TEXT_OPERATION]: {
    bg: "bg-zinc-50",
    text: "text-zinc-900",
    border: "border-zinc-200",
  },
  [StreamContentType.BATCH_PROGRESS]: {
    bg: "bg-warm-50",
    text: "text-warm-900",
    border: "border-warm-200",
  },

  // 其他
  [StreamContentType.FINAL_ANSWER]: {
    bg: "bg-emerald-50",
    text: "text-emerald-900",
    border: "border-emerald-200",
  },
  [StreamContentType.ERROR]: {
    bg: "bg-red-50",
    text: "text-red-900",
    border: "border-red-200",
  },
};

/**
 * 获取内容类型配置
 */
export function getContentTypeConfig(contentType: StreamContentType) {
  return {
    displayName: CONTENT_TYPE_DISPLAY_NAMES[contentType],
    icon: CONTENT_TYPE_ICONS[contentType],
    colors: CONTENT_TYPE_COLORS[contentType],
  };
}

/**
 * 解析内容类型（兼容多种格式）
 */
export function parseContentType(contentType: string | undefined): StreamContentType {
  if (!contentType) {
    return StreamContentType.TEXT;
  }

  // 如果是有效的枚举值，直接返回
  if (Object.values(StreamContentType).includes(contentType as StreamContentType)) {
    return contentType as StreamContentType;
  }

  // 兼容旧格式
  const normalized = contentType.toLowerCase().replace(/-/g, '_');

  // 基础类型
  if (normalized.includes('markdown')) return StreamContentType.MARKDOWN;
  if (normalized.includes('json')) return StreamContentType.JSON;

  // 思考和分析类
  if (normalized.includes('thought')) return StreamContentType.THOUGHT;
  if (normalized.includes('plan')) return StreamContentType.PLAN_STEP;
  if (normalized.includes('insight')) return StreamContentType.INSIGHT;

  // 人物相关
  if (normalized.includes('character_profile') || normalized.includes('人物画像') || normalized.includes('人物小传')) {
    return StreamContentType.CHARACTER_PROFILE;
  }
  if (normalized.includes('relationship') || normalized.includes('人物关系')) {
    return StreamContentType.CHARACTER_RELATIONSHIP;
  }

  // 故事结构相关
  if (normalized.includes('summary') || normalized.includes('梗概')) {
    return StreamContentType.STORY_SUMMARY;
  }
  if (normalized.includes('outline') || normalized.includes('大纲')) {
    return StreamContentType.STORY_OUTLINE;
  }
  if (normalized.includes('story_type') || normalized.includes('类型')) {
    return StreamContentType.STORY_TYPE;
  }
  if (normalized.includes('five_elements') || normalized.includes('五元素')) {
    return StreamContentType.FIVE_ELEMENTS;
  }
  if (normalized.includes('series_info') || normalized.includes('系列信息')) {
    return StreamContentType.SERIES_INFO;
  }
  if (normalized.includes('series_analysis')) {
    return StreamContentType.SERIES_ANALYSIS;
  }

  // 情节相关
  if (normalized.includes('major_plot') || normalized.includes('大情节')) {
    return StreamContentType.MAJOR_PLOT;
  }
  if (normalized.includes('detailed_plot') || normalized.includes('详细情节')) {
    return StreamContentType.DETAILED_PLOT;
  }
  if (normalized.includes('drama_analysis') || normalized.includes('戏剧功能')) {
    return StreamContentType.DRAMA_ANALYSIS;
  }
  if (normalized.includes('plot_analysis') || normalized.includes('情节分析')) {
    return StreamContentType.PLOT_ANALYSIS;
  }

  // 创作相关
  if (normalized.includes('script') || normalized.includes('剧本')) {
    return StreamContentType.SCRIPT;
  }
  if (normalized.includes('drama_plan') || normalized.includes('策划')) {
    return StreamContentType.DRAMA_PLAN;
  }
  if (normalized.includes('proposal') || normalized.includes('提案')) {
    return StreamContentType.PROPOSAL;
  }

  // 可视化
  if (normalized.includes('mind_map') || normalized.includes('思维导图')) {
    return StreamContentType.MIND_MAP;
  }

  // 评估相关
  if (normalized.includes('script_evaluation') || normalized.includes('剧本评估')) {
    return StreamContentType.SCRIPT_EVALUATION;
  }
  if (normalized.includes('story_evaluation') || normalized.includes('故事评估')) {
    return StreamContentType.STORY_EVALUATION;
  }
  if (normalized.includes('outline_evaluation') || normalized.includes('大纲评估')) {
    return StreamContentType.OUTLINE_EVALUATION;
  }
  if (normalized.includes('ip_evaluation')) {
    return StreamContentType.IP_EVALUATION;
  }
  if (normalized.includes('novel_screening')) {
    return StreamContentType.NOVEL_SCREENING;
  }
  if (normalized.includes('score_analysis')) {
    return StreamContentType.SCORE_ANALYSIS;
  }
  if (normalized.includes('eval') || normalized.includes('评估')) {
    return StreamContentType.EVALUATION;
  }

  // 工具相关
  if (normalized.includes('search') || normalized.includes('搜索')) {
    return StreamContentType.SEARCH_RESULT;
  }
  if (normalized.includes('knowledge') || normalized.includes('知识库')) {
    return StreamContentType.KNOWLEDGE_RESULT;
  }
  if (normalized.includes('reference') || normalized.includes('参考')) {
    return StreamContentType.REFERENCE_RESULT;
  }
  if (normalized.includes('document') || normalized.includes('文档')) {
    return StreamContentType.DOCUMENT;
  }
  if (normalized.includes('formatted') || normalized.includes('格式化')) {
    return StreamContentType.FORMATTED_CONTENT;
  }

  // 系统相关
  if (normalized.includes('workflow') || normalized.includes('工作流')) {
    return StreamContentType.WORKFLOW_PROGRESS;
  }
  if (normalized.includes('integration') || normalized.includes('整合')) {
    return StreamContentType.RESULT_INTEGRATION;
  }
  if (normalized.includes('batch') || normalized.includes('批处理')) {
    return StreamContentType.BATCH_PROGRESS;
  }
  if (normalized.includes('text_operation') || normalized.includes('文本操作')) {
    return StreamContentType.TEXT_OPERATION;
  }
  if (normalized.includes('system') || normalized.includes('系统')) {
    return StreamContentType.SYSTEM_PROGRESS;
  }
  if (normalized.includes('tool')) {
    return StreamContentType.TOOL_RESULT;
  }

  // 其他
  if (normalized.includes('final') || normalized.includes('最终')) {
    return StreamContentType.FINAL_ANSWER;
  }
  if (normalized.includes('error') || normalized.includes('错误')) {
    return StreamContentType.ERROR;
  }

  return StreamContentType.TEXT;
}
