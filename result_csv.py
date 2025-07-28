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
#"107004, 103516, 103657, 103524, 103659, 103531, 103661, 103540, 103663, 103546, 103664, 103552, 103667, 103557, 103669, 103563, 103670, 103568, 103671, 103575, 103672, 103580, 103673, 103587, 103674, 103591, 103675, 103594, 103676, 103598, 103677, 103603, 103678, 103606, 103679, 103607, 103680, 103612, 103681, 103615, 103682, 103617, 103683, 103620, 103684, 103624, 103685, 103626, 103686, 103630, 103687, 103632, 103688, 103636, 103689, 103639, 103690, 103641, 103691, 103644, 103692, 103647, 103693, 103651, 103694, 103654, 103695, 124857, 103696, 124859, 103697, 124861, 103698, 124864, 124723, 124866, 124733, 124867, 124741, 124869, 124747, 124872, 124755, 124873, 124763, 124875, 124771, 124876, 124778, 124877, 124785, 124878, 124795, 124879, 124802, 124880, 124806, 124881, 124811, 124882, 124815, 124883, 124820, 124884, 124821, 124885, 124823, 124886, 124825, 124887, 124828, 124888, 124830, 124889, 124832, 124890, 124834, 124891, 124836, 124892, 124838, 124893, 124840, 124894, 124842, 124895, 124843, 124896, 124846, 124897, 124847, 124898, 124849, 124899, 124851, 124900, 124853, 124901, 124856, 124902, 124903, 133639, 124904, 133640, 124905, 133642, 124906, 133643, 133522, 133644, 133530, 133645, 133543, 133646, 133548, 133647, 133553, 133648, 133561, 133649, 133566, 133650, 133573, 133651, 133582, 133652, 133583, 133653, 133588, 133654, 133590, 133655, 133593, 133656, 133597, 133657, 133600, 133658, 133603, 133659, 133605, 133660, 133607, 133661, 133608, 133662, 133611, 133663, 133613, 133664, 133615, 133665, 133617, 133666, 133619, 133667, 133621, 133668, 133622, 133669, 133625, 133670, 133627, 133671, 133629, 140903, 133631, 140911, 133633, 140916, 133635, 140925, 133637, 140933, 140936, 141048, 140946, 141049, 140953, 141050, 140956, 141051, 140963, 141052, 140970, 141053, 140976, 141054, 140980, 141055, 140984, 141056, 140987, 141057, 140990, 141058, 140993, 141059, 140996, 141060, 140999, 141061, 141002, 141062, 141005, 141063, 141008, 141064, 141012, 141065, 141015, 141066, 141017, 141067, 141020, 141068, 141022, 141069, 141023, 141070, 141026, 141071, 141027, 141072, 141029, 141073, 141031, 141074, 141033, 141075, 141036, 141076, 141038, 141077, 141040, 141078, 141041, 141079, 141043, 141080, 141044, 141081, 141045, 154007, 141046, 154010, 141047, 154020, 154033, 154156, 154040, 154157, 154045, 154158, 154052, 154159, 154066, 154160, 154074, 154161, 154080, 154162, 154085, 154163, 154091, 154164, 154095, 154165, 154098, 154166, 154103, 154167, 154106, 154168, 154108, 154169, 154111, 154170, 154115, 154171, 154117, 154172, 154119, 154173, 154121, 154174, 154123, 154175, 154125, 154176, 154127, 154177, 154129, 154178, 154131, 154179, 154133, 154180, 154135, 154181, 154137, 154182, 154139, 154183, 154141, 154184, 154142, 154185, 154145, 154186, 154147, 160608, 154149, 160617, 154151, 160621, 154152, 160629, 154154, 160636, 154155, 160642, 160651, 160718, 160653, 160719, 160660, 160720, 160666, 160721, 160670, 160722, 160673, 160723, 160674, 160724, 160677, 160725, 160681, 160726, 160683, 160727, 160684, 160728, 160687, 160729, 160689, 160730, 160691, 160731, 160693, 160732, 160694, 160733, 160696, 160734, 160698, 160735, 160699, 160736, 160700, 160737, 160701, 160738, 160702, 160739, 160703, 160740, 160704, 160741, 160705, 160742, 160706, 160743, 160707, 160744, 160708, 160745, 160709, 160746, 160710, 160747, 160711, 160748, 160712, 160749, 160713, 160750, 160714, 160751, 160715, 160752, 160716, 160753, 160717"
    main(user_input)
