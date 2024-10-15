# TechReporter.py

import os
import json
from datetime import datetime
from fpdf import FPDF  # Ensure you have fpdf installed: pip install fpdf
import logging

# Configure logging
logging.basicConfig(
    filename='worktwins.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class TechReporter:
    def __init__(self):
        self.overall_summary = {}

    def generate_json_report(self, reports_dir):
        # This method can be used for further aggregation if needed
        pass  # Currently, overall JSON report is generated in WorkTwinsDataSource.py

    def generate_pdf_report(self, reports_dir, output_path):
        # Generate a PDF report using all snapshot JSON files in reports_dir
        # Assuming that WorkTwinsDataSource has already created the overall JSON report
        # Here, we read the overall JSON report and create a PDF from it

        # Find the latest overall JSON report
        overall_reports = [f for f in os.listdir(reports_dir) if f.startswith('report_') and f.endswith('.json')]
        if not overall_reports:
            logging.warning("No overall JSON reports found to generate PDF.")
            print("No overall JSON reports found to generate PDF.")
            return

        latest_report = max(overall_reports, key=lambda x: os.path.getmtime(os.path.join(reports_dir, x)))
        report_path = os.path.join(reports_dir, latest_report)

        try:
            with open(report_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            logging.info(f"Loaded overall JSON report from {report_path}")
            print(f"Loaded overall JSON report from {report_path}")
        except Exception as e:
            logging.error(f"Failed to load overall report {report_path}: {e}")
            print(f"Failed to load overall report {report_path}: {e}")
            return

        # Initialize PDF
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=16)
        pdf.cell(200, 10, txt="WorkTwins FootPrint Report", ln=True, align='C')
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt=f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True, align='C')
        pdf.ln(10)

        for project in data:
            pdf.set_font("Arial", 'B', size=14)
            pdf.cell(200, 10, txt=f"Project: {project.get('project_name', 'N/A')}", ln=True)
            pdf.set_font("Arial", size=12)
            pdf.cell(200, 10, txt=f"Programming Language: {project.get('programming_language', 'N/A')}", ln=True)
            pdf.cell(200, 10, txt=f"Number of Source Files: {len(project.get('project_sources', []))}", ln=True)
            pdf.ln(5)

            # Add external libraries
            external_libs = project.get('external_libraries', [])
            if external_libs:
                pdf.set_font("Arial", 'B', size=12)
                pdf.cell(200, 10, txt="External Libraries:", ln=True)
                pdf.set_font("Arial", size=12)
                for lib in external_libs:
                    pdf.cell(200, 10, txt=f"- {lib.get('import_name', 'N/A')}: {lib.get('count', 0)} imports", ln=True)
            else:
                pdf.cell(200, 10, txt="No external libraries or imports detected.", ln=True)

            # Add observations if any
            observations = project.get('observations', [])
            if observations:
                pdf.set_font("Arial", 'B', size=12)
                pdf.cell(200, 10, txt="Observations:", ln=True)
                pdf.set_font("Arial", size=12)
                for obs in observations:
                    pdf.cell(200, 10, txt=f"- {obs}", ln=True)

            pdf.ln(10)  # Add space between projects

        # Save the PDF
        try:
            pdf.output(output_path)
            logging.info(f"PDF report generated at: {output_path}")
            print(f"PDF report generated at: {output_path}")
        except Exception as e:
            logging.error(f"Failed to generate PDF report {output_path}: {e}")
            print(f"Failed to generate PDF report {output_path}: {e}")
