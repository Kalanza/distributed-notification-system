from typing import Optional, TypeVar, Generic
from pydantic import BaseModel


T = TypeVar('T')


class PaginationMeta(BaseModel):
    total: int
    limit: int
    page: int
    total_pages: int
    has_next: bool
    has_previous: bool


class ApiResponse(BaseModel, Generic[T]):
    success: bool
    data: Optional[T] = None
    error: Optional[str] = None
    message: str
    meta: Optional[PaginationMeta] = None

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "data": {},
                "error": None,
                "message": "Operation successful",
                "meta": None
            }
        }


def create_success_response(data: Optional[T] = None, message: str = "Success", meta: Optional[PaginationMeta] = None) -> ApiResponse[T]:
    """Create a standardized success response"""
    return ApiResponse(
        success=True,
        data=data,
        error=None,
        message=message,
        meta=meta
    )


def create_error_response(error: str, message: str = "Error occurred") -> ApiResponse:
    """Create a standardized error response"""
    return ApiResponse(
        success=False,
        data=None,
        error=error,
        message=message,
        meta=None
    )


def create_paginated_response(data: T, total: int, page: int, limit: int, message: str = "Success") -> ApiResponse[T]:
    """Create a standardized paginated response"""
    total_pages = (total + limit - 1) // limit  # Ceiling division
    has_next = page < total_pages
    has_previous = page > 1
    
    meta = PaginationMeta(
        total=total,
        limit=limit,
        page=page,
        total_pages=total_pages,
        has_next=has_next,
        has_previous=has_previous
    )
    
    return ApiResponse(
        success=True,
        data=data,
        error=None,
        message=message,
        meta=meta
    )
