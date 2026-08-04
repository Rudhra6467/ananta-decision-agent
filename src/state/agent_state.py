from typing import TypedDict, Annotated, List, Optional
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    
    # User related
    user_goal: Optional[str]
    risk_tolerance: Optional[str]
    capital: Optional[float]
    preferred_markets: Optional[List[str]]
    experience_level: Optional[str]
    
    # Market related
    market_data: Optional[dict]
    market_regime: Optional[str]
    
    # Decision related
    decision: Optional[str]
    reason: Optional[str]
    confidence: Optional[float]
    
    # Portfolio related
    portfolio: Optional[dict]
    
    # Control
    next_agent: Optional[str]
