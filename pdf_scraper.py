import camelot
import requests
import logging
from datetime import datetime
from app import db
from models import HospitalCapacity, ScrapingLog

class HospitalDataScraper:
    def __init__(self):
        self.pdf_url = "https://www.ehealthsask.ca/reporting/Documents/SaskatoonHospitalBedCapacity.pdf"
        self.hospital_mapping = {
            'RUH': 'Royal University Hospital',
            'SPH': 'St. Paul\'s Hospital', 
            'SCH': 'Saskatoon City Hospital',
            'JPCH': 'Jim Pattison Children\'s Hospital'
        }
        
    def scrape_hospital_data(self):
        """Main method to scrape hospital data using Camelot"""
        try:
            logging.info("Starting hospital data scraping with Camelot")
            
            # Download and extract tables using Camelot
            tables = camelot.read_pdf(self.pdf_url, pages='all', flavor='lattice')
            
            if not tables:
                raise Exception("No tables found in PDF")
                
            logging.info(f"Found {len(tables)} tables in PDF")
            
            # Process tables to find Emergency Department data
            hospital_data = self._extract_emergency_department_data(tables)
            
            if hospital_data:
                self._save_hospital_data(hospital_data)
                self._log_scraping_result('success', f'Successfully processed {len(hospital_data)} hospitals')
                return True
            else:
                self._log_scraping_result('error', 'No hospital data found in tables')
                return False
                
        except Exception as e:
            error_msg = f"Error scraping hospital data: {str(e)}"
            logging.error(error_msg)
            self._log_scraping_result('error', error_msg)
            return False
    
    def _extract_emergency_department_data(self, tables):
        """Extract Emergency Department data from tables"""
        hospital_data = []
        
        for table_num, table in enumerate(tables):
            try:
                df = table.df
                logging.info(f"Processing table {table_num + 1} with shape {df.shape}")
                
                # Convert entire dataframe to string for searching
                table_text = df.to_string()
                
                # Look for the specific Emergency Department summary table
                if 'Pts in ED' in table_text and 'Site' in table_text:
                    logging.info(f"Found Emergency Department summary table {table_num + 1}")
                    
                    # Look for hospital codes in each row
                    for idx, row in df.iterrows():
                        row_data = self._extract_hospital_from_row(row)
                        if row_data:
                            hospital_data.append(row_data)
                            logging.info(f"Found {row_data['hospital_code']}: {row_data['total_patients']} patients")
                        
            except Exception as e:
                logging.warning(f"Error processing table {table_num + 1}: {str(e)}")
                continue
        
        return hospital_data
    
    def _extract_hospital_from_row(self, row):
        """Extract hospital data from a single row"""
        try:
            row_text = ' '.join(str(cell).strip() for cell in row if str(cell).strip())
            
            # Check for hospital codes
            for code, name in self.hospital_mapping.items():
                if code in row_text:
                    # Extract patient count from the row
                    patient_count = self._extract_patient_count(row)
                    
                    if patient_count is not None:
                        admitted_count = self._extract_admitted_patients_count(row)
                        logging.info(f"Found {code}: {patient_count} total patients, {admitted_count} admitted in ED")
                        return {
                            'hospital_code': code,
                            'hospital_name': name,
                            'total_patients': patient_count,
                            'admitted_patients_in_ed': admitted_count
                        }
                        
        except Exception as e:
            logging.warning(f"Error parsing row: {str(e)}")
            
        return None
    
    def _extract_patient_count(self, row):
        """Extract total patient count from a table row"""
        numbers = []
        for cell in row:
            try:
                cell_str = str(cell).strip()
                if cell_str.isdigit():
                    count = int(cell_str)
                    if 0 <= count <= 500:  # Reasonable range for ED patients
                        numbers.append(count)
            except (ValueError, TypeError):
                continue
        
        # Return the last (rightmost) number found, as this is typically the total
        return numbers[-1] if numbers else None
    
    def _extract_admitted_patients_count(self, row):
        """Extract admitted patients in ED count from a table row"""
        # Look for the pattern: admitted patients are typically in the second-to-last numeric column
        numbers = []
        row_str = ' '.join(str(cell).strip() for cell in row)
        
        # Log the row for debugging
        logging.debug(f"Analyzing row for admitted patients: {row_str}")
        
        for cell in row:
            try:
                cell_str = str(cell).strip()
                if cell_str.isdigit():
                    count = int(cell_str)
                    if 0 <= count <= 200:  # Reasonable range for admitted patients in ED
                        numbers.append(count)
            except (ValueError, TypeError):
                continue
        
        # If we have multiple numbers, the admitted count is typically the second-to-last
        # This follows the pattern: [other data] [admitted_in_ed] [total_patients]
        if len(numbers) >= 2:
            admitted_count = numbers[-2]
            logging.debug(f"Found {len(numbers)} numbers: {numbers}, using {admitted_count} as admitted count")
            return admitted_count
        
        # If we can't distinguish, return None for now
        return None
    
    def _save_hospital_data(self, hospital_data):
        """Save hospital data to database"""
        try:
            for data in hospital_data:
                hospital = HospitalCapacity()
                hospital.hospital_code = data['hospital_code']
                hospital.hospital_name = data['hospital_name']
                hospital.total_patients = data['total_patients']
                db.session.add(hospital)
            
            db.session.commit()
            logging.info(f"Saved {len(hospital_data)} hospital records to database")
            
        except Exception as e:
            db.session.rollback()
            raise Exception(f"Failed to save hospital data: {str(e)}")
    
    def _log_scraping_result(self, status, message):
        """Log the scraping result"""
        try:
            log_entry = ScrapingLog()
            log_entry.status = status
            log_entry.message = message
            db.session.add(log_entry)
            db.session.commit()
        except Exception as e:
            logging.error(f"Failed to log scraping result: {str(e)}")

def run_scraping():
    """Function to run scraping - called by scheduler"""
    from app import app
    with app.app_context():
        scraper = HospitalDataScraper()
        return scraper.scrape_hospital_data()