import os
import sqlite3
import time  
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.tools.tavily_search import TavilySearchResults
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage
from state import LinkedInPostState
import requests

load_dotenv()
LINKEDIN_ACCESS_TOKEN = os.getenv("LINKEDIN_ACCESS_TOKEN")

# ---------------------------------------------------------
# HELPER FUNCTION FOR GEMINI RESPONSE
# ---------------------------------------------------------
def extract_text(content):
    """The Gemini API sometimes returns a list; this safely converts it into a string."""
    if isinstance(content, list):
        return "".join([item.get("text", str(item)) if isinstance(item, dict) else str(item) for item in content])
    return str(content)

# ---------------------------------------------------------
# DATABASE SETUP FOR TOPICS (Preventing Duplicates)
# ---------------------------------------------------------
conn = sqlite3.connect("used_topics.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS topics (topic_name TEXT)")
conn.commit()

def is_topic_used(topic: str) -> bool:
    cursor.execute("SELECT 1 FROM topics WHERE topic_name = ?", (topic,))
    return cursor.fetchone() is not None

def mark_topic_used(topic: str):
    cursor.execute("INSERT INTO topics (topic_name) VALUES (?)", (topic,))
    conn.commit()

def get_all_used_topics():
    """Retrieves up to 5 previously used topics from the database."""
    cursor.execute("SELECT topic_name FROM topics ORDER BY ROWID DESC LIMIT 5")
    topics = [row[0] for row in cursor.fetchall()]
    return topics if topics else ["No topics used yet."]

# ---------------------------------------------------------
# TOOLS & SUB-AGENTS SETUP
# ---------------------------------------------------------
# Tavily tool will automatically use TAVILY_API_KEY from .env
web_tool = TavilySearchResults(max_results=2)

# max_retries and timeout to prevent Connection Drops
llm = ChatGoogleGenerativeAI(
    model="gemini-3.1-flash-lite", 
    temperature=0.7,
    max_retries=3,
    timeout=60
)

checker_llm = ChatGoogleGenerativeAI(
    model="gemini-3.1-flash-lite", 
    temperature=0,
    max_retries=3,
    timeout=60
)

topic_sub_agent = create_react_agent(llm, tools=[web_tool])
creator_sub_agent = create_react_agent(llm, tools=[web_tool])
checker_sub_agent = create_react_agent(checker_llm, tools=[web_tool])

# ---------------------------------------------------------
# AGENT NODES
# ---------------------------------------------------------
def topic_agent(state: LinkedInPostState) -> LinkedInPostState:
    print("🔍 Topic Agent: Searching the web for a new topic...")
    
    used_topics_list = get_all_used_topics()
    
    prompt = f"""You are an expert Data Science Content Strategist.
    Your task is to find a fresh, highly engaging, and trending topic in Data Science, AI, or Machine Learning.
    
    🚨 STRICT RESTRICTION 🚨
    Here is the list of topics we have ALREADY posted about. You MUST NOT choose any topic that is similar to these:
    {used_topics_list}
    
    Use your Tavily search tool to find a completely NEW trend, breakthrough, or best practice from the last few weeks.
    Output ONLY the exact topic title. Do not add any introductory words or quotes."""
    
    response = topic_sub_agent.invoke({"messages": [HumanMessage(content=prompt)]})
    
    # Safe Extract
    raw_content = extract_text(response["messages"][-1].content)
    proposed_topic = raw_content.strip()
    
    if is_topic_used(proposed_topic):
        print(f"⚠️ Warning: AI picked a used topic '{proposed_topic}'. Forcing variation.")
        proposed_topic = proposed_topic + " - Advanced Techniques & New Updates"
        
    print(f"✅ Selected Unique Topic: {proposed_topic}")
    mark_topic_used(proposed_topic)
    
    state["topic"] = proposed_topic
    
    # Pause to prevent rate limit (429 Error)
    print("⏳ Pausing for 5 seconds to avoid API rate limits...")
    time.sleep(5)
    
    return state

