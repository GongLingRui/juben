/**
 * Agents 配置文件
 * 包含所有可用的智能体及其详细信息
 */

export interface AgentConfig {
  id: string;
  name: string;
  displayName: string;
  description: string;
  category: AgentCategory;
  icon: string;
  model: string;
  apiEndpoint: string;
  features: string[];
  capabilities: string[];
  inputExample: string;
  outputExample: string;
  status: 'active' | 'beta' | 'experimental';
}

export type AgentCategory =
  | 'planning'        // 策划类
  | 'creation'        // 创作类
  | 'evaluation'      // 评估类
  | 'analysis'        // 分析类
  | 'workflow'        // 工作流
  | 'utility'         // 工具类
  | 'character'       // 人物类
  | 'story';          // 故事类

/**
 * 所有可用的 Agents 配置
 */
export const AGENTS_CONFIG: AgentConfig[] = [
  // ==================== 策划类 ====================
  {
    id: 'short_drama_planner',
    name: 'ShortDramaPlannerAgent',
    displayName: '短剧策划助手',
    description: '专业的短剧策划和创作建议助手，提供剧本结构、情节设计、人物塑造等全方位策划支持',
    category: 'planning',
    icon: '📋',
    model: 'glm-4-flash',
    apiEndpoint: '/juben/chat',
    features: [
      '剧本策划',
      '情节设计建议',
      '结构优化',
      '创作指导'
    ],
    capabilities: [
      '分析剧本需求并提供专业策划建议',
      '设计合理的情节结构和故事节奏',
      '提供人物塑造和对话写作指导',
      '优化剧本的商业价值和观赏性'
    ],
    inputExample: '帮我策划一个关于都市爱情的短剧剧本',
    outputExample: '根据您的需求，我为您策划了以下短剧方案...',
    status: 'active'
  },

  // ==================== 创作类 ====================
  {
    id: 'short_drama_creator',
    name: 'ShortDramaCreatorAgent',
    displayName: '短剧创作助手',
    description: '专业短剧内容创作助手，帮助生成高质量剧本内容',
    category: 'creation',
    icon: '✍️',
    model: 'glm-4.7-flash',
    apiEndpoint: '/juben/chat',
    features: [
      '剧本创作',
      '场景描写',
      '对话生成',
      '情节展开'
    ],
    capabilities: [
      '创作完整的短剧剧本',
      '生成生动的场景描写',
      '编写符合人物性格的对话',
      '展开引人入胜的故事情节'
    ],
    inputExample: '创作一个悬疑短剧的第一场戏',
    outputExample: '【第一场】\n场景：废弃工厂 - 夜',
    status: 'active'
  },

  // ==================== 评估类 ====================
  {
    id: 'short_drama_evaluation',
    name: 'ShortDramaEvaluationAgent',
    displayName: '短剧评估助手',
    description: '专业的短剧质量评估助手，从多维度评估剧本质量并提供改进建议',
    category: 'evaluation',
    icon: '📊',
    model: 'glm-4.1v-thinking-flash',
    apiEndpoint: '/juben/evaluation/chat',
    features: [
      '质量评估',
      '多维度打分',
      '改进建议',
      '市场分析'
    ],
    capabilities: [
      '从情节、人物、对话等维度评估剧本',
      '提供详细的评分和改进建议',
      '分析剧本的市场潜力',
      '对比同类优秀作品'
    ],
    inputExample: '请评估我的短剧剧本质量',
    outputExample: '【评估报告】\n综合评分：85/100',
    status: 'active'
  },

  {
    id: 'script_evaluation',
    name: 'ScriptEvaluationAgent',
    displayName: '剧本评估专家',
    description: '深度剧本分析评估，提供专业的质量诊断和优化方案',
    category: 'evaluation',
    icon: '🎯',
    model: 'glm-4.1v-thinking-flash',
    apiEndpoint: '/juben/script/evaluation',
    features: [
      '剧本诊断',
      '质量评分',
      '问题定位',
      '优化方案'
    ],
    capabilities: [
      '深度分析剧本结构和逻辑',
      '识别潜在问题和薄弱环节',
      '提供具体的优化方案',
      '对比行业标准'
    ],
    inputExample: '帮我诊断这个剧本的问题',
    outputExample: '【诊断结果】\n发现3个主要问题...',
    status: 'active'
  },

  {
    id: 'ip_evaluation',
    name: 'IPEvaluationAgent',
    displayName: 'IP价值评估',
    description: '评估IP的商业价值和开发潜力',
    category: 'evaluation',
    icon: '💎',
    model: 'glm-4.1v-thinking-flash',
    apiEndpoint: '/juben/ip/evaluation',
    features: [
      'IP价值评估',
      '市场潜力分析',
      '商业化建议',
      '竞品对比'
    ],
    capabilities: [
      '评估IP的商业价值',
      '分析市场潜力和受众定位',
      '提供IP开发建议',
      '对比同类IP竞品'
    ],
    inputExample: '评估这个故事IP的开发价值',
    outputExample: '【IP评估报告】\n综合评级：A级',
    status: 'beta'
  },

  // ==================== 分析类 ====================
  {
    id: 'story_five_elements',
    name: 'StoryFiveElementsAgent',
    displayName: '故事五元素分析',
    description: '分析故事的核心五元素：人物、情节、环境、主题、风格',
    category: 'analysis',
    icon: '🔍',
    model: 'glm-4-flash',
    apiEndpoint: '/juben/story-analysis/analyze',
    features: [
      '五元素分析',
      '结构梳理',
      '主题提炼',
      '风格识别'
    ],
    capabilities: [
      '深度分析故事五要素',
      '梳理故事结构和脉络',
      '提炼核心主题思想',
      '识别故事风格特征'
    ],
    inputExample: '分析这个故事的核心元素',
    outputExample: '【五元素分析】\n一、人物分析...',
    status: 'active'
  },

  {
    id: 'series_analysis',
    name: 'SeriesAnalysisAgent',
    displayName: '已播剧集分析',
    description: '分析已播剧集的数据和表现，提取成功经验',
    category: 'analysis',
    icon: '📺',
    model: 'glm-4-flash',
    apiEndpoint: '/juben/series-analysis/analyze',
    features: [
      '剧集数据分析',
      '成功要素提取',
      '趋势总结',
      '经验归纳'
    ],
    capabilities: [
      '分析已播剧集的各项数据',
      '提取成功剧集的关键要素',
      '总结行业趋势和规律',
      '归纳可复制的经验'
    ],
    inputExample: '分析《某某短剧》的成功要素',
    outputExample: '【剧集分析报告】\n一、数据概览...',
    status: 'active'
  },

  {
    id: 'drama_analysis',
    name: 'DramaAnalysisAgent',
    displayName: '剧本深度分析',
    description: '对剧本进行深度专业分析，挖掘潜在价值',
    category: 'analysis',
    icon: '🔬',
    model: 'glm-4.1v-thinking-flash',
    apiEndpoint: '/juben/drama/analysis',
    features: [
      '剧本结构分析',
      '人物关系梳理',
      '情节节奏分析',
      '价值挖掘'
    ],
    capabilities: [
      '深度解析剧本结构',
      '梳理复杂人物关系',
      '分析情节节奏变化',
      '挖掘潜在商业价值'
    ],
    inputExample: '深度分析这个剧本',
    outputExample: '【深度分析】\n一、结构分析...',
    status: 'active'
  },

  {
    id: 'story_type_analyzer',
    name: 'StoryTypeAnalyzerAgent',
    displayName: '故事类型分析',
    description: '识别和分析故事类型，提供类型化创作建议',
    category: 'analysis',
    icon: '📚',
    model: 'glm-4-flash',
    apiEndpoint: '/juben/story-type/analyze',
    features: [
      '类型识别',
      '类型特征分析',
      '创作规范建议',
      '市场定位'
    ],
    capabilities: [
      '准确识别故事类型',
      '分析类型的核心特征',
      '提供类型化创作规范',
      '定位目标市场'
    ],
    inputExample: '分析这个故事的类型',
    outputExample: '【类型分析】\n类型：都市爱情 + 悬疑',
    status: 'active'
  },

  // ==================== 工作流类 ====================
  {
    id: 'plot_points_workflow',
    name: 'PlotPointsWorkflowAgent',
    displayName: '情节点工作流',
    description: '完整的大情节点与详细情节点生成工作流',
    category: 'workflow',
    icon: '🔄',
    model: 'glm-4-flash',
    apiEndpoint: '/juben/plot-points-workflow/execute',
    features: [
      '大情节点生成',
      '详细情节点展开',
      '结构化输出',
      '可视化展示'
    ],
    capabilities: [
      '生成完整的大情节点框架',
      '展开详细的情节点内容',
      '提供结构化输出格式',
      '支持可视化展示'
    ],
    inputExample: '生成这个故事的完整情节点',
    outputExample: '【情节点工作流】\n一、大情节点...',
    status: 'active'
  },

  {
    id: 'drama_workflow',
    name: 'DramaWorkflowAgent',
    displayName: '剧本创作工作流',
    description: '端到端的剧本创作工作流，从创意到成品',
    category: 'workflow',
    icon: '🎬',
    model: 'glm-4.7-flash',
    apiEndpoint: '/juben/drama-workflow/execute',
    features: [
      '创意开发',
      '大纲生成',
      '剧本创作',
      '质量检验'
    ],
    capabilities: [
      '从创意开发到剧本成品的完整流程',
      '多阶段质量控制',
      '支持迭代优化',
      '输出标准化剧本'
    ],
    inputExample: '执行完整的剧本创作工作流',
    outputExample: '【工作流执行】\n阶段1：创意开发...',
    status: 'beta'
  },

  // ==================== 人物类 ====================
  {
    id: 'character_profile_generator',
    name: 'CharacterProfileGeneratorAgent',
    displayName: '人物小传生成',
    description: '为故事中的主要人物生成详细的人物小传',
    category: 'character',
    icon: '👤',
    model: 'glm-4-flash',
    apiEndpoint: '/juben/character/profile',
    features: [
      '人物识别',
      '小传生成',
      '性格分析',
      '背景构建'
    ],
    capabilities: [
      '识别故事中的主要人物',
      '生成300-500字的详细小传',
      '分析人物性格特征',
      '构建完整的背景故事'
    ],
    inputExample: '为这个故事生成人物小传',
    outputExample: '【人物小传】\n1. 张三（主角）...',
    status: 'active'
  },

  {
    id: 'character_relationship_analyzer',
    name: 'CharacterRelationshipAnalyzerAgent',
    displayName: '人物关系分析',
    description: '分析故事中人物之间的复杂关系网络',
    category: 'character',
    icon: '👥',
    model: 'glm-4-flash',
    apiEndpoint: '/juben/character/relationship',
    features: [
      '关系识别',
      '关系类型分析',
      '关系网络构建',
      '关系演变追踪'
    ],
    capabilities: [
      '识别各种类型的人物关系',
      '分析关系的性质和强度',
      '构建完整的关系网络',
      '追踪关系的演变过程'
    ],
    inputExample: '分析这个故事中的人物关系',
    outputExample: '【人物关系分析】\n1. 张三 ↔ 李四：恋人关系...',
    status: 'active'
  },

  // ==================== 故事类 ====================
  {
    id: 'story_summary_generator',
    name: 'StorySummaryGeneratorAgent',
    displayName: '故事大纲生成',
    description: '为长篇故事生成精炼的故事大纲',
    category: 'story',
    icon: '📝',
    model: 'glm-4-flash',
    apiEndpoint: '/juben/story/summary',
    features: [
      '内容提取',
      '要点总结',
      '结构梳理',
      '精炼表达'
    ],
    capabilities: [
      '从长文本中提取核心内容',
      '总结故事要点和关键情节',
      '梳理故事结构脉络',
      '生成精炼的故事大纲'
    ],
    inputExample: '为这个故事生成大纲',
    outputExample: '【故事大纲】\n一、故事梗概...',
    status: 'active'
  },

  {
    id: 'detailed_plot_points',
    name: 'DetailedPlotPointsAgent',
    displayName: '详细情节点',
    description: '展开详细的情节点内容，丰富故事细节',
    category: 'story',
    icon: '📍',
    model: 'glm-4-flash',
    apiEndpoint: '/juben/plot-points/detailed',
    features: [
      '情节点展开',
      '细节补充',
      '场景描写',
      '情节衔接'
    ],
    capabilities: [
      '展开简略的情节点',
      '补充丰富的细节内容',
      '添加生动的场景描写',
      '确保情节衔接自然'
    ],
    inputExample: '展开这个情节点',
    outputExample: '【详细情节点】\n情节展开如下...',
    status: 'active'
  },

  {
    id: 'plot_points_analyzer',
    name: 'PlotPointsAnalyzerAgent',
    displayName: '情节点分析',
    description: '分析和优化故事情节点的设计',
    category: 'story',
    icon: '📌',
    model: 'glm-4.1v-thinking-flash',
    apiEndpoint: '/juben/plot-points/analyze',
    features: [
      '情节点识别',
      '结构分析',
      '节奏评估',
      '优化建议'
    ],
    capabilities: [
      '识别故事中的关键情节点',
      '分析情节点结构分布',
      '评估情节节奏',
      '提供优化建议'
    ],
    inputExample: '分析这个故事情节点的设计',
    outputExample: '【情节点分析】\n共识别15个关键情节点...',
    status: 'active'
  },

  {
    id: 'mind_map',
    name: 'MindMapAgent',
    displayName: '思维导图',
    description: '生成故事结构可视化思维导图',
    category: 'story',
    icon: '🧠',
    model: 'glm-4-flash',
    apiEndpoint: '/juben/mind-map/generate',
    features: [
      '结构提取',
      '导图生成',
      '可视化展示',
      '编辑导出'
    ],
    capabilities: [
      '提取故事结构层次',
      '生成可视化思维导图',
      '支持在线编辑',
      '可导出多种格式'
    ],
    inputExample: '为这个故事生成思维导图',
    outputExample: '【思维导图】\n已生成，点击查看',
    status: 'active'
  },

  {
    id: 'major_plot_points',
    name: 'MajorPlotPointsAgent',
    displayName: '大情节点分析',
    description: '分析并提取故事的主要情节点',
    category: 'story',
    icon: '🎬',
    model: 'glm-4-flash',
    apiEndpoint: '/juben/major-plot-points/chat',
    features: [
      '大情节点提取',
      '情节点描述',
      '时间线构建',
      '结构优化'
    ],
    capabilities: [
      '识别故事的核心情节点',
      '提取关键转折点',
      '构建故事时间线',
      '优化情节点结构'
    ],
    inputExample: '分析这个故事的大情节点',
    outputExample: '【大情节点】\n1. 开端：主角登场...',
    status: 'active'
  },

  // ==================== 工具类 ====================
  {
    id: 'websearch',
    name: 'WebSearchAgent',
    displayName: '网络搜索',
    description: '实时搜索网络信息，获取最新资料',
    category: 'utility',
    icon: '🌐',
    model: 'glm-4-flash',
    apiEndpoint: '/juben/websearch/chat',
    features: [
      '实时搜索',
      '信息聚合',
      '来源标注',
      '智能摘要'
    ],
    capabilities: [
      '实时搜索最新信息',
      '聚合多个来源结果',
      '标注信息来源',
      '生成智能摘要'
    ],
    inputExample: '搜索2025年短剧市场趋势',
    outputExample: '【搜索结果】\n找到5条相关信息...',
    status: 'active'
  },

  {
    id: 'knowledge',
    name: 'KnowledgeAgent',
    displayName: '知识库查询',
    description: '查询剧本创作知识库，获取专业资料',
    category: 'utility',
    icon: '📚',
    model: 'glm-4-flash',
    apiEndpoint: '/juben/knowledge/chat',
    features: [
      '知识检索',
      '相似度匹配',
      '专业资料',
      '桥段参考'
    ],
    capabilities: [
      '检索剧本创作专业知识',
      '基于相似度匹配结果',
      '提供权威专业资料',
      '参考优秀作品桥段'
    ],
    inputExample: '查询短剧反转技巧',
    outputExample: '【知识库结果】\n找到相关资料...',
    status: 'active'
  },

  {
    id: 'file_reference',
    name: 'FileReferenceAgent',
    displayName: '文件引用解析',
    description: '解析和引用外部文件内容',
    category: 'utility',
    icon: '📄',
    model: 'glm-4-flash',
    apiEndpoint: '/juben/file-reference/chat',
    features: [
      '文件解析',
      '内容提取',
      '智能引用',
      '格式兼容'
    ],
    capabilities: [
      '解析多种文件格式',
      '提取关键内容',
      '智能引用相关部分',
      '兼容常见文档格式'
    ],
    inputExample: '解析这个剧本文件',
    outputExample: '【解析结果】\n文件内容摘要...',
    status: 'active'
  },

  {
    id: 'document_generator',
    name: 'DocumentGeneratorAgent',
    displayName: '文档生成器',
    description: '生成标准化的剧本文档',
    category: 'utility',
    icon: '📃',
    model: 'glm-4-flash',
    apiEndpoint: '/juben/document/generate',
    features: [
      '格式转换',
      '标准排版',
      '批量生成',
      '导出功能'
    ],
    capabilities: [
      '转换为标准剧本格式',
      '自动排版美化',
      '支持批量生成',
      '导出PDF/Word等格式'
    ],
    inputExample: '生成标准剧本文档',
    outputExample: '【文档已生成】\n下载链接：...',
    status: 'beta'
  },

  {
    id: 'output_formatter',
    name: 'OutputFormatterAgent',
    displayName: '输出格式化',
    description: '格式化AI输出，确保符合规范',
    category: 'utility',
    icon: '✨',
    model: 'glm-4-flash',
    apiEndpoint: '/juben/output/format',
    features: [
      '格式规范',
      '样式统一',
      '错误修正',
      '质量提升'
    ],
    capabilities: [
      '按规范格式化输出',
      '统一样式风格',
      '自动修正格式错误',
      '提升输出质量'
    ],
    inputExample: '格式化这段输出',
    outputExample: '【格式化结果】\n已按规范处理...',
    status: 'active'
  },

  // ==================== 更多评估类 ====================
  {
    id: 'story_evaluation',
    name: 'StoryEvaluationAgent',
    displayName: '故事质量评估',
    description: '评估故事的整体质量和吸引力',
    category: 'evaluation',
    icon: '⭐',
    model: 'glm-4.1v-thinking-flash',
    apiEndpoint: '/juben/story/evaluation',
    features: [
      '质量打分',
      '吸引力分析',
      '改进建议',
      '对比评估'
    ],
    capabilities: [
      '对故事质量进行多维度打分',
      '分析故事吸引力要素',
      '提供具体改进建议',
      '与优秀作品对比评估'
    ],
    inputExample: '评估这个故事的质量',
    outputExample: '【质量评估】\n综合评分：88/100...',
    status: 'active'
  },

  {
    id: 'story_outline_evaluation',
    name: 'StoryOutlineEvaluationAgent',
    displayName: '大纲评估',
    description: '评估故事大纲的完整性和可行性',
    category: 'evaluation',
    icon: '📋',
    model: 'glm-4.1v-thinking-flash',
    apiEndpoint: '/juben/outline/evaluation',
    features: [
      '完整性检查',
      '可行性评估',
      '结构调整',
      '补充建议'
    ],
    capabilities: [
      '检查大纲结构完整性',
      '评估创作可行性',
      '提供结构调整建议',
      '指出需要补充的部分'
    ],
    inputExample: '评估这个故事大纲',
    outputExample: '【大纲评估】\n结构完整性：85%...',
    status: 'active'
  },

  {
    id: 'novel_screening_evaluation',
    name: 'NovelScreeningEvaluationAgent',
    displayName: '小说筛选评估',
    description: '评估小说是否适合改编为短剧',
    category: 'evaluation',
    icon: '📖',
    model: 'glm-4.1v-thinking-flash',
    apiEndpoint: '/juben/novel/screening',
    features: [
      '改编可行性',
      'IP价值评估',
      '改编建议',
      '版权分析'
    ],
    capabilities: [
      '评估小说改编短剧的可行性',
      '分析IP的商业价值',
      '提供专业改编建议',
      '分析版权相关事项'
    ],
    inputExample: '评估这本小说的改编价值',
    outputExample: '【改编评估】\n改编可行性：高...',
    status: 'active'
  },

  // ==================== 更多工具类 ====================
  {
    id: 'series_info',
    name: 'SeriesInfoAgent',
    displayName: '剧集信息提取',
    description: '从文本中提取剧集相关信息',
    category: 'utility',
    icon: '📺',
    model: 'glm-4-flash',
    apiEndpoint: '/juben/series/info',
    features: [
      '信息提取',
      '数据整理',
      '格式规范',
      '批量处理'
    ],
    capabilities: [
      '智能提取剧集关键信息',
      '整理结构化数据',
      '规范化输出格式',
      '支持批量处理'
    ],
    inputExample: '提取这部剧的信息',
    outputExample: '【剧集信息】\n剧名：XXX...',
    status: 'active'
  },

  {
    id: 'series_name_extractor',
    name: 'SeriesNameExtractorAgent',
    displayName: '剧名提取',
    description: '智能识别和提取短剧名称',
    category: 'utility',
    icon: '🏷️',
    model: 'glm-4-flash',
    apiEndpoint: '/juben/series/name',
    features: [
      '名称识别',
      '别名提取',
      '规范化处理',
      '去重过滤'
    ],
    capabilities: [
      '准确识别短剧名称',
      '提取别名和简称',
      '规范化名称格式',
      '过滤重复内容'
    ],
    inputExample: '从文本中提取短剧名称',
    outputExample: '【提取结果】\n识别到3个剧名...',
    status: 'active'
  },

  {
    id: 'text_splitter',
    name: 'TextSplitterAgent',
    displayName: '文本分割',
    description: '智能分割长文本为合适的段落',
    category: 'utility',
    icon: '✂️',
    model: 'glm-4-flash',
    apiEndpoint: '/juben/text/split',
    features: [
      '智能分割',
      '长度控制',
      '语义完整',
      '边界识别'
    ],
    capabilities: [
      '智能识别分割边界',
      '控制段落长度',
      '保持语义完整性',
      '识别章节场景边界'
    ],
    inputExample: '分割这个长文本',
    outputExample: '【分割结果】\n共5个段落...',
    status: 'active'
  },

  {
    id: 'text_truncator',
    name: 'TextTruncatorAgent',
    displayName: '文本截断',
    description: '按要求截断文本并保持完整性',
    category: 'utility',
    icon: '✂️',
    model: 'glm-4-flash',
    apiEndpoint: '/juben/text/truncate',
    features: [
      '长度截断',
      '完整性保证',
      '摘要保留',
      '边界优化'
    ],
    capabilities: [
      '按指定长度截断',
      '保证截断处语义完整',
      '保留关键摘要信息',
      '优化截断边界位置'
    ],
    inputExample: '截断这段文本到500字',
    outputExample: '【截断结果】\n已截断至500字...',
    status: 'active'
  },

  // ==================== 结果处理类 ====================
  {
    id: 'result_analyzer_evaluation',
    name: 'ResultAnalyzerEvaluationAgent',
    displayName: '结果分析评估',
    description: '分析评估结果，提供洞察',
    category: 'evaluation',
    icon: '📊',
    model: 'glm-4.1v-thinking-flash',
    apiEndpoint: '/juben/result/analyze',
    features: [
      '结果分析',
      '数据洞察',
      '趋势发现',
      '建议生成'
    ],
    capabilities: [
      '深度分析评估结果',
      '提取数据洞察',
      '发现隐藏趋势',
      '生成改进建议'
    ],
    inputExample: '分析这些评估结果',
    outputExample: '【分析报告】\n关键洞察：...',
    status: 'active'
  },

  {
    id: 'result_integrator',
    name: 'ResultIntegratorAgent',
    displayName: '结果集成器',
    description: '集成多个Agent的结果',
    category: 'workflow',
    icon: '🔗',
    model: 'glm-4-flash',
    apiEndpoint: '/juben/result/integrate',
    features: [
      '结果聚合',
      '格式统一',
      '去重合并',
      '优先级排序'
    ],
    capabilities: [
      '聚合多个Agent输出',
      '统一结果格式',
      '去重和合并内容',
      '按优先级排序'
    ],
    inputExample: '集成多个Agent的结果',
    outputExample: '【集成结果】\n已整合5个来源...',
    status: 'active'
  },

  {
    id: 'score_analyzer',
    name: 'ScoreAnalyzerAgent',
    displayName: '评分分析器',
    description: '分析评分数据，提供解读',
    category: 'evaluation',
    icon: '📈',
    model: 'glm-4.1v-thinking-flash',
    apiEndpoint: '/juben/score/analyze',
    features: [
      '评分统计',
      '分布分析',
      '趋势解读',
      '对比分析'
    ],
    capabilities: [
      '统计分析评分数据',
      '分析评分分布',
      '解读评分趋势',
      '对比历史数据'
    ],
    inputExample: '分析这些评分数据',
    outputExample: '【评分分析】\n平均分：85...',
    status: 'active'
  },

  {
    id: 'text_processor_evaluation',
    name: 'TextProcessorEvaluationAgent',
    displayName: '文本处理评估',
    description: '评估文本处理的质量和效果',
    category: 'evaluation',
    icon: '📝',
    model: 'glm-4-flash',
    apiEndpoint: '/juben/chat',
    features: [
      '质量评估',
      '效果分析',
      '问题识别',
      '改进建议'
    ],
    capabilities: [
      '评估文本处理质量',
      '分析处理效果',
      '识别潜在问题',
      '提供改进建议'
    ],
    inputExample: '评估这段文本处理的效果',
    outputExample: '【处理评估】\n质量得分：90...',
    status: 'active'
  },
];

