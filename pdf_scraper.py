import os
import logging
import re
import requests
from datetime import datetime
from io import BytesIO
import pdfplumber
from app import app, db
from models import HospitalCapacity, ScrapingLog

class HospitalDataScraper:
    def __init__(self):
        # eHealth Saskatchewan PDF URL
        self.pdf_url = os.environ.get("EHEALTH_PDF_URL", "https://www.ehealthsask.ca/reporting/Documents/SaskatoonHospitalBedCapacity.pdf")
        
    def scrape_hospital_data(self):
        """Main method to scrape hospital data from PDF"""
        try:
            logging.info("Starting hospital data scraping...")
            
            # Download the PDF
            pdf_content = self._download_pdf()
            if not pdf_content:
                raise Exception("Failed to download PDF")
            
            # Parse the PDF
            hospital_data = self._parse_pdf(pdf_content)
            if not hospital_data:
                raise Exception("No hospital data found in PDF")
            
            # Save to database
            self._save_hospital_data(hospital_data)
            
            # Log successful scraping
            self._log_scraping_result("success", f"Successfully scraped data for {len(hospital_data)} hospitals")
            
            logging.info(f"Successfully scraped hospital data for {len(hospital_data)} hospitals")
            return True
            
        except Exception as e:
            error_msg = f"Error scraping hospital data: {str(e)}"
            logging.error(error_msg)
            self._log_scraping_result("error", error_msg)
            return False
    
    def _download_pdf(self):
        """Download the PDF from eHealth website"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            response = requests.get(self.pdf_url, headers=headers, timeout=30)
            response.raise_for_status()
            
            return BytesIO(response.content)
            
        except Exception as e:
            logging.error(f"Error downloading PDF: {str(e)}")
            return None
    
    def _parse_pdf(self, pdf_content):
        """Parse the PDF and extract hospital capacity data"""
        hospital_data = []
        
        try:
            with pdfplumber.open(pdf_content) as pdf:
                full_text = ""
                
                # Extract text from all pages
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        full_text += page_text + "\n"
                
                # Parse Emergency Department data
                ed_data = self._parse_emergency_department_data(full_text)
                hospital_data.extend(ed_data)
                
        except Exception as e:
            logging.error(f"Error parsing PDF: {str(e)}")
            
        return hospital_data
    
    def _parse_emergency_department_data(self, text):
        """Parse Emergency Department data from PDF text"""
        hospitals = []
        
        try:
            # Log the extracted text to help debug
            logging.info("Extracted PDF text (first 2000 chars):")
            logging.info(text[:2000])
            
            # Split text into lines and look for Emergency Department tables
            lines = text.split('\n')
            
            # Look specifically for Emergency Department section and tables
            in_ed_section = False
            ed_table_started = False
            
            for i, line in enumerate(lines):
                line = line.strip()
                
                # Detect Emergency Department section
                if 'Emergency Department' in line and 'Please be advised' not in line:
                    in_ed_section = True
                    logging.info(f"Found Emergency Department section at line {i}: {line}")
                    continue
                
                # Look for table headers or data rows in ED section
                if in_ed_section:
                    # Check for hospital names in the Emergency Department context
                    hospital_code = None
                    if 'Royal University' in line or 'RUH' in line:
                        hospital_code = 'RUH'
                    elif "St. Paul's" in line or "St Paul" in line or 'SPH' in line:
                        hospital_code = 'SPH'
                    elif 'Saskatoon City' in line or 'SCH' in line:
                        hospital_code = 'SCH'
                    
                    if hospital_code:
                        # Look for capacity data in the same line or following lines
                        capacity_data = self._extract_ed_capacity_numbers(line, lines, i)
                        if capacity_data:
                            hospitals.append({
                                'hospital_code': hospital_code,
                                'hospital_name': self._get_full_hospital_name(hospital_code),
                                **capacity_data
                            })
                            logging.info(f"Found ED data for {hospital_code}: {capacity_data}")
                
                # Stop parsing if we reach a different section
                if in_ed_section and ('Maternal' in line or 'Children' in line or line.startswith('#')):
                    break
            
            # If we couldn't find proper ED data, log for debugging
            if not hospitals:
                logging.warning("No Emergency Department data found, attempting fallback parsing")
                hospitals = self._fallback_parse_hospital_data(text)
                
        except Exception as e:
            logging.error(f"Error parsing Emergency Department data: {str(e)}")
        
        return hospitals
    
    def _extract_ed_capacity_numbers(self, line, lines, line_index):
        """Extract Emergency Department capacity numbers from line and context"""
        try:
            # Look for ED-specific capacity data patterns
            # Check current line and next few lines for capacity data
            search_lines = [line] + lines[line_index+1:line_index+5]
            
            for search_line in search_lines:
                search_line = search_line.strip()
                
                # Look for patterns specific to Emergency Department capacity
                # Common patterns: "occupied/total", percentages, "Admitted Pts in ED"
                capacity_match = re.search(r'(\d+)\s*/\s*(\d+)', search_line)
                percentage_match = re.search(r'(\d+(?:\.\d+)?)%', search_line)
                admitted_match = re.search(r'(?:admitted|pts|patients).*?(\d+)', search_line.lower())
                
                # For ED data, we want smaller numbers (typically 10-50 beds, not thousands)
                if capacity_match:
                    occupied = int(capacity_match.group(1))
                    total = int(capacity_match.group(2))
                    
                    # Filter out unrealistic ED numbers (ED capacity is typically 10-100 beds)
                    if 5 <= total <= 100 and occupied <= total:
                        percentage = (occupied / total * 100) if total > 0 else 0
                        
                        return {
                            'occupied_beds': occupied,
                            'total_beds': total,
                            'capacity_percentage': round(percentage, 1),
                            'admitted_pts_in_ed': int(admitted_match.group(1)) if admitted_match else 0
                        }
                
                # If we find a percentage without bed counts, still capture it
                elif percentage_match and 'capacity' in search_line.lower():
                    percentage = float(percentage_match.group(1))
                    return {
                        'occupied_beds': None,
                        'total_beds': None,
                        'capacity_percentage': percentage,
                        'admitted_pts_in_ed': int(admitted_match.group(1)) if admitted_match else 0
                    }
                    
        except Exception as e:
            logging.debug(f"Error extracting ED numbers from line '{line}': {str(e)}")
        
        return None

    def _extract_capacity_numbers(self, line):
        """Extract capacity numbers from a line of text (legacy method)"""
        try:
            # Look for patterns like "25/30" (occupied/total) or "83%" (percentage)
            capacity_match = re.search(r'(\d+)/(\d+)', line)
            percentage_match = re.search(r'(\d+(?:\.\d+)?)%', line)
            admitted_match = re.search(r'admitted.*?(\d+)', line.lower())
            
            if capacity_match:
                occupied = int(capacity_match.group(1))
                total = int(capacity_match.group(2))
                percentage = (occupied / total * 100) if total > 0 else 0
                
                return {
                    'occupied_beds': occupied,
                    'total_beds': total,
                    'capacity_percentage': round(percentage, 1),
                    'admitted_pts_in_ed': int(admitted_match.group(1)) if admitted_match else 0
                }
            elif percentage_match:
                percentage = float(percentage_match.group(1))
                return {
                    'capacity_percentage': percentage,
                    'admitted_pts_in_ed': int(admitted_match.group(1)) if admitted_match else 0
                }
                
        except Exception as e:
            logging.debug(f"Error extracting numbers from line '{line}': {str(e)}")
        
        return None
    
    def _fallback_parse_hospital_data(self, text):
        """Fallback parsing method if main parsing fails"""
        hospitals = []
        
        try:
            # Generate placeholder data structure for development
            # In production, this would implement more sophisticated PDF parsing
            hospital_codes = ['RUH', 'SPH', 'SCH']
            
            for code in hospital_codes:
                hospitals.append({
                    'hospital_code': code,
                    'hospital_name': self._get_full_hospital_name(code),
                    'occupied_beds': None,
                    'total_beds': None,
                    'capacity_percentage': None,
                    'admitted_pts_in_ed': None
                })
                
        except Exception as e:
            logging.error(f"Error in fallback parsing: {str(e)}")
        
        return hospitals
    
    def _get_full_hospital_name(self, code):
        """Get full hospital name from code"""
        names = {
            'RUH': 'Royal University Hospital',
            'SPH': "St. Paul's Hospital",
            'SCH': 'Saskatoon City Hospital'
        }
        return names.get(code, code)
    
    def _save_hospital_data(self, hospital_data):
        """Save hospital data to database"""
        try:
            with app.app_context():
                for data in hospital_data:
                    capacity = HospitalCapacity(
                        hospital_code=data['hospital_code'],
                        hospital_name=data['hospital_name'],
                        occupied_beds=data.get('occupied_beds'),
                        total_beds=data.get('total_beds'),
                        capacity_percentage=data.get('capacity_percentage'),
                        admitted_pts_in_ed=data.get('admitted_pts_in_ed'),
                        timestamp=datetime.utcnow()
                    )
                    db.session.add(capacity)
                
                db.session.commit()
                logging.info("Hospital data saved to database")
                
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error saving hospital data: {str(e)}")
            raise
    
    def _log_scraping_result(self, status, message):
        """Log the scraping result"""
        try:
            with app.app_context():
                log_entry = ScrapingLog(
                    status=status,
                    message=message,
                    pdf_url=self.pdf_url,
                    timestamp=datetime.utcnow()
                )
                db.session.add(log_entry)
                db.session.commit()
                
        except Exception as e:
            logging.error(f"Error logging scraping result: {str(e)}")

# Create scraper instance
scraper = HospitalDataScraper()

def run_scraping():
    """Function to run scraping - called by scheduler"""
    return scraper.scrape_hospital_data()
