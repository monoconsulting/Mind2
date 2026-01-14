
import sys
import os

# Add backend/src to path so we can import services
sys.path.append(os.path.join(os.getcwd(), 'backend', 'src'))

from services.invoice_parser import parse_credit_card_statement

def verify_fix():
    print("Verifying fix for FirstCard scanning...")
    
    # 1. Test Merged Lines
    merged_text = "2025-03-05 Amazon 150,00 2025-03-05 Bauhaus 2 579,80"
    print(f"\nInput: '{merged_text}'")
    result = parse_credit_card_statement(merged_text)
    
    print(f"Found {len(result['lines'])} lines.")
    for i, line in enumerate(result['lines']):
        print(f"  Line {i+1}: {line}")
        
    if len(result['lines']) != 2:
        print("FAIL: Expected 2 lines due to merged line splitting.")
        return False
        
    if result['lines'][0]['merchant_name'] != 'Amazon':
        print("FAIL: First merchant should be Amazon.")
        return False
        
    if result['lines'][1]['merchant_name'] != 'Bauhaus':
        print("FAIL: Second merchant should be Bauhaus.")
        return False

    if result['lines'][1]['amount'] != 2579.80:
        print(f"FAIL: Bauhaus amount mismatch. Got {result['lines'][1]['amount']}, expected 2579.80")
        return False

    print("\nSUCCESS: Merged lines and spaced amounts handled correctly!")
    return True

if __name__ == "__main__":
    if verify_fix():
        sys.exit(0)
    else:
        sys.exit(1)
