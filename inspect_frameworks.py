import sqlite3

DB_PATH = r"ld-metrics-translator/app.db"

SQL = {
    "frameworks": "SELECT id, name, slug FROM frameworks ORDER BY sort_order, name",
    "competencies": "SELECT id, name, framework_id FROM competencies WHERE framework_id = ? ORDER BY sort_order, name",
    "metrics_for_comp": (
        "SELECT m.id, m.name FROM competency_metrics cm "
        "JOIN metrics m ON m.id = cm.metric_id "
        "WHERE cm.competency_id = ? ORDER BY m.name"
    ),
}

def main():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    for fw_id, fw_name, fw_slug in cur.execute(SQL["frameworks"]).fetchall():
        print(f"\nFramework: {fw_name} ({fw_slug})")
        comps = cur.execute(SQL["competencies"], (fw_id,)).fetchall()
        print(f"  Competencies: {len(comps)}")
        for comp_id, comp_name, _ in comps:
            print(f"   - {comp_name}")
            links = cur.execute(SQL["metrics_for_comp"], (comp_id,)).fetchall()
            for m_id, m_name in links[:5]:  # limit display
                print(f"      * {m_name}")
    con.close()

if __name__ == "__main__":
    main()
