# com_worktwins_data_sources/WorkTwinsDataSource.py

import os
import logging
from datetime import datetime
from abc import ABC, abstractmethod
import json
import shutil  # For deleting temporary snapshots
from com_worktwins_shooter.SnapshotGenerator import SnapshotGenerator
from collections import defaultdict

# Configure logging
logging.basicConfig(
    filename='worktwins.log',
    level=logging.DEBUG,  # Ensure DEBUG level is enabled for detailed logs
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class WorkTwinsDataSource(ABC):
    def __init__(self, source_code_dir, progress_callback=None):
        self.source_code_dir = source_code_dir  # e.g., com_worktwins_data_github
        self.progress_callback = progress_callback
        self.projects = []
        self.total_projects = 0
        self.scanned_projects = 0
        self.data_source_name = 'datasource'  # Should be overridden in child classes

        # Set the temporary snapshots directory
        self.temp_snapshots_dir = 'com_worktwins_data_tmp'

        # Set the reports directory
        self.reports_dir = 'com_worktwins_data_reports'

        # Ensure that temp_snapshots_dir and reports_dir exist
        os.makedirs(self.temp_snapshots_dir, exist_ok=True)
        os.makedirs(self.reports_dir, exist_ok=True)

    @abstractmethod
    def fetch_data(self):
        """
        Abstract method to fetch data from the data source.
        This could be cloning repositories, downloading files, etc.
        """
        pass

    def generate_json_report(self, output_path=None, print_console=False):
        self.scan_projects()
        timestamp = datetime.now().strftime("%Y%m%d%H%M")

        # Default output file name and path for the overall report
        if output_path is None:
            output_file_name = f"report_{self.data_source_name}_{timestamp}.json"
            output_file_path = os.path.join(self.reports_dir, output_file_name)
        else:
            output_file_path = output_path

        for project_path in self.projects:
            project_name = os.path.basename(project_path)

            # Create snapshot file path in temp_snapshots_dir with .json extension
            snapshot_file_name = f"{project_name}_snapshot_{timestamp}.json"
            snapshot_file_path = os.path.join(self.temp_snapshots_dir, snapshot_file_name)

            config = {
                "root_dir": project_path,
                "avoid_folders": SnapshotGenerator.COMMON_AVOID_FOLDERS,
                "avoid_files": SnapshotGenerator.COMMON_AVOID_FILES,
                "include_extensions": SnapshotGenerator.INCLUDE_EXTENSIONS,
                "key_files": SnapshotGenerator.KEY_FILES,
                "output_file": snapshot_file_path,  # Save snapshot to file
                "compress": self.compress,
                "amount_of_chunks": self.amount_of_chunks,
                "size_of_chunk": self.size_of_chunk,
                "print_console": print_console
            }

            try:
                generator = SnapshotGenerator(config)
                generator.generate_context_file()  # Generates and saves the snapshot
                logging.info(f"Generated snapshot for project {project_name} at {snapshot_file_path}")
                if print_console:
                    print(f"Generated snapshot for project {project_name} at {snapshot_file_path}")
            except Exception as e:
                logging.error(f"Failed to generate snapshot for project {project_name}: {e}")
                if print_console:
                    print(f"Failed to generate snapshot for project {project_name}: {e}")

            # Update progress
            self.scanned_projects += 1
            if self.progress_callback and self.total_projects > 0:
                progress_value = int((self.scanned_projects / self.total_projects) * 100)
                self.progress_callback(progress_value)

        # Now, aggregate snapshot data into the overall JSON report
        logging.info("Starting to aggregate snapshot data into the overall JSON report...")

        aggregated_data = self.aggregate_snapshots()

        overall_summary = {
            'github_user_name': self.get_github_username(),
            'programming_languages': aggregated_data
        }

        # Save aggregated data to the overall JSON report
        try:
            with open(output_file_path, 'w', encoding='utf-8') as f_out:
                json.dump(overall_summary, f_out, indent=4)
            logging.info(f"Overall JSON report generated at: {output_file_path}")
            if print_console:
                print(f"Overall JSON report generated at: {output_file_path}")
        except Exception as e:
            logging.error(f"Failed to write overall report {output_file_path}: {e}")
            if print_console:
                print(f"Failed to write overall report {output_file_path}: {e}")

        # **Commenting out the deletion of temporary snapshots for debugging**
        # Delete the temporary snapshots after generating the report
        # try:
        #     shutil.rmtree(self.temp_snapshots_dir)
        #     os.makedirs(self.temp_snapshots_dir, exist_ok=True)  # Recreate the directory for future use
        #     logging.info(f"Temporary snapshots deleted from {self.temp_snapshots_dir}")
        #     if print_console:
        #         print(f"Temporary snapshots deleted from {self.temp_snapshots_dir}")
        # except Exception as e:
        #     logging.error(f"Failed to delete temporary snapshots: {e}")
        #     if print_console:
        #         print(f"Failed to delete temporary snapshots: {e}")

    def aggregate_snapshots(self):
        """
        Aggregates data from all snapshot JSON files into a structured summary.
        """
        imports_agg = defaultdict(lambda: defaultdict(int))
        file_counts = defaultdict(int)

        for file in os.listdir(self.temp_snapshots_dir):
            if '_snapshot_' in file and file.endswith('.json'):  # Updated condition
                snapshot_file_path = os.path.join(self.temp_snapshots_dir, file)
                try:
                    with open(snapshot_file_path, 'r', encoding='utf-8') as f:
                        project_data = json.load(f)
                        logging.debug(f"Processing snapshot file: {snapshot_file_path}")

                        # Assertions to ensure expected fields exist
                        assert 'programming_language' in project_data, f"'programming_language' missing in {snapshot_file_path}"
                        assert 'file_count' in project_data, f"'file_count' missing in {snapshot_file_path}"
                        assert 'external_libraries' in project_data, f"'external_libraries' missing in {snapshot_file_path}"

                        programming_language = project_data.get('programming_language', '').lower()
                        if programming_language:
                            file_count = project_data.get('file_count', 0)
                            file_counts[programming_language] += file_count
                            logging.debug(f"Found programming language: {programming_language} with {file_count} files")

                            external_libraries = project_data.get('external_libraries', [])
                            if not external_libraries:
                                logging.debug(f"No external libraries found in {snapshot_file_path}")
                            for lib in external_libraries:
                                if isinstance(lib, dict) and 'import_name' in lib and 'count' in lib:
                                    import_name = lib['import_name']
                                    count = lib['count']
                                    # Temporarily disable filtering for debugging
                                    # if self.is_external_library(import_name):
                                    imports_agg[programming_language][import_name] += count
                                    logging.debug(f"Aggregated library: {import_name} with count: {count} for language: {programming_language}")
                                else:
                                    logging.warning(f"Invalid library entry in {snapshot_file_path}: {lib}")
                        else:
                            logging.warning(f"No programming language specified in snapshot: {snapshot_file_path}")
                except AssertionError as ae:
                    logging.error(ae)
                except Exception as e:
                    logging.error(f"Failed to load snapshot {snapshot_file_path}: {e}")

        overall_data = []
        for lang, libs in imports_agg.items():
            libs_list = [{'library_name': lib, 'times_imported': count} for lib, count in sorted(libs.items(), key=lambda item: item[1], reverse=True)]
            overall_data.append({
                'programming_language': lang,
                'libraries_used': libs_list,
                'file_count': file_counts[lang]
            })
            logging.debug(f"Aggregated data for language: {lang} with {len(libs_list)} libraries and {file_counts[lang]} files")

        overall_data.sort(key=lambda x: x['file_count'], reverse=True)

        return overall_data

    def is_external_library(self, lib_name):
        """
        Determines if a library is external based on predefined substrings.
        """
        EXCLUDE_SUBSTRINGS = [
            "com_goldenthinker_",
            "brainboost",
            "goldenthinker",
            "smartband",
            "papitomarket",
            "pelucadorada",
            "formate"
        ]
        for substring in EXCLUDE_SUBSTRINGS:
            if substring.lower() in lib_name.lower():  # Case-insensitive check
                return False
        return True

    def get_github_username(self):
        """
        Retrieves the GitHub username associated with this data source.
        This method should be overridden in GitHubDataSource to return the actual username.
        """
        return "unknown"

    def generate_pdf_report(self, overall_summary, pdf_output_path):
        """
        Generates a PDF report from the aggregated JSON data.
        """
        try:
            json_data = overall_summary

            # Create temporary directory for charts
            charts_dir = os.path.join(self.reports_dir, "charts")
            os.makedirs(charts_dir, exist_ok=True)

            from reportlab.lib.pagesizes import letter
            from reportlab.pdfgen import canvas
            import matplotlib.pyplot as plt

            def draw_pie_chart(data, title, file_path):
                labels = [item['library_name'] for item in data]
                sizes = [item['times_imported'] for item in data]

                plt.figure(figsize=(10, 6))
                plt.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=140)
                plt.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.
                plt.title(title)
                plt.savefig(file_path)
                plt.close()

            def draw_bar_chart(data, title, file_path):
                labels = [item['library_name'] for item in data]
                sizes = [item['times_imported'] for item in data]

                plt.figure(figsize=(12, 8))
                plt.bar(labels, sizes, color='skyblue')
                plt.xlabel('Libraries')
                plt.ylabel('Number of Imports')
                plt.title(title)
                plt.xticks(rotation=90)
                plt.tight_layout()
                plt.savefig(file_path)
                plt.close()

            pdf = canvas.Canvas(pdf_output_path, pagesize=letter)
            width, height = letter

            pdf.setFont("Helvetica", 14)
            pdf.drawString(30, height - 30, f"GitHub User: {json_data.get('github_user_name', 'Unknown')} - Overall Statistics")

            current_y = height - 60

            for lang_data in json_data.get('programming_languages', []):
                programming_language = lang_data.get('programming_language', 'Unknown').capitalize()
                file_count = lang_data.get('file_count', 0)
                libraries_used = lang_data.get('libraries_used', [])

                pdf.setFont("Helvetica-Bold", 12)
                pdf.drawString(30, current_y, f"Programming Language: {programming_language} (Files: {file_count})")
                current_y -= 20

                if libraries_used:
                    pie_chart_path = os.path.join(charts_dir, f"pie_chart_{programming_language}.png")
                    bar_chart_path = os.path.join(charts_dir, f"bar_chart_{programming_language}.png")

                    draw_pie_chart(libraries_used, f"Library Usage for {programming_language}", pie_chart_path)
                    draw_bar_chart(libraries_used, f"Library Usage for {programming_language}", bar_chart_path)

                    # Ensure images exist before drawing
                    if os.path.exists(pie_chart_path) and os.path.exists(bar_chart_path):
                        pdf.drawImage(pie_chart_path, 30, current_y - 200, width=200, height=200)
                        pdf.drawImage(bar_chart_path, 250, current_y - 200, width=300, height=200)
                        current_y -= 220
                    else:
                        logging.warning(f"Chart images for {programming_language} not found.")
                        current_y -= 20

                pdf.setFont("Helvetica", 10)
                for lib in libraries_used:
                    pdf.drawString(30, current_y, f"{lib['library_name']}: {lib['times_imported']} imports")
                    current_y -= 15

                current_y -= 20

                if current_y < 100:
                    pdf.showPage()
                    current_y = height - 30

            pdf.save()

            logging.info(f"PDF report generated at: {pdf_output_path}")
            print(f"PDF report generated at: {pdf_output_path}")

        except Exception as e:
            logging.error(f"Failed to generate PDF report at {pdf_output_path}: {e}")
            print(f"Failed to generate PDF report at {pdf_output_path}: {e}")

    def scan_projects(self):
        # Get a list of all subdirectories (projects) in the source code directory
        for root, dirs, files in os.walk(self.source_code_dir):
            for dir_name in dirs:
                dir_path = os.path.join(root, dir_name)
                self.projects.append(dir_path)
            break  # Only get top-level directories
        if not self.projects:
            self.projects = [self.source_code_dir]  # Analyze the current directory if no subdirectories
        self.total_projects = len(self.projects)
        logging.info(f"Total projects found for data source '{self.data_source_name}': {self.total_projects}")
