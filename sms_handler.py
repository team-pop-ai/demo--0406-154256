import json
from typing import Dict, List
import os
import anthropic
from project_search import search_projects, get_project_context

def verify_twilio_signature(request_body: str, signature: str) -> bool:
    """Verify Twilio webhook signature (simplified for demo)"""
    # In production, implement proper Twilio signature validation
    return True

def format_sms_response(response: str) -> str:
    """Format AI response for SMS character limits"""
    # SMS limit is 160 chars, but allow up to 1600 for concatenated messages
    if len(response) <= 1600:
        return response
    
    # Truncate and add indicator
    return response[:1590] + "... (more)"

def handle_sms_message(body: Dict, projects: List[Dict], team_members: List[Dict]) -> Dict:
    """Process incoming SMS query"""
    try:
        # Extract SMS data
        from_number = body.get('From', '')
        message_body = body.get('Body', '').strip()
        
        if not message_body:
            return {
                "response": "Please send a project question.",
                "status": "error"
            }
        
        # Basic phone number validation (simplified for demo)
        allowed_numbers = [
            '+1234567890',  # Scott's number
            '+1987654321',  # Team member example
        ]
        
        # In demo, allow all numbers
        if from_number not in allowed_numbers and os.environ.get('DEMO_MODE', 'true') != 'true':
            return {
                "response": "Access denied. Contact Scott Moore for project access.",
                "status": "denied"
            }
        
        # Search for relevant projects
        relevant_projects = search_projects(message_body, projects)
        context = get_project_context(relevant_projects, team_members)
        
        # Call Claude API
        client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        
        system_prompt = """You are a construction project intelligence assistant for SMS queries.
        
Format responses EXACTLY as:
Current Status: [status] | Next Steps: [actions] | Responsible Party: [person] | Timeline: [dates]

Keep responses under 300 characters for SMS. Be concise and factual."""
        
        message = f"SMS Query from {from_number}: {message_body}\n\nProject Context:\n{context}"
        
        response = client.messages.create(
            model=os.environ.get("ANTHROPIC_MODEL", "claude-3-haiku-20240307"),
            max_tokens=400,
            system=system_prompt,
            messages=[{"role": "user", "content": message}]
        )
        
        ai_response = response.content[0].text
        formatted_response = format_sms_response(ai_response)
        
        # Return Twilio-compatible response
        return {
            "response": formatted_response,
            "status": "success",
            "from": from_number,
            "message_count": len(formatted_response) // 160 + 1
        }
        
    except Exception as e:
        return {
            "response": f"System error: {str(e)}",
            "status": "error"
        }