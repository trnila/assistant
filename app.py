#!/usr/bin/env python3
import datetime
import pickle
from flask import Flask, render_template, request, redirect
from flask_redis import FlaskRedis
from lunches import gather_restaurants
from public_transport import public_transport_connections



app = Flask(__name__)
redis_client = FlaskRedis(app)

@app.route("/public_transport")
def public_transport():
    srcs = ["Václava Jiřikovského"]
    dsts = ["Hlavní třída", "Rektorát VŠB", "Pustkovecká", "Poruba,Studentské koleje"]
    if datetime.datetime.now().hour >= 12:
        srcs, dsts = dsts, srcs

    return render_template(
            'public_transport.html',
            connections=public_transport_connections(srcs, dsts)
    )

@app.route('/lunch_stats.html')
@app.route("/lunch.json", methods=['GET', 'POST'])
def lunch():
    key = f'restaurants.{datetime.date.today().strftime("%d-%m-%Y")}'
    result = redis_client.get(key)
    if not result or request.method == 'POST':
        result = {
            'last_fetch': int(datetime.datetime.now().timestamp()),
            'fetch_count': redis_client.incr(f'{key}.fetch_count'),
            'restaurants': list(gather_restaurants()),
        }
        redis_client.set(key, pickle.dumps(result), ex=60 * 60 * 24)

        return result
    return pickle.loads(result)

from waitress import serve
serve(app, port=5000, host="127.0.0.1")

