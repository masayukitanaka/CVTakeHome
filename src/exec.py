#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Insurance Document Processing Pipeline

This program executes a complete insurance document processing pipeline:
1. PDF to Markdown conversion
2. Insurance policy summary extraction  
3. Dynamic insurance analysis for additional terms

Usage: python exec.py <PDF_file> [--output-dir OUTPUT_DIR]
"""

import sys
import argparse
import subprocess
from pathlib import Path


def run_command(command: list, description: str) -> bool:
    """
    Run a command and handle errors
    
    Args:
        command: Command to run as list of strings
        description: Description of the command for error reporting
        
    Returns:
        True if successful, False otherwise
    """
    print(f"Processing: {description}...")
    
    try:
        # Run command with real-time output
        # Don't capture output to allow it to stream to console
        subprocess.run(command, check=True)
        print(f"Success: {description} completed successfully")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"Error: {description} failed with return code {e.returncode}")
        return False
    except Exception as e:
        print(f"Error: {description} failed with error: {e}")
        return False


def ensure_output_directory(output_dir: str) -> bool:
    """
    Ensure output directory exists
    
    Args:
        output_dir: Path to output directory
        
    Returns:
        True if directory exists or was created successfully
    """
    try:
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        return True
    except Exception as e:
        print(f"Error: Failed to create output directory '{output_dir}': {e}")
        return False


def get_markdown_filename(pdf_path: str) -> str:
    """
    Generate markdown filename from PDF filename
    
    Args:
        pdf_path: Path to PDF file
        
    Returns:
        Markdown filename
    """
    pdf_name = Path(pdf_path).stem
    return f"{pdf_name}_converted.md"


def main():
    """Main execution function"""
    parser = argparse.ArgumentParser(
        description="Process insurance PDF documents through complete analysis pipeline"
    )
    parser.add_argument("pdf_file", help="Path to PDF file to process")
    parser.add_argument(
        "--output-dir", 
        default="output", 
        help="Output directory (default: output)"
    )
    
    args = parser.parse_args()
    
    # Validate PDF file
    if not Path(args.pdf_file).exists():
        print(f"Error: PDF file '{args.pdf_file}' not found")
        sys.exit(1)
    
    if not args.pdf_file.lower().endswith('.pdf'):
        print(f"Error: File '{args.pdf_file}' is not a PDF file")
        sys.exit(1)
    
    # Ensure output directory exists
    if not ensure_output_directory(args.output_dir):
        sys.exit(1)
    
    # Get absolute paths
    pdf_path = Path(args.pdf_file).resolve()
    output_dir = Path(args.output_dir).resolve()
    
    print("=" * 80)
    print("INSURANCE DOCUMENT PROCESSING PIPELINE")
    print("=" * 80)
    print(f"Input PDF: {pdf_path}")
    print(f"Output Directory: {output_dir}")
    print()
    
    # Generate intermediate file paths
    markdown_filename = get_markdown_filename(str(pdf_path))
    markdown_path = output_dir / markdown_filename
    
    # Step 1: PDF to Markdown conversion
    print("STEP 1: PDF TO MARKDOWN CONVERSION")
    print("-" * 40)
    
    pdf_converter_command = [
        "python", "pdf_to_markdown_converter.py",
        str(pdf_path)
    ]
    
    if not run_command(pdf_converter_command, "Converting PDF to Markdown"):
        print("Pipeline failed at Step 1")
        sys.exit(1)
    
    # Move generated markdown to output directory
    source_markdown = Path(pdf_path.parent) / markdown_filename
    if source_markdown.exists():
        try:
            source_markdown.rename(markdown_path)
            print(f"Markdown file moved to: {markdown_path}")
        except Exception as e:
            print(f"Warning: Could not move markdown file: {e}")
            markdown_path = source_markdown
    else:
        print(f"Warning: Expected markdown file not found at {source_markdown}")
        # Try to find it in current directory
        current_dir_markdown = Path.cwd() / markdown_filename
        if current_dir_markdown.exists():
            try:
                current_dir_markdown.rename(markdown_path)
                print(f"Markdown file moved from current directory to: {markdown_path}")
            except Exception as e:
                print(f"Error: Could not move markdown file: {e}")
                sys.exit(1)
        else:
            print(f"Error: Markdown file not found")
            sys.exit(1)
    
    print()
    
    # Step 2: Insurance policy summary extraction
    print("STEP 2: INSURANCE POLICY SUMMARY EXTRACTION")
    print("-" * 50)
    
    insurance_parser_command = [
        "python", "parse_insurance_markdown.py",
        str(markdown_path)
    ]
    
    if not run_command(insurance_parser_command, "Extracting insurance policy summary"):
        print("Pipeline failed at Step 2")
        sys.exit(1)
    
    # Move generated analysis file to output directory
    analysis_filename = f"{Path(markdown_path).stem}_insurance_analysis.md"
    source_analysis = Path(markdown_path.parent) / analysis_filename
    target_analysis = output_dir / analysis_filename
    
    if source_analysis.exists() and source_analysis != target_analysis:
        try:
            source_analysis.rename(target_analysis)
            print(f"Insurance analysis moved to: {target_analysis}")
        except Exception as e:
            print(f"Warning: Could not move insurance analysis: {e}")
    
    print()
    
    # Step 3: Dynamic insurance analysis
    print("STEP 3: DYNAMIC INSURANCE ANALYSIS")
    print("-" * 35)
    
    dynamic_analyzer_command = [
        "python", "dynamic_insurance_analyzer.py",
        str(markdown_path)
    ]
    
    if not run_command(dynamic_analyzer_command, "Performing dynamic insurance analysis"):
        print("Pipeline failed at Step 3")
        sys.exit(1)
    
    # Move generated dynamic analysis file to output directory
    dynamic_filename = f"{Path(markdown_path).stem}_dynamic_insurance_analysis.md"
    source_dynamic = Path(markdown_path.parent) / dynamic_filename
    target_dynamic = output_dir / dynamic_filename
    
    if source_dynamic.exists() and source_dynamic != target_dynamic:
        try:
            source_dynamic.rename(target_dynamic)
            print(f"Dynamic analysis moved to: {target_dynamic}")
        except Exception as e:
            print(f"Warning: Could not move dynamic analysis: {e}")
    
    print()
    print("=" * 80)
    print("PIPELINE COMPLETED SUCCESSFULLY!")
    print("=" * 80)
    print("Generated Files:")
    print(f"   - Markdown: {markdown_path}")
    print(f"   - Insurance Summary: {output_dir / analysis_filename}")
    print(f"   - Dynamic Analysis: {output_dir / dynamic_filename}")
    print()
    print("All insurance document processing steps completed successfully!")


if __name__ == "__main__":
    main()