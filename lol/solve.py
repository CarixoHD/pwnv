#!/usr/bin/env python3

from pwn import *

host = args.HOST or ''
port = int(args.PORT or 1337)

binary = './binary'

gdbscript = '''
    c
'''

context.binary = elf = ELF(binary)
context.terminal = ['tmux', 'splitw', '-h']

if os.path.isfile("./libc.so.6"): libc = ELF('./libc.so.6', checksec=False)

# utils
u64 = lambda d: pwn.u64(d.ljust(8, b"\0")[:8])
u32 = lambda d: pwn.u32(d.ljust(4, b"\0")[:4])
u16 = lambda d: pwn.u16(d.ljust(2, b"\0")[:2])

# credits to spwn by @chino
ru  = lambda *x, **y: p.recvuntil(*x, **y)
rl  = lambda *x, **y: p.recvline(*x, **y)
rc  = lambda *x, **y: p.recv(*x, **y)
sla = lambda *x, **y: p.sendlineafter(*x, **y)
sa  = lambda *x, **y: p.sendafter(*x, **y)
sl  = lambda *x, **y: p.sendline(*x, **y)
sn  = lambda *x, **y: p.send(*x, **y)


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
        return remote(host, port)
    else:
        return process([elf.path] + argv, *a, **kw)


p = start()



p.interactive()


