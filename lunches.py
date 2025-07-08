#!/usr/bin/env python3
import asyncio
import datetime
import inspect
import json
import logging
import re
import string
import time
import traceback
from dataclasses import dataclass
from enum import Enum
from html import unescape

import httpx
from selectolax.parser import HTMLParser, Selector

days = ["Pondělí", "Úterý", "Středa", "Čtvrtek", "Pátek", "Sobota", "Neděle"]
USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/105.0.0.0 Safari/537.36"


class Location(str, Enum):
    Poruba = ("Poruba",)
    Dubina = ("Dubina",)
    Zabreh = ("Zábřeh",)
    Centrum = ("Centrum",)
    Olomouc = ("Olomouc",)


def restaurant(title, url=None, location: Location = None):
    def wrapper(fn):
        def wrap(*args, **kwargs):
            return fn(*args, **kwargs)

        wrap.parser = {
            "name": fn.__name__,
            "title": title,
            "url": url,
            "location": location,
            "args": fn.__code__.co_varnames[: fn.__code__.co_argcount],
        }
        return wrap

    return wrapper


@dataclass
class Soup:
    name: str
    price: int = None
    photo: str = None


@dataclass
class Lunch:
    name: str
    num: int = None
    price: int = None
    ingredients: str = None
    photo: str = None


def menicka_parser(dom):
    current_day = datetime.datetime.now().strftime("%-d.%-m.%Y")
    for day_dom in dom.css(".content"):
        day = day_dom.css_first("h2").text(strip=True).split(" ", 2)[1]
        if current_day not in day:
            continue

        soup_el = day_dom.css_first(".soup .food")
        if soup_el:
            soup_name = soup_el.text()
            if "Pro tento den nebylo zadáno menu" in soup_name:
                break
            yield Soup(soup_name, day_dom.css_first(".soup .prize").text())

        for food in day_dom.css(".main"):
            match = re.search(r"\((?P<ingredients>.*)\)", food.css_first(".food").text())
            ingredients = match.group("ingredients") if match and len(match.group("ingredients")) > 6 else None

            yield Lunch(
                num=food.css_first(".no").text().strip(" ."),
                name=food.css_first(".food").text(),
                price=food.css_first(".prize").text(),
                ingredients=ingredients,
            )


async def subprocess_check_output(cmd, input):
    p = await asyncio.create_subprocess_exec(*cmd, stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE)
    return (await p.communicate(input))[0].decode("utf-8")


@restaurant("Bistro IN", "https://bistroin.choiceqr.com/delivery", Location.Poruba)
def bistroin(dom):
    elem = dom.css_first("#__NEXT_DATA__")
    if not elem:
        return
    data = json.loads(elem.text())

    for item in data["props"]["app"]["menu"]:
        ingredients = re.sub(r"Al\. \(.+", "", item["description"])
        price = item["price"] // 100
        if "Polévka k menu:" in item["name"]:
            yield Soup(name=item["name"].split(":")[1], price=price)
        else:
            match = re.match(r"^\s*(?P<num>[0-9]+)\s*\.\s*(?P<name>.+)", item["name"])
            if match:
                yield Lunch(**match.groupdict(), price=price - 10, ingredients=ingredients)


@restaurant("U jarosu", "https://www.ujarosu.cz/cz/denni-menu/", Location.Poruba)
def u_jarosu(dom):
    today = datetime.datetime.strftime(datetime.datetime.now(), "%d. %m. %Y")
    for row in dom.css(".celyden"):
        parsed_day = row.css_first(".datum").text()
        if parsed_day == today:
            records = row.css(".tabulka p")
            records = [r.text().strip() for r in records]
            records = [records[i : i + 3] for i in range(0, len(records), 3)]
            for first, name, price in records:
                if first == "Polévka":
                    yield Soup(name)
                else:
                    yield Lunch(name, price=price, num=first.split(".")[0])


