# %% [markdown]
# ## Timetable Download Process
# 
# 1. **Download the timetables from the web** and store them in local repositories.
# 2. **Check if the local repository is empty:**
#    - If **empty**, proceed to download the timetable.
#    - If **not empty**, check the web for the latest schedule.
#      - If a **newer version exists**, download the updated timetable.
#      - If **no update is found**, skip the download process.
# 
# > This approach helps avoid unnecessary downloads and ensures we always work with the most recent data available.

# %%
import requests
from bs4 import BeautifulSoup
import pandas as pd

print("#" * 60 )
print(f"Starting the script")
print(f"Loading the functions and features")

def get_ktmb_komuter_timetables():
    # Generically scrape all Komuter timetable PDFs and infer schedule types
    url = "https://www.ktmb.com.my/TrainTime.html"
    
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        records = []
        print(f"Scraping data from {url}...")
        count = 1
        for link in soup.find_all('a', attrs={'data-target': '#reusemodal'}):
            # print(f"No {count} -   {link}")

            if 'data-dl' not in link.attrs:
                continue
            
            pdf_url = link['data-dl']
            if not pdf_url.startswith('http'):
                pdf_url = f"https://www.ktmb.com.my{pdf_url}"

            schedule = 'NA'
            alt_text = link.get('alt', '').upper()  # Use .lower() for case-insensitive matching
            if any(keyword in alt_text for keyword in ['WEEKDAY ', 'WEEKDAYS']):
                schedule = 'WEEKDAYS'
            elif any(keyword in alt_text for keyword in ['WEEKEND', 'WEEKENDS', 'SATURDAY', 'SUNDAY', 'PUBLIC HOLIDAY']):
                schedule = 'WEEKENDS'
            
            title = link.find('b').get_text(strip=True) if link.find('b') else 'NA'
            effective_date = title.split('Effective ')[1] if 'Effective' in title else 'NA'
            
            records.append({
                'Title': title.upper(),
                'PDF Links': pdf_url,
                'Schedule': schedule,
                'Effective': effective_date
            })

            count += 1
        
        return pd.DataFrame(records)[['Title', 'PDF Links', 'Schedule', 'Effective']]
    
    except Exception as e:
        print(f"Error: {e}")
        return pd.DataFrame()

def get_train_route(departure, destination):
    """
    Get the train route from departure to destination.
    
    Args:
    departure (str): Departure station name.
    destination (str): Destination station name.
    
    Returns:
    str: Route name if found, otherwise None.
    """
    # Load the route data
    df_route = pd.read_excel('train_route.xlsx')
    
    # Convert inputs to uppercase for consistency
    departure = departure.upper()
    destination = destination.upper()
    
    # Get rows for departure and destination
    dep_rows = df_route[df_route['STATION_NAME'] == departure]
    dest_rows = df_route[df_route['STATION_NAME'] == destination]
    
    # Loop through combinations to find first valid (departure < destination) on same route
    for d_idx in dep_rows.index:
        dep_route = df_route.at[d_idx, 'ROUTE_NAME']
        for dst_idx in dest_rows.index:
            if d_idx < dst_idx and df_route.at[dst_idx, 'ROUTE_NAME'] == dep_route:
                return dep_route
    
    return None

def extract_keywords(route):
    # Split the route string into words
    words = route.split()
    
    # Define a list of irrelevant words to ignore
    irrelevant_words = ["LALUAN", "KE"]
    
    # Initialize variables to store keywords
    keywords = []
    current_keyword = []
    
    for word in words:
        # Skip irrelevant words
        if word in irrelevant_words:
            continue
        
        # Add the word to the current keyword
        current_keyword.append(word)
        
        # If the next word is irrelevant or we've reached the end, add the current keyword to the list
        if not words or word == words[-1] or words[words.index(word) + 1] in irrelevant_words:
            keywords.append(" ".join(current_keyword))
            current_keyword = []
    
    return keywords

print(f"functions and features [Completed]")

print("#" * 60)
print(f"Entering main code.. Please wait")

# Run the function
timetables_df = get_ktmb_komuter_timetables()

print(f"Total {len(timetables_df)} timetables found.")


# %%
# Getting the entire pdf link in KTMB website
timetables_df

# %%
print("#" * 60)
print(f"Filtering the timetables for only Klang Valley routes....")
# Filter only needed routes and schedules
route_titles = [
    'TG. MALIM - PELABUHAN KLANG',
    'BATU CAVES - PULAU SEBANG'
]

