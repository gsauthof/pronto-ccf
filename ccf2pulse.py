#!/usr/bin/env python3

# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: © 2021 Georg Sauthoff <mail@gms.tf>

import argparse
import mmap
import os
import struct
import sys

# The Pronto CCF file format describes learned remote controls.
# Basically, it's a concatenation of binary structs.
# Since we are only interested in the CCF IR codes we ignore
# most blocks and just search for the codes.
#
# - Integers are stored big-endian
# - Strings are often referenced via offsets from the file start
# - Strings are often stored as length byte + character bytes
#
# In the diagrams, fields are specified with byte offsets.
#
#
# Button Code Block:
#
#    0                  2                                6
#    +------------------+--------------------------------+---------------------
#    | Size             | Name Offset                    | IR Code Block ...
#    +------------------+--------------------------------+---------------------
#
# where size is a 2 byte integer and the name offset is a 4 byte integer
#
# NB: the size field includes its own field
#
#
# Name String:
#
#    0        1        2        3
#    +--------+--------+--------+-------
#    | Length | Char0  | Char1  | ....
#    +--------+--------+--------+-------
#
#
# IR Code Block:
#
#    0                2                4                6                8
#    +----------------+----------------+----------------+----------------+----------------
#    + Type           | Freq Factor k  | # once pairs   | # repeat pairs | burst pairs ...
#    +----------------+----------------+----------------+----------------+----------------
#
#
# Burst Pair:
#
#    0                2                4
#    +----------------+----------------+
#    | ON Pulse       | Off Pulse      |
#    +----------------+----------------+
#
#
# NB: the pulse widths are specified in units of the configured frequency,
#     cf. the Freq Factor field in the IR Code Block.
#
#
# Carrier Frequency:
#
#     freq = 1000000 / (k * 0.241246)
#
# =>
#
#     k = 1000000 / (freq * 0.241246)
#
#
#
# See also:
#
# - http://www.remotecentral.com/features/irdisp2.htm
# - http://www.hifi-remote.com/infrared/IR-PWM.shtml
# - https://github.com/stewartoallen/tonto/blob/master/doc/ccf-schema.txt


def parse_args():
    p = argparse.ArgumentParser(
            description='Dump raw infrared codes from Pronto CCF files')
    p.add_argument('filename', metavar='FILENAME.CCF',
            help='input Pronto CCF file')
    p.add_argument('--lirc', action='store_true',
            help=("Convert pulse widths to µs"
                " (which is what is used in other raw code formats such as LIRC's)"))
    p.add_argument('--rescale', metavar='HZ', type=int,
            help=('rescale CCF widths to another carrier frequency such 38 kHz or 40 kHz'
                ' (useful e.g. when you know the right carrier frequency, '
                'but the CCF file was created with the wrong carrier frequency '
                'and you want to compare them to other CCF codes)'))
    p.add_argument('--carrier', metavar='HZ', type=int, default=40000,
            help='expected carrier frequency used to search for IR code blocks. Common choices are 38 kHz and 40 kHz (default: %(default)s)')
    args = p.parse_args()
    return args


code_fmt = struct.Struct('>HI2xHHH')
pair_fmt = struct.Struct('>HH')

def unpack_seq(b, i, n):
    r = []
    o = 0
    for k in range(n):
        on, off = pair_fmt.unpack_from(b, i + o)
        r.append(on)
        r.append(off)
        o += 4
    return r

def format_seq(xs, indent, hex=True):
    if not xs:
        return ''
    ss = [ ' ' * indent]
    for i, x in enumerate(xs, 1):
        if hex:
            ss.append(f'{x:04x}')
        else:
            ss.append(f'{x:4d}')
        if i % 6 == 0:
            ss.append('\n' + ' ' * indent)
            continue
        ss.append(' ')
        if i % 2 == 0:
            ss.append(' ')
    return ''.join(ss)

def to_khz(k):
    return 1000000.0 / (k * 0.241246) / 1000.0

def to_usec(x, k):
    return int(x * k * 0.241246)

def rescale(x, old_k, k):
    return int(old_k/k * x)

def freq2k(freq):
    return int(1000000.0 / (freq * 0.241246))

def search_ccf(args):
    filename = args.filename
    k = freq2k(args.carrier)
    k_low, k_high = int(k * 0.97), int(k * 1.03)

    b = mmap.mmap(os.open(filename, os.O_RDONLY), 0, prot=mmap.PROT_READ)
    ident1 = b[8:16]
    ident2 = b[32:36]
    if ident1 != b'@\xa5Z@_CCF' or ident2 != b'CCF\x00':
        raise RuntimeError('CCF file magic not found - not a CCF file?')
    pat = b'\x00\x00\x00'
    off = 0
    while True:
        i = b.find(pat, off)
        if i == -1:
            break

        if b[i+4] == 0 and b[i+6] == 0 and b[i+3] > k_low and b[i+3] < k_high:
            try:
                dump_button(b, i, args)
            except (IndexError, ):
                raise

        off = i + len(pat)

def dump_button(b, i, args):
    n, j, base, once_k, repeat_k = code_fmt.unpack_from(b, i-6)
    if n == 6 + 8 + (once_k + repeat_k) * (2+2):
        l = int(b[j])
        print('Button: ' + b[j+1:j+1+l].decode('latin1'))

        baseP = base
        if args.rescale:
            baseP = freq2k(args.rescale)

        print(f'    Carrier: {to_khz(baseP):.2f} kHz (0x{baseP:x})')
        print(f'    Header:  0000 {baseP:04x} {once_k:04x} {repeat_k:04x}')

        xs = unpack_seq(b, i+8, once_k)
        dump_pairs(xs, 'once', base, args)
        xs = unpack_seq(b, i+8+once_k*4, repeat_k)
        dump_pairs(xs, 'repeat', base, args)

def dump_pairs(xs, name, base, args):
        if args.lirc:
            print(f'    {name} ({len(xs)//2} on/off pairs, in µs, decimal):')
            xs = [ to_usec(x, base) for x in xs ]
        else:
            print(f'    {name} ({len(xs)//2} on/off pairs):')
            if args.rescale:
                k = freq2k(args.rescale)
                xs = [ rescale(x, base, k) for x in xs ]
        s = format_seq(xs, 8, hex=not args.lirc)
        if (s):
            print(s)


def main():
    args = parse_args()
    search_ccf(args)


if __name__ == '__main__':
    sys.exit(main())
