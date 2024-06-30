#!/usr/bin/env python3
import asyncio
import datetime
import itertools
from time import time

import httpx
from selectolax.parser import HTMLParser


async def public_transport_connections(sources, destinations):
    async def fetch(http, source, destination):
        url = f"https://idos.idnes.cz/odis/spojeni/vysledky/?f={source}&fc=303003&t={destination}&tc=303003"
        start = time()
        links = []
        resp = await http.get(url)
        print(f"{url} took {time() - start} sec")
        dom = HTMLParser(resp.text)

        for node in dom.css(".connection.box"):
            link = {
                "connections": [],
            }
            total = node.css(".total strong")[0].text()
            if "hod" in total:
                continue

            link["total"] = int(total.split(" ")[0])
            for a in node.css(".outside-of-popup"):

                def to_datetime(s):
                    date = datetime.datetime.now()
                    hour, minute = s.split(":")
                    return date.replace(hour=int(hour), minute=int(minute), second=0)

                def p(node):
                    return {
                        "time": to_datetime(node.css_first(".time").text()),
                        "station": node.css_first(".station strong").text(),
                    }

                link["connections"].append(
                    {
                        "link": a.css_first(".line-title h3").text(),
                        "from": p(a.css_first(".stations .item")),
                        "to": p(a.css(".stations .item")[1]),
                    }
                )

            links.append(link)
        return links

    searches = list(itertools.product(sources, destinations))
    async with httpx.AsyncClient() as http:
        results = await asyncio.gather(*[fetch(http, *s) for s in searches])
        all_links = list(itertools.chain(*results))

    def time_to_num(t):
        return t
        p = t.split(":")
        p[0] = int(p[0])
        p[1] = int(p[1])

        return p[0] * 60 + p[1]

    all_links.sort(key=lambda i: (time_to_num(i["connections"][-1]["to"]["time"]), i["total"]))
    return all_links


if __name__ == "__main__":
    from pprint import pprint

    result = asyncio.run(
        public_transport_connections(
            ["Václava Jiřikovského"], ["Hlavní třída", "Rektorát VŠB", "Pustkovecká", "Poruba,Studentské koleje"]
        )
    )
    pprint(result)
