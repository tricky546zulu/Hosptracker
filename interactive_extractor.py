import requests
import camelot
import pandas as pd
import json

class InteractiveTableExtractor:
    def __init__(self):
        self.pdf_url = "https://www.ehealthsask.ca/reporting/Documents/SaskatoonHospitalBedCapacity.pdf"
        
    def analyze_pdf_tables(self):
        """Download PDF and show all tables for user selection"""
        try:
            print("Downloading PDF...")
            response = requests.get(self.pdf_url, timeout=30)
            response.raise_for_status()
            
            # Save temporarily
            with open('/tmp/hospital_capacity.pdf', 'wb') as f:
                f.write(response.content)
            
            # Extract all tables
            print("Extracting tables...")
            tables = camelot.read_pdf('/tmp/hospital_capacity.pdf', pages='all', flavor='lattice')
            
            print(f"\nFound {len(tables)} tables in PDF")
            print("="*60)
            
            # Show each table
            for i, table in enumerate(tables):
                print(f"\nTABLE {i+1} (Page {table.page}, Accuracy: {table.accuracy:.1f}%)")
                print("-" * 40)
                
                df = table.df
                print(f"Shape: {df.shape[0]} rows x {df.shape[1]} columns")
                
                # Show table content
                print("\nTable Preview:")
                for row_idx, row in df.iterrows():
                    row_data = [str(cell) if pd.notna(cell) else "" for cell in row.values]
                    print(f"Row {row_idx}: {row_data}")
                    
                    # Stop after 10 rows to keep output manageable
                    if row_idx >= 9:
                        if len(df) > 10:
                            print(f"... ({len(df) - 10} more rows)")
                        break
                
                print("-" * 40)
            
            return tables
            
        except Exception as e:
            print(f"Error analyzing PDF: {e}")
            return None
    
    def configure_extraction(self, tables):
        """Let user configure which table and cells to extract from"""
        print("\n" + "="*60)
        print("EXTRACTION CONFIGURATION")
        print("="*60)
        
        # Let user select table
        table_num = input(f"\nWhich table contains Emergency Department data? (1-{len(tables)}): ")
        try:
            table_index = int(table_num) - 1
            if table_index < 0 or table_index >= len(tables):
                print("Invalid table number")
                return None
            
            selected_table = tables[table_index]
            df = selected_table.df
            
            print(f"\nSelected Table {table_num}:")
            print(f"Shape: {df.shape[0]} rows x {df.shape[1]} columns")
            
            # Show table with row/column indices
            print("\nTable with coordinates:")
            print("Columns:", end="")
            for col_idx in range(df.shape[1]):
                print(f"    Col{col_idx}", end="")
            print()
            
            for row_idx, row in df.iterrows():
                print(f"Row{row_idx:2d}:", end="")
                for col_idx, cell in enumerate(row.values):
                    cell_str = str(cell) if pd.notna(cell) else ""
                    print(f"{cell_str:8s}", end="")
                print()
            
            # Configure hospital extraction
            config = {}
            hospitals = ['RUH', 'SPH', 'SCH', 'JPCH']
            
            for hospital in hospitals:
                print(f"\nFor {hospital}:")
                row = input(f"  Which row contains {hospital} data? (row number): ")
                col = input(f"  Which column contains the patient count? (column number): ")
                
                try:
                    row_idx = int(row)
                    col_idx = int(col)
                    
                    if 0 <= row_idx < df.shape[0] and 0 <= col_idx < df.shape[1]:
                        value = df.iloc[row_idx, col_idx]
                        print(f"  Selected value: {value}")
                        
                        config[hospital] = {
                            'row': row_idx,
                            'column': col_idx,
                            'value': value
                        }
                    else:
                        print(f"  Invalid coordinates for {hospital}")
                        
                except ValueError:
                    print(f"  Invalid input for {hospital}")
            
            # Save configuration
            with open('extraction_config.json', 'w') as f:
                json.dump({
                    'table_index': table_index,
                    'hospital_mapping': config
                }, f, indent=2)
            
            print(f"\nConfiguration saved to extraction_config.json")
            print("Configuration summary:")
            for hospital, mapping in config.items():
                print(f"  {hospital}: Row {mapping['row']}, Column {mapping['column']} = {mapping['value']}")
            
            return config
            
        except ValueError:
            print("Invalid table number")
            return None
    
    def test_extraction(self):
        """Test the configured extraction"""
        try:
            with open('extraction_config.json', 'r') as f:
                config = json.load(f)
            
            print("\nTesting extraction with saved configuration...")
            
            # Download and extract
            response = requests.get(self.pdf_url, timeout=30)
            response.raise_for_status()
            
            with open('/tmp/hospital_capacity.pdf', 'wb') as f:
                f.write(response.content)
            
            tables = camelot.read_pdf('/tmp/hospital_capacity.pdf', pages='all', flavor='lattice')
            selected_table = tables[config['table_index']]
            df = selected_table.df
            
            print(f"Using Table {config['table_index'] + 1}")
            print("Extracted values:")
            
            extracted_data = []
            for hospital, mapping in config['hospital_mapping'].items():
                row_idx = mapping['row']
                col_idx = mapping['column']
                value = df.iloc[row_idx, col_idx]
                
                try:
                    patient_count = int(str(value).strip())
                    extracted_data.append({
                        'hospital_code': hospital,
                        'total_patients': patient_count
                    })
                    print(f"  {hospital}: {patient_count} patients")
                except:
                    print(f"  {hospital}: Could not convert '{value}' to number")
            
            return extracted_data
            
        except FileNotFoundError:
            print("No configuration file found. Run configuration first.")
            return None
        except Exception as e:
            print(f"Error testing extraction: {e}")
            return None

def main():
    extractor = InteractiveTableExtractor()
    
    print("Interactive PDF Table Extractor")
    print("This tool lets you select exactly which table cells to extract data from.")
    
    # Analyze PDF and show tables
    tables = extractor.analyze_pdf_tables()
    if not tables:
        return
    
    # Configure extraction
    config = extractor.configure_extraction(tables)
    if not config:
        return
    
    # Test extraction
    result = extractor.test_extraction()
    if result:
        print("\nExtraction test successful!")
        print("You can now use this configuration in the main scraper.")

if __name__ == "__main__":
    main()