@restaurant("U zlateho lva", "http://www.zlatylev.com/menu_zlaty_lev.html", Location.Poruba)
def u_zlateho_lva(dom):
    day_nth = datetime.datetime.today().weekday()
    text = dom.css_first(".xr_txt.xr_s0").text()

    capturing = False
    state = "num"
    for line in text.splitlines():
        line = line.strip()

        if line.startswith(days[day_nth]):
            capturing = True
        elif capturing:
            if day_nth < 4 and line.startswith(days[day_nth + 1]):
                break
            soup_prefix = "Polévka:"
            if line.startswith(soup_prefix):
                yield Soup(line.replace(soup_prefix, ""))
            else:
                if state == "num":
                    if re.match(r"^[0-9]+\.", line):
                        line, name = line.split(".", 1)
                        food = Lunch(name=name, num=line)
                        state = "price" if name else "name"
                elif state == "name":
                    if line:
                        food.name = line
                        state = "price"
                elif state == "price":  # noqa: SIM102
                    if re.match(r"^[0-9]+\s*(,-|Kč)$", line):
                        food.price = line.split(" ")[0]
                        yield food
                        state = "num"


@restaurant("Globus", "https://www.globus.cz/ostrava/sluzby-a-produkty/restaurace", Location.Poruba)
def globus(dom):
    for row in dom.css(".space-y-2 .flex"):
        spans = row.css("* > span")
        price = fix_price(spans[2].text())
        t = Soup if price < 50 else Lunch
        yield t(spans[1].text(), price=price)


@restaurant("Jacks Burger", "https://www.jacksburgerbar.cz/", Location.Poruba)
def jacks_burger(dom):
    for row in dom.css("#dennimenu table:first-of-type tr"):
        category, name, price = (td.text() for td in row.css("td"))
        if category.lower() == "polévka":
            yield Soup(name)
        elif category.isdigit():
            yield Lunch(name, num=category, price=price)


@restaurant("Poklad", "https://dkpoklad.cz/restaurace/", Location.Poruba)
async def poklad(dom, http):
    pdf_url = dom.css_first(".restaurace-box .wp-block-file a").attributes["href"]
    pdf = (await http.get(pdf_url)).content
    text = await subprocess_check_output(["pdftotext", "-layout", "-", "-"], pdf)

    today = datetime.datetime.strftime(datetime.datetime.now(), "%-d I %-m")
    tomorrow = datetime.datetime.strftime(datetime.datetime.now() + datetime.timedelta(days=1), "%-d I %-m")
    capturing = False
    soup = True
    item = None
    for line in text.splitlines():
        if today in line:
            capturing = True
        elif capturing:
            if tomorrow in line or "NABÍDKA NÁPOJŮ" in line:
                break
            if soup:
                soup = False
                for s in line.split(" I "):
                    yield Soup(s)
            else:
                m = re.match(r"^\s*(?P<num>([0-9]+|BUSINESS))\s*\.?\s*(?P<name>.*?) (?P<price>[0-9]+) Kč", line)
                if m:
                    if item:
                        yield Lunch(**item)
                    item = m.groupdict()
                elif item:
                    if not line:
                        yield Lunch(**item)
                        item = None
                    else:
                        item["name"] += line

    if item:
        yield Lunch(**item)


@restaurant("Trebovicky mlyn", "https://www.trebovickymlyn.cz/denni-menu/", Location.Poruba)
def trebovicky_mlyn(dom):
    el = dom.css_first(".soup h2")
    if not el:
        return
    yield Soup(el.text())

    for lunch in dom.css_first(".owl-carousel").css(".menu-post"):
        parts = lunch.css_first("h2").text().split(")")
        if len(parts) == 2:
            yield Lunch(
                num=parts[0],
                name=parts[1],
                ingredients=lunch.css_first("h2 + div").text(),
                price=lunch.css_first("span").text().split(",")[0],
            )


@restaurant("Trebovicka role", "https://trebovickarole.cz/denni-menu/", Location.Poruba)
def trebovicka_role(dom):
    MENU_REGEXP = re.compile(r"Menu (?P<num>[0-9])\s*:\s*(?P<name>.+)")

    day_nth = datetime.datetime.today().weekday()
    for h4 in dom.css("h4"):
        if days[day_nth] in h4.text():
            table = h4.next
            while table.tag != "table":
                table = table.next
            for row in table.css("tr"):
                name = row.css("td")[0].text(strip=True)
                price = row.css("td")[1].text(strip=True)

                if "Polévka" in name:
                    yield Soup(name.split(":")[1])
                elif name.strip():
                    m = re.match(MENU_REGEXP, name)
                    yield Lunch(price=price, **m.groupdict())


