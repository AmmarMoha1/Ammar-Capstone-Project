"""Destination photos bundled as static files (no database field needed).

Each photo is a freely licensed image from Wikimedia Commons, resized and
converted to WebP. Credits follow the licences' attribution requirements and are
listed on the /credits/ page and next to large photos.
"""

LICENCE_URLS = {
    "CC BY 2.0": "https://creativecommons.org/licenses/by/2.0/",
    "CC BY 3.0": "https://creativecommons.org/licenses/by/3.0/",
    "CC BY 4.0": "https://creativecommons.org/licenses/by/4.0/",
    "CC BY-SA 3.0": "https://creativecommons.org/licenses/by-sa/3.0/",
    "CC BY-SA 4.0": "https://creativecommons.org/licenses/by-sa/4.0/",
}

PHOTOS = {
    "Cairo": {
        "slug": "cairo",
        "alt": "The Nile running through central Cairo, with river boats and high-rise buildings along the bank",
        "artist": "Ghaly",
        "licence": "CC BY-SA 3.0",
        "source": "https://commons.wikimedia.org/wiki/File:Nile_in_Cairo.jpg",
    },
    "Baku": {
        "slug": "baku",
        "alt": "Rooftops of Baku's old city with the three Flame Towers on the skyline",
        "artist": "Francisco Anzola",
        "licence": "CC BY 3.0",
        "source": "https://commons.wikimedia.org/wiki/File:View_From_Maidens_Tower_(221090097).jpeg",
    },
    "Tbilisi": {
        "slug": "tbilisi",
        "alt": "Old Tbilisi's houses climbing the hill below Narikala Fortress, above the river",
        "artist": "GeoO",
        "licence": "CC BY-SA 4.0",
        "source": "https://commons.wikimedia.org/wiki/File:Old_Tbilisi_town_in_Tbilisi,_Georgia.jpg",
    },
    "Dubai": {
        "slug": "dubai",
        "alt": "Dubai Marina's cluster of skyscrapers rising above the water",
        "artist": "Norlando Pobre",
        "licence": "CC BY 2.0",
        "source": "https://commons.wikimedia.org/wiki/File:Dubai_Marina_Skyline.jpg",
    },
    "Istanbul": {
        "slug": "istanbul",
        "alt": "Galata Tower above waterfront buildings, seen across the water in Istanbul",
        "artist": "Gryffindor",
        "licence": "Public domain",
        "source": "https://commons.wikimedia.org/wiki/File:Galata_Bosphorus_Istanbul_2007_012.jpg",
    },
    "Trabzon": {
        "slug": "trabzon",
        "alt": "Uzungöl lake and town in a green mountain valley near Trabzon",
        "artist": "İhsan Deniz Kılıçoğlu",
        "licence": "CC BY-SA 3.0",
        "source": "https://commons.wikimedia.org/wiki/File:Uzung%C3%B6l_lake_and_town.jpg",
    },
    "Sarajevo": {
        "slug": "sarajevo",
        "alt": "Red-roofed houses of Sarajevo filling the valley, with the river and green hills",
        "artist": "Julian Nyča",
        "licence": "CC BY-SA 4.0",
        "source": "https://commons.wikimedia.org/wiki/File:Sarajevo_City_Panorama.JPG",
    },
    "Vienna": {
        "slug": "vienna",
        "alt": "The yellow façade of Schönbrunn Palace in Vienna under a clear sky",
        "artist": "Diego Delso",
        "licence": "CC BY-SA 4.0",
        "source": "https://commons.wikimedia.org/wiki/File:Palacio_de_Sch%C3%B6nbrunn,_Viena,_Austria,_2020-02-02,_DD_07-09_HDR.jpg",
    },
    "Prague": {
        "slug": "prague",
        "alt": "Charles Bridge crossing the Vltava river towards Prague's old town",
        "artist": "DXR",
        "licence": "CC BY-SA 4.0",
        "source": "https://commons.wikimedia.org/wiki/File:North_view_of_Charles_Bridge_from_M%C3%A1nes%C5%AFv_most,_Prague_20160808_1.jpg",
    },
    "Kuala Lumpur": {
        "slug": "kuala-lumpur",
        "alt": "The Petronas Twin Towers rising above Kuala Lumpur at dusk",
        "artist": "James Kerwin",
        "licence": "CC BY 2.0",
        "source": "https://commons.wikimedia.org/wiki/File:The_Twins_SE_Asia_2019_(49171985716).jpg",
    },
    "Bali": {
        "slug": "bali",
        "alt": "Palm trees and terraced rice fields on a green hillside in Bali",
        "artist": "Vyacheslav Argenberg",
        "licence": "CC BY 4.0",
        "source": "https://commons.wikimedia.org/wiki/File:Rice_terraces,_Bali.jpg",
    },
    "Malé": {
        "slug": "male",
        "alt": "A small palm-covered island in a shallow turquoise lagoon in the Maldives",
        "artist": "Nattu",
        "licence": "CC BY 2.0",
        "source": "https://commons.wikimedia.org/wiki/File:Maldives_Islands_-_Flickr_-_nattu.jpg",
    },
}


def photo_for_city(city):
    """Photo details for a city, or None when no photo is bundled."""
    photo = PHOTOS.get(city)
    if photo is None:
        return None
    return {
        **photo,
        "city": city,
        "wide": f"img/destinations/{photo['slug']}-wide.webp",
        "thumb": f"img/destinations/{photo['slug']}-thumb.webp",
        "licence_url": LICENCE_URLS.get(photo["licence"]),
    }


def all_photos():
    return [photo_for_city(city) for city in sorted(PHOTOS)]
