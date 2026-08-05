from langgraph.graph import StateGraph, END
from src.state.agent_state import AgentState
from src.agents.supervisor_agent import supervisor_agent
from src.agents.user_understanding_agent import user_understanding_agent
from src.agents.market_regime_agent import market_regime_agent
from src.agents.strategy_recommendation_agent import strategy_recommendation_agent
from src.agents.portfolio_analysis_agent import portfolio_analysis_agent
from src.agents.tool_execution_agent import tool_execution_agent

def build_graph():
    workflow = StateGraph(AgentState)

    # Register all agents
    workflow.add_node("supervisor", supervisor_agent)
    workflow.add_node("user_understanding", user_understanding_agent)
    workflow.add_node("market_regime", market_regime_agent)
    workflow.add_node("strategy_recommendation", strategy_recommendation_agent)
    workflow.add_node("portfolio_analysis", portfolio_analysis_agent)
    workflow.add_node("tool_execution", tool_execution_agent)

    workflow.set_entry_point("supervisor")

    def router(state: AgentState):
        next_agent = state.get("next_agent", "end")

        if next_agent == "user_understanding":
            return "user_understanding"
        elif next_agent == "market_regime":
            return "market_regime"
        elif next_agent == "strategy_recommendation":
            return "strategy_recommendation"
        elif next_agent == "portfolio_analysis":
            return "portfolio_analysis"
        elif next_agent == "tool_execution":
            return "tool_execution"
        else:
            return END

    workflow.add_conditional_edges("supervisor", router)
    workflow.add_edge("user_understanding", "supervisor")
    workflow.add_edge("market_regime", "supervisor")
    workflow.add_edge("strategy_recommendation", "supervisor")
    workflow.add_edge("portfolio_analysis", "supervisor")
    workflow.add_edge("tool_execution", "supervisor")

    return workflow.compile()

agent_graph = build_graph()
