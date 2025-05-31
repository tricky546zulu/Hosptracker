#!/usr/bin/env python3
"""
Quick PDF verification script to check SCH extraction accuracy
"""
import requests
import pdfplumber
import io
import json
import os
from openai import OpenAI

# Initialize OpenAI
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
openai_client = OpenAI(api_key=OPENAI_API_KEY)

def verify_sch_extraction():
    """Verify SCH patient count extraction from PDF"""
    try:
        # Download PDF
        pdf_url = "https://www.ehealthsask.ca/reporting/Documents/SaskatoonHospitalBedCapacity.pdf"
        
        print("Downloading PDF...")
        response = requests.get(pdf_url, timeout=30)
        response.raise_for_status()
        
        # Extract text
        with pdfplumber.open(io.BytesIO(response.content)) as pdf:
            all_text = ""
            for page in pdf.pages:
                all_text += page.extract_text() + "\n"
        
        # Find Emergency Department table section
        lines = all_text.split('\n')
        ed_lines = []
        
        for i, line in enumerate(lines):
            if 'Emergency Department' in line or any(code in line for code in ['SCH', 'RUH', 'SPH', 'JPCH']) and any(c.isdigit() for c in line):
                # Include context
                start = max(0, i-2)
                end = min(len(lines), i+3)
                for j in range(start, end):
                    if lines[j].strip():
                        ed_lines.append(f"Line {j+1}: {lines[j]}")
        
        print("Emergency Department sections found:")
        for line in ed_lines[:20]:
            print(line)
            if 'SCH' in line:
                print("  ^^ SCH LINE FOUND ^^")
        
        # AI analysis of the table
        table_text = '\n'.join(ed_lines)
        
        prompt = f"""
        Analyze this Emergency Department table from eHealth Saskatchewan PDF and extract the EXACT patient counts.
        
        TABLE TEXT:
        {table_text}
        
        Find the Emergency Department table with columns like: Site, Admitted, Active, Consults, Total
        
        For SCH (Saskatoon City Hospital), what is the EXACT number in the "Total" column?
        
        Respond with JSON:
        {{
            "sch_total": number,
            "table_line_found": "exact line with SCH data",
            "confidence": 0-1,
            "analysis": "explanation of how you found the number"
        }}
        """
        
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a precise data extraction expert. Extract exact numbers from tables."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.1
        )
        
        ai_result = json.loads(response.choices[0].message.content)
        
        print("\n=== AI ANALYSIS ===")
        print(json.dumps(ai_result, indent=2))
        
        return ai_result
        
    except Exception as e:
        print(f"Error: {e}")
        return None

if __name__ == "__main__":
    verify_sch_extraction()