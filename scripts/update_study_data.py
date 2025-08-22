import json
import os
import re
from datetime import datetime, timedelta
import yaml

try:
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
except ImportError:
    # Python 3.8 support
    from backports.zoneinfo import ZoneInfo, ZoneInfoNotFoundError

def load_issue_template(path=".github/ISSUE_TEMPLATE/study_log.yml"):
    """issue_template.ymlを読み込み、IDとラベルのマッピングを作成する"""
    with open(path, "r", encoding="utf-8") as f:
        template = yaml.safe_load(f)
    
    id_to_label = {}
    for item in template.get("body", []):
        if "id" in item and "attributes" in item and "label" in item["attributes"]:
            id_to_label[item["id"]] = item["attributes"]["label"]
    return id_to_label

def parse_goal_id(goal_string):
    """ 'Title (id)' 形式の文字列からIDを抽出する """
    if not goal_string or goal_string == "_No response_":
        return None
    match = re.search(r'\((\S+)\)$', goal_string)
    if match:
        return match.group(1)
    return goal_string

def parse_issue_body(body, id_to_label):
    """Issueの本文を解析して、各フィールドの値を抽出する"""
    data = {}
    
    def escape_for_regex(text):
        return re.escape(text)

    for field_id, label in id_to_label.items():
        escaped_label = escape_for_regex(label)
        pattern = f"### {escaped_label}\s*\n\s*(.*?)(?=\n###|$)"
        match = re.search(pattern, body, re.DOTALL)
        
        value = None
        if match:
            value = match.group(1).strip()
            if value == "_No response_" or not value:
                value = None
        
        data[field_id] = value

    if data.get("goalId"):
        data["goalId"] = parse_goal_id(data["goalId"])

    for field in ["duration", "difficulty", "satisfaction"]:
        if data.get(field):
            try:
                data[field] = int(data[field])
            except (ValueError, TypeError):
                data[field] = None

    if data.get("tags"):
        data["tags"] = [tag.strip() for tag in data["tags"].split(",") if tag.strip()]
    else:
        data["tags"] = []

    if data.get("materials"):
        data["materials"] = parse_materials(data["materials"])
    else:
        data["materials"] = []

    return data

def parse_materials(materials_text):
    """教材のテキストを解析してリストに変換する"""
    if not materials_text:
        return []
    materials = []
    for line in materials_text.strip().split('\n'):
        parts = line.split(':', 2)
        if len(parts) == 3:
            materials.append({
                "type": parts[0].strip(),
                "name": parts[1].strip(),
                "detail": parts[2].strip()
            })
    return materials

def update_analytics(study_data):
    """分析データを再計算する"""
    study_data = update_weekly_minutes(study_data)
    return study_data

def update_weekly_minutes(study_data):
    """週ごとの学習時間を再計算する"""
    tz_str = study_data.get("config", {}).get("timezone", "UTC")
    try:
        tz = ZoneInfo(tz_str)
    except ZoneInfoNotFoundError:
        tz = ZoneInfo("UTC")

    now = datetime.now(tz)
    start_of_week = now - timedelta(days=now.weekday()) # Monday is 0
    start_of_week = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)
    
    weekly_minutes = [0] * 7

    for session in study_data.get("sessions", []):
        session_time = datetime.fromisoformat(session["timestamp"]).astimezone(tz)
        if session_time >= start_of_week:
            day_index = session_time.weekday() # Monday is 0
            duration = session.get("duration", 0) or 0
            weekly_minutes[day_index] += duration
            
    if "analytics" not in study_data:
        study_data["analytics"] = {}
        
    study_data["analytics"]["weeklyMinutes"] = weekly_minutes
    return study_data

def main():
    issue_body = os.environ.get("ISSUE_BODY")
    issue_number = os.environ.get("ISSUE_NUMBER")
    created_at_str = os.environ.get("CREATED_AT")
    issue_url = os.environ.get("ISSUE_URL")

    if not all([issue_body, issue_number, created_at_str, issue_url]):
        print("Error: Missing required environment variables.")
        return

    try:
        id_to_label = load_issue_template()
    except FileNotFoundError:
        print("Error: .github/ISSUE_TEMPLATE/study_log.yml not found.")
        return
    except Exception as e:
        print(f"Error loading or parsing YAML: {e}")
        return

    created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
    parsed_data = parse_issue_body(issue_body, id_to_label)

    new_log = {
        "id": int(issue_number),
        "timestamp": created_at.isoformat(),
        "issueUrl": issue_url,
        **parsed_data
    }

    json_path = "data/study-data.json"
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            study_data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        study_data = {
            "version": "1.0",
            "metadata": {"created": datetime.now().isoformat(), "totalSessions": 0, "totalMinutes": 0},
            "subjects": {}, "goals": [], "sessions": [], "config": {}, "achievements": [], "analytics": {}
        }

    session_exists = False
    for i, session in enumerate(study_data["sessions"]):
        if session.get("id") == new_log["id"]:
            study_data["sessions"][i] = new_log
            session_exists = True
            break
    
    if not session_exists:
        study_data["sessions"].append(new_log)
    
    study_data["sessions"].sort(key=lambda x: x.get("id", 0))

    # メタデータと科目別時間を再計算
    total_minutes = sum(s.get("duration", 0) or 0 for s in study_data["sessions"])
    study_data["metadata"]["totalSessions"] = len(study_data["sessions"])
    study_data["metadata"]["totalMinutes"] = total_minutes
    study_data["metadata"]["lastUpdated"] = datetime.now().isoformat()

    for subject_name in study_data.get("subjects", {}):
        study_data["subjects"][subject_name]["totalMinutes"] = 0
    
    for session in study_data["sessions"]:
        subject_name = session.get("subject")
        duration = session.get("duration", 0) or 0
        if subject_name and subject_name in study_data.get("subjects", {}):
            study_data["subjects"][subject_name].setdefault("totalMinutes", 0)
            study_data["subjects"][subject_name]["totalMinutes"] += duration

    # 分析データを更新
    study_data = update_analytics(study_data)

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(study_data, f, ensure_ascii=False, indent=2)
    
    print(f"Successfully updated {json_path} with log #{issue_number}")

if __name__ == "__main__":
    main()