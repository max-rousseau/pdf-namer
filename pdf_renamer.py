import click
import re
import os
from pathlib import Path
import requests
from tqdm import tqdm
import pypdf


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


def generate_new_filename(text: str, original_file: Path) -> str:
    """
    Generates a new filename based on PDF content and date extracted from the original filename.

    Args:
        text (str): The content of the PDF file.
        original_file (Path): The original PDF file.

    Returns:
        str: The new filename.
    """
    # Extract date components from the original filename
    date_match = re.search(r"(\d{4})_(\d{2})_(\d{2})", original_file.name)
    if date_match:
        date_formatted = (
            f"{date_match.group(1)}.{date_match.group(2)}.{date_match.group(3)}"
        )
    else:
        date_formatted = "UnknownDate"

    # Prepare the prompt for the Ollama service
    prompt = (
        "In 30 characters or less, create a summarized file name for the PDF contents supplied. "
        "The file name should start with the date in this format YYYY.MM.DD then space, then dash, "
        "then space again and then the name of the file - for example: 2024.10.11 - Mills Peninsula Water Invoice.PDF."
    )

    # Send the request to the Ollama service
    response = requests.post(
        "http://127.0.0.1:11434/api/generate",
        json={
            "model": "llama3.1:70b-instruct-q8_0",
            "prompt": f"{prompt}\n\n{text}",
            "stream": False,
        },
        timeout=120,
    )
    response.raise_for_status()
    data = response.json()
    if "response" not in data:
        raise ValueError("The API response does not contain the 'response' key.")

    # Construct the new filename
    summarized_name = data["response"].strip()
    new_filename = f"{date_formatted} - {summarized_name}.pdf"

    return new_filename


def process_pdfs(directory: Path, test_mode: bool):
    """
    Processes PDF files in the given directory.

    Args:
        directory (Path): The directory containing PDF files.
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
            new_filename = generate_new_filename(text, pdf_file)
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
def main(scan_directory, test_mode):
    """Process PDF files in the provided directory."""
    process_pdfs(Path(scan_directory), test_mode)


if __name__ == "__main__":
    main()
