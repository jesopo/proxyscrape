from sys     import argv, stdin
from dronebl import DroneBL

if __name__ == "__main__":
    key     = open(argv[1]).read().strip()
    dronebl = DroneBL(key)

    for line in iter(stdin.readline, ""):
        line = line.strip()

        type, addr, connect_ip = line.split(" ", 2)
        ip, port = addr.split(":", 1)

        if type.startswith("socks"):
            type_n = 8
        elif type.startswith("http"):
            type_n = 9

        retry = 0
        while retry < 3:
            retry += 1
            try:
                look = dronebl.lookup(ip, type_n)
            except Exception:
                print(f"~ retrying {ip}")
                continue

            if not look:
                if ip == connect_ip:
                    comment = ""
                else:
                    comment = f"split tunnel from {connect_ip}"

                try:
                    id, msg = dronebl.add(ip, type_n, comment, port)
                except Exception:
                    print(f"~ retrying {ip}")
                    continue

                if id is not None:
                    print(f"+ {msg}", type, f":{port}")
                else:
                    print("!", msg)
            else:
                print(f"- {ip} already listed")
            break
