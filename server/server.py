import fitbit
from flask import Flask, jsonify, render_template, request, Response
import logging
import os
import requests

# App
from configure import app

# add the mlpred folder
import sys
sys.path.insert(0, '../mlPredictor')
import predictionEngine
model = predictionEngine.train_model()

# Log
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
log_formatter = logging.Formatter('%(asctime)s:%(name)s:%(message)s')
file_handler = logging.FileHandler('logs/server.log')
file_handler.setFormatter(log_formatter)
logger.addHandler(file_handler)

# Modules
from modules import fitbit_module
from modules import betterdoctor

# MongoDB
from pymongo import MongoClient
client = MongoClient()
db = client.heartcare

# User Data
user_data = {
    'Amy': {
        'age': 38.0,
        'hypertension': 1.0,
        'heart_disease': 1.0,
        'bmi': 38.0,
        'gender_numeric': 1.0,
        'ever_married_numeric': 1.0,
        'work_type_numeric': 1.0,
        'residence_type_numeric': 1.0,
        'smoking_status_numeric': 1.0
    },
    'Bob': {
        'age': 78.0,
        'hypertension': 0.0,
        'heart_disease': 1.0,
        'bmi': 41.0,
        'gender_numeric': 1.0,
        'ever_married_numeric': 1.0,
        'work_type_numeric': 1.0,
        'residence_type_numeric': 1.0,
        'smoking_status_numeric': 1.0
    },
    'Charlie': {
        'age': 67.0,
        'hypertension': 0.0,
        'heart_disease': 1.0,
        'bmi': 38.0,
        'gender_numeric': 1.0,
        'ever_married_numeric': 1.0,
        'work_type_numeric': 1.0,
        'residence_type_numeric': 1.0,
        'smoking_status_numeric': 1.0
    }
}


@app.route('/')
def register():
    return render_template('register.html')


@app.route('/api/signup', methods=['POST'])
def signup():

	args = request.args
	print (args)

	username = args['username']
	print(username)
	pw = args['password']
	insurance = args['insurance']
	age = args['age']
	db.user.insert({'username': username,'password': pw,'insurance': insurance,'age': age})
	
	return Response(status=200)


@app.route('/api/user', methods=['POST'])
def get_judges():
    user = user_data.get('Amy')
    if not user:
        logger.error('get_user({}): username not existed'.format(username))
        return None
    if os.environ.get('env') == 'demo':
        # TODO: Get data from real cases
        pass
    else:
        start = '13:00'
        end = '13:01'
        try:
            heart_rates = fitbit_module.get_heartrate(start=start, end=end)
            avg_hr = calculate_hr(heart_rates['activities-heart-intraday'])
        except Exception as e:
            avg_hr = 80.0
    req = user
    req['heart_rate'] = avg_hr
    #clear it for every request
    if 'stroke_probability' in req:
    	del req['stroke_probability']
    stroke_probability = predictionEngine.predict(
        model, req)
    req['stroke_probability'] = stroke_probability
    hospital = getVisitType(req)
    if hospital == 'Heart Healthy':
        hospital = 'relax and no medical help needed'
    message = 'OK, here they are.\n Based on your heart rate in past month, the stroke probability is {}.\n We recommend to go {}. \n Where would you like to go?'.format(
        round(stroke_probability, 2),
        hospital
    )
    res = {
        "user_id": "2",
        "bot_id": "1",
        "module_id": "3",
        "message": message,
        "stroke_probability": stroke_probability
    }
    return jsonify(res)


@app.route('/api/user/<username>', methods=['POST'])
def get_percentage(username):
    user = user_data.get(username)  # 'Amy'
    if not user:
        logger.error('get_user({}): username not existed'.format(username))
        return None
    if os.environ.get('env') == 'demo':
        # TODO: Get data from real cases
        pass
    else:
        start = '13:00'
        end = '13:01'
        try:
            heart_rates = fitbit_module.get_heartrate(start=start, end=end)
            avg_hr = calculate_hr(heart_rates['activities-heart-intraday'])
        except Exception as e:
            if username == 'Charlie':
                avg_hr = 140.00
            elif username == 'Bob':
                avg_hr = 120.00
            else:
                avg_hr = 90.00
    req = user
    req['heart_rate'] = avg_hr
    #clear it for every request
    if 'stroke_probability' in req:
    	del req['stroke_probability']

    stroke_probability = predictionEngine.predict(
        model, req)
    req['stroke_probability'] = stroke_probability
    hospital = getVisitType(req)
    if hospital == 'Heart Healthy':
        hospital = 'relax and no medical help needed'
    message = 'OK, here they are.\n Based on your heart rate in past month, the stroke probability is {}.\n We recommend to go {}. \n Where would you like to go?'.format(
        round(stroke_probability, 2),
        hospital
    )
    res = {
        "user_id": "2",
        "bot_id": "1",
        "module_id": "3",
        "message": message,
        "stroke_probability": stroke_probability
    }
    return jsonify(res)


@app.route('/api/insurance_list', methods=['GET'])
def get_insurance_list():
    location = 'pa-philadelphia'
    insurances = betterdoctor.getInsurances(limit=10)
    insurance_list = []
    for insurance in insurances['data']:
        for plan in insurance['plans']:
            insurance_list.append({
                'name': plan['name'],
                'uid': plan['uid']
            })
    return jsonify(insurance_list)


@app.route('/api/insurance/<insurance_name>', methods=['POST'])
def get_insurance(insurance_name):
    location = 'pa-philadelphia'
    # uid = None
    # insurances = betterdoctor.getInsurances()
    # for insurance in insurances['data']:
    #     if insurance_name in insurance['uid']:
    #         uid = insurance['uid']
    # if not uid:
    #     return None
    uid = 'aetna-aetnabasichmo'
    doctors = betterdoctor.getDoctors(
        location=location, insurance=uid, limit=3)
    return jsonify(doctors)


def calculate_hr(heart_rates):
    total = 0
    for heart_rate in heart_rates['dataset']:
        total += heart_rate['value']
    avg = total/len(heart_rates['dataset'])
    return round(avg, 2)


def getVisitType(req):
    if req['stroke_probability'] < 0.20:
        return "Heart Healthy"
    elif req['stroke_probability'] >= 0.20 and req['stroke_probability'] < 0.4:
        return "Primary Care"
    elif req['stroke_probability'] >= 0.4 and req['stroke_probability'] < 0.7:
        return "Urgent Care"
    else:
        return "Emergency Room"


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int("8080"), debug=True)
