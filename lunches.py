#!/usr/bin/env python3
from bs4 import BeautifulSoup
import subprocess
import re
import json
import datetime
import traceback
import logging
import requests
import string
from html import unescape
from enum import Enum
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
import time

days = ['Pondělí', 'Úterý', 'Středa', 'Čtvrtek', 'Pátek', 'Sobota', 'Neděle']
USER_AGENT = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/105.0.0.0 Safari/537.36'

class Location(str, Enum):
    Poruba = "Poruba",
    Dubina = "Dubina",
    Olomouc = "Olomouc"

logging.basicConfig(level=logging.DEBUG)

def strip_tags(s):
    return re.sub(r'(<[^>]+>|/>)', '', s)

def restaurant(title, url=None, location:Location=None):
    def wrapper(fn):
        def wrap(*args, **kwargs):
            return fn(*args, **kwargs)
        wrap.parser = {
            'name': fn.__name__,
            'title': title,
            'url': url,
            'location': location,
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

def menicka_parser(dom):
    current_day = datetime.datetime.now().strftime("%-d.%-m.%Y")
    for day_dom in dom.select('.content'):
        day = day_dom.select_one('h2').text.strip().split(' ', 2)[1]
        if day != current_day:
            continue

        soup_name = day_dom.select_one('.soup .food').text
        if 'Pro tento den nebylo zadáno menu' in soup_name:
            break
        yield Soup(
            soup_name,
            day_dom.select_one('.soup .prize').text
        )

        for food in day_dom.select('.main'):
            yield Lunch(
                num=food.select_one('.no').text.strip(' .'),
                name=food.select_one('.food').text,
                price=food.select_one('.prize').text,
            )

@restaurant("Bistro IN", "https://bistroin.choiceqr.com/delivery", Location.Poruba)
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

@restaurant("U jarosu", "https://www.ujarosu.cz/cz/denni-menu/", Location.Poruba)
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

@restaurant("U zlateho lva", "http://www.zlatylev.com/menu_zlaty_lev.html", Location.Poruba)
def u_zlateho_lva(dom):
    day_nth = datetime.datetime.today().weekday()
    text = dom.select('.xr_txt.xr_s0')[0].get_text()

    capturing = False
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

@restaurant("Globus", "https://www.globus.cz/ostrava/nabidka/restaurace.html", Location.Poruba)
def globus(dom):
    for row in dom.select('.restaurant__menu-table-row--active')[0].select('tr'):
        tds = row.select('td')
        name = tds[1].text
        price = tds[2].text.replace(',–', '') if len(tds) >= 3 else None
        yield (Lunch if price and int(price) > 50 else Soup)(name=name, price=price)

@restaurant("Jacks Burger", "https://www.zomato.com/cs/widgets/daily_menu.php?entity_id=16525845", Location.Poruba)
def jacks_burger(dom):
    started = False
    full_name = ""
    num = None
    price = None
    for el in dom.select('.main-body > div'):
        if 'line-wider' in el.get('class', []):
            break
        name = el.select_one('.item-name')
        if name is None:
            continue
        name = name.text.strip()
        if 'ROZVOZ PŘES' in name.upper() or '---------' in name or 'JBB OSTRAVA' in name.upper():
            continue

        if re.match('^[0-9]+\..+', name):
            if full_name:
                yield Lunch(name=full_name, price=price, num=num)
                full_name = ""
                price = None
            num = name.split('.')[0]

        full_name += name
        if not started:
            if 'Polévka dle denní nabídky' != full_name:
                yield Soup(name=full_name)
            full_name = ""
            started = True
        else:
            price = el.select_one('.item-price')
            if price:
                price = price.text.strip()
                if price:
                    yield Lunch(name=full_name, price=price, num=num)
                    full_name = ""
                    price = None
                    num = None

@restaurant("Poklad", "https://dkpoklad.cz/restaurace/", Location.Poruba)
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

@restaurant("Trebovicky mlyn", "https://www.trebovickymlyn.cz/", Location.Poruba)
def trebovicky_mlyn(dom):
    el = dom.select('.soup h2')
    if not el:
        return
    yield Soup(el[0].text)

    for lunch in dom.select('.owl-carousel')[0].select('.menu-post'):
        parts = lunch.select('h2')[0].text.split(')')
        if len(parts) == 2:
            yield Lunch(num=parts[0], name=parts[1], ingredients=lunch.select('h2 + div')[0].text, price=lunch.select('span')[0].text.split(',')[0])

@restaurant("La Strada", "http://www.lastrada.cz/cz/?tpl=plugins/DailyMenu/print&week_shift=", Location.Poruba)
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

@restaurant("Ellas", "https://www.restauraceellas.cz/", Location.Poruba)
def ellas(dom):
    day_nth = datetime.datetime.today().weekday()

    for div in dom.select('.moduletable .custom'):
        if div.find('h3').text.strip() != days[day_nth]:
            continue
        foods = div.select('p')
        yield Soup(name=foods[0].text)

        for food in foods[1:]:
            parsed = re.match("\s*(?P<num>[0-9]+)\s*\.\s*(?P<name>[A-Z -]+)\s+(?P<ingredients>.*?)\s*(\([0-9 ,]+\))?\s*(?P<price>[0-9]+),-", food.text).groupdict()
            yield Lunch(**parsed)

@restaurant("Black Kale", "https://deliveryuser.live.boltsvc.net/deliveryClient/public/getMenuCategories?provider_id=64252&version=FW.0.17.8&deviceId=server&deviceType=web&device_name=IOS&device_os_version=Google+Inc.&language=cs-CZ", Location.Poruba)
def black_kale(res):
    res = json.loads(res)
    items = res['data']['items']
    for item in items.values():
        if item['type'] == 'category' and item['name']['value'].lower() == 'polední menu':
            for i, child_id in enumerate(item['child_ids']):
                dish = items[str(child_id)]
                name = dish['name']['value']
                if '+' not in name:
                    t = Soup if i == 0 else Lunch
                    yield t(name=name, price=dish['price']['value'])

@restaurant("Saloon Pub", "http://www.saloon-pub.cz/cs/denni-nabidka/", Location.Poruba)
def saloon_pub(dom):
    day = dom.find(attrs={'id': datetime.datetime.strftime(datetime.datetime.now(), "%Y-%m-%d")})
    if not day:
        return
    day = day.find_next('section')
    yield Soup(name=day.select_one('.category-info').text)
    for tr in day.select('.main-meal-info'):
        yield Lunch(name=tr.select_one('.meal-name').text, price=tr.select_one('.meal-price').text)

@restaurant("Canteen", "https://canteen.cz/menu", Location.Poruba)
def canteen(dom):
    day_nth = datetime.datetime.today().weekday() + 1
    for item in dom.select(f'[data-week-day="{day_nth}"] .food-banner__item'):
        name = item.select_one('h2 a').text
        price = re.search('([0-9]+)\s*kč', item.select_one('.food-banner__item__price').text, flags=re.IGNORECASE).group(1)
        yield Lunch(name=name, price=price)

@restaurant("Kurnik sopa", "https://www.kurniksopahospoda.cz", Location.Poruba)
def kurniksopa(dom):
    for pivo in dom.select('#naCepu-list tr'):
        name = pivo.select_one('.nazev').text
        deg = pivo.select_one('.stupne').text
        type = pivo.select_one('.typ').text
        origin = pivo.select_one('.puvod').text
        yield Lunch(
                name=f"{name} {deg} - {type}, {origin}",
        )

@restaurant("Sbeerka", "https://sbeerka.cz/denni-nabidka", Location.Poruba)
def sbeerka(dom):
    t = None
    for line in dom.select_one('.wysiwyg').text.splitlines():
        line = line.strip()
        if 'Polévky' in line:
            t = Soup
        elif 'Hlavní jídla' in line:
            t = Lunch
        elif t and 'Záloha' not in line:
            m = re.search('(?P<name>.*?)\s*(/[0-9,\s*]+/)?\s*(?P<price>[0-9]+\s*,-)', line)
            if m:
                yield t(**m.groupdict())

    response = requests.get("https://sbeerka.cz/aktualne-na-cepu", headers={'User-Agent': USER_AGENT})
    dom = BeautifulSoup(response.text, 'html.parser')
    for beer in dom.select('.wysiwyg li'):
        price = None
        m = re.search(r'([0-9]+)\s*,-', beer.text)
        if m:
            price = m.group(0)
        yield Lunch(name=beer.text, price=price)

@restaurant("La Futura", "http://lafuturaostrava.cz/", Location.Dubina)
def lafutura(dom):
    container = dom.select_one('.jet-listing-dynamic-repeater__items')
    if not container:
        return
    for item in container.select('.jet-listing-dynamic-repeater__item'):
        tds = item.select('td')
        if tds[0].text.strip() == '𐃸':
            yield Soup(name=tds[1].text)
        else:
            yield Lunch(name=tds[1].text, price=tds[2].text, num=tds[0].text)

@restaurant("Srub", "https://www.menicka.cz/api/iframe/?id=5568", Location.Dubina)
def srub(dom):
    yield from menicka_parser(dom)

@restaurant("U formana", "https://www.menicka.cz/api/iframe/?id=4405", Location.Dubina)
def uformana(dom):
    yield from menicka_parser(dom)

@restaurant("Maston", "https://maston.cz/jidelni-listek/", Location.Dubina)
def maston(dom):
    srcs = dom.select_one('.attachment-large').attrs['srcset']
    img_url = srcs.split(',')[-1].strip().split(' ')[0]

    img = requests.get(img_url).content
    text = subprocess.check_output(["tesseract", "-l", "ces", "--psm", "4", "-", "-"], input=img).decode('utf-8')

    today = datetime.datetime.strftime(datetime.datetime.now(), "%-d%-m")
    capturing = False
    soup = False
    for line in text.splitlines():
        if capturing:
            if 'POLÉVKA' in line:
                if soup:
                    break
                soup = True
                yield Soup(line.split(':', 1)[1])
            else:
                m = re.search('((?P<num>\d)\))?\s*(?P<name>.*?)\s*(?P<price>\d+),-', line)
                if m:
                    yield Lunch(**m.groupdict())
        else:
            if line.replace(' ', '').replace('.', '').endswith(today):
                capturing = True


@restaurant("Kozlovna U Ježka", "https://www.menicka.cz/api/iframe/?id=5122", Location.Dubina)
def kozlovna(dom):
    yield from menicka_parser(dom)

@restaurant("Fontána", "https://www.menicka.cz/api/iframe/?id=1456", Location.Dubina)
def fontana(dom):
    yield from menicka_parser(dom)

@restaurant("Burger & Beer Brothers", "https://www.menicka.cz/api/iframe/?id=7863", Location.Olomouc)
def bbbrothers(dom):
    yield from menicka_parser(dom)

@restaurant("Café Restaurant Caesar", "https://www.menicka.cz/api/iframe/?id=5293", Location.Olomouc)
def caesar(dom):
    yield from menicka_parser(dom)

@restaurant("Morgans restaurant", "https://www.menicka.cz/api/iframe/?id=5294", Location.Olomouc)
def morgans(dom):
    yield from menicka_parser(dom)

def gather_restaurants(allowed_restaurants=None):
    def cleanup(restaurant):
        def fix_name(name):
            name = unescape(name)
            name = re.sub('<[^<]+?>', '', name)
            name = re.sub('\s*(,|:)\s*', '\\1 ', name)
            name = re.sub('\d+\s*(g|ml|l|ks) ', '', name)
            name = re.sub('\([^)]+\)', '', name)
            name = re.sub('(\s*[0-9]+\s*,)+\s*$', '', name)
            name = re.sub('A?\s*[0-9]+(,[0-9]+)*,? ', '', name)
            name = re.sub('(s|š|S|Š)vestk', 'Trnk', name)
            name = name.strip(string.punctuation + string.whitespace + string.digits + '–—\xa0')
            name = re.sub(' +', ' ', name)
            uppers = sum(1 for c in name if c.isupper())
            if uppers > len(name) / 2:
                name = name.lower()
                name = name.capitalize()
            return name

        for t in ['lunches', 'soups']:
            num = 0
            for food in restaurant.get(t, []):
                if food.price:
                    if isinstance(food.price, str):
                        try:
                            sanitized = re.sub('kč', '', food.price, flags=re.IGNORECASE)
                            sanitized = sanitized.replace('.00', '').strip(string.punctuation + string.whitespace)
                            food.price = int(sanitized)
                        except ValueError as e:
                            print(e)
                    else:
                        food.price = int(food.price)
                else:
                    food.price = None

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
            'location': parser.parser['location'],
        }
        try:
            lunches = []
            soups = []

            args = {}
            arg_names = parser.parser['args']
            if 'res' in arg_names or 'dom' in arg_names:
                response = requests.get(parser.parser['url'], headers={'User-Agent': USER_AGENT})
                if 'utf-8' in response.text:
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
        except: # noqa: E722
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
    import sys

    allowed_restaurants = None
    if len(sys.argv) > 1:
        allowed_restaurants = sys.argv[1].split(',')
    restaurants = list(gather_restaurants(allowed_restaurants))

    exit_code = 0
    for i, restaurant in enumerate(restaurants):
        print()
        print(restaurant['name'], f"({restaurant['elapsed']:.3}s)")
        if 'error' in restaurant:
            exit_code = 1
            print(restaurant['error'])
        else:
            for soup in restaurant['soups']:
                print(' ', soup)
            for lunch in restaurant['lunches']:
                print(' ', lunch)

    exit(exit_code)
