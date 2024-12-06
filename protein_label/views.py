import re
import pandas as pd
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render
from io import StringIO, BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, PageBreak
from reportlab.pdfbase import pdfmetrics

from .forms import ExcelUploadForm, ManualInputForm
from .models import ProteinData, RACCValue


# Common function for calculating claims and labels
def calculate_claims(protein_percent, racc_value, score, label_func):
    claim = (protein_percent / 100) * racc_value * (score / 100)
    label = label_func(claim)
    return round(claim, 2), label

def home(request):
    print("Home view called.")
    return render(request, 'index.html')

def label_source(value):
    if value >= 10:
        return 'Excellent Source'
    elif 5 <= value < 10:
        return 'Good Source'
    else:
        return 'No Claim'

def extract_keyword_and_category(product_name):
    product_name = product_name.lower().strip()
    racc_entries = RACCValue.objects.all()

    if "barley flour" in product_name:
        for entry in racc_entries:
            if entry.keyword == "barley flour":
                return {
                    'keyword': entry.keyword,
                    'category': entry.category,
                    'racc_value': entry.racc_value,
                }
    elif product_name == "barley":
        for entry in racc_entries:
            if entry.keyword == "barley" and entry.category == "Cereals":
                return {
                    'keyword': entry.keyword,
                    'category': entry.category,
                    'racc_value': entry.racc_value,
                }

    for entry in racc_entries:
        if "flour" in entry.category.lower():
            keyword_parts = entry.keyword.split()
            if any(part in product_name for part in keyword_parts) and "flour" in product_name:
                return {
                    'keyword': entry.keyword,
                    'category': entry.category,
                    'racc_value': entry.racc_value,
                }

    for entry in racc_entries:
        keyword = entry.keyword
        if re.search(r'\b' + re.escape(keyword) + r'\b', product_name):
            return {
                'keyword': keyword,
                'category': entry.category,
                'racc_value': entry.racc_value,
            }

    return None
