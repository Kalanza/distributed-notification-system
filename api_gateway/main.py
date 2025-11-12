from fastapi import FastAPI, HTTPException, Depends, Header, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List
import uuid
from datetime import datetime
from shared.schemas.notification_schema import NotificationPayload, NotificationStatus
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


@app.post("/notifications/send", response_model=ApiResponse[dict])
@circuit_breaker(failure_threshold=5, recovery_timeout=60, name="send_notification")
async def send_notification(
    payload: NotificationPayload,
    token: Optional[str] = Depends(verify_token)
):
    """
    Send a notification through the appropriate channel
    Supports email and push notifications with idempotency
    """
    correlation_id = payload.correlation_id
    
    try:
        logger.log_notification_lifecycle(
            stage="received",
            request_id=payload.request_id,
            correlation_id=correlation_id,
            status="pending",
            channel=payload.channel,
            user_id=payload.user_id
        )
        
        # Check idempotency - prevent duplicate notifications
        if redis_client.is_notification_processed(payload.request_id):
            logger.warning(
                f"Duplicate notification request: {payload.request_id}",
                correlation_id=correlation_id
            )
            return create_success_response(
                data={"request_id": payload.request_id, "status": "already_processed"},
                message="Notification already processed"
            )
        
        # Check rate limiting
        is_allowed, remaining = redis_client.check_rate_limit(
            user_id=payload.user_id,
            limit=settings.RATE_LIMIT_PER_USER,
            window=settings.RATE_LIMIT_WINDOW
        )
        
        if not is_allowed:
            logger.warning(
                f"Rate limit exceeded for user {payload.user_id}",
                correlation_id=correlation_id
            )
            return create_error_response(
                error="rate_limit_exceeded",
                message=f"Rate limit exceeded. Try again later."
            )
        
        # Validate channel
        if payload.channel not in ["email", "push"]:
            return create_error_response(
                error="invalid_channel",
                message="Channel must be 'email' or 'push'"
            )
        
        # Store notification status
        status = NotificationStatus(
            request_id=payload.request_id,
            user_id=payload.user_id,
            channel=payload.channel,
            status="queued",
            created_at=datetime.utcnow().isoformat(),
            updated_at=datetime.utcnow().isoformat(),
            retry_count=0
        )
        redis_client.set(
            f"notification:status:{payload.request_id}",
            status.model_dump(),
            expire=86400  # 24 hours
        )
        
        # Publish to appropriate queue
        rabbitmq_client.publish_message(
            routing_key=payload.channel,
            message=payload.model_dump(),
            message_id=payload.request_id
        )
        
        # Mark as processed for idempotency
        redis_client.mark_notification_processed(payload.request_id)
        
        logger.log_notification_lifecycle(
            stage="queued",
            request_id=payload.request_id,
            correlation_id=correlation_id,
            status="queued",
            channel=payload.channel,
            remaining_requests=remaining
        )
        
        return create_success_response(
            data={
                "request_id": payload.request_id,
                "status": "queued",
                "channel": payload.channel,
                "correlation_id": correlation_id,
                "remaining_requests": remaining
            },
            message=f"Notification queued successfully for {payload.channel}"
        )
        
    except CircuitBreakerOpenException as e:
        logger.error(f"Circuit breaker open: {str(e)}", correlation_id=correlation_id)
        raise HTTPException(status_code=503, detail="Service temporarily unavailable")
    except Exception as e:
        logger.error(
            f"Error sending notification: {str(e)}",
            correlation_id=correlation_id
        )
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/notifications/status/{request_id}", response_model=ApiResponse[NotificationStatus])
async def get_notification_status(
    request_id: str,
    token: Optional[str] = Depends(verify_token)
):
    """
    Get the status of a notification by request ID
    """
    try:
        status_data = redis_client.get(f"notification:status:{request_id}")
        
        if not status_data:
            return create_error_response(
                error="not_found",
                message="Notification not found"
            )
        
        status = NotificationStatus(**status_data)
        return create_success_response(
            data=status,
            message="Status retrieved successfully"
        )
    except Exception as e:
        logger.error(f"Error retrieving notification status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/notifications/user/{user_id}", response_model=ApiResponse[List[NotificationStatus]])
async def get_user_notifications(
    user_id: int,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
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
