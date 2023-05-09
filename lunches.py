#!/usr/bin/env python3
from bs4 import BeautifulSoup
import subprocess
import re
import json
import datetime
import itertools
import traceback
import tempfile
import logging
import requests
import string
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
import time

days = ['Pondělí', 'Úterý', 'Středa', 'Čtvrtek', 'Pátek', 'Sobota', 'Neděle']
USER_AGENT = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/105.0.0.0 Safari/537.36'

logging.basicConfig(level=logging.DEBUG)

def strip_tags(s):
    return re.sub(r'(<[^>]+>|/>)', '', s)

def restaurant(title, url=None):
    def wrapper(fn):
        def wrap(*args, **kwargs):
            return fn(*args, **kwargs)
        wrap.parser = {
            'name': fn.__name__,
            'title': title,
            'url': url,
            'args': fn.__code__.co_varnames[:fn.__code__.co_argcount],
        }
        return wrap
    return wrapper

@dataclass
class Soup:
    name: str
    price: int = None

@dataclass
class Lunch:
    name: str
    num: int = None
    price: int = None
    ingredients: str = None

@restaurant("Bistro IN", "https://bistroin.choiceqr.com/delivery")
def bistroin(dom):
    data = json.loads(dom.select('#__NEXT_DATA__')[0].get_text())

    for item in data["props"]["app"]["menu"]:
        ingredients = re.sub('Al\. \(.+', '', item['description'])
        price = item['price'] // 100
        if 'Polévka k menu:' in item['name']:
            yield Soup(name=item['name'].split(':')[1], price=price)
        else:
            match = re.match('^\s*(?P<num>[0-9]+)\s*\.\s*(?P<name>.+)', item['name'])
            if match:
                yield Lunch(**match.groupdict(), price=price - 5, ingredients=ingredients)

@restaurant("U jarosu", "https://www.ujarosu.cz/cz/denni-menu/")
def u_jarosu(dom):
    today = datetime.datetime.strftime(datetime.datetime.now(), "%d. %m. %Y")
    for row in dom.select('.celyden'):
        parsed_day = row.select('.datum')[0].get_text()
        if parsed_day == today:
            records = row.select('.tabulka p')
            records = [r.get_text().strip() for r in records]
            records = [records[i:i+3] for i in range(0, len(records), 3)]
            for first, name, price in records:
                if first == 'Polévka':
                    yield Soup(name)
                else:
                    yield Lunch(name, price=price, num=first.split('.')[0])

@restaurant("U zlateho lva", "http://www.zlatylev.com/menu_zlaty_lev.html")
def u_zlateho_lva(dom):
    day_nth = datetime.datetime.today().weekday()
    text = dom.select('.xr_txt.xr_s0')[0].get_text()

    capturing = False
    counter = 0
    state = 'num'
    for line in text.splitlines():
        line = line.strip()

        if line.startswith(days[day_nth]):
            capturing = True
        elif capturing:
            if day_nth < 4 and line.startswith(days[day_nth + 1]):
                break
            soup_prefix = 'Polévka:'
            if line.startswith(soup_prefix):
                yield Soup(line.replace(soup_prefix, ''))
            else:
                if state == 'num':
                    if re.match('^[0-9]+\.', line):
                        line, name = line.split('.', 1)
                        food = Lunch(name=name, num=line)
                        state = 'price' if name else 'name'
                elif state == 'name':
                    if line:
                        food.name = line
                        state = 'price'
                elif state == 'price':
                    if re.match('^[0-9]+\s*(,-|Kč)$', line):
                        food.price = line.split(' ')[0]
                        yield food
                        state = 'num'

@restaurant("Globus", "https://www.globus.cz/ostrava/nabidka/restaurace.html")
def globus(dom):
    for row in dom.select('.restaurant__menu-food-table')[0].select('tr'):
        tds = row.select('td')
        name = tds[1].text
        price = tds[2].text.replace(',–', '') if len(tds) >= 3 else None
        yield (Lunch if price and int(price) > 50 else Soup)(name=name, price=price)