@restaurant("La Strada", "https://www.lastrada.cz/cz/?tpl=plugins/DailyMenu/print&week_shift=", Location.Poruba)
def lastrada(dom):
    day_nth = datetime.datetime.today().weekday()

    capturing = False
    for tr in dom.css("tr"):
        if tr.css_matches(".day"):
            capturing = False
            if days[day_nth] in tr.text() or "Menu na celý týden" in tr.text():
                capturing = True
        elif capturing:
            if tr.css_matches(".highlight"):
                yield Lunch(name=tr.css_first("td").text(), price=tr.css_first(".price").text())


@restaurant("Ellas", "https://www.restauraceellas.cz/", Location.Poruba)
def ellas(dom):
    day_nth = datetime.datetime.today().weekday()
    lunch_pattern = re.compile(r"(?P<name>.*?)\s*(\(([^)]+)\))?\s*–\s*(?P<price>[0-9]+),-")

    for div in dom.css(".moduletable .custom"):
        if div.css_first("h3").text(strip=True) != days[day_nth]:
            continue

        yield Soup(name=div.css_first("p").text())

        for ol in div.css("ol"):
            num = ol.attrs.get("start", 1)
            parsed = re.match(lunch_pattern, ol.text(strip=True))
            yield Lunch(num=num, **parsed.groupdict())


@restaurant("Saloon Pub", "http://www.saloon-pub.cz/cs/denni-nabidka/", Location.Poruba)
def saloon_pub(dom):
    day = dom.css_first(f"#{datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d')} + section")
    if not day:
        return
    yield Soup(name=day.css_first(".category-info").text())
    for tr in day.css(".main-meal-info"):
        yield Lunch(name=tr.css_first(".meal-name").text(), price=tr.css_first(".meal-price").text())


@restaurant("Parlament", "https://www.restauraceparlament.cz/", Location.Poruba)  # codespell:ignore
def parlament(dom):  # codespell:ignore
    day_nth = datetime.datetime.today().weekday()
    day = Selector(dom.css_first(".txt"), "div div").text_contains(days[day_nth])
    if day:
        day = day.matches[0]
        yield Soup(day.css_first("* + dt").text())
        for line in day.css_first("* + dt + p").text().splitlines():
            m = re.match(r"(?P<num>\d+)\.\s*(?P<name>.*?)(?P<price>\d+),-Kč", line)
            if m:
                yield Lunch(**m.groupdict())


