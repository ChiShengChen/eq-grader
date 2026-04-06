import json
import yaml


def _format_rubric(rubric: dict) -> str:
    lines = []
    for dimension, levels in rubric.items():
        lines.append(f"【{dimension}】")
        for score, desc in sorted(levels.items(), key=lambda x: x[0], reverse=True):
            lines.append(f"  {score}分: {desc}")
    return "\n".join(lines)


def _format_feedback_guidelines(style: dict) -> str:
    lines = [f"語氣: {style.get('tone', '溫暖、鼓勵')}"]
    for g in style.get("guidelines", []):
        lines.append(f"- {g}")
    return "\n".join(lines)


def _format_feedback_examples(style: dict) -> str:
    examples = style.get("examples", [])
    if not examples:
        return ""
    parts = []
    for i, ex in enumerate(examples, 1):
        parts.append(f"範例{i}:\n{ex.strip()}")
    return "\n\n".join(parts)


def build_stage1_prompt(questionnaire: dict, student_answer: dict) -> tuple[str, str]:
    system = (
        "你是一位資深的國小EQ教育專家。請分析以下學生的答案，評估其理解程度。"
        "請使用台灣繁體中文回答。請輸出JSON格式。"
    )
    prompt = f"""問卷名稱: {questionnaire['name']}
問卷說明: {questionnaire['description']}
問卷指示: {questionnaire.get('instructions', '')}

學生答案:
{json.dumps(student_answer, ensure_ascii=False, indent=2)}

請分析這份學生答案，輸出以下JSON:
{{
  "understanding": {{
    "event_summary": "學生描述的事件摘要",
    "emotions_identified": "學生識別出的情緒（列出所有）",
    "thoughts_identified": "學生表達的想法",
    "comprehension_level": "完全理解/部分理解/未理解",
    "notable_observations": ["觀察重點1", "觀察重點2"]
  }}
}}"""
    return system, prompt


def build_stage2_prompt(questionnaire: dict, student_answer: dict, understanding: dict) -> tuple[str, str]:
    rubric_text = _format_rubric(questionnaire.get("rubric", {}))

    system = (
        "你是一位資深的國小EQ教育專家。請根據評分規準客觀評估學生答案。"
        "評價時請只根據答案的實際內容來判斷。請使用台灣繁體中文。請輸出JSON格式。"
    )
    prompt = f"""問卷名稱: {questionnaire['name']}

學生答案:
{json.dumps(student_answer, ensure_ascii=False, indent=2)}

Stage 1 分析結果:
{json.dumps(understanding, ensure_ascii=False, indent=2)}

評分規準:
{rubric_text}

請根據以上評分規準，輸出以下JSON:
{{
  "student_self_reflection": {{
    "confidence": "很有信心/普通/不太確定/亂寫的",
    "perceived_difficulty": "以學生角度覺得哪裡最難寫",
    "self_assessment": "用小學生口吻評價自己寫得如何",
    "uncertain_parts": ["不確定的欄位名稱"]
  }},
  "teacher_feedback": {{
    "overall_quality": "優秀/良好/普通/待加強/需重寫",
    "scores": {{
      "completeness": 1到5的整數,
      "correctness": 1到5的整數,
      "depth": 1到5的整數,
      "expression": 1到5的整數,
      "appropriateness": 1到5的整數
    }},
    "strengths": ["優點1", "優點2"],
    "weaknesses": ["需改進之處"],
    "error_analysis": "具體錯誤分析，若無錯誤則寫「無明顯錯誤」",
    "suggestions": "給學生的具體改進建議"
  }}
}}"""
    return system, prompt


def build_stage3_prompt(questionnaire: dict, student_answer: dict, evaluation: dict) -> tuple[str, str]:
    style = questionnaire.get("feedback_style", {})
    guidelines = _format_feedback_guidelines(style)
    examples = _format_feedback_examples(style)

    scores = evaluation.get("teacher_feedback", {}).get("scores", {})
    strengths = evaluation.get("teacher_feedback", {}).get("strengths", [])
    weaknesses = evaluation.get("teacher_feedback", {}).get("weaknesses", [])
    suggestions = evaluation.get("teacher_feedback", {}).get("suggestions", "")
    overall = evaluation.get("teacher_feedback", {}).get("overall_quality", "")

    system = (
        "你是一位溫暖、鼓勵的國小老師。你正在為學生的EQ練習寫評語。"
        "請使用台灣繁體中文，用國小學生能理解的口語化語言。"
        "直接寫出評語文字，不要用JSON格式，不要加任何標題或前綴。"
    )
    prompt = f"""學生答案:
{json.dumps(student_answer, ensure_ascii=False, indent=2)}

評估結果:
- 整體品質: {overall}
- 各項分數: {json.dumps(scores, ensure_ascii=False)}
- 優點: {', '.join(strengths)}
- 需改進: {', '.join(weaknesses)}
- 建議: {suggestions}

評語撰寫指南:
{guidelines}

評語範例（參考風格即可，請根據這位學生的實際答案撰寫）:
{examples}

請根據以上資訊，為這位學生寫一段溫暖鼓勵的評語（30-50字）:
- 先肯定做得好的地方
- 用「你可以試試看...」而非「你做錯了...」
- 給出一個具體可行的改進建議
- 用國小學生能懂的語言"""
    return system, prompt
