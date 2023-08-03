from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import pandas as pd
from io import BytesIO
import re

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# root
@app.get("/")
async def root():
    return {"message": "Hello World"}



@app.post("/uploadfiles")
async def create_upload_file(file: UploadFile = File(...)):
    # Read the data from the uploaded file
    df = pd.read_excel(BytesIO(await file.read()))

    # Convert 'Doc. Date' to datetime format and extract the month
    df['Doc. Date'] = pd.to_datetime(df['Doc. Date'], format='%Y%m%d')
    df['Month'] = df['Doc. Date'].dt.month
    df['Year'] = df['Doc. Date'].dt.year
    # Separate the data into two dataframes: one for employees and one for vendors
    df_employee = df[df['Employee/Appl.Name'].notna()]
    df_vendor = df[df['Vendor Name'].notna()]

    # Group the data by year, name, and month, and sum the expenses for each group
    employee_expenses = df_employee.groupby(['Year', 'Employee/Appl.Name', 'Month'])['ValCOArCur'].sum().reset_index()
    vendor_expenses = df_vendor.groupby(['Year', 'Vendor Name', 'Month'])['ValCOArCur'].sum().reset_index()

    # Pivot the data and add a column for the total expenses for the year
    employee_expenses_pivot = employee_expenses.pivot_table(values='ValCOArCur', index=['Year', 'Employee/Appl.Name'], columns='Month', fill_value=0)
    vendor_expenses_pivot = vendor_expenses.pivot_table(values='ValCOArCur', index=['Year', 'Vendor Name'], columns='Month', fill_value=0)
    employee_expenses_pivot['Total'] = employee_expenses_pivot.sum(axis=1)
    vendor_expenses_pivot['Total'] = vendor_expenses_pivot.sum(axis=1)

    # Convert the dataframes to dictionaries grouped by year
    employee_expenses_dict = employee_expenses_pivot.reset_index().groupby('Year').apply(lambda x: x.set_index('Employee/Appl.Name').drop(columns='Year').to_dict(orient='index')).to_dict()
    vendor_expenses_dict = vendor_expenses_pivot.reset_index().groupby('Year').apply(lambda x: x.set_index('Vendor Name').drop(columns='Year').to_dict(orient='index')).to_dict()

    # Combine the employee and vendor expenses for each year
    expenses = {year: {'employee_expenses': employee_expenses_dict.get(year, {}), 'vendor_expenses': vendor_expenses_dict.get(year, {})} for year in set(employee_expenses_dict) | set(vendor_expenses_dict)}

    # 2 decimal places for all values of the dictionary
    for year in expenses:
        for name in expenses[year]['employee_expenses']:
            for month in expenses[year]['employee_expenses'][name]:
                expenses[year]['employee_expenses'][name][month] = '{:.2f}'.format(expenses[year]['employee_expenses'][name][month])

        for name in expenses[year]['vendor_expenses']:
            for month in expenses[year]['vendor_expenses'][name]:
                expenses[year]['vendor_expenses'][name][month] = '{:.2f}'.format(expenses[year]['vendor_expenses'][name][month])
    return expenses



@app.post("/uploadfiles2")
async def create_upload_files2(files: List[UploadFile] = File(...)):
    all_results = {}
    total_results = {}

    for file in files:
        # Load the Excel file
        df = pd.read_excel(BytesIO(await file.read()))

        # Group by manager name and sum expenses
        manager_expenses = df.groupby('Employee/Appl.Name')['ValCOArCur'].sum()

        # Extract the date from the filename
        match = re.search(r'GM_(\w+)_(\d+).xlsx', file.filename)
        if match:
            month, year = match.groups()

            if year not in all_results:
                all_results[year] = {}
                total_results[year] = {}

            for manager, expense in manager_expenses.items():
                if manager not in all_results[year]:
                    all_results[year][manager] = {}

                all_results[year][manager][month] = '{:.2f}'.format(expense)

                if manager not in total_results[year]:
                    total_results[year][manager] = 0

                total_results[year][manager] += float(expense)

    # Convert total_results to strings
    for year in total_results:
        total_results[year] = {manager: '{:.2f}'.format(expense) for manager, expense in total_results[year].items()}

    return {"all_results": all_results, "total_results": total_results}