from bs4 import BeautifulSoup
from time import time
import aiohttp
import re
import json
import datetime
import asyncio
import itertools


async def public_transport_connections(sources, destinations):
    async with aiohttp.ClientSession() as session:
        async def fetch(source, destination):
            url = f'https://idos.idnes.cz/odis/spojeni/vysledky/?f={source}&fc=303003&t={destination}&tc=303003'
            start = time()
            links = []
            async with session.get(url) as r:
                text = await r.text()
                print(f"{url} took {time() - start} sec")
                dom = BeautifulSoup(text, 'html.parser')

                for node in dom.select('.connection.box'):
                    link = {
                        'connections': [],
                    }
                    total = node.select('.total strong')[0].get_text()
                    if 'hod' in total:
                        continue

                    link['total'] = int(total.split(' ')[0])
                    for a in node.select('.outside-of-popup'):
                        def to_datetime(s):
                            date = datetime.datetime.now()
                            hour, minute = s.split(':')
                            return date.replace(hour=int(hour), minute=int(minute), second=0)

                        def p(node):
                            return {
                                'time': to_datetime(node.select('.time')[0].get_text()),
                                'station': node.select('.station strong')[0].get_text(),
                            }

                        link['connections'].append({
                            'link': a.select('.line-title h3')[0].get_text(),
                            'from': p(a.select('.stations .item')[0]),
                            'to': p(a.select('.stations .item')[1]),
                        })

                    links.append(link)
            return links

        futures = await asyncio.gather(*[fetch(source, dest) for source, dest in itertools.product(sources, destinations)])
        all_links = list(itertools.chain(*futures))

        def time_to_num(t):
            return t
            p = t.split(':')
            p[0] = int(p[0])
            p[1] = int(p[1])

            return p[0] * 60 + p[1]

        all_links.sort(key=lambda i: (time_to_num(i['connections'][-1]['to']['time']), i["total"]))
        return all_links
