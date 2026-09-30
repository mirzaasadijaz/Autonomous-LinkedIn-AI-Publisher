# 💼 Autonomous LinkedIn AI Publisher

A multi-agent pipeline built with **LangGraph** that finds a trending Data Science / AI topic, researches it, writes a LinkedIn post, fact-checks it, and publishes it to LinkedIn automatically.

It ships with a **FastAPI + HTML** web app (default, used by Docker) and a **Streamlit** demo app.

🐳 **Docker image:** [`mirzaasadijaz/ai-linkedin-publisher`](https://hub.docker.com/repository/docker/mirzaasadijaz/ai-linkedin-publisher)

---

## ✨ Features

- **Topic discovery**: searches the web (Tavily) for fresh trends in Data Science, AI and ML.
- **No repeat topics**: used topics are stored in SQLite (`used_topics.db`) and passed to the agent as a blacklist.
- **Research and drafting**: the Creator agent gathers facts and writes a plain-text post with bullets and hashtags.
- **Fact-checking loop**: a strict Checker agent approves the draft or sends feedback back to the Creator (max 3 iterations, then auto-approved).
- **Auto-publishing**: approved posts are pushed to LinkedIn via the `ugcPosts` API.
- **Rate-limit friendly**: pauses between agent calls, plus retries and timeouts on the LLM.

---

## 🧠 How It Works

```
        ┌──────────────┐
        │ Topic_Agent  │  finds a new topic (avoids past ones)
        └──────┬───────┘
               ▼
        ┌──────────────┐
   ┌───►│   Creator    │  researches + writes / rewrites post
   │    └──────┬───────┘
   │           ▼
   │    ┌──────────────┐
   │    │   Checker    │  fact-checks and reviews
   │    └──────┬───────┘
   │  Rejected │ Approved (or 3 iterations reached)
   └───────────┤
               ▼
        ┌──────────────┐
        │  Publisher   │  posts to LinkedIn
        └──────┬───────┘
               ▼
              END
```

**Shared state** (`state.py`): `topic`, `current_draft`, `feedback`, `is_approved`, `iteration_count`, `final_post_url`.

---

## 🗂️ Project Structure

```
.
├── agent.py             # LangGraph workflow (used by Streamlit)
├── app.py               # Streamlit UI
├── main.py              # FastAPI server + workflow (used by Docker)
├── index.html           # Web UI served by FastAPI
├── nodes.py             # Agent nodes, LLM/tool setup, topic DB, LinkedIn publisher
├── state.py             # Shared LangGraph state
├── get_id.py            # Helper to fetch your LinkedIn person URN
├── requirements.txt     # Python dependencies
├── Dockerfile           # Image definition (python:3.10-slim, port 8080)
├── docker-compose.yml   # Runs the published Docker Hub image
├── .dockerignore
├── .gitignore
├── .env.example         # Template for your API keys
└── used_topics.db       # Auto-created SQLite DB (git-ignored)
```

---

## 🧰 Tech Stack

LangGraph, Google Gemini (`langchain-google-genai`), Tavily search, FastAPI + Uvicorn, Tailwind CSS, Streamlit, SQLite, Docker, LinkedIn REST API.

---

## 🔑 Environment Variables

Copy the template and fill in your keys:

```bash
cp .env.example .env
```

| Variable                | Required | Where to get it |
| ----------------------- | -------- | --------------- |
| `GOOGLE_API_KEY`        | Yes | [Google AI Studio](https://aistudio.google.com/) |
| `TAVILY_API_KEY`        | Yes | [Tavily](https://tavily.com/) |
| `LINKEDIN_ACCESS_TOKEN` | Yes | LinkedIn Developer app with **Share on LinkedIn** and **Sign In with LinkedIn (OpenID)** products (scopes `w_member_social`, `openid`, `profile`) |
| `GROQ_API_KEY`          | No  | Only needed if you use `langchain-groq` (currently unused) |

### Get your LinkedIn person URN

```bash
python get_id.py
```

Copy the printed `urn:li:person:XXXXXXXX` value and set it as the `author` field in `linkedin_publisher()` in `nodes.py`.

> ⚠️ The `author` URN in `nodes.py` is currently hard-coded. Replace it with **your own** URN, or load it from `.env` (e.g. `LINKEDIN_PERSON_URN`).

---

## 🐳 Run with Docker (quickest)

The image is published on Docker Hub, so no local build is needed.

1. Create your `.env` file (see above).
2. Create an empty DB file so the volume mounts as a file, not a folder:

   ```bash
   touch used_topics.db
   ```

3. Start the container:

   ```bash
   docker compose up -d
   ```

4. Open **http://localhost:8080** and click **Start Agentic Pipeline**.

Useful commands:

```bash
docker compose logs -f      # view logs
docker compose down         # stop
docker compose pull         # update to the latest image
```

`docker-compose.yml` mounts `./used_topics.db` into the container, so your used-topic history survives restarts.

### Build the image yourself

```bash
docker build -t ai-linkedin-publisher .
docker run -p 8080:8080 --env-file .env ai-linkedin-publisher
```

---

## 💻 Run Locally (without Docker)

```bash
python -m venv venv
# Windows: venv\Scripts\activate
# macOS/Linux: source venv/bin/activate

pip install -r requirements.txt
cp .env.example .env    # then add your keys
```

**FastAPI web app:**

```bash
python main.py          # http://127.0.0.1:8080
```

**Streamlit app:**

```bash
streamlit run app.py
```

The web UI calls `POST /api/generate-and-post`, which returns:

```json
{
  "status": "success",
  "topic": "...",
  "draft": "...",
  "result_message": "Successfully published to your LinkedIn profile!"
}
```

---

## 🔍 Notes & Tips

- **Token expiry**: LinkedIn tokens expire (typically ~60 days). A `401` on publish means you need a new one.
- **Rate limits**: each node sleeps 5 seconds to avoid `429` errors. Adjust in `nodes.py`.
- **Iteration cap**: the Checker auto-approves after 3 drafts. Change `iteration >= 3` in `post_checker` to tune it.
- **Model name**: change the `model=` value in `nodes.py` to use a different Gemini model.
- **Duplicate workflow**: `agent.py` and `main.py` define the same graph; `main.py` could import `get_linkedin_agent()` instead.
- **Unused dependency**: `langchain-groq` is in `requirements.txt` but not used.

---

## 🔒 Security

- Never commit `.env` or `used_topics.db` (both are in `.gitignore` and `.dockerignore`).
- Treat your LinkedIn token like a password. If it was ever committed or shared, revoke and regenerate it.
- The pipeline posts **publicly and autonomously**. Consider adding a manual approval step before the Publisher node while testing.

---

## 🛣️ Ideas for Improvement

- Human-in-the-loop approval before publishing
- Scheduled runs (cron / APScheduler)
- Image or carousel generation
- Store post history and LinkedIn post URLs
- Multi-platform publishing

---

