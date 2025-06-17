from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from flask import Flask, send_file, request, jsonify
from flask_cors import CORS
import numpy as np
from PIL import Image
import requests
import json
import yfinance as yf
import os
from datetime import datetime
import time
from config import FRONTEND_URL, OPENWEATHER_API_KEY

BMP_FILE = "screenshot.bmp"

app = Flask(__name__)
CORS(app)

@app.route('/hackernews')
def get_top_hn_posts():
    # HN API endpoints
    top_stories_url = "https://hacker-news.firebaseio.com/v0/topstories.json"
    item_url = "https://hacker-news.firebaseio.com/v0/item/{}.json"

    try:
        # Get list of top story IDs
        response = requests.get(top_stories_url)
        story_ids = response.json()[:4]  # Get IDs of top 4 stories

        # Fetch details for each story
        stories = []
        for story_id in story_ids:
            story_response = requests.get(item_url.format(story_id))
            story = story_response.json()
            stories.append({
                'title': story.get('title'),
                # 'url': story.get('url'),
                'score': story.get('score'),
                # 'by': story.get('by'),
                'time': story.get('time'),
                'comments_count': story.get('descendants', 0)
            })

        return jsonify(stories), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/image')
def image_handler():
    offset = int(request.args.get("offset", 0))
    limit = int(request.args.get("limit", 0))

    image = Image.open(BMP_FILE)
    data = np.array(image, dtype=np.uint8)
    flattened_data = data.flatten()

    mxLen = min(offset + limit, len(flattened_data))
    flattened_data = flattened_data[offset:mxLen]
    s = ""
    for c in flattened_data:
        s += str(c)

    # one in 3 call the screenshot endpoint
    r = np.random.randint(0, 3)
    if r % 2 == 0:
        screenshot_handler()
    return s, 200, {'Content-Type': 'text/plain', 'Content-Length': str(len(s))}

@app.route('/screenshot')
def screenshot_handler():
    print("Taking screenshot...")
    # Configure Selenium to use headless Chromium
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument(f"--window-size={800},{619}") # 619 is to account for the chrommium top bar (619  = 480 + 139)
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--force-device-scale-factor=1")

    # Set up the Chrome driver
    service = Service("chromedriver/chromedriver")  # Ensure you have the correct chromedriver installed
    browser = webdriver.Chrome(service=service, options=chrome_options)

    try:
        browser.get(FRONTEND_URL)

        # Get the exact viewport size
        width = browser.execute_script("return window.innerWidth")
        height = browser.execute_script("return window.innerHeight")
        print(f"Viewport size: {width} x {height}")
        time.sleep(5)  # Wait for the page to load
        png = browser.save_screenshot("screenshot.png")
        image = Image.open("screenshot.png")
        image = image.convert('1', dither=Image.NONE)
        image.save(BMP_FILE, format="BMP")
        return '', 204
    except Exception as e:
        return '', 500
    finally:
        # Close the browser
        browser.quit()

@app.route('/stocks')
def get_stock_prices():
    # Get tickers from query parameter, e.g. /stocks?tickers=AAPL,MSFT,GOOGL
    tickers_param = request.args.get('tickers', '')
    if not tickers_param:
        return jsonify({'error': 'No tickers provided'}), 400

    # Split the comma-separated tickers
    tickers = tickers_param.split(',')

    try:
        results = {}
        for ticker in tickers:
            stock = yf.Ticker(ticker.strip().upper())
            # Get data for today and yesterday
            data = stock.history(period='2d')

            if not data.empty and len(data) >= 2:
                current_price = data['Close'].iloc[-1]
                yesterday_price = data['Close'].iloc[-2]
                delta_percentage = ((current_price - yesterday_price) / yesterday_price) * 100

                # Get currency information
                info = stock.info
                currency = info.get('currency', 'USD')

                results[ticker] = {
                    'current_price': round(current_price, 2),
                    'delta_percentage': round(delta_percentage, 2),
                    'day_low': round(data['Low'].iloc[-1], 2),
                    'day_high': round(data['High'].iloc[-1], 2),
                    'currency': currency
                }
            else:
                results[ticker] = {
                    'error': 'No data available'
                }

        return jsonify(results), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/weather')
