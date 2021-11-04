import re
import json
import pandas as pd
from os.path import isfile
from numpy import nan
from urllib.request import urlopen
from datetime import datetime, timedelta, timezone
from pyowm import OWM
from pyowm.utils import timestamps, formatting
from html.parser import HTMLParser
from catboost import CatBoostRegressor

mapping = {
    "pol_data": {
        1: "https://mosecom.mos.ru/turistskaya/",
        2: "https://mosecom.mos.ru/koptevskij/",
        3: "https://mosecom.mos.ru/ostankino-0/",
        4: "https://mosecom.mos.ru/glebovskaya/",
        5: "https://mosecom.mos.ru/spiridonovka/",
        6: "https://mosecom.mos.ru/shabolovka/",
        7: "https://mosecom.mos.ru/akademika-anoxina/",
        8: "https://mosecom.mos.ru/butlerova/",
        9: "https://mosecom.mos.ru/proletarskij-prospekt/",
        10: "https://mosecom.mos.ru/marino/"
    },
    "weather_data": {
        1: {"lat": 55.856324, "lon": 37.426628},
        2: {"lat": 55.833222, "lon": 37.525158},
        3: {"lat": 55.821154, "lon": 37.612592},
        4: {"lat": 55.811801, "lon": 37.71249},
        5: {"lat": 55.759354, "lon": 37.595584},
        6: {"lat": 55.715698, "lon": 37.6052377},
        7: {"lat": 55.658163, "lon": 37.471434},
        8: {"lat": 55.649412, "lon": 37.535874},
        9: {"lat": 55.635129, "lon": 37.658684},
        10: {"lat": 55.652695, "lon": 37.751502}
 
    }
}
    
    
with open("owm_api_key", "r") as f:
    owm_api_key = f.readline().strip()
    
class MeteoprofileHTMLParser(HTMLParser):
    
    datetimes = []
    heights = []
    temperatures = []
    
    
    def handle_starttag(self, tag, attrs):
        is_data_element = False
        if tag == "rect":
            for attr in attrs:
                if attr[0] == "class" and attr[1] == "data-element":
                    is_data_element = True
                if is_data_element:
                    if attr[0] == "data-val":
                        temperature = attr[1]
                        if temperature == "Нет данных":
                            temperature = nan
                        else:
                            temperature = float(temperature)
                        self.temperatures.append(temperature)
                    if attr[0] == "data-height":
                        height = int(attr[1])                        
                        self.heights.append(height)
                    if attr[0] == "data-date":
                        datetime = attr[1]
                        self.datetimes.append(datetime)             
    
   
    def get_data(self):
        with urlopen("https://mosecom.mos.ru/meteo/profilemery/ostankino/") as url:          
            data = url.read().decode()
            self.feed(data)
            
        result = pd.DataFrame({"datetime": self.datetimes,
               "height": self.heights,
               "temperature": self.temperatures})
        result.dropna(inplace=True)
        result["datetime"] = pd.to_datetime(result["datetime"], format="%d.%m.%Y %H:%M")
        result["datetime"] = pd.to_datetime(result["datetime"].dt.tz_localize("Europe/Moscow"))
        
        def rename_cols(x):
            if x == "datetime":
                return x
            return f"t_{x}m"
        
        
        result = result.groupby("height").resample("1h", on="datetime").mean().reset_index(level=1).\
            pivot(index="datetime", columns="height", values="temperature").reset_index().\
            rename(mapper=rename_cols, axis=1)
        
        # Add columns not present in the data to preserve data structure
        result["outside_temperature"] = result["t_0m"]
        result["253_wind_direction"] = nan
        result["253_wind_speed"] = nan
        
        return result
    
def get_external_data(station_number):
    pollution_data = fetch_pollution_data(station_number)
    pollution_dataframe = pollution_data_to_dataframe(pollution_data)
    meteoprofile_dataframe = MeteoprofileHTMLParser().get_data()
    mp_dataframe = pollution_dataframe.merge(meteoprofile_dataframe, how="left", on="datetime")
    weather_dataframe = get_weather_data(station_number)
    data = weather_dataframe.merge(mp_dataframe, how="left", on="datetime")
    return data


