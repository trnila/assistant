#!/usr/bin/env python3
import datetime
import ipaddress
import pickle

import redis.asyncio as redis
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from starlette.responses import FileResponse

# from werkzeug.middleware.proxy_fix import ProxyFix
# from flask_redis import FlaskRedis
from lunches import gather_restaurants
from public_transport import public_transport_connections

app = FastAPI(debug=True)
templates = Jinja2Templates(directory="templates")
# app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1)
redis_client = redis.Redis()


@app.get("/")
def index():
    return FileResponse("index.html")


@app.get("/public_transport")
async def public_transport(request: Request):
    srcs = ["Václava Jiřikovského"]
    dsts = ["Hlavní třída", "Rektorát VŠB", "Pustkovecká", "Poruba,Studentské koleje"]
    if datetime.datetime.now().hour >= 12:
        srcs, dsts = dsts, srcs

    return templates.TemplateResponse(
        request=request,
        name="public_transport.html",
        context={"connections": await public_transport_connections(srcs, dsts)},
    )


@app.get("/lunch.json")
@app.post("/lunch.json")
async def lunch(request: Request):
    now = int(datetime.datetime.now().timestamp())
    key = f'restaurants.{datetime.date.today().strftime("%d-%m-%Y")}'
    result_str = await redis_client.get(key)
    if not result_str or request.method == "POST":
        throttle_key = f"{key}.throttle"
        if await redis_client.incr(throttle_key) != 1:
            return {"error": "Fetch limit reached. Try again later."}
        await redis_client.expire(throttle_key, 60 * 3)

        result = {
            "last_fetch": now,
            "fetch_count": await redis_client.incr(f"{key}.fetch_count"),
            "restaurants": list(await gather_restaurants()),
        }
        await redis_client.set(key, pickle.dumps(result))
    else:
        result = pickle.loads(result_str)

    disallow_nets = [
        ipaddress.ip_network(net)
        for net in ["127.0.0.0/8", "::1/128", "192.168.1.0/24", "89.103.137.232/32", "2001:470:5816::/48"]
    ]
    for net in disallow_nets:
        if net.version == 4:
            disallow_nets.append(ipaddress.ip_network(f"::ffff:{net.network_address}/{96 + net.prefixlen}"))

    visitor_addr = ipaddress.ip_address(request.client.host)
    if not any([net for net in disallow_nets if visitor_addr in net]):  # noqa: C419
        await redis_client.incr(f"{key}.access_count")
        await redis_client.setnx(f"{key}.first_access", now)

    async def get(k):
        val = await redis_client.get(f"{key}.{k}")
        if val:
            result[k] = int(val)
        else:
            result[k] = 0

    await get("access_count")
    await get("first_access")
    return result
