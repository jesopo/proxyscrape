import asyncio
from argparse    import ArgumentParser
from asyncio     import StreamReader, StreamWriter
from email.utils import formatdate

async def server(port: int, token: str):
    async def _client(
            reader: StreamReader,
            writer: StreamWriter
            ):
        ip, port = writer.get_extra_info("peername")
        body     = f"{token}\n{ip}\n"
        dt       = formatdate(timeval=None, localtime=False, usegmt=True)
        print(f"- request from {ip}")

        data = [
            "HTTP/1.1 200 OK",
            "Content-Length: " + str(len(body)),
            "Content-Type: text/plain",
            "Date: " + dt,
            "",
            body
        ]
        writer.write("\r\n".join(data).encode("utf8"))
        await writer.drain()

        writer.close()
        await writer.wait_closed()

    server = await asyncio.start_server(_client, "", port)
    async with server:
        await server.serve_forever()

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("port", type=int)
    parser.add_argument("token")
    args   = parser.parse_args()

    asyncio.run(server(args.port, args.token))
