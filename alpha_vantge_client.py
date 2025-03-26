import urllib3
import logging
import requests
import pandas as pd
import time
import numpy as np
import os
import ssl
import socket
import certifi



# Set up logging
urllib3.connectionpool.HTTPSConnectionPool.debuglevel = 1
logging.basicConfig(level=logging.DEBUG)
logging.getLogger("urllib3").setLevel(logging.DEBUG)

def test_connectivity(self):
    """Test network connectivity and Alpha Vantage API availability"""
    print("[INFO] Testing network connectivity...")
    
    # Test general internet connectivity first
    try:
        response = self.session.get("https://www.google.com", timeout=5)
        print(f"[INFO] Internet connection: OK (status {response.status_code})")
    except Exception as e:
        print(f"[ERROR] Internet connection failed: {e}")
        print("[ERROR] Please check your network connection")
        return False
    
    # Test Alpha Vantage connectivity
    try:
        response = self.session.get(f"{self.base_url}?function=TIME_SERIES_INTRADAY&symbol=IBM&interval=1min&apikey={self.api_key}", timeout=5)
        if response.status_code == 200:
            print("[INFO] Alpha Vantage API connection: OK")
            return True
        else:
            print(f"[ERROR] Alpha Vantage API returned error: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"[ERROR] Alpha Vantage API connection failed: {e}")
        return False

# Debug certificate information
print(f"[DEBUG] Certificate path: {certifi.where()}")
print(f"[DEBUG] Certificate exists: {os.path.exists(certifi.where())}")

class AlphaVantageClient:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://www.alphavantage.co/query"
        self.last_request_time = 0
        
        # Create a session with proper configuration
        self.session = requests.Session()
        self.session.mount('https://', requests.adapters.HTTPAdapter(
            max_retries=3,
            pool_connections=1,
            pool_maxsize=10
        ))
        
        # Use certifi's certificate bundle for the session
        self.session.verify = certifi.where()
        
    def test_ssl_connection(self):
        """Test SSL connection to Alpha Vantage"""
        print("[DEBUG] Testing SSL connection to Alpha Vantage...")
        context = ssl.create_default_context()
        
        try:
            with socket.create_connection(("www.alphavantage.co", 443)) as sock:
                with context.wrap_socket(sock, server_hostname="www.alphavantage.co") as ssock:
                    print(f"[DEBUG] SSL connection established. Certificate info:")
                    cert = ssock.getpeercert()
                    print(f"[DEBUG] Issued to: {cert.get('subject')}")
                    print(f"[DEBUG] Issued by: {cert.get('issuer')}")
                    print(f"[DEBUG] Valid until: {cert.get('notAfter')}")
                    return True
        except Exception as e:
            print(f"[DEBUG] SSL connection test failed: {e}")
            return False
    
    def test_connectivity(self):
        """Test network connectivity and Alpha Vantage API availability"""
        print("[INFO] Testing network connectivity...")
        
        # Test general internet connectivity first
        try:
            response = self.session.get("https://www.google.com", timeout=5)
            print(f"[INFO] Internet connection: OK (status {response.status_code})")
        except Exception as e:
            print(f"[ERROR] Internet connection failed: {e}")
            print("[ERROR] Please check your network connection")
            return False
        
        # Test Alpha Vantage connectivity
        try:
            response = self.session.get(
                f"{self.base_url}?function=TIME_SERIES_INTRADAY&symbol=IBM&interval=1min&apikey={self.api_key}", 
                timeout=5
            )
            if response.status_code == 200:
                print("[INFO] Alpha Vantage API connection: OK")
                return True
            else:
                print(f"[ERROR] Alpha Vantage API returned error: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"[ERROR] Alpha Vantage API connection failed: {e}")
            return False
            
    def get_stock_data(self, symbol, output_size="full", max_retries=3):
        """
        Get daily stock data from Alpha Vantage with retry mechanism
        
        Parameters:
        -----------
        symbol: str
            Stock symbol
        output_size: str
            'compact' for last 100 data points, 'full' for all data
        max_retries: int
            Maximum number of retry attempts
            
        Returns:
        --------
        pandas.DataFrame
            DataFrame with stock data
        """
        for attempt in range(max_retries):
            try:
                # Rate limiting
                current_time = time.time()
                time_since_last_request = current_time - self.last_request_time
                if time_since_last_request < 12:
                    time.sleep(12 - time_since_last_request)
                
                # Build request parameters
                params = {
                    "function": "TIME_SERIES_DAILY",
                    "symbol": symbol,
                    "outputsize": output_size,
                    "datatype": "json",
                    "apikey": self.api_key
                }
                
                # Make the request
                print(f"[INFO] Fetching data for {symbol} from Alpha Vantage (Attempt {attempt+1}/{max_retries})")
                response = self.session.get(self.base_url, params=params, timeout=30)
                self.last_request_time = time.time()
                
                # Check if request was successful
                if response.status_code != 200:
                    print(f"[ERROR] API request failed: {response.status_code} - {response.text}")
                    continue
                
                # Parse the response
                data = response.json()
                
                # Check for error messages
                if "Error Message" in data:
                    print(f"[ERROR] API error: {data['Error Message']}")
                    continue
                
                # Extract time series data
                if "Time Series (Daily)" not in data:
                    print(f"[WARNING] No time series data found in response: {data}")
                    continue
                    
                time_series = data["Time Series (Daily)"]
                
                # Convert to DataFrame
                df = pd.DataFrame.from_dict(time_series, orient="index")
                
                # Rename columns to match the expected format used by the existing code
                df.rename(columns={
                    "1. open": "open",
                    "2. high": "high",
                    "3. low": "low",
                    "4. close": "4. close",  # Keep this as "4. close" to match existing code
                    "5. volume": "volume"
                }, inplace=True)
                
                # Convert to numeric
                for col in df.columns:
                    df[col] = pd.to_numeric(df[col])
                
                # Sort index in ascending order and set proper datetime index
                df.index = pd.to_datetime(df.index)
                df.sort_index(inplace=True)
                
                print(f"[INFO] Retrieved {len(df)} days of data for {symbol}")
                
                return df
                
            except requests.exceptions.RequestException as e:
                wait_time = (2 ** attempt) * 3  # Exponential backoff
                print(f"[WARNING] Connection error on attempt {attempt+1}/{max_retries}. Retrying in {wait_time}s: {e}")
                time.sleep(wait_time)
        
        print(f"[ERROR] Failed to fetch stock data after {max_retries} attempts")
        return None
    
    def get_symbol_search(self, keywords, max_retries=3):
        """
        Search for company symbols with Alpha Vantage with retry mechanism
        
        Parameters:
        -----------
        keywords: str
            Search keywords
        max_retries: int
            Maximum number of retry attempts
            
        Returns:
        --------
        list
            List of matching symbols
        """
        for attempt in range(max_retries):
            try:
                # Rate limiting
                current_time = time.time()
                time_since_last_request = current_time - self.last_request_time
                if time_since_last_request < 12:
                    time.sleep(12 - time_since_last_request)
                
                # Build request parameters
                params = {
                    "function": "SYMBOL_SEARCH",
                    "keywords": keywords,
                    "datatype": "json",
                    "apikey": self.api_key
                }
                
                # Make the request
                print(f"[INFO] Searching for '{keywords}' on Alpha Vantage (Attempt {attempt+1}/{max_retries})")
                response = self.session.get(self.base_url, params=params, timeout=15)
                self.last_request_time = time.time()
                
                # Check if request was successful
                if response.status_code != 200:
                    print(f"[ERROR] API request failed: {response.status_code} - {response.text}")
                    continue
                
                # Parse the response
                data = response.json()
                
                # Check for error messages
                if "Error Message" in data:
                    print(f"[ERROR] API error: {data['Error Message']}")
                    continue
                
                # Extract matches
                if "bestMatches" not in data or not data["bestMatches"]:
                    print(f"[WARNING] No matches found for '{keywords}'")
                    return []
                    
                # Return list of symbols with descriptions
                results = []
                for match in data["bestMatches"]:
                    results.append({
                        "symbol": match.get("1. symbol", ""),
                        "name": match.get("2. name", ""),
                        "type": match.get("3. type", ""),
                        "region": match.get("4. region", "")
                    })
                
                return results
                
            except requests.exceptions.RequestException as e:
                wait_time = (2 ** attempt) * 3  # Exponential backoff
                print(f"[WARNING] Connection error on attempt {attempt+1}/{max_retries}. Retrying in {wait_time}s: {e}")
                time.sleep(wait_time)
        
        print(f"[ERROR] Failed to search symbols after {max_retries} attempts")
        return None
    
    def get_company_overview(self, symbol, max_retries=3):
        """
        Get company overview data from Alpha Vantage with retry mechanism
        
        Parameters:
        -----------
        symbol: str
            Stock symbol
        max_retries: int
            Maximum number of retry attempts
            
        Returns:
        --------
        dict
            Company overview data
        """
        for attempt in range(max_retries):
            try:
                # Rate limiting
                current_time = time.time()
                time_since_last_request = current_time - self.last_request_time
                if time_since_last_request < 12:
                    time.sleep(12 - time_since_last_request)
                
                # Build request parameters
                params = {
                    "function": "OVERVIEW",
                    "symbol": symbol,
                    "apikey": self.api_key
                }
                
                # Make the request
                print(f"[INFO] Fetching company overview for {symbol} (Attempt {attempt+1}/{max_retries})")
                response = self.session.get(self.base_url, params=params, timeout=15)
                self.last_request_time = time.time()
                
                # Process response
                if response.status_code != 200:
                    print(f"[ERROR] API request failed: {response.status_code} - {response.text}")
                    continue
                
                data = response.json()
                if not data or "Error Message" in data:
                    print(f"[WARNING] No company overview data found for {symbol}")
                    return None
                    
                return data
                
            except requests.exceptions.RequestException as e:
                wait_time = (2 ** attempt) * 3  # Exponential backoff
                print(f"[WARNING] Connection error on attempt {attempt+1}/{max_retries}. Retrying in {wait_time}s: {e}")
                time.sleep(wait_time)
        
        print(f"[ERROR] Failed to fetch company overview after {max_retries} attempts")
        return None
        
    def get_global_quote(self, symbol, max_retries=3):
        """
        Get current quote for a symbol with retry mechanism
        
        Parameters:
        -----------
        symbol: str
            Stock symbol
        max_retries: int
            Maximum number of retry attempts
            
        Returns:
        --------
        dict
            Quote data
        """
        for attempt in range(max_retries):
            try:
                # Rate limiting
                current_time = time.time()
                time_since_last_request = current_time - self.last_request_time
                if time_since_last_request < 12:
                    time.sleep(12 - time_since_last_request)
                
                # Build request parameters
                params = {
                    "function": "GLOBAL_QUOTE",
                    "symbol": symbol,
                    "apikey": self.api_key
                }
                
                # Make the request
                print(f"[INFO] Fetching current quote for {symbol} (Attempt {attempt+1}/{max_retries})")
                response = self.session.get(self.base_url, params=params, timeout=15)
                self.last_request_time = time.time()
                
                # Check if request was successful
                if response.status_code != 200:
                    print(f"[ERROR] API request failed: {response.status_code} - {response.text}")
                    continue
                
                # Parse the response
                data = response.json()
                
                # Check if data is empty or has error
                if not data or "Error Message" in data or "Global Quote" not in data:
                    print(f"[WARNING] No quote data found for {symbol}")
                    return None
                    
                quote_data = data["Global Quote"]
                
                # Create simplified quote dictionary
                quote = {
                    "symbol": quote_data.get("01. symbol", ""),
                    "price": float(quote_data.get("05. price", 0)),
                    "change": float(quote_data.get("09. change", 0)),
                    "change_percent": quote_data.get("10. change percent", "")
                }
                    
                return quote
                
            except requests.exceptions.RequestException as e:
                wait_time = (2 ** attempt) * 3  # Exponential backoff
                print(f"[WARNING] Connection error on attempt {attempt+1}/{max_retries}. Retrying in {wait_time}s: {e}")
                time.sleep(wait_time)
        
        print(f"[ERROR] Failed to fetch global quote after {max_retries} attempts")
        return None
