#!/usr/bin/python3
"""
    Dashboard launcher.
    Generates the latest dashboard and opens it in your browser.
    Run with: python dashboard.py
    Author: Fortune Nwohiri
"""
import os
import webbrowser
from job_agent.report_generator import generate

if __name__ == "__main__":
    print("Generating dashboard...")
    result = generate()
    dashboard_path = result["dashboard_path"]
    abs_path = os.path.abspath(dashboard_path)
    url = f"file:///{abs_path.replace(os.sep, '/')}"
    print(f"Dashboard ready: {abs_path}")
    print("Opening in browser...")
    webbrowser.open(url)