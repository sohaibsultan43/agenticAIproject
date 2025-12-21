# Test script to verify ScholarSync setup before running notebooks
# Run this from the notebooks/ directory with: python test_setup.py

import sys
from pathlib import Path

# Add parent directory to path
sys.path.append('..')

print("="*60)
print("SCHOLARSYNC SETUP VERIFICATION")
print("="*60)

# Test 1: Check if we can import from src
print("\n1. Testing imports from src/...")
try:
    from src.ingest import load_pdfs, get_weaviate_client, create_weaviate_schema, WEAVIATE_CLASS_NAME
    from src.fetcher import search_arxiv, download_pdf
    print("   ✓ All imports successful")
except ImportError as e:
    print(f"   ✗ Import failed: {e}")
    print("\n   Fix: Make sure you're running from the notebooks/ directory")
    print("        and that src/ directory exists in parent folder")
    sys.exit(1)

# Test 2: Check environment variables
print("\n2. Checking environment variables...")
import os
from dotenv import load_dotenv

# Try to load .env from parent directory
load_dotenv(Path('../.env'))

required_vars = {
    'GEMINI_API_KEY': 'Gemini API key',
    'WEAVIATE_CLOUD_URL': 'Weaviate Cloud URL',
    'WEAVIATE_API_KEY': 'Weaviate API key'
}

missing_vars = []
for var_name, description in required_vars.items():
    if not os.getenv(var_name):
        missing_vars.append(f"   - {var_name} ({description})")
        print(f"   ✗ Missing: {var_name}")
    else:
        print(f"   ✓ Found: {var_name}")

if missing_vars:
    print("\n   Missing environment variables:")
    for var in missing_vars:
        print(var)
    print("\n   Fix: Add these to your .env file in the project root")
    sys.exit(1)

# Test 3: Check Weaviate connection
print("\n3. Testing Weaviate connection...")
try:
    client = get_weaviate_client()
    print("   ✓ Connected to Weaviate")
    client.close()
except Exception as e:
    print(f"   ✗ Connection failed: {e}")
    print("\n   Fix: Verify WEAVIATE_CLOUD_URL and WEAVIATE_API_KEY in .env")
    sys.exit(1)

# Test 4: Check directories
print("\n4. Checking directory structure...")
dirs_to_check = [
    Path('../downloaded_papers'),
    Path('../results'),
    Path('../src'),
    Path('../src/agents')
]

for dir_path in dirs_to_check:
    if dir_path.exists():
        print(f"   ✓ {dir_path} exists")
    else:
        print(f"   ! {dir_path} missing (will be created if needed)")

print("\n" + "="*60)
print("✓ SETUP VERIFICATION COMPLETE")
print("="*60)
print("\nYou're ready to run the notebooks!")
print("\nTo run notebooks:")
print("  1. Make sure you're in the notebooks/ directory")
print("  2. Activate virtual environment: ..\\venv\\Scripts\\Activate")
print("  3. Start Jupyter: jupyter notebook")
print("  4. Open 01_baseline_chunking.ipynb or 02_agent_evaluation.ipynb")
