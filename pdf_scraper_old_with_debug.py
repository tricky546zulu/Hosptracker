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
        
        # Configuration for precise table extraction - Table 5 coordinates
        self.extraction_config = {
            'target_table_index': 4,  # Table 5 (0-indexed)
            'hospital_coordinates': {
                'JPCH': {'row': 1, 'column': 4},  # Row 1, Column 4 = Total column
                'RUH': {'row': 2, 'column': 4},   # Row 2, Column 4 = Total column
                'SPH': {'row': 3, 'column': 4},   # Row 3, Column 4 = Total column
                'SCH': {'row': 4, 'column': 4}    # Row 4, Column 4 = Total column
            },
            'min_accuracy': 90.0
        }
        
    def scrape_hospital_data(self):
        """Main method to scrape hospital data using table extraction"""
        try:
            logging.info("Starting hospital data scraping with table extraction")
            
            # Download PDF
            pdf_content = self._download_pdf()
            if not pdf_content:
                self._log_scraping_result("error", "Failed to download PDF")
                return False
            
            # Parse PDF using table extraction
            hospital_data = self._extract_tables(pdf_content)
            if not hospital_data:
                self._log_scraping_result("error", "No hospital data found in PDF")
                return False
            
            # AI-powered data validation
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
    
    def _extract_tables(self, pdf_content):
        """Extract Emergency Department data using precise table coordinates"""
        try:
            # Save PDF temporarily
            temp_pdf_path = '/tmp/hospital_capacity.pdf'
            with open(temp_pdf_path, 'wb') as f:
                f.write(pdf_content)
            
            # Extract all tables with minimal logging
            import warnings
            warnings.filterwarnings('ignore')
            tables = camelot.read_pdf(temp_pdf_path, pages='all', flavor='lattice')
            
            # Get the target table (Table 5)
            target_index = self.extraction_config['target_table_index']
            
            if target_index >= len(tables):
                logging.error(f"Target table index {target_index} not found. Only {len(tables)} tables available.")
                return []
            
            target_table = tables[target_index]
            df = target_table.df
            
            logging.info(f"Using Table {target_index + 1} with {target_table.accuracy:.1f}% accuracy")
            
            # Extract data using precise coordinates
            hospital_data = []
            coordinates = self.extraction_config['hospital_coordinates']
            
            for hospital_code, coords in coordinates.items():
                try:
                    row_idx = coords['row']
                    col_idx = coords['column']
                    
                    if row_idx < len(df) and col_idx < len(df.columns):
                        value = df.iloc[row_idx, col_idx]
                        patient_count = int(str(value).strip())
                        
                        hospital_info = {
                            'hospital_code': hospital_code,
                            'hospital_name': self._get_full_hospital_name(hospital_code),
                            'total_patients': patient_count
                        }
                        
                        hospital_data.append(hospital_info)
                        logging.info(f"Extracted {hospital_code}: {patient_count} patients from row {row_idx}, col {col_idx}")
                        
                    else:
                        logging.error(f"Invalid coordinates for {hospital_code}: row {row_idx}, col {col_idx}")
                        
                except Exception as e:
                    logging.error(f"Error extracting {hospital_code}: {e}")
            
            return hospital_data
            
        except Exception as e:
            logging.error(f"Table extraction error: {e}")
            return []
    
    def _is_main_ed_table(self, df):
        """Check if this is the main Emergency Department table"""
        try:
            table_str = df.to_string().upper()
            
            # Check for hospital codes
            hospital_codes = self.extraction_config['table_filters']['hospital_codes']
            has_hospitals = any(code in table_str for code in hospital_codes)
            
            # Exclude specialty department tables
            specialty_indicators = ['CARDIOSCIENCES', 'MEDICINE ED', 'ONCOLOGY', 'NEUROSCIENCES']
            is_specialty_table = any(specialty in table_str for specialty in specialty_indicators)
            
            # Look for main ED structure
            main_ed_indicators = ['ADMITTED', 'ACTIVE', 'CONSULTS', 'TOTAL']
            has_main_ed_structure = all(indicator in table_str for indicator in main_ed_indicators)
            
            return has_hospitals and has_main_ed_structure and not is_specialty_table
            
        except Exception as e:
            logging.error(f"Error checking ED table: {e}")
            return False
    
    def _extract_ed_data_from_table(self, df):
        """Extract hospital data from Emergency Department table"""
        try:
            hospital_data = []
            
            for idx, row in df.iterrows():
                row_str = ' '.join(str(cell) for cell in row.values if pd.notna(cell))
                
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
                        
                        break
            
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
            
            # Apply consistency rules
            validated_data = []
            
            for data in hospital_data:
                hospital_code = data['hospital_code']
                patient_count = data['total_patients']
                
                # Hospital-specific validation ranges
                expected_ranges = {
                    'RUH': (20, 150),
                    'SPH': (2, 25),
                    'SCH': (1, 70),
                    'JPCH': (5, 40)
                }
                
                min_expected, max_expected = expected_ranges.get(hospital_code, (5, 200))
                
                if min_expected <= patient_count <= max_expected:
                    validated_data.append(data)
                    logging.info(f"AI validation passed for {hospital_code}: {patient_count} patients")
                else:
                    logging.warning(f"AI validation failed for {hospital_code}: {patient_count} patients outside expected range ({min_expected}-{max_expected})")
            
            return validated_data
            
        except Exception as e:
            logging.error(f"Error in AI validation: {e}")
            return hospital_data
    
    def _clean_existing_anomalous_data(self):
        """Clean up existing anomalous data in the database"""
        try:
            from app import db
            from models import HospitalCapacity
            from datetime import datetime, timedelta
            import pytz
            
            utc_now = datetime.utcnow()
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
            
            # Detect sudden jumps/drops
            for hospital_code in ['RUH', 'SPH', 'SCH', 'JPCH']:
                recent_records = HospitalCapacity.query.filter(
                    HospitalCapacity.hospital_code == hospital_code,
                    HospitalCapacity.timestamp >= cutoff_time
                ).order_by(HospitalCapacity.timestamp.desc()).limit(10).all()
                
                if len(recent_records) >= 2:
                    for i in range(len(recent_records) - 1):
                        current = recent_records[i].total_patients
                        previous = recent_records[i + 1].total_patients
                        
                        if previous > 0:
                            change_percent = abs(current - previous) / previous
                            
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