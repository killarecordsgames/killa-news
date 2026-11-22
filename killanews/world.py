"""Paesi e continenti delle testate internazionali (nomi in italiano)."""

CONTINENTS = ["Europa", "Asia e Medio Oriente", "Africa", "America del Nord", "America Latina", "Oceania"]

_BY_CONTINENT = {
    "Europa": [
        "Unione Europea", "Regno Unito", "Irlanda", "Francia", "Germania", "Spagna", "Portogallo", "Paesi Bassi",
        "Belgio", "Lussemburgo", "Svizzera", "Austria", "Grecia", "Polonia", "Ucraina", "Russia", "Svezia",
        "Norvegia", "Danimarca", "Finlandia", "Islanda", "Romania", "Bulgaria", "Ungheria", "Repubblica Ceca",
        "Slovacchia", "Slovenia", "Croazia", "Serbia", "Bosnia ed Erzegovina", "Albania", "Macedonia del Nord",
        "Montenegro", "Kosovo", "Balcani", "Moldavia", "Bielorussia", "Lituania", "Lettonia", "Estonia", "Malta",
        "Cipro", "Turchia", "Città del Vaticano", "San Marino", "Monaco", "Andorra", "Liechtenstein",
    ],
    "Asia e Medio Oriente": [
        "Giappone", "Cina", "Hong Kong", "Taiwan", "Corea del Sud", "Corea del Nord", "Mongolia", "India",
        "Pakistan", "Bangladesh", "Sri Lanka", "Nepal", "Afghanistan", "Indonesia", "Filippine", "Singapore",
        "Malesia", "Thailandia", "Vietnam", "Cambogia", "Laos", "Myanmar", "Israele", "Palestina", "Libano",
        "Siria", "Giordania", "Iraq", "Iran", "Arabia Saudita", "Emirati Arabi Uniti", "Qatar", "Kuwait",
        "Bahrein", "Oman", "Yemen", "Armenia", "Georgia", "Azerbaigian", "Kazakistan", "Uzbekistan",
    ],
    "Africa": [
        "Africa (tutto il continente)", "Marocco", "Algeria", "Tunisia", "Libia", "Egitto", "Sudan", "Etiopia",
        "Eritrea", "Somalia", "Kenya", "Uganda", "Tanzania", "Ruanda", "Repubblica Democratica del Congo",
        "Nigeria", "Ghana", "Senegal", "Mali", "Burkina Faso", "Niger", "Costa d'Avorio", "Camerun", "Gabon",
        "Angola", "Zambia", "Zimbabwe", "Mozambico", "Madagascar", "Sudafrica", "Namibia", "Botswana",
        "Mauritania", "Guinea", "Sierra Leone", "Liberia", "Togo", "Benin", "Ciad", "Capo Verde",
    ],
    "America del Nord": ["Stati Uniti", "Canada", "Messico"],
    "America Latina": [
        "Brasile", "Argentina", "Cile", "Colombia", "Perù", "Venezuela", "Ecuador", "Bolivia", "Paraguay",
        "Uruguay", "Cuba", "Repubblica Dominicana", "Porto Rico", "Guatemala", "Honduras", "El Salvador",
        "Nicaragua", "Costa Rica", "Panama", "Haiti", "Giamaica",
    ],
    "Oceania": ["Australia", "Nuova Zelanda", "Figi", "Papua Nuova Guinea", "Samoa", "Tonga",
                "Oceania (isole del Pacifico)"],
}

COUNTRY_CONTINENT = {c: cont for cont, countries in _BY_CONTINENT.items() for c in countries}

HOME_COUNTRY = "Italia"


def continent_of(country: str) -> str:
    """Continente del paese indicato; '' per l'Italia o per i paesi sconosciuti."""
    return COUNTRY_CONTINENT.get((country or "").strip(), "")


def countries_of(continent: str):
    return list(_BY_CONTINENT.get(continent, []))


def is_international(country: str) -> bool:
    country = (country or "").strip()
    return bool(country) and country != HOME_COUNTRY
