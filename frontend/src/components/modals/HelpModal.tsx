/**
 * 帮助弹窗 - 快速指引
 */

import { X, Sparkles, Layers, FileText, MessageSquare } from 'lucide-react';

interface HelpModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function HelpModal({ isOpen, onClose }: HelpModalProps) {
  if (!isOpen) return null;

  return (
    <>
      <div
        className="fixed inset-0 bg-black/50 z-50 animate-fade-in"
        onClick={onClose}
      />
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div className="w-full max-w-lg bg-white rounded-2xl shadow-xl overflow-hidden animate-scale-in">
          <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
            <div className="flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-gray-700" />
              <h2 className="text-lg font-semibold text-gray-900">快速上手</h2>
            </div>
            <button
              onClick={onClose}
              className="p-2 rounded-lg hover:bg-gray-100"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          <div className="p-6 space-y-4 text-sm text-gray-700">
            <div className="flex items-start gap-3">
              <MessageSquare className="w-5 h-5 text-gray-500" />
              <div>
                <div className="font-medium text-gray-900">选择 Agent 并对话</div>
                <div>从顶部选择合适的 Agent，输入指令开始对话。</div>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <FileText className="w-5 h-5 text-gray-500" />
              <div>
                <div className="font-medium text-gray-900">查看生成结果</div>
                <div>右侧对话完成后，左侧会显示可复制/导出的成果。</div>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <Layers className="w-5 h-5 text-gray-500" />
              <div>
                <div className="font-medium text-gray-900">Notes 作为素材库</div>
                <div>把内容保存为 Note，后续一键插入继续创作。</div>
              </div>
            </div>
          </div>

          <div className="px-6 py-4 bg-gray-50 text-xs text-gray-500">
            提示：在对话输入框中可使用“插入已选 Notes”。
          </div>
        </div>
      </div>
    </>
  );
}