@restaurant("Plzenka aura", "https://www.plzenkaaura.cz/denni-menu", Location.Poruba)
def plzenka(dom):
    food_type = None
    for el in dom.css(".list-items > *"):
        if el.tag == "h5":
            food_type = {
                "POLÉVKA": Soup,
                "HLAVNÍ JÍDLO": Lunch,
            }.get(el.text(strip=True), None)
        elif food_type:
            if food_type == Soup:
                yield Soup(el.css_first(".modify_item").text())
            else:
                yield Lunch(
                    name=el.css_first(".modify_item").text(),
                    ingredients=el.css_first(".food-info").text(),
                    price=el.css_first(".menu-price").text(),
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
        food.num = None
        yield food


@restaurant("Viktorka", "https://www.viktorkaostrava.cz/denni-menu/", Location.Poruba)
def viktorka(dom):
    soups, lunches = dom.css(".elementor-widget-price-list")
    day_nth = datetime.datetime.today().weekday()

    for item in soups.css(".elementor-price-list-title"):
        name = item.text(strip=True)
        if days[day_nth] in name:
            yield Soup(name.split("-", 2)[1])

    ignore_day_stems = [day[:-1].lower() for idx, day in enumerate(days) if idx != day_nth]
    for item in lunches.css(".elementor-price-list-item"):
        name = item.css_first(".elementor-price-list-title").text(strip=True)
        price = item.css_first(".elementor-price-list-price").text(strip=True)
        if not any(stem in name.lower() for stem in ignore_day_stems):
            yield Lunch(name, price=price)


@restaurant("Futrovna", "https://www.menicka.cz/api/iframe/?id=7200", Location.Poruba)
def futrovna(dom):
    yield from menicka_parser(dom)


@restaurant("Kurnik sopa", "https://www.kurniksopahospoda.cz", Location.Poruba)
def kurniksopa(dom):
    for pivo in dom.css("#naCepu-list tr"):
        name = pivo.css_first(".nazev").text()
        deg = pivo.css_first(".stupne").text()
        type = pivo.css_first(".typ").text()
        origin = pivo.css_first(".puvod").text()
        yield Lunch(
            name=f"{name} {deg} - {type}, {origin}",
        )


@restaurant("Sbeerka", "https://sbeerka.cz/tydenni-menu", Location.Poruba)
async def sbeerka(dom, http):
    REGEXP = re.compile(r"(?P<name>.*?)\s*(/[0-9,\s*]+/)?\s*(?P<price>[0-9]+\s*,-)")
    elem = dom.css_first(".wysiwyg")
    if not elem:
        return

    t = None
    for line in elem.text().splitlines():
        line = line.strip()
        if "Polévk" in line:
            t = Soup
        elif "Hlavní chody" in line:
            t = Lunch
        elif t and "Záloha" not in line:
            m = REGEXP.search(line)
            if m:
                yield t(**m.groupdict())

    PRICE_REGEXP = re.compile(r"([0-9]+)\s*,-")
    response = await http.get("https://sbeerka.cz/aktualne-na-cepu", headers={"User-Agent": USER_AGENT})
    dom = HTMLParser(response.text)
    for beer in dom.css(".wysiwyg li"):
        price = None
        m = PRICE_REGEXP.search(beer.text())
        if m:
            price = m.group(0)
        yield Lunch(name=beer.text(), price=price)


@restaurant("Menza", "https://stravovani.vsb.cz/webkredit", Location.Poruba)
async def menza(http):
    date = datetime.datetime.now().replace(hour=22, minute=0, second=0, microsecond=0)
    fdate = date.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]

    res = await http.get(f"https://stravovani.vsb.cz/webkredit/Api/Ordering/Menu?Dates={fdate}Z&CanteenId=1")
    g = json.loads(res.text)["groups"]
    if not g:
        return

    soup = g[0]["rows"][0]["item"]
    yield Soup(soup["mealName"], soup["price"])

    for lunch in g[1]["rows"]:
        lunch = lunch["item"]
        if lunch["price"] != 0:
            photo = None
            if lunch["imageId"]:
                photo = f"https://stravovani.vsb.cz/webkredit/Api/Ordering/Image?id={lunch['imageId']}"
            yield Lunch(lunch["mealName"], price=lunch["price"], photo=photo)


@restaurant("La Futura", "https://lafuturaostrava.cz/", Location.Dubina)
def lafutura(dom):
    container = dom.css_first(".jet-listing-dynamic-repeater__items")
    if not container:
        return
    for item in container.css(".jet-listing-dynamic-repeater__item"):
        tds = item.css("td")
        if "POLÉVKA" in tds[0].text(strip=True).upper():
            yield Soup(name=tds[1].text())
        else:
            yield Lunch(name=tds[1].text(), price=tds[2].text())


@restaurant("Srub", "https://www.menicka.cz/api/iframe/?id=5568", Location.Dubina)
def srub(dom):
    yield from menicka_parser(dom)


@restaurant("U formana", "https://www.menicka.cz/api/iframe/?id=4405", Location.Dubina)
def uformana(dom):
    yield from menicka_parser(dom)


@restaurant("Maston", "https://maston.cz/jidelni-listek/", Location.Dubina)
async def maston(dom, http):
    srcs = dom.css_first(".attachment-large").attrs["srcset"]
    img_url = srcs.split(",")[-1].strip().split(" ")[0]

    img = (await http.get(img_url)).content
    text = await subprocess_check_output(["tesseract", "-l", "ces", "--psm", "4", "-", "-"], img)

    today = datetime.datetime.strftime(datetime.datetime.now(), "%-d%-m")
    tomorrow = datetime.datetime.strftime(datetime.datetime.now() + datetime.timedelta(days=1), "%-d%-m")
    capturing = False
    for line in text.splitlines():
        txt = line.replace(" ", "").replace(".", "")
        if txt.endswith(today):
            capturing = True
        elif capturing:
            if "SAMOSTATN" in txt.upper() or tomorrow in txt:
                break
            if "POLÉVKA" in line:
                yield Soup(line.split(":", 1)[1])
            else:
                m = re.search(r"((?P<num>\d)\))?\s*(?P<name>.+)(\s*(?P<price>\d+),-)?", line)
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
    yield from menicka_parser(dom)


