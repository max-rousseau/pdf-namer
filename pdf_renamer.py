"""
Module: pdf_renamer

Purpose:
    CLI tool that renames PDF files using a locally running Ollama LLM instance.
    Text is extracted from each PDF and sent to the model, which returns a
    structured JSON response containing a descriptive filename and an inferred
    document date. The file is then renamed to ``YYYY.MM.DD - Description.pdf``.

Classes:
    None

Functions:
    - calculate_context_window: Determine the num_ctx value to send to Ollama.
    - extract_pdf_text: Read all text from a PDF file.
    - generate_new_filename: Query the LLM and parse a (date, filename) tuple.
    - format_filename: Assemble the final filename string from date and name parts.
    - process_pdfs: Iterate over PDFs in a directory and rename them.

Usage Example:
    pdf-namer /path/to/directory
    pdf-namer --test-mode --model gemma3:27b /path/to/directory
    pdf-namer --all-files --backup-model gemma3:27b /path/to/directory

Happy Path Flow:

```mermaid
sequenceDiagram
    participant User
    participant CLI as pdf-namer (CLI)
    participant Extractor as extract_pdf_text
    participant LLM as Ollama (local)
    participant FS as Filesystem

    User->>CLI: pdf-namer /docs
    CLI->>FS: list PDF files
    FS-->>CLI: [2024_01_15_report.pdf, ...]
    CLI->>Extractor: extract_pdf_text(pdf_path)
    Extractor-->>CLI: raw text
    CLI->>LLM: POST /api/generate (prompt + text)
    LLM-->>CLI: {"date": "2024.01.15", "filename": "Verizon MyBill"}
    CLI->>FS: rename to "2024.01.15 - Verizon MyBill.pdf"
    FS-->>CLI: ok
    CLI-->>User: "File renamed successfully"
```
"""

import click
import re
import json
import time
from pathlib import Path
import requests
import pypdf
from click import style

DEFAULT_MODEL = "gemma4:31b"
MODEL_CONTEXT_MAP = {
    "llama3.1:70b-instruct-q8_0": 128000,
    "llama3.2:3b-instruct-fp16": 128000,
    "llama3.1:8b-instruct-fp16": 128000,
    "gemma3:27b": 128000,
    "gemma4:31b": 128000,
}


def calculate_context_window(model: str, prompt: str) -> int:
    """Calculate the num_ctx value to request from Ollama for a given prompt.

    Adds a fixed 1000-character buffer to the prompt length to leave room for
    the model's JSON response, then caps the result at the model's maximum
    supported context size. Falls back to 2048 for unrecognised models.

    Args:
        model: Ollama model tag, e.g. ``"gemma4:31b"``.
        prompt: The fully-formatted prompt string that will be sent to Ollama.

    Returns:
        The context window size to pass as ``num_ctx`` in the Ollama request.

    Example:
        >>> calculate_context_window("gemma4:31b", "x" * 500)
        1500
    """
    try:
        prompt_length = len(prompt)

        # Get max context size for model, default to 2048 if not found
        max_context = MODEL_CONTEXT_MAP.get(model, 2048)

        # Return the minimum required size, capped at model's max
        return min(
            prompt_length + 1000, max_context
        )  # Add 1000 tokens buffer for response
    except Exception as e:
        print(f"Error calculating context window: {str(e)}")
        return 2048  # Return default size on error


def extract_pdf_text(pdf_path: Path) -> str:
    """Extract all text from a PDF file by concatenating every page.

    Args:
        pdf_path: Path to the PDF file to read.

    Returns:
        A single string containing the concatenated text of all pages.
        Pages that yield no text contribute an empty string.

    Raises:
        pypdf.errors.PdfReadError: If the file is corrupted or not a valid PDF.
        OSError: If the file cannot be opened.

    Example:
        >>> text = extract_pdf_text(Path("invoice.pdf"))
        >>> print(text[:80])
        'Invoice #1234 ...'
    """
    text = ""
    with pdf_path.open("rb") as file:
        reader = pypdf.PdfReader(file)
        for page in reader.pages:
            text += page.extract_text() or ""
    return text


FAILED_DATE = "YYYY.MM.DD"
FAILED_FILENAME = "Unknown Document"


