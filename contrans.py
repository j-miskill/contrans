import numpy as np
import pandas as pd
import os
import requests
import json
from bs4 import BeautifulSoup


class contrans:

    def __init__(self):
        self.mypassword = os.getenv('mypassword')
        self.news_api_key = os.getenv("NEWS_API_KEY")
        self.congress_api_key = os.getenv("CONGRESS_API_KEY")

    
    def get_votes(self):
        url = "https://voteview.com/static/data/out/votes/H118_votes.csv"
        votes = pd.read_csv(url)
        return votes

    def get_ideology(self):
        url = "https://voteview.com/static/data/out/votes/H118_members.csv"
        members = pd.read_csv(url)
        return members

    
    def get_useragent(self):
        url = "https://httpbin.org/user-agent"
        r = requests.get(url)
        useragent = json.loads(r.text)['user-agent']
        return useragent

    def make_headers(self, email='jcm4bsq@virginia.edu'):
        useragent = self.get_useragent()
        headers = {
            'User-Agent': useragent,
            'From': email
        }
        return headers
    
    def get_bioguideIDs(self, congress=118):
        params = {'api_key': self.congress_api_key,
                  'limit': 1,
                  'offset':0}
        headers = self.make_headers()
        root = "https://api.congress.gov/v3"
        endpoint = f"/member/congress/{congress}"
        r = requests.get(root + endpoint,
                         params=params, 
                         headers=headers)
        
        bioguides = json.loads(r.text)

        total_records = bioguides['pagination']['count']

        j = 0
        bio_df = pd.DataFrame()
        while j < total_records:
            params['offset'] = j
            params['limit'] = 250
            r = requests.get(root + endpoint,
                         params=params, 
                         headers=headers)
            records = pd.json_normalize(r.json()['members'])
            bio_df = pd.concat([bio_df, records], ignore_index=True)
            j += 250

        # bio_df = pd.json_normalize(records)
        # bio_df = bio_df['name', 'state', 'district', 'partyName', 'bioguideId']
        return bio_df

    def get_bioguide(self, name, state=None, district=None):
        members = self.get_bioguideIDs() # pd dataframe, will replace with SQL query once we have a table to store things

        members['name'] = members['name'].str.lower().str.strip() # lower for all
        name = name.lower().strip()

        to_keep = [name in x for x in members['name']]
        members = members[to_keep]


        if state is not None:
            # state = state.lower().strip()
            members = members.query("state == @state")
            
        if district is not None:
            members = members.query("district == @district")
            
        
        return members.reset_index(drop=True)
    
    def get_sponsored_legislation(self, bioguideid):
        params = {'api_key': self.congress_api_key,
                  'limit': 250}
        headers = self.make_headers()
        root = "https://api.congress.gov/v3/"
        endpoint = f"member/{bioguideid}/sponsored-legislation"

        temp_r = requests.get(root + endpoint,
                         params=params, 
                         headers=headers)
        tmp = json.loads(temp_r.text)
        total_records = tmp['pagination']['count']
        
        j=0
        bills_final = []

        while j < total_records:
            params['offset'] = j
        
            r = requests.get(root + endpoint,
                        params=params, 
                        headers=headers)
            records = r.json()['sponsoredLegislation']
            for record in records:
                bills_final.append(record)
            j += 250
        
        return bills_final
    
    def get_bill_data(self, bill_url):
        r = requests.get(bill_url, params = {"api_key": self.congress_api_key})
        txt_url = json.loads(r.text)['bill']['textVersions']['url']
        r2 = requests.get(txt_url, params={"api_key": self.congress_api_key})
        url_to_scrape = json.loads(r2.text)['textVersions'][0]['formats'][0]['url']

        html_doc = requests.get(url_to_scrape)
        gumbo = BeautifulSoup(html_doc.text, 'html.parser') 
        return gumbo
    

    def get_congressperson_news(self, member):
        params = {"apiKey": self.news_api_key,
                  "q": member,
                  "sortBy": "relevancy",
                  "source": "us"}
        base = "https://newsapi.org/v2/"
        endpoint = "everything"
        headers = self.make_headers()
        r = requests.get(params=params, url=base+endpoint, headers=headers)
        return json.loads(r.text)





