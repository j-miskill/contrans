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
        self.us_state_to_abbrev = {
                        "Alabama": "AL","Alaska": "AK","Arizona": "AZ","Arkansas": "AR",
                        "California": "CA","Colorado": "CO","Connecticut": "CT","Delaware": "DE",
                        "Florida": "FL","Georgia": "GA","Hawaii": "HI",
                        "Idaho": "ID","Illinois": "IL","Indiana": "IN","Iowa": "IA",
                        "Kansas": "KS","Kentucky": "KY","Louisiana": "LA",
                        "Maine": "ME","Maryland": "MD","Massachusetts": "MA",
                        "Michigan": "MI","Minnesota": "MN","Mississippi": "MS",
                        "Missouri": "MO","Montana": "MT","Nebraska": "NE",
                        "Nevada": "NV","New Hampshire": "NH","New Jersey": "NJ",
                        "New Mexico": "NM","New York": "NY","North Carolina": "NC",
                        "North Dakota": "ND","Ohio": "OH","Oklahoma": "OK",
                        "Oregon": "OR","Pennsylvania": "PA","Rhode Island": "RI",
                        "South Carolina": "SC","South Dakota": "SD","Tennessee": "TN",
                        "Texas": "TX","Utah": "UT","Vermont": "VT",
                        "Virginia": "VA","Washington": "WA","West Virginia": "WV",
                        "Wisconsin": "WI","Wyoming": "WY","District of Columbia": "DC",
                        "American Samoa": "AS","Guam": "GU","Northern Mariana Islands": "MP",
                        "Puerto Rico": "PR","United States Minor Outlying Islands": "UM",
                        "Virgin Islands": "VI"
                        }

    
    def get_votes(self):
        url = "https://voteview.com/static/data/out/votes/H118_votes.csv"
        
        votes = pd.read_csv(url)
        return votes

    def get_ideology(self):
        # url = "https://voteview.com/static/data/out/votes/H118_members.csv"
        url = "https://voteview.com/static/data/out/members/H118_members.csv"
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
    

    def make_cand_table(self):
                members = self.get_bioguideIDs()
                replace_map = {'Republican': 'R','Democratic': 'D','Independent': 'I'}
                members['partyletter'] = members['partyName'].replace(replace_map)
                members['state'] = members['state'].replace(self.us_state_to_abbrev)
                members['district'] = members['district'].fillna(0)
                members['district'] = members['district'].astype('int').astype('str')
                members['district'] = ['0' + x if len(x) == 1 else x for x in members['district']]
                members['district'] = [x.replace('00', 'S') for x in members['district']]
                members['DistIDRunFor'] = members['state']+members['district']
                members['lastname']= [x.split(',')[0] for x in members['name']]
                members['firstname']= [x.split(',')[1] for x in members['name']]
                members['name2'] = [ y.strip() + ' (' + z.strip() + ')' 
                                for y, z in 
                                zip(members['lastname'], members['partyletter'])]
                
                cands = pd.read_csv('data/cands22.txt', quotechar="|", header=None)
                cands.columns = ['Cycle', 'FECCandID', 'CID','FirstLastP',
                                'Party','DistIDRunFor','DistIDCurr',
                                'CurrCand','CycleCand','CRPICO','RecipCode','NoPacs']
                cands['DistIDRunFor'] = [x.replace('S0', 'S') for x in cands['DistIDRunFor']]
                cands['DistIDRunFor'] = [x.replace('S1', 'S') for x in cands['DistIDRunFor']]
                cands['DistIDRunFor'] = [x.replace('S2', 'S') for x in cands['DistIDRunFor']]
                cands['name2'] = [' '.join(x.split(' ')[-2:]) for x in cands['FirstLastP']]
                cands = cands[['CID', 'name2', 'DistIDRunFor']].drop_duplicates(subset=['name2', 'DistIDRunFor'])
                crosswalk = pd.merge(members, cands, 
                     left_on=['name2', 'DistIDRunFor'],
                     right_on=['name2', 'DistIDRunFor'],
                     how = 'inner')
                return crosswalk
    

    def terms_df(self, members):
        termsDF = pd.DataFrame()
        for index, row in members.iterrows():
            bioguideId = row['bioguideId']
            terms = row['terms.item']
            df = pd.DataFrame.from_records(terms)
            df['bioguideId'] = bioguideId
            termsDF = pd.concat([termsDF, df])
        members = members.drop("terms.item", axis=1)
        return termsDF, members