def generate_new_filename(text: str, original_file: Path, model: str) -> tuple:
    """Query Ollama to produce a descriptive filename and date for a PDF.

    Reads ``prompt.md`` from the current working directory, formats it with
    the extracted PDF text, and sends the request to the local Ollama API at
    ``http://127.0.0.1:11434``. The model is expected to return a JSON object
    with exactly two keys: ``"date"`` and ``"filename"``.

    When the model cannot determine a date, ``FAILED_DATE`` (``"YYYY.MM.DD"``)
    is used as the date component. When the filename is absent or contains
    ``"unknown"``, ``FAILED_FILENAME`` (``"Unknown Document"``) is substituted.
    Filenames longer than 80 characters (including the date and separator) are
    truncated with an ellipsis.

    Args:
        text: Full text extracted from the PDF, used as the prompt body.
        original_file: Path to the original PDF file (used for logging only).
        model: Ollama model tag to use, e.g. ``"gemma4:31b"``.

    Returns:
        A ``(date, filename)`` tuple on success, or ``None`` if the API
        response is missing, malformed, or cannot be parsed.

    Raises:
        requests.exceptions.RequestException: On network or HTTP errors when
            contacting the Ollama API.
        FileNotFoundError: If ``prompt.md`` does not exist in the working
            directory.

    Example:
        >>> result = generate_new_filename(text, Path("scan.pdf"), "gemma4:31b")
        >>> result
        ('2024.03.15', 'Verizon MyBill')
    """
    # Read the prompt from 'prompt.md'
    prompt_path = Path("prompt.md")
    prompt = prompt_path.read_text()
    prompt = prompt.format(text=text)

    print(style("=" * 50, fg="blue"))
    print(style(f"Prompt Analysis ({model})", fg="green", bold=True))

    # Calculate required context window
    context_window = calculate_context_window(model, prompt)

    print(
        f"Sending prompt to Ollama (length: {len(prompt)} characters, context window: {context_window})"
    )

    # Send the request to the Ollama service and measure time
    start_time = time.time()
    response = requests.post(
        "http://127.0.0.1:11434/api/generate",
        json={
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.5, "num_ctx": context_window},
            "format": "json",
        },
        timeout=600,
    )
    response.raise_for_status()
    elapsed_time = time.time() - start_time
    print(f"Received response from Ollama in {elapsed_time:.2f} seconds")
    print(style("=" * 50, fg="blue"))
    try:
        data = response.json()
        if "response" not in data:
            print(
                f"Error: The API response does not contain the 'response' key.\n{data}"
            )
            return None

        # Parse the JSON response
        try:
            data = json.loads(data["response"])
        except json.JSONDecodeError:
            print("Error: Invalid JSON response from API")
            return None

        # Validate JSON structure
        expected_keys = {"date", "filename"}
        actual_keys = set(data.keys())

        if not expected_keys.issubset(actual_keys):
            missing_keys = expected_keys - actual_keys
            print(f"Error: Missing required keys in response: {missing_keys}\n{data}")
            return None

        if actual_keys != expected_keys:
            extra_keys = actual_keys - expected_keys
            print(f"Error: Unexpected extra keys in response: {extra_keys}\n{data}")
            return None

        # Clean and validate the summarized name
        date = data["date"].strip() if data["date"] else FAILED_DATE
        filename = data["filename"].strip()
        if not filename or "unknown" in filename.lower():
            filename = FAILED_FILENAME

        # Truncate filename if too long (accounting for date and separator)
        max_length = 80
        date_and_sep_len = len(date) + 3  # date + " - "
        if len(filename) > max_length - date_and_sep_len:
            filename = filename[: max_length - date_and_sep_len - 3] + "..."

        return (date, filename)
    except Exception as e:
        print(f"Error generating filename: {str(e)}")
        return None


def format_filename(date: str, filename: str) -> str:
    """Assemble the final filename string from a date and a name part.

    Joins ``date`` and ``filename`` with `` - ``, strips any trailing ``.pdf``
    suffix that may have been included in the LLM response, and removes a
    trailing ellipsis (``...``) left by truncation logic in
    ``generate_new_filename``.

    Args:
        date: Document date string in ``YYYY.MM.DD`` format, or the sentinel
            ``"YYYY.MM.DD"`` when the date could not be determined.
        filename: Descriptive name part, without extension.

    Returns:
        A filename string without extension, ready to have ``.pdf`` appended
        before writing to disk.

    Example:
        >>> format_filename("2024.03.15", "Verizon MyBill")
        '2024.03.15 - Verizon MyBill'
    """
    name = f"{date} - {filename}"
    name = name.replace(".pdf", "")
    if name.endswith("..."):
        name = name[:-3].rstrip()
    return name


