"""Generate sample data files for testing. Run once."""
import pandas as pd
from pathlib import Path

out = Path("sample_data")
out.mkdir(exist_ok=True)

# Machines tab
machines_data = {
    "Year": [2023]*8 + [2024]*8,
    "Quarter": (["Q1","Q1","Q2","Q2","Q3","Q3","Q4","Q4"] * 2),
    "Month": ["Jan","Feb","Apr","May","Jul","Aug","Oct","Nov"] * 2,
    "Machine Type": ["New","Existing"] * 8,
    "Session Count": [
        120, 540,   # Q1-2023
        145, 610,   # Q2-2023
        110, 590,   # Q3-2023
        170, 680,   # Q4-2023
        200, 750,   # Q1-2024
        230, 820,   # Q2-2024
        190, 800,   # Q3-2024
        260, 910,   # Q4-2024
    ],
}

# Software tab
software_data = {
    "Product": [
        "AutoCAD","AutoCAD","AutoCAD",
        "Revit","Revit","Revit",
        "Inventor","Inventor",
        "Navisworks","Navisworks",
        "Civil 3D","Civil 3D",
    ],
    "Version": [
        "2024","2023","2022",
        "2024","2023","2022",
        "2024","2023",
        "2024","2023",
        "2024","2023",
    ],
    "Usage Count": [
        380, 210, 95,
        290, 180, 60,
        145, 88,
        72, 41,
        55, 30,
    ],
}

# Cities tab
cities_data = {
    "Country": [
        "USA","USA","USA","USA",
        "Canada","Canada",
        "UK","UK",
        "Germany","Australia",
        "France","Japan",
    ],
    "City": [
        "New York","Chicago","Houston","San Francisco",
        "Toronto","Vancouver",
        "London","Manchester",
        "Berlin","Sydney",
        "Paris","Tokyo",
    ],
    "Session Count": [
        420, 310, 280, 195,
        175, 130,
        220, 145,
        165, 140,
        110, 95,
    ],
}

machines_df = pd.DataFrame(machines_data)
software_df = pd.DataFrame(software_data)
cities_df   = pd.DataFrame(cities_data)

# Write multi-tab XLSX
with pd.ExcelWriter(out / "sample_usage.xlsx", engine="openpyxl") as xl:
    machines_df.to_excel(xl, sheet_name="Machine Sessions", index=False)
    software_df.to_excel(xl, sheet_name="Software Usage",   index=False)
    cities_df.to_excel(xl,   sheet_name="City Locations",   index=False)

print("Written sample_data/sample_usage.xlsx")

# Write machines-only CSV (for quick test)
machines_df.to_csv(out / "sample_machines.csv", index=False)
print("Written sample_data/sample_machines.csv")
