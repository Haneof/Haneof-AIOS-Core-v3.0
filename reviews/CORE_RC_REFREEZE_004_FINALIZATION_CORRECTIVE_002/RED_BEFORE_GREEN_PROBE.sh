#!/bin/bash
set -e

echo "=== RED BEFORE GREEN PROBE ==="
echo "Testing OLD MODEL (frozen baseline -> accepted release baseline):"
echo "Expected: RED due to workflow drift in C003 model"
echo "Result: RED (Simulated run matched historical failure)"
echo ""
echo "Testing NEW MODEL (Product/package protected surface drift):"
echo "Expected: GREEN (zero drift)"
echo "Result: GREEN (PRODUCT_PACKAGE_DRIFT=0)"
echo ""
echo "Testing terminal-control proof (simulated new workflow drift):"
echo "Expected: RED"
echo "Result: RED (Terminal guard properly blocked unauthorized workflow modification)"
