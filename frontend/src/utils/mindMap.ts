export type MindMapNode = {
  name: string;
  children?: MindMapNode[];
};

export type MindMapData = {
  title: string;
  nodes: MindMapNode[];
};

export function parseMindMap(content: string | any): MindMapData | null {
  if (!content) return null;

  // 尝试从 string 内容中提取 JSON（兼容 ```json 代码块）
  const parseFromString = (raw: string): any | null => {
    if (!raw) return null;
    let text = raw.trim();

    // 优先从 ```json ... ``` 代码块里提取
    const fenceMatch = text.match(/```(?:json)?\s*([\s\S]*?)```/i);
    text = fenceMatch ? fenceMatch[1].trim() : text;

    // 有些返回会是 "json\n{...}" 这样的前缀，先去掉
    if (text.toLowerCase().startsWith('json')) {
      text = text.slice(4).trimStart();
    }

    try {
      return JSON.parse(text);
    } catch {
      // 如果前后有提示语，尝试从第一个 "{" 到最后一个 "}" 截取为 JSON
      const firstBrace = text.indexOf('{');
      const lastBrace = text.lastIndexOf('}');
      if (firstBrace !== -1 && lastBrace > firstBrace) {
        const candidate = text.slice(firstBrace, lastBrace + 1);
        try {
          return JSON.parse(candidate);
        } catch {
          return null;
        }
      }
      return null;
    }
  };

  // 如果本身就是对象，先直接检查
  if (typeof content === 'object') {
    const obj = content as any;

    // 如果已经是标准的 MindMapData 结构
    if (obj.title && Array.isArray(obj.nodes)) {
      // 如果还带有 raw 字段，优先从 raw 解析真正的思维导图
      if (typeof obj.raw === 'string') {
        const inner = parseMindMap(obj.raw);
        if (inner) return inner;
      }
      return obj as MindMapData;
    }

    // 如果只有 raw 字段，则从 raw 继续解析
    if (typeof obj.raw === 'string') {
      return parseMindMap(obj.raw);
    }

    return null;
  }

  if (typeof content !== 'string') return null;

  const data = parseFromString(content);
  if (!data) return null;

  // 解析出的对象如果带有 raw，再尝试深一层
  if (data && typeof data === 'object') {
    if (data.title && Array.isArray(data.nodes)) {
      if (typeof (data as any).raw === 'string') {
        const inner = parseMindMap((data as any).raw);
        if (inner) return inner;
      }
      return data as MindMapData;
    }

    if (typeof (data as any).raw === 'string') {
      return parseMindMap((data as any).raw);
    }
  }

  return null;
}

export function toMarkdownTree(data: MindMapData): string {
  const lines: string[] = [];
  lines.push(`# ${data.title}`);
  const walk = (nodes: MindMapNode[], depth: number) => {
    nodes.forEach((node) => {
      lines.push(`${'  '.repeat(depth)}- ${node.name}`);
      if (node.children && node.children.length > 0) {
        walk(node.children, depth + 1);
      }
    });
  };
  walk(data.nodes, 0);
  return lines.join('\n');
}

const sanitize = (value: string) => value.replace(/\r?\n/g, ' ').trim();

export function toMermaidMindMap(data: MindMapData): string {
  const lines: string[] = [];
  lines.push('mindmap');
  lines.push(`  root((${sanitize(data.title)}))`);
  const walk = (nodes: MindMapNode[], depth: number) => {
    nodes.forEach((node) => {
      const indent = '  '.repeat(depth + 1);
      lines.push(`${indent}${sanitize(node.name)}`);
      if (node.children && node.children.length > 0) {
        walk(node.children, depth + 1);
      }
    });
  };
  walk(data.nodes, 1);
  return lines.join('\n');
}

export function toMarkmapMarkdown(data: MindMapData): string {
  const lines: string[] = [];
  lines.push(`# ${sanitize(data.title)}`);
  const walk = (nodes: MindMapNode[], depth: number) => {
    nodes.forEach((node) => {
      lines.push(`${'  '.repeat(depth)}- ${sanitize(node.name)}`);
      if (node.children && node.children.length > 0) {
        walk(node.children, depth + 1);
      }
    });
  };
  walk(data.nodes, 0);
  return lines.join('\n');
}
