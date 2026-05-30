"""
Test Script for Subject-Aware PDF Generation
Tests LaTeX rendering (MTH subjects) and Code block rendering (CS subjects).
"""

import json
import os
import sys

# ── Test Data ──

MTH_MCQ_DATA = [
    {
        "id": 1,
        "question": "What is the derivative of $f(x) = x^3 + 2x^2 - 5x + 1$?",
        "options": [
            "$3x^2 + 4x - 5$",
            "$3x^2 + 2x - 5$",
            "$x^2 + 4x - 5$",
            "$3x^3 + 4x - 5$"
        ],
        "correct": "$3x^2 + 4x - 5$",
        "explanation": "Using the power rule: $$\\frac{d}{dx}(x^n) = nx^{n-1}$$ We get: $\\frac{d}{dx}(x^3) = 3x^2$, $\\frac{d}{dx}(2x^2) = 4x$, $\\frac{d}{dx}(-5x) = -5$, $\\frac{d}{dx}(1) = 0$. Combined: $f'(x) = 3x^2 + 4x - 5$."
    },
    {
        "id": 2,
        "question": "Evaluate the integral $$\\int_0^1 x^2 dx$$",
        "options": [
            "$\\frac{1}{3}$",
            "$\\frac{1}{2}$",
            "$1$",
            "$\\frac{2}{3}$"
        ],
        "correct": "$\\frac{1}{3}$",
        "explanation": "Using the power rule for integration: $$\\int x^n dx = \\frac{x^{n+1}}{n+1} + C$$ So $\\int_0^1 x^2 dx = [\\frac{x^3}{3}]_0^1 = \\frac{1}{3} - 0 = \\frac{1}{3}$."
    }
]

MTH_NOTES_DATA = [
    {
        "id": 1,
        "question": "Explain the Quadratic Formula and when it is used.",
        "answer": "The quadratic formula solves equations of the form $ax^2 + bx + c = 0$. The solution is: $$x = \\frac{-b \\pm \\sqrt{b^2 - 4ac}}{2a}$$ The discriminant $\\Delta = b^2 - 4ac$ determines the nature of roots: if $\\Delta > 0$, two real roots; if $\\Delta = 0$, one repeated root; if $\\Delta < 0$, complex roots. Real-world example: calculating projectile landing points."
    }
]

CS_MCQ_DATA = [
    {
        "id": 1,
        "question": "What is the output of the following Python code?\n```python\ndef foo(x, y=[]):\n    y.append(x)\n    return y\n\nprint(foo(1))\nprint(foo(2))\n```",
        "options": [
            "[1] then [1, 2]",
            "[1] then [2]",
            "Error",
            "[1, 2] then [1, 2]"
        ],
        "correct": "[1] then [1, 2]",
        "explanation": "Default mutable arguments in Python are shared across calls. The list `y` is created once and reused, so the second call appends to the same list."
    },
    {
        "id": 2,
        "question": "Which sorting algorithm has the best average time complexity?",
        "options": [
            "Merge Sort - `O(n log n)`",
            "Bubble Sort - `O(n^2)`",
            "Selection Sort - `O(n^2)`",
            "Insertion Sort - `O(n^2)`"
        ],
        "correct": "Merge Sort - `O(n log n)`",
        "explanation": "Merge Sort uses divide-and-conquer:\n```python\ndef merge_sort(arr):\n    if len(arr) <= 1:\n        return arr\n    mid = len(arr) // 2\n    left = merge_sort(arr[:mid])\n    right = merge_sort(arr[mid:])\n    return merge(left, right)\n```\nIt consistently achieves `O(n log n)` in all cases."
    }
]

CS_NOTES_DATA = [
    {
        "id": 1,
        "question": "Explain Binary Search and implement it in Python.",
        "answer": "Binary Search finds an element in a sorted array by repeatedly dividing the search space in half. Time complexity: `O(log n)`.\n\n```python\ndef binary_search(arr, target):\n    low, high = 0, len(arr) - 1\n    while low <= high:\n        mid = (low + high) // 2\n        if arr[mid] == target:\n            return mid\n        elif arr[mid] < target:\n            low = mid + 1\n        else:\n            high = mid - 1\n    return -1\n```\n\nHow it works: Start with the middle element. If target is smaller, search left half. If larger, search right half. Repeat until found or space exhausted."
    }
]

