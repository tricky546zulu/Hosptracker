import pdfplumber
import requests
from io import BytesIO
from datetime import datetime
from models import db, HospitalData, ScrapingLog

def run_scraping():
    """
    Scrapes hospital capacity data from the eHealth Saskatchewan PDF report
    using pdfplumber.
    """
    pdf_url = "https://www.ehealthsask.ca/reporting/Documents/SaskatoonHospitalBedCapacity.pdf"
    scraping_time = datetime.utcnow()
    status = "success"
    message = "Scraping completed successfully."

    hospital_codes = {
        "Royal University Hospital": "RUH",
        "St. Paul's Hospital": "SPH",
        "Saskatoon City Hospital": "SCH",
        "Jim Pattison Children's Hospital": "JPCH"
    }

    try:
        print("Starting hospital data scraping with pdfplumber")

        # Download the PDF content
        response = requests.get(pdf_url)
        response.raise_for_status()  # Raise an exception for bad status codes
        pdf_file = BytesIO(response.content)

        all_data = []

        with pdfplumber.open(pdf_file) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables()
                for table in tables:
                    for row in table:
                        # Clean row data by removing None and stripping whitespace
                        cleaned_row = [cell.strip() if cell else "" for cell in row]

                        # Check if the row contains the data we need
                        if "Pts in ED" in cleaned_row and "Site" in cleaned_row:
                            # Find the indices for the required columns
                            try:
                                site_index = cleaned_row.index("Site")
                                pts_in_ed_index = cleaned_row.index("Pts in ED")
                            except ValueError:
                                continue # Skip if headers are not found in this row

                            # Find the data rows that follow the header
                            header_row_index = table.index(row)
                            for data_row in table[header_row_index + 1:]:
                                cleaned_data_row = [cell.strip() if cell else "" for cell in data_row]
                                if len(cleaned_data_row) > max(site_index, pts_in_ed_index):
                                    site_name = cleaned_data_row[site_index]
                                    hospital_code = hospital_codes.get(site_name)

                                    if hospital_code:
                                        try:
                                            patient_count = int(cleaned_data_row[pts_in_ed_index])
                                            all_data.append({
                                                "hospital_code": hospital_code,
                                                "patient_count": patient_count,
                                                "timestamp": scraping_time
                                            })
                                        except (ValueError, IndexError):
                                            # Ignore rows where patient count is not a valid integer or index is out of bounds
                                            continue

        if not all_data:
            raise ValueError
