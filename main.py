from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, Header
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
import ddddocr
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from jose import jwt
import uuid
from database import SessionLocal, init_db
from models import User, Record
from schemas import UserCreate, UserLogin, UserInfo, ChargeRequest
import os
import uvicorn
import logging
import base64
from fastapi import status

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [Prophet Server] - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)

app = FastAPI()
ocr = ddddocr.DdddOcr()

SECRET_KEY = "xmiocrsecretkey"
ALGORITHM = "HS256"
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

OCR_COST = 0.01

templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), 'templates'))

# 依赖项：获取数据库会话
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 密码加密与校验
def get_password_hash(password):
    return pwd_context.hash(password)
def verify_password(plain, hashed):
    return pwd_context.verify(plain, hashed)

def create_api_key():
    return str(uuid.uuid4())

@app.on_event("startup")
def on_startup():
    init_db()
    db = SessionLocal()
    if not db.query(User).filter(User.username == "admin").first():
        hashed = get_password_hash("admin")
        api_key = create_api_key()
        db_user = User(username="admin", hashed_password=hashed, api_key=api_key, balance=9999)
        db.add(db_user)
        db.commit()
    db.close()

@app.get("/")
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/ocr")
def ocr_captcha(file: UploadFile = File(...), x_api_key: str = Header(None), db: Session = Depends(get_db)):
    if not x_api_key:
        raise HTTPException(status_code=401, detail="请提供API Key")
    user = db.query(User).filter(User.api_key == x_api_key).first()
    if not user:
        raise HTTPException(status_code=401, detail="无效API Key")
    if user.balance < OCR_COST:
        raise HTTPException(status_code=402, detail="余额不足，请充值")
    try:
        image = file.file.read()
        result = ocr.classification(image)
        user.balance -= OCR_COST
        db.add(Record(user_id=user.id, action="识别", amount=-OCR_COST))
        db.commit()
        return {"result": result, "balance": user.balance}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/register")
def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@app.post("/register_page")
async def register_page_post(request: Request):
    form = await request.form()
    username = form.get("username")
    password = form.get("password")
    from fastapi import status
    db = SessionLocal()
    forbidden_names = ["admin", "root", "administrator"]
    if username.lower() in forbidden_names:
        return templates.TemplateResponse("register.html", {"request": request, "msg": "该用户名不可用"})
    if db.query(User).filter(User.username == username).first():
        return templates.TemplateResponse("register.html", {"request": request, "msg": "用户名已存在"})
    hashed = get_password_hash(password)
    api_key = create_api_key()
    db_user = User(username=username, hashed_password=hashed, api_key=api_key)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    db.close()
    return RedirectResponse("/login", status_code=status.HTTP_302_FOUND)

@app.get("/login")
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login_page")
async def login_page_post(request: Request):
    form = await request.form()
    username = form.get("username")
    password = form.get("password")
    from fastapi import status
    db = SessionLocal()
    db_user = db.query(User).filter(User.username == username).first()
    if not db_user or not verify_password(password, db_user.hashed_password):
        return templates.TemplateResponse("login.html", {"request": request, "msg": "用户名或密码错误"})
    response = RedirectResponse("/me", status_code=status.HTTP_302_FOUND)
    response.set_cookie(key="api_key", value=db_user.api_key)
    db.close()
    return response

@app.get("/me")
def me_page(request: Request):
    api_key = request.cookies.get("api_key")
    db = SessionLocal()
    user = db.query(User).filter(User.api_key == api_key).first()
    db.close()
    if not user:
        return RedirectResponse("/login")
    return templates.TemplateResponse("me.html", {"request": request, "user": user, "msg": None})

@app.post("/charge_page")
async def charge_page(request: Request):
    form = await request.form()
    amount = float(form.get("amount"))
    api_key = request.cookies.get("api_key")
    db = SessionLocal()
    user = db.query(User).filter(User.api_key == api_key).first()
    if not user:
        db.close()
        return RedirectResponse("/login")
    user.balance += amount
    db.add(Record(user_id=user.id, action="充值", amount=amount))
    db.commit()
    db.refresh(user)
    db.close()
    return templates.TemplateResponse("me.html", {"request": request, "user": user, "msg": "充值成功"})

@app.get("/ocr_page")
async def ocr_page(request: Request):
    return templates.TemplateResponse("ocr_page.html", {"request": request, "result": None, "error": None, "img_b64": None})

@app.post("/ocr_page")
async def ocr_page_post(request: Request):
    form = await request.form()
    file = form["file"]
    api_key = request.cookies.get("api_key")
    db = SessionLocal()
    user = db.query(User).filter(User.api_key == api_key).first()
    if not user:
        db.close()
        return RedirectResponse("/login")
    if user.balance < OCR_COST:
        db.close()
        return templates.TemplateResponse("ocr_page.html", {"request": request, "result": None, "error": "余额不足，请充值", "img_b64": None})
    try:
        image = await file.read()
        result = ocr.classification(image)
        user.balance -= OCR_COST
        db.add(Record(user_id=user.id, action="识别", amount=-OCR_COST))
        db.commit()
        db.refresh(user)
        db.close()
        img_b64 = "data:image/png;base64," + base64.b64encode(image).decode()
        return templates.TemplateResponse("ocr_page.html", {"request": request, "result": result, "error": None, "img_b64": img_b64})
    except Exception as e:
        db.close()
        return templates.TemplateResponse("ocr_page.html", {"request": request, "result": None, "error": str(e), "img_b64": None})

# 获取当前用户
def get_current_user(token: str = Depends(lambda: None), db: Session = Depends(get_db)):
    from fastapi.security import OAuth2PasswordBearer
    oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")
    token = token or oauth2_scheme()
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="无效token")
    except Exception:
        raise HTTPException(status_code=401, detail="无效token")
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise HTTPException(status_code=401, detail="用户不存在")
    return user

@app.get("/me", response_model=UserInfo)
def get_me(user: User = Depends(get_current_user)):
    return UserInfo(username=user.username, balance=user.balance, api_key=user.api_key)

@app.post("/charge")
def charge(req: ChargeRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user.balance += req.amount
    db.add(Record(user_id=user.id, action="充值", amount=req.amount))
    db.commit()
    return {"msg": "充值成功", "balance": user.balance}

@app.get("/logout")
def logout():
    response = RedirectResponse("/")
    response.delete_cookie("api_key")
    return response

@app.get("/api_demo")
def api_demo(request: Request):
    return templates.TemplateResponse("api_demo.html", {"request": request})

APP_NAME = "ddddocr Server"
APP_VERSION = "1.0.0"
PORT = 8000


if __name__ == "__main__":
    logger.info(f"Starting {APP_NAME} service...")
    try:
        uvicorn.run(app, host="0.0.0.0", port=PORT, log_config=None)
    except Exception as e:
        logger.error(f"Failed to start service: {e}")