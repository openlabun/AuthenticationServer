from datetime import datetime, timedelta, timezone
from typing import List

import jwt
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import Column, ForeignKey, Integer, String, create_engine
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base = declarative_base()
engine = create_engine('sqlite:///./auth.db')
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Contract(Base):
    __tablename__ = 'contracts'
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, index=True)
    app_name = Column(String, index=True)
    users = relationship("User", back_populates="contract")


class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    first_name = Column(String)
    last_name = Column(String)
    password = Column(String)
    contract_id = Column(Integer, ForeignKey('contracts.id'))
    contract = relationship("Contract", back_populates="users")


Base.metadata.create_all(bind=engine)


class UserSchema(BaseModel):
    username: str
    first_name: str
    last_name: str
    password: str


class ContractSchema(BaseModel):
    key: str
    app_name: str


class LoginSchema(BaseModel):
    username: str
    password: str
    app_name: str


class DisplayUser(BaseModel):
    username: str
    first_name: str
    last_name: str


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.post("/create-contract", response_model=ContractSchema)
def create_contract(app_name: str, db: SessionLocal = Depends(get_db)):
    import uuid
    new_key = str(uuid.uuid4())
    contract = Contract(key=new_key, app_name=app_name)
    db.add(contract)
    db.commit()
    db.refresh(contract)
    return {"key": contract.key, "app_name": contract.app_name}


@app.post("/register")
async def register(data: UserSchema, contract_key: str, db: SessionLocal = Depends(get_db)):
    contract = db.query(Contract).filter(Contract.key == contract_key).first()
    if not contract:
        raise HTTPException(status_code=400, detail="Invalid contract key")
    
    if len(contract.users) >= 100:
        raise HTTPException(status_code=400, detail="User limit reached for this contract")
    
    existing_user = db.query(User).filter(User.username == data.username, User.contract_id == contract.id).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already registered within this contract")
    
    new_user = User(
        username=data.username,
        first_name=data.first_name,
        last_name=data.last_name,
        password=data.password,
        contract_id=contract.id
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {
        "username": new_user.username,
        "first_name": new_user.first_name,
        "last_name": new_user.last_name,
    }


@app.get("/users")
async def list_users(contract_key: str, db: SessionLocal = Depends(get_db)) -> List[DisplayUser]:
    contract = db.query(Contract).filter(Contract.key == contract_key).first()
    if not contract:
        raise HTTPException(status_code=400, detail="Invalid contract key")
    
    return [
        DisplayUser(username=user.username, first_name=user.first_name, last_name=user.last_name)
        for user in contract.users
    ]


@app.post("/delete-all")
def delete_all(contract_key: str, db: SessionLocal = Depends(get_db)):
    contract = db.query(Contract).filter(Contract.key == contract_key).first()
    if not contract:
        raise HTTPException(status_code=400, detail="Invalid contract key")
    
    for user in contract.users:
        db.delete(user)
    db.commit()
    return {"message": "All users deleted"}


JWT_SECRET = "supersecret"
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_MINUTES = 1440


def authenticate_user(username: str, password: str, app_name: str, db: SessionLocal):
    user = db.query(User).join(Contract).filter(User.username == username, Contract.app_name == app_name).first()
    if not user or user.password != password:
        return False
    return user


def create_jwt_token(user: User):
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token_expires = timedelta(minutes=REFRESH_TOKEN_EXPIRE_MINUTES)
    access_token = jwt.encode(
        {"sub": user.username, "exp": datetime.now(timezone.utc) + access_token_expires},
        JWT_SECRET,
        algorithm=JWT_ALGORITHM,
    )
    refresh_token = jwt.encode(
        {"sub": user.username, "exp": datetime.now(timezone.utc) + refresh_token_expires},
        JWT_SECRET,
        algorithm=JWT_ALGORITHM,
    )
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


class RefreshScheme(BaseModel):
    refresh_token: str


@app.get("/me")
async def me(token: str , db: SessionLocal = Depends(get_db)):
    if not token:
        raise HTTPException(status_code=401, detail="Token is missing")
    try:
        decoded_token = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        username = decoded_token["sub"]
        user = db.query(User).filter(User.username == username).first()
        if not user:
            raise HTTPException(status_code=401, detail="User does not exist")
        return {
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
        }
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

@app.post("/refresh")
async def refresh_token(data: RefreshScheme):
    try:
        decoded_token = jwt.decode(
            data.refresh_token, JWT_SECRET, algorithms=[JWT_ALGORITHM]
        )
        username = decoded_token["sub"]
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = jwt.encode(
            {"sub": username, "exp": datetime.utcnow() + access_token_expires},
            JWT_SECRET,
            algorithm=JWT_ALGORITHM,
        )
        return {"access_token": access_token, "token_type": "bearer"}
    except Exception as e:
        print(e)
        raise HTTPException(status_code=401, detail="Invalid refresh token")


@app.delete("/delete-contract")
def delete_contract(contract_key: str, db: SessionLocal = Depends(get_db)):
    contract = db.query(Contract).filter(Contract.key == contract_key).first()
    if not contract:
        raise HTTPException(status_code=400, detail="Invalid contract key")
    
    db.delete(contract)
    db.commit()
    return {"message": "Contract deleted"}


@app.post("/login")
async def login(data: LoginSchema, db: SessionLocal = Depends(get_db)):
    user = authenticate_user(data.username, data.password, data.app_name, db)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username, password, or app name")
    return create_jwt_token(user)
