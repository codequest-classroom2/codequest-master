#!/usr/bin/env python3
import os
import json
import requests
import base64
import sys
import traceback

def create_student_repo(student_username, student_name, mission_id):
    """Create a personalized mission repo for a student"""
    
    print(f"🚀 Starting repo creation for {student_username}...")
    
    # GitHub token from environment
    token = os.environ.get("GH_TOKEN")
    if not token:
        print("❌ ERROR: GH_TOKEN environment variable not set")
        return False
        
    org_name = "codequest-classroom"
    
    # Load student data
    try:
        student_file = f"students/{student_username}.json"
        print(f"📂 Looking for student file: {student_file}")
        
        if not os.path.exists(student_file):
            print(f"❌ Student file not found: {student_file}")
            return False
            
        with open(student_file, 'r') as f:
            student_data = json.load(f)
        print(f"✅ Loaded student data for {student_username}")
        print(f"   Name: {student_data['student']['name']}")
    except Exception as e:
        print(f"❌ Error loading student file: {e}")
        traceback.print_exc()
        return False
    
    # Load mission data
    try:
        mission_file = f"missions/{mission_id}.json"
        print(f"📂 Looking for mission file: {mission_file}")
        
        if not os.path.exists(mission_file):
            print(f"❌ Mission file not found: {mission_file}")
            return False
            
        with open(mission_file, 'r') as f:
            mission_data = json.load(f)
        print(f"✅ Loaded mission data: {mission_data.get('title', mission_id)}")
    except Exception as e:
        print(f"❌ Error loading mission file: {e}")
        traceback.print_exc()
        return False
    
    # Load rubric
    try:
        mission_num = mission_id.split('-')[-1]
        rubric_file = f"rubrics/mission-{mission_num}.json"
        print(f"📂 Looking for rubric file: {rubric_file}")
        
        if os.path.exists(rubric_file):
            with open(rubric_file, 'r') as f:
                rubric_data = json.load(f)
            print(f"✅ Loaded rubric data")
        else:
            print(f"⚠️ Rubric file not found, using empty rubric")
            rubric_data = {"requirements": [], "xpReward": 0, "badge": ""}
    except Exception as e:
        print(f"⚠️ Error loading rubric: {e}")
        rubric_data = {"requirements": [], "xpReward": 0, "badge": ""}
    
    # Repo name
    repo_name = f"{student_username}-{mission_id}"
    print(f"📦 Will create repo: {repo_name}")
    
    # GitHub API headers
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    # Step 1: Create repo from template
    print(f"📞 Calling GitHub API to create repo from template...")
    create_url = f"https://api.github.com/repos/{org_name}/codequest-templates/generate"
    payload = {
        "owner": org_name,
        "name": repo_name,
        "description": f"CodeQuest mission for {student_name}",
        "private": True,
        "include_all_branches": False
    }
    
    try:
        response = requests.post(create_url, headers=headers, json=payload)
        
        if response.status_code != 201:
            print(f"❌ Failed to create repo: HTTP {response.status_code}")
            print(f"Response: {response.text}")
            return False
        
        repo_data = response.json()
        repo_url = repo_data['html_url']
        print(f"✅ Repo created successfully!")
        print(f"🔗 URL: {repo_url}")
    except Exception as e:
        print(f"❌ Error creating repo: {e}")
        traceback.print_exc()
        return False
    
    # Step 2: Add student as collaborator
    print(f"📞 Adding {student_username} as collaborator...")
    collab_url = f"https://api.github.com/repos/{org_name}/{repo_name}/collaborators/{student_username}"
    try:
        collab_response = requests.put(collab_url, headers=headers)
        
        if collab_response.status_code == 201:
            print(f"✅ Added {student_username} as collaborator")
        elif collab_response.status_code == 204:
            print(f"✅ {student_username} is already a collaborator")
        else:
            print(f"⚠️ Collaborator response: HTTP {collab_response.status_code}")
            print(f"Response: {collab_response.text}")
    except Exception as e:
        print(f"⚠️ Error adding collaborator: {e}")
    
    # Step 3: Customize the repo with student's data
    print(f"📝 Customizing repo files...")
    
    files_to_update = [
        ("identity.json", json.dumps({
            "name": student_data["student"]["name"],
            "xp": student_data["progress"]["xp"],
            "badges": student_data["progress"]["badges"],
            "completedMissions": student_data["progress"]["completedMissions"],
            "currentMission": student_data["progress"]["currentMission"]
        }, indent=2)),
        ("mission.json", json.dumps(mission_data, indent=2)),
        ("rubric.json", json.dumps(rubric_data, indent=2)),
        ("README.md", f"# 🚀 {mission_data['title']}\n\n## Hey {student_name}!\n\n{mission_data['description']}\n\n## Points: {mission_data['points']}\n\nEdit `submissions/solution.py` to complete the mission.")
    ]
    
    for file_path, content in files_to_update:
        try:
            print(f"   Updating {file_path}...")
            
            # Get the current file's SHA
            get_url = f"https://api.github.com/repos/{org_name}/{repo_name}/contents/{file_path}"
            get_response = requests.get(get_url, headers=headers)
            
            if get_response.status_code == 200:
                sha = get_response.json()["sha"]
                
                # Update the file
                update_url = get_url
                update_payload = {
                    "message": f"✨ Customize for {student_username}",
                    "content": base64.b64encode(content.encode()).decode(),
                    "sha": sha
                }
                update_response = requests.put(update_url, headers=headers, json=update_payload)
                
                if update_response.status_code == 200:
                    print(f"   ✅ Updated {file_path}")
                else:
                    print(f"   ⚠️ Failed to update {file_path}: HTTP {update_response.status_code}")
            else:
                print(f"   ⚠️ Could not find {file_path} in repo (HTTP {get_response.status_code})")
        except Exception as e:
            print(f"   ⚠️ Error updating {file_path}: {e}")
    
    print(f"\n🎉 SUCCESS! Student's repo is ready:")
    print(f"   https://github.com/{org_name}/{repo_name}")
    print(f"   Student has been invited as collaborator")
    
    return True

if __name__ == "__main__":
    print("=" * 50)
    print("CREATE STUDENT REPO SCRIPT STARTING")
    print("=" * 50)
    
    # Check arguments
    if len(sys.argv) < 4:
        print("❌ ERROR: Not enough arguments")
        print(f"Usage: python {sys.argv[0]} <student_username> <student_name> <mission_id>")
        print(f"Got: {sys.argv}")
        sys.exit(1)
    
    student_username = sys.argv[1]
    student_name = sys.argv[2]
    mission_id = sys.argv[3]
    
    print(f"📋 Arguments:")
    print(f"   - Username: {student_username}")
    print(f"   - Name: {student_name}")
    print(f"   - Mission: {mission_id}")
    print()
    
    success = create_student_repo(student_username, student_name, mission_id)
    
    if success:
        print("\n✅ Script completed successfully")
        sys.exit(0)
    else:
        print("\n❌ Script failed")
        sys.exit(1)