/**
 * 按分类获取 Agents
 */
export function getAgentsByCategory(category: AgentCategory): AgentConfig[] {
  return AGENTS_CONFIG.filter(agent => agent.category === category);
}

/**
 * 根据 ID 获取 Agent
 */
export function getAgentById(id: string): AgentConfig | undefined {
  return AGENTS_CONFIG.find(agent => agent.id === id);
}

/**
 * 获取激活的 Agents
 */
export function getActiveAgents(): AgentConfig[] {
  return AGENTS_CONFIG.filter(agent => agent.status === 'active');
}

/**
 * 获取 Agent 分类列表
 */
export function getAgentCategories(): { category: AgentCategory; name: string; icon: string }[] {
  return [
    { category: 'planning', name: '策划类', icon: '📋' },
    { category: 'creation', name: '创作类', icon: '✍️' },
    { category: 'evaluation', name: '评估类', icon: '📊' },
    { category: 'analysis', name: '分析类', icon: '🔍' },
    { category: 'workflow', name: '工作流', icon: '🔄' },
    { category: 'character', name: '人物类', icon: '👤' },
    { category: 'story', name: '故事类', icon: '📖' },
    { category: 'utility', name: '工具类', icon: '🛠️' },
  ];
}

/**
 * 搜索 Agents
 */
export function searchAgents(query: string): AgentConfig[] {
  const lowerQuery = query.toLowerCase();
  return AGENTS_CONFIG.filter(agent =>
    agent.name.toLowerCase().includes(lowerQuery) ||
    agent.displayName.toLowerCase().includes(lowerQuery) ||
    agent.description.toLowerCase().includes(lowerQuery) ||
    agent.features.some(f => f.toLowerCase().includes(lowerQuery))
  );
}
