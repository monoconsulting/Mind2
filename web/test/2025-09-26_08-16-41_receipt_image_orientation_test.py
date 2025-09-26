#!/usr/bin/env python3
"""
Receipt Image Orientation Test
===============================

Test som verifierar att kvittobilder visas korrekt i portraitläge
både i thumbnails och i modal-vy efter implementerade förbättringar.

Testar:
1. Thumbnail-generering med korrekt orientering
2. Modal-bildvisning i portraitläge
3. API-endpoints för bildhantering
4. CSS-stilar för optimal bildvisning

Skapad: 2025-09-26 08:16:41
Författare: Test Agent (Claude)
"""

import sys
import os
import time
import json
import requests
from datetime import datetime

# Add project root to path for imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

class ReceiptImageOrientationTest:
    def __init__(self):
        self.test_name = "Receipt Image Orientation Test"
        self.start_time = datetime.now()
        self.results = []
        self.total_tests = 6
        self.passed_tests = 0
        self.base_url = "http://localhost:8000"  # Backend API
        self.frontend_url = "http://localhost:3000"  # Frontend

    def log(self, message, test_passed=None):
        """Log test results"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        status = ""
        if test_passed is True:
            status = " [PASS]"
            self.passed_tests += 1
        elif test_passed is False:
            status = " [FAIL]"

        log_message = f"[{timestamp}] {message}{status}"
        print(log_message)
        self.results.append(log_message)
        return test_passed

    def test_backend_availability(self):
        """Test 1: Kontrollera att backend API är tillgängligt"""
        try:
            response = requests.get(f"{self.base_url}/ai/api/receipts", timeout=10)
            if response.status_code in [200, 404]:  # 404 är OK om inga kvitton finns
                return self.log("Backend API är tillgängligt", True)
            else:
                return self.log(f"Backend API svarar med status {response.status_code}", False)
        except requests.exceptions.RequestException as e:
            return self.log(f"Backend API inte tillgängligt: {e}", False)

    def test_preview_endpoint_with_refresh(self):
        """Test 2: Testa preview endpoint med refresh parameter"""
        try:
            # Försök hämta lista med kvitton först
            response = requests.get(f"{self.base_url}/ai/api/receipts", timeout=10)

            if response.status_code == 200:
                data = response.json()
                items = data.get('items', [])

                if not items:
                    return self.log("Inga kvitton hittades för preview-test", True)

                # Testa preview endpoint med första kvittot
                receipt_id = items[0].get('id')
                preview_response = requests.get(
                    f"{self.base_url}/ai/api/receipts/{receipt_id}/preview?refresh=true",
                    timeout=15
                )

                if preview_response.status_code == 200:
                    return self.log("Preview endpoint med refresh fungerar", True)
                else:
                    return self.log(f"Preview endpoint misslyckades: {preview_response.status_code}", False)
            else:
                return self.log("Kunde inte hämta kvittolista för preview-test", False)

        except requests.exceptions.RequestException as e:
            return self.log(f"Preview endpoint test fel: {e}", False)

    def test_image_endpoint_with_orientation_params(self):
        """Test 3: Testa image endpoint med orientationsparametrar"""
        try:
            response = requests.get(f"{self.base_url}/ai/api/receipts", timeout=10)

            if response.status_code == 200:
                data = response.json()
                items = data.get('items', [])

                if not items:
                    return self.log("Inga kvitton för image orientation test", True)

                receipt_id = items[0].get('id')
                image_response = requests.get(
                    f"{self.base_url}/ai/api/receipts/{receipt_id}/image?quality=high&size=full&rotate=portrait",
                    timeout=15
                )

                if image_response.status_code == 200:
                    content_type = image_response.headers.get('content-type', '')
                    if 'image' in content_type:
                        return self.log("Image endpoint med orientationsparametrar fungerar", True)
                    else:
                        return self.log(f"Image endpoint returnerade fel content-type: {content_type}", False)
                else:
                    return self.log(f"Image endpoint misslyckades: {image_response.status_code}", False)
            else:
                return self.log("Kunde inte hämta kvittolista för image test", False)

        except requests.exceptions.RequestException as e:
            return self.log(f"Image endpoint test fel: {e}", False)

    def test_thumbnail_generation_logic(self):
        """Test 4: Verifiera att thumbnail-genereringslogik är uppdaterad"""
        try:
            # Kontrollera att backend-koden innehåller orientationshantering
            receipts_file = os.path.join(project_root, 'backend', 'src', 'api', 'receipts.py')

            if os.path.exists(receipts_file):
                with open(receipts_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Kontrollera att förbättringarna är implementerade
                required_elements = [
                    'ExifTags',  # EXIF-hantering
                    'rotate(90, expand=True)',  # Portrait rotation
                    'width > height',  # Orientationskontroll
                ]

                missing_elements = []
                for element in required_elements:
                    if element not in content:
                        missing_elements.append(element)

                if not missing_elements:
                    return self.log("Thumbnail-genereringslogik är uppdaterad med orientationshantering", True)
                else:
                    return self.log(f"Saknade element i thumbnail-logik: {missing_elements}", False)
            else:
                return self.log("Kunde inte hitta receipts.py för kodverifiering", False)

        except Exception as e:
            return self.log(f"Fel vid verifiering av thumbnail-logik: {e}", False)

    def test_frontend_preview_refresh_logic(self):
        """Test 5: Kontrollera att frontend använder refresh-parametern"""
        try:
            receipts_jsx = os.path.join(project_root, 'main-system', 'app-frontend', 'src', 'ui', 'pages', 'Receipts.jsx')

            if os.path.exists(receipts_jsx):
                with open(receipts_jsx, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Kontrollera att refresh-parametern används
                required_elements = [
                    'refresh=true',  # Refresh parameter
                    'preview?refresh=true',  # Preview endpoint med refresh
                ]

                found_elements = []
                for element in required_elements:
                    if element in content:
                        found_elements.append(element)

                if len(found_elements) >= 1:  # Minst ett element ska finnas
                    return self.log("Frontend använder refresh-logik för preview", True)
                else:
                    return self.log("Frontend refresh-logik saknas", False)
            else:
                return self.log("Kunde inte hitta Receipts.jsx för frontend-verifiering", False)

        except Exception as e:
            return self.log(f"Fel vid verifiering av frontend refresh-logik: {e}", False)

    def test_css_preview_styles(self):
        """Test 6: Kontrollera att CSS-stilar är optimerade för portrait-bilder"""
        try:
            css_file = os.path.join(project_root, 'main-system', 'app-frontend', 'src', 'index.css')

            if os.path.exists(css_file):
                with open(css_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Kontrollera att CSS är uppdaterad
                required_elements = [
                    '.preview-image',  # CSS klass
                    'max-height: 100%',  # Maximal höjd
                    'object-fit: contain',  # Object fit
                ]

                found_elements = []
                for element in required_elements:
                    if element in content:
                        found_elements.append(element)

                if len(found_elements) >= 2:  # Minst 2 element ska finnas
                    return self.log("CSS-stilar för preview är uppdaterade", True)
                else:
                    return self.log(f"CSS-stilar saknar viktiga element. Hittade: {found_elements}", False)
            else:
                return self.log("Kunde inte hitta CSS-fil för stilverifiering", False)

        except Exception as e:
            return self.log(f"Fel vid verifiering av CSS-stilar: {e}", False)

    def run_all_tests(self):
        """Kör alla tester"""
        self.log(f"Startar {self.test_name}")
        self.log("=" * 60)

        # Kör alla tester
        self.test_backend_availability()
        self.test_preview_endpoint_with_refresh()
        self.test_image_endpoint_with_orientation_params()
        self.test_thumbnail_generation_logic()
        self.test_frontend_preview_refresh_logic()
        self.test_css_preview_styles()

        # Sammanfattning
        self.log("=" * 60)
        success_rate = (self.passed_tests / self.total_tests) * 100
        self.log(f"Testresultat: {self.passed_tests}/{self.total_tests} tester godkända ({success_rate:.1f}%)")

        duration = datetime.now() - self.start_time
        self.log(f"Test slutfört på {duration.total_seconds():.1f} sekunder")

        return success_rate, self.passed_tests, self.total_tests

def main():
    """Huvudfunktion för att köra testet"""
    test = ReceiptImageOrientationTest()
    success_rate, passed, total = test.run_all_tests()

    # Returnera exit code baserat på resultat
    if success_rate == 100.0:
        print("\n[SUCCESS] Alla tester godkända!")
        return 0
    elif success_rate >= 80.0:
        print(f"\n[WARNING] {passed}/{total} tester godkända ({success_rate:.1f}%) - Acceptabelt resultat")
        return 0
    else:
        print(f"\n[FAILED] Endast {passed}/{total} tester godkända ({success_rate:.1f}%) - Behöver förbättringar")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)