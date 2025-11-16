import sys

import pandas as pd
import pdfplumber

MAYOR_1_PAGES = (0, 49)

if __name__ == "__main__":
    mayor_table_setting = {
        "horizontal_strategy": "text",
    }

    pdf = pdfplumber.open(sys.argv[1])

    output_rows = []
    for page_num in range(*MAYOR_1_PAGES):
        page = pdf.pages[page_num]
        table = page.extract_table(mayor_table_setting)
        total_rows = [row for row in table if row[1] and (row[1].strip() == "Total")]
        output_rows.extend(total_rows)

    df = pd.DataFrame(output_rows)
