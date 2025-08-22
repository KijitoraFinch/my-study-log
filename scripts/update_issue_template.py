import json
import yaml

def main():
    """
    data/study-data.json からゴールを読み込み、
    .github/ISSUE_TEMPLATE/study_log.yml のドロップダウン選択肢を更新する
    """
    # data.jsonを読み込む
    try:
        with open("data/study-data.json", "r", encoding="utf-8") as f:
            study_data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error reading or parsing study-data.json: {e}")
        return

    # ゴールを抽出
    goals = study_data.get("goals", [])
    
    # ドロップダウンの選択肢を作成
    # フォーマット: "ゴール名 (goal_id)"
    options = [""]  # 「ゴールなし」の選択肢
    for goal in goals:
        title = goal.get("title")
        goal_id = goal.get("id")
        if title and goal_id:
            options.append(f"{title} ({goal_id})")

    # Issueテンプレートを読み込む
    template_path = ".github/ISSUE_TEMPLATE/study_log.yml"
    try:
        with open(template_path, "r", encoding="utf-8") as f:
            issue_template = yaml.safe_load(f)
    except FileNotFoundError:
        print(f"Error: {template_path} not found.")
        return

    # goalIdドロップダウンを探して選択肢を更新
    updated = False
    for item in issue_template.get("body", []):
        if item.get("id") == "goalId":
            # 既存の選択肢と新しい選択肢が異なる場合のみ更新
            if item.get("attributes", {}).get("options") != options:
                item["attributes"]["options"] = options
                updated = True
                print("Goal options updated in issue template.")
            else:
                print("Goal options are already up-to-date.")
            break
    
    if not updated:
        return # 更新がない場合は書き込みしない

    # 更新したIssueテンプレートを書き戻す
    try:
        with open(template_path, "w", encoding="utf-8") as f:
            # `sort_keys=False` で元の順序を維持
            yaml.dump(issue_template, f, allow_unicode=True, sort_keys=False)
        print(f"Successfully updated {template_path}")
    except Exception as e:
        print(f"Error writing updated template: {e}")

if __name__ == "__main__":
    main()
