/**
 * 知识库服务
 * 提供知识库文档管理的 API 调用
 */

import { api } from './api';

// ==================== 类型定义 ====================

export interface KnowledgeDocument {
  id: string;
  title: string;
  content: string;
  category: string;
  tags: string[];
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
  indexed: boolean;
  size: number;
  indexed_at?: string;
}

export interface CollectionInfo {
  name: string;
  description: string;
  count: number;
  dimension: number;
  indexed_at?: string;
}

export interface SearchResult {
  results: KnowledgeDocument[];
  total: number;
  query: string;
}

export interface KnowledgeStats {
  documents: {
    total: number;
    indexed: number;
    unindexed: number;
    total_size: number;
  };
  categories: {
    total: number;
    list: Array<{ name: string; count: number }>;
  };
  tags: {
    total: number;
    list: Array<{ name: string; count: number }>;
  };
  vectors: {
    total_collections: number;
    total_vectors: number;
  };
}

// ==================== 知识库服务类 ====================

class KnowledgeService {
  private basePath = '/juben/knowledge';

  /**
   * 列出所有集合
   */
  async listCollections(): Promise<{ collections: CollectionInfo[]; total: number }> {
    const response = await api.get<{ success: boolean; data: { collections: CollectionInfo[]; total: number } }>(
      `${this.basePath}/collections`
    );
    return response.data;
  }

  /**
   * 列出文档
   */
  async listDocuments(params?: {
    category?: string;
    tags?: string[];
    indexed?: boolean;
    page?: number;
    page_size?: number;
  }): Promise<{ documents: KnowledgeDocument[]; total: number; page: number; page_size: number }> {
    const queryParams = new URLSearchParams();
    if (params?.category) queryParams.append('category', params.category);
    if (params?.indexed !== undefined) queryParams.append('indexed', String(params.indexed));
    if (params?.tags?.length) params.tags.forEach(tag => queryParams.append('tags', tag));
    if (params?.page) queryParams.append('page', String(params.page));
    if (params?.page_size) queryParams.append('page_size', String(params.page_size));

    const queryString = queryParams.toString();
    const url = queryString ? `${this.basePath}/documents?${queryString}` : `${this.basePath}/documents`;

    const response = await api.get<{ success: boolean; data: { documents: KnowledgeDocument[]; total: number; page: number; page_size: number } }>(url);
    return response.data;
  }

  /**
   * 获取文档详情
   */
  async getDocument(documentId: string): Promise<KnowledgeDocument> {
    const response = await api.get<{ success: boolean; data: KnowledgeDocument }>(
      `${this.basePath}/documents/${documentId}`
    );
    return response.data;
  }

  /**
   * 创建文档
   */
  async createDocument(data: {
    title: string;
    content: string;
    category?: string;
    tags?: string[];
    metadata?: Record<string, unknown>;
  }): Promise<KnowledgeDocument> {
    const response = await api.post<{ success: boolean; data: KnowledgeDocument }>(
      `${this.basePath}/documents`,
      data
    );
    return response.data;
  }

  /**
   * 更新文档
   */
  async updateDocument(
    documentId: string,
    data: {
      title?: string;
      content?: string;
      category?: string;
      tags?: string[];
      metadata?: Record<string, unknown>;
    }
  ): Promise<KnowledgeDocument> {
    const response = await api.put<{ success: boolean; data: KnowledgeDocument }>(
      `${this.basePath}/documents/${documentId}`,
      data
    );
    return response.data;
  }

  /**
   * 删除文档
   */
  async deleteDocument(documentId: string): Promise<{ success: boolean; message: string }> {
    return api.delete<{ success: boolean; message: string }>(
      `${this.basePath}/documents/${documentId}`
    );
  }

  /**
   * 批量删除文档
   */
  async batchDeleteDocuments(documentIds: string[]): Promise<{
    success: boolean;
    message: string;
    data: { deleted_count: number; total: number; errors: string[] };
  }> {
    return api.post<{
      success: boolean;
      message: string;
      data: { deleted_count: number; total: number; errors: string[] };
    }>(`${this.basePath}/documents/batch-delete`, { document_ids: documentIds });
  }

  /**
   * 上传文档文件
   */
  async uploadDocument(file: File, options?: {
    title?: string;
    category?: string;
    tags?: string;
    auto_index?: boolean;
  }): Promise<KnowledgeDocument> {
    const formData = new FormData();
    formData.append('file', file);
    if (options?.title) formData.append('title', options.title);
    if (options?.category) formData.append('category', options.category);
    if (options?.tags) formData.append('tags', options.tags);
    if (options?.auto_index !== undefined) formData.append('auto_index', String(options.auto_index));

    const authHeader = this.getAuthHeader();
    const url = `${api['baseURL'] || 'http://localhost:8000'}${this.basePath}/upload`;

    const response = await fetch(url, {
      method: 'POST',
      headers: {
        ...(authHeader ? { Authorization: authHeader } : {}),
      },
      body: formData,
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`HTTP ${response.status}: ${errorText}`);
    }

    const result = await response.json();
    return result.data;
  }

  /**
   * 索引文档
   */
  async indexDocuments(documentIds: string[], reindex = true): Promise<{
    success: boolean;
    message: string;
    data: { task_id: string; document_count: number };
  }> {
    return api.post<{
      success: boolean;
      message: string;
      data: { task_id: string; document_count: number };
    }>(`${this.basePath}/index`, { document_ids: documentIds, reindex });
  }

  /**
   * 搜索文档
   */
  async searchDocuments(params: {
    query: string;
    collection?: string;
    top_k?: number;
    filter_tags?: string[];
    filter_category?: string;
  }): Promise<SearchResult> {
    const response = await api.post<{ success: boolean; data: SearchResult }>(
      `${this.basePath}/search`,
      params
    );
    return response.data;
  }

  /**
   * 列出分类
   */
  async listCategories(): Promise<{ categories: Array<{ name: string; count: number }>; total: number }> {
    const response = await api.get<{ success: boolean; data: { categories: Array<{ name: string; count: number }>; total: number } }>(
      `${this.basePath}/categories`
    );
    return response.data;
  }

  /**
   * 列出标签
   */
  async listTags(): Promise<{ tags: Array<{ name: string; count: number }>; total: number }> {
    const response = await api.get<{ success: boolean; data: { tags: Array<{ name: string; count: number }>; total: number } }>(
      `${this.basePath}/tags`
    );
    return response.data;
  }

  /**
   * 获取统计信息
   */
  async getStats(): Promise<KnowledgeStats> {
    const response = await api.get<{ success: boolean; data: KnowledgeStats }>(
      `${this.basePath}/stats`
    );
    return response.data;
  }

  /**
   * 获取认证头
   */
  private getAuthHeader(): string | null {
    try {
      const raw = localStorage.getItem('auth-storage');
      if (!raw) return null;
      const parsed = JSON.parse(raw);
      const token = parsed?.state?.tokens?.accessToken;
      return token ? `Bearer ${token}` : null;
    } catch {
      return null;
    }
  }
}

// 导出单例
export const knowledgeService = new KnowledgeService();
export default knowledgeService;
