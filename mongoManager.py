import pymongo as mongo
from dotenv import load_dotenv, find_dotenv
import os
from datetime import datetime
from Train import Train
load_dotenv(find_dotenv())
CONNECTION_URL = os.environ.get("CONNECTION_URL")



class DBMngr :
    def __init__(self):
        self.client = mongo.MongoClient(CONNECTION_URL)
        self.db = self.client['Metro']

        self.trains = self.db['Trains']
    
    def add_train(self, train : Train ):
        res = self.trains.insert_one(train.toDict())
        return res 

    def get_all_trains(self):
        res = list(self.trains.find({}).sort({'train_code':1}))
        if res:
            for r in res:
                r['_id'] = str(r['_id'])
            return res
        else:
            return None 
    
    def unassign_all_trains(self):
        return self.trains.update_many({}, {'$set': {'status':'UNASSIGNED'} }  )
    def update_status(self, train_id, status):
        return self.trains.update_one(
    {'train_id': train_id},
    {'$set': {'status': status}}
)
    
if __name__=='__main__':
    dbMngr = DBMngr()
    
    # dbMngr.add_train(train)
    dbMngr.trains.delete_many({})

    
    