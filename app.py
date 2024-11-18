import dash
from dash import html                        # basic HTML syntax (header, bolds, etc)
from dash import dcc                         # part of dash that has interactive elements
from dash.dependencies import Input, Output  # handling user input and outputing things onto dashboard
from contrans import contrans

ct = contrans()

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

# create the dash app
app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

# populate the layout
# Div is a list of elements from top to bottom
# Know Your Representatives in Elected-office (KYRIE)
# congressional officers now try ramen and noodle soups (CONTRANS)
app.layout = html.Div([

html.H1("Know Your Representatives in Elected-office", style={'text-align': 'center'}),
html.Div([
    dcc.Markdown("To find your Representative and Senators, go [here](https://www.congress.gov/members/find-your-member)"),
    ], style= {"width":"25%", "float": "left"}),
html.Div([
    dcc.Tabs([
        dcc.Tab(label="Bio and Contact Info", children=[]),
        dcc.Tab(label="Bills and Votes", children=[]),
        dcc.Tab(label="Ideology and Votes", children=[]),
        dcc.Tab(label="News", children=[]),
        dcc.Tab(label="Financial Contributors", children=[])
        
])
], style= {"width":"72%", "float": "right"})


])



# run the dash app
if __name__ == "__main__":
    app.run_server(debug=True, host="0.0.0.0", port=8050)