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
                
                # Look for Emergency Department section
                for idx, row in df.iterrows():
                    row_text = ' '.join(str(cell).strip() for cell in row if str(cell).strip())
                    
                    if 'Emergency Department' in row_text or 'Emergency' in row_text:
                        logging.info(f"Found Emergency Department section in table {table_num + 1}")
                        
                        # Extract hospital data from this table
                        table_data = self._parse_emergency_table(df, idx)
                        hospital_data.extend(table_data)
                        break
                        
            except Exception as e:
                logging.warning(f"Error processing table {table_num + 1}: {str(e)}")
                continue
        
        return hospital_data
    
    def _parse_emergency_table(self, df, start_idx):
        """Parse Emergency Department table starting from given index"""
        hospital_data = []
        
        # Look for hospital codes and patient counts in subsequent rows
        for idx in range(start_idx, min(start_idx + 20, len(df))):
            try:
                row = df.iloc[idx]
                row_text = ' '.join(str(cell).strip() for cell in row if str(cell).strip())
                
                # Check for hospital codes
                for code, name in self.hospital_mapping.items():
                    if code in row_text:
                        # Extract patient count from the row
                        patient_count = self._extract_patient_count(row)
                        
                        if patient_count is not None:
                            hospital_data.append({
                                'hospital_code': code,
                                'hospital_name': name,
                                'total_patients': patient_count
                            })
                            logging.info(f"Found {code}: {patient_count} patients")
                            
            except Exception as e:
                logging.warning(f"Error parsing row {idx}: {str(e)}")
                continue
        
        return hospital_data
    
    def _extract_patient_count(self, row):
        """Extract patient count from a table row"""
        for cell in row:
            try:
                cell_str = str(cell).strip()
                if cell_str.isdigit():
                    count = int(cell_str)
                    if 0 <= count <= 500:  # Reasonable range for ED patients
                        return count
            except (ValueError, TypeError):
                continue
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
            log_entry.hospitals_processed = 0
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