def process_excel(request):
    print("Processing Excel file...")

    if request.method == 'POST' and 'file' in request.FILES:
        form = ExcelUploadForm(request.POST, request.FILES)
        if form.is_valid():
            excel_file = request.FILES['file']
            df = pd.read_excel(excel_file)

            # Clean and preprocess the DataFrame
            ProteinData.objects.all().delete()

            df['SAMPLE'] = df['SAMPLE'].str.lower().str.strip()

            def calculate_labels(row):
                product_info = extract_keyword_and_category(row['SAMPLE'])
                protein_percent = row.get('PROTEIN %', 0)
                pdcaas = row.get('PDCAAS', 0)
                ivpdcaas = row.get('IVPDCAAS', 0)

                if product_info:
                    racc_value = product_info['racc_value']

                    pdcaas_claim, pdcaas_label = calculate_claims(protein_percent, racc_value, pdcaas, label_source)
                    ivpdcaas_claim, ivpdcaas_label = calculate_claims(protein_percent, racc_value, ivpdcaas, label_source)

                    return pd.Series({
                        'PDCAAS claim': pdcaas_claim,
                        'PDCAAS label': pdcaas_label,
                        'IVPDCAAS claim': ivpdcaas_claim,
                        'IVPDCAAS label': ivpdcaas_label,
                    })
                else:
                    return pd.Series({
                        'PDCAAS claim': 'Unknown',
                        'PDCAAS label': 'Unknown',
                        'IVPDCAAS claim': 'Unknown',
                        'IVPDCAAS label': 'Unknown',
                    })

            df = df.join(df.apply(calculate_labels, axis=1))

            # Round all numeric fields to 2 decimal places
            numeric_cols = df.select_dtypes(include=['float', 'int']).columns
            df[numeric_cols] = df[numeric_cols].round(2)

            # Store the data in the session
            request.session['original_data'] = df.to_dict(orient='list')
            request.session['filtered_data'] = df.to_dict(orient='list')

            # Convert the DataFrame to HTML for display
            table_html = df.to_html(classes='table table-striped', float_format='{:.2f}'.format)

            return render(request, 'result.html', {
                'table': table_html,
                'pdcaas_label_filter': 'All',
                'ivpdcaas_label_filter': 'All'
            })

    elif request.method == 'GET' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        df_dict = request.session.get('original_data', None)

        if df_dict is not None:
            df = pd.DataFrame.from_dict(df_dict)

            pdcaas_label_filter = request.GET.get('pdcaas_label', 'All')
            ivpdcaas_label_filter = request.GET.get('ivpdcaas_label', 'All')
            category_filter = request.GET.get('category', 'All')

            if pdcaas_label_filter != 'All':
                df = df[df['PDCAAS label'] == pdcaas_label_filter]

            if ivpdcaas_label_filter != 'All':
                df = df[df['IVPDCAAS label'] == ivpdcaas_label_filter]

            if category_filter != 'All':
                df = df[df['Category'] == category_filter]

            is_empty = df.empty
            request.session['filtered_data'] = df.to_dict(orient='list') if not is_empty else request.session[
                'original_data']

            table_html = '<div class="alert alert-warning">No results found for the filters applied.</div>' if is_empty else df.to_html(
                classes='table table-striped', float_format='{:.2f}'.format)

            return JsonResponse({'table_html': table_html, 'is_empty': is_empty})

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

    # Prepare amino acid data for stacked bar chart
    amino_acid_data = []
    amino_acid_columns = ['ASP', 'THR', 'SER','GLU','PRO','GLY','ALA','CYS','VAL','MET','ILE','LEU','TYR','PHE','HIS','LYS','ARG','TRP','AAS','TPD']  # Replace with actual amino acid column names
    for _, row in df.iterrows():
        composition = {col: row[col] for col in amino_acid_columns if col in df.columns}
        composition['sample'] = row['SAMPLE']
        # composition['PROTEIN'] = row['PROTEIN %'] if 'PROTEIN %' in df.columns else 0
        amino_acid_data.append(composition)

        # Protein Percentage Data (Separate)
    protein_data = []
    if 'PROTEIN %' in df.columns:
        for _, row in df.iterrows():
            protein_data.append({
                'sample': row['SAMPLE'],
                'protein': row['PROTEIN %']
            })

    chart_data = {
        'pdcaas': [{'label': key, 'count': value} for key, value in pdcaas_distribution.items()],
        'ivpdcaas': [{'label': key, 'count': value} for key, value in ivpdcaas_distribution.items()],
        'amino_acids': amino_acid_data,
        'proteins': protein_data,
    }

    print("Chart Data:", chart_data)
    return render(request, 'chart.html', {'chart_data': chart_data})

def manual_input(request):
    result = None
    errors = None
    if request.method == 'POST':
        form = ManualInputForm(request.POST)
        if form.is_valid():
            try:
                sample = form.cleaned_data['sample'].lower().strip()
                sample_name = form.cleaned_data['sample']
                protein_percent = form.cleaned_data['protein_percent']
                pdcaas = form.cleaned_data['pdcaas']
                ivpdcaas = form.cleaned_data['ivpdcaas']

                product_info = extract_keyword_and_category(sample)

                if product_info:
                    racc_value = product_info['racc_value']
                    category = product_info['category']
                    keyword = product_info['keyword']

                    pdcaas_result, pdcaas_label = calculate_claims(protein_percent, racc_value, pdcaas, label_source)
                    ivpdcaas_result, ivpdcaas_label = calculate_claims(protein_percent, racc_value, ivpdcaas, label_source)

                    result = {
                        'sample': sample,
                        'sample_name': sample_name,
                        'category': category,
                        'keyword': keyword,
                        'racc_value': racc_value,
                        'pdcaas_result': pdcaas_result,
                        'pdcaas_label': pdcaas_label,
                        'ivpdcaas_result': ivpdcaas_result,
                        'ivpdcaas_label': ivpdcaas_label,
                    }
                else:
                    result = {
                        'error': f"No RACC value found for the sample '{sample}'. Please ensure it matches a known product."
                    }
            except Exception as e:
                errors = {'general': str(e)}
        else:
            errors = form.errors
    else:
        form = ManualInputForm()

    return render(request, 'manual_input.html', {'form': form, 'result': result, 'errors': errors})


