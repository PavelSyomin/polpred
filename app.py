import dash
from dash import dcc
from dash import html
import dash_leaflet as dl
import dash_leaflet.express as dlx
import csv
from dash.dependencies import Output, Input
import pandas as pd
import plotly.express as px
from predictor import Predictor

app = dash.Dash(__name__)

P = Predictor()

with open("stations.csv", "r") as f:
    reader = csv.reader(f)
    stations = []
    for row in reader:
        station_id = row[0]
        station_name = row[1]
        lat = float(row[2])
        lon = float(row[3])
        station = dl.CircleMarker(center=(lat, lon), id=f"station_{station_id}")
        stations.append(station)

pollutant_options = {
    "co": {"label": "Оксид углерода (CO)", "value": "co"},
    "no": {"label": "Оксид азота (NO)", "value": "no"},
    "no2": {"label": "Диоксид азота (NO2)", "value": "no2"},
    "pm25": {"label": "Пыль (PM25)", "value": "pm25"},
    "pm10": {"label": "Пыль (PM10)", "value": "pm10"}
    }

plot = px.line()

app.layout = html.Div(children=[
    html.H1(children='Прогноз загрязнения воздуха в Москве'),

    html.Div(children=["Выберите станцию",
                       dcc.Dropdown(id="station",
                                    options=[
                                        {"label": "Туристская", "value": 1},
                                        {"label": "Коптевский бульвар", "value": 2},
                                        {"label": "Останкино 0", "value": 3},
                                        {"label": "Глебовская", "value": 4},
                                        {"label": "Спиридоновка", "value": 5},
                                        {"label": "Шаболовка", "value": 6},
                                        {"label": "Академика Анохина", "value": 7},
                                        {"label": "Бутлерова", "value": 8},
                                        {"label": "Пролетарский проспект", "value": 9},
                                        {"label": "Марьино", "value": 10}
                                        ],
                                    value=1)]),
                            dcc.Dropdown(id="date",
                                         options=[],
                                         value=""),
                            dcc.Dropdown(id="pollutant",
                                         options=[],
                                         value=""
                                         ),
                                         

    dl.Map([dl.TileLayer(),
           *stations],
           center=(55.752004, 37.617734),
           zoom=10,
           style={'width': '100%', 'height': '500px'},
           id="map"),
    dcc.Graph(id="station_plot",
              figure=plot)
])
    
    
'''@app.callback(
    Output(component_id="station_1", component_property="color"),
    Input(component_id="map", component_property="click_lat_lng")
    )
def change_color(click_lat_lng):
    return "red"'''

@app.callback(
    Output(component_id="station_plot", component_property="figure"),
    Input(component_id="station", component_property="value"),
    Input(component_id="date", component_property="value"),
    Input(component_id="pollutant", component_property="value")
    )
def update_plot(station_id, date, pollutant):
    df = P.get_data(station_id, date)
    plot = px.line(df, x="datetime", y=pollutant)
    return plot

@app.callback(
    Output(component_id="date", component_property="options"),
    Output(component_id="date", component_property="value"),
    Input(component_id="station", component_property="value")
    )
def get_dates_for_station(station_id):
    options = P.get_date_options(station_id)
    default_value = options[0]["value"]
    return options, default_value

@app.callback(
    Output(component_id="pollutant", component_property="options"),
    Output(component_id="pollutant", component_property="value"),
    Input(component_id="station", component_property="value"),
    Input(component_id="date", component_property="value"),
    )
def get_pollutants_for_station(station_id, date):
    options = P.get_pollutant_options(station_id, date)
    default_value = options[0]["value"]
    return options, default_value
    
'''@app.callback(
    Output(component_id="map", component_property="center"),
    Input(component_id="station", component_property="value")
    )
def highlight_station(input_value):
    station = stations[input_value-1]'''
    
    

if __name__ == '__main__':
    app.run_server(debug=True) 
