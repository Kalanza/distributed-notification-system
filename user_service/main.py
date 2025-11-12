from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime
from shared.schemas.response_schema import ApiResponse, create_success_response, create_error_response, create_paginated_response
from shared.config.settings import settings
from shared.utils.logger import get_logger
from shared.utils.redis_client import get_redis_client
from passlib.context import CryptContext

# Initialize FastAPI app
app = FastAPI(
    title="User Service - Notification System",
    description="Manages user contact info and preferences",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize logger
logger = get_logger("user_service", settings.LOG_LEVEL)

# Initialize Redis client
redis_client = get_redis_client()

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Database setup
Base = declarative_base()
engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class User(Base):
    """User model"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    phone_number = Column(String, nullable=True)
    password_hash = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class UserPreferences(Base):
    """User notification preferences"""
    __tablename__ = "user_preferences"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, unique=True, index=True, nullable=False)
    email_enabled = Column(Boolean, default=True)
    push_enabled = Column(Boolean, default=True)
    push_token = Column(String, nullable=True)
    language = Column(String, default="en")
    timezone = Column(String, default="UTC")
    custom_settings = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# Pydantic models
class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    phone_number: Optional[str] = None
    password: str = Field(..., min_length=6)


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = None
    password: Optional[str] = None


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    phone_number: Optional[str]
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class PreferencesUpdate(BaseModel):
    email_enabled: Optional[bool] = None
    push_enabled: Optional[bool] = None
    push_token: Optional[str] = None
    language: Optional[str] = None
    timezone: Optional[str] = None
    custom_settings: Optional[dict] = None


class PreferencesResponse(BaseModel):
    user_id: int
    email_enabled: bool
    push_enabled: bool
    push_token: Optional[str]
    language: str
    timezone: str
    custom_settings: dict
    
    class Config:
        from_attributes = True


# Database dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.on_event("startup")
async def startup_event():
    """Create database tables on startup"""
    Base.metadata.create_all(bind=engine)
    logger.info("User Service started successfully")


@app.get("/health", response_model=ApiResponse)
async def health_check():
    """Health check endpoint"""
    health_status = {
        "service": "user_service",
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "database": "connected"
    }
    
    return create_success_response(
        data=health_status,
        message="Health check completed"
    )


@app.post("/users", response_model=ApiResponse[UserResponse])
async def create_user(user: UserCreate, db: Session = Depends(get_db)):
    """Create a new user"""
    try:
        # Check if user already exists
        existing_user = db.query(User).filter(
            (User.username == user.username) | (User.email == user.email)
        ).first()
        
        if existing_user:
            return create_error_response(
                error="user_exists",
                message="User with this username or email already exists"
            )
        
        # Hash password
        password_hash = pwd_context.hash(user.password)
        
        # Create user
        db_user = User(
            username=user.username,
            email=user.email,
            phone_number=user.phone_number,
            password_hash=password_hash
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        
        # Create default preferences
        preferences = UserPreferences(user_id=db_user.id)
        db.add(preferences)
        db.commit()
        
        logger.info(f"User created: {db_user.id}")
        
        return create_success_response(
            data=UserResponse.model_validate(db_user),
            message="User created successfully"
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating user: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/users/{user_id}", response_model=ApiResponse[UserResponse])
async def get_user(user_id: int, db: Session = Depends(get_db)):
    """Get user by ID"""
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        return create_error_response(
            error="not_found",
            message="User not found"
        )
    
    return create_success_response(
        data=UserResponse.model_validate(user),
        message="User retrieved successfully"
    )


@app.get("/users", response_model=ApiResponse[List[UserResponse]])
async def list_users(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """List all users with pagination"""
    total = db.query(User).count()
    users = db.query(User).offset((page - 1) * limit).limit(limit).all()
    
    return create_paginated_response(
        data=[UserResponse.model_validate(u) for u in users],
        total=total,
        page=page,
        limit=limit,
        message="Users retrieved successfully"
    )


@app.put("/users/{user_id}", response_model=ApiResponse[UserResponse])
async def update_user(user_id: int, user_update: UserUpdate, db: Session = Depends(get_db)):
    """Update user information"""
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        return create_error_response(
            error="not_found",
            message="User not found"
        )
    
    try:
        if user_update.email:
            user.email = user_update.email
        if user_update.phone_number:
            user.phone_number = user_update.phone_number
        if user_update.password:
            user.password_hash = pwd_context.hash(user_update.password)
        
        user.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(user)
        
        logger.info(f"User updated: {user_id}")
        
        return create_success_response(
            data=UserResponse.model_validate(user),
            message="User updated successfully"
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating user: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/users/{user_id}/preferences", response_model=ApiResponse[PreferencesResponse])
async def get_user_preferences(user_id: int, db: Session = Depends(get_db)):
    """Get user notification preferences"""
    # Check cache first
    cached_prefs = redis_client.get_cached_user_preferences(user_id)
    if cached_prefs:
        return create_success_response(
            data=PreferencesResponse(**cached_prefs),
            message="Preferences retrieved from cache"
        )
    
    preferences = db.query(UserPreferences).filter(UserPreferences.user_id == user_id).first()
    
    if not preferences:
        return create_error_response(
            error="not_found",
            message="Preferences not found"
        )
    
    # Cache preferences
    prefs_dict = PreferencesResponse.model_validate(preferences).model_dump()
    redis_client.cache_user_preferences(user_id, prefs_dict)
    
    return create_success_response(
        data=PreferencesResponse.model_validate(preferences),
        message="Preferences retrieved successfully"
    )


@app.put("/users/{user_id}/preferences", response_model=ApiResponse[PreferencesResponse])
async def update_user_preferences(
    user_id: int,
    prefs_update: PreferencesUpdate,
    db: Session = Depends(get_db)
):
    """Update user notification preferences"""
    preferences = db.query(UserPreferences).filter(UserPreferences.user_id == user_id).first()
    
    if not preferences:
        # Create preferences if they don't exist
        preferences = UserPreferences(user_id=user_id)
        db.add(preferences)
    
    try:
        if prefs_update.email_enabled is not None:
            preferences.email_enabled = prefs_update.email_enabled
        if prefs_update.push_enabled is not None:
            preferences.push_enabled = prefs_update.push_enabled
        if prefs_update.push_token is not None:
            preferences.push_token = prefs_update.push_token
        if prefs_update.language is not None:
            preferences.language = prefs_update.language
        if prefs_update.timezone is not None:
            preferences.timezone = prefs_update.timezone
        if prefs_update.custom_settings is not None:
            preferences.custom_settings = prefs_update.custom_settings
        
        preferences.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(preferences)
        
        # Invalidate cache
        redis_client.delete(f"user:preferences:{user_id}")
        
        logger.info(f"Preferences updated for user: {user_id}")
        
        return create_success_response(
            data=PreferencesResponse.model_validate(preferences),
            message="Preferences updated successfully"
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating preferences: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
