import io
import re
import pandas as pd
from django.http import HttpResponse
from django.shortcuts import render
from io import StringIO, BytesIO

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from .forms import ExcelUploadForm
from .models import ProteinData

# Create your views here.

# Define the RACC values as a dictionary
RACC_VALUES = {
    'bean': 35,
    'chickpea': 35,
    'lentil': 35,
    'pea': 35,
    'hemp': 15,
    'oats': 40,
    'wheat': 40,
    'soy': 35,
    'buckwheat': 30,
    'pinto': 15
}


def label_source(value):
    # if pd.isna(value):  # Check if the value is NaN
    #     return 'Unknown'
    if value > 10:
        return 'Excellent Source'
    elif 5 <= value <= 10:
        return 'Good Source'
    else:
        return 'No Claim'

# Function to extract keywords from the sample column and find the corresponding RACC value
def extract_keyword(product_name):
    product_name = product_name.lower()  # Convert to lowercase for matching
    for keyword in RACC_VALUES:
        # Use regular expressions to find the keyword in the product name
        if re.search(r'\b' + keyword + r'\b', product_name):
            return keyword  # Return the matched keyword if found
    return None  # Return None if no keyword matches


def process_excel(request):
    if request.method == 'POST':
        form = ExcelUploadForm(request.POST, request.FILES)
        if form.is_valid():
            excel_file = request.FILES['file']
            # Read the Excel file into a pandas DataFrame
            df = pd.read_excel(excel_file)
            # Clear old entries from ProteinData table
            ProteinData.objects.all().delete()

            # Ensure the 'sample' column is in lowercase and has no leading/trailing spaces
            df['SAMPLE'] = df['SAMPLE'].str.lower().str.strip()

            # Convert relevant columns to numeric, setting errors='coerce' to handle non-numeric data
            # df['PROTEIN %'] = pd.to_numeric(df['PROTEIN %'], errors='coerce')
            # df['PDCAAS'] = pd.to_numeric(df['PDCAAS'], errors='coerce')
            # df['IVPDCAAS'] = pd.to_numeric(df['IVPDCAAS'], errors='coerce')

            # Apply calculations row by row
            def calculate_labels(row):
                product = extract_keyword(row['SAMPLE'])
                protein_percent = row['PROTEIN %']
                pdcaas = row['PDCAAS'] # Fetching Value of PDCAAS from file uploaded
                ivpdcaas = row['IVPDCAAS']  # Fetching Value of IVPDCAAS from file uploaded

                # Check if a keyword was found and is in the predefined list
                # if pd.notnull(protein_percent) and pd.notnull(pdcaas) and pd.notnull(ivpdcaas) and product:
                if product:
                    racc_value = RACC_VALUES[product]
                    # PDCAAS Calculation
                    pdcaas_result = (protein_percent/100) * racc_value * (pdcaas/100)
                    pdcaas_result = round(pdcaas_result, 2)  # Restrict to 2 decimal places
                    pdcaas_label = label_source(pdcaas_result)

                    # IVPDCAAS Calculation
                    ivpdcaas_result = (protein_percent/100) * racc_value * (ivpdcaas/100)
                    ivpdcaas_result = round(ivpdcaas_result, 2)  # Restrict to 2 decimal places
                    ivpdcaas_label = label_source(ivpdcaas_result)

                    return pd.Series({'PDCAAS claim': pdcaas_result, ' PDCAAS label': pdcaas_label, 'IVPDCAAS claim': ivpdcaas_result,'IVPDCAAS label': ivpdcaas_label})
                else:
                    return pd.Series({'PDCAAS claim': 'Unknown', 'label': 'Unknown' , 'IVPDCAAS claim': 'Unknown','IVPDCAAS label': 'Unknown'})  # If no valid keyword is found

            # Apply the calculation to each row and create the two new columns
            df[['PDCAAS claim', 'PDCAAS label', 'IVPDCAAS claim', 'IVPDCAAS label']] = df.apply(calculate_labels, axis=1)


            # Convert the DataFrame to an HTML table to render in the template
            table = df.to_html(classes='table table-striped')

            # Check if the user requested to download as CSV or Excel
            if 'export_csv' in request.POST:
                return download_csv(df)
            elif 'export_excel' in request.POST:
                return export_pdf_file(df)

            return render(request, 'result.html', {'table': table})

    else:
        form = ExcelUploadForm()

    return render(request, 'upload.html', {'form': form})




# CSV download function


def download_csv(request):
    # Get processed data from session
    df_dict = request.session.get('processed_data', None)
    if df_dict is not None:
        df = pd.DataFrame.from_dict(df_dict)

        # Create a StringIO buffer to write CSV data into it
        csv_buffer = StringIO()

        # Convert DataFrame to CSV and write it to the StringIO buffer
        df.to_csv(path_or_buf=csv_buffer, index=False)

        # Get the content of the buffer as a string
        csv_data = csv_buffer.getvalue()

        # Create HttpResponse for CSV
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="output.csv"'

        # Write the CSV data into the response
        response.write(csv_data)

        return response
    else:
        return HttpResponse("No data available to export", status=400)



def export_pdf_file(dataframe):
    # Create a BytesIO buffer to hold the PDF file in memory
    buffer = BytesIO()

    # Create a PDF using reportlab
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    # Title for the PDF
    p.setFont("Helvetica-Bold", 16)
    p.drawString(100, height - 50, "Data Export")

    # Move down for table content
    p.setFont("Helvetica", 12)

    # Start at a fixed vertical position
    y_position = height - 100

    # Column headers
    columns = dataframe.columns.tolist()
    col_widths = 100  # Fixed column width
    x_position = 50  # Starting position for the first column

    # Draw column headers
    for i, col in enumerate(columns):
        p.drawString(x_position + i * col_widths, y_position, col)

    # Draw rows (data)
    y_position -= 20  # Move down for row data
    for index, row in dataframe.iterrows():
        for i, value in enumerate(row):
            p.drawString(x_position + i * col_widths, y_position, str(value))
        y_position -= 20  # Move to the next line for the next row

        # Check if page is full, and create a new page if necessary
        if y_position < 50:
            p.showPage()  # Finish the current page
            p.setFont("Helvetica", 12)  # Reset the font
            y_position = height - 50  # Start from the top of the new page

    # Save the PDF
    p.save()

    # Move buffer's position to the start
    buffer.seek(0)

    return buffer

def download_pdf(request):
    # Sample DataFrame, replace this with your actual data
    df = pd.DataFrame({
        'Column1': [1, 2, 3],
        'Column2': [4, 5, 6]
    })

    # Export to PDF using reportlab
    buffer = export_pdf_file(df)

    # Create HTTP response to send as a file
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="output.pdf"'

    return response





