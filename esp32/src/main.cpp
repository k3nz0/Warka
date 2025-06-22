#include <WiFiMulti.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>

#include <GxEPD2_BW.h>
#include <GxEPD2_3C.h>
#include <GxEPD2_4C.h>
#include <GxEPD2_7C.h>

#include "config.h"

WiFiMulti wiFiMulti;

// Refer to the Wiring section in the README to see how to connect the display to the ESP32
const uint8_t PIN_EPD_BUSY = 4;
const uint8_t PIN_EPD_CS = 5;
const uint8_t PIN_EPD_RST = 16;
const uint8_t PIN_EPD_DC = 17;
const uint8_t PIN_EPD_SCK = 18;

GxEPD2_BW<GxEPD2_750_T7, GxEPD2_750_T7::HEIGHT> display(
    GxEPD2_750_T7(PIN_EPD_CS,
                  PIN_EPD_DC,
                  PIN_EPD_RST,
                  PIN_EPD_BUSY));

uint16_t DISPLAY_WIDTH = 800;
uint16_t DISPLAY_HEIGHT = 480;
uint16_t REFRESH_INTERVAL_SEC = 60; // can be overridden by remote config
const uint8_t BITS_PER_PIXEL = 8;
const int BITMAP_SIZE = 800 * 480 / BITS_PER_PIXEL;
uint8_t hexBuf[10];
uint8_t bmp[BITMAP_SIZE / 2]; // we can't store the whole bitmap in memory, so we need to split it into two parts

void setupWifi()
{
  Serial.printf("Connecting to WIFI SSID: %s\n", WIFI_SSID);
  wiFiMulti.addAP(WIFI_SSID, WIFI_PASSWORD);
  while (wiFiMulti.run() != WL_CONNECTED)
  {
    delay(100);
    Serial.println((char)WiFi.status());
  }
  Serial.println("Connected to Wifi!");
}

// used for remote config; like controlling the screen refresh interval
void loadRemoteConfig()
{
  Serial.println("Loading remote config ...");

  char url[100];
  sprintf(url, "%s/config", BASE_URL);
  HTTPClient http;
  http.begin(url);

  int httpCode = http.GET();
  if (httpCode > 0)
  {
    int sz = http.getSize();
    String payload = http.getString();
    Serial.printf("loadRemoteConfig: %s\n", payload.c_str());

    // parse the json payload
    DynamicJsonDocument doc(1024);
    DeserializationError error = deserializeJson(doc, payload);
    if (error)
    {
      Serial.print(F("deserializeJson() failed: "));
      Serial.println(error.f_str());
      return;
    }

    // check if the json contains the expected keys
    if (doc.containsKey("refresh_interval_sec"))
    {
      REFRESH_INTERVAL_SEC = doc["refresh_interval_sec"];
      Serial.printf("loadRemoteConfig: refresh_interval_sec: %d\n", REFRESH_INTERVAL_SEC);
    }
    else
    {
      Serial.printf("loadRemoteConfig: Invalid JSON format. \n%s\n", payload.c_str());
    }
  }
}

void setup()
{
  display.init(115200, true, 2, false); // USE THIS for Waveshare boards with "clever" reset circuit, 2ms reset pulse
  setupWifi();
  loadRemoteConfig();
}

void displayImage(int offset, int limit)
{
  // display image
  display.setFullWindow();
  display.firstPage();

  char url[100];
  sprintf(url, "%s/image?offset=%d&limit=%d", BASE_URL, offset, limit);
  Serial.printf("getImage: url: %s\n", url);

  HTTPClient http;
  http.begin(url);

  int httpCode = http.GET();
  Serial.printf("getImage: %d\n", httpCode);
  if (httpCode > 0)
  {
    int sz = http.getSize();
    Serial.printf("Payload size len: %d\n", sz);

    WiFiClient *stream = http.getStreamPtr();
    // given that we can't store the whole bitmap in memory, we need to split it into two iterations
    for (int iteration = 0; iteration < 2; iteration++)
    {
      for (int i = 0; i < BITMAP_SIZE / 2; i++)
        bmp[i] = 0;

      for (int i = 0; i < sz / 8 / 2; i++)
      {
        // read bytes from the stream but in practice it's 0s and 1s so every byte needs to be treated as one bit.
        int writtenBytes = stream->readBytes(hexBuf, 8);
        uint8_t byte = 0;
        for (int j = 0; j < 8; j++)
        {
          char c = (hexBuf[j] - '0');
          // 0 means black and 1 means white in the BITMAP image format
          // so we need to invert the color for the display
          c ^= 1;
          byte |= c << (7 - j);
        }
        bmp[i] = byte;
      }

      Serial.printf("Displayed image: %d/%d\n", iteration, sz);

      do
      {
        display.drawBitmap(0, iteration * display.height() / 2, bmp, display.width(), display.height() / 2, GxEPD_BLACK);
      } while (display.nextPage());
    }
  }
}

void loop()
{
  Serial.println("Loop ... ");
  displayImage(0, display.width() * display.height());
  delay(REFRESH_INTERVAL_SEC * 1000);
}
