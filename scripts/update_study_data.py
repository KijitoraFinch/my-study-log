

import json
import os
import re
from datetime import datetime

def parse_issue_body(body):
    """Issueの本文を解析して、各フィールドの値を抽出する"""
    data = {}
    # シンプルなキーと値の抽出
    fields = [
        "subject", "duration", "tags", "difficulty", "satisfaction"
    ]
    for field in fields:
        match = re.search(f"### {get_label_for_field(field)}\s*\n\s*(.*?)\s*\n", body, re.DOTALL)
        if match:
            data[field] = match.group(1).strip()

    # goalIdを特別に処理
    goal_id_match = re.search(f"### {get_label_for_field('goalId')}\s*\n\s*(.*?)\s*\n", body, re.DOTALL)
    if goal_id_match:
        goal_id_raw = goal_id_match.group(1).strip()
        if goal_id_raw and goal_id_raw != "_No response_":
            # "Title (ID)" の形式からIDを抽出
            id_match = re.search(r'\((\S+)\)

def get_label_for_field(field_id):
    """issue_template.ymlのIDからラベル文字列を取得する"""
    labels = {
        "subject": "学習科目",
        "goalId": "関連ゴール",
        "duration": "学習時間（分）",
        "content": "学習内容",
        "tags": "タグ（カンマ区切り）",
        "materials": "教材",
        "notes": "メモ",
        "difficulty": "難易度 \(1-5\)",
        "satisfaction": "満足度 \(1-5\)"
    }
    return labels.get(field_id, "")

def parse_materials(materials_text):
    """教材のテキストを解析してリストに変換する"""
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

def main():
    # 環境変数から情報を取得
    issue_title = os.environ.get("ISSUE_TITLE")
    issue_body = os.environ.get("ISSUE_BODY")
    issue_number = os.environ.get("ISSUE_NUMBER")
    created_at_str = os.environ.get("CREATED_AT")
    issue_url = os.environ.get("ISSUE_URL")

    if not all([issue_title, issue_body, issue_number, created_at_str]):
        print("Error: Missing required environment variables.")
        return

    # 日付をISO 8601形式にパース
    created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))

    # Issueからデータを解析
    parsed_data = parse_issue_body(issue_body)

    # 新しい学習記録を作成
    new_log = {
        "id": int(issue_number),
        "timestamp": created_at.isoformat(),
        "subject": parsed_data.get("subject"),
        "goalId": parsed_data.get("goalId"),
        "duration": parsed_data.get("duration", 0),
        "content": parsed_data.get("content"),
        "tags": parsed_data.get("tags", []),
        "materials": parsed_data.get("materials", []),
        "notes": parsed_data.get("notes"),
        "difficulty": parsed_data.get("difficulty"),
        "satisfaction": parsed_data.get("satisfaction"),
        "issueUrl": issue_url
    }

    # JSONファイルを読み込み、更新
    json_path = "data/study-data.json"
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            study_data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        study_data = {
            "version": "1.0",
            "metadata": {"created": datetime.now().isoformat(), "totalSessions": 0, "totalMinutes": 0},
            "subjects": {},
            "goals": [],
            "sessions": [],
            "config": {},
            "achievements": [],
            "analytics": {}
        }

    # 新しい学習記録をセッションに追加
    study_data["sessions"].append(new_log)
    
    # セッションをIDでソート
    study_data["sessions"].sort(key=lambda x: x.get("id", 0))

    # メタデータを更新
    study_data["metadata"]["totalSessions"] = len(study_data["sessions"])
    total_minutes = sum(s.get("duration", 0) or 0 for s in study_data["sessions"])
    study_data["metadata"]["totalMinutes"] = total_minutes
    study_data["metadata"]["lastUpdated"] = datetime.now().isoformat()

    # 科目別の学習時間を更新
    subject_name = new_log.get("subject")
    duration = new_log.get("duration", 0) or 0
    if subject_name and subject_name in study_data["subjects"]:
        study_data["subjects"][subject_name]["totalMinutes"] = study_data["subjects"][subject_name].get("totalMinutes", 0) + duration

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(study_data, f, ensure_ascii=False, indent=2)
    
    print(f"Successfully added log #{issue_number} to {json_path}")

if __name__ == "__main__":
    main()

