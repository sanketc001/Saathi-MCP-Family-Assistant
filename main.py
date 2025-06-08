from mcp.server.fastmcp import FastMCP
import imaplib
import logging
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import os.path
import pickle
import yfinance as yf
import requests_cache
import requests
import pandas as pd
import time
import datetime
import json
from imdb import Cinemagoer
from pathlib import Path
import mcp.types as types
from youtube_search import YoutubeSearch
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
# from langchain_core.messages import ChatMessage, HumanMessage
# from langchain_ollama import ChatOllama

IMDB = Cinemagoer()


session = requests_cache.CachedSession('yfinance.cache')
# Create an MCP server
mcp = FastMCP("Saathi",instructions="Saathi is a personal assistant that can help you with various tasks. You can ask it to send emails, fetch stock prices, find nearby hospitals, and more. Just ask your question and Saathi will do its best to assist you.")
mail = None
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
creds=None

# Nutrition database path
NUTRITION_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'files', 'nutrition_info.json')

# Create nutrition database file if it doesn't exist
if not os.path.exists(NUTRITION_DB_PATH):
    with open(NUTRITION_DB_PATH, 'w') as file:
        json.dump({"meal_nutrition": []}, file, indent=4)

# @mcp.tool()
# def education_question(query: str) -> str:
#     """Provide information about a specific educational topic.
#     Args:
#         query (str): The educational topic or question to answer.
#     Returns:
#         str: The response from the LLM providing information about the topic along with reasoning.
#     """
    
#     llm = ChatOllama(model="granite3.2:8b")

#     messages = [
#         ChatMessage(role="control", content="thinking"),
#         HumanMessage(query),
#     ]

#     response = llm.invoke(messages)
#     print(response.content)
#     return response


@mcp.tool()
def copy_file_to_files_directory(file_path: str) -> str:
    """Copy a file to the 'files' directory.
    
    Args:
        file_path (str): The path of the file to copy.
    
    Returns:
        str: The absolute path of the copied file in the 'files' directory.
    """
    files_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'files')
    os.makedirs(files_dir, exist_ok=True)
    
    # Get the filename from the provided path
    filename = os.path.basename(file_path)
    
    # Create the destination path
    destination_path = os.path.join(files_dir, filename)
    
    # Copy the file
    try:
        with open(file_path, 'rb') as src_file:
            with open(destination_path, 'wb') as dest_file:
                dest_file.write(src_file.read())
        #process_file(destination_path)  # Process the file if needed
        return destination_path
    except Exception as e:
        return f"Error copying file: {str(e)}"


# def process_file(file_path: str) -> str:
#     """Process the file if needed. This is a placeholder function.
    
#     Args:
#         file_path (str): The path of the file to process.
    
#     Returns:
#         str: A message indicating the result of the processing.
#     """
#     # Implement Document Indexer from LlamaIndex using local Ollama endpoint for llama3.2-vision model

#     # Set up the LlamaIndex LLM with Ollama endpoint
#     llm = Ollama(model="llama3.2-vision", base_url="http://localhost:11434")

#     # Read documents from the file path's directory
#     docs = SimpleDirectoryReader(input_dir=os.path.dirname(file_path)).load_data()

#     # Create a vector index for the documents
#     index = VectorStoreIndex.from_documents(docs, llm=llm)

#     # Optionally, persist the index for later use
#     index.storage_context.persist(persist_dir=os.path.join(os.path.dirname(file_path), "llama_index"))

#     return f"Indexed {len(docs)} documents from {os.path.dirname(file_path)} using LlamaIndex and Ollama llama3.2-vision."
    
#     return f"File {file_path} processed successfully."




@mcp.tool()
def send_email(subject: str, body: str) -> str:
    """
    Send an email using Gmail SMTP.

    Args:
        subject (str): The email subject.
        body (str): The email body text.

    Returns:
        str: Success or error message.
    """
    
    sender_email = os.environ.get("GMAIL_ADDRESS", "")  # set in .env
    app_password = os.environ.get("GMAIL_APP_PASSWORD", "")  # set in .env
    recipient_email = sender_email  # Sending to self
    
    # Create the email message
    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = recipient_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))
    
    # Connect to Gmail's SMTP server
    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()  # Secure the connection
        server.login(sender_email, app_password)
        
        # Send the email
        server.sendmail(sender_email, recipient_email, msg.as_string())
        server.quit()
        return "Email sent successfully!"
    except Exception as e:
        return f"Error sending email: {e}"


@mcp.tool()
def get_info_imdb_id(imdb_id: str) -> dict:
    """Fetch movie or show information from IMDb using its IMDB ID.

    Args:
        imdb_id (str): The name of the movie to look up. e.g: "1234567"

    Returns:
        dict: A dictionary containing movie information. 
    """
    try:
        # Search for the movie
        movies = IMDB.get_movie(imdb_id)
        if not movies:
            return {"error": "Movie not found"}
        
        data={}
        # Return the movie information as a dictionary
        for key, value in movies.items():
            # print(key, value)
            if isinstance(value, list):
                data[key] = [str(item) for item in value]
            elif isinstance(value, dict):
                data[key] = {k: str(v) for k, v in value.items()}
            else:
                data[key] = str(value)
        return data
    except Exception as e:
        return {"error": str(e)}

# print(get_info_imdb_id("0111161"))

@mcp.tool()
def download_stocks_info_as_dataframe(stock_symbols: list[str], period:str="max", interval:str="1d") -> pd.DataFrame:
    """Fetch the current stock price for a given stock symbol.
    Args:
        stock_symbols (list[str]): A list of stock symbols to look up.
        period (str): The period for which to fetch the stock data (default is "max").
        interval (str): The interval for the stock data (default is "1d").
    Args:
        stock_symbol (str): The stock symbol to look up.

    Returns:
        float: The current stock price.
    """
    for ticker in stock_symbols:
        # Downloads historical market data from Yahoo Finance for the specified ticker.
        # The period ('prd') and interval ('intv') for the data are specified as string variables.
        data = yf.download(ticker, group_by="Ticker", period=period, interval=interval, session=session)
        time.sleep(5)
        # Adds a new column named 'ticker' to the DataFrame. This column is filled with the ticker symbol.
        # This step is helpful for identifying the source ticker when multiple DataFrames are combined or analyzed separately.
        data['ticker'] = ticker
    return data

# print(download_stocks_info_as_dataframe(["AAPL", "MSFT", "GOOGL"], period="1d", interval="1w"))

@mcp.tool()
def get_company_info(stock_symbol: str, period:str="1d", request_type:str='info') -> float:
    """Fetch the current stock price for a given stock symbol.

    Args:
        stock_symbol (str): The stock symbol to look up.

    Returns:
        float: The current stock price.
    """
    # Fetch the stock data using yfinance
    stock_data = yf.Ticker(stock_symbol,session=session)
    if request_type == "price":
        # Get the current stock price
        stock_price = stock_data.history(period=period)['Close'].iloc[-1]
        # Return the stock price
        return stock_price
    elif request_type == "info":
        # Get the company information
        company_info = stock_data.info
        # Return the company information
        return company_info
    elif request_type == "history":
        # Get the historical data
        historical_data = stock_data.history(period=period)
        # Return the historical data
        return historical_data
    else:
        raise ValueError("Invalid request type. Use 'price', 'info', or 'history'.")


@mcp.tool()
def connect_to_gmail_imap(user, password):
    """Establish a connection to Gmail's IMAP server.

    Args:
        user (str): The email address of the user.
        password (str): The app password for the email account.

    Returns:
        imaplib.IMAP4_SSL: An object representing the IMAP connection.

    Raises:
        Exception: If the connection or login fails.
    """
    imap_url = 'imap.gmail.com'
    try:
        global mail
        mail = imaplib.IMAP4_SSL(imap_url)
        mail.login(user, password)
        return mail
    except Exception as e:
        logging.error("Connection failed: {}".format(e))
        raise

# function to login to google using app password
def login_to_google(email: str, app_password: str) -> str:
    """Authenticate with Google using an app password.

    Args:
        email (str): The email address of the user.
        app_password (str): The app password for the email account.

    Returns:
        str: A message indicating whether the login was successful.
    """
    return f"Logged in as {email} with app password"

# Add a dynamic greeting resource
@mcp.resource("greeting://{name}")
def get_greeting(name: str) -> str:
    """Generate a personalized greeting message.

    Args:
        name (str): The name of the person to greet.

    Returns:
        str: A greeting message tailored to the provided name.
    """
    return f"Hello, {name}!"

@mcp.tool()
def get_unread_emails() -> int:
    """Retrieve the count of unread emails in the inbox.

    Args:
        mail (imaplib.IMAP4_SSL): The IMAP connection object.

    Returns:
        int: The number of unread emails in the inbox.
    """
    global mail
    mail.select('inbox')
    result, data = mail.search(None, 'UNSEEN')
    unread_email_ids = data[0].split()
    return len(unread_email_ids)


