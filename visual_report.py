import json
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from collections import defaultdict

# === Step 1: Load JSON Data ===
with open("results_107004.json", "r") as f:
    data = json.load(f)

# === Step 2: Prepare Analysis ===
status_counts = {"PASS": 0, "RE-APPEAR": 0}
score_buckets = ['90+', '80-89', '70-79', '60-69', '50-59', '40-49', '<40']
bucket_ranges = {
    '90+': lambda x: x >= 90,
    '80-89': lambda x: 80 <= x < 90,
    '70-79': lambda x: 70 <= x < 80,
    '60-69': lambda x: 60 <= x < 70,
    '50-59': lambda x: 50 <= x < 60,
    '40-49': lambda x: 40 <= x < 50,
    '<40': lambda x: x < 40
}

subject_bucket_counts = defaultdict(lambda: defaultdict(int))
subject_scores = defaultdict(list)

for student in data:
    status = student.get("Status", "RE-APPEAR").strip().upper()
    status_counts[status] += 1

    for subject in student.get("Subjects", []):
        subject_name = subject["Subject"]
        try:
            score = int(subject["Total"])
        except:
            continue

        subject_scores[subject_name].append(score)

        for bucket, rule in bucket_ranges.items():
            if rule(score):
                subject_bucket_counts[subject_name][bucket] += 1
                break

df_buckets = pd.DataFrame(subject_bucket_counts).fillna(0).astype(int).T[score_buckets]
df_avg = pd.DataFrame({subj: [sum(scores)/len(scores)] for subj, scores in subject_scores.items()},
                      index=["Average"]).T.sort_values("Average", ascending=False)

# === Step 3: Generate Charts ===
sns.set(style="whitegrid")

# 1. Stacked Bar Chart with darker for 90+ and lighter for <40
blues = sns.color_palette("Blues", n_colors=len(score_buckets))[::-1]  # Reverse for darker → lighter
df_buckets.plot(kind='bar', stacked=True, color=blues, figsize=(14, 8))
plt.title("Subject-wise Distribution of Marks")
plt.xlabel("Subjects")
plt.ylabel("Number of Students")
plt.xticks(rotation=45, ha="right")
plt.legend(title="Score Range", bbox_to_anchor=(1.05, 1), loc='upper left')
plt.tight_layout()
plt.savefig("subject_score_distribution.png")
plt.close()

# 2. Pie Chart: Pass vs Reappear
plt.figure(figsize=(6, 6))
plt.pie(status_counts.values(), labels=status_counts.keys(), autopct='%1.1f%%',
        colors=['#0d47a1', '#90caf9'], startangle=140)
plt.title("Overall Result: Pass vs Reappear")
plt.tight_layout()
plt.savefig("pass_vs_reappear.png")
plt.close()

# 4. Heatmap of Performance
plt.figure(figsize=(12, 8))
sns.heatmap(df_buckets, annot=True, fmt="d", cmap="Blues")
plt.title("Score Range Heatmap by Subject")
plt.tight_layout()
plt.savefig("subject_score_heatmap.png")
plt.close()

# === Step 4: Generate Markdown Report ===
pass_count = status_counts["PASS"]
reappear_count = status_counts["RE-APPEAR"]
total = pass_count + reappear_count
pass_percent = 100 * pass_count / total
reappear_percent = 100 * reappear_count / total

report_md = f"""
# Examination Report Summary

This report presents an analysis of the students' results, focusing on subject-wise performance, overall pass/reappear rates, and other key visual insights.

---

## 📊 Pass vs Reappear

![Pass vs Reappear](pass_vs_reappear.png)

- **Pass**: {pass_count} students  
- **Reappear**: {reappear_count} students  
- **Pass Percentage**: {pass_percent:.1f}%  
- **Reappear Percentage**: {reappear_percent:.1f}%

---

## 📚 Subject-wise Score Distribution

The chart below shows how many students scored in various score ranges for each subject.

![Subject Score Distribution](subject_score_distribution.png)

---

## 📈 Average Scores by Subject

This chart presents the average score achieved in each subject across all students.

![Average Scores](average_scores.png)

---

## 🔥 Heatmap of Score Distribution

This heatmap provides a tabular view of how students performed across score brackets for each subject.

![Subject Score Heatmap](subject_score_heatmap.png)

---

### 📝 Key Insights

- Subjects like **General Science** and **Education** have higher average scores.
- A few subjects have more students scoring below 40, indicating difficulty or low performance.
- Overall, **{pass_percent:.1f}%** of students passed while **{reappear_percent:.1f}%** need to reappear.
"""

# Save Markdown
with open("report.md", "w", encoding="utf-8") as f:
    f.write(report_md)

print("✅ Report generated successfully: report.md")
