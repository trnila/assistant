#!/usr/bin/env python3
from bs4 import BeautifulSoup
from time import time
import datetime
import itertools
import requests
from concurrent.futures import ThreadPoolExecutor


def public_transport_connections(sources, destinations):
    def fetch(source, destination):
        url = f'https://idos.idnes.cz/odis/spojeni/vysledky/?f={source}&fc=303003&t={destination}&tc=303003'
        start = time()
        links = []
        text = requests.get(url).text
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

    searches = list(itertools.product(sources, destinations))
    with ThreadPoolExecutor(max_workers=len(searches)) as pool:
        all_links = list(itertools.chain(*pool.map(lambda s: fetch(*s), searches)))

    def time_to_num(t):
        return t
        p = t.split(':')
        p[0] = int(p[0])
        p[1] = int(p[1])

        return p[0] * 60 + p[1]

    all_links.sort(key=lambda i: (time_to_num(i['connections'][-1]['to']['time']), i["total"]))
    return all_links

if __name__ == '__main__':
    from pprint import pprint
    result = public_transport_connections(["Václava Jiřikovského"], ["Hlavní třída", "Rektorát VŠB", "Pustkovecká", "Poruba,Studentské koleje"])
    pprint(result)