@mcp.tool()
def find_nearby_hospitals_osm(latitude: float, longitude: float, limit: int = 5):
    """
    Find nearby hospitals using OpenStreetMap Overpass API.

    Args:
        latitude (float): The latitude of the location.
        longitude (float): The longitude of the location.
        limit (int, optional): Maximum number of hospitals to return. Defaults to 5.

    Returns:
        list: List of nearby hospitals with their names and addresses.
    """
    overpass_url = "https://overpass-api.de/api/interpreter"
    query = f"""
    [out:json];
    (
      node["amenity"="hospital"](around:5000,{latitude},{longitude});
      way["amenity"="hospital"](around:5000,{latitude},{longitude});
      relation["amenity"="hospital"](around:5000,{latitude},{longitude});
    );
    out center {limit};
    """
    try:
        response = requests.post(overpass_url, data=query)
        data = response.json()

        if not data.get("elements"):
            return "No hospitals found nearby."

        hospitals = []
        for element in data["elements"][:limit]:
            name = element.get("tags", {}).get("name", "Unnamed Hospital")
            
            # Get coordinates for address lookup
            lat = element.get("lat") or element.get("center", {}).get("lat")
            lon = element.get("lon") or element.get("center", {}).get("lon")
            address = reverse_geocode_osm(lat, lon)
            
            hospitals.append(f"{name}: {address}")
        
        return hospitals
    except Exception as e:
        return f"Error: {str(e)}"


def reverse_geocode_osm(lat, lon):
    """
    Reverse geocode coordinates to human-readable address using OSM Nominatim.
    """
    nominatim_url = "https://nominatim.openstreetmap.org/reverse"
    params = {
        "format": "json",
        "lat": lat,
        "lon": lon,
        "zoom": 18,
        "addressdetails": 1
    }
    try:
        resp = requests.get(nominatim_url, params=params, headers={"User-Agent": "MCP-Agent"})
        data = resp.json()
        return data.get("display_name", "Unknown address")
    except:
        return "Unknown address"


@mcp.tool()
def get_location_from_ip():
    """
    Detect approximate location (latitude, longitude, city, country) based on public IP.

    Returns:
        dict: Contains latitude, longitude, city, region, country.
    """
    try:
        response = requests.get("http://ip-api.com/json/")
        data = response.json()

        if data.get("status") != "success":
            return {"error": "Could not determine location."}

        location = {
            "latitude": data.get("lat"),
            "longitude": data.get("lon"),
            "city": data.get("city"),
            "region": data.get("regionName"),
            "country": data.get("country"),
            "ip": data.get("query")
        }

        return location
    except Exception as e:
        return {"error": str(e)}
    

@mcp.tool()
def get_emails() -> int:
    """Retrieve the total number of emails in the inbox.

    Args:
        mail (imaplib.IMAP4_SSL): The IMAP connection object.

    Returns:
        int: The total number of emails in the inbox.
    """
    global mail
    mail.select('inbox')
    result, data = mail.search(None, 'ALL')
    email_ids = data[0].split()
    return len(email_ids)

@mcp.tool()
def get_recent_email_from_sender(sender: str) -> str:
    """Fetch the most recent email from a specified sender.

    Args:
        mail (imaplib.IMAP4_SSL): The IMAP connection object.
        sender (str): The email address of the sender to search for.

    Returns:
        str: The content of the most recent email from the sender, or a message indicating no emails were found.
    """
    global mail
    mail.select('inbox')
    result, data = mail.search(None, f'FROM "{sender}"')
    email_ids = data[0].split()
    if email_ids:
        latest_email_id = email_ids[-1]
        result, data = mail.fetch(latest_email_id, '(RFC822)')
        return data[0][1]
    else:
        return "No emails from this sender."

@mcp.tool()
def get_total_emails_from_sender(sender: str) -> int:
    """Count the total number of emails from a specified sender.

    Args:
        mail (imaplib.IMAP4_SSL): The IMAP connection object.
        sender (str): The email address of the sender to search for.

    Returns:
        int: The total number of emails from the specified sender.
    """
    global mail
    mail.select('inbox')
    result, data = mail.search(None, f'FROM "{sender}"')
    email_ids = data[0].split()
    return len(email_ids)
    
#function to get a google oauth 2.0 authorized session
@mcp.tool()
def get_google_oauth2_session() -> str:
    """Get an authorized session using Google OAuth 2.0.

    Returns:
        str: A message indicating whether the session was created successfully or if there was an error.
    """
    global creds
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    return "Google OAuth 2.0 credentials stored successfully"

#function to get google calenda events using the google api
@mcp.tool()
def get_google_calendar_events() -> str:
    """Fetch events from the user's Google Calendar.

    Returns:
        str: A message indicating whether the events were retrieved successfully or if there was an error.
    """
    global creds
    if creds is None:
        get_google_oauth2_session()
    try:
        calendar=build('calendar', 'v3', credentials=creds)
        now = datetime.datetime.utcnow().isoformat() + 'Z' # 'Z' indicates UTC time
        events_result = calendar.events().list(calendarId='primary', timeMin=now,
                                          maxResults=10, singleEvents=True,
                                          orderBy='startTime').execute()
        events = events_result.get('items', [])

        if not events:
            return 'No upcoming events found.'
        return events
    except Exception as e:
        return f'Exception: {e}'
    
# Write the complete function to extract all faces from a given image and upscale them
@mcp.tool()
def extract_and_upscale_faces(image_path: str, upscale_factor: int = 2) -> list:
    """Extract all faces from a given image and upscale them.
    
    Args:
        image_path (str): Path to the input image file.
        upscale_factor (int): Factor by which to upscale the faces (default is 2).
        
    Returns:
        list: List of paths to the extracted and upscaled face images.
    """
    import cv2
    import os
    import numpy as np
    from pathlib import Path
    
    try:
        # Create output directory
        files_dir = Path(os.path.dirname(os.path.abspath(__file__))) / 'files'
        os.makedirs(files_dir, exist_ok=True)
        
        # Read the image
        image = cv2.imread(image_path)
        if image is None:
            return [f"Error: Could not read image from {image_path}"]
        
        # Load the face cascade classifier
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        
        # Detect faces
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.1, 4)
        
        if len(faces) == 0:
            return ["No faces detected in the image"]
        
        result_paths = []
        # Extract and upscale each face
        for i, (x, y, w, h) in enumerate(faces):
            # Extract face with some margin
            margin = int(0.2 * min(w, h))
            x1 = max(0, x - margin)
            y1 = max(0, y - margin)
            x2 = min(image.shape[1], x + w + margin)
            y2 = min(image.shape[0], y + h + margin)
            
            face_img = image[y1:y2, x1:x2]
            
            # Upscale using cv2 interpolation
            upscaled_face = cv2.resize(face_img, None, 
                                     fx=upscale_factor, 
                                     fy=upscale_factor, 
                                     interpolation=cv2.INTER_CUBIC)
            
            # Save the upscaled face
            output_path = os.path.join(files_dir, f"face_{i}_upscaled.jpg")
            cv2.imwrite(output_path, upscaled_face)
            result_paths.append(output_path)
        
        return result_paths
        
    except Exception as e:
        return [f"Error processing image: {str(e)}"]

@mcp.tool()
def store_base64_to_file(filename: str, base64_data: str, file_extension: str = None) -> str:
    """Store base64 encoded binary data to a file in the 'files' directory.
    
    Args:
        filename (str): The name to give the file (without extension).
        base64_data (str): The base64 encoded binary data to store.
        file_extension (str, optional): File extension to append (without dot). 
                                       If None, no extension is added.
    
    Returns:
        str: The absolute path to the stored file, or an error message if the operation failed.
    """
    import base64
    import os
    
    try:
        # Create the files directory if it doesn't exist
        files_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'files')
        os.makedirs(files_dir, exist_ok=True)
        
        # Create the full filename with extension if provided
        if file_extension:
            # Remove leading dot if present
            if file_extension.startswith('.'):
                file_extension = file_extension[1:]
            full_filename = f"{filename}.{file_extension}"
        else:
            full_filename = filename
        
        # Create the full file path
        file_path = os.path.join(files_dir, full_filename)
        
        # Decode the base64 data
        try:
            # Try to handle the data with or without the base64 prefix
            if ',' in base64_data:
                # Handle data URIs like "data:image/jpeg;base64,/9j/4AAQSkZJRg..."
                _, encoded_data = base64_data.split(',', 1)
                binary_data = base64.b64decode(encoded_data)
            else:
                # Handle raw base64 data
                binary_data = base64.b64decode(base64_data)
        except Exception as e:
            return f"Failed to decode base64 data: {str(e)}"
        
        # Write the binary data to the file
        with open(file_path, 'wb') as f:
            f.write(binary_data)
        
        return file_path
    
    except Exception as e:
        return f"Error storing file: {str(e)}"

