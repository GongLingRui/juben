/**
 * 消息操作组件
 */

import { Copy, Check, RefreshCw, Bookmark } from 'lucide-react';
import { useState } from 'react';
import type { Message } from '@/types';

interface MessageActionsProps {
  message: Message;
  onCopy: () => void;
  copied: boolean;
}

export default function MessageActions({ message, onCopy, copied }: MessageActionsProps) {
  const [bookmarked, setBookmarked] = useState(false);

  if (message.role === 'user') return null;

  return (
    <div className="flex items-center gap-1 mt-2">
      {/* 复制按钮 */}
      <button
        onClick={onCopy}
        className="p-1.5 rounded-lg hover:bg-gray-200 transition-colors"
        title="复制"
      >
        {copied ? (
          <Check className="w-4 h-4 text-green-600" />
        ) : (
          <Copy className="w-4 h-4 text-gray-400" />
        )}
      </button>

      {/* 重新生成 */}
      {message.status === 'complete' && (
        <button
          className="p-1.5 rounded-lg hover:bg-gray-200 transition-colors"
          title="重新生成"
        >
          <RefreshCw className="w-4 h-4 text-gray-400" />
        </button>
      )}

      {/* 收藏 */}
      <button
        onClick={() => setBookmarked(!bookmarked)}
        className={`p-1.5 rounded-lg transition-colors ${
          bookmarked ? 'bg-yellow-100' : 'hover:bg-gray-200'
        }`}
        title="收藏"
      >
        <Bookmark
          className={`w-4 h-4 ${bookmarked ? 'text-yellow-600 fill-yellow-600' : 'text-gray-400'}`}
        />
      </button>
    </div>
  );
}
