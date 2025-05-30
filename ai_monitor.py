import os
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from openai import OpenAI

from app import app, db
from models import HospitalCapacity, ScrapingLog

# the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
# do not change this unless explicitly requested by the user

class AIMonitor:
    def __init__(self):
        self.client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        
    def analyze_hospital_data(self, hospital_data: List[Dict], historical_data: Dict) -> Dict[str, Any]:
        """
        Analyze current hospital data against historical patterns using AI
        """
        try:
            # Prepare data for AI analysis
            analysis_prompt = self._build_analysis_prompt(hospital_data, historical_data)
            
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert healthcare data analyst specializing in Emergency Department capacity monitoring. "
                        + "Analyze hospital data for anomalies, trends, and potential issues. "
                        + "Respond with JSON in this format: "
                        + "{'anomalies': [{'hospital': 'code', 'issue': 'description', 'severity': 'low/medium/high'}], "
                        + "'trends': [{'hospital': 'code', 'pattern': 'description'}], "
                        + "'overall_assessment': 'summary', 'confidence': number_0_to_1, 'alerts': [{'type': 'alert_type', 'message': 'alert_message'}]}"
                    },
                    {
                        "role": "user", 
                        "content": analysis_prompt
                    }
                ],
                response_format={"type": "json_object"},
                temperature=0.1
            )
            
            result = json.loads(response.choices[0].message.content)
            result['timestamp'] = datetime.utcnow().isoformat()
            result['analysis_type'] = 'ai_oversight'
            
            return result
            
        except Exception as e:
            logging.error(f"Error in AI analysis: {e}")
            return {
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat(),
                'analysis_type': 'ai_oversight'
            }
    
    def _build_analysis_prompt(self, current_data: List[Dict], historical_data: Dict) -> str:
        """
        Build analysis prompt for AI review
        """
        prompt = "Analyze the following Emergency Department data for Saskatoon hospitals:\n\n"
        
        # Current data
        prompt += "CURRENT DATA:\n"
        for hospital in current_data:
            prompt += f"- {hospital['hospital_code']}: {hospital['total_patients']} patients\n"
        
        # Historical context
        prompt += "\nHISTORICAL CONTEXT (past 24 hours):\n"
        for hospital_code, data in historical_data.items():
            if data:
                avg = sum(d['total_patients'] for d in data) / len(data)
                min_val = min(d['total_patients'] for d in data)
                max_val = max(d['total_patients'] for d in data)
                prompt += f"- {hospital_code}: Average: {avg:.1f}, Range: {min_val}-{max_val} patients\n"
        
        prompt += "\nPLEASE ANALYZE FOR:\n"
        prompt += "1. Unusual spikes or drops in patient counts\n"
        prompt += "2. Values that seem unrealistic for Emergency Department capacity\n"
        prompt += "3. Patterns that might indicate data extraction errors\n"
        prompt += "4. Trends that healthcare administrators should be aware of\n"
        prompt += "5. Any other anomalies or concerns\n\n"
        
        prompt += "HOSPITAL CONTEXT:\n"
        prompt += "- RUH (Royal University Hospital): Major trauma center, typically 40-80 patients\n"
        prompt += "- SPH (St. Paul's Hospital): General hospital, typically 20-50 patients\n"
        prompt += "- SCH (Saskatoon City Hospital): General hospital, typically 10-40 patients\n"
        prompt += "- JPCH (Jim Pattison Children's Hospital): Pediatric hospital, typically 5-25 patients\n"
        
        return prompt
    
    def get_historical_data(self, hours: int = 24) -> Dict[str, List[Dict]]:
        """
        Get historical data for comparison
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        hospitals = ['RUH', 'SPH', 'SCH', 'JPCH']
        historical_data = {}
        
        for hospital_code in hospitals:
            records = HospitalCapacity.query.filter(
                HospitalCapacity.hospital_code == hospital_code,
                HospitalCapacity.timestamp >= cutoff_time
            ).order_by(HospitalCapacity.timestamp.desc()).limit(50).all()
            
            historical_data[hospital_code] = [
                {
                    'total_patients': record.total_patients,
                    'timestamp': record.timestamp.isoformat()
                }
                for record in records
            ]
        
        return historical_data
    
    def validate_data_extraction(self, extracted_data: List[Dict]) -> Dict[str, Any]:
        """
        AI validation of extracted data before saving to database
        """
        try:
            validation_prompt = self._build_validation_prompt(extracted_data)
            
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a data quality expert for healthcare systems. "
                        + "Validate Emergency Department patient counts for accuracy and reasonableness. "
                        + "Respond with JSON in this format: "
                        + "{'valid': true/false, 'issues': [{'hospital': 'code', 'problem': 'description', 'suggested_action': 'action'}], "
                        + "'confidence': number_0_to_1, 'overall_assessment': 'summary'}"
                    },
                    {
                        "role": "user",
                        "content": validation_prompt
                    }
                ],
                response_format={"type": "json_object"},
                temperature=0.1
            )
            
            result = json.loads(response.choices[0].message.content)
            result['timestamp'] = datetime.utcnow().isoformat()
            result['validation_type'] = 'pre_save_check'
            
            return result
            
        except Exception as e:
            logging.error(f"Error in AI validation: {e}")
            return {
                'valid': True,  # Allow data through if AI fails
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat(),
                'validation_type': 'pre_save_check'
            }
    
    def _build_validation_prompt(self, extracted_data: List[Dict]) -> str:
        """
        Build validation prompt for extracted data
        """
        prompt = "Validate the following Emergency Department data extracted from eHealth Saskatchewan PDF:\n\n"
        
        for hospital in extracted_data:
            prompt += f"- {hospital['hospital_code']}: {hospital['total_patients']} patients\n"
        
        prompt += "\nVALIDATION CRITERIA:\n"
        prompt += "1. Are these values realistic for Emergency Department capacity?\n"
        prompt += "2. Do any values seem like potential extraction errors?\n"
        prompt += "3. Are all expected hospitals present?\n"
        prompt += "4. Do the values make sense in context of Saskatoon hospital system?\n\n"
        
        prompt += "EXPECTED RANGES:\n"
        prompt += "- RUH: 20-200 patients (major trauma center)\n"
        prompt += "- SPH: 10-80 patients (general hospital)\n"
        prompt += "- SCH: 5-60 patients (general hospital)\n"
        prompt += "- JPCH: 1-40 patients (pediatric hospital)\n"
        
        return prompt
    
    def generate_insights_report(self) -> Dict[str, Any]:
        """
        Generate comprehensive insights about hospital trends and patterns
        """
        try:
            # Get data for past week
            historical_data = self.get_historical_data(hours=168)  # 7 days
            
            insights_prompt = self._build_insights_prompt(historical_data)
            
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a healthcare analytics expert specializing in Emergency Department operations. "
                        + "Generate actionable insights about patient flow patterns, capacity trends, and operational recommendations. "
                        + "Respond with JSON in this format: "
                        + "{'key_insights': [{'insight': 'description', 'hospital': 'code_or_all', 'impact': 'high/medium/low'}], "
                        + "'recommendations': [{'recommendation': 'description', 'rationale': 'explanation'}], "
                        + "'patterns': {'hourly': 'description', 'daily': 'description', 'weekly': 'description'}, "
                        + "'forecasting': 'next_24_hours_prediction', 'confidence': number_0_to_1}"
                    },
                    {
                        "role": "user",
                        "content": insights_prompt
                    }
                ],
                response_format={"type": "json_object"},
                temperature=0.2
            )
            
            result = json.loads(response.choices[0].message.content)
            result['timestamp'] = datetime.utcnow().isoformat()
            result['report_type'] = 'weekly_insights'
            
            return result
            
        except Exception as e:
            logging.error(f"Error generating insights: {e}")
            return {
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat(),
                'report_type': 'weekly_insights'
            }
    
    def _build_insights_prompt(self, historical_data: Dict[str, List[Dict]]) -> str:
        """
        Build prompt for insights analysis
        """
        prompt = "Analyze the following 7-day Emergency Department data for Saskatoon hospitals:\n\n"
        
        for hospital_code, data in historical_data.items():
            if data:
                values = [d['total_patients'] for d in data]
                prompt += f"{hospital_code}:\n"
                prompt += f"  - Total readings: {len(values)}\n"
                prompt += f"  - Average: {sum(values)/len(values):.1f} patients\n"
                prompt += f"  - Range: {min(values)}-{max(values)} patients\n"
                prompt += f"  - Recent trend: {values[:5] if len(values) >= 5 else values}\n\n"
        
        prompt += "ANALYSIS REQUESTED:\n"
        prompt += "1. Identify patterns in patient flow (time of day, day of week)\n"
        prompt += "2. Compare hospitals' relative capacity utilization\n"
        prompt += "3. Detect any concerning trends or operational issues\n"
        prompt += "4. Predict likely capacity needs for next 24 hours\n"
        prompt += "5. Recommend operational improvements or resource allocation\n"
        
        return prompt


def run_ai_oversight():
    """
    Run AI oversight analysis on current data
    """
    with app.app_context():
        try:
            monitor = AIMonitor()
            
            # Get current data (latest reading for each hospital)
            current_data = []
            hospitals = ['RUH', 'SPH', 'SCH', 'JPCH']
            
            for hospital_code in hospitals:
                latest = HospitalCapacity.query.filter_by(
                    hospital_code=hospital_code
                ).order_by(HospitalCapacity.timestamp.desc()).first()
                
                if latest:
                    current_data.append({
                        'hospital_code': hospital_code,
                        'hospital_name': latest.hospital_name,
                        'total_patients': latest.total_patients,
                        'timestamp': latest.timestamp.isoformat()
                    })
            
            if not current_data:
                logging.warning("No current data available for AI oversight")
                return None
            
            # Get historical context
            historical_data = monitor.get_historical_data(24)
            
            # Run AI analysis
            analysis = monitor.analyze_hospital_data(current_data, historical_data)
            
            # Log analysis results
            if 'error' not in analysis:
                log_message = f"AI Oversight: {analysis.get('overall_assessment', 'Analysis completed')}"
                if analysis.get('anomalies'):
                    log_message += f" | Anomalies detected: {len(analysis['anomalies'])}"
                if analysis.get('alerts'):
                    log_message += f" | Alerts: {len(analysis['alerts'])}"
            else:
                log_message = f"AI Oversight error: {analysis['error']}"
            
            # Save to scraping log for tracking
            log_entry = ScrapingLog(
                status='ai_analysis',
                message=log_message[:500],  # Truncate if too long
                pdf_url='ai_oversight_system'
            )
            db.session.add(log_entry)
            db.session.commit()
            
            logging.info(f"AI oversight completed: {log_message}")
            return analysis
            
        except Exception as e:
            logging.error(f"Error in AI oversight: {e}")
            return None


def validate_extracted_data(extracted_data: List[Dict]) -> bool:
    """
    Validate extracted data using AI before saving
    """
    try:
        monitor = AIMonitor()
        validation = monitor.validate_data_extraction(extracted_data)
        
        if 'error' in validation:
            logging.warning(f"AI validation failed: {validation['error']}")
            return True  # Allow data through if AI validation fails
        
        if not validation.get('valid', True):
            issues = validation.get('issues', [])
            logging.warning(f"AI validation flagged issues: {issues}")
            
            # Log validation concerns but still allow data through
            # (Human oversight can review these later)
            log_entry = ScrapingLog(
                status='validation_warning',
                message=f"AI flagged data quality issues: {json.dumps(issues)[:500]}",
                pdf_url='ai_validation_system'
            )
            
            with app.app_context():
                db.session.add(log_entry)
                db.session.commit()
        
        return True  # Always allow data through for now
        
    except Exception as e:
        logging.error(f"Error in AI validation: {e}")
        return True  # Allow data through if validation fails