# import io
# import openpyxl
# import re
# import pandas as pd
# from django.http import HttpResponse
# from django.shortcuts import render
# from io import StringIO, BytesIO
# from reportlab.lib import colors
# from reportlab.lib.pagesizes import letter, landscape
# from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, PageBreak
# from reportlab.lib.units import inch
#
# from .forms import ExcelUploadForm
# from .models import ProteinData
#
# # Define the RACC values as a dictionary
# RACC_VALUES = {
#     'bean': 35,
#     'chickpea': 35,
#     'lentil': 35,
#     'pea': 35,
#     'hemp': 15,
#     'oats': 40,
#     'wheat': 40,
#     'soy': 35,
#     'buckwheat': 30,
#     'pinto': 15
# }
#
# def label_source(value):
#     if value > 10:
#         return 'Excellent Source'
#     elif 5 <= value <= 10:
#         return 'Good Source'
#     else:
#         return 'No Claim'
#
# # Extract keywords and get corresponding RACC value
# def extract_keyword(product_name):
#     product_name = product_name.lower()
#     for keyword in RACC_VALUES:
#         if re.search(r'\b' + keyword + r'\b', product_name):
#             return keyword
#     return None
#
# def process_excel(request):
#     if request.method == 'POST':
#         form = ExcelUploadForm(request.POST, request.FILES)
#         if form.is_valid():
#             excel_file = request.FILES['file']
#             df = pd.read_excel(excel_file)
#             ProteinData.objects.all().delete()
#             df['SAMPLE'] = df['SAMPLE'].str.lower().str.strip()
#
#             def calculate_labels(row):
#                 product = extract_keyword(row['SAMPLE'])
#                 protein_percent = row['PROTEIN %']
#                 pdcaas = row['PDCAAS']
#                 ivpdcaas = row['IVPDCAAS']
#
#                 if product:
#                     racc_value = RACC_VALUES[product]
#                     pdcaas_result = round((protein_percent / 100) * racc_value * (pdcaas / 100), 2)
#                     ivpdcaas_result = round((protein_percent / 100) * racc_value * (ivpdcaas / 100), 2)
#                     pdcaas_label = label_source(pdcaas_result)
#                     ivpdcaas_label = label_source(ivpdcaas_result)
#
#                     return pd.Series({
#                         'PDCAAS claim': pdcaas_result,
#                         'PDCAAS label': pdcaas_label,
#                         'IVPDCAAS claim': ivpdcaas_result,
#                         'IVPDCAAS label': ivpdcaas_label
#                     })
#                 else:
#                     return pd.Series({
#                         'PDCAAS claim': 'Unknown',
#                         'PDCAAS label': 'Unknown',
#                         'IVPDCAAS claim': 'Unknown',
#                         'IVPDCAAS label': 'Unknown'
#                     })
#
#             # Apply calculations and create new columns
#             df[['PDCAAS claim', 'PDCAAS label', 'IVPDCAAS claim', 'IVPDCAAS label']] = df.apply(calculate_labels,
#                                                                                                 axis=1)
#             table = df.to_html(classes='table table-striped')
#             request.session['processed_data'] = df.to_dict(orient='list')
#
#             # Download options
#             if 'export_csv' in request.POST:
#                 return download_csv(request)
#             elif 'export_pdf' in request.POST:
#                 return download_pdf(request)
#
#             return render(request, 'result.html', {'table': table})
#     else:
#         form = ExcelUploadForm()
#     return render(request, 'upload.html', {'form': form})
#
#
# # CSV download function
# def download_csv(request):
#     df_dict = request.session.get('processed_data')
#     if df_dict is not None:
#         df = pd.DataFrame.from_dict(df_dict)
#         csv_buffer = StringIO()
#         df.to_csv(path_or_buf=csv_buffer, index=False)
#         csv_data = csv_buffer.getvalue()
#         response = HttpResponse(content_type='text/csv')
#         response['Content-Disposition'] = 'attachment; filename="output.csv"'
#         response.write(csv_data)
#         return response
#     return HttpResponse("No data available to export", status=400)
#
#
# # PDF export function with proper adjustments for landscape orientation
# def export_pdf_file(dataframe):
#     buffer = BytesIO()
#     pdf = SimpleDocTemplate(buffer, pagesize=landscape(letter))
#     # Split data into chunks for multi-table support
#     max_columns_per_table = 10  # Adjust as needed
#     data_tables = []
#     widths = []
#
#     for i in range(0, len(dataframe.columns), max_columns_per_table):
#         table_data = [dataframe.columns[i:i + max_columns_per_table].tolist()] + dataframe.iloc[:,
#                                                                                  i:i + max_columns_per_table].values.tolist()
#         data_tables.append(table_data)
#         widths.append(['*'] * min(max_columns_per_table, len(dataframe.columns) - i))  # Use * for automatic width
#
#     story = []
#     for table_data, col_widths in zip(data_tables, widths):
#         table = Table(table_data)
#         # Set Table Styles to add padding, alignment, and row height for better spacing
#         table.setStyle(TableStyle([
#             ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
#             ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
#             ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
#             ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
#             ('FONTSIZE', (0, 1), (-1, -1), 8),  # Set font size to avoid overcrowding
#             ('BOTTOMPADDING', (0, 0), (-1, 0), 10),  # Padding for header
#             ('BOTTOMPADDING', (0, 1), (-1, -1), 6),  # Padding for each data cell
#             ('TOPPADDING', (0, 1), (-1, -1), 6),
#             ('GRID', (0, 0), (-1, -1), 0.5, colors.black),  # Thin grid lines for structure
#             ('ROWHEIGHT', (0, 0), (-1, -1), 15),  # Minimum row height for better spacing
#         ]))
#         table._argW = col_widths  # Set column widths
#         story.append(table)
#         story.append(PageBreak())  # Add a page break between tables
#
#     pdf.build(story)
#     buffer.seek(0)
#     return buffer.read()
#
#
# # PDF download function
# def download_pdf(request):
#     df_dict = request.session.get('processed_data')
#     if df_dict is not None:
#         df = pd.DataFrame.from_dict(df_dict)
#         pdf_content = export_pdf_file(df)
#         response = HttpResponse(pdf_content, content_type='application/pdf')
#         response['Content-Disposition'] = 'attachment; filename="output.pdf"'
#         return response
#     return HttpResponse("No data available to export", status=400)



