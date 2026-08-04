from langgraph.graph import StateGraph, END
from src.state.agent_state import AgentState
from src.agents.supervisor_agent import supervisor_agent
from src.agents.market_regime_agent import market_regime_agent
from src.agents.strategy_recommendation_agent import strategy_recommendation_agent
from src.agents.user_understanding_agent import user_understanding_agent

def build_graph():
    workflow = StateGraph(AgentState)

    # Add agents
    workflow.add_node("supervisor", supervisor_agent)
    workflow.add_node("user_understanding", user_understanding_agent)
    workflow.add_node("market_regime", market_regime_agent)
    workflow.add_node("strategy_recommendation", strategy_recommendation_agent)

    workflow.set_entry_point("supervisor")

    def router(state: AgentState):
        next_agent = state.get("next_agent", "end")

        if next_agent == "user_understanding":
            return "user_understanding"
        elif next_agent == "market_regime":
            return "market_regime"
        elif next_agent == "strategy_recommendation":
            return "strategy_recommendation"
        else:
            return END

    workflow.add_conditional_edges("supervisor", router)
    workflow.add_edge("user_understanding", "supervisor")
    workflow.add_edge("market_regime", "supervisor")
    workflow.add_edge("strategy_recommendation", "supervisor")

    return workflow.compile()

agent_graph = build_graph()
