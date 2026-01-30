#!/usr/bin/env -S uv run --script
import asyncio
import datetime
import itertools
from time import time

import httpx
from pydantic import BaseModel
from selectolax.parser import HTMLParser, Node


class Station(BaseModel):
    time: datetime.datetime
    station: str


class Connection(BaseModel):
    link: str
    from_: Station
    to: Station


class Link(BaseModel):
    total: int
    connections: list[Connection]


async def public_transport_connections(sources: list[str], destinations: list[str]) -> list[Link]:
    async def fetch(http: httpx.AsyncClient, source: str, destination: str) -> list[Link]:
        url = f"https://idos.cz/odis/spojeni/vysledky/?f={source}&fc=303003&t={destination}&tc=303003"
        start = time()
        links = []
        resp = await http.get(url)
        print(f"{url} took {time() - start} sec")
        dom = HTMLParser(resp.text)

        for node in dom.css(".connection.box"):
            total = node.css(".total strong")[0].text()
            if "hod" in total:
                continue

            connections = []
            for a in node.css(".outside-of-popup"):

                def to_datetime(s: str) -> datetime.datetime:
                    date = datetime.datetime.now()
                    hour, minute = s.split(":")
                    return date.replace(hour=int(hour), minute=int(minute), second=0)

                def p(node: Node) -> Station:
                    return Station(
                        time=to_datetime(node.css(".time")[0].text()),
                        station=node.css(".station strong")[0].text(),
                    )

                connections.append(
                    Connection(
                        link=a.css(".line-title h3")[0].text(),
                        from_=p(a.css(".stations .item")[0]),
                        to=p(a.css(".stations .item")[1]),
                    )
                )

            links.append(Link(total=int(total.split(" ")[0]), connections=connections))
        return links

    searches = list(itertools.product(sources, destinations))
    async with httpx.AsyncClient() as http:
        results = await asyncio.gather(*[fetch(http, *s) for s in searches])
        all_links = list(itertools.chain(*results))

    all_links.sort(key=lambda i: (i.connections[-1].to.time, i.total))
    return all_links


if __name__ == "__main__":
    from pprint import pprint

    result = asyncio.run(
        public_transport_connections(
            ["Václava Jiřikovského"], ["Hlavní třída", "Rektorát VŠB", "Pustkovecká", "Poruba,Studentské koleje"]
        )
    )
    pprint(result)
