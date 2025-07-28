import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import json
import re
import matplotlib.pyplot as plt
import seaborn as sns
from collections import defaultdict
from io import StringIO

# ========== Scraping Functions (Same as before) ==========
def fetch_html(p, q, r):
    url = "https://results.biserawalpindi.edu.pk/Result_Detail"
    params = {"p": p, "q": q, "r": r}
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, params=params, headers=headers)
    response.raise_for_status()
    return response.text

def extract_result(html):
    soup = BeautifulSoup(html, "html.parser")
    info = {}

    def get_field(label):
        field = soup.find(string=re.compile(rf"^{label}", re.IGNORECASE))
        return field.find_next().get_text(strip=True) if field else ""

    info["Roll No"] = get_field("ROLL NO")
    info["Student Name"] = get_field("STUDENT NAME")
    info["Student Type"] = get_field("STUDENT TYPE")
    info["Grand Total"] = get_field("GRAND TOTAL")
    info["Status"] = get_field("STATUS")

    subject_table = soup.find("table")
    subjects = []

    if subject_table:
        rows = subject_table.find_all("tr")
        headers = [th.get_text(strip=True).upper() for th in rows[0].find_all("th")]

        for row in rows[1:]:
            cells = row.find_all("td")
            if len(cells) != len(headers):
                continue

            values = [td.get_text(strip=True) for td in cells]
            row_dict = dict(zip(headers, values))

            if not row_dict.get("SUBJECT"):
                continue

            subject_entry = {
                "Subject": row_dict.get("SUBJECT", ""),
                "Theory-I": row_dict.get("THEORY-I", ""),
                "Theory-II": row_dict.get("THEORY-II", ""),
                "Practical": row_dict.get("PRACTICAL", ""),
                "Total": row_dict.get("TOTAL", "")
            }

            if "PERCENTILE MARKS" in headers:
                if row_dict.get("PERCENTILE MARKS"):
                    subject_entry["Percentile Marks"] = row_dict["PERCENTILE MARKS"]
                if row_dict.get("RELATIVE GRADE"):
                    subject_entry["Relative Grade"] = row_dict["RELATIVE GRADE"]
                if row_dict.get("REMARKS"):
                    subject_entry["Remarks"] = row_dict["REMARKS"]

            subjects.append(subject_entry)

    info["Subjects"] = subjects
    return info

def parse_p_input(p_input):
    result = []
    for part in p_input.split(','):
        part = part.strip()
        if '-' in part:
            start, end = map(int, part.split('-'))
            result.extend(range(start, end + 1))
        else:
            result.append(int(part))
    return result

def scrape_data(p_values, q=2, r=2025):
    p_list = parse_p_input(p_values)
    all_results = []

    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i, p in enumerate(p_list):
        try:
            status_text.text(f"Fetching roll number: {p} ({i+1}/{len(p_list)})")
            html = fetch_html(p, q, r)
            result = extract_result(html)
            if result.get("Roll No"):  # Only include if valid
                all_results.append(result)
        except Exception as e:
            st.warning(f"Failed for roll number {p}: {str(e)}")
        
        progress_bar.progress((i + 1) / len(p_list))
    
    status_text.text("Scraping complete!")
    return all_results

# ========== Visualization Functions ==========
def prepare_analysis(data):
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
    
    return status_counts, df_buckets, df_avg, subject_scores

def plot_subject_group(selected_group, subject_scores):
    group_scores = {subj: scores for subj, scores in subject_scores.items() if subj in selected_group}
    if not group_scores:
        return None
    
    df = pd.DataFrame(group_scores)
    plt.figure(figsize=(10, 6))
    
    # Calculate means and sort
    means = df.mean().sort_values(ascending=False)
    df = df[means.index]
    
    # Create boxplot with enhanced styling
    box = sns.boxplot(data=df, palette="Blues", showmeans=True,
                     meanprops={"marker":"o", "markerfacecolor":"white", 
                               "markeredgecolor":"red", "markersize":"8"})
    
    # Add median labels
    for i, line in enumerate(box.get_lines()[4::6]):  # Every 6th line is a median line
        x, y = line.get_xydata()[1]
        box.text(x, y, f'{y:.1f}', ha='center', va='center', 
                fontweight='bold', color='white', bbox=dict(facecolor='#0d47a1', alpha=0.7))
    
    plt.title(f"Performance in {', '.join(selected_group)}", pad=20)
    plt.ylabel("Scores")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    return plt

