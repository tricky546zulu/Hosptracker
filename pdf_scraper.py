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
                    
                    # Log the entire table structure for debugging
                    logging.info("Full table content:")
                    for idx, row in df.iterrows():
                        row_content = ' | '.join(str(cell).strip() for cell in row.values)
                        logging.info(f"Row {idx}: {row_content}")
                    
                    # Identify column headers
                    header_row_idx = None
                    admitted_col_idx = None
                    total_col_idx = None
                    
                    for idx, row in df.iterrows():
                        row_text = ' '.join(str(cell).strip().lower() for cell in row.values)
                        if 'admitted' in row_text and 'pts' in row_text:
                            header_row_idx = idx
                            # Find the column indices
                            for col_idx, cell in enumerate(row.values):
                                cell_text = str(cell).strip().lower()
                                if 'admitted' in cell_text and 'pts' in cell_text:
                                    admitted_col_idx = col_idx
                                elif 'total' in cell_text and 'pts' in cell_text:
                                    total_col_idx = col_idx
                            logging.info(f"Found header at row {idx}, admitted_col: {admitted_col_idx}, total_col: {total_col_idx}")
                            break
                    
                    # Extract data with column awareness
                    for idx, row in df.iterrows():
                        if idx != header_row_idx:  # Skip header row
                            row_data = self._extract_hospital_from_row_with_columns(row, admitted_col_idx, total_col_idx)
                            if row_data:
                                hospital_data.append(row_data)
                                logging.info(f"Found {row_data['hospital_code']}: {row_data['total_patients']} total, {row_data['admitted_patients_in_ed']} admitted")
                        
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
    
    def _extract_hospital_from_row_with_columns(self, row, admitted_col_idx, total_col_idx):
        """Extract hospital data from a row using specific column indices"""
        try:
            row_text = ' '.join(str(cell).strip() for cell in row.values)
            
            # Check if this row contains a hospital code
            for code, name in self.hospital_mapping.items():
                if code in row_text:
                    # Extract values from specific columns
                    total_patients = None
                    admitted_patients = None
                    
                    # Extract from the rightmost column for total (typically column 4 in the Saskatchewan table)
                    if len(row.values) >= 5:
                        try:
                            total_patients = int(str(row.values[4]).strip())
                        except (ValueError, TypeError):
                            total_patients = self._extract_patient_count(row.values)
                    else:
                        total_patients = self._extract_patient_count(row.values)
                    
                    # Extract from the first column for admitted patients (column 1 after Site name)
                    if len(row.values) >= 2:
                        try:
                            admitted_patients = int(str(row.values[1]).strip())
                        except (ValueError, TypeError):
                            admitted_patients = None
                    else:
                        admitted_patients = None
                    
                    if total_patients is not None:
                        return {
                            'hospital_code': code,
                            'hospital_name': name,
                            'total_patients': total_patients,
                            'admitted_patients_in_ed': admitted_patients
                        }
                        
        except Exception as e:
            logging.warning(f"Error parsing row with columns: {str(e)}")
            
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
        """Save hospital data to database with validation"""
        try:
            # Define reasonable ranges for validation
            hospital_ranges = {
                'RUH': {'min': 15, 'max': 120},
                'SPH': {'min': 5, 'max': 80},
                'SCH': {'min': 0, 'max': 60},
                'JPCH': {'min': 0, 'max': 40}
            }
            
            valid_data = []
            for data in hospital_data:
                total_patients = data['total_patients']
                hospital_code = data['hospital_code']
                
                # Validate patient count is reasonable
                range_check = hospital_ranges.get(hospital_code, {'min': 0, 'max': 200})
                if total_patients < range_check['min'] or total_patients > range_check['max']:
                    logging.warning(f"Skipping {hospital_code} data: {total_patients} patients outside reasonable range {range_check}")
                    continue
                
                # Check for sudden changes compared to recent data
                recent = HospitalCapacity.query.filter_by(hospital_code=hospital_code).order_by(
                    HospitalCapacity.timestamp.desc()
                ).first()
                
                if recent and recent.total_patients > 0:
                    change_percent = abs(total_patients - recent.total_patients) / recent.total_patients
                    time_diff = (datetime.utcnow() - recent.timestamp).total_seconds() / 60  # minutes
                    
                    # Skip if more than 50% change in less than 30 minutes (likely error)
                    if change_percent > 0.5 and time_diff < 30:
                        logging.warning(f"Skipping {hospital_code} data: {recent.total_patients} -> {total_patients} ({change_percent*100:.1f}% change in {time_diff:.1f} minutes)")
                        continue
                
                valid_data.append(data)
            
            # Save valid data
            for data in valid_data:
                hospital = HospitalCapacity()
                hospital.hospital_code = data['hospital_code']
                hospital.hospital_name = data['hospital_name']
                hospital.total_patients = data['total_patients']
                hospital.admitted_patients_in_ed = data['admitted_patients_in_ed']
                db.session.add(hospital)
            
            db.session.commit()
            logging.info(f"Saved {len(valid_data)} validated hospital records to database (filtered {len(hospital_data) - len(valid_data)} invalid records)")
            
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