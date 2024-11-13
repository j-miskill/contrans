import numpy as np
import pandas as pd
import os
import requests
import json
import psycopg  # postgres adapter
from sqlalchemy import create_engine  # shortcut tool to connect database to pandas
from bs4 import BeautifulSoup
import pymongo
from bson.json_util import dumps, loads


class contrans:

    def __init__(self):
        self.mypassword = os.getenv('mypassword')
        self.news_api_key = os.getenv("NEWS_API_KEY")
        self.congress_api_key = os.getenv("CONGRESS_API_KEY")
        self.postgres_password = os.getenv("POSTGRES_PASSWORD")
        self.MONGO_INITDB_ROOT_USERNAME = os.getenv("MONGO_INITDB_ROOT_USERNAME")
        self.MONGO_INITDB_ROOT_PASSWORD = os.getenv("MONGO_INITDB_ROOT_PASSWORD")
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
        return bio_df.reset_index(drop=True)

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
    
    def get_sponsored_legislation(self, bioguideid, congress=118):
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
        
        bills_final = [x for x in bills_final if x['congress']==congress]
        bills_final = [x for x in bills_final if "/bill" in x['url']]
        return bills_final
    
    def get_bill_data(self, bill_url):
        r = requests.get(bill_url, params = {"api_key": self.congress_api_key})
        bills_json = json.loads(r.text)
        txt_url = bills_json['bill']['textVersions']['url']
        r2 = requests.get(txt_url, params={"api_key": self.congress_api_key})
        url_to_scrape = json.loads(r2.text)['textVersions'][0]['formats'][0]['url']

        html_doc = requests.get(url_to_scrape)
        gumbo = BeautifulSoup(html_doc.text, 'html.parser') 
        bill_text = gumbo.text
        bills_json['bill_text'] = bill_text
        return bills_json
        
    

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
                     how = 'left')
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
    
    ### Methods for building the third normal form relational database tables

    def make_members_df(self, members, ideology, engine):
        """
            members should be the output of get_bioguideIDs but w/ terms removed by get_terms
            augmented with contributions by make_cand_table()

            Ideology should be the output of get_ideology()
        """
        
        members_df = pd.merge(members, ideology,
                              left_on='bioguideId',
                              right_on='bioguide_id',
                              how='left')
        members_df.columns = members_df.columns.str.lower()
        members_df.columns = members_df.columns.str.replace(".", "_")
        members_df.to_sql("members", con=engine, index=False, chunksize=1000, if_exists="replace")
        return members_df
    

    def connect_to_postgres(self, password, user='postgres', host='localhost', port='5432', create_contrans=False):
        dbserver = psycopg.connect(user=user, password=password, host=host, port=port)
        dbserver.autocommit = True
        if create_contrans:
            # cursor is the location for writing code to run on the server
            cursor = dbserver.cursor()
            cursor.execute("DROP DATABASE IF EXISTS contrans")
            cursor.execute("CREATE DATABASE contrans")
        
        engine = create_engine(f"postgresql+psycopg://{user}:{password}@{host}:{port}/contrans")
        return dbserver, engine


    def make_terms_df(self,terms, engine):
        terms.columns = terms.columns.str.lower()
        terms.to_sql("terms", con=engine, index=False, chunksize=1000, if_exists="replace")
        

    def make_votes_df(self, votes, engine):
        votes.columns = votes.columns.str.lower()
        votes.to_sql("votes", con=engine, index=False, chunksize=1000, if_exists="replace")
        

    def make_agreements_df(self, agreements, engine):
        agreements.columns = agreements.columns.str.lower()
        agreements.to_sql("agreements", con=engine, index=False, chunksize=1000, if_exists="replace")

    def dbml_helper(self, data):
        dt = data.dtypes.reset_index().rename({0:'dtype'}, axis=1)
        replace_map = {'object': 'varchar',
                    'int64': 'int',
                    'float64': 'float'}
        dt['dtype'] = dt['dtype'].replace(replace_map)
        return dt.to_string(index=False, header=False)
    
    def make_agreement_df(self, bioguide_id, engine):
        myquery = f'''
        SELECT icpsr
            FROM members m
        WHERE bioguideid = {bioguide_id}
        '''
        icpsr = int(pd.read_sql_query(myquery, con=engine)['icpsr'][0])
        myquery = f'''
        SELECT m.name, m.partyname, m.state, m.district, v.agree
        FROM members m
        INNER JOIN (
        SELECT
                a.icpsr AS icpsr1,
                b.icpsr AS icpsr2,
                AVG(CAST((a.cast_code = b.cast_code) AS INT)) AS agree
                FROM votes a
        INNER JOIN votes b
                ON a.rollnumber = b.rollnumber
                AND a.chamber = b.chamber
        WHERE a.icpsr={icpsr} AND b.icpsr!={icpsr}
        GROUP BY icpsr1, icpsr2
        ORDER BY agree DESC
        ) v
        ON CAST(m.icpsr AS INT) = v.icpsr2
        WHERE m.icpsr IS NOT NULL
        ORDER BY v.agree DESC
        '''
        df = pd.read_sql_query(myquery, con=engine)
        return df.head(10), df.tail(10)
    
    def connect_to_mongo(self, from_scratch=False):
        myclient = pymongo.MongoClient(f"mongodb://{self.MONGO_INITDB_ROOT_USERNAME}:{self.MONGO_INITDB_ROOT_PASSWORD}@localhost:27017/")
        mongo_contrans = myclient['contrans']
        collist = mongo_contrans.list_collection_names()
        if from_scratch and "bills" in collist:
            mongo_contrans.bills.drop()
        return mongo_contrans['bills']
    
    
    def upload_one_member_to_mongo(self, mongo_bills: pymongo.MongoClient, bioguideid: str):
        # just one member's bills to be uploaded
        bill_list = self.get_sponsored_legislation(bioguideid)
        bill_list_with_text = [self.get_bill_data(x['url']) for x in bill_list]
        mongo_bills.insert_many(bill_list_with_text)

    def upload_many_members_to_mongo(self, mongo_bills: pymongo.MongoClient, members: list):
        i = 1
        for m in members:
            try:
                print('uploading bills from {m} to MongoDB: legislator {i} of {len(members)}')
                self.upload_one_member_to_mongo(mongo_bills=mongo_bills, bioguideid=m)
            except Exception as e:
                print(f"Process failed for: {m} on the {i} index.")
                print(e)
                continue
            i += 1

    def query_mongo(self, collection, rows, columns):
        cursor = collection.find(rows, columns)
        result_dumps = dumps(cursor)
        result_loads = loads(result_dumps)
        result_df = pd.DataFrame.from_records(result_loads)
        return result_df
    
    def query_mongo_search_engine(self, collection, key_to_search, search_terms):
        collection.create_index([(key_to_search, 'text')])


        cursor = collection.find({"$text": 
                                    {"$search": search_terms, 
                                    "$caseSensitive": False}
                                    }, 
                                    {})
        result_dumps = dumps(cursor)
        result_loads = loads(result_dumps)
        result_df = pd.DataFrame.from_records(result_loads)
        return result_df