@restaurant("Jacks Burger", "https://www.zomato.com/cs/widgets/daily_menu.php?entity_id=16525845")
def jacks_burger(dom):
    day_nth = datetime.datetime.today().weekday()

    started = False
    prev_line = ""
    for el in dom.select('.main-body > div'):
        if 'line-wider' in el.get('class', []):
            break
        name = el.select_one('.item-name')
        if name is None:
            continue
        name = name.text.strip()
        if 'ROZVOZ PŘES' in name.upper() or '---------' in name or 'JBB OSTRAVA' in name.upper():
            continue
        num = None
        if re.match('^[0-9]+\..+', name):
            num = name.split('.')[0]

        if not started:
            yield Soup(name=prev_line)
            started = True

        price = el.select_one('.item-price')
        if price:
            price = price.text.strip()
            yield Lunch(name=name, price=price, num=num)
        else:
            prev_line = name

@restaurant("Poklad", "https://dkpoklad.cz/restaurace/")
def poklad(dom):
    pdf_url = dom.select('.restaurace-box .wp-block-file a')[0]['href']
    pdf = requests.get(pdf_url).content
    text = subprocess.check_output(["pdftotext", "-layout", "-", "-"], input=pdf).decode('utf-8')

    today = datetime.datetime.strftime(datetime.datetime.now(), "%-d I %-m")
    tomorrow = datetime.datetime.strftime(datetime.datetime.now() + datetime.timedelta(days=1), "%-d I %-m")
    capturing = False
    soup = True
    item = None
    for line in text.splitlines():
        if today in line:
            capturing = True
        elif capturing:
            if tomorrow in line:
                break
            if soup:
                soup = False
                for s in line.split(' I '):
                    yield Soup(s)
            else:
                m = re.match("^(?P<num>[0-9]+)\s*\.?\s*(?P<name>.*?) (?P<price>[0-9]+) Kč", line)
                if m:
                    if item:
                        yield Lunch(**item)
                    item = m.groupdict()
                elif item:
                    item['name'] += line

    if item:
        yield Lunch(**item)

@restaurant("Trebovicky mlyn", "https://www.trebovickymlyn.cz/")
def trebovicky_mlyn(dom):
    el = dom.select('.soup h2')
    if not el:
        return
    yield Soup(el[0].text)

    for lunch in dom.select('.owl-carousel')[0].select('.menu-post'):
        parts = lunch.select('h2')[0].text.split(')')
        if len(parts) == 2:
            yield Lunch(num=parts[0], name=parts[1], ingredients=lunch.select('h2 + div')[0].text, price=lunch.select('span')[0].text.split(',')[0])

@restaurant("La Strada", "http://www.lastrada.cz/cz/?tpl=plugins/DailyMenu/print&week_shift=")
def lastrada(dom):
    day_nth = datetime.datetime.today().weekday()

    capturing = False
    for tr in dom.select('tr'):
        if 'day' in tr.get('class', []):
            capturing = False
            if days[day_nth] in tr.text or 'Menu na celý týden' in tr.text:
                capturing = True
        elif capturing:
            if 'highlight' in tr.get('class', []):
                yield Lunch(name=tr.select_one('td').text, price=tr.select_one('.price').text)

@restaurant("Ellas", "https://www.restauraceellas.cz/")
def ellas(dom):
    day_nth = datetime.datetime.today().weekday()

    for div in dom.select('.moduletable .custom'):
        if div.find('h3').text.strip() != days[day_nth]:
            continue
        foods = div.select('p')
        yield Soup(name=foods[0].text)

        for food in foods[1:]:
            parts = [strip_tags(s) for s in food.decode_contents().split('<br')]
            num, name = parts[0].split('.')
            yield Lunch(num=num, name=name, ingredients=parts[1], price=parts[2])

