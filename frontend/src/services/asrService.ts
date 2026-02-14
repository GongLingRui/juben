import { API_BASE_URL, getAuthHeaderValue } from './api';

export async function transcribeAudio(file: Blob, language?: string, model?: string): Promise<{
  success: boolean;
  text?: string;
  message?: string;
}> {
  try {
    const formData = new FormData();
  formData.append('audio', file, 'speech.webm');
    if (language) formData.append('language', language);
    if (model) formData.append('model', model);

    const res = await fetch(`${API_BASE_URL}/juben/asr/transcribe`, {
      method: 'POST',
      headers: {
        ...(getAuthHeaderValue() ? { Authorization: getAuthHeaderValue() as string } : {}),
      },
      body: formData
    });
    if (!res.ok) {
      return { success: false, message: await res.text() };
    }
    const data = await res.json();
    return { success: true, text: data?.data?.text };
  } catch (error) {
    console.error('ASR转写失败:', error);
    return { success: false, message: 'ASR转写失败' };
  }
}