, goal_id_raw)
            if id_match:
                data['goalId'] = id_match.group(1)
            else:
                data['goalId'] = goal_id_raw
        else:
            data['goalId'] = None
    else:
        data['goalId'] = None

    # 複数行のフィールド
    multi_line_fields = ["content", "materials", "notes"]
    for field in multi_line_fields:
        match = re.search(f"### {get_label_for_field(field)}\s*\n\s*(.*?)(?=\n###|$)", body, re.DOTALL)
        if match:
            value = match.group(1).strip()
            if value == "_No response_" or not value:
                data[field] = None
            else:
                data[field] = value
    
    # 数値への変換
    for field in ["duration", "difficulty", "satisfaction"]:
        if data.get(field):
            try:
                data[field] = int(data[field])
            except (ValueError, TypeError):
                data[field] = None

    # タグをリストに変換
    if data.get("tags"):
        data["tags"] = [tag.strip() for tag in data["tags"].split(",") if tag.strip()]
    else:
        data["tags"] = []

    # 教材をパース
    if data.get("materials"):
        data["materials"] = parse_materials(data["materials"])

    return data

def get_label_for_field(field_id):
    """issue_template.ymlのIDからラベル文字列を取得する"""
    labels = {
        "subject": "学習科目",
        "goalId": "関連ゴール",
        "duration": "学習時間（分）",
        "content": "学習内容",
        "tags": "タグ（カンマ区切り）",
        "materials": "教材",
        "notes": "メモ",
        "difficulty": "難易度 \(1-5\)",
        "satisfaction": "満足度 \(1-5\)"
    }
    return labels.get(field_id, "")

def parse_materials(materials_text):
    """教材のテキストを解析してリストに変換する"""
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

def main():
    # 環境変数から情報を取得
    issue_title = os.environ.get("ISSUE_TITLE")
    issue_body = os.environ.get("ISSUE_BODY")
    issue_number = os.environ.get("ISSUE_NUMBER")
    created_at_str = os.environ.get("CREATED_AT")
    issue_url = os.environ.get("ISSUE_URL")

    if not all([issue_title, issue_body, issue_number, created_at_str]):
        print("Error: Missing required environment variables.")
        return

    # 日付をISO 8601形式にパース
    created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))

    # Issueからデータを解析
    parsed_data = parse_issue_body(issue_body)

    # 新しい学習記録を作成
    new_log = {
        "id": int(issue_number),
        "timestamp": created_at.isoformat(),
        "subject": parsed_data.get("subject"),
        "goalId": parsed_data.get("goalId"),
        "duration": parsed_data.get("duration", 0),
        "content": parsed_data.get("content"),
        "tags": parsed_data.get("tags", []),
        "materials": parsed_data.get("materials", []),
        "notes": parsed_data.get("notes"),
        "difficulty": parsed_data.get("difficulty"),
        "satisfaction": parsed_data.get("satisfaction"),
        "issueUrl": issue_url
    }

    # JSONファイルを読み込み、更新
    json_path = "data/study-data.json"
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            study_data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        study_data = {
            "version": "1.0",
            "metadata": {"created": datetime.now().isoformat(), "totalSessions": 0, "totalMinutes": 0},
            "subjects": {},
            "goals": [],
            "sessions": [],
            "config": {},
            "achievements": [],
            "analytics": {}
        }

    # 新しい学習記録をセッションに追加
    study_data["sessions"].append(new_log)
    
    # セッションをIDでソート
    study_data["sessions"].sort(key=lambda x: x.get("id", 0))

    # メタデータを更新
    study_data["metadata"]["totalSessions"] = len(study_data["sessions"])
    total_minutes = sum(s.get("duration", 0) or 0 for s in study_data["sessions"])
    study_data["metadata"]["totalMinutes"] = total_minutes
    study_data["metadata"]["lastUpdated"] = datetime.now().isoformat()

    # 科目別の学習時間を更新
    subject_name = new_log.get("subject")
    duration = new_log.get("duration", 0) or 0
    if subject_name and subject_name in study_data["subjects"]:
        study_data["subjects"][subject_name]["totalMinutes"] = study_data["subjects"][subject_name].get("totalMinutes", 0) + duration

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(study_data, f, ensure_ascii=False, indent=2)
    
    print(f"Successfully added log #{issue_number} to {json_path}")

if __name__ == "__main__":
    main()

