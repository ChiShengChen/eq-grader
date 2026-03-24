import json
from fastapi import APIRouter, Request, Depends, BackgroundTasks
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from app.database import get_session, engine
from app.models import StudentSubmission, AIEvaluation

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/")
async def index(request: Request):
    from app.main import app_state
    questionnaires = app_state["questionnaires"]
    return templates.TemplateResponse("student_form.html", {
        "request": request,
        "questionnaires": questionnaires,
        "questionnaire": None,
    })


@router.get("/questionnaire/{q_id}")
async def questionnaire_form(request: Request, q_id: str):
    from app.main import app_state
    questionnaires = app_state["questionnaires"]
    q = questionnaires.get(q_id)
    if not q:
        return templates.TemplateResponse("student_form.html", {
            "request": request,
            "questionnaires": questionnaires,
            "questionnaire": None,
            "error": "找不到這份問卷",
        })

    fixed_slots = {}
    for field_def in q.get("schema", {}).get("fields", []):
        if field_def.get("type") == "emotion_wheel":
            fixed_slots = field_def.get("fixed_slots", {})
            break

    return templates.TemplateResponse("student_form.html", {
        "request": request,
        "questionnaires": questionnaires,
        "questionnaire": q,
        "fixed_slots": fixed_slots,
    })


@router.post("/submit")
async def submit_answer(
    request: Request,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
):
    from app.main import app_state
    form = await request.form()
    q_id = form.get("questionnaire_id", "")
    student_name = form.get("student_name", "").strip()
    questionnaires = app_state["questionnaires"]
    q = questionnaires.get(q_id)

    if not q or not student_name:
        return templates.TemplateResponse("student_form.html", {
            "request": request,
            "questionnaires": questionnaires,
            "questionnaire": q,
            "error": "請填寫姓名並選擇問卷",
        })

    answers = _parse_form_answers(form, q)

    submission = StudentSubmission(
        questionnaire_id=q_id,
        student_name=student_name,
        raw_answer=json.dumps(answers, ensure_ascii=False),
        status="grading",
    )
    session.add(submission)
    session.commit()
    session.refresh(submission)

    background_tasks.add_task(_grade_submission, submission.id, q_id, answers)

    return templates.TemplateResponse("student_submitted.html", {
        "request": request,
        "submission": submission,
        "questionnaire": q,
    })


@router.get("/result/{submission_id}")
async def show_result(request: Request, submission_id: str, session: Session = Depends(get_session)):
    from app.main import app_state
    submission = session.get(StudentSubmission, submission_id)
    if not submission:
        return templates.TemplateResponse("student_result.html", {
            "request": request,
            "error": "找不到這筆作答紀錄",
        })

    evaluation = session.exec(
        select(AIEvaluation).where(AIEvaluation.submission_id == submission_id)
    ).first()

    answers = json.loads(submission.raw_answer)
    q_name = app_state["questionnaires"].get(submission.questionnaire_id, {}).get("name", submission.questionnaire_id)
    comment = ""
    if evaluation:
        comment = evaluation.teacher_override or evaluation.teacher_comment

    return templates.TemplateResponse("student_result.html", {
        "request": request,
        "submission": submission,
        "answers": answers,
        "teacher_comment": comment,
        "questionnaire_name": q_name,
    })


def _parse_form_answers(form, questionnaire: dict) -> dict:
    answers = {}
    for field_def in questionnaire.get("schema", {}).get("fields", []):
        name = field_def["name"]
        if field_def["type"] == "text":
            answers[name] = form.get(name, "")
        elif field_def["type"] == "emotion_wheel":
            fixed = field_def.get("fixed_slots", {})
            slots = []
            for i in range(1, 9):
                slot = {"slot_number": i}
                if i in fixed or str(i) in fixed:
                    fixed_data = fixed.get(i) or fixed.get(str(i), {})
                    slot["color"] = fixed_data.get("color", "")
                    slot["emotion"] = fixed_data.get("emotion", "")
                else:
                    slot["color"] = form.get(f"slot_{i}_color", "")
                    slot["emotion"] = form.get(f"slot_{i}_emotion", "")
                slot["thought"] = form.get(f"slot_{i}_thought", "")
                slots.append(slot)
            answers[name] = slots
    return answers


async def _grade_submission(submission_id: str, questionnaire_id: str, answers: dict):
    from app.main import app_state

    pipeline = app_state["pipeline"]
    with Session(engine) as session:
        submission = session.get(StudentSubmission, submission_id)
        if not submission:
            return

        try:
            result = await pipeline.grade(questionnaire_id, answers)
            evaluation = AIEvaluation(
                submission_id=submission.id,
                student_self_reflection=json.dumps(result.student_self_reflection, ensure_ascii=False),
                teacher_scores=json.dumps(result.teacher_scores, ensure_ascii=False),
                teacher_comment=result.teacher_comment,
                raw_llm_output=json.dumps(result.raw_output, ensure_ascii=False),
            )
            session.add(evaluation)
            submission.status = "completed"
        except Exception as e:
            submission.status = "error"
            evaluation = AIEvaluation(
                submission_id=submission.id,
                teacher_comment=f"AI 評分時發生錯誤，請老師手動批改。錯誤: {str(e)[:200]}",
                raw_llm_output=json.dumps({"error": str(e)}, ensure_ascii=False),
            )
            session.add(evaluation)

        session.add(submission)
        session.commit()
