/**
 * Markdown 处理工具
 */

/**
 * 提取代码块语言
 */
export function extractCodeBlockLanguage(markdown: string): string | null {
  const match = markdown.match(/^```(\w+)?/m);
  return match ? (match[1] || 'text') : null;
}

/**
 * 检查是否包含代码块
 */
export function hasCodeBlock(text: string): boolean {
  return /```[\s\S]*```/.test(text) || /^```[\s\S]*$/.test(text);
}

/**
 * 检查是否包含 Markdown 语法
 */
export function hasMarkdownSyntax(text: string): boolean {
  return /(^|[^\\])[#*_`\-\[\]()]/.test(text);
}

/**
 * 提取纯文本（移除 Markdown 格式）
 */
export function stripMarkdown(markdown: string): string {
  return markdown
    // 移除代码块
    .replace(/```[\s\S]*?```/g, '')
    // 移除行内代码
    .replace(/`[^`]+`/g, '')
    // 移除加粗
    .replace(/\*\*([^*]+)\*\*/g, '$1')
    // 移除斜体
    .replace(/\*([^*]+)\*/g, '$1')
    // 移除标题
    .replace(/^#+\s+/gm, '')
    // 移除链接
    .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
    // 移除多余的换行
    .replace(/\n{3,}/g, '\n\n')
    .trim();
}

/**
 * 转换为纯文本摘要
 */
export function markdownToSummary(markdown: string, maxLength: number = 200): string {
  const plainText = stripMarkdown(markdown);
  if (plainText.length <= maxLength) return plainText;
  return plainText.slice(0, maxLength) + '...';
}

/**
 * 验证 Markdown 语法
 */
export function validateMarkdown(markdown: string): {
  valid: boolean;
  errors: string[];
} {
  const errors: string[] = [];

  // 检查未闭合的代码块
  const codeBlocks = markdown.match(/```/g);
  if (codeBlocks && codeBlocks.length % 2 !== 0) {
    errors.push('存在未闭合的代码块');
  }

  // 检查未闭合的行内代码
  const inlineCodes = markdown.match(/`/g);
  if (inlineCodes && inlineCodes.length % 2 !== 0) {
    errors.push('存在未闭合的行内代码');
  }

  // 检查链接格式
  const links = markdown.match(/\[([^\]]+)\](\([^)]*\))?/g);
  if (links) {
    links.forEach(link => {
      if (!link.endsWith(')')) {
        errors.push(`链接格式错误: ${link}`);
      }
    });
  }

  return {
    valid: errors.length === 0,
    errors,
  };
}

/**
 * 统计 Markdown 内容
 */
export function analyzeMarkdown(markdown: string): {
  characters: number;
  words: number;
  lines: number;
  codeBlocks: number;
  links: number;
  images: number;
} {
  return {
    characters: markdown.length,
    words: markdown.split(/\s+/).filter(w => w.length > 0).length,
    lines: markdown.split('\n').length,
    codeBlocks: (markdown.match(/```/g) || []).length / 2,
    links: (markdown.match(/!\[([^\]]+)\]\([^)]+\)/g) || []).length,
    images: (markdown.match(/\[([^\]]+)\]\([^)]+\)/g) || []).length,
  };
}
