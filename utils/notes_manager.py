"""
Juben Notes管理器
 ，提供统一的Notes系统管理
"""
import asyncio
import logging
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import json

try:
    from .logger import JubenLogger
    from .storage_manager import get_storage
except ImportError:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    
    from utils.logger import JubenLogger
    from utils.storage_manager import get_storage


class JubenNotesManager:
    """
    Juben Notes管理器
    
    核心功能：
    1. Notes的创建、读取、更新、删除
    2. Notes的分类和标签管理
    3. Notes的搜索和检索
    4. Notes的版本管理
    5. Notes的引用和关联
    """
    
    def __init__(self):
        self.logger = JubenLogger("NotesManager")
        self.storage = get_storage()
        self._notes_cache = {}  # 内存缓存
        
        self.logger.info("Notes管理器初始化完成")
    
    async def create_note(self, user_id: str, session_id: str, title: str, content: str,
                         note_type: str = "general", tags: List[str] = None,
                         metadata: Dict[str, Any] = None) -> str:
        """
        创建新的Note
        
        Args:
            user_id: 用户ID
            session_id: 会话ID
            title: 标题
            content: 内容
            note_type: 类型
            tags: 标签列表
            metadata: 元数据
            
        Returns:
            str: Note ID
        """
        try:
            note_id = str(uuid.uuid4())
            note_data = {
                "note_id": note_id,
                "user_id": user_id,
                "session_id": session_id,
                "title": title,
                "content": content,
                "note_type": note_type,
                "tags": tags or [],
                "metadata": metadata or {},
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "version": 1
            }
            
            # 保存到数据库
            await self.storage.save_note(note_data)
            
            # 更新缓存
            cache_key = f"{user_id}:{session_id}"
            if cache_key not in self._notes_cache:
                self._notes_cache[cache_key] = {}
            self._notes_cache[cache_key][note_id] = note_data
            
            self.logger.info(f"✅ 创建Note成功: {note_id}")
            return note_id
            
        except Exception as e:
            self.logger.error(f"❌ 创建Note失败: {e}")
            raise
    
    async def get_note(self, note_id: str, user_id: str = None) -> Optional[Dict[str, Any]]:
        """
        获取单个Note
        
        Args:
            note_id: Note ID
            user_id: 用户ID（可选，用于权限检查）
            
        Returns:
            Dict: Note数据
        """
        try:
            note_data = await self.storage.get_note(note_id, user_id)
            if note_data:
                self.logger.debug(f"✅ 获取Note成功: {note_id}")
            return note_data
            
        except Exception as e:
            self.logger.error(f"❌ 获取Note失败: {e}")
            return None
    
    async def get_notes(self, user_id: str, session_id: str = None,
                       note_type: str = None, tags: List[str] = None,
                       limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """
        获取Notes列表
        
        Args:
            user_id: 用户ID
            session_id: 会话ID（可选）
            note_type: 类型过滤（可选）
            tags: 标签过滤（可选）
            limit: 限制数量
            offset: 偏移量
            
        Returns:
            List[Dict]: Notes列表
        """
        try:
            notes = await self.storage.get_notes(
                user_id=user_id,
                session_id=session_id,
                note_type=note_type,
                tags=tags,
                limit=limit,
                offset=offset
            )
            
            self.logger.debug(f"✅ 获取Notes成功: {len(notes)}条")
            return notes
            
        except Exception as e:
            self.logger.error(f"❌ 获取Notes失败: {e}")
            return []
    
    async def update_note(self, note_id: str, user_id: str, updates: Dict[str, Any]) -> bool:
        """
        更新Note
        
        Args:
            note_id: Note ID
            user_id: 用户ID
            updates: 更新数据
            
        Returns:
            bool: 是否成功
        """
        try:
            # 获取现有Note
            existing_note = await self.get_note(note_id, user_id)
            if not existing_note:
                self.logger.warning(f"Note不存在: {note_id}")
                return False
            
            # 合并更新数据
            updated_note = {**existing_note, **updates}
            updated_note["updated_at"] = datetime.now(timezone.utc).isoformat()
            updated_note["version"] = existing_note.get("version", 1) + 1
            
            # 保存更新
            await self.storage.update_note(note_id, updated_note, user_id)
            
            # 更新缓存
            cache_key = f"{user_id}:{existing_note.get('session_id', '')}"
            if cache_key in self._notes_cache and note_id in self._notes_cache[cache_key]:
                self._notes_cache[cache_key][note_id] = updated_note
            
            self.logger.info(f"✅ 更新Note成功: {note_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 更新Note失败: {e}")
            return False
    
    async def delete_note(self, note_id: str, user_id: str) -> bool:
        """
        删除Note
        
        Args:
            note_id: Note ID
            user_id: 用户ID
            
        Returns:
            bool: 是否成功
        """
        try:
            # 获取现有Note信息用于清理缓存
            existing_note = await self.get_note(note_id, user_id)
            
            # 删除Note
            await self.storage.delete_note(note_id, user_id)
            
            # 清理缓存
            if existing_note:
                cache_key = f"{user_id}:{existing_note.get('session_id', '')}"
                if cache_key in self._notes_cache and note_id in self._notes_cache[cache_key]:
                    del self._notes_cache[cache_key][note_id]
            
            self.logger.info(f"✅ 删除Note成功: {note_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 删除Note失败: {e}")
            return False
    
    async def search_notes(self, user_id: str, query: str, session_id: str = None,
                          note_type: str = None, tags: List[str] = None,
                          limit: int = 50) -> List[Dict[str, Any]]:
        """
        搜索Notes
        
        Args:
            user_id: 用户ID
            query: 搜索查询
            session_id: 会话ID（可选）
            note_type: 类型过滤（可选）
            tags: 标签过滤（可选）
            limit: 限制数量
            
        Returns:
            List[Dict]: 搜索结果
        """
        try:
            results = await self.storage.search_notes(
                user_id=user_id,
                query=query,
                session_id=session_id,
                note_type=note_type,
                tags=tags,
                limit=limit
            )
            
            self.logger.info(f"✅ 搜索Notes成功: 查询='{query}', 结果={len(results)}条")
            return results
            
        except Exception as e:
            self.logger.error(f"❌ 搜索Notes失败: {e}")
            return []
    
    async def get_note_tags(self, user_id: str, session_id: str = None) -> List[str]:
        """
        获取用户的所有标签
        
        Args:
            user_id: 用户ID
            session_id: 会话ID（可选）
            
        Returns:
            List[str]: 标签列表
        """
        try:
            tags = await self.storage.get_note_tags(user_id, session_id)
            self.logger.debug(f"✅ 获取标签成功: {len(tags)}个")
            return tags
            
        except Exception as e:
            self.logger.error(f"❌ 获取标签失败: {e}")
            return []
    
    async def get_note_types(self, user_id: str, session_id: str = None) -> List[str]:
        """
        获取用户的所有Note类型
        
        Args:
            user_id: 用户ID
            session_id: 会话ID（可选）
            
        Returns:
            List[str]: 类型列表
        """
        try:
            types = await self.storage.get_note_types(user_id, session_id)
            self.logger.debug(f"✅ 获取类型成功: {len(types)}个")
            return types
            
        except Exception as e:
            self.logger.error(f"❌ 获取类型失败: {e}")
            return []
    
    def clear_cache(self, user_id: str, session_id: str = None):
        """清理缓存"""
        if session_id:
            cache_key = f"{user_id}:{session_id}"
            if cache_key in self._notes_cache:
                del self._notes_cache[cache_key]
                self.logger.debug(f"✅ 清理缓存成功: {cache_key}")
        else:
            # 清理用户的所有缓存
            keys_to_remove = [key for key in self._notes_cache.keys() if key.startswith(f"{user_id}:")]
            for key in keys_to_remove:
                del self._notes_cache[key]
            self.logger.debug(f"✅ 清理用户缓存成功: {user_id}, {len(keys_to_remove)}个会话")


# 全局实例
_notes_manager = None

def get_notes_manager() -> JubenNotesManager:
    """获取Notes管理器实例"""
    global _notes_manager
    if _notes_manager is None:
        _notes_manager = JubenNotesManager()
    return _notes_manager
