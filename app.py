import dash
from dash import dcc
from dash import html
import dash_leaflet as dl

app = dash.Dash(__name__)

app.layout = html.Div(children=[
    html.H1(children='Прогноз загрязнения воздуха в Москве'),

    html.Div(children=["Выберите станцию",
                       dcc.Dropdown(id="station",
                                    options=[
                                        {"label": "Туристская", "value": 1},
                                        {"label": "Коптевский бул", "value": 2},
                                        {"label": "Останкино 0", "value": 3},
                                        {"label": "Глебовска", "value": 4},
                                        {"label": "Спиридоновка", "value": 5},
                                        {"label": "Шаболовка", "value": 6},
                                        {"label": "Академика Анохина", "value": 7},
                                        {"label": "Бутлерова", "value": 8},
                                        {"label": "Пролетарский проспект", "value": 9},
                                        {"label": "Марьино", "value": 10}
                                        ],
                                    value=1)]),

    dl.Map(dl.TileLayer(),
           center=(55.752004, 37.617734),
           zoom=10,
           style={'width': '100%', 'height': '500px'})
])

if __name__ == '__main__':
    app.run_server(debug=True) 
