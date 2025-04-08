import blpapi

# Connection options
options = blpapi.SessionOptions()
options.setServerHost("localhost")
options.setServerPort(8194)

# Start session
session = blpapi.Session(options)
if not session.start():
    print("Failed to start session. Is the Bloomberg Terminal running?")
    exit()

# Open reference data service
if not session.openService("//blp/refdata"):
    print("Failed to open service.")
    exit()

# Create and configure the request
refDataService = session.getService("//blp/refdata")
request = refDataService.createRequest("ReferenceDataRequest")

# Specify the stock (security)
request.getElement("securities").appendValue("AAPL US Equity")  # Example: Apple stock
request.getElement("fields").appendValue("NEWS_SENTIMENT")  # Sentiment score

# Send the request
try:
    session.sendRequest(request)
except Exception as e:
    print(f"Error sending request: {e}")
    session.stop()
    exit()

# Process the response
sentiment_data = []
while True:
    event = session.nextEvent(500)  # Timeout in milliseconds
    if event.eventType() == blpapi.Event.RESPONSE:
        for msg in event:
            securityData = msg.getElement("securityData")
            for security in securityData.values():
                ticker = security.getElementAsString("security")
                fieldData = security.getElement("fieldData")
                if fieldData.hasElement("NEWS_SENTIMENT"):
                    sentiment = fieldData.getElementAsFloat("NEWS_SENTIMENT")
                    # Normalize from -1 to 1 to 0 to 1
                    normalized_sentiment = (sentiment + 1) / 2
                    sentiment_data.append({
                        "ticker": ticker,
                        "original_sentiment": sentiment,
                        "normalized_sentiment": normalized_sentiment
                    })
        break

session.stop()

# Print parsed sentiment data
for item in sentiment_data:
    print(f"{item['ticker']}: Original News Sentiment = {item['original_sentiment']}, Normalized Sentiment (0-1) = {item['normalized_sentiment']:.2f}")
