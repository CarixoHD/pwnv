template = r"""#!/usr/bin/env python3

from pwn import *

host = args.HOST or ''
port = int(args.PORT or 1337)
ssl = args.SSL or False

binary = './binary'

gdbscript = '''
    c
'''

context.binary = elf = ELF(binary)
context.terminal = ['tmux', 'splitw', '-h']

if os.path.isfile("./libc.so.6"): libc = ELF('./libc.so.6', checksec=False)


# utils
u64 = lambda d: struct.unpack("<Q", d.ljust(8, b"\0"))[0]
u32 = lambda d: struct.unpack("<I", d.ljust(4, b"\0"))[0]
u16 = lambda d: struct.unpack("<H", d.ljust(2, b"\0"))[0]

# credits to spwn by @chino
ru         = lambda *x, **y: p.recvuntil(*x, **y, drop=True)
rl         = lambda *x, **y: p.recvline(*x, **y)
rc         = lambda *x, **y: p.recv(*x, **y)
sla        = lambda *x, **y: p.sendlineafter(*x, **y)
sa         = lambda *x, **y: p.sendafter(*x, **y)
sl         = lambda *x, **y: p.sendline(*x, **y)
sn         = lambda *x, **y: p.send(*x, **y)
logbase    = lambda: log.info("libc base = %#x" % libc.address)
logleak    = lambda name, val: log.info(name+" = %#x" % val)
one_gadget = lambda: [int(i) + libc.address for i in subprocess.check_output(['one_gadget', '--raw', '-l1', libc.path]).decode().split(' ')]

# exit_handler stuff
fs_decrypt = lambda addr, key: ror(addr, 0x11) ^ key
fs_encrypt = lambda addr, key: rol(addr ^ key, 0x11)


# heap stuff
prot_ptr = lambda pos, ptr: (pos >> 12) ^ ptr
def deobfuscate(val):
    mask = 0xfff << 52
    while mask:
        v = val & mask
        val ^= (v >> 12)
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


"""