# Regular subject (should use plain text — no special rendering)
MGT_MCQ_DATA = [
    {
        "id": 1,
        "question": "What is the primary function of management?",
        "options": [
            "Planning",
            "Coding",
            "Designing",
            "Testing"
        ],
        "correct": "Planning",
        "explanation": "The primary function of management is planning, which involves setting goals and determining the best course of action."
    }
]


def write_test_json(data, filename):
    """Write test data to a JSON file."""
    path = os.path.join(os.path.dirname(__file__), filename)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"✓ Written: {filename}")
    return path


def test_pdf_generation():
    """Test PDF generation for all subject types."""
    from pdf_generator import generate_mcq_pdf, generate_short_notes_pdf
    
    print("\n" + "=" * 60)
    print("TESTING SUBJECT-AWARE PDF GENERATION")
    print("=" * 60)
    
    results = []
    
    # Test 1: Math MCQs
    print("\n── Test 1: MTH501 MCQs (LaTeX rendering) ──")
    try:
        path = write_test_json(MTH_MCQ_DATA, "MTH501_test_mids_mcqs.json")
        pdf = generate_mcq_pdf(path)
        results.append(("MTH MCQs", "✅ SUCCESS", pdf))
        print(f"  ✅ Generated: {pdf}")
    except Exception as e:
        results.append(("MTH MCQs", f"❌ FAILED: {e}", ""))
        print(f"  ❌ Failed: {e}")
    
    # Test 2: Math Short Notes
    print("\n── Test 2: MTH501 Short Notes (LaTeX rendering) ──")
    try:
        path = write_test_json(MTH_NOTES_DATA, "short note MTH501_test_mids.json")
        pdf = generate_short_notes_pdf(path)
        results.append(("MTH Notes", "✅ SUCCESS", pdf))
        print(f"  ✅ Generated: {pdf}")
    except Exception as e:
        results.append(("MTH Notes", f"❌ FAILED: {e}", ""))
        print(f"  ❌ Failed: {e}")
    
    # Test 3: CS MCQs
    print("\n── Test 3: CS301 MCQs (Code block rendering) ──")
    try:
        path = write_test_json(CS_MCQ_DATA, "CS301_test_mids_mcqs.json")
        pdf = generate_mcq_pdf(path)
        results.append(("CS MCQs", "✅ SUCCESS", pdf))
        print(f"  ✅ Generated: {pdf}")
    except Exception as e:
        results.append(("CS MCQs", f"❌ FAILED: {e}", ""))
        print(f"  ❌ Failed: {e}")
    
    # Test 4: CS Short Notes
    print("\n── Test 4: CS301 Short Notes (Code block rendering) ──")
    try:
        path = write_test_json(CS_NOTES_DATA, "short note CS301_test_mids.json")
        pdf = generate_short_notes_pdf(path)
        results.append(("CS Notes", "✅ SUCCESS", pdf))
        print(f"  ✅ Generated: {pdf}")
    except Exception as e:
        results.append(("CS Notes", f"❌ FAILED: {e}", ""))
        print(f"  ❌ Failed: {e}")
    
    # Test 5: Regular subject (MGT - no special rendering)
    print("\n── Test 5: MGT501 MCQs (Plain text — no special rendering) ──")
    try:
        path = write_test_json(MGT_MCQ_DATA, "MGT501_test_mids_mcqs.json")
        pdf = generate_mcq_pdf(path)
        results.append(("MGT MCQs", "✅ SUCCESS", pdf))
        print(f"  ✅ Generated: {pdf}")
    except Exception as e:
        results.append(("MGT MCQs", f"❌ FAILED: {e}", ""))
        print(f"  ❌ Failed: {e}")
    
    # Summary
    print("\n" + "=" * 60)
    print("RESULTS SUMMARY")
    print("=" * 60)
    for name, status, path in results:
        print(f"  {name}: {status}")
        if path:
            print(f"    → {path}")
    
    passed = sum(1 for _, s, _ in results if "SUCCESS" in s)
    total = len(results)
    print(f"\n  Total: {total}, Passed: {passed}, Failed: {total - passed}")
    print("=" * 60)
    
    # Cleanup test JSON files
    for f in ["MTH501_test_mids_mcqs.json", "short note MTH501_test_mids.json",
              "CS301_test_mids_mcqs.json", "short note CS301_test_mids.json",
              "MGT501_test_mids_mcqs.json"]:
        fp = os.path.join(os.path.dirname(__file__), f)
        if os.path.exists(fp):
            os.remove(fp)
    
    return passed == total


if __name__ == "__main__":
    success = test_pdf_generation()
    sys.exit(0 if success else 1)
