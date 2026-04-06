import json
from typing import List, Dict, Any

def fuzzy_match(query: str, text: str) -> float:
    """Simple fuzzy matching score between 0 and 1"""
    query_words = query.lower().split()
    text_words = text.lower().split()
    
    matches = 0
    for query_word in query_words:
        for text_word in text_words:
            if query_word in text_word or text_word in query_word:
                matches += 1
                break
    
    return matches / len(query_words) if query_words else 0

def search_projects(query: str, projects: List[Dict]) -> List[Dict]:
    """Find projects relevant to the query"""
    if not projects:
        return []
    
    scored_projects = []
    
    for project in projects:
        score = 0
        
        # Check project name and address
        score += fuzzy_match(query, project.get("name", "")) * 3
        score += fuzzy_match(query, project.get("address", "")) * 3
        
        # Check status and permit fields
        score += fuzzy_match(query, project.get("status", "")) * 2
        score += fuzzy_match(query, project.get("permit_status", "")) * 2
        
        # Check contractors and responsible parties
        contractors = project.get("contractors", [])
        for contractor in contractors:
            if isinstance(contractor, dict):
                score += fuzzy_match(query, contractor.get("name", ""))
                score += fuzzy_match(query, contractor.get("trade", ""))
        
        score += fuzzy_match(query, project.get("responsible_party", ""))
        
        # Check next steps and compliance
        score += fuzzy_match(query, project.get("next_steps", ""))
        compliance_items = project.get("compliance_items", [])
        for item in compliance_items:
            if isinstance(item, dict):
                score += fuzzy_match(query, item.get("requirement", ""))
        
        if score > 0:
            scored_projects.append((score, project))
    
    # Sort by score and return top matches
    scored_projects.sort(key=lambda x: x[0], reverse=True)
    return [project for score, project in scored_projects[:3]]

def get_project_context(projects: List[Dict], team_members: List[Dict]) -> str:
    """Format project information for Claude processing"""
    if not projects:
        return "No matching projects found."
    
    context = []
    
    for project in projects:
        project_info = []
        project_info.append(f"PROJECT: {project.get('name', 'Unknown')}")
        project_info.append(f"ADDRESS: {project.get('address', 'Unknown')}")
        project_info.append(f"STATUS: {project.get('status', 'Unknown')}")
        project_info.append(f"PERMIT STATUS: {project.get('permit_status', 'Unknown')}")
        
        timeline = project.get('timeline', {})
        if timeline:
            project_info.append(f"TIMELINE: Start: {timeline.get('start', 'TBD')}, End: {timeline.get('end', 'TBD')}")
        
        responsible = project.get('responsible_party', '')
        if responsible:
            project_info.append(f"RESPONSIBLE PARTY: {responsible}")
        
        next_steps = project.get('next_steps', '')
        if next_steps:
            project_info.append(f"NEXT STEPS: {next_steps}")
        
        contractors = project.get('contractors', [])
        if contractors:
            contractor_list = []
            for contractor in contractors:
                if isinstance(contractor, dict):
                    name = contractor.get('name', '')
                    trade = contractor.get('trade', '')
                    contractor_list.append(f"{name} ({trade})")
            if contractor_list:
                project_info.append(f"CONTRACTORS: {', '.join(contractor_list)}")
        
        compliance = project.get('compliance_items', [])
        if compliance:
            compliance_list = []
            for item in compliance:
                if isinstance(item, dict):
                    req = item.get('requirement', '')
                    status = item.get('status', '')
                    compliance_list.append(f"{req}: {status}")
            if compliance_list:
                project_info.append(f"COMPLIANCE: {'; '.join(compliance_list)}")
        
        context.append('\n'.join(project_info))
    
    return '\n\n'.join(context)