def fetch_pollution_data(station_number):
    link = mapping["pol_data"][station_number]
    with urlopen(link) as url:
        page_src = url.read().decode()
        pol_data_src = re.findall("AirCharts.init.*", page_src)[0]
        pol_data_start = len("AirCharts.init(")
        pol_data_end = pol_data_src.find(', {"months"')
        pol_data_str = pol_data_src[pol_data_start:pol_data_end]
        pol_data_dict = json.loads(pol_data_str)
        return pol_data_dict


def pollution_data_to_dataframe(pollution_data):
    dataframes = {}
    longest = [0, ""]
    hourly_data = pollution_data["units"]["h"]
    for pollutant_name in ["CO", "NO", "NO2", "PM2.5", "PM10"]:
        if pollutant_name not in hourly_data:
            continue
        timestamps = []
        concentrations = []
        for data_tuple in hourly_data[pollutant_name]["data"]:
            timestamps.append(data_tuple[0])
            concentrations.append(data_tuple[1])
        pollutant_name = pollutant_name.lower().replace(".", "")
        pollutant_data = pd.DataFrame({"datetime": timestamps,
                                      pollutant_name: concentrations})
        dataframes[pollutant_name] = pollutant_data
        if pollutant_data.shape[0] > longest[0]:
            longest = [pollutant_data.shape[0], pollutant_name]
    if longest[0] == 0:
        print("No data for station.")
        result = None
    else:
        result = dataframes[longest[1]]
        for name, df in dataframes.items():
            if name == longest[1]:
                continue
            result = result.merge(df, on="datetime")
    result["datetime"] = pd.to_datetime(result["datetime"], unit="ms")
    result["datetime"] = pd.to_datetime(result["datetime"].dt.tz_localize("Europe/Moscow"))
    return result


def get_weather_data(station_number):
    owm = OWM(owm_api_key)
    mgr = owm.weather_manager()
    coords = mapping["weather_data"][station_number]
    forecast_data = get_weather_forecast(mgr, coords)
    historical_data = get_weather_history(mgr, coords)
    weather_data = historical_data.append(forecast_data).drop_duplicates(subset="datetime")
    weather_data["datetime"] = pd.to_datetime(weather_data["datetime"])

    return weather_data
    
    
def get_weather_forecast(owm_manager, point_coordinates):
    owm_station = owm_manager.one_call(**point_coordinates)
    station_weather_forecast = {
        "datetime": [],
        "temperature": [],
        "wind_speed": [],
        "wind_direction": [],
        "pressure": [],
        "humidity": [],
        "precipitation": []
    }

    for hourly_data in owm_station.forecast_hourly:
        station_weather_forecast["datetime"].append(datetime.fromtimestamp(hourly_data.ref_time,\
                                                                           tz=timezone(timedelta(hours=3),\
                                                                           name="Europe/Moscow")))
        station_weather_forecast["temperature"].append(hourly_data.temperature("celsius").get("temp"))    
        station_weather_forecast["wind_speed"].append(hourly_data.wind()["speed"])
        station_weather_forecast["wind_direction"].append(hourly_data.wind()["deg"])
        station_weather_forecast["humidity"].append(hourly_data.humidity)
        station_weather_forecast["pressure"].append(hourly_data.pressure["press"])
        
        precipitation = hourly_data.rain.get("1h", 0) + hourly_data.snow.get("1h", 0)
        station_weather_forecast["precipitation"].append(precipitation)

    result = pd.DataFrame(station_weather_forecast)
    return result

def get_weather_history(owm_manager, point_coordinates):
    today = int(datetime.now().timestamp())
    yesterday = formatting.to_UNIXtime(timestamps.yesterday())

    owm_station_hist_today = owm_manager.one_call_history(**point_coordinates, dt=today)
    owm_station_hist_yesterday = owm_manager.one_call_history(**point_coordinates, dt=yesterday)
    owm_station_hist = owm_station_hist_yesterday.forecast_hourly + owm_station_hist_today.forecast_hourly
    
    station_weather_hist = {
        "datetime": [],
        "temperature": [],
        "wind_speed": [],
        "wind_direction": [],
        "pressure": [],
        "humidity": [],        
        "precipitation": []
    }

    for hourly_data in owm_station_hist:
        station_weather_hist["datetime"].append(datetime.fromtimestamp(hourly_data.ref_time,\
                                                                      tz=timezone(timedelta(hours=3),\
                                                                                  name="Europe/Moscow")))
        station_weather_hist["temperature"].append(hourly_data.temperature("celsius").get("temp"))    
        station_weather_hist["wind_speed"].append(hourly_data.wind()["speed"])
        station_weather_hist["wind_direction"].append(hourly_data.wind()["deg"])
        station_weather_hist["humidity"].append(hourly_data.humidity)
        station_weather_hist["pressure"].append(hourly_data.pressure["press"])
        
        precipitation = hourly_data.rain.get("1h", 0) + hourly_data.snow.get("1h", 0)
        station_weather_hist["precipitation"].append(precipitation)

    result = pd.DataFrame(station_weather_hist)
    return result


