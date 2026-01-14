
import re

_LINE_PATTERN = re.compile(
    r"^(20\d{2}-\d{2}-\d{2})\s+(.+?)\s+(-?\d+[.,]\d{2})$",
    re.MULTILINE,
)

def parse_with_current_logic(text):
    print(f"--- Parsing: '{text}' ---")
    match = _LINE_PATTERN.search(text)
    if match:
        d, m, a = match.groups()
        print(f"MATCH FOUND!")
        print(f"  Date:     {d}")
        print(f"  Merchant: {m}")
        print(f"  Amount:   {a}")
        return d, m, a
    else:
        print("POOR MATCH (No regex match)")
        return None

def test_merged_lines_amazon_bauhaus():
    # Scenario:
    # Line 1: 2025-03-05 Amazon 150,00
    # Line 2: 2025-03-05 Bauhaus 2 579,80
    # OCR merges them into one line.
    
    # Case A: Strict merge
    text_a = "2025-03-05 Amazon 150,00 2025-03-05 Bauhaus 2 579,80"
    
    # Case B: With typical OCR spacing
    text_b = "2025-03-05 Amazon 150,00   2025-03-05 Bauhaus 2 579,80"

    print("\n>>> TEST CASE A: Merged Lines (Amazon + Bauhaus)")
    parse_with_current_logic(text_a)

    print("\n>>> TEST CASE B: Merged Lines with extra space")
    parse_with_current_logic(text_b)

def test_proposed_fix_logic(text):
    print(f"\n--- Proposed Logic on: '{text}' ---")
    # 1. Pre-process: Split dates that aren't at start of line
    # Insert newline before YYYY-MM-DD if likely a new line
    
    # Look for YYYY-MM-DD that is NOT at the start of the string
    # We can replace " (20\d{2}-)" with "\n\1"
    
    fixed_text = re.sub(r"(\s)(20\d{2}-\d{2}-\d{2})", r"\n\2", text)
    print(f"Post-processing text:\n{fixed_text}")
    
    # 2. Iterate lines
    for line in fixed_text.split('\n'):
        if not line.strip(): continue
        # 3. Enhanced Regex for amounts with spaces
        # Note: We need to handle the space inside the amount group
        pattern = re.compile(r"^(20\d{2}-\d{2}-\d{2})\s+(.+?)\s+(-?[\d\s]+[.,]\d{2})$")
        match = pattern.search(line.strip())
        if match:
            d, m, a = match.groups()
            print(f"  Found Line -> Date: {d}, Merch: {m}, Amt: {a}")
        else:
            print(f"  No match for line: {line}")

if __name__ == "__main__":
    test_merged_lines_amazon_bauhaus()
    
    print("\n\n>>> TESTING FIX <<<")
    text_merge = "2025-03-05 Amazon 150,00 2025-03-05 Bauhaus 2 579,80"
    test_proposed_fix_logic(text_merge)
