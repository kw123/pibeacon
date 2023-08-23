# -*- coding: utf-8 -*-
# (c) Copyright 2019 Sensirion AG, Switzerland

from __future__ import absolute_import, division, print_function

import logging
log = logging.getLogger(__name__)


class I2cTransceiverV1(object):
    """
    Interface to be implemented by every I²C transceiver with API version 1.
    """

    API_VERSION = 1  #: API version (accessed by I2cConnection)

    # Status codes
    STATUS_OK = 0  #: Status code for "transceive operation succeeded".
    STATUS_CHANNEL_DISABLED = 1  #: Status code for "channel disabled error".
    STATUS_NACK = 2  #: Status code for "not acknowledged error".
    STATUS_TIMEOUT = 3  #: Status code for "timeout error".
    STATUS_UNSPECIFIED_ERROR = 4  #: Status code for "unspecified error".

    def __init__(self):
        super(I2cTransceiverV1, self).__init__()

    @property
    def description(self):
        """
        Description of the transceiver (for logging/debugging purposes).
        Should be a short one-line string.

        :return: Description.
        :rtype: str
        """
        return ""

    @property
    def channel_count(self):
        """
        Channel count of this transceiver. This is needed by
        :py:class:`~sensirion_i2c_driver.connection.I2cConnection` to determine
        whether this is a single-channel or multi-channel transceiver, and how
        many channels it has (in case of multi-channel).

        :return:
            The channel count if it's a multi-channel transceiver, or None if
            it's a single-channel transceiver.
        :rtype: int/None
        """
        return None

    def transceive(self, slave_address, tx_data, rx_length, read_delay,
                   timeout):
        """
        Transceive an I²C frame synchronously.

        :param byte slave_address:
            The I²C address of the slave to communicate with.
        :param bytes/None tx_data:
            The data to send. If empty, only the write header (without data) is
            sent. If None, no write header is sent at all.
        :param int/None rx_length:
            Number of bytes to read. If zero, only the read header is sent,
            without reading any data. If None, no read header is sent at all.
        :param float read_delay:
            Delay before sending the read header in Seconds.
        :param float timeout:
            Timeout (for clock stretching) in Seconds. If the clock gets
            stretched longer than this time, the transceive operation is
            aborted with timeout error.
        :return:
            - A status code of the transceive operation
            - In case of errors, the underlying (transceiver-dependent)
              exception
            - The received data from the read operation
        :rtype:
            - If single-channel: tuple(int, Exception, bytes)
            - If multi-channel: list(tuple(int, Exception, bytes))
        :raises:
            Only raises a (transceiver-specific) exception if the operation
            could not be executed at all. If the operation was executed but
            failed with NACK or timeout, no exception is raised. These errors
            are reported by the returned status code instead.
        """
        assert type(slave_address) is int
        assert (tx_data is None) or (type(tx_data) is bytes)
        assert (rx_length is None) or (type(rx_length) is int)
        assert type(read_delay) in [float, int]
        assert type(timeout) in [float, int]
        raise NotImplementedError()
