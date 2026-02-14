import os
import subprocess
import logging

logger = logging.getLogger(__name__)


def ensure_ollama_model(model: str, base_url: str) -> None:
    if not model:
        return
    if os.getenv("OLLAMA_AUTO_PULL", "false").lower() != "true":
        return
    try:
        subprocess.run(
            ["ollama", "pull", model],
            check=True,
            timeout=600
        )
        logger.info(f"Ollama模型已拉取: {model}")
    except FileNotFoundError:
        logger.warning("未找到ollama命令，自动拉取失败")
    except subprocess.TimeoutExpired:
        logger.warning("Ollama模型拉取超时")
    except Exception as e:
        logger.warning(f"Ollama模型拉取失败: {e}")
