# PDF Namer

A Python CLI tool that intelligently renames PDF files using LLaMA AI model integration. It extracts text from PDFs and generates meaningful filenames based on the content.

[![Python Tests](https://github.com/yourusername/pdf-namer/actions/workflows/pytest.yml/badge.svg)](https://github.com/yourusername/pdf-namer/actions/workflows/pytest.yml)

## Features

- Extracts text content from PDF files
- Uses LLaMA AI to generate meaningful filenames
- Supports different LLaMA models
- Includes test mode for safe operation
- Handles batch processing of multiple PDFs
- Configurable context window sizes
- Built-in error handling and validation

## Prerequisites

- Python 3.11 or higher
- Ollama running locally with LLaMA models installed
- Git (for cloning the repository)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/pdf-namer.git
cd pdf-namer
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

Basic usage:
```bash
python pdf_renamer.py /path/to/pdf/directory
```

Options:
- `--test-mode`: Run without actually renaming files (recommended for first use)
- `--model`: Specify which LLaMA model to use (default: llama3.1:70b-instruct-q8_0)
- `--all-files`: Process all PDF files regardless of filename pattern

Example with options:
```bash
python pdf_renamer.py --test-mode --model "llama3.1:70b-instruct-q8_0" /path/to/pdfs
```

## File Naming Convention

By default, the script processes files matching the pattern:
`YYYY_MM_DD_HH_MM_SS_*.pdf`

Output format:
`YYYY.MM.DD - Descriptive Name.pdf`

## Development

### Running Tests

```bash
pytest
```

For coverage report:
```bash
pytest --cov=. --cov-report=term-missing
```

### Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the BSD 2-Clause License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- More than 90% of this project was developed using [Aider](https://github.com/Aider-AI/aider), an AI pair programming tool
- Uses the Ollama API for LLaMA model integration
- Built with PyPDF for PDF text extraction
