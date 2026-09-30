import streamlit as st
from agent import get_linkedin_agent

st.set_page_config(page_title="Autonomous LinkedIn AI", layout="centered")
st.title("💼 Fully Autonomous LinkedIn Pipeline")
st.write("This system searches the web for a new Data Science topic (avoiding previously used ones), researches it, writes a post, and fact-checks it automatically.")

st.markdown("---")

if st.button("🚀 Start Autonomous Workflow", use_container_width=True):
    orchestrator = get_linkedin_agent()
    
    initial_state = {
        "topic": "",
        "current_draft": "",
        "feedback": "",
        "is_approved": False,
        "iteration_count": 0,
        "final_post_url": ""
    }
    
    with st.status("Agent Workflow Running...", expanded=True) as status:
        for output in orchestrator.stream(initial_state):
            for key, value in output.items():
                if key == "Topic_Agent":
                    st.write(f"🔍 **Topic Agent** found a unique topic: *{value['topic']}*")
                elif key == "Creator":
                    st.write("✍️ **Creator** researched and drafted the post.")
                elif key == "Checker":
                    if value["is_approved"]:
                        st.success("✅ **Checker** fact-checked and approved the post!")
                    else:
                        st.warning(f"⚠️ **Checker** rejected the post. Feedback: {value['feedback']}")
                        st.info("🔄 Sending back to Creator for revision...")
        
        status.update(label="Workflow Complete!", state="complete", expanded=False)
        
    final_state = output["Publisher"]
    
    st.markdown("### 🎉 Final Approved Post")
    st.info(final_state["current_draft"])
    st.markdown(f"**Simulated Live Link:** [{final_state['final_post_url']}]({final_state['final_post_url']})")
    st.write(f"*Total Revisions Needed: {final_state['iteration_count'] - 1}*")