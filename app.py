#!/usr/bin/env python3
import datetime
import pickle
from flask import Flask, render_template
from flask_redis import FlaskRedis
from lunches import gather_restaurants
from public_transport import public_transport_connections



app = Flask(__name__)
redis_client = FlaskRedis(app)

@app.route("/public_transport")
async def public_transport():
    srcs = ["Václava Jiřikovského"]
    dsts = ["Hlavní třída", "Rektorát VŠB", "Pustkovecká", "Poruba,Studentské koleje"]
    if datetime.datetime.now().hour >= 12:
        srcs, dsts = dsts, srcs

    return render_template(
            'public_transport.html',
            connections=await public_transport_connections(srcs, dsts)
    )

@app.route("/lunch", defaults={'format': 'html'})
@app.route("/lunch.json", defaults={'format': 'json'})
async def lunch(format):
    key = f'restaurants.{datetime.date.today().strftime("%d-%m-%Y")}'
    restaurants = redis_client.get(key)
    if not restaurants:
        restaurants = list(await gather_restaurants())
        redis_client.set(key, pickle.dumps(restaurants), ex=60 * 60 * 24)
    else:
        restaurants = pickle.loads(restaurants)

    if format == 'json':
        return {'restaurants': restaurants}
    else:
        return render_template(
                'lunch.html',
                restaurants=restaurants,
                date=datetime.datetime.now(),
        )

from waitress import serve
serve(app, port=5000, host="127.0.0.1")

