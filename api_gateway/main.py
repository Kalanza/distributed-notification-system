from fastapi import FastAPI, HTTPException, Depends, Header, Query, Path
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List
import uuid
from datetime import datetime
from shared.schemas.notification_schema import (
    NotificationPayload,
    NotificationStatusUpdate,
    NotificationStatus,
    NotificationType,
    UserCreate,
    UserResponse
)
from shared.schemas.response_schema import ApiResponse, create_success_response, create_error_response, create_paginated_response
from shared.config.settings import settings
from shared.utils.logger import get_logger
from shared.utils.rabbitmq_client import get_rabbitmq_client
from shared.utils.redis_client import get_redis_client
from shared.utils.circuit_breaker import circuit_breaker, CircuitBreakerOpenException
import json

# Initialize FastAPI app
app = FastAPI(
    title="API Gateway - Notification System",
    description="Entry point for all notification requests",
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
logger = get_logger("api_gateway", settings.LOG_LEVEL)

# Initialize clients
rabbitmq_client = get_rabbitmq_client()
redis_client = get_redis_client()


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    try:
        rabbitmq_client.connect()
        rabbitmq_client.setup_exchange_and_queues()
        logger.info("API Gateway started successfully")
    except Exception as e:
        logger.error(f"Failed to start API Gateway: {str(e)}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    rabbitmq_client.close()
    logger.info("API Gateway shutdown complete")


def verify_token(authorization: Optional[str] = Header(None)) -> Optional[str]:
    """Simple token verification (expand with JWT validation in production)"""
    if not authorization:
        return None
    return authorization.replace("Bearer ", "")


@app.get("/health", response_model=ApiResponse)
async def health_check():
    """
    Health check endpoint
    Returns the health status of the service and its dependencies
    """
    health_status = {
        "service": "api_gateway",
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "dependencies": {
            "rabbitmq": rabbitmq_client.health_check(),
            "redis": redis_client.health_check()
        }
    }
    
    all_healthy = all(health_status["dependencies"].values())
    
    if not all_healthy:
        health_status["status"] = "degraded"
    
    return create_success_response(
        data=health_status,
        message="Health check completed"
    )


@app.post("/api/v1/notifications/", response_model=ApiResponse[dict])
@circuit_breaker(failure_threshold=5, recovery_timeout=60, name="send_notification")
async def send_notification(
    payload: NotificationPayload,
    token: Optional[str] = Depends(verify_token)
):
    """
    Send a notification through the appropriate channel
    Supports email and push notifications with idempotency
    
    Request body:
    - notification_type: Type of notification (email or push)
    - user_id: User UUID
    - template_code: Template code or path
    - variables: User data for template (name, link, meta)
    - request_id: Unique request ID (auto-generated if not provided)
    - priority: Priority level 1-10 (lower is higher priority)
    - metadata: Optional additional metadata
    """
    try:
        logger.info(
            f"Notification request received: {payload.request_id}",
            correlation_id=payload.request_id
        )
        
        # Check idempotency - prevent duplicate notifications
        if redis_client.is_notification_processed(payload.request_id):
            logger.warning(
                f"Duplicate notification request: {payload.request_id}",
                correlation_id=payload.request_id
            )
            return create_success_response(
                data={"request_id": payload.request_id, "status": "already_processed"},
                message="Notification already processed"
            )
        
        # Check rate limiting
        is_allowed, remaining = redis_client.check_rate_limit(
            user_id=int(uuid.UUID(payload.user_id).int % (2**31)),  # Convert UUID to int for rate limiting
            limit=settings.RATE_LIMIT_PER_USER,
            window=settings.RATE_LIMIT_WINDOW
        )
        
        if not is_allowed:
            logger.warning(
                f"Rate limit exceeded for user {payload.user_id}",
                correlation_id=payload.request_id
            )
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded. Try again later."
            )
        
        # Create notification ID
        notification_id = str(uuid.uuid4())
        
        # Store notification status
        status_update = NotificationStatusUpdate(
            notification_id=notification_id,
            status=NotificationStatus.pending,
            timestamp=datetime.utcnow(),
            error=None
        )
        redis_client.set(
            f"notification:status:{notification_id}",
            status_update.model_dump(mode='json'),
            expire=86400  # 24 hours
        )
        
        # Prepare message for queue
        queue_message = {
            "notification_id": notification_id,
            "request_id": payload.request_id,
            "user_id": payload.user_id,
            "notification_type": payload.notification_type.value,
            "template_code": payload.template_code,
            "variables": payload.variables.model_dump(),
            "priority": payload.priority,
            "metadata": payload.metadata,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Publish to appropriate queue
        rabbitmq_client.publish_message(
            routing_key=payload.notification_type.value,
            message=queue_message,
            message_id=payload.request_id
        )
        
        # Mark as processed for idempotency
        redis_client.mark_notification_processed(payload.request_id)
        
        logger.info(
            f"Notification queued: {notification_id} via {payload.notification_type.value}",
            correlation_id=payload.request_id
        )
        
        return create_success_response(
            data={
                "notification_id": notification_id,
                "request_id": payload.request_id,
                "status": "pending",
                "notification_type": payload.notification_type.value,
                "remaining_requests": remaining
            },
            message=f"Notification queued successfully for {payload.notification_type.value}"
        )
        
    except CircuitBreakerOpenException as e:
        logger.error(f"Circuit breaker open: {str(e)}", correlation_id=payload.request_id)
        raise HTTPException(status_code=503, detail="Service temporarily unavailable")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error sending notification: {str(e)}",
            correlation_id=payload.request_id
        )
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/users/", response_model=ApiResponse[UserResponse])
async def create_user(
    user: UserCreate,
    token: Optional[str] = Depends(verify_token)
):
    """
    Create a new user
    
    Request body:
    - name: User's full name
    - email: User's email address
    - push_token: Optional push notification token
    - preferences: Notification preferences (email, push)
    - password: User password (min 8 characters)
    """
    try:
        # Generate user ID
        user_id = str(uuid.uuid4())
        
        # In production, hash password and store in database
        # For now, store basic user data in Redis
        user_data = {
            "user_id": user_id,
            "name": user.name,
            "email": user.email,
            "push_token": user.push_token,
            "preferences": user.preferences.model_dump(),
            "created_at": datetime.utcnow().isoformat()
        }
        
        # Store in Redis (in production, use PostgreSQL)
        redis_client.set(
            f"user:{user_id}",
            user_data,
            expire=None  # No expiration for user data
        )
        
        # Also index by email for lookup
        redis_client.set(
            f"user:email:{user.email}",
            {"user_id": user_id},
            expire=None
        )
        
        logger.info(f"User created: {user_id} ({user.email})")
        
        response_data = UserResponse(
            user_id=user_id,
            name=user.name,
            email=user.email,
            push_token=user.push_token,
            preferences=user.preferences,
            created_at=datetime.utcnow()
        )
        
        return create_success_response(
            data=response_data,
            message="User created successfully"
        )
        
    except Exception as e:
        logger.error(f"Error creating user: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/{notification_type}/status/", response_model=ApiResponse[dict])
async def update_notification_status(
    notification_type: NotificationType,
    status_update: NotificationStatusUpdate,
    token: Optional[str] = Depends(verify_token)
):
    """
    Update the status of a notification
    
    Path parameter:
    - notification_type: Type of notification (email or push)
    
    Request body:
    - notification_id: Notification ID
    - status: New status (delivered, pending, failed)
    - timestamp: Optional timestamp of status update
    - error: Optional error message if failed
    """
    try:
        # Retrieve existing status
        existing_data = redis_client.get(f"notification:status:{status_update.notification_id}")
        
        if not existing_data:
            raise HTTPException(
                status_code=404,
                detail="Notification not found"
            )
        
        # Update status
        redis_client.set(
            f"notification:status:{status_update.notification_id}",
            status_update.model_dump(mode='json'),
            expire=86400  # 24 hours
        )
        
        logger.info(
            f"Status updated for {status_update.notification_id}: {status_update.status.value}",
            correlation_id=status_update.notification_id
        )
        
        return create_success_response(
            data={
                "notification_id": status_update.notification_id,
                "status": status_update.status.value,
                "timestamp": status_update.timestamp.isoformat() if status_update.timestamp else datetime.utcnow().isoformat()
            },
            message="Notification status updated successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating notification status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/notifications/{notification_id}/status", response_model=ApiResponse[NotificationStatusUpdate])
async def get_notification_status(
    notification_id: str = Path(..., description="Notification ID"),
    token: Optional[str] = Depends(verify_token)
):
    """
    Get the status of a notification by notification ID
    """
    try:
        status_data = redis_client.get(f"notification:status:{notification_id}")
        
        if not status_data:
            raise HTTPException(
                status_code=404,
                detail="Notification not found"
            )
        
        status = NotificationStatusUpdate(**status_data)
        return create_success_response(
            data=status,
            message="Status retrieved successfully"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving notification status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/users/{user_id}", response_model=ApiResponse[UserResponse])
async def get_user(
    user_id: str = Path(..., description="User UUID"),
    token: Optional[str] = Depends(verify_token)
):
    """
    Get user information by user ID
    """
    try:
        user_data = redis_client.get(f"user:{user_id}")
        
        if not user_data:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )
        
        user = UserResponse(**user_data)
        return create_success_response(
            data=user,
            message="User retrieved successfully"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving user: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/users/{user_id}/notifications", response_model=ApiResponse[List[NotificationStatusUpdate]])
async def get_user_notifications(
    user_id: str = Path(..., description="User UUID"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    token: Optional[str] = Depends(verify_token)
):
    """
    Get all notifications for a specific user with pagination
    """
    try:
        # In production, this would query a database
        # For now, return a placeholder response
        notifications = []
        total = 0
        
        return create_paginated_response(
            data=notifications,
            total=total,
            page=page,
            limit=limit,
            message="User notifications retrieved successfully"
        )
    except Exception as e:
        logger.error(f"Error retrieving user notifications: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/metrics", response_model=ApiResponse[dict])
async def get_metrics():
    """
    Get API Gateway metrics
    """
    try:
        # In production, collect real metrics
        metrics = {
            "total_notifications_sent": 0,
            "email_notifications": 0,
            "push_notifications": 0,
            "failed_notifications": 0,
            "average_response_time_ms": 0,
            "uptime_seconds": 0
        }
        
        return create_success_response(
            data=metrics,
            message="Metrics retrieved successfully"
        )
    except Exception as e:
        logger.error(f"Error retrieving metrics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
