"""
AI Health Assistant Decision-Tree Router:
Endpoints for traversing the healthcare decision tree prototype,
providing safe guidance on HRT, crisis triage, surgery coverage, and affirmative care.
"""
from fastapi import APIRouter, HTTPException

from app import schemas
from app.services import health_assistant

router = APIRouter(prefix="/health-assistant", tags=["ai-health-assistant"])


@router.get("/tree", response_model=schemas.HealthTraverseResponse)
def get_initial_tree():
    """
    Returns the initial root node of the healthcare decision tree.
    Provides entry points for Crisis SOS, Safe HRT, Surgeries, and Mental Health.
    """
    root_node = health_assistant.get_decision_tree()
    return schemas.HealthTraverseResponse(
        node=root_node,
        disclaimer=health_assistant.HEALTH_DISCLAIMER,
    )


@router.get("/nodes/{node_id}", response_model=schemas.HealthTraverseResponse)
def get_node_by_id(node_id: str):
    """Retrieve a specific decision node by its ID."""
    node_data = health_assistant.DECISION_NODES.get(node_id)
    if not node_data:
        raise HTTPException(status_code=404, detail="Decision node not found")

    node = health_assistant._build_node_schema(node_data)
    return schemas.HealthTraverseResponse(
        node=node,
        disclaimer=health_assistant.HEALTH_DISCLAIMER,
    )


@router.post("/traverse", response_model=schemas.HealthTraverseResponse)
def traverse_decision_tree(req: schemas.HealthTraverseRequest):
    """
    Step through the decision tree by submitting the current node and selected option ID.
    Returns the next guidance node, warnings, recommended actions, and emergency contacts.
    """
    return health_assistant.traverse_decision_tree(req.current_node_id, req.option_id)
