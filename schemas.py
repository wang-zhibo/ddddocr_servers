from pydantic import BaseModel

class UserCreate(BaseModel):
    username: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class UserInfo(BaseModel):
    username: str
    balance: float
    api_key: str

class ChargeRequest(BaseModel):
    amount: float 