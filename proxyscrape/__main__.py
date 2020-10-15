from argparse  import ArgumentParser
from asyncio   import Queue, run
from sys       import stderr, stdout

from anyio     import create_task_group

from .scrapers import get_scrapers, scrape
from .checkers import check_many


async def main():
    parser = ArgumentParser()
    parser.add_argument("target_ip")
    parser.add_argument("target_port", type=int)
    parser.add_argument("token")
    parser.add_argument("--concurrent", "-c", type=int, default=100)
    args = parser.parse_args()

    scrapers = get_scrapers()
    items    = await scrape(scrapers)
    stderr.write(f"checking {len(items)} proxies\n")
    stderr.flush()

    queue: "Queue[Tuple[str, str, int, str]]" = Queue()
    async with create_task_group() as tg:
        await tg.spawn(
            check_many,
            items,
            args.target_ip,
            args.target_port,
            args.token,
            args.concurrent,
            queue
        )

        while True:
            type, ip, port, out = await queue.get()
            stdout.write(f"{type} {out}:{port} {ip}\n")
            stdout.flush()

run(main())
