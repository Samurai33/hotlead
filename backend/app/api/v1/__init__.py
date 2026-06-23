from fastapi import APIRouter
from app.api.v1 import jobs, prospects, accounts

router = APIRouter()
router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
router.include_router(prospects.router, prefix="/jobs", tags=["prospects"])
router.include_router(accounts.router, prefix="/accounts", tags=["accounts"])
