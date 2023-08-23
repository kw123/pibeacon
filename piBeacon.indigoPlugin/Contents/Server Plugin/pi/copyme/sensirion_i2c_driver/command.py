# -*- coding: utf-8 -*-
# (c) Copyright 2019 Sensirion AG, Switzerland

from __future__ import absolute_import, division, print_function


class I2cCommand(object):
    """
    Base class for all I²C commands.
    """

    def __init__(self, tx_data, rx_length, read_delay, timeout,
                 post_processing_time=0.0):
        """
        Constructs a new I²C command.

        :param bytes-like/list/None tx_data:
            Bytes to be sent to the I²C device. None means that no write header
            will be sent at all. An empty list/bytes object means to send the
            write header, but without data following it.
        :param int/None rx_length:
            Number of bytes to be read from the I²C device. None means that no
            read header is sent at all. Zero means to send the read header,
            but without reading any data.
        :param float read_delay:
            Delay (in Seconds) to be inserted between the end of the write
            operation and the beginning of the read operation. This is needed
            if the device needs some time to prepare the RX data, e.g. if it
            has to perform a measurement. Set to 0.0 to indicate that no delay
            is needed, i.e. the device does not need any processing time.
        :param float timeout:
            Timeout (in Seconds) to be used in case of clock stretching. If the
            device stretches the clock longer than this value, the transceive
            operation will be aborted with a timeout error. Set to 0.0 to
            indicate that the device will not stretch the clock for this
            command.
        :param float post_processing_time:
            Maximum time in seconds the device needs for post processing of
            this command until it is ready to receive the next command. For
            example after a device reset command, the device might need some
            time until it is ready again. Usually this is 0.0s, i.e. no post
            processing is needed.
        """
        super(I2cCommand, self).__init__()

        #: The data bytes to be send to the device (bytes/None).
        # Note: Typecasts are needed to allow arbitrary iterables.
        self.tx_data = bytes(bytearray(tx_data)) \
            if tx_data is not None else None

        #: Number of bytes to be read from the device (int/None).
        self.rx_length = int(rx_length) if rx_length is not None else None

        #: Delay in Seconds between write and read operation (float).
        self.read_delay = float(read_delay)

        #: Timeout in Seconds for clock stretching (float).
        self.timeout = float(timeout)

        #: Time in Seconds how long the post processing takes (float).
        self.post_processing_time = float(post_processing_time)

    def interpret_response(self, data):
        """
        Interprets the raw response from the device and returns it in the
        proper data type.

        .. note:: This implementation returns the data as-is, or as None if
                  there is no data received. Derived classes may override this
                  method to convert the data to the proper data types.

        :param bytes data:
            Received raw bytes from the read operation.
        :return:
            The received raw bytes, or None if there is no data received.
        :rtype:
            bytes or None
        """
        return data if len(data) > 0 else None
