"""
Timetable Download Process

1. Download the timetables from the web and store them in local repositories.
2. Check if the local repository is empty:
   - If empty, proceed to download the timetable.
   - If not empty, check the web for the latest schedule.
     - If a newer version exists, download the updated timetable.
     - If no update is found, skip the download process.

This approach helps avoid unnecessary downloads and ensures we always work with the most recent data available
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import camelot
import tempfile
import os
import re
import requests
import pandas as pd
from datetime import datetime

print("#" * 60 )
print(f"Starting the script")
print(f"Loading the functions and features")


def get_ktmb_komuter_timetables():
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
            print(f"No {count} -   {link}")

            if 'data-dl' not in link.attrs:
                continue
            
            pdf_url = link['data-dl']
            if not pdf_url.startswith('http'):
                pdf_url = f"https://www.ktmb.com.my{pdf_url}"  # Fixed extra space

            # Determine schedule type
            alt_text = link.get('alt', '').upper()
            schedule = 'NA'
            if any(kw in alt_text for kw in ['WEEKDAY ', 'WEEKDAYS']):
                schedule = 'WEEKDAYS'
            elif any(kw in alt_text for kw in ['WEEKEND', 'WEEKENDS', 'SATURDAY', 'SUNDAY', 'PUBLIC HOLIDAY']):
                schedule = 'WEEKENDS'
            else:
                schedule = pd.NA
            
            # Extract title safely
            title_tag = link.find('b')
            title = title_tag.get_text(strip=True) if title_tag else ''
            
            # Step 1: Try to get date from title
            effective_date = pd.NA
            if title:
                match = re.search(r'Effective\s+(.+)', title, re.IGNORECASE)
                if match:
                    effective_date = match.group(1).strip()

            # Step 2: If not found, parse from PDF URL filename
            if pd.isna(effective_date):
                effective_date = extract_date_from_pdf_url(pdf_url)

            records.append({
                'Title': title.upper() if title else pd.NA,
                'PDF Links': pdf_url,
                'Schedule': schedule,
                'Effective': effective_date
            })
            count += 1
        
        return pd.DataFrame(records)[['Title', 'PDF Links', 'Schedule', 'Effective']]
    
    except Exception as e:
        print(f"Error: {e}")
        return pd.DataFrame()


def extract_date_from_pdf_url(pdf_url):
    """
    Extracts a human-readable date string from KTMB PDF URLs like:
    - .../2023/Jadual-Komuter-Utara-16-Sept-2023.pdf → "16 Sept 2023"
    - .../BCPS_Komuter Weekday mulai 25 Ogos 2025 1.pdf → "25 Ogos 2025"
    Returns pd.NA if no date found.
    """
    try:
        # Get filename from URL
        filename = pdf_url.split('/')[-1]
        # Remove .pdf extension
        base = filename.rsplit('.', 1)[0]

        # Normalize: replace underscores, multiple spaces, etc.
        clean = re.sub(r'[^a-zA-Z0-9\s\-]', ' ', base)
        clean = re.sub(r'\s+', ' ', clean).strip()

        # Month mappings (English + Malay)
        month_map = {
            'jan': 'January', 'feb': 'February', 'mar': 'March', 'apr': 'April',
            'may': 'May', 'jun': 'June', 'jul': 'July', 'aug': 'August',
            'sep': 'September', 'oct': 'October', 'nov': 'November', 'dec': 'December',
            'mac': 'March', 'mei': 'May', 'jun': 'June', 'jul': 'July',
            'ogos': 'August', 'sept': 'September', 'okt': 'October', 'dis': 'December'
        }

        # Pattern: day-month-year (with - or space)
        # e.g., "16-Sept-2023", "25 Ogos 2025"
        date_pattern = r'(\d{1,2})[\-\s]+([a-zA-Z]{3,})[\-\s]+(\d{4})'
        match = re.search(date_pattern, clean, re.IGNORECASE)
        if match:
            day = match.group(1)
            month_abbr = match.group(2).lower()
            year = match.group(3)

            # Normalize month to full English name
            for key in month_map:
                if month_abbr.startswith(key):
                    month_full = month_map[key]
                    return f"{day} {month_full} {year}"

            # If no match in map, return as-is (e.g., "16 Sept 2023")
            return f"{day} {match.group(2)} {year}"

        # Alternative: Look for "mulai DD Month YYYY"
        mulai_match = re.search(r'mulai\s+(\d{1,2})\s+([a-zA-Z]+)\s+(\d{4})', clean, re.IGNORECASE)
        if mulai_match:
            day, month, year = mulai_match.groups()
            return f"{day} {month} {year}"

        return pd.NA

    except Exception:
        return pd.NA

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

def extract_date_from_link(link):
    print(f"Extracting date from link: {link}")

    # Normalize the link: remove spaces and common separators
    filename = link.split('/')[-1]  # Get only the file name
    clean = re.sub(r'[^\w\-]', ' ', filename).replace('_', '-').lower()

    # Date patterns to match
    patterns = [
        (r'(\d{1,2})-?(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|mac|mei|jun|jul|ogos|sept|okt|nov|dis)[\-\s]?(\d{2,4})', "%d-%b-%Y"),  # 16-Sept-2023 / 15Mac2025
        (r'(\d{1,2})\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|mac|mei|jun|jul|ogos|sept|okt|nov|dis)\s+(\d{2,4})', "%d-%b-%Y"),  # 1 Mac 2024
        (r'(\d{4})-?(\d{2})-?(\d{2})', "%Y-%m-%d"),  # 20240101 or 2024-01-01
    ]

    for pattern, date_format in patterns:
        match = re.search(pattern, clean, re.IGNORECASE)
        if match:
            try:
                if 'b' in date_format.lower():  # Month name pattern
                    day = match.group(1)
                    month = match.group(2).lower().replace("mac", "mar").replace("mei", "may").replace("ogos", "aug").replace("sept", "sep").replace("okt", "oct").replace("dis", "dec")
                    year = match.group(3)
                    date_str = f"{day}-{month.title()}-{year}"
                    return datetime.strptime(date_str, "%d-%b-%Y")
                else:
                    return datetime.strptime(match.group(0), date_format)
            except Exception as e:
                print(f"Error parsing date: {e}")
                continue
    return None

print(f"functions and features [Completed]")

print("#" * 60)
print(f"Entering main code.. Please wait")


# Run the function
timetables_df = get_ktmb_komuter_timetables()

# Create a new column Effective_Date save as date format so that we can get the latest timetable
timetables_df['Effective_Date'] = (
    timetables_df['Effective']
    .str.replace(r'(\d+)(st|nd|rd|th)', r'\1', regex=True)
    .apply(pd.to_datetime, errors='coerce')
    .dt.strftime('%Y-%m-%d')
)

# remove rows with NaT in 'Effective'
timetables_df = timetables_df.dropna(subset=['Effective_Date'])

# Save in a 'timetables' folder in the current working directory
DATA_DIR = os.path.join(os.getcwd(), "timetables")
print(f"Saving the timetables in {DATA_DIR} folder...")

output_path = os.path.join(DATA_DIR, f"timetables_info.parquet")
timetables_df.to_parquet(output_path, index=False)
print(f"[{datetime.now()}] Saved timetables_df to {output_path}")


print(f"Total {len(timetables_df)} timetables found.")

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
filtered_timetables['Effective_Date'] = pd.to_datetime(filtered_timetables['Effective_Date'], errors='coerce')

# Step 4: Sort and drop duplicates to get latest per Title + Schedule
latest_timetables = (
    filtered_timetables
    .sort_values(by='Effective_Date', ascending=False)
    .drop_duplicates(subset=['Title', 'Schedule'])
)

# Step 5: Sort final output by Title and Schedule
latest_timetables = latest_timetables.sort_values(by=['Title', 'Schedule', 'Effective_Date'], ascending=[True, True, False])


print(f"Total {len(latest_timetables)} timetables found after filtering. We only need 4")
latest_timetables

'''
## Load PDF into Local Database

To proceed, ensure the following:

1. A total of **4 files** are required.
2. Each route must include:
   - **Weekday schedule**
   - **Weekend schedule**
'''

print("#" * 60)
print("Extracting the latest timetable for Batu Caves and Pelabuhan Klang...")

# Extract latest schedules for Batu Caves and Pelabuhan Klang
latest_batu_caves_weekends = latest_timetables[
    (latest_timetables['Title'].str.contains('BATU CAVES', case=False)) &
    (latest_timetables['Schedule'] == 'WEEKENDS')
].sort_values(by='Effective_Date', ascending=False).head(1)

latest_batu_caves_weekdays = latest_timetables[
    (latest_timetables['Title'].str.contains('BATU CAVES', case=False)) &
    (latest_timetables['Schedule'] == 'WEEKDAYS')
].sort_values(by='Effective_Date', ascending=False).head(1)

latest_klang_weekends = latest_timetables[
    (latest_timetables['Title'].str.contains('PELABUHAN KLANG', case=False)) &
    (latest_timetables['Schedule'] == 'WEEKENDS')
].sort_values(by='Effective_Date', ascending=False).head(1)

latest_klang_weekdays = latest_timetables[
    (latest_timetables['Title'].str.contains('PELABUHAN KLANG', case=False)) &
    (latest_timetables['Schedule'] == 'WEEKDAYS')
].sort_values(by='Effective_Date', ascending=False).head(1)

# List of schedule entries to process
schedule_entries = [
    ('batu_caves_weekends', latest_batu_caves_weekends),
    ('batu_caves_weekdays', latest_batu_caves_weekdays),
    ('klang_weekends', latest_klang_weekends),
    ('klang_weekdays', latest_klang_weekdays),
]

# Save in a 'timetables' folder in the current working directory
DATA_DIR = os.path.join(os.getcwd(), "timetables")
print(f"Saving the timetables in {DATA_DIR} folder...")

if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)


# Initialize list to hold enriched DataFrames
dfs_with_key = []

for name, df in schedule_entries:
    # Add a column to identify the schedule key
    df_copy = df.copy()
    df_copy['schedule_key'] = name
    dfs_with_key.append(df_copy)

# Concatenate all into one DataFrame
schedule_df = pd.concat(dfs_with_key, ignore_index=True)

# Reorder columns for clarity (optional)
schedule_df = schedule_df[['schedule_key', 'Title', 'PDF Links', 'Schedule', 'Effective', 'Effective_Date']]

# Now you have a clean, unified DataFrame
schedule_df

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
        # tables = camelot.read_pdf(pdf_path, pages='1-end')
        tables = camelot.read_pdf(pdf_path, pages='1-end', backend='pdfium')
        print(f"Extracted {len(tables)} tables from {pdf_path}")

        # Save each table as a DataFrame in the dictionary
        for i, table in enumerate(tables):

            df_name = f"{name}_route_{i+1}"
            # Setting up dataframe to be saved in parquet
            df = table.df.copy()
            print(f"Printing length of the DataFrame: {len(df)}")


            new_columns = df.iloc[2]  # Third row has column names
            df = df[3:]  # Remove first three rows
            df.columns = new_columns  # Apply new headers
            df = df.reset_index(drop=True)

            # Change the first column name to "STATION"
            df = df.rename(columns={df.columns[0]: "STATION"})

            # drop column names that are empty or NaN            
            df = df.loc[:, df.columns.notnull()]
            df = df.loc[:, df.columns != '']
            df = df.loc[:, df.columns.str.strip() != '']

            print(f"Saving table as {df_name}...")
            timetable_data[df_name] = df

# Save all tables as Parquet
for df_name, df in timetable_data.items():

    output_path = os.path.join(DATA_DIR, f"{df_name}.parquet")
    df.to_parquet(output_path, index=False)
    print(f"[{datetime.now()}] Saved {df_name} to {output_path}")


# Assign back to global variables
globals().update(timetable_data)
print("Klang Valley timetables extracted successfully.")




print("#" * 60)
print("Extracting the latest timetable for UTARA...")
print("#" * 60)

# Step 1: Filter timetables containing "UTARA" as a whole word (case-insensitive)
mask = timetables_df['Title'].str.contains(r'\bUTARA\b', case=False, regex=True)
north_filtered_timetables = timetables_df[mask].copy()

print(f"Total {len(north_filtered_timetables)} timetables found for UTARA routes.")

# Step 2: Get the most recent one based on Effective date
latest_utara = north_filtered_timetables.sort_values(by='Effective_Date', ascending=False).head(1)

if latest_utara.empty:
    print("No valid timetable found for UTARA.")
else:
    # Prepare directory to save extracted data
    DATA_DIR = os.path.join(os.getcwd(), "timetables")
    os.makedirs(DATA_DIR, exist_ok=True)

    # Store resulting DataFrames
    timetable_data = {}

    # Download and extract PDF
    title_str = latest_utara['Title'].iloc[0].replace(' ', '_')
    pdf_url = latest_utara['PDF Links'].iloc[0]

    with tempfile.TemporaryDirectory() as temp_dir:
        pdf_path = os.path.join(temp_dir, f"{title_str}.pdf")

        print(f"Downloading UTARA timetable PDF from: {pdf_url}")
        response = requests.get(pdf_url)
        with open(pdf_path, 'wb') as f:
            f.write(response.content)

        print(f"Reading UTARA PDF: {pdf_path}")
        # tables = camelot.read_pdf(pdf_path, pages='1-end')
        tables = camelot.read_pdf(pdf_path, pages='1-end', backend='pdfium')
        tables_size = len(tables)

        print(f"Extracted {tables_size} tables from {pdf_path}")

        # --- NEW: Track numbering per route type ---
        route_counters = {"ipoh": 0, "butterworth": 0, "padangbesar": 0}

        for i, table in enumerate(tables):
            df = table.df.copy()
            print(f"Processing table {i+1}, original length: {len(df)}")

            # Use third row as header
            if len(df) < 3:
                print(f"Skipping table {i+1}: Not enough rows to extract header.")
                continue

            new_columns = df.iloc[2]
            df = df[3:]
            df.columns = new_columns
            df = df.reset_index(drop=True)

            # Clean and standardize
            df = df.astype(str).apply(lambda x: x.str.strip())
            df.columns = [col.upper() for col in df.columns]

            # Default name in case no match
            df_name = f"utara_route_{i+1}"

            # Check for NOMBOR TREN
            if 'NOMBOR TREN' not in df.columns:
                print(f"Warning: 'NOMBOR TREN' column not found in table {i+1}. Using default name.")
            else:
                tren_values = df['NOMBOR TREN'].str.upper()

                if (tren_values.str.contains(r'\bIPOH\b', regex=True, na=False)).any():
                    route_type = "ipoh"
                    route_counters[route_type] += 1
                    df_name = f"utara_{route_type}_{route_counters[route_type]}"
                elif (tren_values.str.contains(r'\bPADANG BESAR\b', regex=True, na=False)).any():
                    route_type = "padangbesar"
                    route_counters[route_type] += 1
                    df_name = f"utara_{route_type}_{route_counters[route_type]}"
                else:
                    print(f"No Ipoh or Padang Besar found in NOMBOR TREN for table {i+1}. Using route fallback.")
                    df_name = f"utara_route_{i+1}"                


            # Convert first column to uppercase
            first_col = df.columns[0]
            df[first_col] = df[first_col].str.upper()

            # Change the first column name to "STATION"
            df = df.rename(columns={df.columns[0]: "STATION"})


            print(f"Saving table as {df_name}...")
            timetable_data[df_name] = df

    # Save all tables as Parquet files
    for df_name, df in timetable_data.items():
        output_path = os.path.join(DATA_DIR, f"{df_name}.parquet")
        df.to_parquet(output_path, index=False)
        print(f"[{datetime.now()}] Saved {df_name} to {output_path}")

    # Assign back to global variables for easy access
    globals().update(timetable_data)

print("UTARA timetables extracted successfully.")

print("#" * 60)
print("Listing all parquet files in the timetables folder...")
data_dir = os.path.join(os.getcwd(), "timetables") 
parquet_files = [f for f in os.listdir(data_dir) if f.endswith('.parquet')]
print(f"Total {len(parquet_files)} parquet files found.")
for i, f in enumerate(parquet_files, start=1):
    print(f" {i} - {f}")
print("Script completed.")