# import openpyxl
# import re
# import pandas as pd
# from django.http import JsonResponse
# from django.http import HttpResponse
# from django.shortcuts import render, redirect
# from io import StringIO, BytesIO
#
# from reportlab.lib import colors
# from reportlab.lib.pagesizes import letter, landscape
#
# from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, PageBreak
#
# from reportlab.pdfbase import pdfmetrics
#
# from .forms import ExcelUploadForm, ManualInputForm
# from .models import ProteinData,RACCValue
#
#
# # Create your views here.
#
#
# def home(request):
#     print("Home view called.")
#     return render(request, 'index.html')
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
# def extract_keyword_and_category(product_name):
#     product_name = product_name.lower()  # Convert to lowercase for matching
#     racc_entries = RACCValue.objects.all()
#
#     for entry in racc_entries:
#         keyword = entry.keyword
#         if re.search(r'\b' + re.escape(keyword) + r'\b', product_name):
#             return {
#                 'keyword': keyword,
#                 'category': entry.category,
#                 'racc_value': entry.racc_value,
#             }
#     return None  # Return None if no keyword matches
#
#
# def process_excel(request):
#     print("Processing Excel file...")
#
#     if request.method == 'POST' and 'file' in request.FILES:
#         # Handle initial file upload
#         form = ExcelUploadForm(request.POST, request.FILES)
#         if form.is_valid():
#             excel_file = request.FILES['file']
#             df = pd.read_excel(excel_file)
#
#             # Clear old entries from ProteinData table (if necessary)
#             ProteinData.objects.all().delete()
#
#             # Ensure the 'SAMPLE' column is in lowercase and has no leading/trailing spaces
#             df['SAMPLE'] = df['SAMPLE'].str.lower().str.strip()
#
#             # Apply calculations row by row
#             def calculate_labels(row):
#                 product_info = extract_keyword_and_category(row['SAMPLE'])
#                 protein_percent = row.get('PROTEIN %', 0)
#                 pdcaas = row.get('PDCAAS', 0)
#                 ivpdcaas = row.get('IVPDCAAS', 0)
#
#                 if product_info:
#                     racc_value = product_info['racc_value']
#                     pdcaas_result = (protein_percent / 100) * racc_value * (pdcaas / 100)
#                     pdcaas_label = label_source(pdcaas_result)
#
#                     ivpdcaas_result = (protein_percent / 100) * racc_value * (ivpdcaas / 100)
#                     ivpdcaas_label = label_source(ivpdcaas_result)
#
#                     return pd.Series({
#                         # 'Category': product_info['category'],
#                         # 'Keyword': product_info['keyword'],
#                         'PDCAAS claim': round(pdcaas_result, 2),
#                         'PDCAAS label': pdcaas_label,
#                         'IVPDCAAS claim': round(ivpdcaas_result, 2),
#                         'IVPDCAAS label': ivpdcaas_label,
#                     })
#                 else:
#                     return pd.Series({
#                         # 'Category': 'Unknown',
#                         # 'Keyword': 'Unknown',
#                         'PDCAAS claim': 'Unknown',
#                         'PDCAAS label': 'Unknown',
#                         'IVPDCAAS claim': 'Unknown',
#                         'IVPDCAAS label': 'Unknown',
#                     })
#
#             # Apply the calculation to each row
#             df = df.join(df.apply(calculate_labels, axis=1))
#
#             # Store the original processed data in session for future filtering or downloads
#             request.session['original_data'] = df.to_dict(orient='list')
#             request.session['filtered_data'] = df.to_dict(orient='list')  # Set initially to the full data
#
#             # Render the results page with the table
#             table_html = df.to_html(classes='table table-striped')
#             return render(request, 'result.html', {
#                 'table': table_html,
#                 'pdcaas_label_filter': 'All',
#                 'ivpdcaas_label_filter': 'All'
#             })
#
#     elif request.method == 'GET' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
#         print("Handling AJAX filtering request...")
#         # Handle AJAX filtering
#         df_dict = request.session.get('original_data', None)  # Start with the original data
#
#         if df_dict is not None:
#             df = pd.DataFrame.from_dict(df_dict)
#
#             # Apply filters based on AJAX request
#             pdcaas_label_filter = request.GET.get('pdcaas_label', 'All')
#             ivpdcaas_label_filter = request.GET.get('ivpdcaas_label', 'All')
#             category_filter = request.GET.get('category', 'All')
#
#             if pdcaas_label_filter != 'All':
#                 df = df[df['PDCAAS label'] == pdcaas_label_filter]
#
#             if ivpdcaas_label_filter != 'All':
#                 df = df[df['IVPDCAAS label'] == ivpdcaas_label_filter]
#
#             if category_filter != 'All':
#                 df = df[df['Category'] == category_filter]
#
#             # Check if the filtered DataFrame is empty
#             is_empty = df.empty
#
#             # Update the session with the filtered data if there are results
#             request.session['filtered_data'] = df.to_dict(orient='list') if not is_empty else request.session[
#                 'original_data']
#
#             print(request.session.get('filtered_data', 'No Data Found'))  # for debugging
#
#             # Convert filtered DataFrame to an HTML table or return a message if empty
#             table_html = '<div class="alert alert-warning">No results found for the filters applied.</div>' if is_empty else df.to_html(
#                 classes='table table-striped')
#
#             return JsonResponse({'table_html': table_html, 'is_empty': is_empty})
#
#     # If there's no file or the method is GET without AJAX, render the upload form
#     form = ExcelUploadForm()
#     return render(request, 'upload.html', {'form': form})
#
#
# def download_csv(request):
#     # Use filtered data if available
#     df_dict = request.session.get('filtered_data', None)
#     if df_dict is not None:
#         df = pd.DataFrame.from_dict(df_dict)
#
#         # Create a StringIO buffer to write CSV data into it
#         csv_buffer = StringIO()
#         df.to_csv(path_or_buf=csv_buffer, index=False)
#         csv_data = csv_buffer.getvalue()
#
#         # Create HttpResponse for CSV
#         response = HttpResponse(content_type='text/csv')
#         response['Content-Disposition'] = 'attachment; filename="output.csv"'
#         response.write(csv_data)
#
#         return response
#     else:
#         return HttpResponse("No data available to export", status=400)
#
#
# def download_pdf(request):
#     # Use filtered data if available
#     df_dict = request.session.get('filtered_data', None)
#     if df_dict is not None:
#         df = pd.DataFrame.from_dict(df_dict)
#         pdf_content = export_pdf(df)
#
#         response = HttpResponse(pdf_content, content_type='application/pdf')
#         response['Content-Disposition'] = 'attachment; filename="output.pdf"'
#         return response
#     else:
#         return HttpResponse("No data available to export", status=400)
#
#
# # PDF export function with dynamic column width adjustments
# def export_pdf(dataframe):
#     try:
#         buffer = BytesIO()
#         pdf = SimpleDocTemplate(buffer, pagesize=landscape(letter))
#         elements = []
#         columns_per_page = 12
#         num_columns = len(dataframe.columns)
#         num_rows = len(dataframe)
#
#         def get_column_widths(df_page):
#             col_widths = []
#             for col in df_page.columns:
#                 max_text = max([str(x) for x in df_page[col].values] + [col], key=len)
#                 width = pdfmetrics.stringWidth(max_text, 'Helvetica', 8) + 10  # extra padding
#                 col_widths.append(width)
#             return col_widths
#
#         # Iterate through the columns to create pages if necessary
#         for start_col in range(0, num_columns, columns_per_page):
#             end_col = min(start_col + columns_per_page, num_columns)
#             page_df = dataframe.iloc[:, start_col:end_col]
#
#             # Convert the DataFrame into a list for Table generation
#             data = [page_df.columns.tolist()] + page_df.values.tolist()
#
#             # Calculate dynamic column widths
#             col_widths = get_column_widths(page_df)
#             table = Table(data, colWidths=col_widths)
#
#             # Set table styles
#             table.setStyle(TableStyle([
#                 ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
#                 ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
#                 ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
#                 ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
#                 ('FONTSIZE', (0, 0), (-1, -1), 8),
#                 ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
#                 ('BACKGROUND', (0, 1), (-1, -1), colors.white),
#                 ('GRID', (0, 0), (-1, -1), 0.25, colors.black),
#             ]))
#
#             elements.append(table)
#             elements.append(PageBreak())
#
#         pdf.build(elements)
#         buffer.seek(0)
#         return buffer.getvalue()
#
#     except Exception as e:
#         print("Error generating PDF:", e)  # Log error for debugging
#         return None
#
# def chart_view(request):
#     print("Chart view called.")
#     filtered_data = request.session.get('filtered_data', None)
#     if not filtered_data:
#         print("No filtered data found in session.")
#         return render(request, 'chart.html', {'error': 'No data available for visualization.'})
#
#     df = pd.DataFrame.from_dict(filtered_data)
#     pdcaas_distribution = df['PDCAAS label'].value_counts().to_dict()
#     ivpdcaas_distribution = df['IVPDCAAS label'].value_counts().to_dict()
#
#     # Prepare amino acid data for stacked bar chart
#     amino_acid_data = []
#     amino_acid_columns = ['ASP', 'THR', 'SER','GLU','PRO','GLY','ALA','CYS','VAL','MET','ILE','LEU','TYR','PHE','HIS','LYS','ARG','TRP','AAS','TPD']  # Replace with actual amino acid column names
#     for _, row in df.iterrows():
#         composition = {col: row[col] for col in amino_acid_columns if col in df.columns}
#         composition['sample'] = row['SAMPLE']
#         # composition['PROTEIN'] = row['PROTEIN %'] if 'PROTEIN %' in df.columns else 0
#         amino_acid_data.append(composition)
#
#         # Protein Percentage Data (Separate)
#     protein_data = []
#     if 'PROTEIN %' in df.columns:
#         for _, row in df.iterrows():
#             protein_data.append({
#                 'sample': row['SAMPLE'],
#                 'protein': row['PROTEIN %']
#             })
#
#     chart_data = {
#         'pdcaas': [{'label': key, 'count': value} for key, value in pdcaas_distribution.items()],
#         'ivpdcaas': [{'label': key, 'count': value} for key, value in ivpdcaas_distribution.items()],
#         'amino_acids': amino_acid_data,
#         'proteins': protein_data,
#     }
#
#     print("Chart Data:", chart_data)
#     return render(request, 'chart.html', {'chart_data': chart_data})
#
#
# def manual_input(request):
#     result = None
#     errors = None
#     if request.method == 'POST':
#         form = ManualInputForm(request.POST)
#         if form.is_valid():
#             try:
#                 # Extract form data
#                 sample = form.cleaned_data['sample'].lower().strip()
#                 sample_name = form.cleaned_data['sample']
#                 protein_percent = form.cleaned_data['protein_percent']
#                 pdcaas = form.cleaned_data['pdcaas']
#                 ivpdcaas = form.cleaned_data['ivpdcaas']
#
#                 # Determine the RACC value and category based on the sample keyword
#                 product_info = extract_keyword_and_category(sample)
#
#                 if product_info:
#                     racc_value = product_info['racc_value']
#                     category = product_info['category']
#                     keyword = product_info['keyword']
#
#                     # Calculate claims and labels
#                     pdcaas_result = (protein_percent / 100) * racc_value * (pdcaas / 100)
#                     pdcaas_label = label_source(pdcaas_result)
#
#                     ivpdcaas_result = (protein_percent / 100) * racc_value * (ivpdcaas / 100)
#                     ivpdcaas_label = label_source(ivpdcaas_result)
#
#                     # Prepare results
#                     result = {
#                         'sample': sample,
#                         'sample_name': sample_name,
#                         'category': category,
#                         'keyword': keyword,
#                         'racc_value': racc_value,
#                         'pdcaas_result': round(pdcaas_result, 2),
#                         'pdcaas_label': pdcaas_label,
#                         'ivpdcaas_result': round(ivpdcaas_result, 2),
#                         'ivpdcaas_label': ivpdcaas_label,
#                     }
#                 else:
#                     result = {
#                         'error': f"No RACC value found for the sample '{sample}'. Please ensure it matches a known product."
#                     }
#             except Exception as e:
#                 errors = {'general': str(e)}
#         else:
#             errors = form.errors
#     else:
#         form = ManualInputForm()
#
#     return render(request, 'manual_input.html', {'form': form, 'result': result, 'errors': errors})
#
#
#
#
#
#