# Step 1: Create a mask for filtering
mask = timetables_df['Title'].str.contains('|'.join(route_titles), case=False, na=False) & \
    timetables_df['Schedule'].isin(['WEEKDAYS', 'WEEKENDS'])

# Step 2: Apply mask and sort by Effective (descending) to get latest entries
filtered_timetables = timetables_df[mask].copy()

# Step 3: Ensure datetime format for proper sorting (if needed)
# Convert 'Effective' column to datetime if it's not already
filtered_timetables['Effective'] = pd.to_datetime(filtered_timetables['Effective'], errors='coerce')

# Step 4: Sort and drop duplicates to get latest per Title + Schedule
latest_timetables = (
    filtered_timetables
    .sort_values(by='Effective', ascending=False)
    .drop_duplicates(subset=['Title', 'Schedule'])
)

# Step 5: Sort final output by Title and Schedule
latest_timetables = latest_timetables.sort_values(by=['Title', 'Schedule', 'Effective'], ascending=[True, True, False])

latest_timetables
print(f"Total {len(latest_timetables)} timetables found after filtering. We only need 4")


# %% [markdown]
# ## Load PDF into Local Database
# 
# To proceed, ensure the following:
# 
# 1. A total of **4 files** are required.
# 2. Each route must include:
#    - **Weekday schedule**
#    - **Weekend schedule**
# 

# %%
print("#" * 60)
print("Extracting the latest timetable for Batu Caves and Pelabuhan Klang...")

import camelot
import tempfile
import os
import requests
import pandas as pd
from datetime import datetime

# Extract latest schedules for Batu Caves and Pelabuhan Klang
latest_batu_caves_weekends = latest_timetables[
    (latest_timetables['Title'].str.contains('BATU CAVES', case=False)) &
    (latest_timetables['Schedule'] == 'WEEKENDS')
].sort_values(by='Effective', ascending=False).head(1)

latest_batu_caves_weekdays = latest_timetables[
    (latest_timetables['Title'].str.contains('BATU CAVES', case=False)) &
    (latest_timetables['Schedule'] == 'WEEKDAYS')
].sort_values(by='Effective', ascending=False).head(1)

latest_klang_weekends = latest_timetables[
    (latest_timetables['Title'].str.contains('PELABUHAN KLANG', case=False)) &
    (latest_timetables['Schedule'] == 'WEEKENDS')
].sort_values(by='Effective', ascending=False).head(1)

latest_klang_weekdays = latest_timetables[
    (latest_timetables['Title'].str.contains('PELABUHAN KLANG', case=False)) &
    (latest_timetables['Schedule'] == 'WEEKDAYS')
].sort_values(by='Effective', ascending=False).head(1)

# List of schedule entries to process
schedule_entries = [
    ('batu_caves_weekends', latest_batu_caves_weekends),
    ('batu_caves_weekdays', latest_batu_caves_weekdays),
    ('klang_weekends', latest_klang_weekends),
    ('klang_weekdays', latest_klang_weekdays),
]

# Save in a 'timetables' folder in the current working directory
DATA_DIR = os.path.join(os.getcwd(), "timetables")
os.makedirs(DATA_DIR, exist_ok=True)

# Dictionary to store resulting DataFrames
timetable_data = {}

with tempfile.TemporaryDirectory() as temp_dir:
    for name, entry in schedule_entries:
        if entry.empty:
            print(f"No data found for {name}")
            continue

        # Get title and clean it for filename
        title_str = entry['Title'].iloc[0].replace(' ', '_')
        pdf_path = os.path.join(temp_dir, f"{title_str}.pdf")

        # Download the PDF
        pdf_url = entry['PDF Links'].iloc[0]
        response = requests.get(pdf_url)
        with open(pdf_path, 'wb') as f:
            f.write(response.content)

        # Read tables from PDF
        print(f"Reading {name} PDF: {pdf_path}")
        tables = camelot.read_pdf(pdf_path, pages='1-end')
        print(f"Extracted {len(tables)} tables from {pdf_path}")

        # Save each table as a DataFrame in the dictionary
        for i, table in enumerate(tables):
            df_name = f"{name}_route_{i+1}"
            timetable_data[df_name] = table.df.iloc[2:].reset_index(drop=True)

# Save all tables as Parquet
for df_name, df in timetable_data.items():
    output_path = os.path.join(DATA_DIR, f"{df_name}.parquet")
    df.to_parquet(output_path, index=False)
    print(f"[{datetime.now()}] Saved {df_name} to {output_path}")


# Assign back to global variables
globals().update(timetable_data)

print("All timetables extracted successfully.")
