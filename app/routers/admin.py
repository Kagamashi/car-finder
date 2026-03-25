from fastapi import APIRouter, Header, HTTPException

from app.config import settings

router = APIRouter()


def _verify_admin_key(x_admin_key: str = Header(...)):
    if x_admin_key != settings.ADMIN_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid admin key")


@router.post("/scrape/trigger", dependencies=[])
async def trigger_scrape(x_admin_key: str = Header(...)):
    _verify_admin_key(x_admin_key)
    from app.tasks.scrape_tasks import dispatch_all_sources

    task = dispatch_all_sources.delay()
    return {"task_id": task.id, "status": "queued"}
