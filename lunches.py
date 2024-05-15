#!/usr/bin/env python3
from selectolax.parser import HTMLParser, Selector
import subprocess
import re
import json
import datetime
import traceback
import logging
import httpx as requests
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
    for day_dom in dom.css('.content'):
        day = day_dom.css_first('h2').text(strip=True).split(' ', 2)[1]
        if current_day not in day:
            continue

        soup_el = day_dom.css_first('.soup .food')
        if soup_el:
            soup_name = soup_el.text()
            if 'Pro tento den nebylo zadáno menu' in soup_name:
                break
            yield Soup(
                soup_name,
                day_dom.css_first('.soup .prize').text()
            )

        for food in day_dom.css('.main'):
            yield Lunch(
                num=food.css_first('.no').text().strip(' .'),
                name=food.css_first('.food').text(),
                price=food.css_first('.prize').text(),
            )

@restaurant("Bistro IN", "https://bistroin.choiceqr.com/delivery", Location.Poruba)
def bistroin(dom):
    data = json.loads(dom.css_first('#__NEXT_DATA__').text())

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
    for row in dom.css('.celyden'):
        parsed_day = row.css_first('.datum').text()
        if parsed_day == today:
            records = row.css('.tabulka p')
            records = [r.text().strip() for r in records]
            records = [records[i:i+3] for i in range(0, len(records), 3)]
            for first, name, price in records:
                if first == 'Polévka':
                    yield Soup(name)
                else:
                    yield Lunch(name, price=price, num=first.split('.')[0])

@restaurant("U zlateho lva", "http://www.zlatylev.com/menu_zlaty_lev.html", Location.Poruba)
def u_zlateho_lva(dom):
    day_nth = datetime.datetime.today().weekday()
    text = dom.css_first('.xr_txt.xr_s0').text()

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

@restaurant("Globus", "https://www.globus.cz/ostrava/sluzby-a-produkty/restaurace", Location.Poruba)
def globus(dom):
    for row in dom.css('.space-y-2 .flex'):
        spans = row.css('* > span')
        price = fix_price(spans[2].text())
        t = Soup if price < 50 else Lunch
        yield t(spans[1].text(), price=price)

@restaurant("Jacks Burger", "https://www.zomato.com/cs/widgets/daily_menu.php?entity_id=16525845", Location.Poruba)
def jacks_burger(dom):
    started = False
    full_name = ""
    num = None
    price = None
    for el in dom.css('.main-body > div'):
        if el.css_matches('.line-wider'):
            break
        name = el.css_first('.item-name')
        if name is None:
            continue
        name = name.text(strip=True)
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
            price = el.css_first('.item-price')
            if price:
                price = price.text(strip=True)
                if price:
                    yield Lunch(name=full_name, price=price, num=num)
                    full_name = ""
                    price = None
                    num = None

@restaurant("Poklad", "https://dkpoklad.cz/restaurace/", Location.Poruba)
def poklad(dom):
    pdf_url = dom.css_first('.restaurace-box .wp-block-file a').attributes['href']
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
            if tomorrow in line or 'NABÍDKA NÁPOJŮ' in line:
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
    el = dom.css_first('.soup h2')
    if not el:
        return
    yield Soup(el.text())

    for lunch in dom.css_first('.owl-carousel').css('.menu-post'):
        parts = lunch.css_first('h2').text().split(')')
        if len(parts) == 2:
            yield Lunch(num=parts[0], name=parts[1], ingredients=lunch.css_first('h2 + div').text(), price=lunch.css_first('span').text().split(',')[0])

@restaurant("La Strada", "http://www.lastrada.cz/cz/?tpl=plugins/DailyMenu/print&week_shift=", Location.Poruba)
def lastrada(dom):
    day_nth = datetime.datetime.today().weekday()

    capturing = False
    for tr in dom.css('tr'):
        if tr.css_matches('.day'):
            capturing = False
            if days[day_nth] in tr.text() or 'Menu na celý týden' in tr.text():
                capturing = True
        elif capturing:
            if tr.css_matches('.highlight'):
                yield Lunch(name=tr.css_first('td').text(), price=tr.css_first('.price').text())

@restaurant("Ellas", "https://www.restauraceellas.cz/", Location.Poruba)
def ellas(dom):
    day_nth = datetime.datetime.today().weekday()

    for div in dom.css('.moduletable .custom'):
        if div.css_first('h3').text(strip=True) != days[day_nth]:
            continue
        foods = div.css('p')
        yield Soup(name=foods[0].text())

        for food in foods[1:]:
            if food.text():
                parsed = re.match("\s*(?P<num>[0-9]+)\s*\.\s*(?P<name>[A-Z -]+)\s+(?P<ingredients>.*?)\s*(\([0-9 ,]+\))?\s*(?P<price>[0-9]+),-", food.text()).groupdict()
                yield Lunch(**parsed)

