"""
NOTES:
JSON looks like this:
{
    'key':'value',
    12:'xyz'
}
If it's a string, send in quotes

"""

from flask import Flask, request
from pymongo import MongoClient
import hashlib, json, random
from datetime import datetime as dt, timedelta as td

app = Flask(__name__)
mongo = MongoClient("mongodb://mongo_api:27017")
USERS_DB = mongo['meta']['users']
DATA_DB = mongo['userdata']
def gen_random_str(length=8): return random.getrandbits(length)

@app.route("/cov_api/login", methods=["POST"])
def login_signup():
    """
    {'mode':'signup', //change 'signup' to 'login' if not adding new user
    'username':abcd,
    'password':abcd}
    """
    data = {x[0]:x[1] for x in request.args.items()}
    if 'json' in data.keys(): data = json.load(data['json'])
    if 'mode' not in data.keys(): return 'mode missing, choose signup or login'
    if 'username' not in data.keys(): return 'username missing'
    if 'password' not in data.keys(): return 'password missing'
    random_appended = data['password'] + '1xky'
    data['password'] = hashlib.md5(random_appended.encode('utf-8')).hexdigest()
    auth_user = USERS_DB.find_one({'username':data['username']})
    if data['mode'] == 'signup':
        del data['mode']
        if auth_user: USERS_DB.insert_one(data)
        return 'username already exists, login instead'
    else:
        if not auth_user: return 'user doesnt exist'
        elif auth_user['password'] != data['password']: return 'wrong password or username'
    access_token = str(gen_random_str(64))
    USERS_DB.update_one({'username':data['username']}, {"$set":{'access_token': access_token, 'login_valid_till': dt.now()+td(days=1)}})
    return str(access_token)

@app.route('/cov_api/data', methods=["GET", "POST"])
def add_data_to_user():
    request_data = {x[0]:x[1] for x in request.args.items()}
    user = USERS_DB.find_one({"access_token": request_data['access_token']})
    if not user: return 'invalid access_token/user doesnt exist'
    elif user['login_valid_till'] < dt.now(): return 'access_token expired, re-login'
    user_data_collection = DATA_DB[user['username']]
    if request.method == "POST":
        if 'json' not in request_data.keys(): return 'only json format supported'
        jsonified = json.loads(request_data['json'])
        if len(jsonified.keys()) == 1: user_data_collection.insert_one(jsonified)
        else: user_data_collection.insert_many(jsonified)
        return 'success'
    elif request.method == 'GET':
        user_data = [x for x in user_data_collection.find({})]
        for x  in user_data: del x['_id']
        return json.dumps(user_data)


app.run(host="0.0.0.0", port=80)