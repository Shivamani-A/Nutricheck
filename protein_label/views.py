
import re
import pandas as pd
from django.http import JsonResponse
from django.http import HttpResponse
from django.shortcuts import render, redirect
from io import StringIO, BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape

from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, PageBreak

from reportlab.pdfbase import pdfmetrics

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

def home(request):
    print("Home view called.")
    return render(request, 'index.html')

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
    print("Processing Excel file...")

    if request.method == 'POST' and 'file' in request.FILES:
        # Handle initial file upload
        form = ExcelUploadForm(request.POST, request.FILES)
        if form.is_valid():
            excel_file = request.FILES['file']
            df = pd.read_excel(excel_file)

            # Clear old entries from ProteinData table (if necessary)
            ProteinData.objects.all().delete()

            # Ensure the 'sample' column is in lowercase and has no leading/trailing spaces
            df['SAMPLE'] = df['SAMPLE'].str.lower().str.strip()

            # Apply calculations row by row
            def calculate_labels(row):
                product = extract_keyword(row['SAMPLE'])
                protein_percent = row['PROTEIN %']
                pdcaas = row['PDCAAS']
                ivpdcaas = row['IVPDCAAS']

                if product:
                    racc_value = RACC_VALUES[product]
                    pdcaas_result = (protein_percent / 100) * racc_value * (pdcaas / 100)
                    pdcaas_label = label_source(pdcaas_result)

                    ivpdcaas_result = (protein_percent / 100) * racc_value * (ivpdcaas / 100)
                    ivpdcaas_label = label_source(ivpdcaas_result)

                    return pd.Series({'PDCAAS claim': round(pdcaas_result, 2), 'PDCAAS label': pdcaas_label,
                                      'IVPDCAAS claim': round(ivpdcaas_result, 2), 'IVPDCAAS label': ivpdcaas_label})
                else:
                    return pd.Series({'PDCAAS claim': 'Unknown', 'PDCAAS label': 'Unknown',
                                      'IVPDCAAS claim': 'Unknown', 'IVPDCAAS label': 'Unknown'})

            # Apply the calculation to each row
            df[['PDCAAS claim', 'PDCAAS label', 'IVPDCAAS claim', 'IVPDCAAS label']] = df.apply(calculate_labels, axis=1)

            # Store the original processed data in session for future filtering or downloads
            request.session['original_data'] = df.to_dict(orient='list')
            request.session['filtered_data'] = df.to_dict(orient='list')  # Set initially to the full data

            # Render the results page with the table
            table_html = df.to_html(classes='table table-striped')
            return render(request, 'result.html', {
                'table': table_html,
                'pdcaas_label_filter': 'All',
                'ivpdcaas_label_filter': 'All'
            })


    elif request.method == 'GET' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        print("Handling AJAX filtering request...")
        # Handle AJAX filtering

        df_dict = request.session.get('original_data', None)  # Start with the original data

        if df_dict is not None:

            df = pd.DataFrame.from_dict(df_dict)

            # Apply filters based on AJAX request

            pdcaas_label_filter = request.GET.get('pdcaas_label', 'All')

            ivpdcaas_label_filter = request.GET.get('ivpdcaas_label', 'All')

            if pdcaas_label_filter != 'All':
                df = df[df['PDCAAS label'] == pdcaas_label_filter]

            if ivpdcaas_label_filter != 'All':
                df = df[df['IVPDCAAS label'] == ivpdcaas_label_filter]

            # Check if the filtered DataFrame is empty

            is_empty = df.empty

            # Update the session with the filtered data if there are results

            request.session['filtered_data'] = df.to_dict(orient='list') if not is_empty else request.session[
                'original_data']

            print(request.session.get('filtered_data', 'No Data Found')) ## for debugging

            # Convert filtered DataFrame to an HTML table or return a message if empty

            table_html = '<div class="alert alert-warning">No results found for the filters applied.</div>' if is_empty else df.to_html(
                classes='table table-striped')

            return JsonResponse({'table_html': table_html, 'is_empty': is_empty})

        # If there's no file or the method is GET without AJAX, render the upload form

    form = ExcelUploadForm()

    return render(request, 'upload.html', {'form': form})

