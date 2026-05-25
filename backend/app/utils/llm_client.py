# 大模型 API 统一调用（支持 OpenAI 兼容接口 + 用户坐姿数据注入）

import os
import httpx
import traceback

# 配置（由 main.py 启动时通过 dotenv 加载）
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_API_BASE = os.getenv("LLM_API_BASE", "https://api.openai.com/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-3.5-turbo")
LLM_TIMEOUT = 30

# 启动时诊断
if not LLM_API_KEY:
    print("[LLM] 警告: LLM_API_KEY 未设置，智能客服将不可用")
    print("[LLM] 请在 backend/.env 中配置（复制 .env.example → .env 并填入真实的 API Key）")
else:
    print(f"[LLM] 已加载配置: base={LLM_API_BASE}, model={LLM_MODEL}, key={'*' * 8}{LLM_API_KEY[-4:]}")

SYSTEM_PROMPT = """你是一个专业的坐姿健康助手，属于"智能坐姿监测系统"。你的职责是：

1. 解答用户关于坐姿健康的问题（头部前倾、高低肩、驼背含胸、身体倾斜、圆肩等）
2. 根据用户提供的监测数据给出个性化改善建议
3. 推荐科学的坐姿矫正方法和锻炼方式
4. 解释各项坐姿指标的含义和正常范围

重要规则：
- 你的建议仅供参考，不能替代专业医学诊断
- 如用户描述严重症状，应建议咨询专业医疗机构
- 回答简洁、专业、易懂，每次控制在 200 字以内
- 使用中文回答

坐姿指标正常范围参考：
- 头部前倾角度：< 30° 正常，30-40° 轻度，40-50° 中度，> 50° 重度
- 高低肩比例：< 5% 正常，5-8% 轻度，8-12% 中度，> 12% 重度
- 驼背前倾比例：< 0.3 正常，0.3-0.5 轻度，0.5-0.7 中度，> 0.7 重度
- 身体倾斜角度：< 5° 正常，5-10° 轻度，10-15° 中度，> 15° 重度
- 圆肩比例：< 0.2 正常，0.2-0.3 轻度，0.3-0.5 中度，> 0.5 重度
"""


def build_posture_context(db, user_id: int) -> str | None:
    """
    从数据库拉取用户最新坐姿数据，构建自然语言描述
    注入到 AI 对话中，使客服能针对性地回答

    Returns:
        str: 坐姿数据摘要，如 "用户当前坐姿：头部前倾22.4°, ..."
        None: 无数据
    """
    try:
        from ..db import crud as db_crud
        from datetime import datetime, timedelta, date

        latest = db_crud.get_latest_record(db, user_id)
        if not latest:
            return None

        # 最新指标
        parts = []
        if latest.head_angle is not None:
            parts.append(f"头部前倾{latest.head_angle:.1f}°")
        if latest.shoulder_diff is not None:
            parts.append(f"高低肩{(latest.shoulder_diff * 100):.1f}%")
        if latest.hunchback_score is not None:
            parts.append(f"驼背前倾比例{(latest.hunchback_score * 100):.1f}%")
        if latest.body_tilt is not None:
            parts.append(f"身体倾斜{latest.body_tilt:.1f}°")
        if latest.round_shoulder is not None:
            parts.append(f"圆肩{(latest.round_shoulder * 100):.1f}%")
        if latest.confidence is not None:
            parts.append(f"置信度{latest.confidence * 100:.0f}%")

        # 今日统计
        today = date.today()
        today_start = datetime.combine(today, datetime.min.time())
        today_end = datetime.combine(today, datetime.max.time())
        today_records = db_crud.get_records_by_time_range(db, user_id, today_start, today_end, limit=100000)

        today_stats = ""
        if today_records:
            bad_count = sum(1 for r in today_records if r.posture_label and r.posture_label != "normal")
            total = len(today_records)
            today_stats = f"\n今日统计：共{total}条记录，不良坐姿{bad_count}条（{bad_count / total * 100:.0f}%）"

        ctx = "【当前用户真实坐姿数据】\n" + "，".join(parts) + today_stats
        ctx += f"\n综合标签：{latest.posture_label or '未知'}"
        ctx += f"\n记录时间：{latest.created_at.strftime('%Y-%m-%d %H:%M')}"

        return ctx

    except Exception as e:
        print(f"[LLM] 数据上下文构建失败: {e}")
        return None


async def chat(message: str, history: list = None, posture_ctx: str = None) -> str:
    if not LLM_API_KEY:
        return "请先配置 LLM_API_KEY（复制 backend/.env.example → backend/.env 并填入你的 API Key）"

    if history is None:
        history = []

    # 构建系统提示词（含用户真实坐姿数据）
    system_content = SYSTEM_PROMPT
    if posture_ctx:
        system_content += f"\n\n{posture_ctx}\n\n请根据以上真实的用户坐姿数据来回答问题。如果用户询问当前坐姿、健康状况等，直接引用这些数据给出针对性建议。"

    messages = [{"role": "system", "content": system_content}]
    messages.extend(history)
    messages.append({"role": "user", "content": message})

    try:
        async with httpx.AsyncClient(timeout=LLM_TIMEOUT) as client:
            resp = await client.post(
                f"{LLM_API_BASE}/chat/completions",
                headers={
                    "Authorization": f"Bearer {LLM_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": LLM_MODEL,
                    "messages": messages,
                    "max_tokens": 500,
                    "temperature": 0.7,
                },
            )

            if resp.status_code != 200:
                error_detail = resp.text[:300]
                print(f"[LLM] API 返回错误 {resp.status_code}: {error_detail}")
                return f"AI 服务返回错误 ({resp.status_code})，请检查 API Key 和模型名是否正确。\n\n详情: {error_detail}"

            data = resp.json()
            return data["choices"][0]["message"]["content"]

    except httpx.ConnectError:
        return "无法连接到 AI 服务，请检查网络和 LLM_API_BASE 地址是否正确。"
    except httpx.TimeoutException:
        return "AI 服务响应超时，请稍后重试。"
    except Exception as e:
        traceback.print_exc()
        return f"AI 服务调用异常: {str(e)}"


def chat_sync(message: str, history: list = None) -> str:
    import asyncio
    return asyncio.run(chat(message, history))

