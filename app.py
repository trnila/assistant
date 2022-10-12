#!/usr/bin/env python3
import datetime
import pickle
import ipaddress
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

@app.route("/lunch.json", methods=['GET', 'POST'])
def lunch():
    now = int(datetime.datetime.now().timestamp())
    key = f'restaurants.{datetime.date.today().strftime("%d-%m-%Y")}'
    result_str = redis_client.get(key)
    if not result_str or request.method == 'POST':
        result = {
            'last_fetch': now,
            'fetch_count': redis_client.incr(f'{key}.fetch_count'),
            'restaurants': list(gather_restaurants()),
        }
        redis_client.set(key, pickle.dumps(result), ex=60 * 60 * 24)
    else:
        result = pickle.loads(result_str)

    disallow_nets = [ipaddress.ip_network(net) for net in [
        '127.0.0.0/8',
        '::1/128',
        '192.168.1.0/24',
        '89.103.137.232/32',
        '2001:470:5816::/48'
    ]]

    visitor_addr = ipaddress.ip_address(request.remote_addr)
    if not any([net for net in disallow_nets if visitor_addr in net]):
        redis_client.incr(f'{key}.access_count');
        redis_client.setnx(f'{key}.first_access', now)
    
    def get(k):
        val = redis_client.get(f'{key}.{k}')
        if val:
            result[k] = int(val)
        else:
            result[k] = 0

    get('access_count')
    get('first_access')
    return result


from waitress import serve
serve(app, port=5000, host="127.0.0.1")