@restaurant("Saloon Pub", "http://www.saloon-pub.cz/cs/denni-nabidka/", Location.Poruba)
def saloon_pub(dom):
    day = dom.css_first(f'#{datetime.datetime.strftime(datetime.datetime.now(), "%Y-%m-%d")} + section')
    if not day:
        return
    yield Soup(name=day.css_first('.category-info').text())
    for tr in day.css('.main-meal-info'):
        yield Lunch(name=tr.css_first('.meal-name').text(), price=tr.css_first('.meal-price').text())

@restaurant("Parlament", "https://www.restauraceparlament.cz/", Location.Poruba)
def parlament(dom):
    day_nth = datetime.datetime.today().weekday()
    day = Selector(dom.css_first('.txt'), 'div div').text_contains(days[day_nth])
    if day:
        day = day.matches[0]
        yield Soup(day.css_first('* + dt').text())
        for line in day.css_first('* + dt + p').text().splitlines():
            m = re.match('(?P<num>\d+)\.\s*(?P<name>.*?)(?P<price>\d+),-Kč', line)
            if m:
                yield Lunch(**m.groupdict())

@restaurant("Plzenka aura", "https://www.plzenkaaura.cz/denni-menu", Location.Poruba)
def plzenka(dom):
    food_type = None
    for el in dom.css('.list-items > *'):
        if el.tag == 'h5':
            food_type = {
                "POLÉVKA": Soup,
                "HLAVNÍ JÍDLO": Lunch,
            }.get(el.text(strip=True), None)
        elif food_type:
            if food_type == Soup:
                yield Soup(el.css_first('.modify_item').text())
            else:
                yield Lunch(
                    name=el.css_first('.modify_item').text(),
                    ingredients=el.css_first('.food-info').text(),
                    price=el.css_first('.menu-price').text(),
            )

@restaurant("El Amigo Muerto", "https://www.menicka.cz/api/iframe/?id=5560", Location.Poruba)
def el_amigo_muerto(dom):
    yield from menicka_parser(dom)

@restaurant("Rusty Bell Pub", "https://www.menicka.cz/api/iframe/?id=1547", Location.Poruba)
def rusty_bell_pub(dom):
    foods = list(menicka_parser(dom))
    if not foods:
        return
    yield Soup(foods[1].name)
    for food in foods[2:]:
        yield food

@restaurant("Kurnik sopa", "https://www.kurniksopahospoda.cz", Location.Poruba)
def kurniksopa(dom):
    for pivo in dom.css('#naCepu-list tr'):
        name = pivo.css_first('.nazev').text()
        deg = pivo.css_first('.stupne').text()
        type = pivo.css_first('.typ').text()
        origin = pivo.css_first('.puvod').text()
        yield Lunch(
                name=f"{name} {deg} - {type}, {origin}",
        )

@restaurant("Sbeerka", "https://sbeerka.cz/denni-nabidka", Location.Poruba)
def sbeerka(dom):
    REGEXP = re.compile('(?P<name>.*?)\s*(/[0-9,\s*]+/)?\s*(?P<price>[0-9]+\s*,-)')
    t = None
    for line in dom.css_first('.wysiwyg').text().splitlines():
        line = line.strip()
        if 'Polévky' in line:
            t = Soup
        elif 'Hlavní jídla' in line:
            t = Lunch
        elif t and 'Záloha' not in line:
            m = REGEXP.search(line)
            if m:
                yield t(**m.groupdict())

    PRICE_REGEXP = re.compile(r'([0-9]+)\s*,-')
    response = requests.get("https://sbeerka.cz/aktualne-na-cepu", headers={'User-Agent': USER_AGENT})
    dom = HTMLParser(response.text)
    for beer in dom.css('.wysiwyg li'):
        price = None
        m = PRICE_REGEXP.search(beer.text())
        if m:
            price = m.group(0)
        yield Lunch(name=beer.text(), price=price)

@restaurant("La Futura", "https://lafuturaostrava.cz/", Location.Dubina)
def lafutura(dom):
    container = dom.css_first('.jet-listing-dynamic-repeater__items')
    if not container:
        return
    for item in container.css('.jet-listing-dynamic-repeater__item'):
        tds = item.css('td')
        if "POLÉVKA" in tds[0].text(strip=True).upper():
            yield Soup(name=tds[1].text())
        else:
            yield Lunch(name=tds[1].text(), price=tds[2].text(), num=tds[0].text())

@restaurant("Srub", "https://www.menicka.cz/api/iframe/?id=5568", Location.Dubina)
def srub(dom):
    yield from menicka_parser(dom)

@restaurant("U formana", "https://www.menicka.cz/api/iframe/?id=4405", Location.Dubina)
def uformana(dom):
    yield from menicka_parser(dom)

