from pymongo import MongoClient
import pandas as pd
import yaml
import math

# Load the config file
with open('./config.yaml', 'r') as file:
    config = yaml.safe_load(file)

def get_database():
 
   # Provide the mongodb atlas url to connect python to mongodb using pymongo
   CONNECTION_STRING = "mongodb+srv://Admin:ConnorMunk2017@munkdojo.ovfzr.mongodb.net/?retryWrites=true&w=majority&appName=MunkDojo"
 
   # Create a connection using MongoClient. You can import MongoClient or use pymongo.MongoClient
   client = MongoClient(CONNECTION_STRING)
   print('Successfully connected to DB')
   # Create the database for our example (we will use the same database throughout the tutorial
   return client['Dojo']

dbname = get_database()
    
dojo_collection = dbname['users']
history_collection = dbname['user_history']

def create_new_user(disc_username, lol_username, discord_id):
    print('Creating new user...', disc_username, lol_username)
    user = dojo_collection.find_one({"Discord Username": disc_username})
    print('User found:', user)
    if user:
        return f"Username {disc_username} aready exists"
    
    user = {
        'Discord Username': disc_username,
        'Discord ID': discord_id,
        'Username': lol_username,
        'Current ELO': config['account_creation']['default_elo'],
        'Previous ELO': math.nan,
    }
    
    user_history = {
        'Discord Username': disc_username,
        'Discord ID': discord_id,
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
        
def update_elo(discord_id, elo_change):
    user = dojo_collection.find_one({"Discord ID": discord_id})
    if not user:
        return f"Discord ID {discord_id} does not exists"
    
    # Safeguard to ensure ELO doesn't drop below 0
    current_elo = user.get("Current ELO", 0)
    if current_elo + elo_change < 0:
        elo_change = -current_elo  # Adjust elo_change to set ELO to 0
    
    dojo_collection.update_one({"_id": user['_id']}, {"$inc": {"Current ELO": elo_change}})
    add_to_elo_history(discord_id=discord_id, new_elo=user['Current ELO'] + elo_change)
    
    # rerank_users() # Take this out later
    
    return "User elo updated successfully"

def get_leaderboard():
    sorted_docs = dojo_collection.find().sort("Current ELO", -1)
    return sorted_docs

def update_users_elo(discord_ids, elo_changes):
    for discord_id, elo_change in zip(discord_ids, elo_changes):
        print(update_elo(discord_id=discord_id, elo_change=elo_change))
        
    rerank_users()
    
def add_to_elo_history(discord_id, new_elo):
    history_collection.update_one(
        {"Discord ID": discord_id},
        {"$push": {"Elo History": new_elo}}
    )
    
def get_user_data(disc_usernames):
    items = dojo_collection.find({'Discord Username': {'$in': disc_usernames}})
    df = pd.DataFrame(items)
    return df

def get_user_data_by_name(disc_username):
    user = dojo_collection.find_one({"Discord Username": disc_username})
    return user

def check_if_user_exists(disc_username):
    user = dojo_collection.find_one({"Discord Username": disc_username})
    return user is not None

if __name__ == '__main__':
    dbname = get_database()
    
    dojo_collection = dbname['users']
    history_collection = dbname['user_history']
    
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
