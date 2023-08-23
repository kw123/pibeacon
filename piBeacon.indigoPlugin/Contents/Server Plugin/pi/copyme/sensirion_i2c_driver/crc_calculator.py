# -*- coding: utf-8 -*-
# (c) Copyright 2019 Sensirion AG, Switzerland

from __future__ import absolute_import, division, print_function


class CrcCalculator(object):
    """
    Helper class to calculate arbitrary CRCs. An instance of this class
    can be called like a function to calculate the CRC of the passed data.

    .. note:: This class is not used within this package, its purpose is to
              help users writing drivers for I²C devices which protect the
              transferred data with CRCs.
    """
    def __init__(self, width, polynomial, init_value=0, final_xor=0):
        """
        Constructs a calculator object with the given CRC parameters.

        :param int width:
            Number of bits of the CRC (e.g. 8 for CRC-8).
        :param int polynomial:
            The polynomial of the CRC, without leading '1' (e.g. 0x31 for the
            polynomial x^8 + x^5 + x^4 + 1).
        :param int init_value:
            Initialization value of the CRC. Defaults to 0.
        :param int final_xor:
            Final XOR value of the CRC. Defaults to 0.
        """
        super(CrcCalculator, self).__init__()
        self._width = width
        self._polynomial = polynomial
        self._init_value = init_value
        self._final_xor = final_xor

    def __call__(self, data):
        """
        Calculate the CRC of the given data.

        :param iterable data:
            The input data (iterable with values of given bit width, e.g.
            list of 8-bit integers).
        :return:
            The calculated CRC.
        :rtype:
            int
        """
        crc = self._init_value
        for value in data:
            crc ^= value
            for i in range(self._width):
                if crc & (1 << (self._width - 1)):
                    crc = (crc << 1) ^ self._polynomial
                else:
                    crc = crc << 1
                crc &= (1 << self._width) - 1
        return crc ^ self._final_xor
