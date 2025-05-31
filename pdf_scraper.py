import os
import logging
import requests
import camelot
import pandas as pd
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from app import db
from models import HospitalCapacity, ScrapingLog

# Set up logging
logging.basicConfig(level=logging.DEBUG)

class HospitalDataScraper:
    def __init__(self):
        self.pdf_url = "https://www.ehealthsask.ca/reporting/Documents/SaskatoonHospitalBedCapacity.pdf"
        
        # Configuration for precise table extraction
        self.extraction_config = {
            'method': 'camelot',
            'column_mapping': {
                # Map hospital codes to which column index to use for patient count
                'RUH': -1,    # Use last column (Total)
                'SPH': -1,    # Use last column (Total)  
                'SCH': -1,    # Use last column (Total)
                'JPCH': -1    # Use last column (Total)
            },
            'table_filters': {
                'min_accuracy': 90.0,
                'required_keywords': ['Emergency Department', 'Site', 'Total'],
                'hospital_codes': ['RUH', 'SPH', 'SCH', 'JPCH']
            }
        }
        
    def scrape_hospital_data(self):
        """Main method to scrape hospital data from PDF using table extraction"""
        try:
            logging.info("Starting hospital data scraping with table extraction")
            
            # Download PDF
            pdf_content = self._download_pdf()
            if not pdf_content:
                self._log_scraping_result("error", "Failed to download PDF")
                return False
            
            # Parse PDF using table extraction
            hospital_data = self._parse_pdf_with_tables(pdf_content)
            if not hospital_data:
                self._log_scraping_result("error", "No hospital data found in PDF")
                return False
            
            # AI-powered data validation and cleanup
            validated_data = self._ai_validate_and_clean_data(hospital_data)
            
            # Save to database
            saved_count = self._save_hospital_data(validated_data)
            
            if saved_count > 0:
                self._log_scraping_result("success", f"Successfully scraped and validated data for {saved_count} hospitals")
                logging.info(f"Successfully scraped hospital data for {len(validated_data)} hospitals")
                
                # Clean up existing anomalous data
                self._clean_existing_anomalous_data()
                return True
            else:
                self._log_scraping_result("error", "No valid data passed AI validation")
                return False
                
        except Exception as e:
            error_msg = f"Error during scraping: {str(e)}"
            logging.error(error_msg)
            self._log_scraping_result("error", error_msg)
            return False
    
    def _download_pdf(self):
        """Download the PDF from eHealth website"""
        try:
            logging.info(f"Downloading PDF from {self.pdf_url}")
            response = requests.get(self.pdf_url, timeout=30)
            response.raise_for_status()
            return response.content
        except Exception as e:
            logging.error(f"Failed to download PDF: {e}")
            return None
    
    def _parse_pdf_with_tables(self, pdf_content):
        """Parse PDF using Camelot table extraction"""
        try:
            # Save PDF temporarily for Camelot processing
            temp_pdf_path = '/tmp/hospital_capacity.pdf'
            with open(temp_pdf_path, 'wb') as f:
                f.write(pdf_content)
            
            # Extract tables using Camelot
            hospital_data = self._extract_with_camelot(temp_pdf_path)
            
            return hospital_data
            
        except Exception as e:
            logging.error(f"Error parsing PDF with tables: {e}")
            return None
    
    def _extract_with_camelot(self, pdf_path):
        """Extract Emergency Department data using Camelot table extraction"""
        try:
            # Extract all tables from PDF
            tables = camelot.read_pdf(pdf_path, pages='all', flavor='lattice')
            
            hospital_data = []
            best_table = None
            max_hospitals_found = 0
            
            for i, table in enumerate(tables):
                # Check table quality
                if table.accuracy < self.extraction_config['table_filters']['min_accuracy']:
                    continue
                
                df = table.df
                
                # Check if this is an Emergency Department table
                if self._is_ed_table(df):
                    logging.info(f"Found potential Emergency Department table {i+1} with {table.accuracy:.1f}% accuracy")
                    
                    # Extract hospital data from this table
                    ed_data = self._extract_ed_data_from_table(df)
                    if ed_data:
                        # Prefer tables that have more hospitals (main ED table should have all 4)
                        if len(ed_data) > max_hospitals_found:
                            max_hospitals_found = len(ed_data)
                            best_table = ed_data
                            logging.info(f"Table {i+1} has {len(ed_data)} hospitals - new best candidate")
            
            return best_table if best_table else []
            
        except Exception as e:
            logging.error(f"Camelot extraction error: {e}")
            return []
    
    def _is_ed_table(self, df):
        """Check if this table contains the main Emergency Department totals (not specialty departments)"""
        try:
            # Convert to string to search
            table_str = df.to_string().upper()
            
            # Check for hospital codes
            hospital_codes = self.extraction_config['table_filters']['hospital_codes']
            has_hospitals = any(code in table_str for code in hospital_codes)
            
            # Make sure it's NOT a specialty department table
            specialty_indicators = ['CARDIOSCIENCES', 'MEDICINE ED', 'ONCOLOGY', 'NEUROSCIENCES']
            is_specialty_table = any(specialty in table_str for specialty in specialty_indicators)
            
            # Look for main ED table indicators - should have column headers like Admitted, Active, Consults, Total
            main_ed_indicators = ['ADMITTED', 'ACTIVE', 'CONSULTS', 'TOTAL']
            has_main_ed_structure = all(indicator in table_str for indicator in main_ed_indicators)
            
            # This should be a main ED table: has hospitals, has proper structure, NOT specialty departments
            return has_hospitals and has_main_ed_structure and not is_specialty_table
            
        except Exception as e:
            logging.error(f"Error checking ED table: {e}")
            return False
    
    def _extract_ed_data_from_table(self, df):
        """Extract specific hospital data from Emergency Department table"""
        try:
            hospital_data = []
            
            # Look for hospital rows
            for idx, row in df.iterrows():
                row_str = ' '.join(str(cell) for cell in row.values if pd.notna(cell))
                
                # Check for each hospital
                for hospital_code in self.extraction_config['table_filters']['hospital_codes']:
                    if hospital_code in row_str:
                        logging.info(f"Found {hospital_code} in table row: {row_str}")
                        
                        # Extract numbers from the row
                        numbers = []
                        for cell in row.values:
                            try:
                                if pd.notna(cell) and str(cell).strip().isdigit():
                                    numbers.append(int(cell))
                            except:
                                continue
                        
                        if numbers:
                            # Use configured column mapping
                            column_index = self.extraction_config['column_mapping'][hospital_code]
                            if abs(column_index) <= len(numbers):
                                total_patients = numbers[column_index]
                                
                                hospital_info = {
                                    'hospital_code': hospital_code,
                                    'hospital_name': self._get_full_hospital_name(hospital_code),
                                    'total_patients': total_patients
                                }
                                
                                logging.info(f"Successfully extracted data for {hospital_code}: {hospital_info}")
                                hospital_data.append(hospital_info)
                        
                        break  # Found this hospital, move to next row
            
            return hospital_data
            
        except Exception as e:
            logging.error(f"Error extracting ED data from table: {e}")
            return []
    
    def _get_full_hospital_name(self, code):
        """Get full hospital name from code"""
        names = {
            'RUH': 'Royal University Hospital',
            'SPH': 'St. Paul\'s Hospital',
            'SCH': 'Saskatoon City Hospital',
            'JPCH': 'Jim Pattison Children\'s Hospital'
        }
        return names.get(code, code)
    
    def _ai_validate_and_clean_data(self, hospital_data):
        """AI-powered validation and cleaning of scraped data"""
        try:
            from ai_monitor import validate_extracted_data
            
            # Validate data using AI
            is_valid = validate_extracted_data(hospital_data)
            
            if not is_valid:
                logging.warning("AI validation failed for scraped data")
                return []
            
            # Apply consistency rules and remove obvious anomalies
            validated_data = []
            
            for data in hospital_data:
                hospital_code = data['hospital_code']
                patient_count = data['total_patients']
                
                # Hospital-specific validation ranges based on observed data
                expected_ranges = {
                    'RUH': (20, 150),     # Large hospital
                    'SPH': (2, 25),       # Confirmed range by user
                    'SCH': (1, 70),       # Can be as low as 1 at times
                    'JPCH': (5, 40)       # Children's hospital
                }
                
                min_expected, max_expected = expected_ranges.get(hospital_code, (5, 200))
                
                # Check if value is within reasonable range
                if min_expected <= patient_count <= max_expected:
                    validated_data.append(data)
                    logging.info(f"AI validation passed for {hospital_code}: {patient_count} patients")
                else:
                    logging.warning(f"AI validation failed for {hospital_code}: {patient_count} patients outside expected range ({min_expected}-{max_expected})")
            
            return validated_data
            
        except Exception as e:
            logging.error(f"Error in AI validation: {e}")
            # Return original data if AI validation fails
            return hospital_data
    
    def _clean_existing_anomalous_data(self):
        """Clean up existing anomalous data in the database"""
        try:
            from app import db
            from models import HospitalCapacity
            from datetime import datetime, timedelta
            import pytz
            
            # Define Saskatchewan timezone
            sask_tz = pytz.timezone('America/Regina')
            utc_now = datetime.utcnow()
            
            # Look at data from the last 24 hours
            cutoff_time = utc_now - timedelta(hours=24)
            
            # Hospital-specific anomaly detection ranges
            anomaly_thresholds = {
                'RUH': {'min': 15, 'max': 200},
                'SPH': {'min': 8, 'max': 100},
                'SCH': {'min': 12, 'max': 80},
                'JPCH': {'min': 3, 'max': 50}
            }
            
            removed_count = 0
            
            for hospital_code, thresholds in anomaly_thresholds.items():
                # Find anomalous records
                anomalous_records = HospitalCapacity.query.filter(
                    HospitalCapacity.hospital_code == hospital_code,
                    HospitalCapacity.timestamp >= cutoff_time,
                    db.or_(
                        HospitalCapacity.total_patients < thresholds['min'],
                        HospitalCapacity.total_patients > thresholds['max']
                    )
                ).all()
                
                for record in anomalous_records:
                    logging.info(f"Removing anomalous data: {hospital_code} had {record.total_patients} patients at {record.timestamp}")
                    db.session.delete(record)
                    removed_count += 1
            
            # Also detect sudden jumps/drops in recent data
            for hospital_code in ['RUH', 'SPH', 'SCH', 'JPCH']:
                recent_records = HospitalCapacity.query.filter(
                    HospitalCapacity.hospital_code == hospital_code,
                    HospitalCapacity.timestamp >= cutoff_time
                ).order_by(HospitalCapacity.timestamp.desc()).limit(10).all()
                
                if len(recent_records) >= 2:
                    for i in range(len(recent_records) - 1):
                        current = recent_records[i].total_patients
                        previous = recent_records[i + 1].total_patients
                        
                        if previous > 0:  # Avoid division by zero
                            change_percent = abs(current - previous) / previous
                            
                            # Remove records with >60% sudden changes
                            if change_percent > 0.6:
                                logging.info(f"Removing sudden change anomaly: {hospital_code} jumped from {previous} to {current} patients ({change_percent:.1%} change)")
                                db.session.delete(recent_records[i])
                                removed_count += 1
            
            if removed_count > 0:
                db.session.commit()
                logging.info(f"AI cleanup removed {removed_count} anomalous data points")
            
        except Exception as e:
            logging.error(f"Error cleaning anomalous data: {e}")
            db.session.rollback()
    
    def _save_hospital_data(self, hospital_data):
        """Save hospital data to database"""
        saved_count = 0
        
        for data in hospital_data:
            try:
                hospital_record = HospitalCapacity(
                    hospital_code=data['hospital_code'],
                    hospital_name=data['hospital_name'],
                    total_patients=data['total_patients']
                )
                db.session.add(hospital_record)
                saved_count += 1
                
            except IntegrityError as e:
                logging.warning(f"Database constraint violation for {data['hospital_code']}: {e}")
                db.session.rollback()
                continue
            except Exception as e:
                logging.error(f"Error saving data for {data['hospital_code']}: {e}")
                db.session.rollback()
                continue
        
        try:
            db.session.commit()
            logging.info(f"Hospital data saved to database for {saved_count} hospitals")
            return saved_count
        except Exception as e:
            logging.error(f"Error committing to database: {e}")
            db.session.rollback()
            return 0
    
    def _log_scraping_result(self, status, message):
        """Log the scraping result"""
        try:
            log_entry = ScrapingLog(
                status=status,
                message=message,
                pdf_url=self.pdf_url
            )
            db.session.add(log_entry)
            db.session.commit()
        except Exception as e:
            logging.error(f"Error logging scraping result: {e}")
            db.session.rollback()

def run_scraping():
    """Function to run scraping - called by scheduler"""
    from app import app
    
    with app.app_context():
        scraper = HospitalDataScraper()
        return scraper.scrape_hospital_data()