@restaurant("U Kristýna", "https://www.menicka.cz/api/iframe/?id=5471", Location.Olomouc)
def kristyn(dom):
    yield from menicka_parser(dom)


@restaurant("Assen", "https://www.menicka.cz/api/iframe/?id=8767", Location.Zabreh)
def assen(dom):
    yield from menicka_parser(dom)


@restaurant("Bistro Paulus", "https://www.bistro-paulus.cz/poledni-menu/", Location.Olomouc)
def paulus(dom):
    current_day = datetime.datetime.now().strftime("%-d.%-m.%Y")
    for day_dom in dom.css(".section-day"):
        day = "".join(day_dom.css_first("h3").text(strip=True).split()[1:])
        if current_day not in day:
            continue

        soup_table = day_dom.css("table")[0].css("span")
        for soup, price in zip(soup_table[::2], soup_table[1::2]):
            yield Soup(soup.text(strip=True), price.text(strip=True))

        lunch_table = day_dom.css("table")[1].css("span") + day_dom.css("table")[2].css("span")
        for lunch, price in zip(lunch_table[::2], lunch_table[1::2]):
            yield Lunch(lunch.text(strip=True), price=price.text(strip=True))


@restaurant("Slezska P.U.O.R", "https://www.menicka.cz/api/iframe/?id=1406", Location.Centrum)
def puor(dom):
    yield from menicka_parser(dom)


@restaurant("Frankie's Pub", "https://www.menicka.cz/api/iframe/?id=7080", Location.Centrum)
def frankies_pub(dom):
    yield from menicka_parser(dom)


@restaurant("Ostrawica Lokál", "https://www.menicka.cz/api/iframe/?id=8648", Location.Centrum)
def ostravica_lokal(dom):
    yield from menicka_parser(dom)


@restaurant("Kanteen", "https://www.menicka.cz/api/iframe/?id=8684", Location.Centrum)
def kanteen(dom):
    yield from menicka_parser(dom)


@restaurant("Pizza Coloseum Karolina", "https://www.menicka.cz/api/iframe/?id=517", Location.Centrum)
def coloseum(dom):
    yield from menicka_parser(dom)


@restaurant("IQ Restaurant", "https://www.menicka.cz/api/iframe/?id=1401", Location.Centrum)
def iq(dom):
    yield from menicka_parser(dom)


@restaurant("2 Promile", "https://www.menicka.cz/api/iframe/?id=3486", Location.Centrum)
def two_promile(dom):
    yield from menicka_parser(dom)


def fix_price(price):
    if not price:
        return None
    if not isinstance(price, str):
        return int(price)
    try:
        sanitized = re.sub("kč", "", price, flags=re.IGNORECASE)
        sanitized = sanitized.replace(".00", "").strip(string.punctuation + string.whitespace)
        return int(sanitized)
    except ValueError as e:
        print(e)
    return None


