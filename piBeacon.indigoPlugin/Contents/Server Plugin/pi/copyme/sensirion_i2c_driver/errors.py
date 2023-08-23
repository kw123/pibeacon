# -*- coding: utf-8 -*-
# (c) Copyright 2019 Sensirion AG, Switzerland

from __future__ import absolute_import, division, print_function

import logging
log = logging.getLogger(__name__)


class I2cError(IOError):
    """
    I2C error base exception.
    """
    def __init__(self, received_data=None, message="I2C error."):
        super(I2cError, self).__init__(message)
        self.received_data = received_data
        self.error_message = message


class I2cChecksumError(I2cError):
    """
    I2C checksum error.
    """
    def __init__(self, received_checksum, expected_checksum, received_data):
        super(I2cChecksumError, self).__init__(
            received_data,
            "I2C error: Received wrong checksum 0x{:02X} (expected 0x{:02X})."
            .format(received_checksum, expected_checksum)
        )
        self.received_checksum = received_checksum
        self.expected_checksum = expected_checksum


class I2cTransceiveError(I2cError):
    """
    I2C transceive error.
    """
    def __init__(self, transceiver_error, received_data,
                 message="Unknown error."):
        super(I2cTransceiveError, self).__init__(
            received_data,
            "I2C transceive failed: {}".format(message)
        )
        self.transceiver_error = transceiver_error


class I2cChannelDisabledError(I2cTransceiveError):
    """
    I2C channel disabled error.
    """
    def __init__(self, transceiver_error, received_data):
        super(I2cChannelDisabledError, self).__init__(
            transceiver_error,
            received_data,
            "Channel is disabled ({}).".format(str(transceiver_error))
        )


class I2cNackError(I2cTransceiveError):
    """
    I2C transceive NACK error.
    """
    def __init__(self, transceiver_error, received_data):
        super(I2cNackError, self).__init__(
            transceiver_error,
            received_data,
            "NACK (byte not acknowledged)."
        )


class I2cTimeoutError(I2cTransceiveError):
    """
    I2C transceive timeout error.
    """
    def __init__(self, transceiver_error, received_data):
        super(I2cTimeoutError, self).__init__(
            transceiver_error,
            received_data,
            "Timeout."
        )
