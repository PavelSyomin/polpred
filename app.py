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
    stations = {}
    station_markers = []
    for row in reader:
        station_id = int(row[0])
        station_name = row[1]
        lat = float(row[2])
        lon = float(row[3])
        station_marker = dl.CircleMarker(center=(lat, lon), id=f"station_{station_id}", color="#0000A8")
        station_markers.append(station_marker)
        stations[station_id] = (lat, lon, station_name)

plot = px.line()

app.layout = html.Div(children=[
    html.Div(children=[
        html.Div(children=[
            html.Div("4 Virtual.env", style={"font-size": 28, "font-weight": "bold", "color": "#fff"}, className="col-3"),
            html.Div("Прогноз загрязнения воздуха в Москве", className="col-9",
                    style={"font-size": 28, "color": "#fff", "line-height": "1.2"})], className="row align-items-baseline",
            style={
            "height": "7vh",
            "background-image": "linear-gradient(to right, #EC0E43, #0000A8)"}),
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
                                         options=[{"label": "Сейчас", "value": "now"}],
                                         value="now",
                                         className="mb-3",
                                         clearable=False,
                                         searchable=False),
                            html.Label("Загрязнитель"),
                            dcc.Dropdown(id="pollutant",
                                         options=[],
                                         value="",
                                         clearable=False,
                                         searchable=False
                                        ),
                            html.Div(children=[], id="station_info")], className="col-3"),
                                         
    html.Div(children=[
    dl.Map([dl.TileLayer(),
           *station_markers,
           dl.FeatureGroup(id="user_click"),
           dl.FeatureGroup(children=[dl.CircleMarker(center=(55.856324, 37.426628), color="#EC0E43", fill=False)], id="highlighted")],
           center=(55.752004, 37.617734),
           zoom=10,
           style={'width': '100%', 'height': '100%'},
           id="map"),
    dcc.Graph(id="station_plot",
              figure=plot,
              style={"position": "absolute", "bottom": 0, "z-index": "1000", "width": "100%", "height": "40%", "padding": "5px"})
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
        nearest_station_coords = (0, 0)
        min_distance = 1000
        for row in reader:
            station_id = int(row[0])
            lat = float(row[2])
            lon = float(row[3])
            distance = ((lat - click_lat)**2 + (lon-click_lon)**2)**0.5
            if distance < min_distance:
                min_distance = distance
                nearest_station = station_id
                nearest_station_coords = (lat, lon)
    highlighted_marker = dl.CircleMarker(center=nearest_station_coords, color="#EC0E43", fill=False)
    zoom = 13
    return nearest_station

@app.callback(
    Output(component_id="station_plot", component_property="figure"),
    Output(component_id="station_info", component_property="children"),
    Input(component_id="station", component_property="value"),
    Input(component_id="date", component_property="value"),
    Input(component_id="pollutant", component_property="value")
    )
def update_plot_and_info(station_id, date, pollutant):
    df = P.get_data(station_id, date)
    station = stations[int(station_id)]
    station_name = station[2]
    station_coords = f"{station[0]} N, {station[1]} E"
    current_row = df.loc[(df.value_type == "Прогноз") | (df.value_type == "forecast")].iloc[0]
    current_values = ["Концентрация загрязнителей на ", html.Nobr(current_row.iat[0].strftime("%H:%M %d.%m.%Y")),
        " (мг/м3):", html.Br()]
    values_list = []
    for pollutant_name in ["CO", "NO2", "NO", "PM25", "PM10"]:
        key = pollutant_name.lower().replace(".", "")
        value = current_row.get(key)
        if value is not None:
            values_list.append(html.Li(f"{pollutant_name} — {value}"))
    current_values.append(html.Ul(children=values_list))
    plot = px.line(df, x="datetime", y=pollutant, color="value_type",
                   labels={"datetime": "Дата и время", pollutant: f"{pollutant.upper()}, мг/м3",
                           "value_type": "Значение"},
                   color_discrete_map={"fact": "#EC0E43", "forecast": "#0000A8",
                                       "Факт": "#EC0E43", "Прогноз": "#0000A8",
                                       "OpenWeatherMap": "#B470AD"})
    info = [html.H3(children=station_name, className="mt-5"),
            html.P(children=station_coords, className="fst-italic"),
            html.P(children=current_values)]
    return plot, info

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

@app.callback(
    Output(component_id="highlighted", component_property="children"),
    Output(component_id="map", component_property="zoom"),
    Output(component_id="map", component_property="center"),
    Input(component_id="station", component_property="value"),
    Input(component_id="map", component_property="click_lat_lng"),
    prevent_initial_call=True
    )
def zoom_move_hightlight(station_id, latlng):
    station = stations[int(station_id)]
    click_lat = station[0]
    click_lon = station[1]
    nearest_station_coords = (click_lat, click_lon)
    highlighted_marker = dl.CircleMarker(center=nearest_station_coords, color="#EC0E43")
    zoom = 13
    return highlighted_marker, zoom, nearest_station_coords    


if __name__ == '__main__':
    app.run_server(debug=True) 
