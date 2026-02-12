"""
Case Linkage Service
Provides API endpoints for cross-case matching and linkage detection
"""

import logging
import json
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, Query, Path as PathParam
from pydantic import BaseModel

from graph.ingest_to_neo4j import Neo4jIngestor

# Set up logging
logger = logging.getLogger(__name__)

# Define API models
class LinkageMatch(BaseModel):
    """Model for a single linkage match between cases"""
    type: str
    this_case: str
    other_case: str
    entity_type: str
    value: Optional[str] = None
    confidence: float
    
class LinkageEvidence(BaseModel):
    """Model for evidence supporting a case linkage"""
    type: str
    entity_type: str
    value: Optional[str] = None
    confidence: float
    
class CaseLinkage(BaseModel):
    """Model for a case linkage relationship"""
    this_case: str
    other_case: str
    evidence: List[LinkageEvidence]
    confidence: float
    created_at: datetime
    
class LinkageResponse(BaseModel):
    """Response model for linkage API"""
    exact_matches: List[LinkageMatch]
    fuzzy_matches: List[LinkageMatch]
    graph_matches: List[LinkageMatch]
    case_linkages: List[CaseLinkage]

# Create router
router = APIRouter(
    prefix="/api/graph",
    tags=["graph", "linkage"],
    responses={404: {"description": "Not found"}},
)

# Dependency for Neo4j connection
def get_neo4j_ingestor():
    """Dependency to get Neo4j ingestor"""
    ingestor = Neo4jIngestor()
    if not ingestor.driver:
        raise HTTPException(status_code=503, detail="Neo4j connection unavailable")
    return ingestor

@router.post("/linkage/{case_id}", response_model=LinkageResponse)
async def run_case_linkage(
    case_id: str = PathParam(..., description="Case ID to analyze for linkages"),
    ingestor: Neo4jIngestor = Depends(get_neo4j_ingestor)
):
    """
    Run cross-case matching and create linkages for a case
    
    This endpoint:
    1. Finds exact matches (phone numbers, emails, crypto addresses, media hashes)
    2. Finds fuzzy matches (face embeddings, CLIP similarity, text similarity)
    3. Finds graph pattern matches (communication patterns, location patterns)
    4. Creates LINKED_TO relationships in the graph with evidence
    5. Creates Flag nodes for review
    
    Returns all matches and created linkages
    """
    try:
        # Run cross-case matching
        matches = ingestor.run_cross_case_matching(case_id)
        
        # Get created linkages
        linkages = _get_case_linkages(case_id, ingestor)
        
        # Return combined results
        return LinkageResponse(
            exact_matches=matches.get("exact_matches", []),
            fuzzy_matches=matches.get("fuzzy_matches", []),
            graph_matches=matches.get("graph_matches", []),
            case_linkages=linkages
        )
    except Exception as e:
        logger.error(f"Error running case linkage: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error running case linkage: {str(e)}")

@router.get("/linkage/{case_id}", response_model=List[CaseLinkage])
async def get_case_linkages(
    case_id: str = PathParam(..., description="Case ID to get linkages for"),
    ingestor: Neo4jIngestor = Depends(get_neo4j_ingestor)
):
    """
    Get all linkages for a case
    
    Returns all LINKED_TO relationships for the specified case
    """
    try:
        return _get_case_linkages(case_id, ingestor)
    except Exception as e:
        logger.error(f"Error getting case linkages: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting case linkages: {str(e)}")

