from fastapi import FastAPI

app = FastAPI()


@app.post("/students/{student_id}/progress")
def record_progress(student_id: str, payload: dict):  # expect: A7
    try:
        return {"ok": int(payload["score"])}
    except Exception:  # expect: A6
        pass