# import io
# import openpyxl
# import re
# import pandas as pd
# from django.http import HttpResponse
# from django.shortcuts import render
# from io import StringIO, BytesIO
#
# from reportlab.lib import colors
# from reportlab.lib.pagesizes import letter, landscape,A3
#
# from reportlab.lib.units import inch
# from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
#
# from .forms import ExcelUploadForm
# from .models import ProteinData
#
# # Define the RACC values as a dictionary
# RACC_VALUES = {
#     'bean': 35,
#     'chickpea': 35,
#     'lentil': 35,
#     'pea': 35,
#     'hemp': 15,
#     'oats': 40,
#     'wheat': 40,
#     'soy': 35,
#     'buckwheat': 30,
#     'pinto': 15
# }
#
#
# def label_source(value):
#     if value > 10:
#         return 'Excellent Source'
#     elif 5 <= value <= 10:
#         return 'Good Source'
#     else:
#         return 'No Claim'
#
#
# # Extract keywords and get corresponding RACC value
# def extract_keyword(product_name):
#     product_name = product_name.lower()
#     for keyword in RACC_VALUES:
#         if re.search(r'\b' + keyword + r'\b', product_name):
#             return keyword
#     return None
#
#
# def process_excel(request):
#     if request.method == 'POST':
#         form = ExcelUploadForm(request.POST, request.FILES)
#         if form.is_valid():
#             excel_file = request.FILES['file']
#             df = pd.read_excel(excel_file)
#             ProteinData.objects.all().delete()
#             df['SAMPLE'] = df['SAMPLE'].str.lower().str.strip()
#
#             def calculate_labels(row):
#                 product = extract_keyword(row['SAMPLE'])
#                 protein_percent = row['PROTEIN %']
#                 pdcaas = row['PDCAAS']
#                 ivpdcaas = row['IVPDCAAS']
#
#                 if product:
#                     racc_value = RACC_VALUES[product]
#                     pdcaas_result = round((protein_percent / 100) * racc_value * (pdcaas / 100), 2)
#                     ivpdcaas_result = round((protein_percent / 100) * racc_value * (ivpdcaas / 100), 2)
#                     pdcaas_label = label_source(pdcaas_result)
#                     ivpdcaas_label = label_source(ivpdcaas_result)
#                     return pd.Series({
#                         'PDCAAS claim': pdcaas_result,
#                         'PDCAAS label': pdcaas_label,
#                         'IVPDCAAS claim': ivpdcaas_result,
#                         'IVPDCAAS label': ivpdcaas_label
#                     })
#                 else:
#                     return pd.Series({
#                         'PDCAAS claim': 'Unknown',
#                         'PDCAAS label': 'Unknown',
#                         'IVPDCAAS claim': 'Unknown',
#                         'IVPDCAAS label': 'Unknown'
#                     })
#
#             # Apply calculations and create new columns
#             df[['PDCAAS claim', 'PDCAAS label', 'IVPDCAAS claim', 'IVPDCAAS label']] = df.apply(calculate_labels,axis=1)
#             table = df.to_html(classes='table table-striped')
#             request.session['processed_data'] = df.to_dict(orient='list')
#
#             # Download options
#             if 'export_csv' in request.POST:
#                 return download_csv(request)
#             elif 'export_pdf' in request.POST:
#                 return download_pdf(request)
#
#             return render(request, 'result.html', {'table': table})
#     else:
#         form = ExcelUploadForm()
#     return render(request, 'upload.html', {'form': form})
#
#
# # CSV download function
# def download_csv(request):
#     df_dict = request.session.get('processed_data')
#     if df_dict is not None:
#         df = pd.DataFrame.from_dict(df_dict)
#         csv_buffer = StringIO()
#         df.to_csv(path_or_buf=csv_buffer, index=False)
#         csv_data = csv_buffer.getvalue()
#         response = HttpResponse(content_type='text/csv')
#         response['Content-Disposition'] = 'attachment; filename="output.csv"'
#         response.write(csv_data)
#         return response
#     return HttpResponse("No data available to export", status=400)
#
#
# # PDF export function with proper adjustments for landscape orientation
# def calculate_row_width(row, column_widths):
#     return sum(column_widths)
#
#
# # Function to calculate table widths and split the table into multiple parts
# def split_table_if_overflow(data, column_widths, max_width):
#     tables = []
#     current_table = []
#     current_width = 0
#
#     for row in data:
#         row_width = calculate_row_width(row, column_widths)
#         if current_width + row_width <= max_width:
#             current_table.append(row)
#             current_width += row_width
#         else:
#             # Save the current table and start a new one
#             tables.append(current_table)
#             current_table = [row]  # Start new table with the current row
#             current_width = row_width  # Reset the width for the new table
#
#     # Add the remaining rows as a new table
#     if current_table:
#         tables.append(current_table)
#     return tables
#
#
# # PDF export function with proper adjustments for landscape orientation and table splitting
# def export_pdf_file(dataframe):
#     buffer = BytesIO()
#     pdf = SimpleDocTemplate(buffer, pagesize=landscape(letter))
#     # Convert dataframe to list of rows
#     data = [dataframe.columns.tolist()] + dataframe.values.tolist()
#
#     # Calculate column widths (this is an approximation, adjust as needed)
#     column_widths = [1.5 * inch] * len(data[0])  # Adjust column width based on the number of columns
#
#     # Maximum width for the table (adjust to fit within landscape page width)
#     max_width = 9 * inch
#
#     # Split the table if the total width exceeds the maximum width
#     tables = split_table_if_overflow(data, column_widths, max_width)
#
#     # Create tables for each part and apply styling
#     table_list = []
#     for table_data in tables:
#         table = Table(table_data)
#         style = TableStyle([
#             ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
#             ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
#             ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
#             ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
#             ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
#             ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
#             ('GRID', (0, 0), (-1, -1), 1, colors.black),
#         ])
#         table.setStyle(style)
#         table_list.append(table)
#
#     # Build the PDF with the tables, ensuring page breaks between them
#     pdf.build(table_list)
#     buffer.seek(0)
#     return buffer.read()
#
#
# # PDF download function (adjust as needed for your web framework)
# def download_pdf(request):
#     df_dict = request.session.get('processed_data')
#     if df_dict is not None:
#         df = pd.DataFrame.from_dict(df_dict)
#         pdf_content = export_pdf_file(df)
#         response = HttpResponse(pdf_content, content_type='application/pdf')
#         response['Content-Disposition'] = 'attachment; filename="output.pdf"'
#         return response
#     return HttpResponse("No data available to export", status=400)




