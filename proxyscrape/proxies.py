import ssl, struct, sys
from asyncio import open_connection, run, StreamReader, StreamWriter
from socket  import inet_aton
from typing  import Optional, Tuple

async def _recv(
        reader: StreamReader,
        count:  int
        ) -> bytes:
    buff = b""
    while len(buff) < count:
        byte = await reader.read(1)
        if byte == b"":
            return None
        else:
            buff += byte
    return buff

async def _http(
        type:   str,
        reader: StreamReader
        ) -> Optional[Tuple[int, bytes]]:

    head = True
    buff = b""
    clen = -1
    stat = -1
    while True:
        data = await reader.read(1024)
        if not data:
            return stat, None
        elif head:
            lines = (buff+data).split(b"\r\n")
            buff  = lines.pop(-1)
            for i, line in enumerate(lines):
                if (line.startswith(b"HTTP/1.") and
                        line.count(b" ") >= 2):
                    stat = int(line.split(b" ", 2)[1])
                if line.lower().startswith(b"content-length: "):
                    clen = int(line.split(b" ", 1)[1])
                elif line == b"":
                    if clen == -1:
                        return stat, b""
                    else:
                        head = False

                    body = b"\r\n".join(lines[i+1:])
                    if body and not buff:
                        body += b"\r\n"
                    else:
                        body += buff
                    buff = body
                    break
        else:
            buff += data

        if clen > -1 and len(buff) >= clen:
            return stat, buff[:clen]

async def http_get(
        reader: StreamReader,
        writer: StreamWriter,
        target_ip:   str,
        target_port: int
        ) -> Optional[bytes]:

    write = f"GET http://{target_ip}:{target_port} HTTP/1.0\r\n\r\n"
    writer.write(write.encode("utf8"))
    await writer.drain()
    stat, body = await _http("GET", reader)
    return body

async def http_connect(
        reader: StreamReader,
        writer: StreamWriter,
        target_ip:   str,
        target_port: int
        ) -> Optional[bytes]:

    write = f"CONNECT {target_ip}:{target_port} HTTP/1.0\r\n\r\n"
    writer.write(write.encode("utf8"))
    await writer.drain()
    stat, body = await _http("CONNECT1", reader)
    if stat == 200 and body == b"":
        writer.write(b"GET / HTTP/1.0\r\n\r\n")
        await writer.drain()
        stat, body = await _http("CONNECT2", reader)
        return body
    return None

async def socks5(
        reader: StreamReader,
        writer: StreamWriter,
        target_ip:   str,
        target_port: int
        ) -> Optional[bytes]:

    writer.write(bytes([
        0x05, # version
        0x01, # auth option count
        0x00  # anonymous auth
    ]))
    await writer.drain()

    resp = await _recv(reader, 2)
    if not resp == b"\x05\x00":
        return None

    # they said yes!
    writer.write(struct.pack(
        "!BBBB4sH",
        0x05, # version
        0x01, # CONNECT command
        0x00, # reserved
        0x01, # IPv4 address type,
        inet_aton(target_ip),
        target_port
    ))
    await writer.drain()

    resp = await _recv(reader, 4)
    if not resp == b"\x05\x00\x00\x01":
        return None

    # we don't actually need to parse these
    addr = await _recv(reader, 4) # inet_ntoa
    port = await _recv(reader, 2) # ([0]<<8) + [1]

    writer.write(f"GET / HTTP/1.0\r\n\r\n".encode("utf8"))
    await writer.drain()

    stats, body = await _http("SOCKS5", reader)
    return body

async def from_type(
        type:   str,
        reader: StreamReader,
        writer: StreamWriter,
        target_ip:   str,
        target_port: int
        ) -> Optional[bytes]:
    if   type == "socks5":
        return await socks5(
            reader, writer, target_ip, target_port)
    elif type == "http-get":
        return await http_get(
            reader, writer, target_ip, target_port)
    elif type == "http-connect":
        return await http_connect(
            reader, writer, target_ip, target_port)
