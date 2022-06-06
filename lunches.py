from bs4 import BeautifulSoup
import subprocess
import aiohttp
import re
import json
import datetime
import asyncio
import itertools
import traceback
import tempfile
from dataclasses import dataclass

@dataclass
class Restaurant:
    name: str
    parser: int
    url: str

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


days = ['Pondělí', 'Úterý', 'Středa', 'Čtvrtek', 'Pátek', 'Sobota', 'Neděle']

async def gather_restaurants(allowed_restaurants=None):
    async with aiohttp.ClientSession() as session:
        async def bistroin(res):
            dom = BeautifulSoup(res, 'html.parser')
            for node in dom.select('.orderitem-right'):
                ingredients = node.select('.ingredients')[0].get_text()
                ingredients = re.sub('Al\. \(.+', '', ingredients)
                name = node.select('.name')[0].get_text()
                price = int(node.select('.priceValue')[0].get_text().split()[0])
                if 'Polévka k menu:' in name:
                    yield Soup(name=name.split(':')[1], price=price)
                else:
                    parts = name.split('.', 1)
                    if len(parts) == 2:
                        yield Lunch(num=parts[0], name=parts[1], price=price - 5, ingredients=ingredients)

        async def u_jarosu(res):
            dom = BeautifulSoup(res, 'html.parser')

            day_nth = datetime.datetime.today().weekday()

            counter = 0
            food = {}
            capturing = False
            for row in dom.findAll('tr'):
                day = row.select('td')[0].get_text().strip(' \n\t\xa0:')
                if day in days:
                    if capturing:
                        break
                    if day == days[day_nth]:
                        capturing = True
                        yield Soup(name=row.select('td')[1].get_text())
                elif capturing:
                    spaces = all(not td.get_text().strip() for td in row.select('td'))
                    if spaces:
                        break

                    try:
                        num = int(row.select('td')[0].get_text().strip().split('.')[0])
                    except ValueError:
                        num = -1
                    if num == counter + 1:
                        counter += 1
                        if food:
                            yield food
                        food = Lunch(
                            name=row.select('td')[1].get_text(),
                            price=row.select('td')[2].get_text() if len(row.select('td')) >= 3 else None,
                            num=num,
                        )
                    else:
                        food.name += ' ' + row.select('td')[1].get_text()

            if food:
                yield food

        async def u_zlateho_lva(res):
            day_nth = datetime.datetime.today().weekday()
            dom = BeautifulSoup(res, 'html.parser')
            text = dom.select('.xr_txt.xr_s0')[0].get_text()

            capturing = False
            counter = 0
            state = 'name'
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
                        if state == 'name':
                            if re.match('^[0-9]+\.', line):
                                line, name = line.split('.', 1)
                                food = Lunch(name=name, num=line)
                                state = 'price'
                        elif state == 'price':
                            if re.match('^[0-9]+\s*(,-|Kč)$', line):
                                food.price = line.split(' ')[0]
                                yield food
                                state = 'name'

        async def globus(res):
            dom = BeautifulSoup(res, 'html.parser')
            for row in dom.select('.restaurant__menu-food-table')[0].select('tr'):
                tds = row.select('td')
                name = tds[1].text
                price = tds[2].text.replace(',–', '') if len(tds) >= 3 else None
                yield (Lunch if price and int(price) > 50 else Soup)(name=name, price=price)

        async def jacks_burger(res):
            day_nth = datetime.datetime.today().weekday()
            dom = BeautifulSoup(res, 'html.parser')
            for day_menu in dom.select('.menicka'):
                day = day_menu.select('.nadpis')[0].text.split(' ')[0]
                if day != days[day_nth]:
                    continue

                soup_el = day_menu.select('.polevka div')
                if soup_el:
                    yield Soup(name=soup_el[0].text)

                for food_li in day_menu.select('li.jidlo'):
                    txt = food_li.select('.polozka')[0].text
                    num, name = txt.split('.', 1)

                    price_tag = food_li.select('.cena')
                    price = price_tag[0].text if price_tag else None
                    yield Lunch(num=num, name=name, price=price)

        async def poklad(res):
            images = [r.strip().split(' ') for r in re.search('srcset="([^"]+)"', res).group(1).split(',')]
            img = sorted(images, key=lambda r: int(r[1].replace('w', '')))[-1][0]
            async with session.get(img) as r:
                with tempfile.NamedTemporaryFile() as tmp:
                    tmp.write(await r.read())
                    tmp.flush()
                    proc = await asyncio.create_subprocess_exec('tesseract', '--psm', '6', '-l', 'ces', tmp.name, '-', stdout=asyncio.subprocess.PIPE)
                    txt = (await proc.communicate())[0].decode('utf-8')

                in_common = True
                in_day = False
                in_day_soup = False
                for line in txt.splitlines():
                    m = re.match('([0-9]{1,2})\s*\.*\s*([0-9]{1,2})\s*\.*\s*([0-9]{4})', line)
                    if m:
                        c = [int(i) for i in m.groups()]
                        day = datetime.date(day=c[0], month=c[1], year=c[2]).weekday()
                        day_nth = datetime.datetime.today().weekday()
                        in_day = day == day_nth
                        in_day_soup = in_day
                        in_common = False
                    elif re.match('^[0-9]+', line):
                        if in_common or in_day:
                            price = re.search('([0-9]{3}) kč', line.lower())
                            m = re.search('^(?P<num>[0-9]+)\s*\.?\s*[0-9]+\s*(g|ks|)\s*[\|—]?\s*(?P<name>.+).*?(?P<price>[12][0-9]{2})', line)
                            values = m.groupdict() if m else {'name': line}
                            if len(values['name']) > 8:
                                yield Lunch(**values)
                    elif in_day_soup:
                        in_day_soup = False
                        for soup in line.split('/'):
                            yield Soup(name=soup)


        restaurants = [
            Restaurant("Bistro IN", bistroin, "https://onemenu.cz/menu/Bistro-In"),
            Restaurant("U jarosu", u_jarosu, "https://www.ujarosu.cz/cz/denni-menu/"),
            Restaurant("U zlateho lva", u_zlateho_lva, "http://www.zlatylev.com/menu_zlaty_lev.html"),
            Restaurant("Jacks Burger", jacks_burger, "https://www.menicka.cz/1534-jacks-burger-bar.html"),
            Restaurant("Poklad", poklad, "https://dkpoklad.cz/restaurace/poledni-menu-4-8-6-8/"),
            Restaurant("Globus", globus, "https://www.globus.cz/ostrava/nabidka/restaurace.html"),
        ]


        async def collect(restaurant):
            res = {
                'name': restaurant.name,
                'url': restaurant.url,
            }
            try:
                lunches = []
                soups = []
                async with session.get(restaurant.url) as r:
                    async for item in restaurant.parser(await r.text()):
                        if isinstance(item, Soup):
                            soups.append(item)
                        elif isinstance(item, Lunch):
                            lunches.append(item)
                        else:
                            raise "Unsupported item"
                    return {
                        **res,
                        'lunches': lunches,
                        'soups': soups,
                    }
            except:
                return {
                    **res,
                    'error': traceback.format_exc()
                }

        if not allowed_restaurants:
            allowed_restaurants = [r.parser.__name__ for r in restaurants]
        foods = await asyncio.gather(*[collect(r) for r in restaurants if r.parser.__name__ in allowed_restaurants])

        def cleanup(restaurant):
            def fix_name(name):
                uppers = sum(1 for c in name if c.isupper())
                if uppers > len(name) / 2:
                    name = name.lower()
                    name = name.capitalize()
                name = re.sub('\d+\s*(g|ml|ks) ', '', name)
                name = re.sub('\([^)]+\)', '', name)
                name = re.sub('A?[0-9]+(,[0-9]+){1,},?', '', name)
                return name.strip(' \n\r\t-/©*01234567890—.|"')

            for t in ['lunches', 'soups']:
                for food in restaurant.get(t, []):
                    if food.price and isinstance(food.price, str):
                        food.price = int(food.price.replace(',-', '').replace('Kč', ''))
                    food.name = fix_name(food.name)
            return restaurant

        return map(cleanup, foods)

if __name__ == '__main__':
    from pprint import pprint
    import sys

    allowed_restaurants = None
    if len(sys.argv) > 1:
        allowed_restaurants = sys.argv[1].split(',')
    res = asyncio.new_event_loop().run_until_complete(gather_restaurants(allowed_restaurants))
    pprint(list(res), width=180)
