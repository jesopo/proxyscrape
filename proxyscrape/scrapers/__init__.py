import glob, importlib.util, os.path
from random import shuffle
from typing import Awaitable, Callable, List, Tuple

_TYPE_SCRAPER = Callable[[], Awaitable[List[Tuple[str, str, int]]]]
SCRAPERS: List[_TYPE_SCRAPER] = []

def scraper_decorator(func: _TYPE_SCRAPER):
    SCRAPERS.append(func)
    return func

def get_scrapers() -> List[_TYPE_SCRAPER]:
    basedir = os.path.dirname(os.path.realpath(__file__))
    files   = glob.glob(os.path.join(basedir, "*.py"))

    if not SCRAPERS:
        for filepath in files:
            filename   = os.path.basename(filepath)
            modulename = f"scraper_{filename[:-3]}"
            spec       = importlib.util.spec_from_file_location(
                modulename, filepath
            )
            module     = importlib.util.module_from_spec(spec)
            setattr(module, "scraper_decorator", scraper_decorator)
            spec.loader.exec_module(module)

    return SCRAPERS

async def scrape(
        scrapers: List[_TYPE_SCRAPER]
        ) -> List[Tuple[str, str, int]]:

    all: List[Tuple[str, str, int]] = []
    for scraper in scrapers:
        list = await scraper()
        all.extend(list)

    shuffle(all)
    return all
