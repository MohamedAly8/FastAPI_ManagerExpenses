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
async def create_upload_files(files: List[UploadFile] = File(...)):
    all_results = {}
    total_results = {}
    
    for file in files:
        # Load the Excel file
        df = pd.read_excel(BytesIO(await file.read()))

        # Group by manager name and sum expenses
        manager_expenses = df.groupby('Employee/Appl.Name')['ValCOArCur'].sum()

        # valCoArCur should have 2 decimal places, even if integer
        manager_expenses = manager_expenses.sort_values(ascending=False)
        manager_expenses = manager_expenses.apply(lambda x: '{:.2f}'.format(x))

        # Convert the result to a dictionary and store it in all_results
        all_results[file.filename] = manager_expenses.to_dict()
        
        # add to total result for each manager
        for manager, expense in manager_expenses.items():
 
            if manager in total_results:
                total_results[manager] += float(expense)
            else:
                total_results[manager] = float(expense)

    
    # make all values in total_results have 2 decimal places
    total_results = {k: '{:.2f}'.format(v) for k, v in total_results.items()}

    return {"all_results": all_results, "total_results": total_results}

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