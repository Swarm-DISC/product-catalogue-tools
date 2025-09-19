#!/usr/bin/env python3
"""
Generate a CSV file matching input.csv format from the JSON catalogue files.
This script reads all JSON files in the catalogue directory and creates a CSV
with the same columns as input.csv.
"""

import json
import csv
from pathlib import Path
from typing import List, Dict, Any, Optional

def load_authors_mapping() -> Dict[str, Dict[str, str]]:
    """Load the authors.json file for reverse mapping"""
    authors_file = Path('authors.json')
    if authors_file.exists():
        with open(authors_file, 'r') as f:
            return json.load(f)
    return {}

def find_author_abbreviation(author_name: str, ror: str, authors_db: Dict[str, Dict[str, str]]) -> str:
    """Find the abbreviation for an author based on name and ROR"""
    # First try to match by ROR
    if ror:
        for key, author in authors_db.items():
            if author.get('ror', '') == ror:
                return author.get('abbreviation', author['name'])
    
    # Then try to match by name
    for key, author in authors_db.items():
        if author['name'].lower() == author_name.lower():
            return author.get('abbreviation', author['name'])
    
    # If no match found, return the original name
    return author_name

def format_authors(authors: List[Dict[str, str]], authors_db: Dict[str, Dict[str, str]]) -> str:
    """Format authors list into comma-separated string using full names"""
    if not authors:
        return ""
    
    author_names = []
    for author in authors:
        name = author.get('name', '')
        author_names.append(name)
    
    return ', '.join(author_names)

def format_product_types(product_types: List[str]) -> str:
    """Format product types list into comma-separated string"""
    if not product_types:
        return ""
    return ', '.join(product_types)

def extract_csv_data(json_file: Path, authors_db: Dict[str, Dict[str, str]]) -> Optional[Dict[str, Any]]:
    """Extract data from a JSON file and format it for CSV output"""
    try:
        with open(json_file, 'r') as f:
            data = json.load(f)
        
        product_id = data.get('product_id', '')
        if not product_id:
            print(f"Warning: No product_id found in {json_file}")
            return None
        
        # Extract and format the data
        csv_row = {
            'Name': product_id,
            'Description(short_description)': data.get('definition', ''),
            'Version / Baseline': '0',  # Default value from input.csv
            'Directorate': 'D/EOP',  # Default value from input.csv
            'Status': 'Available',  # Default value from input.csv
            'Access Type': 'External Data',  # Default value from input.csv
            'Geo Restriction': 'World Wide',  # Default value from input.csv
            'Product Types': format_product_types(data.get('product_types', [])),
            'Heritage': 'No',  # Default value from input.csv
            'Constellations': 'Swarm',  # Default value from input.csv
            'Landing Page URL': f"https://swarmhandbook.earth.esa.int/catalogue/{product_id}",
            'Dissemination mode': 'Swarm Mission Specific Service',  # Default value from input.csv
            'Data Policy URL': 'https://earth.esa.int/eogateway/documents/20142/1564626/Terms-and-Conditions-for-the-use-of-ESA-Data.pdf',  # Default value from input.csv
            'Creation year': data.get('creation_year', ''),
            'Publication Year': data.get('creation_year', ''),  # Same as creation year
            'File Format': '',  # Empty in input.csv
            'Owned by': 'Antonio de la Fuente',  # Default value from input.csv
            'Deputy Owner': '',  # Empty in input.csv
            'Collection': 'TRUE',  # Default value from input.csv
            'Dataset': 'TRUE',  # Default value from input.csv
            'Campaign': 'FALSE',  # Default value from input.csv
            'EarthOnline page requested': 'FALSE',  # Default value from input.csv
            'Authors': format_authors(data.get('authors', []), authors_db),
            'Creators': 'European Space Agency',  # Default value from input.csv
            'Publisher': 'European Space Agency',  # Default value from input.csv
            'Language': 'en'  # Default value from input.csv
        }
        
        return csv_row
        
    except Exception as e:
        print(f"Error processing {json_file}: {e}")
        return None

def main():
    """Main function to generate CSV from JSON files"""
    # Load authors mapping
    print("Loading authors mapping...")
    authors_db = load_authors_mapping()
    print(f"Loaded {len(authors_db)} authors from authors.json")
    
    # Find all JSON files in catalogue directory
    catalogue_dir = Path('product-catalogue/catalogue')
    if not catalogue_dir.exists():
        print(f"Error: Directory {catalogue_dir} does not exist")
        return
    
    json_files = list(catalogue_dir.glob('*.json'))
    print(f"Found {len(json_files)} JSON files to process")
    
    # Extract data from all JSON files
    csv_data = []
    for json_file in json_files:
        row_data = extract_csv_data(json_file, authors_db)
        if row_data:
            csv_data.append(row_data)
    
    if not csv_data:
        print("No data extracted from JSON files")
        return
    
    # Define CSV columns in the same order as input.csv
    columns = [
        'Name', 'Description(short_description)', 'Version / Baseline', 'Directorate', 
        'Status', 'Access Type', 'Geo Restriction', 'Product Types', 'Heritage', 
        'Constellations', 'Landing Page URL', 'Dissemination mode', 'Data Policy URL', 
        'Creation year', 'Publication Year', 'File Format', 'Owned by', 'Deputy Owner', 
        'Collection', 'Dataset', 'Campaign', 'EarthOnline page requested', 'Authors', 
        'Creators', 'Publisher', 'Language'
    ]
    
    # Write CSV file
    output_file = 'table_for_DOIs.csv'
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=columns, quoting=csv.QUOTE_MINIMAL)
        writer.writeheader()
        writer.writerows(csv_data)
    
    print(f"\nGenerated {output_file} with {len(csv_data)} products")
    print(f"Columns: {', '.join(columns)}")

if __name__ == '__main__':
    main()
