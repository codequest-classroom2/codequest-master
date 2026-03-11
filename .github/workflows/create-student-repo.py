import os
import json
import requests
import base64
import sys
import time

def create_student_repo(student_username, student_name, mission_id):
    token = os.environ.get("GH_TOKEN")
    template_org = "codequest-templates"
    classroom_org = "codequest-classroom"
    
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }

    # --- DEBUG 1: Token & Connection Check ---
    print(f"🔍 DEBUG: Verifying GH_TOKEN and Org access...")
    user_check = requests.get("https://api.github.com/user", headers=headers)
    if user_check.status_code != 200:
        print(f"❌ CRITICAL: Token invalid! (Code: {user_check.status_code})")
        return False
    print(f"✅ Authenticated as: {user_check.json().get('login')}")

    # --- 1. Load Configs ---
    try:
        with open(f"students/{student_username}.json", 'r') as f: student_data = json.load(f)
        with open(f"missions/{mission_id}.json", 'r') as f: mission_data = json.load(f)
        with open(f"rubrics/{mission_id}.json", 'r') as f: rubric_data = json.load(f)
        print("✅ Config files loaded.")
    except Exception as e:
        print(f"❌ File Load Error: {e}")
        return False

    template_name = mission_data.get("template", "basic-web-mission")
    repo_name = f"{student_username}-{mission_id}"

    # --- 2. Generate Repo ---
    print(f"🛠️ Step 1: Generating {repo_name} from {template_org}/{template_name}...")
    create_url = f"https://api.github.com/repos/{template_org}/{template_name}/generate"
    payload = {"owner": classroom_org, "name": repo_name, "private": True}
    
    response = requests.post(create_url, headers=headers, json=payload)
    
    if response.status_code not in [201, 200]:
        print(f"❌ REPO CREATION FAILED: {response.status_code}")
        print(f"💬 Error Msg: {response.text}")
        return False
    
    print(f"✅ Repo created! Sleeping 10s for GitHub backend...")
    time.sleep(10)

    # --- 3. Push Files (BEFORE Invite) ---
    print(f"📝 Step 2: Pushing mission files...")
    identity_content = {
        "username": student_username, "name": student_name,
        "xp": student_data.get("progress", {}).get("xp", 0),
        "currentMission": mission_id
    }
    
    files = [
        ("identity.json", json.dumps(identity_content, indent=2)),
        ("mission.json", json.dumps(mission_data, indent=2)),
        ("rubric.json", json.dumps(rubric_data, indent=2)),
        ("README.md", f"# 🚀 Mission: {mission_data['title']}\n\nWelcome {student_name}!")
    ]

    for filename, content in files:
        file_url = f"https://api.github.com/repos/{classroom_org}/{repo_name}/contents/{filename}"
        put_payload = {
            "message": f"🤖 Setup {filename}",
            "content": base64.b64encode(content.encode()).decode()
        }
        f_res = requests.put(file_url, headers=headers, json=put_payload)
        print(f"   {'✅' if f_res.status_code in [200,201] else '⚠️'} {filename} ({f_res.status_code})")

    # --- 4. Invite & Debug Email ---
    print(f"📧 Step 3: Triggering Invitation for @{student_username}...")
    invite_url = f"https://api.github.com/repos/{classroom_org}/{repo_name}/invitations"
    
    # Try the formal Invitation API first (better for emails)
    inv_res = requests.post(invite_url, headers=headers, json={"invitee": student_username, "permissions": "push"})
    
    if inv_res.status_code == 201:
        inv_data = inv_res.json()
        print(f"✅ INVITE SUCCESS (201)")
        print(f"🔗 DIRECT INVITE LINK: {inv_data.get('html_url')}")
        print(f"💡 Copy this link if the email doesn't arrive!")
    elif inv_res.status_code == 422:
        print(f"⚠️ User already invited or already a member. Checking status...")
    else:
        print(f"❌ Invite API Failed ({inv_res.status_code}). Trying Collaborator fallback...")
        collab_url = f"https://api.github.com/repos/{classroom_org}/{repo_name}/collaborators/{student_username}"
        c_res = requests.put(collab_url, headers=headers, json={"permission": "push"})
        print(f"   Fallback Result: {c_res.status_code}")

    print(f"\n🚀 SETUP COMPLETE: https://github.com/{classroom_org}/{repo_name}")
    return True

if __name__ == "__main__":
    if len(sys.argv) < 4: sys.exit(1)
    success = create_student_repo(sys.argv[1], sys.argv[2], sys.argv[3])
    sys.exit(0 if success else 1)
