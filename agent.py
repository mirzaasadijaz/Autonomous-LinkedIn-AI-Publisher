from langgraph.graph import StateGraph, END
from state import LinkedInPostState
from nodes import topic_agent, post_creator, post_checker, linkedin_publisher

def routing_logic(state: LinkedInPostState):
    if state["is_approved"]:
        return "Publish"
    else:
        return "Revise" 

def get_linkedin_agent():
    workflow = StateGraph(LinkedInPostState)
    
    workflow.add_node("Topic_Agent", topic_agent)
    workflow.add_node("Creator", post_creator)
    workflow.add_node("Checker", post_checker)
    workflow.add_node("Publisher", linkedin_publisher)
    
    workflow.set_entry_point("Topic_Agent")
    
    workflow.add_edge("Topic_Agent", "Creator")
    workflow.add_edge("Creator", "Checker")
    
    workflow.add_conditional_edges(
        "Checker",
        routing_logic,
        {
            "Publish": "Publisher",
            "Revise": "Creator"
        }
    )
    
    workflow.add_edge("Publisher", END)
    
    return workflow.compile()