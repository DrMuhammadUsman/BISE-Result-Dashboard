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
from itertools import zip_longest
from fpdf import FPDF
import streamlit.components.v1 as components

# CSS for print page breaks
PRINT_CSS = """
<style>
@media print {
  .pagebreak { page-break-after: always; }
}
</style>
"""

# Function to render a Print button
def render_print_button():
    st.markdown(PRINT_CSS, unsafe_allow_html=True)
    components.html(
        """
        <button onclick="window.print()" 
                style="padding:8px 16px;font-size:16px;
                       background:#4CAF50;color:white;border:none;
                       border-radius:4px;cursor:pointer;">
           Print Report
        </button>
        """, height=60)
    
# ========== Scraping Functions ==========
def fetch_html(p, q, r):
    url = "https://results.biserawalpindi.edu.pk/Result_Detail"
    params = {"p": p, "q": q, "r": r}
    ###
    headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 \
                  (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
    "Referer": "https://results.biserawalpindi.edu.pk/",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
}

    response = requests.get(url, headers=headers)

    ###
#     headers = {
#     "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
#     "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
#     "Accept-Language": "en-US,en;q=0.5",
#     "Referer": "https://results.biserawalpindi.edu.pk/",
#     "Connection": "keep-alive",
# }

    url = f"https://results.biserawalpindi.edu.pk/Result_Detail?p={p}&q=2&r=2025"

    response = requests.get(url, headers=headers)
    response.raise_for_status()  # raises 403 if blocked

    # headers = {"User-Agent": "Mozilla/5.0"}
    # response = requests.get(url, params=params, headers=headers)
    # response.raise_for_status()
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

# ========== Data Processing Functions ==========
def process_uploaded_file(uploaded_file):
    try:
        if uploaded_file.type == "application/json":
            return pd.read_json(uploaded_file)
        else:
            return pd.read_csv(uploaded_file)
    except Exception as e:
        st.error(f"Error processing file: {str(e)}")
        return None

