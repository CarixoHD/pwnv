from pwn import *

con = "{{service.host}} {{service.port}}"


host, port = con.replace(" ", ":").split(":")


ssl = False

binary = "./binary"

gdbscript = """
    c
"""

elf = context.binary = ELF(binary)
libc = context.binary.libc
context.terminal = ["tmux", "splitw", "-h"]


# utils
def u64(d):
    return struct.unpack("<Q", d.ljust(8, b"\0"))[0]


def u32(d):
    return struct.unpack("<I", d.ljust(4, b"\0"))[0]


def u16(d):
    return struct.unpack("<H", d.ljust(2, b"\0"))[0]


# credits to spwn by @chino
def ru(*x, **y):
    return p.recvuntil(*x, **y, drop=True)


def rl(*x, **y):
    return p.recvline(*x, **y, keepends=False)


def rc(*x, **y):
    return p.recv(*x, **y)


def sla(*x, **y):
    return p.sendlineafter(*x, **y)


def sa(*x, **y):
    return p.sendafter(*x, **y)


def sl(*x, **y):
    return p.sendline(*x, **y)


def sn(*x, **y):
    return p.send(*x, **y)


def logbase():
    return log.info("libc base = %#x" % libc.address)


def logleak(name, val):
    return log.info(name + " = %#x" % val)


def ls(x):
    return log.success(x)


def lss(x):
    return ls("\033[1;31;40m{} -> 0x{:x} \033[0m".format(x, eval(x)))


def one_gadget():
    return [
        int(i) + libc.address
        for i in subprocess.check_output(["one_gadget", "--raw", "-l1", libc.path])
        .decode()
        .split(" ")
    ]


# exit_handler stuff
def fs_decrypt(addr, key):
    return ror(addr, 0x11) ^ key


def fs_encrypt(addr, key):
    return rol(addr ^ key, 0x11)


# heap stuff
def prot_ptr(pos, ptr):
    return (pos >> 12) ^ ptr


def deobfuscate(val):
    mask = 0xFFF << 52
    while mask:
        v = val & mask
        val ^= v >> 12
        mask >>= 12
    return val


def start(argv=[], *a, **kw):
    if args.GDB:
        return gdb.debug([elf.path] + argv, gdbscript=gdbscript, *a, **kw)
    elif args.REMOTE:
        return remote(host, port, ssl=ssl)
    else:
        return process([elf.path] + argv, *a, **kw)


p = start()


p.interactive()
