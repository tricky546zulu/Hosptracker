import pdfplumber
import requests
from io import BytesIO
from datetime import datetime
from models import db, HospitalData, ScrapingLog
import re # Import regex for parsing hospital codes

def run_scraping():
    """
    Scrapes hospital capacity data from the eHealth Saskatchewan PDF report
    using pdfplumber.
    """
    pdf_url = "https://www.ehealthsask.ca/reporting/Documents/SaskatoonHospitalBedCapacity.pdf"
    scraping_time = datetime.utcnow()
    status = "success"
    message = "Scraping completed successfully."

    # Updated hospital codes to match the format in the PDF (e.g., "RUH")
    # We will extract the code from the first cell of the row
    valid_hospital_codes = ["RUH", "SPH", "SCH", "JPCH"]

    try:
        print("Starting hospital data scraping with pdfplumber")

        # Download the PDF content
        response = requests.get(pdf_url)
        response.raise_for_status()  # Raise an exception for bad status codes
        pdf_file = BytesIO(response.content)

        all_data = []

        with pdfplumber.open(pdf_file) as pdf:
            # Iterate through all pages to find the table
            for page in pdf.pages:
                # Extract tables from the page
                tables = page.extract_tables()

                for table in tables:
                    # Iterate through rows to find data
                    for row in table:
                        # Clean row data by removing None and stripping whitespace
                        cleaned_row = [cell.strip() if cell else "" for cell in row]

                        # Check if the first cell contains a hospital code followed by a colon
                        # e.g., "JPCH:"
                        if cleaned_row and cleaned_row[0]:
                            match = re.match(r'([A-Z]{3,4}):', cleaned_row[0])
                            if match:
                                hospital_code = match.group(1)
                                if hospital_code in valid_hospital_codes:
                                    # Extract numerical data from the rest of the row
                                    # Assuming the last number is the total Pts in ED
                                    numerical_values = []
                                    for cell in cleaned_row[1:]: # Start from the second cell
                                        try:
                                            numerical_values.append(int(cell))
                                        except ValueError:
                                            continue # Skip non-integer cells

                                    if numerical_values:
                                        patient_count = numerical_values[-1] # Take the last numerical value
                                        all_data.append({
                                            "hospital_code": hospital_code,
                                            "patient_count": patient_count,
                                            "timestamp": scraping_time
                                        })

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

if __name__ == '__main__':
    # This allows running the scraper manually for testing
    # Requires the Flask app context to be set up
    from main import app
    with app.app_context():
        run_scraping()
