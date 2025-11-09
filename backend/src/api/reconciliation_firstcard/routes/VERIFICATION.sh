#!/bin/bash
# Verification script for route extraction

echo "=== Route Extraction Verification ==="
echo ""

routes_dir="E:/projects/Mind2/backend/src/api/routes"

echo "1. File existence check:"
for file in log.py upload.py status.py lines.py matching.py statements.py __init__.py; do
    if [ -f "$routes_dir/$file" ]; then
        echo "   ✓ $file exists"
    else
        echo "   ✗ $file MISSING"
    fi
done
echo ""

echo "2. Line count verification:"
echo "   log.py:        $(wc -l < "$routes_dir/log.py") lines (expected ~297)"
echo "   upload.py:     $(wc -l < "$routes_dir/upload.py") lines (expected ~326)"
echo "   status.py:     $(wc -l < "$routes_dir/status.py") lines (expected ~386)"
echo "   lines.py:      $(wc -l < "$routes_dir/lines.py") lines (expected ~337)"
echo "   matching.py:   $(wc -l < "$routes_dir/matching.py") lines (expected ~295)"
echo "   statements.py: $(wc -l < "$routes_dir/statements.py") lines (expected ~510)"
echo ""

echo "3. Encoding header verification:"
for file in log.py upload.py status.py lines.py matching.py statements.py; do
    first_line=$(head -n 1 "$routes_dir/$file")
    second_line=$(head -n 2 "$routes_dir/$file" | tail -n 1)
    if [[ "$first_line" == "# -*- coding: utf-8 -*-" ]] && [[ "$second_line" =~ "Kontrollrad" ]]; then
        echo "   ✓ $file has correct encoding headers"
    else
        echo "   ✗ $file MISSING encoding headers"
    fi
done
echo ""

echo "4. Endpoint decorator count:"
for file in log.py upload.py status.py lines.py matching.py statements.py; do
    count=$(grep -c "@recon_bp\." "$routes_dir/$file")
    echo "   $file: $count endpoint(s)"
done
echo ""

echo "5. Import verification (recon_bp):"
for file in log.py upload.py status.py lines.py matching.py statements.py; do
    if grep -q "from .. import recon_bp" "$routes_dir/$file"; then
        echo "   ✓ $file imports recon_bp"
    else
        echo "   ✗ $file MISSING recon_bp import"
    fi
done
echo ""

echo "=== Verification Complete ==="