@mcp.tool()
def process_image_from_base64(base64_data: str, filename: str = "image", file_extension: str = "jpg") -> dict:
    """Process an image from base64 data and store it.
    
    Args:
        base64_data (str): Base64 encoded image data.
        filename (str): The name to give the file (without extension).
        file_extension (str): File extension to append (without dot).
        
    Returns:
        dict: Information about the stored image.
    """
    try:
        # Store the image
        image_path = store_base64_to_file(filename, base64_data, file_extension)
        
        if isinstance(image_path, str) and image_path.startswith("Error") or image_path.startswith("Failed"):
            return {"success": False, "message": image_path}
        
        return {
            "success": True,
            "image_path": image_path,
            "message": f"Image successfully stored at {image_path}"
        }
        
    except Exception as e:
        return {"success": False, "message": f"Error processing image: {str(e)}"}

@mcp.tool()
def fetch_website(
    url: str,
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """Fetch the content of a website and return it as text.
    Args:
        url (str): The URL of the website to fetch.
    Returns:
        list[types.TextContent | types.ImageContent | types.EmbeddedResource]: A list of content objects.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        return [types.TextContent(type="text", text=response.text)]
    except Exception as e:
        return [types.TextContent(type="text", text=f"Error fetching website: {str(e)}")]

@mcp.tool()
def search_hotels(location: str, check_in_date: str = None, check_out_date: str = None, guests: int = 2) -> dict:
    """Search for hotels on Trivago or similar hotel booking platforms.
    
    Args:
        location (str): The destination city, region, or hotel name to search for.
        check_in_date (str, optional): Check-in date in YYYY-MM-DD format.
        check_out_date (str, optional): Check-out date in YYYY-MM-DD format.
        guests (int, optional): Number of guests. Default is 2.
        
    Returns:
        dict: Search results with hotel information or error message.
    """
    import urllib.parse
    
    try:
        # If dates not provided, use current date logic
        if not check_in_date:
            today = datetime.datetime.now()
            check_in_date = today.strftime("%Y-%m-%d")
        
        if not check_out_date:
            check_in = datetime.datetime.strptime(check_in_date, "%Y-%m-%d")
            check_out = check_in + datetime.timedelta(days=1)
            check_out_date = check_out.strftime("%Y-%m-%d")
        
        # Construct the Trivago search URL
        encoded_location = urllib.parse.quote(location)
        trivago_url = f"https://www.trivago.com/en-US/lm/hotels-{encoded_location}?search=200-{encoded_location}"
        
        # Additional parameters if dates are specified
        if check_in_date and check_out_date:
            trivago_url += f"&checkin={check_in_date}&checkout={check_out_date}"
        
        if guests:
            trivago_url += f"&persons={guests}"
        
        # For demonstration purposes, return sample hotels instead of scraping
        sample_hotels = [
            {
                "name": f"Grand Hotel {location}",
                "rating": 4.5,
                "price": "$120-$250 per night",
                "amenities": ["Pool", "Spa", "Free WiFi", "Restaurant"]
            },
            {
                "name": f"Comfort Inn {location}",
                "rating": 3.8,
                "price": "$89-$150 per night",
                "amenities": ["Free Breakfast", "Gym", "Free WiFi"]
            },
            {
                "name": f"{location} Luxury Resort",
                "rating": 4.7,
                "price": "$250-$500 per night",
                "amenities": ["Pool", "Beach Access", "Spa", "Multiple Restaurants", "Fitness Center"]
            },
            {
                "name": f"Budget Stay {location}",
                "rating": 3.2,
                "price": "$65-$90 per night",
                "amenities": ["Free WiFi", "Free Parking"]
            }
        ]
            
        # Return sample data and the search URL
        return {
            "success": True,
            "message": f"Found {len(sample_hotels)} hotels in {location}",
            "search_url": trivago_url,
            "hotels": sample_hotels,
            "dates": {
                "check_in": check_in_date,
                "check_out": check_out_date
            },
            "note": "These are sample hotels. For complete and up-to-date listings, please visit the search URL."
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error searching for hotels: {str(e)}"
        }

@mcp.tool()
def store_image_from_url(image_url: str, filename: str) -> dict:
    """Download and store an image from a URL to the files directory with a specific filename.
    
    Args:
        image_url (str): URL of the image to download.
        filename (str): Name to give the file when saving (including extension).
    
    Returns:
        dict: Information about the stored image including path and status.
    """
    import requests
    import os
    from pathlib import Path
    
    try:
        # Create the files directory if it doesn't exist
        files_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'files')
        os.makedirs(files_dir, exist_ok=True)
        
        # Set the file path for the image
        file_path = os.path.join(files_dir, filename)
        
        # Download the image
        response = requests.get(image_url, stream=True)
        response.raise_for_status()  # Raise an exception for error status codes
        
        # Save the image to a file
        with open(file_path, 'wb') as file:
            for chunk in response.iter_content(chunk_size=8192):
                file.write(chunk)
        
        return {
            "success": True,
            "message": f"Image successfully downloaded and stored as {filename}",
            "file_path": file_path
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error downloading image: {str(e)}"
        }



























#create a function to generate resources dynamically for all files in the files directory
# @mcp.resource("file://{resource_name}")
# def files() -> list[str]:
#     """List the files in the user's desktop"""
#     files = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'files')
#     if not os.path.exists(files):
#         os.makedirs(files)
#         return ["No files found"]
#     files = Path(files)
#     return [str(f) for f in files.iterdir()]


























@mcp.prompt()
def compare_tickers(symbols: str) -> str:
    """
    Compare multiple ticker symbols for the best trading opportunity
    
    Args:
        symbols: Comma-separated list of ticker symbols
    """
    symbol_list = [s.strip() for s in symbols.split(",")]
    symbol_section = "\n".join([f"- {s}" for s in symbol_list])
    
    return f"""You are a professional stock market analyst. I would like you to compare these stocks and identify the best trading opportunity:

{symbol_section}

For each stock in the list, please:

1. Check the current market data using the appropriate resource
2. Generate a comprehensive trade recommendation using the trade_recommendation tool
3. Compare all stocks based on:
   - Current trend direction and strength
   - Technical indicator signals
   - Risk/reward profile
   - Trading recommendation strength

After analyzing each stock, rank them from most promising to least promising trading opportunity. Explain your ranking criteria and why you believe the top-ranked stock represents the best current trading opportunity.

Conclude with a specific recommendation on which stock to trade and what action to take (buy, sell, or hold)."""

@mcp.prompt()
def intraday_strategy_builder(symbol: str) -> str:
    """
    Build a custom intraday trading strategy for a specific ticker
    """
    return f"""You are an expert algorithmic trader specializing in intraday strategies. I want you to develop a custom intraday trading strategy for {symbol}.

Please follow these steps:

1. First, analyze the current market data for {symbol} using the market-data resource
2. Calculate relevant technical indicators:
   - Moving averages (short and long periods)
   - RSI
3. Based on your analysis, design an intraday trading strategy that includes:
   - Specific entry conditions (technical setups that would trigger a buy/sell)
   - Exit conditions (both take-profit and stop-loss levels)
   - Position sizing recommendations
   - Optimal trading times during the day
   - Risk management rules

Make your strategy specific to the current market conditions for {symbol}, not just generic advice. Include exact indicator values and price levels where possible.

Conclude with a summary of the strategy and how a trader should implement it for today's trading session."""

@mcp.prompt()
def hotel_search_assistant(location: str) -> str:
    """
    Create a hotel search assistant prompt for a specific location
    
    Args:
        location: The destination city or region to search for hotels
    """
    return f"""You are a helpful travel assistant specializing in hotel recommendations. I'm looking for hotels in {location}.

Please help me search for suitable accommodations by:

1. Using the search_hotels tool to find available options in {location}
2. Asking me about my preferences regarding:
   - Specific check-in and check-out dates
   - Number of guests
   - Budget range
   - Hotel amenities that are important to me (pool, gym, breakfast, etc.)
   - Preferred location within {location} (downtown, near airport, etc.)

Based on my responses, refine the search and provide recommendations. If I have specific dates or requirements, use them with the search_hotels tool to get more relevant results.

If I'm just browsing without firm dates, suggest popular hotels in {location} and provide general information about the best areas to stay, seasonal considerations, and any local events that might affect hotel availability or prices."""


@mcp.prompt()
def family_saathi() -> str:
    """You are a family assistant. I want you to help me manage my family data.
    
    Please help me with the following tasks:
    1. Add a new family member
    2. Update existing family member information
    3. Retrieve all family members' information
    4. Set or update my own information
    5. Add birthday events for family members
    """
    return "I am here to assist you with your family data management."

# Family data management tools
@mcp.tool()
def get_family_members() -> dict:
    """Retrieve all family members' information.
    
    Returns:
        dict: All family member information
    """
    try:
        family_data_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'files', 'family_data.json')
        with open(family_data_path, 'r') as file:
            family_data = json.load(file)
        return family_data
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def add_family_member(name: str, relationship: str, age: int = None, birthday: str = None, notes: str = None) -> dict:
    """Add a new family member to the family data.
    
    Args:
        name (str): The name of the family member
        relationship (str): Relationship to the user (e.g. spouse, child, parent)
        age (int, optional): Age of the family member
        birthday (str, optional): Birthday in YYYY-MM-DD format
        notes (str, optional): Additional notes about the family member
    
    Returns:
        dict: Status of the operation
    """
    try:
        # Load existing family data
        family_data_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'files', 'family_data.json')
        with open(family_data_path, 'r') as file:
            family_data = json.load(file)
        
        # Create new family member
        new_member = {
            "name": name,
            "relationship": relationship
        }
        
        # Add optional fields if provided
        if age is not None:
            new_member["age"] = age
        if birthday:
            new_member["birthday"] = birthday
        if notes:
            new_member["notes"] = notes
        
        # Check if member with same name already exists
        for member in family_data.get("members", []):
            if member["name"].lower() == name.lower():
                return {"error": f"A family member with the name '{name}' already exists"}
        
        # Add new member
        family_data["members"].append(new_member)
        
        # Save updated data
        with open(family_data_path, 'w') as file:
            json.dump(family_data, file, indent=4)
        
        # Add birthday events if birthday is provided
        if birthday:
            add_birthday_events_for_family()
        
        return {"success": True, "message": f"{name} was added to your family members"}
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def update_family_member(name: str, field: str, value: str) -> dict:
    """Update a specific field for a family member.
    
    Args:
        name (str): Name of the family member to update
        field (str): Field to update (age, birthday, relationship, notes)
        value (str): New value for the field
    
    Returns:
        dict: Status of the operation
    """
    try:
        # Load existing family data
        family_data_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'files', 'family_data.json')
        with open(family_data_path, 'r') as file:
            family_data = json.load(file)
        
        # Find the member to update
        member_found = False
        for member in family_data.get("members", []):
            if member["name"].lower() == name.lower():
                member_found = True
                # Convert value to appropriate type for age
                if field.lower() == "age" and value.isdigit():
                    member[field.lower()] = int(value)
                else:
                    member[field.lower()] = value
                break
        
        # Also check if it's the user
        if not member_found and family_data.get("user", {}).get("name", "").lower() == name.lower():
            member_found = True
            if field.lower() == "age" and value.isdigit():
                family_data["user"][field.lower()] = int(value)
            else:
                family_data["user"][field.lower()] = value
        
        if not member_found:
            return {"error": f"No family member with the name '{name}' was found"}
        
        # Save updated data
        with open(family_data_path, 'w') as file:
            json.dump(family_data, file, indent=4)
        
        # Update birthday events if birthday is updated
        if field.lower() == "birthday":
            add_birthday_events_for_family()
        
        return {"success": True, "message": f"Updated {field} for {name} to {value}"}
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def set_user_info(name: str, age: int = None, birthday: str = None) -> dict:
    """Set or update the user's own information.
    
    Args:
        name (str): The name of the user
        age (int, optional): Age of the user
        birthday (str, optional): Birthday in YYYY-MM-DD format
        
    Returns:
        dict: Status of the operation
    """
    try:
        # Load existing family data
        family_data_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'files', 'family_data.json')
        if not os.path.exists(family_data_path):
            # Create a new family data file if it doesn't exist
            family_data = {"user": {}, "members": []}
            with open(family_data_path, 'w') as file:
                json.dump(family_data, file, indent=4)
        with open(family_data_path, 'r') as file:
            family_data = json.load(file)
        
        # Update or create user information
        if "user" not in family_data:
            family_data["user"] = {}
        
        family_data["user"]["name"] = name
        
        if age is not None:
            family_data["user"]["age"] = age
            
        if birthday:
            family_data["user"]["birthday"] = birthday
            
        # Save updated data
        with open(family_data_path, 'w') as file:
            json.dump(family_data, file, indent=4)
        
        # Update birthday events if birthday was set
        if birthday:
            add_birthday_events_for_family()
        
        return {"success": True, "message": f"User information updated for {name}"}
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def update_user_birthday(birthday: str) -> dict:
    """Update the user's birthday and automatically update related birthday events.
    
    Args:
        birthday (str): Birthday in YYYY-MM-DD format
        
    Returns:
        dict: Status of the operation
    """
    try:
        # Load existing family data
        family_data_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'files', 'family_data.json')
        with open(family_data_path, 'r') as file:
            family_data = json.load(file)
        
        # Update user's birthday
        if "user" not in family_data:
            return {"error": "User information not found. Please set user info first using set_user_info."}
        
        family_data["user"]["birthday"] = birthday
            
        # Save updated data
        with open(family_data_path, 'w') as file:
            json.dump(family_data, file, indent=4)
        
        # Update birthday events
        add_birthday_events_for_family()
        
        return {"success": True, "message": f"User birthday updated to {birthday}"}
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def add_relative(name: str, relation_type: str, birthday: str = None, notes: str = None) -> dict:
    """Add a relative like aunt (bua), uncle, cousin, etc. to family data.
    
    Args:
        name (str): Name of the relative
        relation_type (str): Type of relation (bua, chacha, mama, etc.)
        birthday (str, optional): Birthday in YYYY-MM-DD format
        notes (str, optional): Additional notes
    
    Returns:
        dict: Status of the operation
    """
    try:
        # Load existing family data
        family_data_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'files', 'family_data.json')
        with open(family_data_path, 'r') as file:
            family_data = json.load(file)
        
        # Create new relative data
        new_relative = {
            "name": name,
            "relationship": relation_type
        }
        
        # Add optional fields if provided
        if birthday:
            new_relative["birthday"] = birthday
        if notes:
            new_relative["notes"] = notes
        
        # Check if member with same name already exists
        for member in family_data.get("members", []):
            if member["name"].lower() == name.lower():
                return {"error": f"A family member with the name '{name}' already exists"}
        
        # Add new relative
        family_data["members"].append(new_relative)
        
        # Save updated data
        with open(family_data_path, 'w') as file:
            json.dump(family_data, file, indent=4)
        
        # Add birthday events if birthday is provided
        if birthday:
            add_birthday_events_for_family()
        
        return {"success": True, "message": f"{name} ({relation_type}) was added to your family members"}
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def get_family_summary() -> dict:
    """Get a summary of the family including all members and upcoming birthdays.
    
    Returns:
        dict: Family summary information
    """
    try:
        # Load family data
        family_data_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'files', 'family_data.json')
        with open(family_data_path, 'r') as file:
            family_data = json.load(file)
        
        # Load events data for birthdays
        events_data_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'files', 'family_events.json')
        with open(events_data_path, 'r') as file:
            events_data = json.load(file)
        
        # Get user information
        user_info = family_data.get("user", {})
        user_name = user_info.get("name", "User")
        
        # Prepare member data
        members = []
        for member in family_data.get("members", []):
            member_summary = {
                "name": member.get("name", "Unknown"),
                "relationship": member.get("relationship", "Unknown"),
            }
            
            if "age" in member:
                member_summary["age"] = member["age"]
                
            if "birthday" in member:
                member_summary["birthday"] = member["birthday"]
                
            members.append(member_summary)
        
        # Get upcoming birthdays (next 30 days)
        today = datetime.datetime.now().date()
        upcoming_birthdays = []
        
        for event in events_data.get("events", []):
            if "birthday" in event.get("title", "").lower():
                event_date = datetime.datetime.strptime(event["date"], "%Y-%m-%d").date()
                days_until = (event_date - today).days
                
                if 0 <= days_until <= 30:
                    upcoming_birthdays.append({
                        "name": event["title"].split("'")[0],
                        "date": event["date"],
                        "days_until": days_until
                    })
        
        # Sort upcoming birthdays
        upcoming_birthdays.sort(key=lambda x: x["days_until"])
        
        return {
            "user": user_info,
            "member_count": len(family_data.get("members", [])),
            "members": members,
            "upcoming_birthdays": upcoming_birthdays
        }
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def add_birthday_events_for_family() -> dict:
    """Add or update birthday events for all family members.
    
    Returns:
        dict: Status of the operation
    """
    try:
        # Load family data
        family_data_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'files', 'family_data.json')
        with open(family_data_path, 'r') as file:
            family_data = json.load(file)
        
        # Load events data
        events_data_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'files', 'family_events.json')
        if not os.path.exists(events_data_path):
            # Create a new events file if it doesn't exist
            events_data = {"events": []}
            with open(events_data_path, 'w') as file:
                json.dump(events_data, file, indent=4)

        with open(events_data_path, 'r') as file:
            events_data = json.load(file)
        
        # Extract existing events that are not birthdays
        non_birthday_events = []
        for event in events_data.get("events", []):
            if "birthday" not in event.get("id", "").lower():
                non_birthday_events.append(event)
        
        # Initialize new events list with non-birthday events
        new_events = non_birthday_events
        
        # Current year and next year
        current_year = datetime.datetime.now().year
        next_year = current_year + 1
        
        # Process user birthday
        user = family_data.get("user", {})
        if user and "birthday" in user and user["birthday"]:
            user_name = user.get("name", "User")
            user_birthday = user["birthday"]
            birthday_parts = user_birthday.split("-")
            
            if len(birthday_parts) == 3:
                month_day = "-".join(birthday_parts[1:])
                
                # Add birthday event for current year
                current_year_birthday = f"{current_year}-{month_day}"
                new_events.append({
                    "id": f"birthday_user_{current_year}",
                    "title": f"{user_name}'s Birthday",
                    "date": current_year_birthday,
                    "description": f"{user_name}'s birthday celebration",
                    "participants": [member["name"] for member in family_data.get("members", [])] + [user_name]
                })
                
                # Add birthday event for next year
                next_year_birthday = f"{next_year}-{month_day}"
                new_events.append({
                    "id": f"birthday_user_{next_year}",
                    "title": f"{user_name}'s Birthday",
                    "date": next_year_birthday,
                    "description": f"{user_name}'s birthday celebration",
                    "participants": [member["name"] for member in family_data.get("members", [])] + [user_name]
                })
        
        # Process family members' birthdays
        for member in family_data.get("members", []):
            if "birthday" in member and member["birthday"]:
                member_name = member["name"]
                member_birthday = member["birthday"]
                birthday_parts = member_birthday.split("-")
                
                if len(birthday_parts) == 3:
                    month_day = "-".join(birthday_parts[1:])
                    
                    # Add birthday event for current year
                    current_year_birthday = f"{current_year}-{month_day}"
                    new_events.append({
                        "id": f"birthday_{member_name}_{current_year}",
                        "title": f"{member_name}'s Birthday",
                        "date": current_year_birthday,
                        "description": f"{member_name}'s birthday celebration",
                        "participants": [m["name"] for m in family_data.get("members", [])] + 
                                      [user.get("name")] if user and "name" in user else []
                    })
                    
                    # Add birthday event for next year
                    next_year_birthday = f"{next_year}-{month_day}"
                    new_events.append({
                        "id": f"birthday_{member_name}_{next_year}",
                        "title": f"{member_name}'s Birthday",
                        "date": next_year_birthday,
                        "description": f"{member_name}'s birthday celebration",
                        "participants": [m["name"] for m in family_data.get("members", [])] + 
                                      [user.get("name")] if user and "name" in user else []
                    })
        
        # Update events data
        events_data["events"] = new_events
        
        # Save updated events
        with open(events_data_path, 'w') as file:
            json.dump(events_data, file, indent=4)
        
        return {"success": True, "message": "Birthday events updated for all family members"}
    except Exception as e:
        return {"error": str(e)}

