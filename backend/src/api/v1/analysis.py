"""
Analysis API endpoints
"""

import asyncio
from typing import Dict, Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import StreamingResponse
import structlog

from ...models.analysis import AnalysisRequest, AnalysisResponse
from ...models.requests import AnalysisConfigRequest
from ...services.coordinator import CoordinatorService
from ...utils.exceptions import SIRAException, AnalysisError, ValidationError
from ...utils.logging import log_analysis_event

router = APIRouter()
logger = structlog.get_logger("api.analysis")


def get_coordinator_service(request: Request) -> CoordinatorService:
    """Get coordinator service from app state"""
    if not hasattr(request.app.state, 'coordinator'):
        raise HTTPException(
            status_code=503,
            detail="Coordinator service not available"
        )
    return request.app.state.coordinator


@router.post("/analyze", response_model=AnalysisResponse)
async def start_analysis(
    analysis_request: AnalysisRequest,
    config: AnalysisConfigRequest = None,
    coordinator: CoordinatorService = Depends(get_coordinator_service)
) -> AnalysisResponse:
    """
    Start a new environmental analysis
    
    Args:
        analysis_request: Analysis request data
        config: Optional analysis configuration
        coordinator: Coordinator service
        
    Returns:
        Analysis response with tracking information
    """
    try:
        log_analysis_event(
            logger,
            "Analysis request received",
            "new",
            filename=analysis_request.filename,
            image_type=analysis_request.image_type
        )
        
        # Prepare request data for agents
        request_data = {
            "image_data": analysis_request.image_data,
            "image_type": analysis_request.image_type,
            "filename": analysis_request.filename,
            "coordinates": analysis_request.coordinates,
            "focus_areas": analysis_request.focus_areas,
            "metadata": analysis_request.metadata or {}
        }
        
        # Add configuration if provided
        if config:
            request_data["config"] = {
                "focus_areas": config.focus_areas,
                "detail_level": config.detail_level,
                "include_recommendations": config.include_recommendations,
                "include_confidence_scores": config.include_confidence_scores,
                "language": config.language
            }
        
        # Start analysis
        analysis_response = await coordinator.start_analysis(
            request_data=request_data,
            user_id=analysis_request.user_id
        )
        
        log_analysis_event(
            logger,
            "Analysis started",
            str(analysis_response.analysis_id),
            status=analysis_response.status.value
        )
        
        return analysis_response
        
    except SIRAException:
        raise
    except Exception as e:
        logger.error(
            "Failed to start analysis",
            error=str(e),
            filename=analysis_request.filename,
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start analysis: {str(e)}"
        )


@router.get("/analyze/{analysis_id}", response_model=AnalysisResponse)
async def get_analysis(
    analysis_id: UUID,
    coordinator: CoordinatorService = Depends(get_coordinator_service)
) -> AnalysisResponse:
    """
    Get analysis by ID
    
    Args:
        analysis_id: Analysis ID
        coordinator: Coordinator service
        
    Returns:
        Analysis response
    """
    try:
        analysis = await coordinator.get_analysis(analysis_id)
        
        if not analysis:
            raise HTTPException(
                status_code=404,
                detail=f"Analysis {analysis_id} not found"
            )
        
        log_analysis_event(
            logger,
            "Analysis retrieved",
            str(analysis_id),
            status=analysis.status.value
        )
        
        return analysis
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to get analysis",
            analysis_id=str(analysis_id),
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get analysis: {str(e)}"
        )


