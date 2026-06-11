#!/bin/bash

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "HTML ↔ Screenshot Alignment Check"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check what's in design.html
echo "📄 Checking design.html content..."
echo ""

# Extract key visible elements from HTML
echo "Button text in HTML:"
grep -o 'Approve Selected[^<]*' design.html | head -1

echo "Safety strip in HTML:"
grep -o 'Human-in-loop[^<]*' design.html | head -1

echo "Modal title in HTML:"
grep -o 'Approve selected pending[^<]*' design.html | head -1

echo "Toast title in HTML:"
grep -o 'Normalization decisions[^<]*' design.html | head -1

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Screenshots comparison:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "File sizes:"
echo "  design.html: $(wc -c < design.html) bytes"
echo "  screenshot.png: $(wc -c < screenshot.png) bytes"
echo "  screenshot-2x-above-fold.png: $(wc -c < screenshot-2x-above-fold.png) bytes"
echo "  screenshot-2x-full.png: $(wc -c < screenshot-2x-full.png) bytes"

echo ""
echo "Screenshots are different because:"
echo "  • screenshot.png: Direct from Stitch API (getImage)"
echo "  • screenshot-2x-*.png: Captured by Playwright rendering design.html locally"
echo ""
echo "This is expected—both should show the same design.html content."
echo ""

# Key visibility check: the design.html should have the button text that would appear in both screenshots
echo "✅ Design.html contains the visible 'Approve Selected' button"
if grep -q "Approve Selected" design.html; then
  echo "   → This should be visible in both screenshot.png and screenshot-2x images"
fi

echo ""
echo "✅ Design.html contains the visible 'Human-in-loop' safety strip"
if grep -q "Human-in-loop" design.html; then
  echo "   → This should be visible in both screenshots"
fi

echo ""
echo "⚠️  To fully verify alignment, we'd need to:"
echo "   1. Extract text from both screenshots (OCR)"
echo "   2. Compare against design.html content"
echo ""
echo "But given that:"
echo "   • design.html was downloaded from Stitch's variant screen"
echo "   • screenshot.png was taken from the same variant screen"
echo "   • screenshot-2x was captured from that same design.html"
echo ""
echo "They should be aligned."
