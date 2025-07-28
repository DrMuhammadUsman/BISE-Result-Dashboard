# import requests
# from bs4 import BeautifulSoup
# import json
# import re

# def fetch_result(p, q, r):
#     url = "https://results.biserawalpindi.edu.pk/Result_Detail"
#     params = {"p": p, "q": q, "r": r}
#     headers = {"User-Agent": "Mozilla/5.0"}
#     response = requests.get(url, params=params, headers=headers)
#     response.raise_for_status()
#     return response.text

# def parse_result(html):
#     soup = BeautifulSoup(html, "html.parser")
#     result = {}

#     # Extract basic fields
#     text_fields = {
#         "ROLL NO": "Roll No",
#         "STUDENT NAME": "Student Name",
#         "STUDENT TYPE": "Student Type",
#         "FORM-ID (for office use only)": "Form-ID",
#         "GRAND TOTAL": "Grand Total",
#         "STATUS": "Status",
#         "PERCENTILE MARKS": "Percentile Marks",
#         "RELATIVE GRADE": "Relative Grade",
#         "REMARKS": "Remarks"
#     }

#     for field, label in text_fields.items():
#         tag = soup.find(string=re.compile(field))
#         if tag:
#             value = tag.find_next().get_text(strip=True)
#             result[label] = value

#     # Extract subject-wise marks
#     result["Subjects"] = []
#     table = soup.find("table")
#     if table:
#         headers = [th.get_text(strip=True) for th in table.find_all("th")]
#         for row in table.find_all("tr")[1:]:
#             cells = row.find_all("td")
#             if cells:
#                 subject_data = dict(zip(headers, [td.get_text(strip=True) for td in cells]))
#                 filtered_subject = {
#                     "Subject": subject_data.get("SUBJECT"),
#                     "Theory-I": subject_data.get("THEORY-I"),
#                     "Theory-II": subject_data.get("THEORY-II"),
#                     "Practical": subject_data.get("PRACTICAL"),
#                     "Total": subject_data.get("TOTAL")
#                 }
#                 result["Subjects"].append(filtered_subject)
#     return result

# def parse_p_input(p_input):
#     p_values = []
#     parts = p_input.split(',')
#     for part in parts:
#         if '-' in part:
#             start, end = map(int, part.split('-'))
#             p_values.extend(range(start, end + 1))
#         else:
#             p_values.append(int(part))
#     return p_values

# def main(p_input, q=2, r=2025, output_file="results.json"):
#     p_list = parse_p_input(p_input)
#     all_results = []

#     for p in p_list:
#         try:
#             print(f"Fetching result for p={p}")
#             html = fetch_result(p, q, r)
#             data = parse_result(html)
#             data["P"] = p  # To keep track of the parameter
#             all_results.append(data)
#         except Exception as e:
#             print(f"Error fetching p={p}: {e}")

#     with open(output_file, "w", encoding="utf-8") as f:
#         json.dump(all_results, f, indent=2, ensure_ascii=False)
#     print(f"Saved {len(all_results)} results to {output_file}")

# if __name__ == "__main__":
#     # Example usage: input any mix of individual or ranges
#     user_input = "123075,123076,123078-123080"
#     main(user_input)


import requests
from bs4 import BeautifulSoup
import json
import re

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

    # Extract top-level student info
    info["Roll No"] = get_field("ROLL NO")
    info["Student Name"] = get_field("STUDENT NAME")
    info["Student Type"] = get_field("STUDENT TYPE")
    info["Grand Total"] = get_field("GRAND TOTAL")
    info["Status"] = get_field("STATUS")

    # Subject Table Processing
    subject_table = soup.find("table")
    subjects = []

    if subject_table:
        rows = subject_table.find_all("tr")
        headers = [th.get_text(strip=True).upper() for th in rows[0].find_all("th")]

        for row in rows[1:]:
            cells = row.find_all("td")
            if len(cells) != len(headers):
                continue  # skip malformed or irrelevant rows

            values = [td.get_text(strip=True) for td in cells]
            row_dict = dict(zip(headers, values))

            if not row_dict.get("SUBJECT"):
                continue  # skip invalid subjects

            subject_entry = {
                "Subject": row_dict.get("SUBJECT", ""),
                "Theory-I": row_dict.get("THEORY-I", ""),
                "Theory-II": row_dict.get("THEORY-II", ""),
                "Practical": row_dict.get("PRACTICAL", ""),
                "Total": row_dict.get("TOTAL", "")
            }

            # Optional Fields
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
        if '-' in part:
            start, end = map(int, part.split('-'))
            result.extend(range(start, end + 1))
        else:
            result.append(int(part))
    return result

def main(p_values, q=2, r=2025, output="results_107004_ad.json"):
    p_list = parse_p_input(p_values)
    all_results = []

    for p in p_list:
        try:
            print(f"Fetching p={p}")
            html = fetch_html(p, q, r)
            result = extract_result(html)
            if result.get("Roll No"):  # Only include if valid
                all_results.append(result)
        except Exception as e:
            print(f"Failed for p={p}: {e}")

    with open(output, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    print(f"Saved {len(all_results)} results to {output}")

if __name__ == "__main__":
    # Example usage: individual and range combined
    user_input = "103683,124861"
    main(user_input)