# Family events management tools
@mcp.tool()
def add_family_event(title: str, date: str, description: str = None, participants: list = None) -> dict:
    """Add a new family event to the calendar.
    
    Args:
        title (str): Title of the event
        date (str): Date of the event in YYYY-MM-DD format
        description (str, optional): Description of the event
        participants (list, optional): List of family members participating
    
    Returns:
        dict: Status of the operation
    """
    try:
        # Load existing events data
        events_data_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'files', 'family_events.json')
        with open(events_data_path, 'r') as file:
            events_data = json.load(file)
        
        # Load family data to get all member names
        family_data_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'files', 'family_data.json')
        with open(family_data_path, 'r') as file:
            family_data = json.load(file)
            
        # Get user name
        user_name = family_data.get("user", {}).get("name", "User")
        
        # Generate a unique ID for the event
        event_id = f"event_{title.lower().replace(' ', '_')}_{date}"
        
        # Create event object
        event = {
            "id": event_id,
            "title": title,
            "date": date,
        }
        
        # Add optional fields
        if description:
            event["description"] = description
        else:
            event["description"] = f"Family event: {title}"
            
        if participants:
            event["participants"] = participants
        else:
            # If no participants specified, include all family members
            all_participants = [member["name"] for member in family_data.get("members", [])]
            if user_name:
                all_participants.append(user_name)
            event["participants"] = all_participants
        
        # Add event
        events_data["events"].append(event)
        
        # Save updated events
        with open(events_data_path, 'w') as file:
            json.dump(events_data, file, indent=4)
            
        return {"success": True, "message": f"Event '{title}' added on {date}"}
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def get_upcoming_events(days: int = 30) -> dict:
    """Get upcoming family events within the specified number of days.
    
    Args:
        days (int, optional): Number of days to look ahead (default: 30)
    
    Returns:
        dict: Upcoming events
    """
    try:
        # Load events data
        events_data_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'files', 'family_events.json')
        with open(events_data_path, 'r') as file:
            events_data = json.load(file)
        
        # Get today's date
        today = datetime.datetime.now().date()
        
        # Filter upcoming events
        upcoming_events = []
        
        for event in events_data.get("events", []):
            try:
                event_date = datetime.datetime.strptime(event["date"], "%Y-%m-%d").date()
                days_until = (event_date - today).days
                
                if 0 <= days_until <= days:
                    event_info = {
                        "id": event.get("id", ""),
                        "title": event.get("title", ""),
                        "date": event.get("date", ""),
                        "days_until": days_until
                    }
                    
                    if "description" in event:
                        event_info["description"] = event["description"]
                        
                    if "participants" in event:
                        event_info["participants"] = event["participants"]
                        
                    upcoming_events.append(event_info)
            except Exception:
                # Skip events with invalid dates
                continue
        
        # Sort by date
        upcoming_events.sort(key=lambda x: x["days_until"])
        
        return {
            "success": True,
            "count": len(upcoming_events),
            "events": upcoming_events
        }
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def display_upcoming_events(days: int = 365) -> dict:
    """Display upcoming family events in a human-readable format.
    
    Args:
        days (int, optional): Number of days to look ahead (default: 365)
    
    Returns:
        dict: Formatted information about upcoming events
    """
    upcoming = get_upcoming_events(days)
    
    if "error" in upcoming:
        return upcoming
    
    events_by_month = {}
    
    for event in upcoming.get("events", []):
        event_date = datetime.datetime.strptime(event["date"], "%Y-%m-%d")
        month_key = event_date.strftime("%B %Y")
        
        if month_key not in events_by_month:
            events_by_month[month_key] = []
            
        events_by_month[month_key].append({
            "day": event_date.strftime("%d"),
            "title": event["title"],
            "days_until": event["days_until"]
        })
    
    # Format for display
    display_format = {
        "success": True,
        "message": f"Upcoming events for the next {days} days",
        "events_by_month": []
    }
    
    for month, events in events_by_month.items():
        month_data = {
            "month": month,
            "events": events
        }
        display_format["events_by_month"].append(month_data)
    
    return display_format