import io
import openpyxl
import re
import pandas as pd
from django.http import HttpResponse
from django.shortcuts import render
from io import StringIO, BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, PageBreak
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics

from .forms import ExcelUploadForm
from .models import ProteinData

# from django.template.loader import render_to_string
# from weasyprint import HTML
# import tempfile

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

            # Save processed data in session for export functions
            request.session['processed_data'] = df.to_dict(orient='list')

            # Check if the user requested to download as CSV or Excel
            if 'export_csv' in request.POST:
                return download_csv(request)
            elif 'export_excel' in request.POST:
                return download_pdf(request)

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
        df.to_csv(path_or_buf=csv_buffer, index=False)
        csv_data = csv_buffer.getvalue()

        # Create HttpResponse for CSV
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="output.csv"'
        response.write(csv_data)

        return response
    else:
        return HttpResponse("No data available to export", status=400)

# pdfmetrics.registerFont(TTFont('Helvetica', 'Helvetica.ttf'))

# PDF export function with dynamic column width adjustments
def export_pdf(dataframe):
    buffer = BytesIO()
    pdf = SimpleDocTemplate(buffer, pagesize=landscape(letter))
    elements = []
    columns_per_page = 12
    num_columns = len(dataframe.columns)
    num_rows = len(dataframe)

    # Function to calculate dynamic column widths based on cell content
    def get_column_widths(df_page):
        col_widths = []
        for col in df_page.columns:
            max_text = max([str(x) for x in df_page[col].values] + [col], key=len)
            width = pdfmetrics.stringWidth(max_text, 'Helvetica', 8) + 10  # extra padding
            col_widths.append(width)
        return col_widths

    for start_col in range(0, num_columns, columns_per_page):
        end_col = min(start_col + columns_per_page, num_columns)
        page_df = dataframe.iloc[:, start_col:end_col]
        data = [page_df.columns.tolist()] + page_df.values.tolist()

        col_widths = get_column_widths(page_df)
        table = Table(data, colWidths=col_widths)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 0.25, colors.black),
        ]))

        elements.append(table)
        elements.append(PageBreak())

    pdf.build(elements)
    buffer.seek(0)
    return buffer.getvalue()

def download_pdf(request):
    df = pd.DataFrame(request.session.get('processed_data', None))
    pdf_content = export_pdf(df)

    response = HttpResponse(pdf_content, content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="output.pdf"'

    return response