def process_pdfs(directory: Path, test_mode: bool, model: str, all_files: bool = False, backup_model: str = None):
    """Process and rename PDF files in a directory using LLM-generated names.

    By default, only files whose names contain a timestamp in the format
    ``YYYY_MM_DD_HH_MM_SS`` are processed. Pass ``all_files=True`` to process
    every PDF in the directory.

    For each file, ``extract_pdf_text`` and ``generate_new_filename`` are
    called. If either the date or the filename component of the primary model's
    response is a failure sentinel and ``backup_model`` is provided, the backup
    model is queried and its successful fields are merged into the result.

    In test mode the user is prompted to confirm each rename interactively.
    In normal mode files are renamed immediately.

    Args:
        directory: Directory to scan for PDF files.
        test_mode: When ``True``, prompt the user before each rename instead
            of renaming automatically.
        model: Primary Ollama model tag, e.g. ``"gemma4:31b"``.
        all_files: When ``True``, process every PDF regardless of filename
            pattern. When ``False`` (default), skip files that do not match
            the ``YYYY_MM_DD_HH_MM_SS`` timestamp pattern.
        backup_model: Optional Ollama model tag used as a fallback when the
            primary model returns a failure sentinel for ``date`` or
            ``filename``. Only the failed fields are replaced; successful
            fields from the primary model are preserved.

    Raises:
        requests.exceptions.RequestException: Propagated per-file on network
            failure; the file is skipped and processing continues.
    """
    # Get all PDF files first
    pdf_files = [
        file
        for file in directory.iterdir()
        if file.is_file() and file.suffix.lower() == ".pdf"
    ]

    if not pdf_files:
        print(style("No PDF files found in the directory", fg="yellow"))
        return

    # Filter by date pattern if not processing all files
    if not all_files:
        date_pattern = re.compile(r"\d{4}_\d{2}_\d{2}_\d{2}_\d{2}_\d{2}")
        pdf_files = [file for file in pdf_files if date_pattern.search(file.name)]
        if not pdf_files:
            print(
                style(
                    "No PDF files found matching the required date pattern format (YYYY_MM_DD_HH_MM_SS)",
                    fg="yellow",
                )
            )
            return

    # Process each PDF file
    for pdf_file in pdf_files:
        print(style("=" * 50, fg="blue"))
        print(style(f"Processing {pdf_file.name}", fg="green", bold=True))
        try:
            text = extract_pdf_text(pdf_file)
            result = generate_new_filename(text, pdf_file, model)
            if not result:
                print(f"Error processing {pdf_file.name}. Ignoring.")
                continue

            date, filename = result
            has_bad_date = date == FAILED_DATE
            has_bad_filename = filename == FAILED_FILENAME

            # Retry with backup model if there's any failure
            if backup_model and (has_bad_date or has_bad_filename):
                print(style(f"Partial/total failure detected, retrying with backup model: {backup_model}", fg="yellow"))
                backup_result = generate_new_filename(text, pdf_file, backup_model)
                if backup_result:
                    backup_date, backup_filename = backup_result
                    if has_bad_date and backup_date != FAILED_DATE:
                        date = backup_date
                    if has_bad_filename and backup_filename != FAILED_FILENAME:
                        filename = backup_filename

            new_filename = format_filename(date, filename)

            print(f"Original filename:\t{pdf_file.name}")
            print(f"New filename:\t{new_filename}")

            if test_mode:
                if click.confirm("Do you want to rename this file?", default=False):
                    pdf_file.rename(directory / f"{new_filename}.pdf")
                    print(style("File renamed successfully", fg="green"))
                else:
                    print(style("Skipping file rename in test mode", fg="yellow"))
            else:
                pdf_file.rename(directory / f"{new_filename}.pdf")
                print(style("File renamed successfully", fg="green"))

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
@click.option(
    "--all-files",
    is_flag=True,
    help="Process all PDF files in the directory, regardless of filename pattern.",
)
@click.option(
    "--backup-model",
    default=None,
    help="Backup model to retry when the primary model fails to extract date or filename.",
)
def main(scan_directory, test_mode, model, all_files, backup_model):
    """Process PDF files in the provided directory."""
    process_pdfs(Path(scan_directory), test_mode, model, all_files, backup_model)


if __name__ == "__main__":
    main()
