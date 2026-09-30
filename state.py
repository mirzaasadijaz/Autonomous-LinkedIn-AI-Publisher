from typing import TypedDict

class LinkedInPostState(TypedDict):
    """Memory shared between all agents in the loop."""
    topic: str
    current_draft: str
    feedback: str
    is_approved: bool
    iteration_count: int
    final_post_url: str