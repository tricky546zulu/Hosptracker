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
        response.raise_for_status()
        pdf_file = BytesIO(response.content)

        all_data = []

        with pdfplumber.open(pdf_file) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables()
                for table in tables:
                    # Find the header row to locate the correct columns
                    header_row = None
                    for row in table:
                        if row and "Pts in ED" in row and "Site" in row:
                            header_row = [cell.strip() if cell else "" for cell in row]
                            break

                    if not header_row:
                        continue

                    site_index = header_row.index("Site")
                    pts_in_ed_index = header_row.index("Pts in ED")

                    # Extract data from rows following the header
                    for row in table:
                        cleaned_data_row = [cell.strip() if cell else "" for cell in row]
                        if cleaned_data_row == header_row:
                            continue # Skip the header row itself

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
                                    continue

        if not all_data:
            raise ValueError("Could not find any valid hospital data in the PDF.")

        # Save data to the database
        for data in all_data:
            hospital_data = HospitalData(
                hospital_code=data["hospital_code"],
                patient_count=data["patient_count"],
                timestamp=data["timestamp"]
            )
            db.session.add(hospital_data)

        db.session.commit()
        print(f"Successfully scraped and saved data for {len(all_data)} hospitals.")

    except Exception as e:
        status = "error"
        message = f"Error scraping hospital data: {e}"
        print(message)
        db.session.rollback()

    finally:
        # Log the scraping attempt
        try:
            log_entry = ScrapingLog(timestamp=scraping_time, status=status, message=message)
            db.session.add(log_entry)
            db.session.commit()
        except Exception as log_e:
            print(f"Failed to log scraping result: {log_e}")
            db.session.rollback()
