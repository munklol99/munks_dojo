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
    user = dojo_collection.find_one({"Discord Username": disc_username})
    if user:
        return f"Username {disc_username} aready exists"
    
    user = {
        'Discord Username': disc_username,
        'Username': lol_username,
        'Current ELO': config['account_creation']['default_elo'],
        'Roles': roles,
        'Preferred Role': pref_role,
        'Previous ELO': math.nan,
    }
    
    user_history = {
        'Discord Username': disc_username,
        'Username': lol_username,
        'Elo History': [config['account_creation']['default_elo']]
    }
    
    dojo_collection.insert_one(user)
    history_collection.insert_one(user_history)
    
    rerank_users()
    
    return "User created successfully"
    
def delete_user(disc_username):
    user = dojo_collection.find_one({"Discord Username": disc_username})
    if not user:
        return f"Username {disc_username} does not exists"
    
    dojo_collection.delete_many({'Discord Username': disc_username})
    history_collection.delete_many({'Discord Username': disc_username})
    rerank_users()
    
    return "User deleted successfully"
    
def rerank_users():
    sorted_docs = dojo_collection.find().sort("Current ELO", -1)

    # Update the Rank based on order
    for rank, doc in enumerate(sorted_docs, start=1):
        dojo_collection.update_one({"_id": doc["_id"]}, {"$set": {"Rank": rank}})
        
def update_elo(disc_username, elo_change):
    user = dojo_collection.find_one({"Discord Username": disc_username})
    if not user:
        return f"Username {disc_username} does not exists"
    
    dojo_collection.update_one({"_id": user['_id']}, {"$inc": {"Current ELO": elo_change}})
    add_to_elo_history(disc_username=disc_username, new_elo=user['Current ELO'] + elo_change)
    
    rerank_users() # Take this out later
    
    return "User elo updated successfully"

def update_users_elo(disc_usernames, elo_changes):
    for disc_username, elo_change in zip(disc_usernames, elo_changes):
        update_elo(disc_username=disc_username, elo_change=elo_change)
        
    rerank_users()
    
def add_to_elo_history(disc_username, new_elo):
    history_collection.update_one(
        {"Discord Username": disc_username},
        {"$push": {"Elo History": new_elo}}
    )

if __name__ == '__main__':
    dbname = get_database()
    
    dojo_collection = dbname['userData']
    history_collection = dbname['user_elo_history']
    
    items = dojo_collection.find({'Current ELO': {'$gt': 800}})
    # items = dojo_collection.find()
    
    items = pd.DataFrame(items)
    # print(items)
    
    print(create_new_user('Test', 'LOL_Test', ['Top', 'Mid', 'Jungle', 'ADC', 'Support'], 'Jungle'))
    
    update_elo(disc_username='Test', elo_change=10)
    # items = dojo_collection.find({'Discord Username': 'Test'})
    items = dojo_collection.find()
    
    items = pd.DataFrame(items)
    print(items)
    
    print(delete_user('Test'))
    items = dojo_collection.find({'Discord Username': 'Test'})
    
    items = pd.DataFrame(items)
    print(items)