@restaurant("Maston", "https://maston.cz/jidelni-listek/", Location.Dubina)
def maston(dom):
    srcs = dom.css_first('.attachment-large').attrs['srcset']
    img_url = srcs.split(',')[-1].strip().split(' ')[0]

    img = requests.get(img_url).content
    text = subprocess.check_output(["tesseract", "-l", "ces", "--psm", "4", "-", "-"], input=img).decode('utf-8')

    today = datetime.datetime.strftime(datetime.datetime.now(), "%-d%-m")
    tomorrow = datetime.datetime.strftime(datetime.datetime.now() + datetime.timedelta(days=1), "%-d%-m")
    capturing = False
    for line in text.splitlines():
        txt = line.replace(' ', '').replace('.', '')
        if txt.endswith(today):
            capturing = True
        elif capturing:
            if 'SAMOSTATN' in txt.upper() or tomorrow in txt:
                break
            if 'POLÉVKA' in line:
                yield Soup(line.split(':', 1)[1])
            else:
                m = re.search('((?P<num>\d)\))?\s*(?P<name>.+)(\s*(?P<price>\d+),-)?', line)
                if m:
                    yield Lunch(**m.groupdict())

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

@restaurant("U Mořice", "https://www.menicka.cz/api/iframe/?id=5299", Location.Olomouc)
def moric(dom):
    yield from menicka_parser(dom)

@restaurant("Kikiriki", "https://www.menicka.cz/api/iframe/?id=5309", Location.Olomouc)
def kikiriki(dom):
    current_day = datetime.datetime.now().strftime("%-d.%-m.%Y")
    for day_dom in dom.css('.content'):
        day = day_dom.css_first('h2').text(strip=True).split(' ', 2)[1]
        if current_day not in day:
            continue

        parsed_soup = False
        for food in day_dom.css('.soup'):
            if 'Pro tento den nebylo zadáno menu' in food.text():
                break
            txt = food.css_first('.food').text()
            txt = re.sub('^\s*[0-9]+\s*,\s*[0-9]+\s*l?', '', txt)
            soup, lunch = re.split('\+|,', txt, 1)

            if not parsed_soup:
                parsed_soup = True
                yield Soup(soup)

            yield Lunch(
                name=lunch,
                price=food.css_first('.prize').text(),
            )

@restaurant("U Kristýna", "https://www.menicka.cz/api/iframe/?id=5471", Location.Olomouc)
def kristyn(dom):
    yield from menicka_parser(dom)

def fix_price(price):
    if not price:
        return None
    if not isinstance(price, str):
        return int(price)
    try:
        sanitized = re.sub('kč', '', price, flags=re.IGNORECASE)
        sanitized = sanitized.replace('.00', '').strip(string.punctuation + string.whitespace)
        return int(sanitized)
    except ValueError as e:
        print(e)
    return None

def gather_restaurants(allowed_restaurants=None):
    replacements = [
        (re.compile('^\s*(Polévka|BUSINESS MENU)', re.IGNORECASE), ''),
        (re.compile('k menu\s*$'), ''),
        (re.compile('(s|š|S|Š)vestk'), 'Trnk'),
        (re.compile('\s*(,|:)\s*'), '\\1 '),
        (re.compile('<[^<]+?>'), ''),
        (re.compile('\d+\s*(g|ml|l|ks) '), ''),
        (re.compile('\([^)]+\)'), ''),
        (re.compile('(\s*[0-9]+\s*,)+\s*$'), ''),
        (re.compile('A?\s*[0-9]+(,[0-9]+)*,? '), ''),
        (re.compile(' +'), ' '),
    ]
    UPPER_REGEXP = re.compile('[A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ]')

    def detect_encoding(text):
        if b'windows-1250' in text:
            return 'windows-1250'
        return 'utf-8'
    client = requests.Client(default_encoding=detect_encoding, headers={'User-Agent': USER_AGENT})

    def cleanup(restaurant):
        def fix_name(name):
            name = unescape(name)
            for pattern, replacement in replacements:
                name = pattern.sub(replacement, name)
            name = name.strip(string.punctuation + string.whitespace + string.digits + '–—\xa0')
            uppers = len(UPPER_REGEXP.findall(name))
            if uppers > len(name) / 2:
                name = name.lower()
                name = name.capitalize()
            return name

        for t in ['lunches', 'soups']:
            num = 0
            for food in restaurant.get(t, []):
                food.price = fix_price(food.price)
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
                response = client.get(parser.parser['url'])
                if 'res' in arg_names:
                    args['res'] = response.text
                else:
                    args['dom'] = HTMLParser(response.text)

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
    for restaurant in sorted(restaurants, key=lambda r: ('error' in r, len(r.get('lunches', [])) == 0)):
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
