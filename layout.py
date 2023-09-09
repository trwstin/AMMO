import dash
from dash import html, dcc

# app settings
app = dash.Dash(__name__, update_title=None)
app.title = "TikTok AMMO"
server = app.server

# app layout
app.layout = html.Div(
    [
        html.Div(
            [html.H4("Advertisement-Moderator Matching Optimizer", 
                     className="header_text")],
            className="app_header"),

        html.Div(
            html.H2('Upload .xlsx file to Begin',
                id='greeting',
                title='Upload .xlsx file to Begin',
                style={'padding-top':'50px'}),
        
            style={"display": "flex", "justifyContent": "center"}),

        html.Div(
            html.H4('After uploading, please wait 1-2 minutes for file to download'),
            style={"display": "flex", "justifyContent": "center"}),

        html.Div(
            dcc.Upload(
                id="upload-data",
                className="upload",
                children=html.Div(
                    children=[
                        html.P("Drag and Drop or "),
                        html.A("Select Files"),
                    ]
                ),
                accept=".xlsx",
            ),
            style={'width':'40%', 'padding-top':'50px', 'margin':'0 auto', 
                   'text-align':'center'}
        ),

        html.Div([
            html.H4(["File has been downloaded on your system!", html.Br(),
                    "Check your default download folder."], id="success-msg"
                    , style={'display':'none', 'align':'center'}),
            dcc.Download(id="download")],
            style={"padding-top":"50px", "display": "flex", 
                   "justifyContent": "center", "color":"red"}),
    ]
)