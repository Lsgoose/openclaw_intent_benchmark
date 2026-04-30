from litellm.integrations.custom_logger import CustomLogger
from litellm.proxy.proxy_server import UserAPIKeyAuth, DualCache
import json
import os


def ensure_extra_body(data: dict) -> dict:
    extra_body = data.get("extra_body")
    if not isinstance(extra_body, dict):
        extra_body = {}
        data["extra_body"] = extra_body
    return extra_body


def ensure_extra_headers(data: dict) -> dict:
    extra_headers = data.get("extra_headers")
    if not isinstance(extra_headers, dict):
        extra_headers = {}
        data["extra_headers"] = extra_headers
    return extra_headers


def _as_text_block_with_cache(x: str) -> dict:
    return {"type": "text", "text": x, "cache_control": {"type": "ephemeral"}}


def _ensure_cache_control_on_content(content):
    """Best-effort add Anthropic prompt-cache markers to message content."""
    if isinstance(content, str):
        return [_as_text_block_with_cache(content)]
    if isinstance(content, list):
        out = []
        injected = False
        for item in content:
            if isinstance(item, dict):
                obj = dict(item)
                if (
                    not injected
                    and obj.get("type") == "text"
                    and isinstance(obj.get("text"), str)
                    and "cache_control" not in obj
                ):
                    obj["cache_control"] = {"type": "ephemeral"}
                    injected = True
                out.append(obj)
            elif isinstance(item, str):
                if not injected:
                    out.append(_as_text_block_with_cache(item))
                    injected = True
                else:
                    out.append({"type": "text", "text": item})
            else:
                out.append(item)
        return out
    return content


def _inject_claude_prompt_cache_markers(data: dict) -> None:
    # Handle top-level system if present (OpenAI-style adapters sometimes use this).
    if "system" in data:
        data["system"] = _ensure_cache_control_on_content(data.get("system"))

    msgs = data.get("messages")
    if not isinstance(msgs, list):
        return
    out_msgs = []
    injected_in_messages = False
    for m in msgs:
        if not isinstance(m, dict):
            out_msgs.append(m)
            continue
        mm = dict(m)
        role = str(mm.get("role") or "").lower()
        # Mark earliest cacheable prefix blocks for Anthropic prompt cache.
        if role in ("system", "user") and not injected_in_messages:
            mm["content"] = _ensure_cache_control_on_content(mm.get("content"))
            injected_in_messages = True
        out_msgs.append(mm)
    data["messages"] = out_msgs


class InjectThinkingParams(CustomLogger):
    async def async_pre_call_hook(
        self,
        user_api_key_dict: UserAPIKeyAuth,
        cache: DualCache,
        data: dict,
        call_type: str,
    ):
        if call_type not in ("completion", "text_completion", "acompletion", "atext_completion"):
            return data

        # Streaming: upstream must emit a final chunk with usage or OpenClaw writes zeros to session JSONL.
        if data.get("stream"):
            so = data.get("stream_options")
            if not isinstance(so, dict):
                so = {}
                data["stream_options"] = so
            so.setdefault("include_usage", True)

        model = str(data.get("model", "")).lower()
        # Enforce deterministic sampling params for all requests.
        data["temperature"] = 0
        data["top_p"] = 0.95

        # OpenAI GPT-5.1 / GPT-5.4:
        # Chat Completions / OpenAI-compatible route 通常用顶层 reasoning_effort
        if "gpt-5" in model:
            data["reasoning_effort"] = "none"

        # Claude:
        # Anthropic route 可直接顶层传 thinking disabled
        elif "claude" in model:
            data["thinking"] = {"type": "disabled"}
            beta_header = os.getenv("ANTHROPIC_BETA_HEADER", "prompt-caching-2024-07-31")
            if beta_header:
                extra_headers = ensure_extra_headers(data)
                extra_headers.setdefault("anthropic-beta", beta_header)
            _inject_claude_prompt_cache_markers(data)

        # DeepSeek (Ofox openai/deepseek/...):
        # v3.x 上游按 OpenAI Chat Completions 校验，不接受顶层或合并后的 thinking 字段，注入会 400。
        elif "deepseek" in model:
            pass

        # Kimi / GLM / Doubao / MiniMax:
        # 走 Ofox OpenAI-compatible route 时，vendor-native 参数放 extra_body 里更稳
        elif any(x in model for x in [
            "kimi",
            "moonshot",
            "glm",
            "z-ai",
            "zai",
            "doubao",
            "minimax",
        ]):
            extra_body = ensure_extra_body(data)
            extra_body["thinking"] = {"type": "disabled"}

        # Qwen / Bailian:
        # 百炼/Qwen 通常用 enable_thinking=false
        elif any(x in model for x in ["qwen", "bailian"]):
            extra_body = ensure_extra_body(data)
            extra_body["enable_thinking"] = False

        # Gemini:
        # Gemini 3 / Gemini 2.5 Pro 不能真正关闭 thinking，不注入 off
        elif "gemini" in model:
            pass

        preview = {
            "model": data.get("model"),
            "call_type": call_type,
            "temperature": data.get("temperature"),
            "top_p": data.get("top_p"),
            "reasoning_effort": data.get("reasoning_effort"),
            "thinking": data.get("thinking"),
            "extra_body": data.get("extra_body"),
            "extra_headers": data.get("extra_headers"),
        }

        print("[LiteLLM pre_call data]", json.dumps(preview, ensure_ascii=False, default=str))
        return data


proxy_handler_instance = InjectThinkingParams()