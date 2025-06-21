import { useEffect, useState } from "react";

interface StockData {
  current_price: number;
  delta_percentage: number;
  day_low: number;
  day_high: number;
  currency: string;
}

interface StockResponse {
  [key: string]: StockData | { error: string };
}

interface HNStory {
  title: string;
  url: string;
  score: number;
  by: string;
  time: number;
  comments_count: number;
}

interface Weather {
  forecast: {
    date: string;
    current_temp: number;
    min_temp: number;
    max_temp: number;
    status: string;
    description: string;
    timestamp: string;
  }[];
  sunrise: string;
  sunset: string;
}

interface Stock {
  ticker: string;
  value: number;
  type: "cash" | "stock" | "total";
  percentage: number;
}

interface Holdings {
  stocks: Stock[];
  total_value_gross: number;
  total_value_approximation: number;
}

const getWeatherEmoji = (status: string): string => {
  const weatherMap: { [key: string]: string } = {
    Clear: "☀️",
    Clouds: "☁️",
    Rain: "🌧️",
    Snow: "❄️",
    Thunderstorm: "⛈️",
    Drizzle: "🌦️",
    Mist: "🌫️",
    Fog: "🌫️",
  };
  return weatherMap[status] || "🌡️";
};

const API_BASE_URL = "http://localhost:8000";

const EInkDisplay = () => {
  const [stocks, setStocks] = useState<StockResponse>({});
  const [news, setNews] = useState<HNStory[]>([]);
  const [weather, setWeather] = useState<Weather | null>(null);
  const [holdings, setHoldings] = useState<Holdings | null>(null);

  useEffect(() => {
    const fetchStocks = async () => {
      try {
        const response = await fetch(
          `${API_BASE_URL}/stocks?tickers=CW8.PA,WPEA.PA,DDOG,^GSPC,USDEUR=X`,
        );
        const data = await response.json();
        setStocks(data);
      } catch (error) {
        console.error("Error fetching stocks:", error);
      }
    };

    const fetchNews = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/hackernews`);
        const data = await response.json();
        setNews(data);
      } catch (error) {
        console.error("Error fetching news:", error);
      }
    };

    const fetchWeather = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/weather`);
        const data = await response.json();
        setWeather(data);
      } catch (error) {
        console.error("Error fetching weather:", error);
      }
    };

    const fetchHoldings = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/holdings`);
        const data = await response.json();
        setHoldings(data);
      } catch (error) {
        console.error("Error fetching holdings:", error);
      }
    };

    // Initial fetches
    fetchStocks();
    fetchNews();
    fetchWeather();
    fetchHoldings();

    // Refresh intervals
    const stocksInterval = setInterval(fetchStocks, 5 * 60 * 1000);
    const newsInterval = setInterval(fetchNews, 15 * 60 * 1000);
    const weatherInterval = setInterval(fetchWeather, 30 * 60 * 1000);
    const holdingsInterval = setInterval(fetchHoldings, 5 * 60 * 1000); // Refresh holdings every 5 minutes

    return () => {
      clearInterval(stocksInterval);
      clearInterval(newsInterval);
      clearInterval(weatherInterval);
      clearInterval(holdingsInterval);
    };
  }, []);

  // Format timestamp to relative time
  const getRelativeTime = (timestamp: number) => {
    const now = Date.now() / 1000;
    const diff = now - timestamp;

    if (diff < 3600) {
      return `${Math.floor(diff / 60)}m`;
    } else if (diff < 86400) {
      return `${Math.floor(diff / 3600)}h`;
    } else {
      return `${Math.floor(diff / 86400)}d`;
    }
  };

  return (
    <div className="w-[800px] h-[480px] bg-white text-black p-2 flex flex-col justify-between">
      <div id="header" className="flex justify-between items-center mb-1">
        <p className="text-xl font-bold">
          {new Date().toLocaleDateString("en-US", {
            month: "long",
            day: "numeric",
            year: "numeric",
          })}
        </p>
        <div className="flex items-center gap-2">
          <div className="flex gap-2">
            <p className="text-lg">Paris</p>
            <p className="text-xs">
              <p>{weather?.sunrise} ☀️︎</p>
              <p>{weather?.sunset} 🌑</p>
            </p>
          </div>
          <div className="flex gap-1">
            {weather &&
              weather.forecast.map((day, index) => (
                <div
                  id="weather"
                  key={index}
                  className="flex items-center border border-black rounded-lg p-1 w-[80px]"
                >
                  <div className="flex flex-col items-center w-full">
                    <p className="text-sm font-semibold">
                      {new Date(day.date).toLocaleDateString("en-US", {
                        weekday: "short",
                      })}
                      <span className="text-sm">
                        {getWeatherEmoji(day.status)}
                      </span>
                    </p>
                    <p className="text-base">{day.current_temp}°C</p>
                  </div>
                </div>
              ))}
          </div>
        </div>
      </div>

      <div className="flex flex-row justify-between mb-1 gap-1">
        <div
          id="stocks"
          className="flex flex-col border border-black rounded-lg p-2 shadow-sm w-[300px]"
        >
          <h2 className="text-lg font-semibold border-b border-gray-400">
            Market Watch
          </h2>
          {Object.entries(stocks).map(([ticker, data]) => (
            <div key={ticker}>
              {"error" in data ? (
                <p className="text-xl whitespace-pre-line">
                  {ticker}: Error loading data
                </p>
              ) : (
                <>
                  <p className="text-xl whitespace-pre-line">
                    {ticker}: {data.current_price.toFixed(2)}{" "}
                    {data.currency === "USD" ? "$" : "€"} (
                    {data.delta_percentage >= 0 ? "+" : ""}
                    {data.delta_percentage.toFixed(2)}%)
                  </p>
                  <p className="text-sm whitespace-pre-line">
                    [{data.day_low.toFixed(2)}, {data.day_high.toFixed(2)}]
                  </p>
                </>
              )}
            </div>
          ))}
        </div>
        <div
          id="news"
          className="flex flex-col max-w-[500px] border border-black rounded-lg p-2 shadow-sm w-full"
        >
          <h2 className="text-lg font-semibold border-b border-gray-400">
            Top Hacker News posts
          </h2>
          {news.map((story, index) => (
            <div key={index} className="mb-2">
              <p className="text-xl">{story.title}</p>
              <p className="text-xs text-black-600">
                {story.score}pts by {story.by} {getRelativeTime(story.time)} ago
                • {story.comments_count} comments
              </p>
            </div>
          ))}
        </div>
      </div>

      <div className="flex flex-row justify-between">
        <div
          id="net-worth"
          className="flex flex-col border border-black rounded-lg p-1 shadow-sm w-full"
        >
          <h2 className="text-lg font-semibold mb-1 border-b border-gray-200 pb-1">
            Portfolio Overview
          </h2>
          {holdings && (
            <>
              <div className="grid grid-cols-3 gap-1">
                {holdings.stocks.map((stock) => (
                  <div key={stock.ticker} className="flex">
                    <p className="text-sm font-semibold w-[90px]">
                      {stock.ticker}
                    </p>
                    <p className="text-sm">
                      {stock.value.toLocaleString("fr-FR", {
                        minimumFractionDigits: 2,
                        maximumFractionDigits: 2,
                      })}{" "}
                      € {stock.type !== "total" && `(${stock.percentage}%)`}
                    </p>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
};

function App() {
  return (
    <div className="w-[800px] h-[480px]">
      <EInkDisplay />
    </div>
  );
}

export default App;
