import json
import re

# Step 1: Load the JSON file
with open("OCR_data.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# Step 2: Get markdown content
markdown = data.get("markdown", "")

# Step 3: Extract all 6-digit numbers using regex
roll_numbers = re.findall(r"\b\d{6}\b", markdown)

# Step 4: Output the list
print("Extracted 6-digit roll numbers:")
print(roll_numbers)
