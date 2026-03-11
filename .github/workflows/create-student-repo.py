import os
import json
import requests
import base64
import sys
import time
from pathlib import Path

def create_student_repo(student_username, student_name, mission_id):
    """Create a personalized mission repo for a student"""
    
    # GitHub token from secrets
    token = os.environ.get("GH_TOKEN")
    org_name = "codequest-classroom"
    
    print(f"\n{'='*60}")
    print(f"📦 Starting repo creation for {student_username}...")
    print(f"{'='*60}")
    
    # Load student data
    student_file = f"students/{student_username}.json"
    try:
        with open(student_file, 'r') as f:
            student_data = json.load(f)
        print(f"✅ Loaded student data for {student_name}")
    except Exception as e:
        print(f"❌ Could not load student file: {e}")
        return False
    
    # Determine which template to use based on mission type
    if mission_id.startswith(('html-', 'css-', 'js-')):
        template_name = "basic-web-mission"
        print(f"🎨 Using web mission template")
    else:
        template_name = "basic-python-mission"
        print(f"🐍 Using Python mission template")
    
    # Load mission data
    mission_file = f"missions/{mission_id}.json"
    try:
        with open(mission_file, 'r') as f:
            mission_data = json.load(f)
        print(f"✅ Loaded mission: {mission_data.get('title', mission_id)}")
    except Exception as e:
        print(f"❌ Could not load mission file: {e}")
        return False
    
    # Load rubric
    rubric_file = f"rubrics/{mission_id}.json"
    try:
        with open(rubric_file, 'r') as f:
            rubric_data = json.load(f)
        print(f"✅ Loaded rubric with {len(rubric_data.get('checks', []))} checks")
    except Exception as e:
        print(f"⚠️ Could not load rubric file: {e}")
        rubric_data = {"checks": [], "totalPoints": mission_data.get('points', 0), "passingScore": 1}
    
    # Create mission repo
    repo_name = f"{student_username}-{mission_id}"
    
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    print(f"\n📦 Creating mission repo: {repo_name}")
    
    # Check if repo already exists
    check_url = f"https://api.github.com/repos/{org_name}/{repo_name}"
    check_response = requests.get(check_url, headers=headers)
    
    if check_response.status_code == 200:
        print(f"⚠️ Repo {repo_name} already exists! Skipping creation...")
        repo_url = check_response.json()['html_url']
    else:
        # Create repo from template
        create_url = f"https://api.github.com/repos/{org_name}/codequest-templates/generate"
        payload = {
            "owner": org_name,
            "name": repo_name,
            "description": f"{mission_data.get('title', mission_id)} for {student_name}",
            "private": False,  # Set to False for demo, change to True for production
            "include_all_branches": False
        }
        
        response = requests.post(create_url, headers=headers, json=payload)
        
        if response.status_code != 201:
            print(f"❌ Failed to create mission repo: {response.text}")
            return False
        
        repo_data = response.json()
        repo_url = repo_data['html_url']
        print(f"✅ Mission repo created: {repo_url}")
        
        # Wait a moment for repo to be ready
        time.sleep(2)
    
    # Add student as collaborator
    collab_url = f"https://api.github.com/repos/{org_name}/{repo_name}/collaborators/{student_username}"
    collab_response = requests.put(collab_url, headers=headers)
    
    if collab_response.status_code == 201:
        print(f"✅ Added {student_username} as collaborator")
    elif collab_response.status_code == 204:
        print(f"✅ {student_username} is already a collaborator")
    else:
        print(f"⚠️ Could not add collaborator: {collab_response.status_code}")
    
    # Customize mission repo with student data
    print(f"\n📝 Customizing mission repo with student data...")
    
    files_to_update = [
        ("identity.json", json.dumps({
            "username": student_username,
            "name": student_name,
            "xp": student_data["progress"]["xp"],
            "badges": student_data["progress"]["badges"],
            "completedMissions": student_data["progress"]["completedMissions"],
            "currentMission": mission_id
        }, indent=2)),
        ("mission.json", json.dumps(mission_data, indent=2)),
        ("rubric.json", json.dumps(rubric_data, indent=2)),
    ]
    
    # Customize README.md with mission details and StackBlitz link
    readme_content = f"""# 🚀 **{mission_data.get('title', mission_id)}**

## 👋 Hey {student_name}!

<div align="center">
  <img src="https://media.giphy.com/media/26tn33aiTi1jkl6H6/giphy.gif" width="200" alt="Coding gif"/>
</div>

Welcome to your next coding challenge! Get ready to level up your skills! 🎮

---

## 🚀 **LAUNCH YOUR CODING ENVIRONMENT**

<div align="center">
  
[![OPEN IN STACKBLITZ](https://developer.stackblitz.com/img/open_in_stackblitz.svg)](https://stackblitz.com/github/{org_name}/{repo_name})

**✨ One click → Instant coding environment! No installation needed! ✨**

</div>

---

## 📋 **YOUR MISSION**

{mission_data.get('description', 'Complete the mission requirements.')}

### ✅ **Requirements:**
"""
    
    # Add requirements checklist
    for req in mission_data.get('requirements', []):
        readme_content += f"- [ ] {req}\n"
    
    readme_content += f"""

## 📁 **YOUR FILES**
