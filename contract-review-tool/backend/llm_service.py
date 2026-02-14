import json
from openai import AsyncOpenAI

DEFAULT_REVIEW_PROMPT = """你是一位专业的合同审查律师。请仔细审查以下合同内容，找出需要修改或存在风险的条款。

对于每一个需要修改的地方，请提供：
1. location: 该条款所在的位置描述（如"第X条 XXX"或引用原文片段）
2. original_text: 需要修改的原文内容（精确引用）
3. suggested_text: 建议修改后的完整内容
4. reason: 修改原因（从法律风险、公平性、合规性等角度分析）
5. severity: 严重程度（critical=必须修改, warning=建议修改, info=可选优化）

请以JSON数组格式输出，每个元素包含上述5个字段。如果合同没有问题，返回空数组[]。

注意：
- 重点关注：权责不对等、违约金过高、知识产权归属不明、保密条款缺失、争议解决方式不合理等问题
- 修改建议应具体、可直接替换原文
- 仅输出JSON数组，不要输出其他内容

合同内容：
{contract_text}"""

DEFAULT_CLASSIFY_PROMPT = """请对以下合同进行分类，从下列类别中选择最合适的一个：
- 供应商合同
- 技术服务合同
- 咨询服务合同
- 场地租赁合同
- 劳动合同
- 销售合同
- 保密协议
- 合作框架协议
- 其他

仅输出类别名称，不要输出其他内容。

合同内容（前2000字）：
{contract_text}"""


async def analyze_contract(
    contract_text: str,
    api_key: str,
    base_url: str | None = None,
    model: str = "gpt-4o",
    review_prompt: str | None = None,
) -> list[dict]:
    """Analyze a contract and return review items."""
    prompt = (review_prompt or DEFAULT_REVIEW_PROMPT).replace("{contract_text}", contract_text)

    client_kwargs = {"api_key": api_key}
    if base_url:
        client_kwargs["base_url"] = base_url

    client = AsyncOpenAI(**client_kwargs)

    response = await client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        stream=False,
    )

    content = response.choices[0].message.content.strip()
    # Strip markdown code fences if present
    if content.startswith("```"):
        lines = content.split("\n")
        lines = lines[1:]  # remove opening fence
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        content = "\n".join(lines)

    try:
        items = json.loads(content)
    except json.JSONDecodeError:
        # Try to extract JSON array from response
        start = content.find("[")
        end = content.rfind("]") + 1
        if start != -1 and end > start:
            items = json.loads(content[start:end])
        else:
            raise ValueError(f"LLM返回内容无法解析为JSON: {content[:200]}")

    return items


async def classify_contract(
    contract_text: str,
    api_key: str,
    base_url: str | None = None,
    model: str = "gpt-4o",
    classify_prompt: str | None = None,
) -> str:
    """Classify a contract into a category."""
    text_preview = contract_text[:2000]
    prompt = (classify_prompt or DEFAULT_CLASSIFY_PROMPT).replace("{contract_text}", text_preview)

    client_kwargs = {"api_key": api_key}
    if base_url:
        client_kwargs["base_url"] = base_url

    client = AsyncOpenAI(**client_kwargs)

    response = await client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        stream=False,
    )

    return response.choices[0].message.content.strip()