def prepare_analysis(data):
    # Handle both raw scraped data and uploaded DataFrame
    if isinstance(data, pd.DataFrame):
        # Process uploaded file data
        status_counts = {"PASS": 0, "RE-APPEAR": 0}
        subject_scores = defaultdict(list)
        
        # Convert DataFrame to the same format as scraped data
        for _, row in data.iterrows():
            status = row.get("Status", "RE-APPEAR").strip().upper()
            status_counts[status] += 1
            
            # Process subjects - this part needs to match your actual DataFrame structure
            # You may need to adjust this based on how your uploaded data is structured
            subjects = eval(row.get("Subjects", "[]")) if isinstance(row.get("Subjects"), str) else row.get("Subjects", [])
            for subject in subjects:
                subject_name = subject.get("Subject", "")
                try:
                    score = int(subject.get("Total", 0))
                    subject_scores[subject_name].append(score)
                except:
                    continue
        
                # Create score buckets
                score_buckets = ['95+', '90-94', '85-89', '80-84', '75-79', '70-74', '60-69', '50-59', '40-49', '<40']
                bucket_ranges = {
                    '95+': lambda x: x >= 95,
                    '90-94': lambda x: 90 <= x < 95,
                    '85-89': lambda x: 85 <= x < 90,
                    '80-84': lambda x: 80 <= x < 85,
                    '75-79': lambda x: 75 <= x < 80,
                    '70-74': lambda x: 70 <= x < 75,
                    '60-69': lambda x: 60 <= x < 70,
                    '50-59': lambda x: 50 <= x < 60,
                    '40-49': lambda x: 40 <= x < 50,
                    '<40': lambda x: x < 40
                }
        
        subject_bucket_counts = defaultdict(lambda: defaultdict(int))
        
        for subject, scores in subject_scores.items():
            for score in scores:
                for bucket, rule in bucket_ranges.items():
                    if rule(score):
                        subject_bucket_counts[subject][bucket] += 1
                        break
        
        # Ensure all buckets are present for each subject
        for subject in subject_bucket_counts:
            for bucket in score_buckets:
                if bucket not in subject_bucket_counts[subject]:
                    subject_bucket_counts[subject][bucket] = 0
        
        df_buckets = pd.DataFrame(subject_bucket_counts).fillna(0).astype(int).T
        # Reorder columns to match score_buckets
        df_buckets = df_buckets[score_buckets] if all(b in df_buckets.columns for b in score_buckets) else df_buckets
        
        df_avg = pd.DataFrame({subj: [sum(scores)/len(scores)] for subj, scores in subject_scores.items()},
                              index=["Average"]).T.sort_values("Average", ascending=False)
        
        return status_counts, df_buckets, df_avg, subject_scores
    
    else:
        # Process scraped data (original implementation)
        status_counts = {"PASS": 0, "RE-APPEAR": 0}
        # Create score buckets
        score_buckets = ['95+', '90-94', '85-89', '80-84', '75-79', '70-74', '60-69', '50-59', '40-49', '<40']
        bucket_ranges = {
            '95+': lambda x: x >= 95,
            '90-94': lambda x: 90 <= x < 95,
            '85-89': lambda x: 85 <= x < 90,
            '80-84': lambda x: 80 <= x < 85,
            '75-79': lambda x: 75 <= x < 80,
            '70-74': lambda x: 70 <= x < 75,
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

        # Ensure all buckets are present for each subject
        for subject in subject_bucket_counts:
            for bucket in score_buckets:
                if bucket not in subject_bucket_counts[subject]:
                    subject_bucket_counts[subject][bucket] = 0

        df_buckets = pd.DataFrame(subject_bucket_counts).fillna(0).astype(int).T
        # Reorder columns to match score_buckets
        df_buckets = df_buckets[score_buckets] if all(b in df_buckets.columns for b in score_buckets) else df_buckets
        
        df_avg = pd.DataFrame({subj: [sum(scores)/len(scores)] for subj, scores in subject_scores.items()},
                              index=["Average"]).T.sort_values("Average", ascending=False)
        
        return status_counts, df_buckets, df_avg, subject_scores

# ========== Visualization Functions ==========
# def plot_subject_group(selected_group, subject_scores):
#     # Filter scores based on selected group
#     group_scores = {subj: scores for subj, scores in subject_scores.items() if subj in selected_group}
#     if not group_scores:
#         return None

#     # Create DataFrame with NaN padding for unequal lengths
#     df = pd.DataFrame(dict(zip(group_scores.keys(), zip_longest(*group_scores.values()))))

#     # Calculate mean scores for each subject
#     mean_scores = df.mean().sort_values(ascending=False)

#     # Plot bar chart
#     plt.figure(figsize=(10, 6))
#     bars = plt.bar(mean_scores.index, mean_scores.values, color=sns.color_palette("Blues", len(mean_scores)))

#     # Add value labels on bars
#     for bar in bars:
#         height = bar.get_height()
#         plt.text(bar.get_x() + bar.get_width()/2, height + 0.5, f'{height:.1f}', ha='center', fontweight='bold')

#     plt.title(f"Average Scores in {', '.join(selected_group)}", pad=20)
#     plt.ylabel("Average Score")
#     plt.xticks(rotation=45, ha="right")
#     plt.tight_layout()

#     return plt

# def show_top_scorers_table(groups, subject_scores, full_data):
#     for group in groups:
#         group_name = group["name"]
#         selected_subjects = group["subjects"]

#         group_scores = {subj: scores for subj, scores in subject_scores.items() if subj in selected_subjects}
#         if not group_scores:
#             st.warning(f"No data for group '{group_name}'")
#             continue

#         df = pd.DataFrame(dict(zip(group_scores.keys(), zip_longest(*group_scores.values()))))
#         df["Total"] = df.sum(axis=1)

#         full_df = df.copy()
#         full_df["Roll No"] = full_data["Roll No"].values[:len(df)]
#         full_df["Student Name"] = full_data["Student Name"].values[:len(df)]
#         full_df["Grand Total"] = full_data["Grand Total"].values[:len(df)]

#         available_subjects = [s for s in selected_subjects if s in full_df.columns]

#         columns_to_show = ["Roll No", "Student Name", "Grand Total"] + available_subjects
#         top5 = full_df.sort_values("Total", ascending=False).head(5)[columns_to_show]

#         st.markdown(f"**Top 5 Scorers in Group: {group_name}**")
#         st.dataframe(top5.reset_index(drop=True), use_container_width=True)


def plot_enhanced_bar(df, title):
    plt.figure(figsize=(14, 8))
    colors = sns.color_palette("Blues", n_colors=len(df))[::-1]
    
    ax = df.plot(kind='bar', 
                 width=0.95, 
                 color=colors,
                #  edgecolor='black',
                #  linewidth=0.5,
                 figsize=(14, 8))
    
    # Add value labels on each bar
    for container in ax.containers:
        ax.bar_label(container, 
                    label_type='edge', 
                    padding=6,
                    fontsize=5,
                    rotation = 90,
                    fmt='%d')
    
    plt.title(title, 
              fontsize=16, 
              pad=20, 
              fontweight='bold')
    plt.xlabel("Subjects", 
               fontsize=12, 
               labelpad=10)
    plt.ylabel("Number of Students", 
               fontsize=12, 
               labelpad=10)
    
    plt.xticks(rotation=45, 
               ha="right",
               fontsize=10)
    plt.yticks(fontsize=10)
    
    plt.grid(axis='y', 
             linestyle='--', 
             alpha=0.7)
    
    plt.legend(title="Score Range", 
               bbox_to_anchor=(1.02, 1), 
               loc='upper left',
               frameon=True,
               fontsize=10)
    
    plt.tight_layout()
    return plt
#######
# plt.savefig("subject_score_distribution.png")
# plt.close()
#########
# ========== Streamlit Pages ==========
# In your main app file (before any page definitions)
if 'school_name' not in st.session_state:
    st.session_state.school_name = ""

def page1():
    # School name input (only show on first page if not set)
    if not st.session_state.school_name:
        st.session_state.school_name = st.text_input("Enter School Name", 
                                                   value="",
                                                   max_chars=100)
    
    st.title(f"B.I.S.E RAWALPINDI SSC Annual Examination 2025 | {st.session_state.school_name} Result Analysis Dashboard")
    if 'processed_data' not in st.session_state:
        st.session_state.processed_data = None
    if 'scraped_results' not in st.session_state:
        st.session_state.scraped_results = None
    
    input_method = st.radio(
        "Choose your input method:",
        ("Upload JSON File", "Enter Roll Numbers Manually"),
        horizontal=True
    )
    
    if input_method == "Upload JSON File":
        uploaded_file = st.file_uploader(
            "Upload your JSON file ",
            type=["json"],
            accept_multiple_files=False,
            key="file_uploader"
        )
        
        if uploaded_file:
            processed_data = process_uploaded_file(uploaded_file)
            if processed_data is not None:
                st.session_state.processed_data = processed_data
                st.success("File processed successfully!")
                st.dataframe(processed_data.head())
                
                if st.button("Proceed to Visualization"):
                    st.session_state.page = "page2"
                    st.rerun()
    
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
        
        if st.button("Start Scraping", disabled=not ('valid_rolls' in st.session_state)):
            st.session_state.scraping_started = True
            
            try:
                scraped_data = scrape_data(st.session_state.valid_rolls, q=q_value, r=r_value)
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
                
                # Add download buttons
                st.subheader("Download Scraped Data")
                col1, col2 = st.columns(2)
                
                with col1:
                    # CSV Download
                    pass
                
                with col2:
                    # JSON Download
                    json_data = json.dumps(scraped_data, indent=2)
                    st.download_button(
                        label="Download as JSON",
                        data=json_data,
                        file_name='bise_results.json',
                        mime='application/json',
                    )
                
            # if st.button("Proceed to Visualization"):
            #     st.session_state.page = "page2"
            #     st.rerun()
                
            except Exception as e:
                st.error(f"Error during scraping: {str(e)}")
                st.session_state.scraping_complete = False

def page2():
    st.title(f"B.I.S.E RAWALPINDI SSC Annual Examination 2025 | {st.session_state.school_name} Result Analysis Dashboard")
    # st.title("B.I.S.E RAWALPINDI SSC Annual Examination 2025 Institution Result Analysis Dashboard")
    
    if 'processed_data' not in st.session_state and 'scraped_results' not in st.session_state:
        st.warning("No data available. Please go back to Page 1 and upload or scrape data first.")
        if st.button("Go to Data Input Page"):
            st.session_state.page = "page1"
            st.rerun()
        return
    
    # Prepare data
    data_source = st.session_state.processed_data if 'processed_data' in st.session_state else st.session_state.scraped_results
    status_counts, df_buckets, df_avg, subject_scores = prepare_analysis(data_source)
    
    # Overall metrics
    st.header("Overall Performance")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Students", sum(status_counts.values()))
    col2.metric("Passed Students", status_counts["PASS"])
    col3.metric("Pass Percentage", f"{100 * status_counts['PASS']/sum(status_counts.values()):.1f}%")
    col4.metric("Reappear Percentage", f"{100 - (100 * status_counts['PASS']/sum(status_counts.values())):.1f}%")
    
    # Tab layout
    tab1, tab2, tab3, tab4 = st.tabs(["Score Distribution", "Subject Groups Analysis", "Advanced Visualizations", "Teacher-wise Report"])
    
    with tab1:
        st.subheader("Pass vs Reappear")
        fig, ax = plt.subplots(figsize=(6, 6))
        wedges, texts, autotexts = ax.pie(
            status_counts.values(), 
            labels=status_counts.keys(), 
            autopct='%1.1f%%',
            colors=['#0d47a1', '#90caf9'],
            startangle=90,
            explode=(0.05, 0),  # slight separation
            shadow=False,
            textprops={'fontsize': 12, 'color': 'white', 'weight': 'bold'}
        )

        # Improve legend
        ax.legend(
            wedges, 
            status_counts.keys(),
            title="Status",
            loc="center left",
            bbox_to_anchor=(1, 0, 0.5, 1)
        )

        # Make percentage labels more visible
        plt.setp(autotexts, size=12, weight="bold", color='white')

        # Equal aspect ratio ensures pie is drawn as circle
        ax.axis('equal')  
        ax.set_title("Overall Result: Pass vs Reappear", pad=20, fontweight='bold')

        plt.tight_layout()
        st.pyplot(fig)


        st.subheader("Score Distribution by Subject")
        if not df_buckets.empty:
            fig = plot_enhanced_bar(df_buckets, "Subject-wise Score Distribution")
            st.pyplot(fig)
        else:
            st.warning("No score distribution data available")
        
        st.subheader("Average Scores by Subject")
        if not df_avg.empty:
            fig, ax = plt.subplots(figsize=(14, 8))
            
            # Sort scores to get darker colors for higher values
            scores = df_avg["Average"]
            ranks = scores.rank(ascending=False).astype(int)  # 1 = highest score
            n_colors = len(scores)
            
            # Generate a reversed Blues palette (darker → lighter)
            palette = sns.color_palette("Blues", n_colors=n_colors)[::-1]
            
            # Map ranks to colors
            colors = [palette[rank - 1] for rank in ranks]

            sns.barplot(x=df_avg.index, y=scores, palette=colors)

            # Add value labels
            for i, v in enumerate(scores):
                ax.text(i, v + 0.5, f"{v:.1f}", ha='center', va='bottom', fontweight='bold')

            plt.xticks(rotation=45, ha="right", fontsize = 8)
            plt.title("Average Scores by Subject")
            plt.ylabel("Average Score")
            plt.tight_layout()
            st.pyplot(fig)

        else:
            st.warning("No average score data available")
    # Prepare full_data for top scorers (must include Roll No and Student Name)
        if st.session_state.processed_data is not None:
            df_raw_data = st.session_state.processed_data.copy()
        elif st.session_state.scraped_results is not None:
            df_raw_data = pd.DataFrame([
                {
                    "Roll No": record["Roll No"],
                    "Student Name": record["Student Name"],
                    **{s["Subject"]: s["Marks"] for s in record["Subjects"]}
                }
                for record in st.session_state.scraped_results
            ])
        else:
            df_raw_data = pd.DataFrame(columns=["Roll No", "Student Name"])


    with tab2:
        # st.subheader("Subject Group Analysis")

        # if "saved_subject_groups" not in st.session_state:
        #     st.session_state.saved_subject_groups = []
        # if "temp_subjects" not in st.session_state:
        #     st.session_state.temp_subjects = []

        # all_subjects = list(subject_scores.keys())
        # st.markdown("### Create New Group")

        # # Checkboxes for each subject
        # selected_subjects = []
        # cols = st.columns(4)
        # for i, subject in enumerate(all_subjects):
        #     with cols[i % 4]:
        #         if st.checkbox(subject, value=subject in st.session_state.temp_subjects, key=f"sub_chk_{subject}"):
        #             selected_subjects.append(subject)
        # st.session_state.temp_subjects = selected_subjects

        # group_name = st.text_input("Group Name")

        # if st.button("Save Group"):
        #     if group_name and selected_subjects:
        #         st.session_state.saved_subject_groups.append({
        #             "name": group_name,
        #             "subjects": selected_subjects
        #         })
        #         st.success(f"Group '{group_name}' saved.")
        #         st.session_state.temp_subjects = []

        # if st.session_state.saved_subject_groups:
        #         show_top_scorers_table(st.session_state.saved_subject_groups, subject_scores, df_raw_data)
        pass

    
    with tab3:
        st.subheader("Heatmap of Performance")
        if not df_buckets.empty:
            fig, ax = plt.subplots(figsize=(12, 8))
            sns.heatmap(df_buckets, annot=True, fmt="d", cmap="Blues", ax=ax)
            plt.title("Score Range Heatmap by Subject")
            st.pyplot(fig)
        else:
            st.warning("No data available for heatmap")

    # Tab 4 - Teacher Wise Report
    with tab4:
        st.subheader("Teacher-wise Comparative Report")

        if "teacher_entries" not in st.session_state:
            st.session_state.teacher_entries = []

        if st.button("Add Teacher"):
            st.session_state.teacher_entries.append({
                "name": "",
                "rolls": [],
                "subject": "",
                "show_graphs": False  # Track if graphs should be shown
            })

        # Roll number mapping
        roll_map = {
            r['Roll No']: r for r in data_source
        } if isinstance(data_source, list) else {
            row['Roll No']: row.to_dict() for _, row in data_source.iterrows()
        }

        # Extract subject list
        all_subjects = set()
        for r in roll_map.values():
            for subj in r.get("Subjects", []):
                all_subjects.add(subj.get("Subject", ""))
        all_subjects = sorted(all_subjects)

        for idx, teacher in enumerate(st.session_state.teacher_entries):
            st.markdown(f"Teacher {idx + 1}")

            teacher["name"] = st.text_input(
                f"Name of Teacher {idx+1}", value=teacher["name"], key=f"name_{idx}"
            )

            teacher["subject"] = st.selectbox(
                f"Subject Taught by {teacher['name'] or f'Teacher {idx+1}'}",
                all_subjects,
                index=all_subjects.index(teacher["subject"]) if teacher["subject"] in all_subjects else 0,
                key=f"subject_{idx}"
            )

            # Checkboxes for selecting roll numbers
            selected_rolls = []
            with st.expander(f"Select Students (Roll Numbers) for {teacher['name'] or f'Teacher {idx+1}'}"):
                for roll_no in roll_map.keys():
                    checked = roll_no in teacher["rolls"]
                    if st.checkbox(f"{roll_no}", checked, key=f"{roll_no}_{idx}"):
                        selected_rolls.append(roll_no)

            teacher["rolls"] = selected_rolls

            # Save selection
            if st.button(f"Save Selections for Teacher {idx+1}"):
                teacher["show_graphs"] = True

            if teacher.get("show_graphs", False):
                selected_results = [roll_map[r] for r in teacher["rolls"] if r in roll_map]
                selected_subject = teacher["subject"]

                pass_count = 0
                subject_scores = []

                for student in selected_results:
                    subjects = student.get("Subjects", [])
                    for subj in subjects:
                        if subj.get("Subject") == selected_subject:
                            try:
                                score = float(subj.get("Total", 0))
                                if student.get("Status", "").upper() == "PASS":
                                    pass_count += 1
                                subject_scores.append(score)
                            except (ValueError, TypeError):
                                continue

                total = len(selected_results)

                col1, col2 = st.columns(2)

                with col1:
                    st.markdown(f"**{pass_count} Passed** / **{total - pass_count} Reappeared**")

                    if total > 0:
                        fig, ax = plt.subplots(figsize=(3.5, 3.5))
                        ax.pie(
                            [pass_count, total - pass_count],
                            labels=["Pass", "Reappear"],
                            autopct='%1.1f%%',
                            colors=['#2e7d32', '#ef5350'],
                            startangle=90
                        )
                        ax.set_title(f"{teacher['name']} - {selected_subject}")
                        st.pyplot(fig)
                    else:
                        st.warning("No students selected for this teacher to display pie chart.")

                with col2:
                    if subject_scores:
                        fig, ax = plt.subplots(figsize=(5, 3))
                        sns.histplot(subject_scores, bins=10, kde=True, ax=ax, color="skyblue")
                        ax.set_title(f"Distribution of Marks in {selected_subject}")
                        ax.set_xlabel("Marks")
                        st.pyplot(fig)
                    else:
                        st.info("No valid scores available for selected subject.")
    
    if st.button("Back to Data Input Page"):
        st.session_state.page = "page1"
        st.rerun()

# ========== Main App ==========
# Modify main()
def main():

    if 'page' not in st.session_state:
        st.session_state.page = "page1"

    if st.session_state.page == "page1":
        page1()
    elif st.session_state.page == "page2":
        page2()

if __name__ == "__main__":
    main()