@router.get("/analyze/{analysis_id}/progress")
async def get_analysis_progress(
    analysis_id: UUID,
    coordinator: CoordinatorService = Depends(get_coordinator_service)
):
    """
    Get analysis progress (Server-Sent Events)
    
    Args:
        analysis_id: Analysis ID
        coordinator: Coordinator service
        
    Returns:
        SSE stream with progress updates
    """
    async def generate_progress():
        """Generate progress updates"""
        try:
            # Initial check
            analysis = await coordinator.get_analysis(analysis_id)
            if not analysis:
                yield f"data: {{'error': 'Analysis not found'}}\n\n"
                return
            
            # Send initial status
            if analysis.progress:
                yield f"data: {analysis.progress.json()}\n\n"
            
            # Monitor for updates
            max_iterations = 300  # 5 minutes with 1-second intervals
            iteration = 0
            
            while iteration < max_iterations:
                analysis = await coordinator.get_analysis(analysis_id)
                
                if not analysis:
                    yield f"data: {{'error': 'Analysis not found'}}\n\n"
                    break
                
                if analysis.progress:
                    yield f"data: {analysis.progress.json()}\n\n"
                
                # Check if completed
                if analysis.status.value in ["completed", "failed", "cancelled"]:
                    # Send final status
                    final_data = {
                        "analysis_id": str(analysis.analysis_id),
                        "status": analysis.status.value,
                        "progress_percentage": 100.0 if analysis.status.value == "completed" else 0.0,
                        "current_step": "Finalizado",
                        "message": "Análise concluída" if analysis.status.value == "completed" else "Análise falhou",
                        "error_message": analysis.error_message
                    }
                    yield f"data: {str(final_data).replace(\"'\", '\"')}\n\n"
                    break
                
                await asyncio.sleep(1)
                iteration += 1
            
        except Exception as e:
            logger.error(
                "Progress stream error",
                analysis_id=str(analysis_id),
                error=str(e),
                exc_info=True
            )
            yield f"data: {{'error': 'Progress stream failed: {str(e)}'}}\n\n"
    
    return StreamingResponse(
        generate_progress(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control"
        }
    )


@router.delete("/analyze/{analysis_id}")
async def cancel_analysis(
    analysis_id: UUID,
    coordinator: CoordinatorService = Depends(get_coordinator_service)
) -> Dict[str, Any]:
    """
    Cancel an ongoing analysis
    
    Args:
        analysis_id: Analysis ID
        coordinator: Coordinator service
        
    Returns:
        Cancellation confirmation
    """
    try:
        analysis = await coordinator.get_analysis(analysis_id)
        
        if not analysis:
            raise HTTPException(
                status_code=404,
                detail=f"Analysis {analysis_id} not found"
            )
        
        if analysis.status.value not in ["pending", "processing"]:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot cancel analysis in status: {analysis.status.value}"
            )
        
        # Note: In a full implementation, you would implement cancellation logic
        # For now, we'll just return a success message
        
        log_analysis_event(
            logger,
            "Analysis cancellation requested",
            str(analysis_id),
            status=analysis.status.value
        )
        
        return {
            "message": "Analysis cancellation requested",
            "analysis_id": str(analysis_id),
            "status": "cancellation_requested"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to cancel analysis",
            analysis_id=str(analysis_id),
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to cancel analysis: {str(e)}"
        )


@router.get("/analyze/{analysis_id}/result")
async def get_analysis_result(
    analysis_id: UUID,
    coordinator: CoordinatorService = Depends(get_coordinator_service)
) -> Dict[str, Any]:
    """
    Get analysis result (compatible with frontend)
    
    Args:
        analysis_id: Analysis ID
        coordinator: Coordinator service
        
    Returns:
        Analysis result in frontend-compatible format
    """
    try:
        analysis = await coordinator.get_analysis(analysis_id)
        
        if not analysis:
            raise HTTPException(
                status_code=404,
                detail=f"Analysis {analysis_id} not found"
            )
        
        if analysis.status.value != "completed":
            raise HTTPException(
                status_code=400,
                detail=f"Analysis not completed. Status: {analysis.status.value}"
            )
        
        if not analysis.result:
            raise HTTPException(
                status_code=404,
                detail="Analysis result not available"
            )
        
        # Return result in frontend-compatible format
        result_data = {
            "analysis_id": str(analysis.analysis_id),
            "filename": analysis.filename,
            "created_at": analysis.created_at.isoformat(),
            "processing_time": analysis.processing_time,
            "result": analysis.result.dict() if hasattr(analysis.result, 'dict') else analysis.result
        }
        
        log_analysis_event(
            logger,
            "Analysis result retrieved",
            str(analysis_id),
            processing_time=analysis.processing_time
        )
        
        return result_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to get analysis result",
            analysis_id=str(analysis_id),
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get analysis result: {str(e)}"
        )