def post_creator(state: LinkedInPostState) -> LinkedInPostState:
    print("✍️ Creator: Researching and Drafting...")
    
    topic = state["topic"]
    feedback = state.get("feedback", "")
    iteration = state.get("iteration_count", 0)

    if feedback:
        prompt = f"""Rewrite this Data Science LinkedIn post based on the reviewer's feedback.
        Original Topic: {topic}
        Feedback: {feedback}
        Current Draft: {state['current_draft']}
        Write the post in strictly PLAIN TEXT. Do NOT use any Markdown formatting or asterisks (*).
        """
    else:
        prompt = f"""You are an expert Data Scientist. 
        Topic: {topic}
        
        Step 1: Use your search tool to find 1 or 2 quick facts or updates about this topic.
        Step 2: Write an engaging social media post for an AI/Tech audience using those facts. Include bullet points and 3-5 hashtags.
        
        🚨 STRICT FORMATTING RULES 🚨
        - OUTPUT ONLY THE FINAL POST. 
        - DO NOT print your research notes or the facts you found.
        - DO NOT include introductory titles like "LinkedIn Post:" or "Here is the post:".
        - DO NOT use any Markdown formatting, bolding, italics, dividers (***), or asterisks (*).
        - Write strictly in PLAIN TEXT.
        """

    response = creator_sub_agent.invoke({"messages": [HumanMessage(content=prompt)]})
    
    # Safe Extract
    state["current_draft"] = extract_text(response["messages"][-1].content)
    state["iteration_count"] = iteration + 1
    
    # Pause to prevent rate limit (429 Error)
    print("⏳ Pausing for 5 seconds to avoid API rate limits...")
    time.sleep(5)
    
    return state

def post_checker(state: LinkedInPostState) -> LinkedInPostState:
    print("🧐 Checker: Fact-checking and Reviewing...")
    
    draft = state["current_draft"]
    iteration = state["iteration_count"]

    prompt = f"""You are a strict Technical Editor. 
    Draft:
    {draft}
    
    1. Use your search tool to quickly verify any bold claims or stats in this draft.
    2. Review if it sounds professional and not overly generic.

    Respond STRICTLY with:
    APPROVED: [True or False]
    FEEDBACK: [Your feedback or fact-check corrections]
    """
    
    response = checker_sub_agent.invoke({"messages": [HumanMessage(content=prompt)]})
    
    # Safe Extract
    checker_output = extract_text(response["messages"][-1].content)
    
    is_approved = "APPROVED: True" in checker_output
    feedback = checker_output.split("FEEDBACK:")[-1].strip() if "FEEDBACK:" in checker_output else "Looks good."

    if iteration >= 3:
        print("⚠️ Max iterations reached. Auto-approving.")
        is_approved = True
        feedback = "Auto-approved to prevent infinite loop."

    state["is_approved"] = is_approved
    state["feedback"] = feedback
    
    if is_approved:
        print("✅ Checker: Approved!")
    else:
        print(f"❌ Checker: Rejected. Feedback: {feedback}")
        
    # Pause to prevent rate limit (429 Error)
    print("⏳ Pausing for 5 seconds to avoid API rate limits...")
    time.sleep(5)
        
    return state

def linkedin_publisher(state: LinkedInPostState) -> LinkedInPostState:
    """Publishes the approved content directly to LinkedIn using the official API."""
    print("🚀 Publisher: Pushing to live LinkedIn API...")
    
    # .replace("hashtag", "") to remove the literal word
    approved_post = state["current_draft"].replace("*", "").replace("hashtag", "").strip()
    
    if LINKEDIN_ACCESS_TOKEN:
        url = "https://api.linkedin.com/v2/ugcPosts"
        headers = {
            "Authorization": f"Bearer {LINKEDIN_ACCESS_TOKEN}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0"
        }
        
        payload = {
            "author": "urn:li:person:5CpI2oGJ_y",
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {
                        "text": approved_post
                    },
                    "shareMediaCategory": "NONE"
                }
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
            }
        }
        
        try:
            # API call
            response = requests.post(url, headers=headers, json=payload)
            
            # 201 "Created/Success"
            if response.status_code == 201:
                print("✅ Successfully posted to LinkedIn!")
                state["final_post_url"] = "Successfully published to your LinkedIn profile!"
            else:
                print(f"❌ Failed to post. LinkedIn Error: {response.text}")
                state["final_post_url"] = f"Failed to publish: {response.status_code}"
                
        except Exception as e:
            print(f"❌ API Connection Error: {str(e)}")
            state["final_post_url"] = "API connection error."
            
    else:
        print("⚠️ LinkedIn Access Token missing. Skipping live post.")
        state["final_post_url"] = "Token missing - Not posted."
        
    return state