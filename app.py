import dash
from dash import html                        # basic HTML syntax (header, bolds, etc)
from dash import dcc                         # part of dash that has interactive elements
from dash.dependencies import Input, Output  # handling user input and outputing things onto dashboard
import plotly.figure_factory as ff
from contrans import contrans
import pandas as pd
import numpy as np
import os


# create the dash app
external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
app = dash.Dash(__name__, external_stylesheets=external_stylesheets)


# set up contrans and postgres connections
ct = contrans()
server, engine = ct.connect_to_postgres(os.getenv("POSTGRES_PASSWORD"), host="postgres") # networking docker containers


# create fixed variables for use in the dashboard
myquery = """
SELECT *
FROM members
ORDER BY lastname
"""
members = pd.read_sql_query(myquery, con=engine)
bioguides = members['bioguideid']
displayname = members['firstname'] + " " + members['lastname'] + " (" + members['partyletter'] + ", " + members['state'] + "-" + members['district'] + ")"

dropdown_options = [{"label": y, "value": x} for x,y in zip(bioguides, displayname)]


# populate the layout with callbacks included

app.layout = html.Div([

html.H1("Know Your Representatives in Elected-office", style={'text-align': 'center'}),
html.Div([
    dcc.Markdown("To find your Representative and Senators, go [here](https://www.congress.gov/members/find-your-member)"),
    dcc.Markdown("Select your representatives or Senator here"),
    dcc.Dropdown(id='dropdown', options=dropdown_options, value='N000188')
    ], style= {"width":"25%", "float": "left"}),
html.Div([
    dcc.Tabs([
        
        dcc.Tab(label="Bio and Contact Info", children=[
            
            # picture
            html.Div([html.Img(id="bioimage", style={"width": "100%", "height":"100%"})
                ], style=({"width": '30%', 'float':'left'})),

            # table
            html.Div([
                dcc.Graph(id='biotable')
                ], style=({"width": '68%', 'float':'right'})), 
                dcc.Markdown("This person votes very similarly to the follow people:"),
                dcc.Graph(id="agreetable"),
                dcc.Markdown("This person rarely votes the same way as the following people:"),
                dcc.Graph(id="disagreetable")
            ]),

        dcc.Tab(label="Bills and Votes", children=[]),

        dcc.Tab(label="Ideology and Votes", children=[
            dcc.Graph(id="ideograph")
        ]),

        dcc.Tab(label="News", children=[]),

        dcc.Tab(label="Financial Contributors", children=[])
        
])
], style= {"width":"72%", "float": "right"})
])


"""
    callback methods
"""

@app.callback([Output(component_id='biotable', component_property='figure')],
              [Input(component_id='dropdown', component_property='value')])
def biotable(b):
    myquery = f'''
    SELECT 
        name AS Name, 
        partyname AS Party, 
        state AS State, 
        district AS District,        
        CAST((2024 - born) AS INT) AS Age 
    FROM members    
    WHERE bioguideid='{b}'
    '''
    mydf = pd.read_sql_query(myquery, con=engine)
    mydf.columns = [x.capitalize() for x in mydf.columns]
    mydf = mydf.T.reset_index()
    mydf = mydf.rename({'index':'', 0:''}, axis=1)
    return [ff.create_table(mydf)]

@app.callback([Output(component_id='bioimage', component_property='src')],
              [Input(component_id='dropdown', component_property='value')])
def bioimage(b):
    myquery = f"""
    SELECT depiction_imageurl
    FROM members
    WHERE bioguideid='{b}'
    """
    mydf = pd.read_sql_query(myquery, con=engine)
    return [mydf['depiction_imageurl'][0]]

@app.callback([Output(component_id="ideograph", component_property="figure")],
              [Input(component_id="dropdown", component_property="value")])
def ideograph(b):
    g = ct.plot_ideology(b, host="postgres")
    return [g]

@app.callback([Output(component_id="agreetable", component_property="figure")],
              [Input(component_id="dropdown", component_property="value")])
def agreetable(b):
    agreedf = ct.make_agreement_df(b, engine=engine)
    return [agreedf]

@app.callback([Output(component_id="disagreetable", component_property="figure")],
              [Input(component_id="dropdown", component_property="value")])
def disagreetable(b):
    disagreedf = ct.make_agreement_df(b, engine=engine)
    return [disagreedf]


# run the dash app
if __name__ == "__main__":
    app.run_server(debug=True, host="0.0.0.0", port=8050)