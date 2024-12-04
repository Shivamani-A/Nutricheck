Nutricheck

Nutricheck is a Python-based application designed to analyze and manage nutritional information for various food products. This project simplifies nutritional data tracking and provides insights into food-related information for individuals and businesses by dentifying PDCAAS claim and label them accordingly.

Table of Contents

Overview
Features
Technologies Used
Installation
Prerequisites
Setup
Usage
Contributing
License
Contact
Overview

Nutricheck streamlines the process of tracking nutritional data by providing tools to:

Extract product names from detailed descriptions.
Match extracted product names with updated Recommended Amount Customary Consumption (RACC) values.
Generate comprehensive reports on nutritional data.
The application aims to help users make informed dietary choices and ensure compliance with food labeling standards.

Features

Automated Product Extraction: Extract specific product names from detailed descriptions.
RACC Matching: Automatically match product names with their updated RACC values.
User-Friendly Interface: Simple and efficient workflows.
Scalability: Designed to handle large datasets.

Technologies Used

Python: Core programming language.
Pandas: Data manipulation and analysis.
Regular Expressions (re): Text processing.
OpenPyXL/XlsxWriter: Excel file handling.

Installation

Prerequisites
Before installing Nutricheck, ensure the following software is installed on your system:

Python: Version 3.7 or higher.
Download Python
Git (optional, for cloning the repository).
Download Git

Setup
Clone the Repository: Open your terminal or command prompt and run:
git clone https://github.com/Shivamani-A/Nutricheck.git
cd Nutricheck
Install Required Libraries: Use pip to install the required dependencies:
pip install -r requirements.txt
Run the Application: Execute the main script to start the program:
python nutricheck.py

Usage

Place your input file (e.g., an Excel file with food product descriptions) in the designated directory.
Modify the configuration file (if applicable) to include paths and parameters.
Run the script using:
python nutricheck.py
View the output in the results folder, which includes matched RACC values and processed data.
Contributing

Contact

For questions or collaboration, feel free to reach out:

Author: Shivamani A
GitHub: Shivamani-A