def get_weather():
    try:
        # Paris coordinates
        lat = "48.8566"
        lon = "2.3522"

        # Get current weather for sunrise/sunset
        current_url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={OPENWEATHER_API_KEY}&units=metric"
        current_response = requests.get(current_url)
        current_data = current_response.json()

        # Get 5-day forecast
        forecast_url = f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={OPENWEATHER_API_KEY}&units=metric"
        forecast_response = requests.get(forecast_url)
        forecast_data = forecast_response.json()

        if current_response.status_code == 200 and forecast_response.status_code == 200:
            # Get sunrise and sunset times
            sunrise = datetime.fromtimestamp(current_data['sys']['sunrise']).strftime('%H:%M')
            sunset = datetime.fromtimestamp(current_data['sys']['sunset']).strftime('%H:%M')

            # Process the forecast data
            forecast = []
            # Group by day and get the first entry for each day
            current_date = None
            for item in forecast_data['list']:
                date = datetime.fromtimestamp(item['dt']).strftime('%Y-%m-%d')
                if date != current_date:
                    current_date = date
                    forecast.append({
                        'date': date,
                        'current_temp': round(item['main']['temp']),
                        'min_temp': round(item['main']['temp_min']),
                        'max_temp': round(item['main']['temp_max']),
                        'status': item['weather'][0]['main'],
                        'description': item['weather'][0]['description'],
                        'timestamp': datetime.now().isoformat()
                    })
                    if len(forecast) >= 8:  # Get only 7 days
                        break

            return jsonify({
                'forecast': forecast,
                'sunrise': sunrise,
                'sunset': sunset
            }), 200
        else:
            return jsonify({'error': 'Failed to fetch weather data'}), response.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/holdings')
def get_holdings():
    usd_eur_rate = yf.Ticker("USDEUR=X").history(period='1d')['Close'].iloc[-1]
    cw8_price = yf.Ticker("CW8.PA").history(period='1d')['Close'].iloc[-1]
    wpea_price = yf.Ticker("WPEA.PA").history(period='1d')['Close'].iloc[-1]
    ddog_price = yf.Ticker("DDOG").history(period='1d')['Close'].iloc[-1]

    # Update this to reflect your own holdings
    cw8 = 10 * cw8_price
    wpea = 10 * wpea_price
    ddog = 10 * ddog_price * usd_eur_rate
    cash = 5000.00

    total_value_gross = cash + cw8 + wpea + ddog
    total_value_approximation = cash + cw8 + wpea + ddog * 0.55

    stocks = [
        {
            'ticker': 'Cash',
            'value': cash,
            'type': 'cash'
        },
        {
            'ticker': 'CW8.PA',
            'value': cw8,
            'type': 'stock'
        },
        {
            'ticker': 'Total (Gross)',
            'value': total_value_gross,
            'type': 'total'
        },
        {
            'ticker': 'WPEA.PA',
            'value': wpea,
            'type': 'stock'
        },
        {
            'ticker': 'DDOG',
            'value': ddog,
            'type': 'stock'
        },
        {
            'ticker': 'Total (Net)',
            'value': total_value_approximation,
            'type': 'total'
        }
    ]

    # Calculate percentages
    for stock in stocks:
        if stock['type'] != 'total':  # Don't calculate percentage for totals
            stock['percentage'] = round((stock['value'] / total_value_gross) * 100, 2)
        else:
            stock['percentage'] = 100

    result = {
        'stocks': stocks,
        'total_value_gross': total_value_gross,
        'total_value_approximation': total_value_approximation,
    }
    return jsonify(result), 200

@app.route('/config')
def get_config():
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
        return jsonify(config), 200
    except FileNotFoundError:
        return jsonify({'error': 'Config file not found'}), 404
    except json.JSONDecodeError:
        return jsonify({'error': 'Error decoding JSON'}), 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8000)
