import asyncio, ssl, sys
from argparse import ArgumentParser
from asyncio  import StreamReader, StreamWriter
from typing   import Dict, List, Optional, Tuple

from anyio         import create_task_group
from async_timeout import timeout as timeout_

from . import scrapers, proxies

async def _connect(
        ip:    str,
        port:  int,
        istls: bool
        ) -> Tuple[StreamReader, StreamWriter]:

    tls: Optional[ssl.SSLContext] = None
    if istls:
        tls = ssl.SSLContext(ssl.PROTOCOL_TLS)

    async with timeout_(30):
        reader, writer = await asyncio.open_connection(ip, port, ssl=tls)
        return (reader, writer)

async def check_one(
        type_:       str,
        ip:          str,
        port:        int,
        target_ip:   str,
        target_port: int,
        token:       str
        ) -> Optional[str]:

    tls   = False
    types: List[str] = []
    if type_ in ["http", "https"]:
        types = ["http-connect", "http-get"]
    else:
        types = [type_]

    for type_ in types:
        try:
            reader, writer = await _connect(ip, port, tls)
        except Exception:
            break

        try:
            async with timeout_(30):
                resp = await proxies.from_type(
                    type_, reader, writer, target_ip, target_port
                )
        except Exception as e:
            pass
        else:
            if resp is not None:
                lines = resp.decode("latin-1").split("\n")
                if (lines[0] == token and
                        not lines[1] == target_ip):
                    return lines[1]
                else:
                    pass
        finally:
            writer.close()
    return None

async def check_many(
        items:       List[Tuple[str, str, int]],
        target_ip:   str,
        target_port: int,
        token:       str,
        concurrent:  int,
        queue:       "Queue[Tuple[str, str, int, str]]"
        ) -> Dict[Tuple[str, int], str]:

    sema = asyncio.Semaphore(concurrent)

    async def _check(type: str, ip: str, port: int):
        out = await check_one(type, ip, port, target_ip, target_port, token)
        if out is not None:
            await queue.put((type, ip, port, out))
        sema.release()

    async with create_task_group() as tg:
        for type, ip, port in items:
            await sema.acquire()
            await tg.spawn(_check, type, ip, port)
