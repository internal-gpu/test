import asyncio
import traceback
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, File, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from pydantic import BaseModel

from database import get_db, init_db
from models import Contract, ReviewItem, Setting
from llm_service import analyze_contract, classify_contract, DEFAULT_REVIEW_PROMPT, DEFAULT_CLASSIFY_PROMPT
from docx_utils import extract_text_from_docx, create_reviewed_docx


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    # Seed default settings
    async for db in get_db():
        for key, value in [
            ("review_prompt", DEFAULT_REVIEW_PROMPT),
            ("classify_prompt", DEFAULT_CLASSIFY_PROMPT),
            ("api_key", ""),
            ("base_url", ""),
            ("model", "gpt-4o"),
        ]:
            existing = await db.execute(select(Setting).where(Setting.key == key))
            if not existing.scalar_one_or_none():
                db.add(Setting(key=key, value=value))
        await db.commit()
    yield


app = FastAPI(title="合同审查工具", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── File Storage ────────────────────────────────────────────────────────────
# Store raw DOCX bytes in memory (keyed by contract ID) for download later.
# In production, use object storage.
_file_store: dict[int, bytes] = {}


# ─── Schemas ─────────────────────────────────────────────────────────────────

class SettingUpdate(BaseModel):
    value: str


class ReviewItemOut(BaseModel):
    id: int
    location: str
    original_text: str
    suggested_text: str
    reason: str
    severity: str

    class Config:
        from_attributes = True


class ContractOut(BaseModel):
    id: int
    filename: str
    category: str
    status: str
    error_message: str | None
    created_at: str
    reviews: list[ReviewItemOut]

    class Config:
        from_attributes = True


class ContractBrief(BaseModel):
    id: int
    filename: str
    category: str
    status: str
    error_message: str | None
    created_at: str
    review_count: int


class CategoryCount(BaseModel):
    category: str
    count: int


class AnalyzeRequest(BaseModel):
    contract_ids: list[int] | None = None  # None = analyze all pending


# ─── Settings API ────────────────────────────────────────────────────────────

@app.get("/api/settings")
async def get_settings(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Setting))
    settings = result.scalars().all()
    return {s.key: s.value for s in settings}


@app.put("/api/settings/{key}")
async def update_setting(key: str, body: SettingUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Setting).where(Setting.key == key))
    setting = result.scalar_one_or_none()
    if not setting:
        setting = Setting(key=key, value=body.value)
        db.add(setting)
    else:
        setting.value = body.value
    await db.commit()
    return {"key": key, "value": body.value}


# ─── Upload API ──────────────────────────────────────────────────────────────