# Budget management tools
@mcp.tool()
def add_budget_item(item_type: str, name: str, amount: float, category: str = None, date: str = None) -> dict:
    """Add a budget item (income, expenses, savings, goals).

    Args:
        item_type (str): Type of budget item (income, expenses, savings, goals)
        name (str): Name or description of the item
        amount (float): Amount in currency
        category (str, optional): Category of the item
        date (str, optional): Date in YYYY-MM-DD format
    
    Returns:
        dict: Status of the operation
    """
    try:
        # Validate item type
        valid_types = ["income", "expenses", "savings", "goals"]
        if item_type.lower() not in valid_types:
            return {"error": f"Invalid item type. Must be one of: {', '.join(valid_types)}"}
        
        # Load budget data
        budget_data_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'files', 'budget_data.json')
        if not os.path.exists(budget_data_path):
            # Create a new budget data file if it doesn't exist
            budget_data = {"income": [], "expenses": [], "savings": [], "goals": []}
            with open(budget_data_path, 'w') as file:
                json.dump(budget_data, file, indent=4)

        with open(budget_data_path, 'r') as file:
            budget_data = json.load(file)
        
        # Create the budget item
        new_item = {
            "name": name,
            "amount": amount,
            "timestamp": time.time()
        }
        
        # Add optional fields if provided
        if category:
            new_item["category"] = category
        if date:
            new_item["date"] = date
        else:
            # If no date provided, use current date
            new_item["date"] = datetime.datetime.now().strftime("%Y-%m-%d")
        
        # Add to appropriate list based on type
        item_type = item_type.lower()
        budget_data[item_type].append(new_item)
        
        # Save updated data
        with open(budget_data_path, 'w') as file:
            json.dump(budget_data, file, indent=4)
            
        return {
            "success": True, 
            "message": f"Added {item_type} item: {name} ({amount})"
        }
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def get_budget_summary() -> dict:
    """Get a summary of the budget.
    
    Returns:
        dict: Budget summary
    """
    try:
        # Load budget data
        budget_data_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'files', 'budget_data.json')
        with open(budget_data_path, 'r') as file:
            budget_data = json.load(file)
        
        # Calculate totals
        total_income = sum(item["amount"] for item in budget_data.get("income", []))
        total_expenses = sum(item["amount"] for item in budget_data.get("expenses", []))
        total_savings = sum(item["amount"] for item in budget_data.get("savings", []))
        total_goals = sum(item["amount"] for item in budget_data.get("goals", []))
        
        # Calculate net (income - expenses)
        net = total_income - total_expenses
        
        # Group expenses by category
        expenses_by_category = {}
        for expense in budget_data.get("expenses", []):
            category = expense.get("category", "Uncategorized")
            if category not in expenses_by_category:
                expenses_by_category[category] = 0
            expenses_by_category[category] += expense["amount"]
        
        # Get recent transactions (last 10)
        all_transactions = []
        
        # Add income
        for item in budget_data.get("income", []):
            all_transactions.append({
                "type": "Income",
                "name": item["name"],
                "amount": item["amount"],
                "date": item.get("date", ""),
                "timestamp": item.get("timestamp", 0)
            })
        
        # Add expenses
        for item in budget_data.get("expenses", []):
            all_transactions.append({
                "type": "Expense",
                "name": item["name"],
                "amount": -item["amount"],  # Negative for expenses
                "category": item.get("category", "Uncategorized"),
                "date": item.get("date", ""),
                "timestamp": item.get("timestamp", 0)
            })
        
        # Sort by timestamp (recent first) and limit to 10
        all_transactions.sort(key=lambda x: x.get("timestamp", 0), reverse=True)
        recent_transactions = all_transactions[:10]
        
        return {
            "summary": {
                "total_income": total_income,
                "total_expenses": total_expenses,
                "total_savings": total_savings,
                "total_goals": total_goals,
                "net_balance": net,
                "savings_ratio": (total_savings / total_income) * 100 if total_income > 0 else 0
            },
            "expenses_by_category": expenses_by_category,
            "recent_transactions": recent_transactions
        }
    except Exception as e:
        return {"error": str(e)}