@restaurant("La Futura", "http://lafuturaostrava.cz/")
def lafutura(dom):
    for item in dom.select_one('.jet-listing-dynamic-repeater__items').select('.jet-listing-dynamic-repeater__item'):
        tds = item.select('td')
        if tds[0].text.strip() == '𐃸':
            yield Soup(name=tds[1].text)
        else:
            yield Lunch(name=tds[1].text, price=tds[2].text, num=tds[0].text)

def gather_restaurants(allowed_restaurants=None):
    requests.packages.urllib3.util.ssl_.DEFAULT_CIPHERS += ':HIGH:!DH:!aNULL'

    def cleanup(restaurant):
        def fix_name(name):
            uppers = sum(1 for c in name if c.isupper())
            if uppers > len(name) / 2:
                name = name.lower()
                name = name.capitalize()
            name = re.sub('<[^<]+?>', '', name)
            name = re.sub('\d+\s*(g|ml|ks) ', '', name)
            name = re.sub('\([^)]+\)', '', name)
            name = re.sub('(\s*[0-9]+\s*,)+\s*$', '', name)
            name = re.sub('A?\s*[0-9]+(,[0-9]+)*,?', '', name)
            name = name.strip(string.punctuation + string.whitespace + string.digits + '–\xa0')
            name = re.sub(' +', ' ', name)
            return name

        for t in ['lunches', 'soups']:
            num = 0
            for food in restaurant.get(t, []):
                if food.price:
                    if isinstance(food.price, str):
                        try:
                            food.price = int(food.price.replace('Kč', '').replace('.00', '').strip(string.punctuation + string.whitespace))
                        except ValueError as e:
                            print(e)
                            pass
                    else:
                        food.price = int(food.price)

                food.name = fix_name(food.name)
                if t == 'lunches':
                    if food.ingredients:
                        food.ingredients = fix_name(food.ingredients)

                    if isinstance(food.num, str):
                        try:
                            food.num = int(food.num.replace('.', ''))
                        except ValueError as e:
                            logging.exception(e)
                            food.num = None
                    if not food.num:
                        food.num = num + 1
                    num = food.num
        return restaurant

    def collect(parser):
        start = time.time()
        res = {
            'name': parser.parser['title'],
            'url': parser.parser['url'],
        }
        try:
            lunches = []
            soups = []

            args = {}
            arg_names = parser.parser['args']
            if 'res' in arg_names or 'dom' in arg_names:
                response = requests.get(parser.parser['url'], headers={'User-Agent': USER_AGENT})
                response.encoding = 'utf-8'
                if 'res' in arg_names:
                    args['res'] = response.text
                else:
                    args['dom'] = BeautifulSoup(response.text, 'html.parser')

            for item in parser(**args) or []:
                if isinstance(item, Soup):
                    soups.append(item)
                elif isinstance(item, Lunch):
                    lunches.append(item)
                else:
                    raise "Unsupported item"
            return cleanup({
                **res,
                'lunches': lunches,
                'soups': soups,
                'elapsed': time.time() - start,
            })
        except:
            return {
                **res,
                'error': traceback.format_exc(),
                'elapsed': time.time() - start,
            }

    restaurants = [obj for _, obj in globals().items() if hasattr(obj, 'parser')]
    if not allowed_restaurants:
        allowed_restaurants = [r.parser['name'] for r in restaurants]

    with ThreadPoolExecutor(max_workers=len(allowed_restaurants)) as pool:
        return pool.map(collect, [r for r in restaurants if r.parser['name'] in allowed_restaurants])

if __name__ == '__main__':
    from pprint import pprint
    import sys

    allowed_restaurants = None
    if len(sys.argv) > 1:
        allowed_restaurants = sys.argv[1].split(',')
    res = gather_restaurants(allowed_restaurants)
    pprint(list(res), width=180)