@app.post("/api/upload")
async def upload_contracts(
    files: list[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Batch upload DOCX files."""
    uploaded = []
    for f in files:
        if not f.filename.endswith((".docx", ".DOCX")):
            continue
        file_bytes = await f.read()
        text = extract_text_from_docx(file_bytes)
        contract = Contract(filename=f.filename, original_text=text, status="pending")
        db.add(contract)
        await db.flush()
        _file_store[contract.id] = file_bytes
        uploaded.append({"id": contract.id, "filename": f.filename})
    await db.commit()
    return {"uploaded": uploaded, "count": len(uploaded)}


# ─── Analyze API ─────────────────────────────────────────────────────────────

@app.post("/api/analyze")
async def start_analysis(body: AnalyzeRequest, db: AsyncSession = Depends(get_db)):
    """Start analyzing contracts. Returns immediately; processing happens in background."""
    # Load settings
    result = await db.execute(select(Setting))
    settings = {s.key: s.value for s in result.scalars().all()}

    api_key = settings.get("api_key", "")
    if not api_key:
        raise HTTPException(status_code=400, detail="请先在设置中配置API Key")

    base_url = settings.get("base_url", "") or None
    model = settings.get("model", "gpt-4o")
    review_prompt = settings.get("review_prompt", "")
    classify_prompt = settings.get("classify_prompt", "")

    # Get contracts to analyze
    if body.contract_ids:
        result = await db.execute(
            select(Contract).where(Contract.id.in_(body.contract_ids))
        )
    else:
        result = await db.execute(
            select(Contract).where(Contract.status == "pending")
        )
    contracts = result.scalars().all()

    if not contracts:
        raise HTTPException(status_code=404, detail="没有待分析的合同")

    # Mark as analyzing
    for c in contracts:
        c.status = "analyzing"
    await db.commit()

    contract_data = [(c.id, c.original_text) for c in contracts]

    # Launch background task
    asyncio.create_task(
        _process_contracts(contract_data, api_key, base_url, model, review_prompt, classify_prompt)
    )

    return {"message": f"开始分析 {len(contracts)} 份合同", "count": len(contracts)}


async def _process_contracts(
    contract_data: list[tuple[int, str]],
    api_key: str,
    base_url: str | None,
    model: str,
    review_prompt: str,
    classify_prompt: str,
):
    """Background task to process contracts sequentially."""
    from database import async_session

    for contract_id, text in contract_data:
        async with async_session() as db:
            try:
                contract = await db.get(Contract, contract_id)
                if not contract:
                    continue

                # Classify
                category = await classify_contract(
                    text, api_key, base_url, model, classify_prompt or None
                )
                contract.category = category

                # Analyze
                items = await analyze_contract(
                    text, api_key, base_url, model, review_prompt or None
                )

                # Save review items
                for item in items:
                    review = ReviewItem(
                        contract_id=contract_id,
                        location=item.get("location", ""),
                        original_text=item.get("original_text", ""),
                        suggested_text=item.get("suggested_text", ""),
                        reason=item.get("reason", ""),
                        severity=item.get("severity", "warning"),
                    )
                    db.add(review)

                contract.status = "completed"
                await db.commit()

            except Exception as e:
                async with async_session() as err_db:
                    contract = await err_db.get(Contract, contract_id)
                    if contract:
                        contract.status = "error"
                        contract.error_message = f"{type(e).__name__}: {str(e)}"
                        await err_db.commit()


# ─── Contract List / Detail ─────────────────────────────────────────────────

@app.get("/api/contracts", response_model=list[ContractBrief])
async def list_contracts(
    category: str | None = Query(None),
    status: str | None = Query(None),
    search: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    query = select(Contract).order_by(Contract.created_at.desc())
    if category:
        query = query.where(Contract.category == category)
    if status:
        query = query.where(Contract.status == status)
    if search:
        query = query.where(Contract.filename.contains(search))

    result = await db.execute(query)
    contracts = result.scalars().all()

    # Get review counts
    briefs = []
    for c in contracts:
        count_result = await db.execute(
            select(func.count(ReviewItem.id)).where(ReviewItem.contract_id == c.id)
        )
        count = count_result.scalar() or 0
        briefs.append(ContractBrief(
            id=c.id,
            filename=c.filename,
            category=c.category,
            status=c.status,
            error_message=c.error_message,
            created_at=c.created_at.isoformat() if c.created_at else "",
            review_count=count,
        ))
    return briefs


@app.get("/api/contracts/{contract_id}")
async def get_contract(contract_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Contract).where(Contract.id == contract_id).options(selectinload(Contract.reviews))
    )
    contract = result.scalar_one_or_none()
    if not contract:
        raise HTTPException(status_code=404, detail="合同不存在")

    return {
        "id": contract.id,
        "filename": contract.filename,
        "original_text": contract.original_text,
        "category": contract.category,
        "status": contract.status,
        "error_message": contract.error_message,
        "created_at": contract.created_at.isoformat() if contract.created_at else "",
        "reviews": [
            {
                "id": r.id,
                "location": r.location,
                "original_text": r.original_text,
                "suggested_text": r.suggested_text,
                "reason": r.reason,
                "severity": r.severity,
            }
            for r in contract.reviews
        ],
    }


@app.delete("/api/contracts/{contract_id}")
async def delete_contract(contract_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Contract).where(Contract.id == contract_id))
    contract = result.scalar_one_or_none()
    if not contract:
        raise HTTPException(status_code=404, detail="合同不存在")
    await db.delete(contract)
    await db.commit()
    _file_store.pop(contract_id, None)
    return {"message": "已删除"}


# ─── Download reviewed DOCX ─────────────────────────────────────────────────

@app.get("/api/contracts/{contract_id}/download")
async def download_reviewed_docx(contract_id: int, db: AsyncSession = Depends(get_db)):
    """Download the contract DOCX with review annotations inline."""
    result = await db.execute(
        select(Contract).where(Contract.id == contract_id).options(selectinload(Contract.reviews))
    )
    contract = result.scalar_one_or_none()
    if not contract:
        raise HTTPException(status_code=404, detail="合同不存在")

    file_bytes = _file_store.get(contract_id)
    if not file_bytes:
        raise HTTPException(status_code=404, detail="原始文件不可用（服务重启后文件丢失）")

    reviews = [
        {
            "original_text": r.original_text,
            "suggested_text": r.suggested_text,
            "reason": r.reason,
            "severity": r.severity,
        }
        for r in contract.reviews
    ]

    reviewed_bytes = create_reviewed_docx(file_bytes, reviews)

    filename = contract.filename.replace(".docx", "_审查结果.docx")
    return Response(
        content=reviewed_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ─── Categories ──────────────────────────────────────────────────────────────

@app.get("/api/categories", response_model=list[CategoryCount])
async def get_categories(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Contract.category, func.count(Contract.id))
        .group_by(Contract.category)
        .order_by(func.count(Contract.id).desc())
    )
    rows = result.all()
    return [CategoryCount(category=cat, count=cnt) for cat, cnt in rows]


# ─── Serve frontend static files ─────────────────────────────────────────────

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend" / "dist"

if FRONTEND_DIR.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIR / "assets"), name="static-assets")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        """Serve the React SPA for any non-API route."""
        file_path = FRONTEND_DIR / full_path
        if file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(FRONTEND_DIR / "index.html")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
