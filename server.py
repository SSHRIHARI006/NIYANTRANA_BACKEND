from flask import Flask , request, session, redirect, url_for
from dotenv import load_dotenv, find_dotenv
from datetime import timedelta, datetime

from mongoManager import DBMngr
from flask_cors  import cross_origin, CORS
from Train import Train
from classify_trains import run_optimization
import os

app = Flask(
    __name__
)

dbmngr = DBMngr()

@app.get("/api/get_trains")
@cross_origin()
def get_trains():
    trains = dbmngr.get_all_trains()
    return trains

@app.route("/api/addtrain", methods=["POST"])
@cross_origin()
def add_train():
    train = request.json
    train = Train(**train)
    res =  dbmngr.add_train(train)
    if res:
        return "ok"
    else :
        return "error"
    
@app.get("/api/get_current_model_assignment")
@cross_origin()
def get_current_model_assignment():
    print("Sa")
    trains = dbmngr.get_all_trains()
    for train in trains:
        train.pop('_id')
        if train.get('branding_expiry_date'):
            train['branding_expiry_date'] = datetime.strptime(train['branding_expiry_date'], "%Y-%m-%d").date()
    trains = [ Train(**train) for train in trains]
    run_optimization(trains)
    trains = [ train.toDict() for train in trains]
    
    return trains

@app.route("/api/update_status", methods=['POST'])
@cross_origin()
def update_status():
    train_code, status = request.json['train_id'], request.json['status']
    res = dbmngr.update_status(train_code, status)
    if res:
        return "ok"
    else:
        return "err"
@app.route("/api/resetstatus")
@cross_origin()
def reset_status():
    res =  dbmngr.unassign_all_trains()
    if res:
        return "ok"
    else:
        return "err"



if __name__ == '__main__':

    app.run(
        port=4001,
        debug=True
    )
