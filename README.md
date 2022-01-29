This repository contains ccf2pulse, a tool for extracting
infrared pulse codes from old-school Pronto CCF files.

## Background

Back in the days, Philips produced a PDA like universal remote
control called [Pronto][1]. Like any universal remote control the
Pronto can also learn codes from other remote controls. For some
reason, the Pronto and its file exchange format CCF was kind of popular.

## Use Cases

Say your remote-control for your old HiFi/appliance/etc. device
is broken. Or you obtained some device with the remote control
missing. And - say - there isn't even any replacement
commercially available, but you manage to hunt down some CCF file
from somebody's homepage or some IR database site such as
[remotecentral][2].

So far, so good. But how to actually read that obscure
proprietary CCF format?

ccf2pulse helps with that. It extracts the raw infrared pulses in
an annotated text format for copy and pasting into other infrared
code configurations.


## Examples

Dump Codes:

```
./ccf2pulse.py xyz.ccf
[..]
Button: Down
    Carrier: 40.24 kHz (0x67)
    Header:  0000 0067 0000 0012
    once (0 on/off pairs):
    repeat (18 on/off pairs):
        0017 0095  0017 0095  0097 0015
        0097 0015  0017 0095  0017 0095
        0017 0095  0017 0095  0017 0095
        0017 0095  0017 0095  0017 0095
        0017 0095  0017 0095  0097 0015
        0097 0015  0097 0015  0097 041c
```

Rewrite to another carrier frequency:

```
./ccf2pulse.py xyz.ccf --rescale 38000 
[..]
Button: Down
    Carrier: 38.03 kHz (0x6d)
    Header:  0000 006d 0000 0012
    once (0 on/off pairs):
    repeat (18 on/off pairs):
        0015 008c  0015 008c  008e 0013
        008e 0013  0015 008c  0015 008c
        0015 008c  0015 008c  0015 008c
        0015 008c  0015 008c  0015 008c
        0015 008c  0015 008c  008e 0013
        008e 0013  008e 0013  008e 03e2
```

Dump pulses using human readable units:

```
./ccf2pulse.py xyz.ccf --lirc  | less
[..]
Button: Down
    Carrier: 40.24 kHz (0x67)
    Header:  0000 0067 0000 0012
    once (0 on/off pairs, in µs, decimal):
    repeat (18 on/off pairs, in µs, decimal):
         571 3702   571 3702  3752  521
        3752  521   571 3702   571 3702
         571 3702   571 3702   571 3702
         571 3702   571 3702   571 3702
         571 3702   571 3702  3752  521
        3752  521  3752  521  3752 26140
```


## CCF Format

The Pronto CCF basically defines some buttons for a learned
device, i.e. it defines the placement of some UI elements
and the IR codes itself.

The codes are learned raw, i.e. each learned button is basically
just a list of on/off pulse pairs. In a weird format, using weird
units.

See the inline comments and format documentation in
`ccf2pulse.py`.


## Related Work

There is pronto2lirc but it can't read binary CCF files. Instead
it refers to CCFTools/CCFDecompile which seem to have been
windows-only tools, which I couldn't find online, anymore, as of
2022.

There was the 'tonto' project which looks like it supports some
kind of CCF extraction feature. However, it's written in a kind
of lasagna code style and its project page is also gone. Also,
it's probably hard to get going since it's written in Java.

There is [IrScrutinizer][3] which is a Java GUI applications that
supports importing/exporting into various IR code formats,
including CCF and LIRC. Since it's written in Java, it isn't packaged
by Linux distributions, probably either downloads half the
internet via maven and/or requires trusting many unpackaged
dependencies I haven't tried it.

The LIRC project has a huge IR remote control database in a much
more sane format than CCF. Besides raw codes it also supports
more semantic/structured codes (such as NEC) which are more
compact and easier to [reason about][7]. But even when using raw
codes, the LIRC format is more useful, since the pulses are
specified in microseconds.

However, unfortunately, the LIRC project looks kind of dead,
nowadays.  For example, the last remote control configuration was
added in 2018.

When targeting microcontrollers, there are several Arduino open
source libraries for decoding and transmitting IR codes, such as
[IRLib2][5] and [IRremote][6] that can also deal with raw codes.


[1]: https://etmriwi.home.xs4all.nl/ht/pronto.htm
[2]: http://www.remotecentral.com/
[3]: http://www.harctoolbox.org/IrScrutinizer.html
[4]: https://sourceforge.net/p/lirc-remotes/code/ci/master/tree/remotes/
[5]: https://github.com/cyborg5/IRLib2
[6]: https://github.com/Arduino-IRremote/Arduino-IRremote
[7]: http://www.righto.com/2010/03/understanding-sony-ir-remote-codes-lirc.html
