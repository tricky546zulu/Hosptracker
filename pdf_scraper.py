import os
import re
import requests
import pdfplumber
from io import BytesIO
from datetime import datetime
from main import app, db
from models import Hospital, HospitalData, ScrapingLog

def log_scraping_attempt(status, message):
    """Logs the result of a scraping attempt to the database."""
    with app.app_context():
        try:
            log_entry = ScrapingLog(timestamp=datetime.utcnow(), status=status, message=message)
            db.session.add(log_entry)
            db.session.commit()
        except Exception as e:
            # If logging fails, print the error to the console
            print(f"Failed to log scraping result: {e}")
            db.session.rollback()

def run_scraping():
    """
    Scrapes hospital capacity data from a PDF and stores it in the database.
    """
    pdf_url = "https://www.saskhealthauthority.ca/sites/default/files/2024-07/ER-Capacity-Report.pdf"
    print("Starting hospital data scraping with pdfplumber")

    try:
        response = requests.get(pdf_url)
        response.raise_for_status()
        pdf_file = BytesIO(response.content)

        with pdfplumber.open(pdf_file) as pdf:
            page = pdf.pages[0]
            text = page.extract_text()

        if not text:
            raise ValueError("Could not extract text from the PDF.")

        # Use regex to find the "Last Update" timestamp
        last_update_match = re.search(r"Last Update: (\w+\s+\d{1,2}, \d{4}, \d{1,2}:\d{2}:\d{2} [ap]\.m\.)", text)
        if not last_update_match:
            raise ValueError("Could not find the 'Last Update' timestamp in the PDF.")

        last_update_str = last_update_match.group(1)
        last_update = datetime.strptime(last_update_str, "%B %d, %Y, %I:%M:%S %p")

        # Define the expected hospital names and their abbreviations
        hospital_mapping = {
            "St. Paul's Hospital": "SPH",
            "Saskatoon City Hospital": "SCH",
            "Jim Pattison Children's Hospital": "JPCH",
            "Royal University Hospital": "RUH"
        }

        data_found = False
        with app.app_context():
            for full_name, code in hospital_mapping.items():
                # Regex to find the data for each hospital
                pattern = re.compile(rf"{re.escape(full_name)}\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)")
                match = pattern.search(text)

                if match:
                    data_found = True
                    inpatient_beds, overcapacity_beds, total_patients, waiting_for_inpatient_bed = map(int, match.groups())

                    hospital = Hospital.query.filter_by(code=code).first()
                    if not hospital:
                        hospital = Hospital(code=code, name=full_name)
                        db.session.add(hospital)
                        db.session.commit()

                    # Check if data for this timestamp already exists
                    existing_data = HospitalData.query.filter_by(
                        hospital_id=hospital.id,
                        timestamp=last_update
                    ).first()

                    if not existing_data:
                        hospital_data = HospitalData(
                            hospital_id=hospital.id,
                            timestamp=last_update,
                            inpatient_beds=inpatient_beds,
                            overcapacity_beds=overcapacity_beds,
                            total_patients=total_patients,
                            waiting_for_inpatient_bed=waiting_for_inpatient_bed
                        )
                        db.session.add(hospital_data)

            if not data_found:
                raise ValueError("Could not find any valid hospital data in the PDF.")

            db.session.commit()
            log_message = f"Successfully scraped data for timestamp: {last_update_str}"
            print(log_message)
            log_scraping_attempt("success", log_message)

    except Exception as e:
        error_message = f"Error scraping hospital data: {e}"
        print(error_message)
        log_scraping_attempt("error", error_message)
        with app.app_context():
            db.session.rollback()

if __name__ == "__main__":
    run_scraping()
