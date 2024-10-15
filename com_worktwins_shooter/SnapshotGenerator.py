# SnapshotGenerator.py

import os
import re
from datetime import datetime
import json
from collections import defaultdict

class SnapshotGenerator:
    # Class variables for common avoid folders and files
    COMMON_AVOID_FOLDERS = [
        "node_modules", "venv", "env", "__pycache__", "site-packages", "myenv",
        "target", "bin", "build",
        "obj",
        "vendor", ".git", ".hg", ".svn"
    ]

    COMMON_AVOID_FILES = [
        "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "Cargo.lock",
        "Pipfile.lock", "composer.lock", ".DS_Store", "thumbs.db", "Thumbs.db",
        "npm-debug.log", "yarn-error.log", "Dockerfile", "docker-compose.yml",
        ".env", ".gitignore", ".gitattributes", "Makefile"
    ]

    # Key framework files to include
    KEY_FILES = [
        "Dockerfile", ".dockerignore", "package.json", "requirements.txt",
        "Pipfile", "composer.json", "Gemfile", "build.gradle", "pom.xml",
        "Cargo.toml", "Makefile"
    ]

    # Include extensions for source code files
    INCLUDE_EXTENSIONS = [
        # Programming Languages
        ".js", ".mjs", ".jsx",     # JavaScript
        ".ts", ".tsx",             # TypeScript
        ".py",                     # Python
        ".java",                   # Java
        ".cs", ".csproj",          # C#
        ".cpp", ".hpp", ".h", ".cc", # C++
        ".c", ".h",                # C
        ".rb", ".erb", ".rake",    # Ruby
        ".php", ".phtml", ".php3", ".php4", ".php5", ".phps", # PHP
        ".swift",                  # Swift
        ".kt", ".kts",             # Kotlin
        ".go",                     # Go
        ".R", ".r",                # R
        ".pl", ".pm", ".t",        # Perl
        ".sh", ".bash",            # Shell Scripting
        ".html", ".htm",           # HTML
        ".css", ".scss", ".sass", ".less", # CSS and preprocessors
        ".sql",                    # SQL
        ".scala", ".sc",           # Scala
        ".hs", ".lhs",             # Haskell
        ".lua",                    # Lua
        ".rs",                     # Rust
        ".dart",                   # Dart
        ".m",                      # MATLAB, Objective-C
        ".jl",                     # Julia
        ".vb", ".vbs",             # Visual Basic
        ".asm", ".s",              # Assembly Language
        ".fs", ".fsi", ".fsx",     # F#
        ".groovy", ".gvy", ".gy", ".gsh", # Groovy
        ".erl", ".hrl",            # Erlang
        ".ex", ".exs",             # Elixir
        ".cob", ".cbl",            # COBOL
        ".f", ".for", ".f90", ".f95", # Fortran
        ".adb", ".ads",            # Ada
        ".pl", ".pro", ".P",       # Prolog
        ".lisp", ".lsp",           # Lisp
        ".scm", ".ss",             # Scheme
        ".rkt",                    # Racket
        ".v", ".vh",               # Verilog
        ".vhdl", ".vhd",           # VHDL
        ".md", ".markdown",        # Markdown

        # Frameworks and Libraries
        ".vue",                    # Vue.js
        ".svelte",                 # Svelte
        ".ipynb",                  # Jupyter Notebooks

        # Configuration and Other Relevant Files
        ".json",                   # JSON
        ".yaml", ".yml",           # YAML
        ".xml",                    # XML
        ".gitignore", ".gitattributes", # Git
        ".travis.yml", "Jenkinsfile", ".circleci/config.yml", ".gitlab-ci.yml", "azure-pipelines.yml" # CI/CD
    ]

    # Define a set of binary file extensions to skip
    BINARY_EXTENSIONS = {
        ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".pdf", ".exe", ".dll", ".so",
        ".zip", ".tar", ".gz", ".7z", ".rar", ".mp3", ".mp4", ".avi", ".mov",
        ".wmv", ".flv", ".mkv", ".iso", ".jar", ".war", ".ear", ".class", ".o",
        ".obj", ".pyc", ".pyo", ".apk", ".dmg", ".pkg", ".app", ".deb", ".rpm",
        ".psd", ".ai", ".eps", ".ps", ".ttf", ".woff", ".woff2", ".eot", ".otf",
        ".ico", ".icns", ".swf", ".fla", ".cab", ".sys", ".msi", ".msp", ".msm",
        ".crx", ".xpi", ".vsix", ".doc", ".docx", ".xls", ".xlsx", ".ppt",
        ".pptx", ".odt", ".ods", ".odp", ".odg", ".odb", ".odf", ".rtf"
    }

    def __init__(self, config):
        self.root_dir = config['root_dir']
        self.avoid_folders = config['avoid_folders']
        self.avoid_files = set(config.get('avoid_files', []))
        self.include_extensions = set(config['include_extensions'])
        self.key_files = config['key_files']
        self.output_file = config.get('output_file', None)
        self.compress = config.get('compress', 0)
        self.amount_of_chunks = config.get('amount_of_chunks', 0)
        self.size_of_chunk = config.get('size_of_chunk', 0)
        self.imports = defaultdict(int)
        self.project_name = os.path.basename(self.root_dir)
        self.language_extensions = {
            ".py": "Python",
            ".js": "JavaScript",
            ".java": "Java",
            ".cpp": "C++",
            ".c": "C",
            ".cs": "C#",
            ".php": "PHP",
            ".rb": "Ruby",
            ".go": "Go",
            ".swift": "Swift",
            ".ts": "TypeScript",
            ".kt": "Kotlin",
            ".rs": "Rust",
            ".dart": "Dart",
            # Add more mappings as needed
        }
        self.detected_language = None
        self.print_console = config.get('print_console', False)

    def generate_context_data(self):
        project_data = {
            'project_name': self.project_name,
            'project_sources': [],
            'external_libraries': [],
            'observations': []
        }

        if self.print_console:
            print(f"Processing project: {self.project_name}")

        for root, dirs, files in os.walk(self.root_dir):
            # Exclude directories
            dirs[:] = [d for d in dirs if d not in self.avoid_folders]

            for file in files:
                if file in self.avoid_files:
                    continue

                file_path = os.path.join(root, file)
                extension = os.path.splitext(file)[1].lower()

                # Skip binary files
                if extension in self.BINARY_EXTENSIONS:
                    if self.print_console:
                        print(f"Skipping binary file {file_path}")
                    continue

                # Process files with included extensions or key files
                if extension in self.include_extensions or file in self.key_files:
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()

                        file_info = os.stat(file_path)
                        source_data = {
                            'file': {
                                'File': file,
                                'Full Path': file_path,
                                'Relative Path': os.path.relpath(file_path, self.root_dir),
                                'Size': file_info.st_size,
                                'Last Modified': datetime.fromtimestamp(file_info.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
                                'Lines': len(content.splitlines()),
                                'Source_Code': content
                            }
                        }
                        project_data['project_sources'].append(source_data)

                        # Extract imports
                        self.extract_imports(content, extension)

                        # Detect programming language
                        if not self.detected_language:
                            self.detected_language = self.detect_programming_language(file)

                    except UnicodeDecodeError as e:
                        if self.print_console:
                            print(f"Skipping file {file_path} due to decoding error: {e}")
                    except Exception as e:
                        if self.print_console:
                            print(f"Skipping file {file_path} due to an unexpected error: {e}")

        project_data['programming_language'] = self.detected_language or 'unknown'
        project_data['file_count'] = len(project_data['project_sources'])  # Adding file_count
        project_data['external_libraries'] = [{"import_name": imp, "count": count} for imp, count in self.imports.items()]

        if not self.imports:
            project_data['observations'].append("No external libraries or imports were detected in the source code.")

        return project_data

    def generate_context_file(self):
        project_data = self.generate_context_data()

        if self.output_file:
            with open(self.output_file, 'w', encoding='utf-8') as f_out:
                json.dump(project_data, f_out, indent=4)

            os.chmod(self.output_file, 0o666)
            if self.print_console:
                print(f"Context file generated at: {self.output_file}")

    def extract_imports(self, content, extension):
        if extension == '.py':
            imports = re.findall(r'^\s*(?:import|from)\s+([^\s,]+)', content, re.MULTILINE)
            for imp in imports:
                self.imports[imp] += 1
        elif extension in ['.js', '.jsx', '.ts', '.tsx']:
            imports = re.findall(r'^\s*(?:import\s.*?from\s+[\'"]([^\'"]+)[\'"])|(?:require\([\'"]([^\'"]+)[\'"]\))', content, re.MULTILINE)
            for imp_tuple in imports:
                imp = imp_tuple[0] or imp_tuple[1]
                if imp:
                    self.imports[imp] += 1
        elif extension == '.java':
            imports = re.findall(r'^\s*import\s+([^\s;]+);', content, re.MULTILINE)
            for imp in imports:
                self.imports[imp] += 1
        # Add parsing for other languages if needed

    def detect_programming_language(self, filename):
        extension = os.path.splitext(filename)[1]
        return self.language_extensions.get(extension)

    # Add other methods if necessary
