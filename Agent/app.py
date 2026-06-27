import threading
from datetime import datetime
from typing import Any, Dict

from flask import Flask, jsonify, request
from flask_cors import CORS

from annotation_agent.database import SessionLocal
from annotation_agent.models import AISuggestion, AIAuditReport
from annotation_agent.suggestion import generate_suggestion

app = Flask(__name__)
CORS(app)


def _row_to_dict_suggestion(row: AISuggestion) -> Dict[str, Any]:
    return {
        "suggestion_id": row.id,
        "status": row.status,
        "suggestion": row.suggestion,
        "model": row.model,
        "error": row.error,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "completed_at": row.completed_at.isoformat() if row.completed_at else None,
    }


def _row_to_dict_audit(row: AIAuditReport) -> Dict[str, Any]:
    return {
        "audit_id": row.id,
        "status": row.status,
        "score": float(row.score) if row.score is not None else None,
        "issues": row.issues,
        "reasoning": row.reasoning,
        "suggestion": row.suggestion,
        "evidence": row.evidence,
        "model": row.model,
        "error": row.error,
    }


@app.get("/health")
def health():
    return jsonify({"status": "ok"})


def _generate_in_background(suggestion_id: str, template_schema: Any, raw_data: Any) -> None:
    session = SessionLocal()
    try:
        result = generate_suggestion(template_schema, raw_data)
        row = session.get(AISuggestion, suggestion_id)
        if row is None:
            return
        row.suggestion = result.get("suggestion")
        row.model = result.get("model")
        row.error = result.get("error")
        row.status = "done"
        row.completed_at = datetime.utcnow()
        session.commit()
    except Exception as e:
        session.rollback()
        row = session.get(AISuggestion, suggestion_id)
        if row is not None:
            row.status = "failed"
            row.error = f"{type(e).__name__}: {str(e)[:480]}"
            row.completed_at = datetime.utcnow()
            try:
                session.commit()
            except Exception:
                session.rollback()
    finally:
        session.close()


@app.post("/suggestion")
def suggestion():
    body = request.get_json(silent=True) or {}
    suggestion_id = body.get("suggestion_id")
    task_id = body.get("task_id")
    task_item_id = body.get("task_item_id")
    template_schema = body.get("template_schema")
    raw_data = body.get("raw_data")

    if not suggestion_id or task_id is None or task_item_id is None:
        return jsonify({"code": 1, "message": "missing required fields: suggestion_id, task_id, task_item_id"}), 400

    session = SessionLocal()
    try:
        row = session.get(AISuggestion, suggestion_id)
        if row is None:
            row = AISuggestion(
                id=suggestion_id, task_id=int(task_id), task_item_id=int(task_item_id),
                status="pending",
            )
            session.add(row)
            session.commit()
        thread = threading.Thread(
            target=_generate_in_background,
            args=(suggestion_id, template_schema, raw_data),
            daemon=True,
        )
        thread.start()
    except Exception as e:
        session.rollback()
        return jsonify({"code": 1, "message": str(e)}), 500
    finally:
        session.close()

    return jsonify({"suggestion_id": suggestion_id, "status": "generating"})


@app.get("/suggestion/<suggestion_id>")
def get_suggestion(suggestion_id: str):
    session = SessionLocal()
    try:
        row = session.get(AISuggestion, suggestion_id)
        if row is None:
            return jsonify({"code": 1, "message": "not found"}), 404
        return jsonify(_row_to_dict_suggestion(row))
    finally:
        session.close()


@app.get("/audit/<audit_id>")
def get_audit(audit_id: str):
    session = SessionLocal()
    try:
        row = session.get(AIAuditReport, audit_id)
        if row is None:
            return jsonify({"code": 1, "message": "not found"}), 404
        return jsonify(_row_to_dict_audit(row))
    finally:
        session.close()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)