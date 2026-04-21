import dash
from dash import dcc, html
import requests
import json

# Initialize the Dash app
app = dash.Dash(__name__)

# cAdvisor API URL
CADVISOR_URL = "http://cadvisor:8080/api/v1.3/docker"

# Function to get container info from cAdvisor
def get_container_info():
    try:
        response = requests.get(CADVISOR_URL)
        response.raise_for_status()
        containers = response.json()
        return containers
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from cAdvisor: {e}")
        return {}

# App layout
app.layout = html.Div([
    html.H1("Container Monitoring with cAdvisor"),
    html.Div(id='container-info')
])

# Callback to update container info
@app.callback(
    dash.dependencies.Output('container-info', 'children'),
    [dash.dependencies.Input('container-info', 'id')]
)
def update_container_info(_):
    containers = get_container_info()
    if not containers:
        return html.P("No container data available.")

    container_elements = []
    for name, data in containers.items():
        container_elements.append(html.H3(f"Container: {data.get('aliases', [name])[0]}"))
        container_elements.append(html.Pre(json.dumps(data.get('spec'), indent=2)))
        container_elements.append(html.Hr())

    return container_elements

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8050)