def generate_features(data):
    # Split by pollutant
    pollutants = ["co", "no2", "no", "pm10", "pm25"]

    features = {}
    for pollutant_name in pollutants:
        if pollutant_name in data.columns:
            cols_to_remove = [p for p in pollutants if p in data.columns and p != pollutant_name]
            data_part = data.drop(cols_to_remove, axis=1)
            data_part.rename({pollutant_name: "pollutant_concentration"}, axis=1,inplace=True)
            features[pollutant_name] = data_part
        
    for pollutant_name, table in features.items():
        table["month"] = table["datetime"].dt.month
        table["day"] = table["datetime"].dt.day
        table["day_of_week"] = table["datetime"].dt.weekday
        table["hour"] = table["datetime"].dt.hour
        table.index = pd.Index(table.datetime)
        table.drop("datetime", axis=1, inplace=True)
    

        # Generate historical features
        hist_features = ["temperature", "wind_speed", "wind_direction",\
                                "pressure", "humidity", "precipitation", "pollutant_concentration"]

        for timeshift in [*range(1, 25)] + [168]:
            for feature in hist_features:
                if feature not in list(table.columns):
                    continue
                col_name = feature + "_prev_" + str(timeshift) + "h"
                col_value = table[feature].shift(timeshift)
                table[col_name] = col_value

        # Generate forecast features
        forecast_features = ["temperature", "wind_speed", "wind_direction",\
                                "pressure", "humidity", "precipitation"]

        for timeshift in range(1, 25):
            for feature in forecast_features:
                col_name = feature + "_forecast_" + str(timeshift) + "h"
                col_value = table[feature].shift(-timeshift)
                table[col_name] = col_value
        

        
        # Leave only row with current state
        current_row_datetime = datetime.now(tz=timezone(timedelta(hours=3), name="Europe/Moscow")).strftime("%Y/%m/%d %H:00:00")
        now = pd.to_datetime(current_row_datetime)
        row = table.loc[table.index == current_row_datetime]
        
        features[pollutant_name] = row
    
    return features


def get_predictions(station_number, data):
    predictions = {}
    now = pd.Timestamp(data[list(data)[0]].index.to_pydatetime()[0])
    for pollutant_name, features in data.items():
        model_path = f"pretrained_models/{station_number}_{pollutant_name}.cbm"
        if not isfile(model_path):
            print(f"Model for {pollutant_name.upper()} on station {station_number} is not found. Skipping this pollutant.")
            continue
        model = CatBoostRegressor()
        model.load_model(model_path)
        prediction = model.predict(features)
        prediction[prediction < 0] = 0.0
        predictions[pollutant_name] = prediction[0]
    result = pd.DataFrame(predictions)
    result.insert(0, "datetime", pd.date_range(now, periods = result.shape[0], freq="1h"))
    result = result.round({"co": 2, "no": 4, "no2": 4, "pm25": 4, "pm10": 4})
    return result


def join_history_and_forecast(current_data, forecast_data):
    col_names = forecast_data.columns
    first_forecast_datetime = forecast_data.iat[0, 0]
    current_pollution_data = current_data.loc[current_data["datetime"] < first_forecast_datetime, col_names]
    result = current_pollution_data.append(forecast_data).reset_index(drop=True)
    return result


def get_data(station_number):
    if station_number not in range(1, 11):
        print("Station number must be between 1 and 10.")
        return None
    
    current_data = get_external_data(station_number)
    features = generate_features(current_data)
    forecast_data = get_predictions(station_number, features)
    result = join_history_and_forecast(current_data, forecast_data)
    return result
