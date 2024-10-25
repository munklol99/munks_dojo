from pymongo import MongoClient
import pandas as pd
import yaml
import math

# Load the config file
with open('../config.yaml', 'r') as file:
    config = yaml.safe_load(file)

def get_database():
 
   # Provide the mongodb atlas url to connect python to mongodb using pymongo
   CONNECTION_STRING = "mongodb+srv://Admin:ConnorMunk2017@munkdojo.ovfzr.mongodb.net/?retryWrites=true&w=majority&appName=MunkDojo"
 
   # Create a connection using MongoClient. You can import MongoClient or use pymongo.MongoClient
   client = MongoClient(CONNECTION_STRING)
 
   # Create the database for our example (we will use the same database throughout the tutorial
   return client['Dojo']

def create_new_user(disc_username, lol_username, roles, pref_role):
    user = {
        'Discord Username': disc_username,
        'Username': lol_username,
        'Current ELO': config['account_creation']['default_elo'],
        'Roles': roles,
        'Preferred Role': pref_role,
        'Previous ELO': math.nan,
    }
    
    dojo_collection.insert_one(user)
    
    rerank_users()
    
def delete_user(disc_username):
    dojo_collection.delete_many({'Discord Username': disc_username})
    rerank_users()
    
def rerank_users():
    sorted_docs = dojo_collection.find().sort("Current ELO", -1)

    # Update the Rank based on order
    for rank, doc in enumerate(sorted_docs, start=1):
        dojo_collection.update_one({"_id": doc["_id"]}, {"$set": {"Rank": rank}})
        
def update_elo(disc_username, elo_change):
    dojo_collection.update_one({"_id": disc_username}, {"$inc": {"Current Elo": elo_change}})
    
def update_users_elo(disc_usernames, elo_changes):
    for disc_username, elo_change in zip(disc_usernames, elo_changes):
        update_elo(disc_username=disc_username, elo_change=elo_change)
        
    rerank_users()

if __name__ == '__main__':
    dbname = get_database()
    
    dojo_collection = dbname['userData']
    
    items = dojo_collection.find({'Current ELO': {'$gt': 800}})
    # items = dojo_collection.find()
    
    items = pd.DataFrame(items)
    # print(items)
    
    create_new_user('Test', 'LOL_Test', ['Top', 'Mid', 'Jungle', 'ADC', 'Support'], 'Jungle')
    # items = dojo_collection.find({'Discord Username': 'Test'})
    items = dojo_collection.find()
    
    items = pd.DataFrame(items)
    print(items)
    
    delete_user('Test')
    items = dojo_collection.find({'Discord Username': 'Test'})
    
    items = pd.DataFrame(items)
    print(items)
