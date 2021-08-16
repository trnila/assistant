import datetime
from flask import Flask, render_template
from lunches import gather_restaurants
from public_transport import public_transport_connections


app = Flask(__name__)

@app.route("/public_transport")
async def public_transport():
    srcs = ["Václava Jiřikovského"]
    dsts = ["Hlavní třída", "Pustkovecká", "Krásnopolská", "Poruba,Studentské koleje"]
    if datetime.datetime.now().hour >= 12:
        srcs, dsts = dsts, srcs

    return render_template(
            'public_transport.html',
            connections=await public_transport_connections(srcs, dsts)
    )

@app.route("/lunch")
async def lunch():
    return render_template(
            'lunch.html',
            restaurants=await gather_restaurants()
    )
