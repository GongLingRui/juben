"""
意图识别工具
用于识别用户输入是否需要联网查询或知识库检索
"""

import re
from typing import Dict, Any, List


class IntentRecognizer:
    """意图识别器"""
    
    def __init__(self):
        # 联网查询关键词
        self.web_search_keywords = [
            "最新", "新闻", "热点", "趋势", "市场", "数据", "统计", "报告",
            "今天", "最近", "当前", "现在", "实时", "更新", "动态",
            "搜索", "查找", "查询", "了解", "知道", "获取"
        ]
        
        # 知识库查询关键词
        self.knowledge_keywords = [
            "创作", "编剧", "剧本", "故事", "情节", "人物", "角色", "对话",
            "技巧", "方法", "理论", "原则", "经验", "建议", "指导",
            "短剧", "策划", "制作", "拍摄", "导演", "演员", "表演",
            "结构", "节奏", "冲突", "高潮", "结局", "开头", "结尾"
        ]
        
        # 文件引用关键词
        self.file_reference_keywords = [
            "文件", "文档", "图片", "视频", "音频", "PDF", "Word", "Excel",
            "上传", "附件", "资料", "素材", "内容", "文本"
        ]
    
    async def analyze(self, user_input: str) -> Dict[str, Any]:
        """分析用户意图"""
        if not user_input:
            return {
                "intent": "unknown",
                "confidence": 0.0,
                "needs_web_search": False,
                "needs_knowledge_base": False,
                "has_file_references": False
            }
        
        # 检测文件引用
        has_file_references = self._detect_file_references(user_input)
        
        # 检测联网查询意图
        needs_web_search = self._detect_web_search_intent(user_input)
        
        # 检测知识库查询意图
        needs_knowledge_base = self._detect_knowledge_base_intent(user_input)
        
        # 确定主要意图
        intent = self._determine_primary_intent(user_input, needs_web_search, needs_knowledge_base, has_file_references)
        
        # 计算置信度
        confidence = self._calculate_confidence(user_input, intent)
        
        return {
            "intent": intent,
            "confidence": confidence,
            "needs_web_search": needs_web_search,
            "needs_knowledge_base": needs_knowledge_base,
            "has_file_references": has_file_references,
            "user_input": user_input
        }
    
    def _detect_file_references(self, text: str) -> bool:
        """检测文件引用"""
        if not text:
            return False
        
        # 检测@符号引用
        at_ref_pattern = r'@(file\d+|image\d+|document\d+|pdf\d+|excel\d+|audio\d+|video\d+)'
        if re.search(at_ref_pattern, text, re.IGNORECASE):
            return True
        
        # 检测自然语言引用
        natural_patterns = [
            r"第([一二三四五六七八九十\d]+)个文件",
            r"最新上传的(.+)",
            r"刚才上传的(.+)",
            r"那个(.+)文件",
            r"我的(.+)文件",
            r"(.+)文件"
        ]
        
        for pattern in natural_patterns:
            if re.search(pattern, text):
                return True
        
        return False
    
    def _detect_web_search_intent(self, text: str) -> bool:
        """检测联网查询意图"""
        if not text:
            return False
        
        text_lower = text.lower()
        
        # 检查联网查询关键词
        for keyword in self.web_search_keywords:
            if keyword in text_lower:
                return True
        
        # 检查特定模式
        web_patterns = [
            r"搜索.*?信息",
            r"查找.*?资料",
            r"了解.*?最新",
            r"获取.*?数据",
            r"查询.*?内容"
        ]
        
        for pattern in web_patterns:
            if re.search(pattern, text):
                return True
        
        return False
    
    def _detect_knowledge_base_intent(self, text: str) -> bool:
        """检测知识库查询意图"""
        if not text:
            return False
        
        text_lower = text.lower()
        
        # 检查知识库关键词
        for keyword in self.knowledge_keywords:
            if keyword in text_lower:
                return True
        
        # 检查特定模式
        knowledge_patterns = [
            r"如何.*?创作",
            r"怎样.*?编剧",
            r"怎么.*?写",
            r"创作.*?技巧",
            r"编剧.*?方法",
            r"短剧.*?策划"
        ]
        
        for pattern in knowledge_patterns:
            if re.search(pattern, text):
                return True
        
        return False
    
    def _determine_primary_intent(self, text: str, needs_web_search: bool, needs_knowledge_base: bool, has_file_references: bool) -> str:
        """确定主要意图"""
        if has_file_references:
            return "file_reference"
        elif needs_web_search and needs_knowledge_base:
            return "comprehensive_assistance"
        elif needs_web_search:
            return "web_search"
        elif needs_knowledge_base:
            return "knowledge_base"
        else:
            return "creation_assistance"
    
    def _calculate_confidence(self, text: str, intent: str) -> float:
        """计算置信度"""
        if not text:
            return 0.0
        
        confidence = 0.5  # 基础置信度
        
        # 根据意图类型调整置信度
        if intent == "file_reference":
            # 文件引用意图的置信度计算
            file_keywords = ["文件", "文档", "上传", "附件"]
            for keyword in file_keywords:
                if keyword in text:
                    confidence += 0.1
        elif intent == "web_search":
            # 联网查询意图的置信度计算
            web_keywords = ["最新", "新闻", "热点", "搜索", "查询"]
            for keyword in web_keywords:
                if keyword in text:
                    confidence += 0.1
        elif intent == "knowledge_base":
            # 知识库查询意图的置信度计算
            knowledge_keywords = ["创作", "编剧", "技巧", "方法", "指导"]
            for keyword in knowledge_keywords:
                if keyword in text:
                    confidence += 0.1
        elif intent == "creation_assistance":
            # 创作辅助意图的置信度计算
            creation_keywords = ["短剧", "策划", "故事", "剧本", "人物"]
            for keyword in creation_keywords:
                if keyword in text:
                    confidence += 0.1
        
        # 限制置信度范围
        return min(max(confidence, 0.0), 1.0)
    
    def get_intent_explanation(self, intent: str) -> str:
        """获取意图说明"""
        explanations = {
            "file_reference": "检测到文件引用，将解析文件内容",
            "web_search": "检测到需要联网查询，将搜索最新信息",
            "knowledge_base": "检测到需要专业知识，将查询知识库",
            "comprehensive_assistance": "检测到需要综合帮助，将同时使用联网搜索和知识库",
            "creation_assistance": "检测到创作需求，将提供专业创作指导",
            "unknown": "无法确定具体意图，将提供通用帮助"
        }
        
        return explanations.get(intent, "未知意图")