# Grocery list and meal plan management tools
@mcp.tool()
def add_grocery_list(name: str, items: list) -> dict:
    """Add a new grocery list.
    
    Args:
        name (str): Name of the grocery list
        items (list): List of items to buy
    
    Returns:
        dict: Status of the operation
    """
    try:
        # Load grocery data
        grocery_data_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'files', 'grocery_lists.json')
        if not os.path.exists(grocery_data_path):
            # Create a new grocery data file if it doesn't exist
            grocery_data = {"lists": []}
            with open(grocery_data_path, 'w') as file:
                json.dump(grocery_data, file, indent=4)
        with open(grocery_data_path, 'r') as file:
            grocery_data = json.load(file)
        
        # Create the new grocery list
        new_list = {
            "id": f"list_{int(time.time())}",
            "name": name,
            "created": datetime.datetime.now().strftime("%Y-%m-%d"),
            "items": items
        }
        
        # Add to lists
        grocery_data["lists"].append(new_list)
        
        # Save updated data
        with open(grocery_data_path, 'w') as file:
            json.dump(grocery_data, file, indent=4)
            
        return {
            "success": True, 
            "message": f"Added grocery list: {name} with {len(items)} items"
        }
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def get_grocery_lists() -> dict:
    """Get all grocery lists.
    
    Returns:
        dict: All grocery lists
    """
    try:
        # Load grocery data
        grocery_data_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'files', 'grocery_lists.json')
        with open(grocery_data_path, 'r') as file:
            grocery_data = json.load(file)
            
        return grocery_data
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def add_meal_plan(week_starting: str, meals: dict) -> dict:
    """Add a meal plan for a specific week.
    
    Args:
        week_starting (str): Start date of the week in YYYY-MM-DD format
        meals (dict): Dictionary with days as keys and meal details as values
    
    Returns:
        dict: Status of the operation
    """
    try:
        # Load meal plan data
        meal_plan_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'files', 'meal_plans.json')
        if not os.path.exists(meal_plan_path):
            # Create a new meal plan file if it doesn't exist
            meal_plan_data = {"plans": []}
            with open(meal_plan_path, 'w') as file:
                json.dump(meal_plan_data, file, indent=4)

        with open(meal_plan_path, 'r') as file:
            meal_plan_data = json.load(file)
        
        # Create the meal plan
        new_plan = {
            "id": f"plan_{week_starting}",
            "week_starting": week_starting,
            "meals": meals
        }
        
        # Check if a plan for this week already exists
        for i, plan in enumerate(meal_plan_data.get("plans", [])):
            if plan.get("week_starting") == week_starting:
                # Replace the existing plan
                meal_plan_data["plans"][i] = new_plan
                
                # Save updated data
                with open(meal_plan_path, 'w') as file:
                    json.dump(meal_plan_data, file, indent=4)
                    
                return {
                    "success": True, 
                    "message": f"Updated meal plan for week starting {week_starting}"
                }
        
        # If no existing plan, add a new one
        meal_plan_data["plans"].append(new_plan)
        
        # Save updated data
        with open(meal_plan_path, 'w') as file:
            json.dump(meal_plan_data, file, indent=4)
            
        return {
            "success": True, 
            "message": f"Added meal plan for week starting {week_starting}"
        }
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def add_meal_nutrition(meal_id: str, meal_name: str, calories: int, proteins: float, carbs: float, fats: float, vitamins: dict = None, notes: str = None) -> dict:
    """Add nutrition information for a specific meal.
    
    Args:
        meal_id (str): Unique identifier for the meal (e.g., "Monday_breakfast_2025-05-12")
        meal_name (str): Name of the meal
        calories (int): Total calories in the meal
        proteins (float): Protein content in grams
        carbs (float): Carbohydrate content in grams
        fats (float): Fat content in grams
        vitamins (dict, optional): Dictionary of vitamins and their amounts
        notes (str, optional): Additional nutritional notes
    
    Returns:
        dict: Status of the operation
    """
    try:
        # Load nutrition data
        if os.path.exists(NUTRITION_DB_PATH):
            with open(NUTRITION_DB_PATH, 'r') as file:
                nutrition_data = json.load(file)
        else:
            nutrition_data = {"meal_nutrition": []}
        
        # Create nutrition entry
        nutrition_entry = {
            "meal_id": meal_id,
            "meal_name": meal_name,
            "calories": calories,
            "macronutrients": {
                "proteins": proteins,
                "carbohydrates": carbs,
                "fats": fats
            },
            "updated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        if vitamins:
            nutrition_entry["vitamins"] = vitamins
            
        if notes:
            nutrition_entry["notes"] = notes
        
        # Check if entry for this meal already exists
        for i, entry in enumerate(nutrition_data.get("meal_nutrition", [])):
            if entry.get("meal_id") == meal_id:
                # Update existing entry
                nutrition_data["meal_nutrition"][i] = nutrition_entry
                
                # Save updated data
                with open(NUTRITION_DB_PATH, 'w') as file:
                    json.dump(nutrition_data, file, indent=4)
                    
                return {
                    "success": True, 
                    "message": f"Updated nutrition info for meal: {meal_name}"
                }
        
        # If no existing entry, add a new one
        nutrition_data["meal_nutrition"].append(nutrition_entry)
        
        # Save updated data
        with open(NUTRITION_DB_PATH, 'w') as file:
            json.dump(nutrition_data, file, indent=4)
            
        return {
            "success": True, 
            "message": f"Added nutrition info for meal: {meal_name}"
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to add nutrition information: {str(e)}"
        }

@mcp.tool()
def get_meal_nutrition(meal_id: str = None, date_range: list = None) -> dict:
    """Get nutrition information for specific meals or within a date range.
    
    Args:
        meal_id (str, optional): Unique identifier for a specific meal
        date_range (list, optional): List with start and end dates in YYYY-MM-DD format
    
    Returns:
        dict: Nutrition information for the requested meals
    """
    try:
        # Load nutrition data
        if not os.path.exists(NUTRITION_DB_PATH):
            return {
                "success": False,
                "message": "No nutrition data available"
            }
            
        with open(NUTRITION_DB_PATH, 'r') as file:
            nutrition_data = json.load(file)
        
        # If meal_id is provided, return info for that specific meal
        if meal_id:
            for entry in nutrition_data.get("meal_nutrition", []):
                if entry.get("meal_id") == meal_id:
                    return {
                        "success": True,
                        "data": entry
                    }
            
            return {
                "success": False,
                "message": f"No nutrition information found for meal ID: {meal_id}"
            }
        
        # If date_range is provided, filter entries by date
        elif date_range and len(date_range) == 2:
            start_date = date_range[0]
            end_date = date_range[1]
            
            filtered_entries = []
            for entry in nutrition_data.get("meal_nutrition", []):
                # Extract date from meal_id (assuming format ends with YYYY-MM-DD)
                meal_date = entry.get("meal_id", "").split("_")[-1]
                
                if meal_date and start_date <= meal_date <= end_date:
                    filtered_entries.append(entry)
            
            return {
                "success": True,
                "count": len(filtered_entries),
                "data": filtered_entries
            }
        
        # If no specific filters provided, return all entries
        else:
            return {
                "success": True,
                "count": len(nutrition_data.get("meal_nutrition", [])),
                "data": nutrition_data.get("meal_nutrition", [])
            }
            
    except Exception as e:
        return {
            "success": False,
            "message": f"Error retrieving nutrition information: {str(e)}"
        }

@mcp.tool()
def calculate_nutrition_summary(period: str, date: str) -> dict:
    """Calculate a summary of nutritional intake for a specific day or week.
    
    Args:
        period (str): Type of period to calculate ('day' or 'week')
        date (str): The specific date in YYYY-MM-DD format. For 'week', this is the start date.
    
    Returns:
        dict: Summary of nutritional intake for the requested period
    """
    try:
        # Load nutrition data
        if not os.path.exists(NUTRITION_DB_PATH):
            return {
                "success": False,
                "message": "No nutrition data available"
            }
            
        with open(NUTRITION_DB_PATH, 'r') as file:
            nutrition_data = json.load(file)
        
        # Initialize counters
        total_calories = 0
        total_proteins = 0
        total_carbs = 0
        total_fats = 0
        meal_count = 0
        
        # Get date range for filtering
        if period == 'day':
            start_date = date
            end_date = date
        elif period == 'week':
            start_date = date
            # Convert to datetime to calculate end date
            start_dt = datetime.datetime.strptime(date, "%Y-%m-%d")
            end_dt = start_dt + datetime.timedelta(days=6)
            end_date = end_dt.strftime("%Y-%m-%d")
        else:
            return {
                "success": False,
                "message": "Invalid period. Use 'day' or 'week'."
            }
        
        # Filter meals by date range
        included_meals = []
        for entry in nutrition_data.get("meal_nutrition", []):
            # Extract date from meal_id (assuming format ends with YYYY-MM-DD)
            meal_id_parts = entry.get("meal_id", "").split("_")
            if len(meal_id_parts) >= 3:
                meal_date = meal_id_parts[-1]
                
                if meal_date and start_date <= meal_date <= end_date:
                    included_meals.append(entry)
                    total_calories += entry.get("calories", 0)
                    total_proteins += entry.get("macronutrients", {}).get("proteins", 0)
                    total_carbs += entry.get("macronutrients", {}).get("carbohydrates", 0)
                    total_fats += entry.get("macronutrients", {}).get("fats", 0)
                    meal_count += 1
        
        # Calculate daily averages for week
        if period == 'week' and meal_count > 0:
            daily_avg_calories = total_calories / 7
            daily_avg_proteins = total_proteins / 7
            daily_avg_carbs = total_carbs / 7
            daily_avg_fats = total_fats / 7
        else:
            daily_avg_calories = total_calories
            daily_avg_proteins = total_proteins
            daily_avg_carbs = total_carbs
            daily_avg_fats = total_fats
        
        return {
            "success": True,
            "period": period,
            "start_date": start_date,
            "end_date": end_date,
            "meal_count": meal_count,
            "total_nutrition": {
                "calories": total_calories,
                "proteins": total_proteins,
                "carbohydrates": total_carbs,
                "fats": total_fats
            },
            "daily_average": {
                "calories": round(daily_avg_calories, 2),
                "proteins": round(daily_avg_proteins, 2),
                "carbohydrates": round(daily_avg_carbs, 2),
                "fats": round(daily_avg_fats, 2)
            },
            "included_meals": included_meals
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error calculating nutrition summary: {str(e)}"
        }

@mcp.tool()
def analyze_meal_nutrition(meal_description: str) -> dict:
    """Analyze a meal description and estimate its nutritional content.
    
    Args:
        meal_description (str): Description of the meal
        
    Returns:
        dict: Estimated nutritional content
    """
    try:
        # This is a simplified estimation based on common meal ingredients
        # In a real implementation, you might use a nutrition API or database
        
        # Calculate base nutrition values
        base_calories = 0
        base_proteins = 0
        base_carbs = 0
        base_fats = 0
        
        # Simple rules for estimation (this is very basic and imprecise)
        meal_lower = meal_description.lower()
        
        # Protein sources
        if any(food in meal_lower for food in ["chicken", "beef", "fish", "salmon", "tuna", "eggs", "paneer", "tofu"]):
            base_proteins += 20
            base_calories += 150
            base_fats += 8
        
        # Additional protein for specific items
        if "salmon" in meal_lower or "tuna" in meal_lower:
            base_proteins += 5
            base_fats += 5
            
        if "eggs" in meal_lower:
            base_proteins += 6
            base_fats += 5
            base_calories += 70
            
        if "paneer" in meal_lower or "tofu" in meal_lower:
            base_proteins += 12
            base_fats += 6
            
        # Carb sources
        if any(food in meal_lower for food in ["rice", "bread", "pasta", "naan", "potato", "quinoa", "oatmeal"]):
            base_carbs += 30
            base_calories += 150
            
        # Additional carbs for specific items
        if "whole grain" in meal_lower or "brown rice" in meal_lower:
            base_carbs += 5
            base_proteins += 2
            
        if "oatmeal" in meal_lower:
            base_carbs += 25
            base_proteins += 5
            base_calories += 150
        
        # Vegetables and fruits
        if any(food in meal_lower for food in ["vegetable", "salad", "spinach", "broccoli", "asparagus", "cabbage"]):
            base_carbs += 10
            base_calories += 50
            
        # Fruits
        if any(food in meal_lower for food in ["fruit", "berry", "banana", "apple", "mango", "orange"]):
            base_carbs += 15
            base_calories += 80
            
        # Nuts and healthy fats
        if any(food in meal_lower for food in ["nuts", "avocado", "olive oil", "coconut"]):
            base_fats += 10
            base_calories += 120
        
        # Dairy
        if any(food in meal_lower for food in ["yogurt", "cheese", "milk", "raita"]):
            base_proteins += 7
            base_fats += 5
            base_calories += 100
            
        # Beans and legumes
        if any(food in meal_lower for food in ["beans", "lentil", "chickpea", "rajma"]):
            base_proteins += 7
            base_carbs += 20
            base_calories += 120
            
        # Adjust for meal type
        if "breakfast" in meal_lower:
            base_calories = max(300, base_calories)
        elif "lunch" in meal_lower:
            base_calories = max(400, base_calories)
        elif "dinner" in meal_lower:
            base_calories = max(500, base_calories)
        elif "snack" in meal_lower:
            base_calories = min(200, base_calories)
            
        # Generate vitamins estimate
        vitamins = {
            "A": "low" if not any(food in meal_lower for food in ["carrot", "spinach", "sweet potato"]) else "high",
            "C": "low" if not any(food in meal_lower for food in ["orange", "lemon", "bell pepper", "broccoli"]) else "high",
            "D": "low" if not any(food in meal_lower for food in ["fish", "egg"]) else "moderate",
            "Iron": "low" if not any(food in meal_lower for food in ["spinach", "lentil", "meat"]) else "high"
        }
        
        return {
            "success": True,
            "meal": meal_description,
            "estimated_nutrition": {
                "calories": round(base_calories),
                "proteins": round(base_proteins, 1),
                "carbohydrates": round(base_carbs, 1),
                "fats": round(base_fats, 1)
            },
            "vitamin_content": vitamins,
            "note": "This is a rough estimation. For accurate nutrition data, please consult a nutritionist or use specialized nutrition databases."
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error analyzing meal nutrition: {str(e)}"
        }

# Windows Calendar Reminder Tool
@mcp.tool()
def create_windows_calendar_reminder(title: str, date: str, start_time: str, duration: int = 60, description: str = None, location: str = None) -> dict:
    """Create a reminder in Windows Calendar using Outlook COM interface.
    
    Args:
        title (str): Title of the reminder/appointment
        date (str): Date in YYYY-MM-DD format
        start_time (str): Start time in HH:MM format (24-hour)
        duration (int, optional): Duration in minutes (default: 60)
        description (str, optional): Description of the appointment
        location (str, optional): Location of the appointment
    
    Returns:
        dict: Status of the operation
    """
    try:
        # Try to import win32com.client
        try:
            import win32com.client
        except ImportError:
            return {
                "success": False,
                "message": "win32com.client is not installed. Please install it using 'pip install pywin32'"
            }
        
        # Parse the date and time
        try:
            date_parts = list(map(int, date.split('-')))
            time_parts = list(map(int, start_time.split(':')))
            
            start_datetime = datetime.datetime(
                year=date_parts[0],
                month=date_parts[1],
                day=date_parts[2],
                hour=time_parts[0],
                minute=time_parts[1]
            )
            
            end_datetime = start_datetime + datetime.timedelta(minutes=duration)
        except Exception as e:
            return {
                "success": False,
                "message": f"Error parsing date or time: {str(e)}"
            }
        
        # Create an Outlook application object
        outlook = win32com.client.Dispatch("Outlook.Application")
        
        # Get the namespace
        namespace = outlook.GetNamespace("MAPI")
        
        # Get the calendar folder
        calendar = namespace.GetDefaultFolder(9)  # 9 corresponds to the calendar folder
        
        # Create a new appointment item
        appointment = calendar.Items.Add()
        
        # Set appointment properties
        appointment.Subject = title
        appointment.Start = start_datetime.strftime("%Y-%m-%d %H:%M")
        appointment.End = end_datetime.strftime("%Y-%m-%d %H:%M")
        
        if description:
            appointment.Body = description
            
        if location:
            appointment.Location = location
        
        # Set a reminder (15 minutes by default)
        appointment.ReminderSet = True
        appointment.ReminderMinutesBeforeStart = 15
        
        # Save the appointment
        appointment.Save()
        
        return {
            "success": True,
            "message": f"Calendar reminder '{title}' created for {date} at {start_time}",
            "details": {
                "title": title,
                "start_datetime": start_datetime.strftime("%Y-%m-%d %H:%M"),
                "end_datetime": end_datetime.strftime("%Y-%m-%d %H:%M"),
                "duration_minutes": duration
            }
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Error creating calendar reminder: {str(e)}"
        }

@mcp.tool()
def create_family_calendar_reminder(family_member: str, event_type: str, date: str, start_time: str, duration: int = 60, description: str = None, location: str = None) -> dict:
    """Create a calendar reminder for a family member event.
    
    Args:
        family_member (str): Name of the family member
        event_type (str): Type of event (e.g., birthday, doctor appointment, etc.)
        date (str): Date in YYYY-MM-DD format
        start_time (str): Start time in HH:MM format (24-hour)
        duration (int, optional): Duration in minutes (default: 60)
        description (str, optional): Additional description
        location (str, optional): Location of the event
    
    Returns:
        dict: Status of the operation
    """
    try:
        # Load family data to verify the family member exists
        family_data_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'files', 'family_data.json')
        with open(family_data_path, 'r') as file:
            family_data = json.load(file)
        
        # Check if the family member exists
        member_exists = False
        for member in family_data.get("members", []):
            if member["name"].lower() == family_member.lower():
                member_exists = True
                break
        
        # Also check if it's the user
        if not member_exists and family_data.get("user", {}).get("name", "").lower() == family_member.lower():
            member_exists = True
        
        if not member_exists:
            return {
                "success": False,
                "message": f"No family member named '{family_member}' found"
            }
        
        # Create a title for the reminder
        title = f"{family_member}'s {event_type}"
        
        # Generate a description if not provided
        if not description:
            description = f"Event for {family_member}: {event_type}"
        
        # Create the reminder in Windows Calendar
        result = create_windows_calendar_reminder(
            title=title,
            date=date,
            start_time=start_time,
            duration=duration,
            description=description,
            location=location
        )
        
        # If calendar reminder was created successfully, also add to family events
        if result.get("success", False):
            try:
                # Add to family events
                add_family_event(
                    title=title,
                    date=date,
                    description=description,
                    participants=[family_member]
                )
                
                result["message"] += " and added to family events"
            except Exception as e:
                result["message"] += f" but failed to add to family events: {str(e)}"
        
        return result
    except Exception as e:
        return {
            "success": False,
            "message": f"Error creating family calendar reminder: {str(e)}"
        }

