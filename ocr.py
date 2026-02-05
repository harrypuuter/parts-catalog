"""OCR module for extracting text from images using EasyOCR."""

import re
import easyocr

# Initialize reader once (lazy loading)
_reader = None


def get_reader():
    """Get or create EasyOCR reader instance."""
    global _reader
    if _reader is None:
        # Initialize with English; add more languages as needed
        _reader = easyocr.Reader(['en'], gpu=False)
    return _reader


def extract_text(image_path):
    """
    Extract text from an image file.

    Args:
        image_path: Path to the image file

    Returns:
        List of dicts with 'text' and 'confidence' keys,
        sorted by confidence (highest first)
    """
    reader = get_reader()
    results = reader.readtext(image_path)

    # Format results: [(bbox, text, confidence), ...]
    extracted = []
    for bbox, text, confidence in results:
        text = text.strip()
        if text:  # Skip empty strings
            extracted.append({
                'text': text,
                'confidence': round(confidence * 100, 1)
            })

    # Sort by confidence descending
    extracted.sort(key=lambda x: x['confidence'], reverse=True)

    return extracted


def is_likely_code(text):
    """
    Determine if text looks like a part code/identifier.

    Part codes typically:
    - Are short (under 20 characters)
    - Contain alphanumeric characters with optional separators (-, _, .)
    - Have a mix of letters and numbers, or are purely numeric
    - Don't look like natural language (few spaces, no common words)

    Returns:
        Tuple of (is_code: bool, score: float)
        Score indicates how "code-like" the text is (0-100)
    """
    text = text.strip()

    # Too long for a code
    if len(text) > 25:
        return False, 0

    # Too short to be meaningful
    if len(text) < 2:
        return False, 0

    # Multiple spaces suggest description text
    if text.count(' ') > 2:
        return False, 0

    # Calculate code-likeness score
    score = 50  # Start neutral

    # Alphanumeric with separators pattern (e.g., P-1234, ABC_123, A1.B2)
    code_pattern = re.compile(r'^[A-Za-z0-9][-_./A-Za-z0-9]*[A-Za-z0-9]$|^[A-Za-z0-9]$')
    if code_pattern.match(text.replace(' ', '')):
        score += 20

    # Contains digits - very common in part codes
    digit_ratio = sum(c.isdigit() for c in text) / len(text)
    if digit_ratio > 0:
        score += min(30, digit_ratio * 40)

    # Has separators like dashes or underscores (common in codes)
    if re.search(r'[-_./]', text):
        score += 15

    # Short length is more code-like
    if len(text) <= 10:
        score += 15
    elif len(text) <= 15:
        score += 5

    # All uppercase or mixed case with numbers suggests code
    if text.isupper() or (any(c.isupper() for c in text) and any(c.isdigit() for c in text)):
        score += 10

    # Penalize if it looks like natural language
    lowercase_words = len(re.findall(r'\b[a-z]{3,}\b', text))
    if lowercase_words > 0:
        score -= lowercase_words * 15

    # Common description words
    description_words = ['the', 'and', 'for', 'with', 'from', 'this', 'that', 'part', 'type', 'size', 'model']
    for word in description_words:
        if word in text.lower().split():
            score -= 20

    is_code = score >= 50
    return is_code, max(0, min(100, score))


def categorize_text(extracted_texts):
    """
    Categorize extracted text into codes and descriptions.

    Args:
        extracted_texts: List of dicts with 'text' and 'confidence' keys

    Returns:
        Dict with 'codes' and 'descriptions' lists, each containing
        dicts with 'text', 'confidence', and 'code_score' keys
    """
    codes = []
    descriptions = []

    for item in extracted_texts:
        is_code, code_score = is_likely_code(item['text'])
        enriched = {
            'text': item['text'],
            'confidence': item['confidence'],
            'code_score': code_score
        }

        if is_code:
            codes.append(enriched)
        else:
            descriptions.append(enriched)

    # Sort codes by code_score (most code-like first), then by confidence
    codes.sort(key=lambda x: (x['code_score'], x['confidence']), reverse=True)

    # Sort descriptions by confidence
    descriptions.sort(key=lambda x: x['confidence'], reverse=True)

    return {
        'codes': codes,
        'descriptions': descriptions
    }


def extract_and_categorize(image_path, min_confidence=30):
    """
    Extract text from image and categorize into codes and descriptions.

    Args:
        image_path: Path to the image file
        min_confidence: Minimum confidence threshold (0-100)

    Returns:
        Dict with 'codes' and 'descriptions' lists
    """
    results = extract_text(image_path)

    # Filter by confidence
    filtered = [r for r in results if r['confidence'] >= min_confidence]

    return categorize_text(filtered)


# Keep old function for backwards compatibility
def extract_text_candidates(image_path, min_confidence=30):
    """
    Extract text candidates suitable for part codes.

    Args:
        image_path: Path to the image file
        min_confidence: Minimum confidence threshold (0-100)

    Returns:
        List of text strings above the confidence threshold
    """
    results = extract_text(image_path)
    return [
        r for r in results
        if r['confidence'] >= min_confidence
    ]
