import click
import re
import json
from pathlib import Path
import requests
from tqdm import tqdm
import pypdf

DEFAULT_MODEL = "llama3.1:70b-instruct-q8_0"


def extract_pdf_text(pdf_path: Path) -> str:
    """
    Extracts text from a PDF file.

    Args:
        pdf_path (Path): Path to the PDF file.

    Returns:
        str: Extracted text.
    """
    text = ""
    with pdf_path.open("rb") as file:
        reader = pypdf.PdfReader(file)
        for page in reader.pages:
            text += page.extract_text() or ""
    return text


def generate_new_filename(text: str, original_file: Path, model: str) -> str:
    """
    Generates a new filename based on PDF content and date extracted from the original filename.

    Args:
        text (str): The content of the PDF file.
        original_file (Path): The original PDF file.
        model (str): The LLM model to use for generating filenames.

    Returns:
        str: The new filename.
    """

    max_summarized_length = 17

    # Prepare the prompt for the Ollama service
    prompt = "sample prompt"

    # Send the request to the Ollama service
    response = requests.post(
        "http://127.0.0.1:11434/api/generate",
        json={
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.5},
            "format": "json",
        },
        timeout=300,
    )
    response.raise_for_status()
    data = response.json()
    if "response" not in data:
        raise ValueError("The API response does not contain the 'response' key.")
    else:
        data = json.loads(data["response"])
    # Clean and validate the summarized name
    summarized_name = f"{data['date'].strip()} - {data['filename'].strip()}"

    # Construct the new filename
    return summarized_name


def process_pdfs(directory: Path, test_mode: bool, model: str):
    """
    Processes PDF files in the given directory.

    Args:
        directory (Path): The directory containing PDF files.
        test_mode (bool): Whether to run in test mode without renaming
        model (str): The LLM model to use for generating filenames
    """
    # Regular expression to match the date pattern
    date_pattern = re.compile(r"\d{4}_\d{2}_\d{2}_\d{2}_\d{2}_\d{2}")

    # Find all PDF files matching the date pattern
    pdf_files = [
        file
        for file in directory.iterdir()
        if file.is_file()
        and file.suffix.lower() == ".pdf"
        and date_pattern.search(file.name)
    ]

    # Process each PDF file with a progress bar
    for pdf_file in tqdm(pdf_files, desc="Processing PDFs"):
        try:
            text = extract_pdf_text(pdf_file)
            new_filename = generate_new_filename(text, pdf_file, model)
            if not new_filename:
                print(f"Error processing {pdf_file.name}. Ignoring.")
            if test_mode:
                print(f"Original filename: {pdf_file.name}")
                print(f"New filename: {new_filename}")
            else:
                pdf_file.rename(directory / new_filename)
        except requests.exceptions.RequestException as e:
            print(f"Network error processing {pdf_file.name}: {e}")
        except Exception as e:
            print(f"Error processing {pdf_file.name}: {e}")


@click.command()
@click.argument("scan_directory", type=click.Path(exists=True, file_okay=False))
@click.option(
    "--test-mode", is_flag=True, help="Run in test mode without renaming files."
)
@click.option(
    "--model",
    default=DEFAULT_MODEL,
    help="Specify the LLM model to use for generating filenames.",
)
def main(scan_directory, test_mode, model):
    """Process PDF files in the provided directory."""
    process_pdfs(Path(scan_directory), test_mode, model)


if __name__ == "__main__":
    main()
