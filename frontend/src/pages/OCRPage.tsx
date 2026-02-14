/**
 * OCR 功能页面
 * 完整的 OCR 识别界面
 */

import React, { useState } from 'react';
import { FileText, Sparkles, Info } from 'lucide-react';
import { OCRUploader, OCRResult } from '@/components/ocr';

export default function OCRPage() {
  const [showInfo, setShowInfo] = useState(false);

  const handleUploadComplete = (result: OCRResult) => {
    console.log('OCR 完成:', result);
  };

  const handleError = (error: string) => {
    console.error('OCR 错误:', error);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 dark:from-gray-900 dark:to-gray-800">
      {/* 头部 */}
      <header className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
        <div className="max-w-7xl mx-auto px-4 py-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-3 bg-blue-600 rounded-xl">
                <FileText className="w-8 h-8 text-white" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
                  OCR 文字识别
                </h1>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  基于 PaddleOCR-VL 的智能文字识别服务
                </p>
              </div>
            </div>

            <button
              onClick={() => setShowInfo(!showInfo)}
              className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
            >
              <Info className="w-6 h-6 text-gray-500" />
            </button>
          </div>

          {/* 功能说明 */}
          {showInfo && (
            <div className="mt-4 p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
              <h3 className="font-semibold text-blue-900 dark:text-blue-300 mb-2">
                功能说明
              </h3>
              <ul className="space-y-1 text-sm text-blue-800 dark:text-blue-400">
                <li>• 支持中英文混合识别</li>
                <li>• 支持表格识别和结构化输出</li>
                <li>• 支持公式识别（LaTeX 格式）</li>
                <li>• 多种输出格式：纯文本、Markdown、JSON</li>
                <li>• 本地 GPU 加速（RTX 5070 8GB）</li>
              </ul>
            </div>
          )}
        </div>
      </header>

      {/* 主内容 */}
      <main className="max-w-4xl mx-auto px-4 py-8">
        {/* OCR 上传组件 */}
        <OCRUploader
          onUploadComplete={handleUploadComplete}
          onError={handleError}
          className="mb-8"
        />

        {/* 功能特性 */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-lg">
            <div className="flex items-center gap-3 mb-3">
              <div className="p-2 bg-blue-100 dark:bg-blue-900/30 rounded-lg">
                <Sparkles className="w-5 h-5 text-blue-600 dark:text-blue-400" />
              </div>
              <h3 className="font-semibold text-gray-900 dark:text-white">
                高精度识别
              </h3>
            </div>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              基于深度学习的文字检测和识别，准确率超过 95%
            </p>
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-lg">
            <div className="flex items-center gap-3 mb-3">
              <div className="p-2 bg-green-100 dark:bg-green-900/30 rounded-lg">
                <FileText className="w-5 h-5 text-green-600 dark:text-green-400" />
              </div>
              <h3 className="font-semibold text-gray-900 dark:text-white">
                结构化输出
              </h3>
            </div>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              自动识别表格、公式、版面结构，输出格式化结果
            </p>
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-lg">
            <div className="flex items-center gap-3 mb-3">
              <div className="p-2 bg-purple-100 dark:bg-purple-900/30 rounded-lg">
                <FileText className="w-5 h-5 text-purple-600 dark:text-purple-400" />
              </div>
              <h3 className="font-semibold text-gray-900 dark:text-white">
                本地处理
              </h3>
            </div>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              所有识别在本地 GPU 完成，数据不上传云端
            </p>
          </div>
        </div>
      </main>
    </div>
  );
}
