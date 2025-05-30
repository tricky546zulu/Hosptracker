import os
import re
import logging
import requests
import pdfplumber
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from app import db
from models import HospitalCapacity, ScrapingLog

# Set up logging
logging.basicConfig(level=logging.DEBUG)

class HospitalDataScraper:
    def __init__(self):
        self.pdf_url = "https://www.ehealthsask.ca/reporting/Documents/SaskatoonHospitalBedCapacity.pdf"
        
    def scrape_hospital_data(self):
        """Main method to scrape hospital data from PDF"""
        try:
            logging.info("Starting hospital data scraping")
            
            # Download PDF
            pdf_content = self._download_pdf()
            if not pdf_content:
                self._log_scraping_result("error", "Failed to download PDF")
                return False
            
            # Parse PDF and extract data
            hospital_data = self._parse_pdf(pdf_content)
            if not hospital_data:
                self._log_scraping_result("error", "No hospital data found in PDF")
                return False
            
            # Save to database
            saved_count = self._save_hospital_data(hospital_data)
            
            if saved_count > 0:
                self._log_scraping_result("success", f"Successfully scraped data for {saved_count} hospitals")
                logging.info(f"Successfully scraped hospital data for {len(hospital_data)} hospitals")
                return True
            else:
                self._log_scraping_result("error", "No new data was saved")
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
    
    def _parse_pdf(self, pdf_content):
        """Parse the PDF and extract hospital capacity data"""
        try:
            hospital_data = []
            
            import io
            with pdfplumber.open(io.BytesIO(pdf_content)) as pdf:
                all_text = ""
                for page in pdf.pages:
                    all_text += page.extract_text() + "\n"
            
            # Split into lines for processing
            lines = all_text.split('\n')
            
            # Find Emergency Department section
            ed_section_found = False
            for i, line in enumerate(lines):
                # Look for the Emergency Department table header or data rows
                if ('Site Admitted Active Consults Total' in line or 
                    'Emergency Department' in line or
                    (any(code in line for code in ['RUH', 'SPH', 'SCH', 'JPCH']) and 
                     any(num.isdigit() for num in line.split()))):
                    
                    logging.info(f"Found Emergency Department section at line {i}: {line}")
                    
                    # Parse Emergency Department data from the complete table section
                    # Include more context to capture all hospital rows
                    ed_data = self._parse_emergency_department_data(lines[max(0, i-2):i+20])
                    if ed_data:
                        hospital_data.extend(ed_data)
                        ed_section_found = True
                        break
            
            if not ed_section_found:
                logging.warning("Emergency Department section not found in PDF - no data will be saved")
                return None
            
            return hospital_data
            
        except Exception as e:
            logging.error(f"Error parsing PDF: {e}")
            return None
    
    def _parse_emergency_department_data(self, text):
        """Parse Emergency Department data from PDF text"""
        hospital_data = []
        
        # Process all lines to find hospital data
        for i, line in enumerate(text):
            line = line.strip()
            
            # Check each hospital code
            for hospital_code in ['RUH', 'SPH', 'SCH', 'JPCH']:
                if hospital_code in line and any(c.isdigit() for c in line):
                    # Skip specialty department lines - only capture main Emergency Department entries
                    # For lines that contain both main ED data and specialty info, extract the main ED total
                    if 'CARDIOSCIENCES' in line.upper() or 'MEDICINE ED' in line.upper():
                        logging.info(f"Skipping specialty department line: {line}")
                        continue
                    
                    # For hospital lines with specialty info at the end, extract main ED data correctly
                    # Format: "HOSPITAL Admitted Active Consults Total SpecialtyName ED Number"
                    if any(specialty in line.upper() for specialty in ['ADDICTION SERVICES', 'NEUROSCIENCES ED', 'ONCOLOGY ED', 'SURGERY ED']):
                        numbers = re.findall(r'\b\d+\b', line)
                        if len(numbers) >= 4:
                            # The 4th number is always the Total for main Emergency Department
                            # regardless of specialty numbers that follow
                            total_patients = int(numbers[3])
                            
                            hospital_info = {
                                'hospital_code': hospital_code,
                                'hospital_name': self._get_full_hospital_name(hospital_code),
                                'total_patients': total_patients
                            }
                            
                            logging.info(f"Successfully extracted main ED data for {hospital_code}: {hospital_info}")
                            hospital_data.append(hospital_info)
                            break
                        continue
                    
                    # Extract numbers from this line
                    numbers = re.findall(r'\b\d+\b', line)
                    if numbers:
                        numbers = [int(n) for n in numbers]
                        logging.info(f"{hospital_code}: Found numbers {numbers} in line: {line}")
                        
                        # Use the last number as Emergency Department Total
                        total_patients = numbers[-1]
                        
                        # Apply validation for RUH
                        if hospital_code == 'RUH' and (total_patients < 20 or total_patients > 200):
                            logging.warning(f"RUH: Patient count {total_patients} outside reasonable range (20-200), skipping")
                            continue
                        
                        hospital_info = {
                            'hospital_code': hospital_code,
                            'hospital_name': self._get_full_hospital_name(hospital_code),
                            'total_patients': total_patients
                        }
                        
                        logging.info(f"Successfully extracted data for {hospital_code}: {hospital_info}")
                        hospital_data.append(hospital_info)
                        break  # Found this hospital, move to next line
        
        return hospital_data
    
    def _extract_numbers_from_line_context(self, lines, line_index, hospital_code):
        """Extract Total patients from Emergency Department table"""
        
        for i, line in enumerate(lines):
            if hospital_code in line:
                # Skip specialty department lines (like "RUH Cardiosciences ED")
                # Focus on main Emergency Department entries
                if any(specialty in line.upper() for specialty in ['CARDIOSCIENCES', 'NEUROSCIENCES', 'ADDICTION']):
                    logging.info(f"Skipping specialty department line for {hospital_code}: {line}")
                    continue
                
                # Extract all numbers from this line
                numbers = re.findall(r'\b\d+\b', line)
                
                if numbers:
                    # Convert to integers
                    numbers = [int(n) for n in numbers]
                    logging.info(f"{hospital_code}: Found numbers {numbers} in line: {line}")
                    
                    if hospital_code == 'RUH':
                        # For RUH, use the last number as Emergency Department Total
                        total_patients = numbers[-1] if numbers else None
                        
                        # Validation - RUH Emergency Department should have reasonable volume
                        if total_patients is None or total_patients < 20 or total_patients > 200:
                            logging.warning(f"RUH: Patient count {total_patients} outside reasonable range (20-200), skipping")
                            return None
                        
                        # Additional safety check - log successful extraction for monitoring
                        logging.info(f"RUH: Successfully extracted valid patient count: {total_patients}")
                            
                        return {
                            'hospital_code': hospital_code,
                            'hospital_name': self._get_full_hospital_name(hospital_code),
                            'total_patients': total_patients
                        }
                
                    elif hospital_code == 'SCH':
                        # For SCH, sum Active + Consults for true Emergency Department total
                        # PDF format: Admitted | Active | Consults | Total
                        if len(numbers) >= 4:
                            active = int(numbers[-3])  # Active patients
                            consults = int(numbers[-2])  # Consults
                            total_patients = active + consults  # True ED total
                        else:
                            total_patients = int(numbers[-1])
                        return {
                            'hospital_code': hospital_code,
                            'hospital_name': self._get_full_hospital_name(hospital_code),
                            'total_patients': total_patients
                        }
                    elif hospital_code == 'JPCH':
                        # For JPCH, use the last number as Total
                        total_patients = int(numbers[-1])
                        return {
                            'hospital_code': hospital_code,
                            'hospital_name': self._get_full_hospital_name(hospital_code),
                            'total_patients': total_patients
                        }
                    else:
                        # Default case for any other hospital
                        total_patients = int(numbers[-1])
                        return {
                            'hospital_code': hospital_code,
                            'hospital_name': self._get_full_hospital_name(hospital_code),
                            'total_patients': total_patients
                        }
            
            # No valid data found
            return None
    
    def _get_full_hospital_name(self, code):
        """Get full hospital name from code"""
        names = {
            'RUH': 'Royal University Hospital',
            'SPH': 'St. Paul\'s Hospital',
            'SCH': 'Saskatoon City Hospital',
            'JPCH': 'Jim Pattison Children\'s Hospital'
        }
        return names.get(code, code)
    

    
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
        except Exception as e:
            logging.error(f"Error committing to database: {e}")
            db.session.rollback()
            saved_count = 0
        
        return saved_count
    
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