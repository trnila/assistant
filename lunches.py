from bs4 import BeautifulSoup
import aiohttp
import re
import json
import datetime
import asyncio
import itertools


days = ['Pondělí', 'Úterý', 'Středa', 'Čtvrtek', 'Pátek', 'Sobota', 'Neděle']


async def gather_restaurants():
    async with aiohttp.ClientSession() as session:
        async def bistroin():
            async with session.get("https://onemenu.cz/menu/Bistro-In") as r:
                text = await r.text()
                dom = BeautifulSoup(text, 'html.parser')
                foods = []
                soup = None
                soup_price = None
                for node in dom.select('.orderitem-right'):
                    ingredients = node.select('.ingredients')[0].get_text()
                    ingredients = re.sub('Al\. \(.+', '', ingredients)
                    name = node.select('.name')[0].get_text()
                    price = node.select('.priceValue')[0].get_text().split()[0]
                    if 'Polévka' in name:
                        soup = name.split(':')[1]
                        soup_price = price
                    else:
                        parts = name.split('.', 1)
                        if len(parts) == 2:
                            foods.append({
                                'num': parts[0],
                                'name': parts[1],
                                'ingredients': ingredients,
                                'price': price,
                            })
                return {
                    'name': 'Bistro IN',
                    'soup': soup,
                    'soup_price': soup_price,
                    'lunches': foods,
                }

        async def u_jarosu():
            async with session.get("https://www.ujarosu.cz/cz/denni-menu/") as r:
                result = {
                    'name': 'U Jarošů',
                    'soup': None,
                    'lunches': [],
                }

                text = await r.text()
                dom = BeautifulSoup(text, 'html.parser')

                day_nth = datetime.datetime.today().weekday()
                day_nth = 3

                counter = 0
                food = {}
                foods = []
                capturing = False
                for row in dom.findAll('tr'):
                    day = row.select('td')[0].get_text().strip(' \n\t\xa0:')
                    if day in days:
                        if capturing:
                            break
                        if day == days[day_nth]:
                            capturing = True
                            result['soup'] = row.select('td')[1].get_text()
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
                                foods.append(food)
                            food = {
                                'name': row.select('td')[1].get_text(),
                                'price': row.select('td')[2].get_text(),
                                'num': str(num),
                            }
                        else:
                            food['name'] += ' ' + row.select('td')[1].get_text()


                if food:
                    foods.append(food)

                result['lunches'] = foods
                return result

        async def u_zlateho_lva():
            day_nth = datetime.datetime.today().weekday()
            async with session.get("http://www.zlatylev.com/menu_zlaty_lev.html") as r:
                text = await r.text()
                dom = BeautifulSoup(text, 'html.parser')
                foods = []
                text = dom.select('.xr_txt.xr_s0')[0].get_text()

                def remove_alergens(s):
                    return re.sub('\(A-\d.+', '', s)

                capturing = False
                counter = 0
                food = {}
                soup = None
                state = 'num'
                for line in text.splitlines():
                    line = line.strip()

                    if line.startswith(days[day_nth]):
                        capturing = True
                    elif capturing:
                        if day_nth < 4 and line.startswith(days[day_nth + 1]):
                            break
                        print(line, state)
                        if line.startswith('Polévka:'):
                            soup = remove_alergens(line.split(':')[1])
                        else:
                            if state == 'num':
                                if re.match('^[0-9]+\.$', line):
                                    food = {
                                        'num': line.split('.')[0],
                                    }
                                    state = 'name'
                            elif state == 'name':
                                if line:
                                    food['name'] = remove_alergens(line)
                                    state = 'price'
                            elif state == 'price':
                                if re.match('^[0-9]+ Kč$', line):
                                    food['price'] = line.split(' ')[0]
                                    foods.append(food)
                                    state = 'num'

                return {
                    'name': 'U Zlatého Lva',
                    'soup': soup,
                    'lunches': foods,
                }

        restaurants = [
            bistroin,
            u_jarosu,
            u_zlateho_lva
        ]

        foods = await asyncio.gather(*[f() for f in restaurants])
        names = [r.__name__ for r in restaurants]

        def cleanup_foods(foods):
            def fix_name(name):
                uppers = sum(1 for c in name if c.isupper())
                if uppers > len(name) / 2:
                    name = name.lower()
                    name = name.capitalize()
                return name

            for food in foods['lunches']:
                for k, v in food.items():
                    food[k] = v.strip()
                    if k == 'price':
                        try:
                            food[k] = int(food[k])
                        except ValueError:
                            pass
                food['name'] = fix_name(food['name'])
            if foods['soup']:
                foods['soup'] = fix_name(foods['soup'])
            return foods


        return map(cleanup_foods, foods)
