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
        """Initializes an I2cError exception, passing the message to the base Exception and storing the received data and error message on the instance.

        Inputs:
            received_data (bytes or None): Raw data received during the failed I2C operation
            message (str): Human-readable error message
        Outputs:
            None: Initializes the exception instance and stores received_data and error_message
        """
        super(I2cError, self).__init__(message)
        self.received_data = received_data
        self.error_message = message


class I2cChecksumError(I2cError):
    """
    I2C checksum error.
    """
    def __init__(self, received_checksum, expected_checksum, received_data):
        """Initializes an I2cChecksumError, building a formatted message reporting the received versus expected checksum and storing both checksums on the instance.

        Inputs:
            received_checksum (int): Checksum byte actually received
            expected_checksum (int): Checksum byte expected
            received_data (bytes): Raw data received during the operation
        Outputs:
            None: Initializes the exception and stores received_checksum and expected_checksum
        """
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
        """Initializes an I2cTransceiveError, forwarding the received data and a formatted transceive-failure message to the base class and storing the underlying transceiver error.

        Inputs:
            transceiver_error (int): Underlying low-level transceiver error code
            received_data (bytes): Raw data received during the operation
            message (str): Detail message describing the failure
        Outputs:
            None: Initializes the exception and stores transceiver_error
        """
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
        """Initializes an I2cChannelDisabledError by calling the I2cTransceiveError base with a 'Channel is disabled' message that embeds the transceiver error.

        Inputs:
            transceiver_error (int): Underlying low-level transceiver error code
            received_data (bytes): Raw data received during the operation
        Outputs:
            None: Initializes the channel-disabled exception via the base class
        """
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
        """Initializes an I2cNackError by calling the I2cTransceiveError base with a 'NACK (byte not acknowledged)' message.

        Inputs:
            transceiver_error (int): Underlying low-level transceiver error code
            received_data (bytes): Raw data received during the operation
        Outputs:
            None: Initializes the NACK exception via the base class
        """
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
        """Initializes an I2cTimeoutError by calling the I2cTransceiveError base with a 'Timeout.' message.

        Inputs:
            transceiver_error (int): Underlying low-level transceiver error code
            received_data (bytes): Raw data received during the operation
        Outputs:
            None: Initializes the timeout exception via the base class
        """
        super(I2cTimeoutError, self).__init__(
            transceiver_error,
            received_data,
            "Timeout."
        )