def plot_enhanced_bar(df, title):
    plt.figure(figsize=(12, 6))
    ax = df.plot(kind='bar', color=sns.color_palette("Blues", len(df)), edgecolor='black')
    
    # Add values on top of bars
    for p in ax.patches:
        ax.annotate(f"{int(p.get_height())}", 
                   (p.get_x() + p.get_width() / 2., p.get_height()),
                   ha='center', va='center', 
                   xytext=(0, 5), 
                   textcoords='offset points',
                   fontsize=8)
    
    plt.title(title, pad=20)
    plt.ylabel("Number of Students")
    plt.xlabel("Subjects")
    plt.xticks(rotation=45, ha="right")
    plt.legend(title="Score Range", bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()
    return plt

# ========== Streamlit Pages ==========
def page1():
    st.title("BISE Rawalpindi Result Scraper")
    
    if 'processed_data' not in st.session_state:
        st.session_state.processed_data = None
    if 'scraping_started' not in st.session_state:
        st.session_state.scraping_started = False
    
    input_method = st.radio(
        "Choose your input method:",
        ("Upload File (CSV/JSON)", "Enter Roll Numbers Manually"),
        horizontal=True
    )
    
    if input_method == "Upload File (CSV/JSON)":
        uploaded_file = st.file_uploader(
            "Upload your file (CSV or JSON)",
            type=["json", "csv"],
            accept_multiple_files=False,
            key="file_uploader"
        )
        
        if uploaded_file:
            try:
                if uploaded_file.type == "application/json":
                    data = pd.read_json(uploaded_file)
                else:
                    data = pd.read_csv(uploaded_file)
                
                if 'roll_number' not in data.columns and 'Roll No' not in data.columns:
                    st.error("File must contain a 'roll_number' or 'Roll No' column")
                else:
                    st.session_state.processed_data = data
                    st.success("File processed successfully!")
                    st.dataframe(data.head())
                
            except Exception as e:
                st.error(f"Error processing file: {str(e)}")
    
    else:
        roll_numbers = st.text_area(
            "Enter 6-digit roll numbers (comma separated or ranges with hyphen)",
            height=150,
            key="roll_numbers_input",
            help="Example: 103683, 124861 or 100001-100005"
        )
        
        if roll_numbers:
            try:
                valid = True
                for part in roll_numbers.split(','):
                    part = part.strip()
                    if '-' in part:
                        start_end = part.split('-')
                        if len(start_end) != 2:
                            valid = False
                            break
                        start, end = start_end
                        if not (start.isdigit() and end.isdigit()):
                            valid = False
                            break
                    else:
                        if not part.isdigit():
                            valid = False
                            break
                
                if valid:
                    st.session_state.valid_rolls = roll_numbers
                    st.success("Valid roll numbers format detected")
                else:
                    st.error("Invalid format. Use comma separated numbers or ranges (e.g., 100001-100005)")
                
            except Exception as e:
                st.error(f"Error processing input: {str(e)}")
    
    with st.expander("Advanced Options"):
        col1, col2 = st.columns(2)
        with col1:
            q_value = st.number_input("Q Parameter (default 2)", min_value=1, value=2)
        with col2:
            r_value = st.number_input("R Parameter (Year, default 2025)", min_value=2000, value=2025)
    
    if st.button("Start Scraping", disabled=not (
        (input_method == "Upload File (CSV/JSON)" and 'processed_data' in st.session_state and st.session_state.processed_data is not None) or
        (input_method == "Enter Roll Numbers Manually" and 'valid_rolls' in st.session_state)
    )):
        st.session_state.scraping_started = True
        
        try:
            if input_method == "Upload File (CSV/JSON)":
                if 'roll_number' in st.session_state.processed_data.columns:
                    roll_numbers = ",".join(map(str, st.session_state.processed_data['roll_number'].astype(int).tolist()))
                else:
                    roll_numbers = ",".join(map(str, st.session_state.processed_data['Roll No'].astype(int).tolist()))
            else:
                roll_numbers = st.session_state.valid_rolls
            
            scraped_data = scrape_data(roll_numbers, q=q_value, r=r_value)
            
            st.session_state.scraped_results = scraped_data
            st.session_state.scraping_complete = True
            
            # Convert to DataFrame for better display
            df_results = pd.json_normalize(
                scraped_data,
                meta=['Roll No', 'Student Name', 'Student Type', 'Grand Total', 'Status'],
                record_path='Subjects',
                errors='ignore'
            )
            
            st.success("Scraping completed successfully!")
            st.session_state.page = "page2"  # Move to visualization page
            st.experimental_rerun()
            
        except Exception as e:
            st.error(f"Error during scraping: {str(e)}")
            st.session_state.scraping_complete = False

def page2():
    st.title("Result Analysis Dashboard")
    
    if 'scraped_results' not in st.session_state:
        st.warning("No data available. Please go back to Page 1 and scrape data first.")
        if st.button("Go to Scraping Page"):
            st.session_state.page = "page1"
            st.experimental_rerun()
        return
    
    # Prepare data
    status_counts, df_buckets, df_avg, subject_scores = prepare_analysis(st.session_state.scraped_results)
    
    # Overall metrics
    st.header("Overall Performance")
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Students", sum(status_counts.values()))
    col2.metric("Passed Students", status_counts["PASS"])
    col3.metric("Pass Percentage", f"{100 * status_counts['PASS']/sum(status_counts.values()):.1f}%")
    
    # Tab layout
    tab1, tab2, tab3 = st.tabs(["Score Distribution", "Subject Groups Analysis", "Advanced Visualizations"])
    
    with tab1:
        st.subheader("Score Distribution by Subject")
        fig = plot_enhanced_bar(df_buckets, "Subject-wise Score Distribution")
        st.pyplot(fig)
        
        st.subheader("Average Scores by Subject")
        fig, ax = plt.subplots(figsize=(10, 6))
        sns.barplot(x=df_avg.index, y=df_avg["Average"], palette="Blues")
        
        # Add value labels
        for i, v in enumerate(df_avg["Average"]):
            ax.text(i, v + 0.5, f"{v:.1f}", ha='center', va='bottom', fontweight='bold')
        
        plt.xticks(rotation=45, ha="right")
        plt.title("Average Scores by Subject")
        plt.ylabel("Average Score")
        plt.tight_layout()
        st.pyplot(fig)
    
    with tab2:
        st.subheader("Subject Group Analysis")
        
        # Define subject groups
        subject_groups = {
            "Math, Physics, Chemistry, Biology": ["MATHEMATICS", "PHYSICS", "CHEMISTRY", "BIOLOGY"],
            "Math, Physics, Chemistry, CS": ["MATHEMATICS", "PHYSICS", "CHEMISTRY", "COMPUTER SCIENCE"],
            "Math, General Science, Islamiat, Elective": ["MATHEMATICS", "GENERAL SCIENCE", "ISLAMIAT", "ELECTIVE"],
            "Math, General Science, Physical Education": ["MATHEMATICS", "GENERAL SCIENCE", "PHYSICAL EDUCATION"],
            "Math, General Science, Food and Nutrition": ["MATHEMATICS", "GENERAL SCIENCE", "FOOD AND NUTRITION"],
            "Math, General Science, Clothing and Textile": ["MATHEMATICS", "GENERAL SCIENCE", "CLOTHING AND TEXTILE"]
        }
        
        selected_group = st.selectbox("Select Subject Group", list(subject_groups.keys()))
        
        fig = plot_subject_group(subject_groups[selected_group], subject_scores)
        if fig:
            st.pyplot(fig)
        else:
            st.warning("No data available for selected subject group")
    
    with tab3:
        st.subheader("Heatmap of Performance")
        fig, ax = plt.subplots(figsize=(12, 8))
        sns.heatmap(df_buckets, annot=True, fmt="d", cmap="Blues", ax=ax)
        plt.title("Score Range Heatmap by Subject")
        st.pyplot(fig)
        
        st.subheader("Pass vs Reappear")
        fig, ax = plt.subplots(figsize=(6, 6))
        ax.pie(status_counts.values(), labels=status_counts.keys(), autopct='%1.1f%%',
               colors=['#0d47a1', '#90caf9'], startangle=140)
        ax.set_title("Overall Result: Pass vs Reappear")
        st.pyplot(fig)
    
    if st.button("Back to Scraping Page"):
        st.session_state.page = "page1"
        st.experimental_rerun()

# ========== Main App ==========
def main():
    if 'page' not in st.session_state:
        st.session_state.page = "page1"
    
    if st.session_state.page == "page1":
        page1()
    elif st.session_state.page == "page2":
        page2()

if __name__ == "__main__":
    main()