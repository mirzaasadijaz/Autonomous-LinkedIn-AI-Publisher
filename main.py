from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from langgraph.graph import StateGraph, END
import uvicorn

from state import LinkedInPostState
from nodes import topic_agent, post_creator, post_checker, linkedin_publisher

app = FastAPI(title="AI Agent Publisher API")

# ---------------------------------------------------------
# SETUP LANGGRAPH PIPELINE
# ---------------------------------------------------------
workflow = StateGraph(LinkedInPostState)

workflow.add_node("topic_agent", topic_agent)
workflow.add_node("post_creator", post_creator)
workflow.add_node("post_checker", post_checker)
workflow.add_node("linkedin_publisher", linkedin_publisher)

workflow.set_entry_point("topic_agent")
workflow.add_edge("topic_agent", "post_creator")
workflow.add_edge("post_creator", "post_checker")

# Conditional Edge for Checker
def check_approval(state):
    if state.get("is_approved"):
        return "linkedin_publisher"
    return "post_creator"

workflow.add_conditional_edges("post_checker", check_approval)
workflow.add_edge("linkedin_publisher", END)

app_graph = workflow.compile()

# ---------------------------------------------------------
# FASTAPI ROUTES
# ---------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
async def serve_ui():
    """HTML to frontend -> serve"""
    with open("index.html", "r", encoding="utf-8") as f:
        return f.read()

@app.post("/api/generate-and-post")
async def run_pipeline():
    """Agent pipeline -> trigger"""
    initial_state = {
        "topic": "", 
        "current_draft": "", 
        "is_approved": False, 
        "feedback": "", 
        "iteration_count": 0, 
        "final_post_url": ""
    }
    
    # Run the AI Graph
    final_state = app_graph.invoke(initial_state)
    
    return {
        "status": "success",
        "topic": final_state.get("topic"),
        "draft": final_state.get("current_draft"),
        "result_message": final_state.get("final_post_url")
    }

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8080)