@router.delete("/linkage/{case_id}/{other_case_id}")
async def delete_case_linkage(
    case_id: str = PathParam(..., description="Source case ID"),
    other_case_id: str = PathParam(..., description="Target case ID"),
    ingestor: Neo4jIngestor = Depends(get_neo4j_ingestor)
):
    """
    Delete a linkage between two cases
    
    Removes the LINKED_TO relationship and associated Flag nodes
    """
    try:
        with ingestor.driver.session() as session:
            # Delete the relationship and flags
            query = """
            MATCH (c1:Case {case_id: $case_id})-[r:LINKED_TO]->(c2:Case {case_id: $other_case_id})
            DELETE r
            
            WITH c1, c2
            MATCH (f:Flag)-[:REFERS_TO]->(c1), (f)-[:REFERS_TO]->(c2)
            WHERE f.type = 'case_linkage'
            DETACH DELETE f
            
            RETURN count(r) as deleted_count
            """
            
            result = session.run(query, case_id=case_id, other_case_id=other_case_id)
            deleted_count = result.single()["deleted_count"]
            
            if deleted_count == 0:
                raise HTTPException(status_code=404, detail="Linkage not found")
                
            return {"status": "success", "message": "Linkage deleted"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting case linkage: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error deleting case linkage: {str(e)}")

@router.put("/linkage/{case_id}/{other_case_id}/review")
async def review_case_linkage(
    case_id: str = PathParam(..., description="Source case ID"),
    other_case_id: str = PathParam(..., description="Target case ID"),
    status: str = Query(..., description="Review status (confirmed, rejected, pending_review)"),
    ingestor: Neo4jIngestor = Depends(get_neo4j_ingestor)
):
    """
    Update the review status of a case linkage
    
    Updates the status of the Flag node associated with the linkage
    """
    valid_statuses = ["confirmed", "rejected", "pending_review"]
    if status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}")
    
    try:
        with ingestor.driver.session() as session:
            # Update flag status
            query = """
            MATCH (c1:Case {case_id: $case_id})-[r:LINKED_TO]->(c2:Case {case_id: $other_case_id})
            MATCH (f:Flag)-[:REFERS_TO]->(c1), (f)-[:REFERS_TO]->(c2)
            WHERE f.type = 'case_linkage'
            
            SET f.status = $status,
                f.reviewed_at = datetime(),
                r.reviewed = true,
                r.review_status = $status
                
            RETURN count(f) as updated_count
            """
            
            result = session.run(query, 
                                case_id=case_id, 
                                other_case_id=other_case_id,
                                status=status)
            updated_count = result.single()["updated_count"]
            
            if updated_count == 0:
                raise HTTPException(status_code=404, detail="Linkage not found")
                
            return {"status": "success", "message": f"Linkage status updated to {status}"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating case linkage status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error updating case linkage status: {str(e)}")

def _get_case_linkages(case_id: str, ingestor: Neo4jIngestor) -> List[CaseLinkage]:
    """
    Helper function to get all linkages for a case
    
    Args:
        case_id: The case ID to get linkages for
        ingestor: Neo4j ingestor instance
        
    Returns:
        List of case linkages
    """
    with ingestor.driver.session() as session:
        query = """
        MATCH (c1:Case {case_id: $case_id})-[r:LINKED_TO]->(c2:Case)
        RETURN c1.case_id as this_case,
               c2.case_id as other_case,
               r.evidence as evidence,
               r.confidence as confidence,
               r.created_at as created_at
        
        UNION
        
        MATCH (c1:Case)-[r:LINKED_TO]->(c2:Case {case_id: $case_id})
        RETURN c2.case_id as this_case,
               c1.case_id as other_case,
               r.evidence as evidence,
               r.confidence as confidence,
               r.created_at as created_at
        """
        
        result = session.run(query, case_id=case_id)
        
        linkages = []
        for record in result:
            # Convert Neo4j datetime to Python datetime
            created_at = record["created_at"]
            if isinstance(created_at, str):
                created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                
            # Parse evidence JSON if needed
            evidence = record["evidence"]
            if isinstance(evidence, str):
                evidence = json.loads(evidence)
                
            linkages.append(CaseLinkage(
                this_case=record["this_case"],
                other_case=record["other_case"],
                evidence=evidence,
                confidence=record["confidence"],
                created_at=created_at
            ))
            
        return linkages