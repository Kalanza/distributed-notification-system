from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from jinja2 import Template, TemplateError
from shared.schemas.response_schema import ApiResponse, create_success_response, create_error_response, create_paginated_response
from shared.config.settings import settings
from shared.utils.logger import get_logger
from shared.utils.redis_client import get_redis_client

# Initialize FastAPI app
app = FastAPI(
    title="Template Service - Notification System",
    description="Manages notification templates with versioning",
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
logger = get_logger("template_service", settings.LOG_LEVEL)

# Initialize Redis client
redis_client = get_redis_client()

# Database setup
Base = declarative_base()
engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class NotificationTemplate(Base):
    """Notification template model"""
    __tablename__ = "templates"
    
    id = Column(Integer, primary_key=True, index=True)
    template_id = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    channel = Column(String, nullable=False)  # email or push
    language = Column(String, default="en")
    subject = Column(String, nullable=True)  # For email
    body_text = Column(Text, nullable=False)
    body_html = Column(Text, nullable=True)  # For email
    variables = Column(JSON, default=[])  # List of required variables
    version = Column(Integer, default=1)
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# Pydantic models
class TemplateCreate(BaseModel):
    template_id: str = Field(..., description="Unique template identifier")
    name: str = Field(..., description="Template name")
    channel: str = Field(..., description="Channel: email or push")
    language: str = Field(default="en", description="Template language")
    subject: Optional[str] = Field(None, description="Email subject (for email channel)")
    body_text: str = Field(..., description="Template body text")
    body_html: Optional[str] = Field(None, description="HTML body (for email channel)")
    variables: List[str] = Field(default=[], description="List of required variables")


class TemplateUpdate(BaseModel):
    name: Optional[str] = None
    subject: Optional[str] = None
    body_text: Optional[str] = None
    body_html: Optional[str] = None
    variables: Optional[List[str]] = None
    is_active: Optional[bool] = None


class TemplateResponse(BaseModel):
    id: int
    template_id: str
    name: str
    channel: str
    language: str
    subject: Optional[str]
    body_text: str
    body_html: Optional[str]
    variables: List[str]
    version: int
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class TemplateRenderRequest(BaseModel):
    template_id: str
    variables: Dict[str, Any]
    language: Optional[str] = "en"


class TemplateRenderResponse(BaseModel):
    subject: Optional[str]
    body_text: str
    body_html: Optional[str]


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
    logger.info("Template Service started successfully")


@app.get("/health", response_model=ApiResponse)
async def health_check():
    """Health check endpoint"""
    health_status = {
        "service": "template_service",
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "database": "connected"
    }
    
    return create_success_response(
        data=health_status,
        message="Health check completed"
    )


@app.post("/templates", response_model=ApiResponse[TemplateResponse])
async def create_template(template: TemplateCreate, db: Session = Depends(get_db)):
    """Create a new notification template"""
    try:
        # Check if template_id already exists
        existing = db.query(NotificationTemplate).filter(
            NotificationTemplate.template_id == template.template_id,
            NotificationTemplate.language == template.language
        ).first()
        
        if existing:
            return create_error_response(
                error="template_exists",
                message="Template with this ID and language already exists"
            )
        
        # Validate channel
        if template.channel not in ["email", "push"]:
            return create_error_response(
                error="invalid_channel",
                message="Channel must be 'email' or 'push'"
            )
        
        # Validate email templates have subject
        if template.channel == "email" and not template.subject:
            return create_error_response(
                error="missing_subject",
                message="Email templates must have a subject"
            )
        
        # Create template
        db_template = NotificationTemplate(
            template_id=template.template_id,
            name=template.name,
            channel=template.channel,
            language=template.language,
            subject=template.subject,
            body_text=template.body_text,
            body_html=template.body_html,
            variables=template.variables
        )
        db.add(db_template)
        db.commit()
        db.refresh(db_template)
        
        logger.info(f"Template created: {db_template.template_id}")
        
        return create_success_response(
            data=TemplateResponse.model_validate(db_template),
            message="Template created successfully"
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating template: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/templates/{template_id}", response_model=ApiResponse[TemplateResponse])
async def get_template(
    template_id: str,
    language: str = Query(default="en"),
    db: Session = Depends(get_db)
):
    """Get template by ID and language"""
    # Check cache first
    cache_key = f"template:{template_id}:{language}"
    cached_template = redis_client.get(cache_key)
    if cached_template:
        return create_success_response(
            data=TemplateResponse(**cached_template),
            message="Template retrieved from cache"
        )
    
    template = db.query(NotificationTemplate).filter(
        NotificationTemplate.template_id == template_id,
        NotificationTemplate.language == language,
        NotificationTemplate.is_active == 1
    ).first()
    
    if not template:
        return create_error_response(
            error="not_found",
            message="Template not found"
        )
    
    # Cache template
    template_dict = TemplateResponse.model_validate(template).model_dump()
    redis_client.set(cache_key, template_dict, expire=3600)
    
    return create_success_response(
        data=TemplateResponse.model_validate(template),
        message="Template retrieved successfully"
    )


@app.get("/templates", response_model=ApiResponse[List[TemplateResponse]])
async def list_templates(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    channel: Optional[str] = Query(None),
    language: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """List all templates with pagination and filters"""
    query = db.query(NotificationTemplate)
    
    if channel:
        query = query.filter(NotificationTemplate.channel == channel)
    if language:
        query = query.filter(NotificationTemplate.language == language)
    
    total = query.count()
    templates = query.offset((page - 1) * limit).limit(limit).all()
    
    return create_paginated_response(
        data=[TemplateResponse.model_validate(t) for t in templates],
        total=total,
        page=page,
        limit=limit,
        message="Templates retrieved successfully"
    )


@app.post("/templates/render", response_model=ApiResponse[TemplateRenderResponse])
async def render_template(
    render_request: TemplateRenderRequest,
    db: Session = Depends(get_db)
):
    """Render a template with provided variables"""
    try:
        # Get template
        template = db.query(NotificationTemplate).filter(
            NotificationTemplate.template_id == render_request.template_id,
            NotificationTemplate.language == render_request.language,
            NotificationTemplate.is_active == 1
        ).first()
        
        if not template:
            return create_error_response(
                error="not_found",
                message="Template not found"
            )
        
        # Validate required variables
        missing_vars = set(template.variables) - set(render_request.variables.keys())
        if missing_vars:
            return create_error_response(
                error="missing_variables",
                message=f"Missing required variables: {', '.join(missing_vars)}"
            )
        
        # Render templates
        rendered_subject = None
        if template.subject:
            subject_template = Template(template.subject)
            rendered_subject = subject_template.render(**render_request.variables)
        
        body_text_template = Template(template.body_text)
        rendered_body_text = body_text_template.render(**render_request.variables)
        
        rendered_body_html = None
        if template.body_html:
            html_template = Template(template.body_html)
            rendered_body_html = html_template.render(**render_request.variables)
        
        return create_success_response(
            data=TemplateRenderResponse(
                subject=rendered_subject,
                body_text=rendered_body_text,
                body_html=rendered_body_html
            ),
            message="Template rendered successfully"
        )
    except TemplateError as e:
        logger.error(f"Template rendering error: {str(e)}")
        return create_error_response(
            error="rendering_error",
            message=f"Error rendering template: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error rendering template: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
