import fitz  # PyMuPDF
def extract_raw_text(file_path: str) -> str:
    """
    Extracts plain text from all pages of a PDF invoice.
    
    Input: Path to a PDF file
    Output: Raw combined text string from all pages
    """
    # Open the PDF file
    document = fitz.open(file_path)
    
    # Initialize an empty string to hold the extracted text
    raw_text = ""
    
    # Iterate through each page and extract text
    for page_num in range(len(document)):
        page = document.load_page(page_num)
        raw_text += page.get_text()
    
    # Close the document
    document.close()
    
    return raw_text