import json
import os
from typing import Optional
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import anthropic
from project_search import search_projects, get_project_context
from sms_handler import handle_sms_message

app = FastAPI(title="Construction Project Intelligence")
templates = Jinja2Templates(directory=".")

def load_json(path, default=None):
    try:
        with open(path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default if default is not None else []

# Load mock data
projects = load_json("data/projects.json", [])
team_members = load_json("data/team_members.json", [])
example_queries = load_json("data/example_queries.json", [])

@app.get("/", response_class=HTMLResponse)
async def serve_chat(request: Request):
    return templates.TemplateResponse(
        request=request, 
        name="index.html", 
        context={
            "example_queries": example_queries[:6],  # Show first 6 examples
            "projects": projects[:5]  # Show first 5 projects in sidebar
        }
    )

@app.post("/query")
async def process_query(body: dict):
    query = body.get("query", "").strip()
    if not query:
        return {"error": "No query provided"}
    
    # Search for relevant projects
    relevant_projects = search_projects(query, projects)
    context = get_project_context(relevant_projects, team_members)
    
    # Call Claude API
    try:
        client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        
        system_prompt = """You are a construction project intelligence assistant. 
        
Extract relevant project information and format responses EXACTLY as:
Current Status: [status] | Next Steps: [actions] | Responsible Party: [person] | Timeline: [dates]

Be concise and factual. Use the project data provided to give specific answers.
If multiple projects match, focus on the most relevant one.
If information is missing, state "Information not available" for that field."""
        
        message = f"Query: {query}\n\nProject Context:\n{context}"
        
        response = client.messages.create(
            model=os.environ.get("ANTHROPIC_MODEL", "claude-3-haiku-20240307"),
            max_tokens=800,
            system=system_prompt,
            messages=[{"role": "user", "content": message}]
        )
        
        return {"response": response.content[0].text}
    except Exception as e:
        return {"error": f"AI processing failed: {str(e)}"}

@app.post("/sms")
async def handle_sms(body: dict):
    return handle_sms_message(body, projects, team_members)

@app.get("/projects")
async def list_projects():
    return {"projects": projects}

@app.get("/project/{project_id}")
async def get_project(project_id: str):
    project = next((p for p in projects if p.get("id") == project_id), None)
    if not project:
        return {"error": "Project not found"}
    return {"project": project}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)