# com_worktwins_data_sources/LocalFoldersDataSource.py

from com_worktwins_data_sources.WorkTwinsDataSource import WorkTwinsDataSource
import logging

class LocalFoldersDataSource(WorkTwinsDataSource):
    def __init__(self, source_code_dir, progress_callback=None, compress=0, amount_of_chunks=0, size_of_chunk=0):
        super().__init__(source_code_dir, progress_callback)
        self.data_source_name = 'local_folder'
        self.compress = compress
        self.amount_of_chunks = amount_of_chunks
        self.size_of_chunk = size_of_chunk

    def fetch_data(self):
        """
        Since data is already present locally, no action is needed.
        This method can be used to verify the local folder or perform additional checks.
        """
        logging.info(f"Using local folder: {self.source_code_dir}")
        # Additional processing can be added here if necessary
