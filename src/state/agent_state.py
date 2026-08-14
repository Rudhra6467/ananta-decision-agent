from typing import TypedDict, Annotated, List, Optional
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    ranking_explanation: Optional[str]

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
    entry_idea: Optional[str]
    stop_loss_idea: Optional[str]
    take_profit_idea: Optional[str]
    execution_status: Optional[str]
    paper_trades: Optional[list]
    strategy_options: Optional[list]

    # Risk / load awareness
    load_level: Optional[str]
    enabled_count: Optional[int]
    open_positions_count: Optional[int]
    disable_suggestions: Optional[list]

    # Portfolio related
    portfolio: Optional[dict]
    # Control
    next_agent: Optional[str]