def download_csv(request):
    # Use filtered data if available
    df_dict = request.session.get('filtered_data', None)
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


def download_pdf(request):
    # Use filtered data if available
    df_dict = request.session.get('filtered_data', None)
    if df_dict is not None:
        df = pd.DataFrame.from_dict(df_dict)
        pdf_content = export_pdf(df)

        response = HttpResponse(pdf_content, content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="output.pdf"'
        return response
    else:
        return HttpResponse("No data available to export", status=400)


# PDF export function with dynamic column width adjustments
def export_pdf(dataframe):
    try:
        buffer = BytesIO()
        pdf = SimpleDocTemplate(buffer, pagesize=landscape(letter))
        elements = []
        columns_per_page = 12
        num_columns = len(dataframe.columns)
        num_rows = len(dataframe)

        def get_column_widths(df_page):
            col_widths = []
            for col in df_page.columns:
                max_text = max([str(x) for x in df_page[col].values] + [col], key=len)
                width = pdfmetrics.stringWidth(max_text, 'Helvetica', 8) + 10  # extra padding
                col_widths.append(width)
            return col_widths

        # Iterate through the columns to create pages if necessary
        for start_col in range(0, num_columns, columns_per_page):
            end_col = min(start_col + columns_per_page, num_columns)
            page_df = dataframe.iloc[:, start_col:end_col]

            # Convert the DataFrame into a list for Table generation
            data = [page_df.columns.tolist()] + page_df.values.tolist()

            # Calculate dynamic column widths
            col_widths = get_column_widths(page_df)
            table = Table(data, colWidths=col_widths)

            # Set table styles
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

    except Exception as e:
        print("Error generating PDF:", e)  # Log error for debugging
        return None

def chart_view(request):
    print("Chart view called.")
    filtered_data = request.session.get('filtered_data', None)
    if not filtered_data:
        print("No filtered data found in session.")
        return render(request, 'chart.html', {'error': 'No data available for visualization.'})

    df = pd.DataFrame.from_dict(filtered_data)
    pdcaas_distribution = df['PDCAAS label'].value_counts().to_dict()
    ivpdcaas_distribution = df['IVPDCAAS label'].value_counts().to_dict()

    chart_data = {
        'pdcaas': [{'label': key, 'count': value} for key, value in pdcaas_distribution.items()],
        'ivpdcaas': [{'label': key, 'count': value} for key, value in ivpdcaas_distribution.items()],
    }

    print("Chart Data:", chart_data)
    return render(request, 'chart.html', {'chart_data': chart_data})


# def chart_view(request):
#     print("Chart view called.")
#     # Retrieve chart data from session
#     filtered_data = request.session.get('filtered_data', None)
#
#     if not filtered_data:
#         print("No filtered data found in session.")
#         return render(request, 'chart.html', {'error': 'No data available for visualization.'})
#
#     if filtered_data:
#         df = pd.DataFrame.from_dict(filtered_data)
#
#         # Check if necessary columns exist
#         if 'PDCAAS label' in df.columns and 'IVPDCAAS label' in df.columns:
#             pdcaas_counts = df['PDCAAS label'].value_counts().to_dict()
#             ivpdcaas_counts = df['IVPDCAAS label'].value_counts().to_dict()
#
#             chart_data = {
#                 'pdcaas': [{'label': label, 'count': count} for label, count in pdcaas_counts.items()],
#                 'ivpdcaas': [{'label': label, 'count': count} for label, count in ivpdcaas_counts.items()]
#             }
#             return render(request, 'chart.html', {'chart_data': chart_data})
#
#     # Redirect if no valid data found
#     return redirect('process_excel')

