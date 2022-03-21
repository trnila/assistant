from bs4 import BeautifulSoup
import aiohttp
import re
import json
import datetime
import asyncio
import itertools
import traceback
from dataclasses import dataclass

@dataclass
class Restaurant:
    name: str
    parser: int

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

async def gather_restaurants():
    async with aiohttp.ClientSession() as session:
        async def bistroin():
            async with session.get("https://onemenu.cz/menu/Bistro-In") as r:
                dom = BeautifulSoup(await r.text(), 'html.parser')
                for node in dom.select('.orderitem-right'):
                    ingredients = node.select('.ingredients')[0].get_text()
                    ingredients = re.sub('Al\. \(.+', '', ingredients)
                    name = node.select('.name')[0].get_text()
                    price = node.select('.priceValue')[0].get_text().split()[0]
                    if 'Polévka' in name:
                        yield Soup(name=name.split(':')[1], price=price)
                    else:
                        parts = name.split('.', 1)
                        if len(parts) == 2:
                            yield Lunch(num=parts[0], name=parts[1], price=price, ingredients=ingredients)

        async def u_jarosu():
            async with session.get("https://www.ujarosu.cz/cz/denni-menu/") as r:
                dom = BeautifulSoup(await r.text(), 'html.parser')

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
                                price=row.select('td')[2].get_text(),
                                num=num,
                            )
                        else:
                            food.name += ' ' + row.select('td')[1].get_text()

                if food:
                    yield food

        async def u_zlateho_lva():
            day_nth = datetime.datetime.today().weekday()
            async with session.get("http://www.zlatylev.com/menu_zlaty_lev.html") as r:
                dom = BeautifulSoup(await r.text(), 'html.parser')
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

        async def globus():
            async with session.get("https://www.globus.cz/ostrava/nabidka/restaurace.html") as r:
                dom = BeautifulSoup(await r.text(), 'html.parser')
                for row in dom.select('.restaurant__menu-food-table')[0].select('tr'):
                    tds = row.select('td')
                    name = tds[1].text
                    price = tds[2].text.replace(',–', '')
                    yield (Lunch if int(price) > 50 else Soup)(name=name, price=price)

        async def jacks_burger():
            async with session.get("https://www.menicka.cz/1534-jacks-burger-bar.html") as r:
                day_nth = datetime.datetime.today().weekday()

                dom = BeautifulSoup(await r.text(), 'html.parser')
                for day_menu in dom.select('.menicka'):
                    day = day_menu.select('.nadpis')[0].text.split(' ')[0]
                    if day != days[day_nth]:
                        continue
                    yield Soup(name=day_menu.select('.polevka div')[0].text)

                    for food_li in day_menu.select('li.jidlo'):
                        txt = food_li.select('.polozka')[0].text
                        num, name = txt.split('.', 1)
                        price = food_li.select('.cena')[0].text.replace('Kč', '')
                        yield Lunch(num=num, name=name, price=price)

        restaurants = [
            Restaurant("Bistro IN", bistroin),
            Restaurant("U jarosu", u_jarosu),
            Restaurant("U zlateho lva", u_zlateho_lva),
            Restaurant("Globus", globus),
            Restaurant("Jacks Burger", jacks_burger),
        ]


        async def collect(restaurant):
            try:
                lunches = []
                soups = []
                async for item in restaurant.parser():
                    if isinstance(item, Soup):
                        soups.append(item)
                    elif isinstance(item, Lunch):
                        lunches.append(item)
                    else:
                        raise "Unsupported item"
                return {
                    'name': restaurant.name,
                    'lunches': lunches,
                    'soups': soups,
                }
            except:
                return {"error": traceback.format_exc()}

        foods = await asyncio.gather(*[collect(r) for r in restaurants])

        def cleanup(restaurant):
            def fix_name(name):
                uppers = sum(1 for c in name if c.isupper())
                if uppers > len(name) / 2:
                    name = name.lower()
                    name = name.capitalize()
                name = re.sub('\d+\s*(g|ml|ks) ', '', name)
                name = re.sub('\([^)]+\)', '', name)
                return name.strip(' \n\r\t-/')

            for t in ['lunches', 'soups']:
                for food in restaurant.get(t, []):
                    if food.price:
                        food.price = int(food.price.replace(',-', ''))
                    food.name = fix_name(food.name)
            return restaurant

        return map(cleanup, foods)
