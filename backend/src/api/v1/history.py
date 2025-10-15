"""
History API endpoints
"""

from datetime import datetime
from typing import Dict, Any, List, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, Depends, Query
from google.cloud import firestore
import structlog

from ...models.requests import HistoryRequest
from ...config import settings
from ...utils.exceptions import DatabaseError

router = APIRouter()
logger = structlog.get_logger("api.history")


def get_firestore_client() -> firestore.AsyncClient:
    """Get Firestore client"""
    return firestore.AsyncClient(
        project=settings.google_cloud_project,
        database=settings.firestore_database
    )


@router.get("/history")
async def get_analysis_history(
    user_id: Optional[str] = Query(None, description="User ID filter"),
    limit: int = Query(20, ge=1, le=100, description="Number of results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    status_filter: Optional[str] = Query(None, description="Status filter"),
    start_date: Optional[datetime] = Query(None, description="Start date filter"),
    end_date: Optional[datetime] = Query(None, description="End date filter")
) -> Dict[str, Any]:
    """
    Get analysis history with filtering and pagination
    
    Args:
        user_id: Optional user ID filter
        limit: Number of results to return
        offset: Offset for pagination
        status_filter: Optional status filter
        start_date: Optional start date filter
        end_date: Optional end date filter
        
    Returns:
        Paginated analysis history
    """
    try:
        db = get_firestore_client()
        
        # Build query
        query = db.collection(settings.analyses_collection)
        
        # Apply filters
        if user_id:
            query = query.where("user_id", "==", user_id)
        
        if status_filter:
            query = query.where("status", "==", status_filter)
        
        if start_date:
            query = query.where("created_at", ">=", start_date)
        
        if end_date:
            query = query.where("created_at", "<=", end_date)
        
        # Order by creation date (descending)
        query = query.order_by("created_at", direction=firestore.Query.DESCENDING)
        
        # Apply pagination
        query = query.offset(offset).limit(limit)
        
        # Execute query
        docs = query.stream()
        
        # Process results
        analyses = []
        async for doc in docs:
            data = doc.to_dict()
            data["analysis_id"] = doc.id
            analyses.append(data)
        
        # Get total count (for pagination info)
        # Note: This is a simplified approach. In production, you might want to cache this
        count_query = db.collection(settings.analyses_collection)
        if user_id:
            count_query = count_query.where("user_id", "==", user_id)
        if status_filter:
            count_query = count_query.where("status", "==", status_filter)
        
        total_count = len([doc async for doc in count_query.stream()])
        
        logger.info(
            "History retrieved",
            user_id=user_id,
            count=len(analyses),
            total_count=total_count,
            offset=offset,
            limit=limit
        )
        
        return {
            "analyses": analyses,
            "pagination": {
                "offset": offset,
                "limit": limit,
                "total": total_count,
                "has_more": offset + len(analyses) < total_count
            },
            "filters": {
                "user_id": user_id,
                "status_filter": status_filter,
                "start_date": start_date.isoformat() if start_date else None,
                "end_date": end_date.isoformat() if end_date else None
            }
        }
        
    except Exception as e:
        logger.error(
            "Failed to get analysis history",
            error=str(e),
            user_id=user_id,
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get analysis history: {str(e)}"
        )


@router.get("/history/stats")
async def get_analysis_stats(
    user_id: Optional[str] = Query(None, description="User ID filter")
) -> Dict[str, Any]:
    """
    Get analysis statistics
    
    Args:
        user_id: Optional user ID filter
        
    Returns:
        Analysis statistics
    """
    try:
        db = get_firestore_client()
        
        # Build base query
        query = db.collection(settings.analyses_collection)
        if user_id:
            query = query.where("user_id", "==", user_id)
        
        # Get all analyses
        docs = query.stream()
        
        # Calculate statistics
        stats = {
            "total_analyses": 0,
            "status_breakdown": {
                "completed": 0,
                "failed": 0,
                "processing": 0,
                "pending": 0,
                "cancelled": 0
            },
            "recent_activity": {
                "last_24h": 0,
                "last_7d": 0,
                "last_30d": 0
            },
            "average_processing_time": 0,
            "success_rate": 0
        }
        
        now = datetime.utcnow()
        processing_times = []
        
        async for doc in docs:
            data = doc.to_dict()
            stats["total_analyses"] += 1
            
            # Status breakdown
            status = data.get("status", "unknown")
            if status in stats["status_breakdown"]:
                stats["status_breakdown"][status] += 1
            
            # Recent activity
            created_at = data.get("created_at")
            if created_at:
                if isinstance(created_at, str):
                    created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                
                time_diff = (now - created_at).total_seconds()
                
                if time_diff <= 24 * 3600:  # 24 hours
                    stats["recent_activity"]["last_24h"] += 1
                if time_diff <= 7 * 24 * 3600:  # 7 days
                    stats["recent_activity"]["last_7d"] += 1
                if time_diff <= 30 * 24 * 3600:  # 30 days
                    stats["recent_activity"]["last_30d"] += 1
            
            # Processing time
            processing_time = data.get("processing_time")
            if processing_time and isinstance(processing_time, (int, float)):
                processing_times.append(processing_time)
        
        # Calculate averages
        if processing_times:
            stats["average_processing_time"] = sum(processing_times) / len(processing_times)
        
        # Calculate success rate
        if stats["total_analyses"] > 0:
            completed = stats["status_breakdown"]["completed"]
            stats["success_rate"] = (completed / stats["total_analyses"]) * 100
        
        logger.info(
            "Statistics calculated",
            user_id=user_id,
            total_analyses=stats["total_analyses"],
            success_rate=stats["success_rate"]
        )
        
        return stats
        
    except Exception as e:
        logger.error(
            "Failed to get analysis statistics",
            error=str(e),
            user_id=user_id,
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get analysis statistics: {str(e)}"
        )


@router.delete("/history/{analysis_id}")
async def delete_analysis(
    analysis_id: UUID,
    user_id: Optional[str] = Query(None, description="User ID for authorization")
) -> Dict[str, Any]:
    """
    Delete an analysis from history
    
    Args:
        analysis_id: Analysis ID to delete
        user_id: Optional user ID for authorization
        
    Returns:
        Deletion confirmation
    """
    try:
        db = get_firestore_client()
        
        # Get analysis document
        doc_ref = db.collection(settings.analyses_collection).document(str(analysis_id))
        doc = await doc_ref.get()
        
        if not doc.exists:
            raise HTTPException(
                status_code=404,
                detail=f"Analysis {analysis_id} not found"
            )
        
        # Check authorization (if user_id provided)
        if user_id:
            data = doc.to_dict()
            if data.get("user_id") != user_id:
                raise HTTPException(
                    status_code=403,
                    detail="Not authorized to delete this analysis"
                )
        
        # Delete the document
        await doc_ref.delete()
        
        logger.info(
            "Analysis deleted",
            analysis_id=str(analysis_id),
            user_id=user_id
        )
        
        return {
            "message": "Analysis deleted successfully",
            "analysis_id": str(analysis_id)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to delete analysis",
            analysis_id=str(analysis_id),
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete analysis: {str(e)}"
        )
