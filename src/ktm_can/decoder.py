# -*- encoding: utf-8 -*-

## decodes messages read from the KTM CAN bus

import struct


def lo_nibble(b):
    return b & 0x0F


def hi_nibble(b):
    return (b >> 4) & 0x0F


def signed12(value):
    return -(value & 0b100000000000) | (value & 0b011111111111)


class Message(object):
    """a message read from the bus"""
    def __init__(self, sender_id, data):
        super(Message, self).__init__()
        self.id = sender_id
        self.data = data


class Decoder(object):
    """decoder of Message objects"""
    def __init__(self, emit_unmapped=False):
        super(Decoder, self).__init__()

        self.emit_unmapped = emit_unmapped

    def decode(self, msg):
        """yields (id, key, value) tuples for known data in a Message"""

        if msg.id == 0x120:
            ## Received every 20ms

            ## D0, D1 -- engine rpm
            yield msg.id, "rpm", struct.unpack(">H", msg.data[0:2])[0]

            ## D2 -- (commanded?) throttle;
            ## @todo confirm range; assumed to be 0-255
            yield msg.id, "throttle", msg.data[2]

            ## D3 B4 -- kill switch position
            yield msg.id, "kill_switch", (msg.data[3] & 0b00010000) >> 4

            ## D4, B7 -- throttle map
            ## @todo determine if requested or actual
            yield msg.id, "throttle_map", msg.data[4] & 0b00000001

            ## D5 -- unknown
            ## D6 -- unknown
            ## D7 -- counter

            ## no additional usable data found
            if self.emit_unmapped:
                yield msg.id, "unmapped", " ".join([
                    "__",
                    "__",
                    "__",
                    "{:02X}".format(msg.data[3] & (~0b00010000 & 0xFF)),
                    "{:02X}".format(msg.data[4] & (~0b00000001 & 0xFF)),
                    "{:02X}".format(msg.data[5]),
                    "{:02X}".format(msg.data[6]),
                    "__", # "{:02X}".format(msg.data[7]),              ## counter?
                ])

        elif msg.id == 0x129:
            ## Received every 20ms

            ## D0, B0..B4 -- gear position; 0 is neutral
            yield msg.id, "gear", hi_nibble(msg.data[0])

            ## D0, B5 -- clutch switch
            yield msg.id, "clutch_in", ((msg.data[0] & 0b00001000) >> 3) == 1

            ## D1 -- unknown
            ## D2 -- unknown
            ## D3 -- unknown
            ## D4 -- unknown
            ## D5 -- unknown
            ## D6 -- unknown
            ## D7 -- counter

            ## no additional usable data found
            if self.emit_unmapped:
                yield msg.id, "unmapped", " ".join([
                    "__",
                    "{:02X}".format(msg.data[1]),
                    "{:02X}".format(msg.data[2]),
                    "{:02X}".format(msg.data[3]),
                    "{:02X}".format(msg.data[4]),
                    "{:02X}".format(msg.data[5]),
                    "{:02X}".format(msg.data[6]),
                    "__", # "{:02X}".format(msg.data[7]),              ## counter?
                ])

        elif msg.id == 0x12A:
            ## Received every 50ms

            ## D0 -- unknown

            ## D1, B1 -- requested throttle map: 0 == mode 1, 1 == mode 2
            yield msg.id, "requested_throttle_map", (msg.data[1] & 0b01000000) >> 6

            ## D2 -- unknown
            ## D3 -- unknown
            ## D4 -- unknown
            ## D5 -- unknown
            ## D6 -- unknown
            ## D7 -- unknown

            if self.emit_unmapped:
                yield msg.id, "unmapped", " ".join([
                    "{:02X}".format(msg.data[0]),
                    "{:02X}".format(msg.data[1] & (~0b01000000 & 0xFF)),
                    "{:02X}".format(msg.data[2]),
                    "{:02X}".format(msg.data[3]),
                    "{:02X}".format(msg.data[4]),
                    "{:02X}".format(msg.data[5]),
                    "{:02X}".format(msg.data[6]),
                    "{:02X}".format(msg.data[7]),
                ])

        elif msg.id == 0x12B:
            ## Received every 10ms

            ## D0     -- always 0
            ## D1     -- always 0
            ## D2..D3 -- unknown, looks like a number
            ## D4     -- always 0

            ## D5..D7 -- lean angle, tilt
            ## from Dan Plastina:
            #> Lean Angle – it’s provided by ID 299. The last 3 bytes (6,7,8)
            #> split into two 12bit counters. The last 0x000 is for lean. I’ve
            #> tested the lean extensively. 0x000 is neutral, 0x001 starts
            #> leaning to the right. 0xFFF starts leaning to the left. I
            #> *believe* the first 0x000 are tilt but I’ve yet to validate.

            ## this looks like a 12-bit two's complement signed integer
            ## https://stackoverflow.com/a/32262478/53051

            # @todo confirm
            yield msg.id, "tilt?", signed12((msg.data[5] << 4) | hi_nibble(msg.data[6]))

            # @todo confirm
            yield msg.id, "lean?", signed12((lo_nibble(msg.data[6]) << 8) | msg.data[7])

            ## this looks like a number, but can't find a correlation in the data
            # yield msg.id, "@todo trace", struct.unpack(">H", msg.data[2:4])

            if self.emit_unmapped:
                yield msg.id, "unmapped", " ".join([
                    "__", # "{:02X}".format(msg.data[0]),
                    "__", # "{:02X}".format(msg.data[1]),
                    "{:02X}".format(msg.data[2]),
                    "{:02X}".format(msg.data[3]),
                    "__", # "{:02X}".format(msg.data[4]),
                    "__", # "{:02X}".format(msg.data[5]),
                    "__", # "{:02X}".format(msg.data[6]),
                    "__", # "{:02X}".format(msg.data[7]),
                ])

        elif msg.id == 0x540:
            ## Received every 100ms

            ## D0 -- always 0x02
            assert msg.data[0] == 0x02

            ## D1, D2 -- engine rpm; as 0x120, but updated more slowly
            yield msg.id, "rpm", struct.unpack(">H", msg.data[1:3])[0]

            ## D4 -- kickstand (1 is raised), kickstand error
            yield msg.id, "kickstand_up", (msg.data[4] & 0b00000001) == 1
            yield msg.id, "kickstand_err", ((msg.data[4] & 0b10000000) >> 7) == 1

            ## D5 -- always 0x00
            assert msg.data[5] == 0x00

            ## D6 -- engine coolant, °C; compared to OBD2 value
            yield msg.id, "coolant_temp", struct.unpack(">H", msg.data[6:])[0] / 10.0

            if self.emit_unmapped:
                yield msg.id, "unmapped", " ".join([
                    "__",
                    "__",
                    "__",
                    "{:02X}".format(msg.data[3]),
                    "{:02X}".format(msg.data[4] & 0b01111110),
                    "__",
                    "__",
                    "__",
                ])