@mcp.tool()
def get_nutrition_suggestions(week_starting: str = None) -> dict:
    """Provide nutritional suggestions based on meal plans.
    
    Args:
        week_starting (str, optional): Week start date in YYYY-MM-DD format. 
                                      If not provided, uses the most recent meal plan.
    
    Returns:
        dict: Nutritional suggestions and insights
    """
    try:
        # Load meal plans
        meal_plan_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'files', 'meal_plans.json')
        if not os.path.exists(meal_plan_path):
            return {
                "success": False,
                "message": "No meal plans available"
            }
            
        with open(meal_plan_path, 'r') as file:
            meal_plan_data = json.load(file)
            
        plans = meal_plan_data.get("plans", [])
        if not plans:
            return {
                "success": False,
                "message": "No meal plans available"
            }
        
        # Get the target meal plan
        target_plan = None
        if week_starting:
            for plan in plans:
                if plan.get("week_starting") == week_starting:
                    target_plan = plan
                    break
        else:
            # Use the most recent plan
            target_plan = plans[-1]
            
        if not target_plan:
            return {
                "success": False,
                "message": f"No meal plan found for week starting {week_starting}"
            }
        
        # Analyze meals in the plan
        meals_by_type = {
            "breakfast": [],
            "lunch": [],
            "dinner": [],
            "snacks": []
        }
        
        protein_sources = []
        vegetable_count = 0
        fruit_count = 0
        whole_grain_count = 0
        
        # Process each day's meals
        for day, day_meals in target_plan.get("meals", {}).items():
            for meal_type, meal_desc in day_meals.items():
                if meal_type.lower() in meals_by_type:
                    meals_by_type[meal_type.lower()].append(meal_desc)
                    
                    # Count nutrition components
                    meal_lower = meal_desc.lower()
                    
                    # Check protein sources
                    for protein in ["chicken", "fish", "beef", "tofu", "eggs", "paneer", "beans", "lentils"]:
                        if protein in meal_lower and protein not in protein_sources:
                            protein_sources.append(protein)
                            
                    # Check vegetables
                    for veg in ["vegetable", "spinach", "broccoli", "carrot", "salad", "asparagus", "cabbage"]:
                        if veg in meal_lower:
                            vegetable_count += 1
                            break
                            
                    # Check fruits
                    for fruit in ["fruit", "berry", "apple", "banana", "orange", "mango"]:
                        if fruit in meal_lower:
                            fruit_count += 1
                            break
                            
                    # Check whole grains
                    for grain in ["whole grain", "brown rice", "quinoa", "oatmeal"]:
                        if grain in meal_lower:
                            whole_grain_count += 1
                            break
        
        # Generate suggestions based on analysis
        suggestions = []
        
        # Protein variety
        if len(protein_sources) < 3:
            suggestions.append("Consider adding more variety to protein sources in your meals.")
            
        # Vegetable intake
        if vegetable_count < 7:  # At least one per day
            suggestions.append("Try to include vegetables in more meals throughout the week.")
            
        # Fruit intake
        if fruit_count < 7:  # At least one per day
            suggestions.append("Consider adding more fruits to your meals or snacks.")
            
        # Whole grain intake
        if whole_grain_count < 5:
            suggestions.append("Try to include more whole grains in place of refined grains.")
            
        # Balance of meal types
        if len(meals_by_type["breakfast"]) < 7:
            suggestions.append("Make sure to include breakfast every day for sustained energy.")
            
        # Generate meal-specific suggestions
        meal_suggestions = {
            "breakfast": "Consider adding protein to breakfast for better satiety and energy balance.",
            "lunch": "Try to include a balance of protein, complex carbohydrates, and vegetables at lunch.",
            "dinner": "Keep dinners lighter with plenty of vegetables and moderate portions of protein.",
            "snacks": "Choose nutrient-dense snacks with protein and fiber to maintain energy levels."
        }
        
        return {
            "success": True,
            "week_starting": target_plan.get("week_starting"),
            "nutritional_analysis": {
                "protein_variety": len(protein_sources),
                "protein_sources": protein_sources,
                "vegetable_servings": vegetable_count,
                "fruit_servings": fruit_count,
                "whole_grain_servings": whole_grain_count
            },
            "general_suggestions": suggestions,
            "meal_specific_suggestions": meal_suggestions,
            "daily_targets": {
                "vegetables": "At least 2-3 servings per day",
                "fruits": "1-2 servings per day",
                "protein": "Include in every meal, aiming for 0.8g per kg of body weight daily",
                "whole_grains": "Make at least half of grain intake whole grains",
                "water": "Aim for 2-3 liters per day"
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Error generating nutrition suggestions: {str(e)}"
        }














@mcp.tool()
def youtube_search(query: str) -> dict:
    """Search for YouTube videos based on a query.
    
    Args:
        query (str): Search query for YouTube.
    
    Returns:
        dict: Video Search results.
    """
    try:
        # Perform the search
        results = YoutubeSearch(query, max_results=2).to_dict()

        return results
    except Exception as e:
        return {
            "success": False,
            "message": f"Error searching YouTube: {str(e)}"
        }