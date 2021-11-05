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
import dash_bootstrap_components as dbc

app = dash.Dash(__name__, 
                external_stylesheets=[dbc.themes.BOOTSTRAP])

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

plot = px.line()

app.layout = html.Div(children=[
    html.Div(children=[html.H1("Virtual.env", style={"font-size": 40, "color": "#fff", "margin-left": 52})], className="d-flex w-100", style={
    "height": "7vh",
    "background-image": "linear-gradient(to right, #EC0E43, #0000A8)",}),
    html.Div(children=[
    html.Div(children=[
    html.Div(children=[html.Label("Станция мониторинга", className="mt-4"),
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
                                    value=1,
                                    className="mb-3",
                                    clearable=False),
                            html.Label("Дата"),
                            dcc.Dropdown(id="date",
                                         options=[{"label": "15.01.2021", "value": "2021-01-15"}],
                                         value="2021-01-15",
                                         className="mb-3",
                                         clearable=False,
                                         searchable=False),
                            html.Label("Загрязнитель"),
                            dcc.Dropdown(id="pollutant",
                                         options=[],
                                         value="",
                                         clearable=False,
                                         searchable=False
                                        )], className="col-3"),
                                         
    html.Div(children=[
    dl.Map([dl.TileLayer(),
           *stations,
           dl.FeatureGroup(id="user_click")],
           center=(55.752004, 37.617734),
           zoom=10,
           style={'width': '100%', 'height': '100%'},
           id="map"),
    dcc.Graph(id="station_plot",
              figure=plot,
              style={"position": "absolute", "bottom": 0, "z-index": "1000", "width": "100%", "height": "40%", "padding": "15px"})
], className="col-9 g-0", style={"height": "93vh", "position": "relative"})], className="row")
    
    ], className="container-fluid", style={"height": "100%"})])
    
    
@app.callback(
    Output(component_id="user_click", component_property="children"),
    Input(component_id="map", component_property="click_lat_lng"),
    prevent_initial_call=True
    )
def add_marker(click_lat_lng):
    return [dl.Circle(center=click_lat_lng, radius=16, color="#EC0E43", fill=True, fillOpacity=1, stroke=False),
            dl.Circle(center=click_lat_lng, radius=160, color="#78797A", fill=True, fillOpacity=0.3, stroke=False)]

@app.callback(
    Output(component_id="station", component_property="value"),
    Input(component_id="map", component_property="click_lat_lng"),
    prevent_initial_call=True
    )
def select_nearset_station(latlng):
    click_lat = latlng[0]
    click_lon = latlng[1]
    with open("stations.csv", "r") as f:
        reader = csv.reader(f)
        nearest_station = 0
        min_distance = 1000
        for row in reader:
            station_id = int(row[0])
            lat = float(row[2])
            lon = float(row[3])
            distance = ((lat - click_lat)**2 + (lon-click_lon)**2)**0.5
            if distance < min_distance:
                min_distance = distance
                nearest_station = station_id
    return nearest_station

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
    default_value = options[1]["value"]
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
    

    

if __name__ == '__main__':
    app.run_server(debug=True) 
