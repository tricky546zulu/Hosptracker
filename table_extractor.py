import pandas as pd
import camelot
import tabula
import requests
import logging
from io import BytesIO

class PrecisionTableExtractor:
    def __init__(self):
        self.pdf_url = "https://www.ehealthsask.ca/reporting/Documents/SaskatoonHospitalBedCapacity.pdf"
        
    def extract_ed_tables(self):
        """Extract Emergency Department tables with precise control"""
        try:
            # Download PDF
            response = requests.get(self.pdf_url, timeout=30)
            response.raise_for_status()
            
            # Save temporarily for processing
            with open('/tmp/hospital_capacity.pdf', 'wb') as f:
                f.write(response.content)
            
            # Method 1: Use Camelot for precise table extraction
            print("=== CAMELOT EXTRACTION ===")
            camelot_tables = self._extract_with_camelot('/tmp/hospital_capacity.pdf')
            
            # Method 2: Use Tabula for comparison
            print("\n=== TABULA EXTRACTION ===")
            tabula_tables = self._extract_with_tabula('/tmp/hospital_capacity.pdf')
            
            return {
                'camelot_tables': camelot_tables,
                'tabula_tables': tabula_tables
            }
            
        except Exception as e:
            logging.error(f"Error extracting tables: {e}")
            return None
    
    def _extract_with_camelot(self, pdf_path):
        """Extract tables using Camelot for precise control"""
        try:
            # Extract all tables from PDF
            tables = camelot.read_pdf(pdf_path, pages='all', flavor='lattice')
            
            results = []
            for i, table in enumerate(tables):
                print(f"Table {i+1} (Page {table.page}):")
                print(f"Shape: {table.df.shape}")
                print(f"Accuracy: {table.accuracy:.2f}")
                print("Preview:")
                print(table.df.head())
                print("-" * 50)
                
                # Look for Emergency Department tables
                df = table.df
                if self._is_ed_table(df):
                    ed_data = self._extract_ed_data_from_table(df, method="camelot")
                    if ed_data:
                        results.append({
                            'table_index': i+1,
                            'page': table.page,
                            'accuracy': table.accuracy,
                            'ed_data': ed_data,
                            'raw_table': df.to_dict()
                        })
            
            return results
            
        except Exception as e:
            print(f"Camelot extraction error: {e}")
            return []
    
    def _extract_with_tabula(self, pdf_path):
        """Extract tables using Tabula"""
        try:
            # Extract all tables
            tables = tabula.read_pdf(pdf_path, pages='all', multiple_tables=True)
            
            results = []
            for i, df in enumerate(tables):
                print(f"Tabula Table {i+1}:")
                print(f"Shape: {df.shape}")
                print("Preview:")
                print(df.head())
                print("-" * 50)
                
                if self._is_ed_table(df):
                    ed_data = self._extract_ed_data_from_table(df, method="tabula")
                    if ed_data:
                        results.append({
                            'table_index': i+1,
                            'ed_data': ed_data,
                            'raw_table': df.to_dict()
                        })
            
            return results
            
        except Exception as e:
            print(f"Tabula extraction error: {e}")
            return []
    
    def _is_ed_table(self, df):
        """Check if this table contains Emergency Department data"""
        # Convert to string to search
        table_str = df.to_string().upper()
        
        # Look for Emergency Department indicators
        ed_indicators = ['EMERGENCY DEPARTMENT', 'SITE', 'ADMITTED', 'ACTIVE', 'CONSULTS', 'TOTAL']
        hospital_codes = ['RUH', 'SPH', 'SCH', 'JPCH']
        
        has_ed_indicators = any(indicator in table_str for indicator in ed_indicators)
        has_hospitals = any(code in table_str for code in hospital_codes)
        
        return has_ed_indicators and has_hospitals
    
    def _extract_ed_data_from_table(self, df, method=""):
        """Extract specific hospital data from Emergency Department table"""
        try:
            hospital_data = []
            
            # Convert DataFrame to string for easier searching
            for idx, row in df.iterrows():
                row_str = ' '.join(str(cell) for cell in row.values if pd.notna(cell))
                
                # Check for each hospital
                for hospital_code in ['RUH', 'SPH', 'SCH', 'JPCH']:
                    if hospital_code in row_str:
                        print(f"\n{method} - Found {hospital_code} row:")
                        print(f"Row {idx}: {row_str}")
                        
                        # Extract numbers from the row
                        numbers = []
                        for cell in row.values:
                            try:
                                if pd.notna(cell) and str(cell).strip().isdigit():
                                    numbers.append(int(cell))
                            except:
                                continue
                        
                        print(f"Numbers found: {numbers}")
                        
                        # Let you choose which number to use for each hospital
                        if numbers:
                            hospital_data.append({
                                'hospital_code': hospital_code,
                                'hospital_name': self._get_full_hospital_name(hospital_code),
                                'row_data': row.values.tolist(),
                                'numbers_found': numbers,
                                'suggested_total': numbers[-1] if numbers else 0,  # Default to last number
                                'row_text': row_str
                            })
            
            return hospital_data
            
        except Exception as e:
            print(f"Error extracting ED data: {e}")
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
    
    def extract_and_display_options(self):
        """Extract tables and display options for user selection"""
        results = self.extract_ed_tables()
        
        if not results:
            print("No tables extracted successfully")
            return
        
        print("\n" + "="*60)
        print("EXTRACTION COMPLETE - SELECT YOUR DATA")
        print("="*60)
        
        # Display Camelot results
        if results['camelot_tables']:
            print("\nCAMELOT RESULTS:")
            for table in results['camelot_tables']:
                print(f"\nTable {table['table_index']} (Page {table['page']}, Accuracy: {table['accuracy']:.2f}):")
                for hospital in table['ed_data']:
                    print(f"\n{hospital['hospital_code']} ({hospital['hospital_name']}):")
                    print(f"  Row text: {hospital['row_text']}")
                    print(f"  Numbers: {hospital['numbers_found']}")
                    print(f"  Suggested total: {hospital['suggested_total']}")
        
        # Display Tabula results
        if results['tabula_tables']:
            print("\nTABULA RESULTS:")
            for table in results['tabula_tables']:
                print(f"\nTable {table['table_index']}:")
                for hospital in table['ed_data']:
                    print(f"\n{hospital['hospital_code']} ({hospital['hospital_name']}):")
                    print(f"  Row text: {hospital['row_text']}")
                    print(f"  Numbers: {hospital['numbers_found']}")
                    print(f"  Suggested total: {hospital['suggested_total']}")
        
        return results

if __name__ == "__main__":
    extractor = PrecisionTableExtractor()
    extractor.extract_and_display_options()