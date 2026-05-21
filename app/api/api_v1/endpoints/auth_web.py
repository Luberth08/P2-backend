from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.schemas.auth import LoginRequest, TokenResponse, RegisterInitRequest, RegisterCompleteRequest
from app.services import auth_service, registration_service
from app.core.exceptions import InvalidTokenError

router = APIRouter(tags=["Authentication - Web"])

@router.post("/login", response_model=TokenResponse)
async def web_login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    return await auth_service.login_user(db, req.email, req.password)

@router.post("/logout", status_code=204)
async def web_logout(request: Request, db: AsyncSession = Depends(get_db)):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise InvalidTokenError()
    token = auth_header.split(" ")[1]
    await auth_service.logout_user(db, token)
    return Response(status_code=204)

@router.post("/register/init")
async def register_init(req: RegisterInitRequest, db: AsyncSession = Depends(get_db)):
    await registration_service.start_web_registration(db, req.dict())
    return {"message": "OTP sent"}

@router.post("/register/complete", response_model=TokenResponse)
async def register_complete(req: RegisterCompleteRequest, db: AsyncSession = Depends(get_db)):
    return await registration_service.complete_web_registration(db, req.email, req.code)