async def gather_restaurants(allowed_restaurants=None):
    replacements = [
        (re.compile(r"^\s*(Polévka|BUSINESS MENU|business|SALÁT TÝDNE|tip týdne)", re.IGNORECASE), ""),
        (re.compile(r"k menu\s*$"), ""),
        (re.compile(r"(s|š|S|Š)vestk"), "Trnk"),
        # ugly space before comma or colon
        (re.compile(r"\s*(,|:)\s*"), "\\1 "),
        # HTML tags
        (re.compile(r"<[^<]+?>"), ""),
        # grammage
        (re.compile(r"\d+\s*(g|ml|l|ks)( |,)"), ""),
        # remove leftover alergen 'A:1,2,3'
        (re.compile(r"A:\s*\d(\s*,\s*\d+,)*"), ""),
        # alergens pattern 'Al ('
        (re.compile(r"\s*A?l?\.?\s*\("), "("),
        # alergens as a numbers: 1, 2, 3
        (re.compile(r"[0-9]+(\s*,\s*[0-9]+)+"), ""),
        # brackets
        (re.compile(r"\([^)]+\)"), ""),
        # multiple white-spaces
        (re.compile(r"\s+"), " "),
    ]
    UPPER_REGEXP = re.compile(r"[A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ]")

    def detect_encoding(text):
        if b"windows-1250" in text:
            return "windows-1250"
        return "utf-8"

    client = httpx.AsyncClient(default_encoding=detect_encoding, headers={"User-Agent": USER_AGENT}, timeout=15)

    def cleanup(restaurant):
        def fix_name(name):
            name = unescape(name)
            for pattern, replacement in replacements:
                name = pattern.sub(replacement, name)
            name = name.strip(string.punctuation + string.whitespace + string.digits + "–—\xa0")
            uppers = len(UPPER_REGEXP.findall(name))
            if uppers > len(name) / 2:
                name = name.lower()
                name = name.capitalize()
            return name

        for t in ["lunches", "soups"]:
            num = 0
            for food in restaurant.get(t, []):
                food.price = fix_price(food.price)
                food.name = fix_name(food.name)
                if t == "lunches":
                    if food.ingredients:
                        food.ingredients = fix_name(food.ingredients)

                    if isinstance(food.num, str):
                        try:
                            food.num = int(food.num.replace(".", ""))
                        except ValueError:
                            logging.warning("Failed to parse lunch position: %s", food.num)
                            food.num = None
                    if not food.num:
                        food.num = num + 1
                    num = food.num
        return restaurant

    async def collect(parser):
        start = time.time()
        res = {
            "name": parser.parser["title"],
            "url": parser.parser["url"],
            "location": parser.parser["location"],
        }
        try:
            lunches = []
            soups = []

            args = {}
            arg_names = parser.parser["args"]
            if "res" in arg_names or "dom" in arg_names:
                response = await client.get(parser.parser["url"])
                if "res" in arg_names:
                    args["res"] = response.text
                elif "dom" in arg_names:
                    args["dom"] = HTMLParser(response.text)
            if "http" in arg_names:
                args["http"] = client
            html_request_time = time.time() - start
            start = time.time()
            parsed = parser(**args)
            if inspect.isasyncgen(parsed):
                parsed = [i async for i in parsed]
            for item in parsed or []:
                if isinstance(item, Soup):
                    soups.append(item)
                elif isinstance(item, Lunch):
                    lunches.append(item)
                else:
                    raise "Unsupported item"
            match_time = time.time() - start
            return cleanup(
                {
                    **res,
                    "lunches": lunches,
                    "soups": soups,
                    "elapsed": html_request_time + match_time,
                    "elapsed_html_request": html_request_time,
                    "elapsed_parsing": match_time,
                }
            )
        except:  # noqa: E722
            return {
                **res,
                "error": traceback.format_exc(),
                "elapsed": time.time() - start,
                "elapsed_html_request": 0,
                "elapsed_parsing": 0,
            }

    restaurants = [obj for _, obj in globals().items() if hasattr(obj, "parser")]
    if not allowed_restaurants:
        allowed_restaurants = [r.parser["name"] for r in restaurants]

    return await asyncio.gather(*[collect(r) for r in restaurants if r.parser["name"] in allowed_restaurants])


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("restaurant", nargs="*")
    p.add_argument("--sort", "-s", choices=["error", "time"], default="error")
    args = p.parse_args()

    logging.basicConfig(format="[%(asctime)s] %(levelname)s %(name)s - %(message)s", level=logging.INFO)

    restaurants = asyncio.run(gather_restaurants(args.restaurant))

    sorters = {
        "time": lambda r: r["elapsed"],
        "error": lambda r: ("error" in r, len(r.get("lunches", [])) == 0),
    }

    exit_code = 0
    for restaurant in sorted(restaurants, key=sorters[args.sort]):
        print()
        print(restaurant["name"], f"({restaurant['elapsed']:.3}s)")
        if "error" in restaurant:
            exit_code = 1
            print(restaurant["error"])
        else:
            for soup in restaurant["soups"]:
                print(" ", soup)
            for lunch in restaurant["lunches"]:
                print(" ", lunch)

    exit(exit_code)
