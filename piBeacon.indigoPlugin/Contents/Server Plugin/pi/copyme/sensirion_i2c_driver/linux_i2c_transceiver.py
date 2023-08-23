# -*- coding: utf-8 -*-
# (c) Copyright 2019 Sensirion AG, Switzerland

from __future__ import absolute_import, division, print_function
import time
import os

import logging
log = logging.getLogger(__name__)


class LinuxI2cTransceiver(object):
    """
    Transceiver for the Linux I²C kernel driver, for example to use the I²C
    pins of a Raspberry Pi.

    .. note:: This class can be used in a "with"-statement, and it's
              recommended to do so as it automatically closes the device file
              after using it.
    """

    API_VERSION = 1  #: API version (accessed by I2cConnection)

    # Status codes
    STATUS_OK = 0  #: Status code for "transceive operation succeeded".
    STATUS_CHANNEL_DISABLED = 1  #: Status code for "channel disabled error".
    STATUS_NACK = 2  #: Status code for "not acknowledged error".
    STATUS_TIMEOUT = 3  #: Status code for "timeout error".
    STATUS_UNSPECIFIED_ERROR = 4  #: Status code for "unspecified error".

    def __init__(self, device_file, do_open=True):
        """
        Create a transceiver for a given I²C device file and (optionally) open
        it for read/write access.

        :param str device_file:
            Path to the I²C device file, for example "/dev/i2c-1".
        :param bool do_open:
            Whether the file should be opened immediately or not. If ``False``,
            you will have to call
            :py:meth:`~sensirion_i2c_driver.linux_i2c_transceiver.LinuxI2cTransceiver.open`
            manually before using the transceiver. Defaults to ``True``.
        """
        super(LinuxI2cTransceiver, self).__init__()
        self._device_file = device_file
        self._file_descriptor = None
        if do_open:
            self.open()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def open(self):
        """
        Open the I²C port (only needs to be called if ``do_open`` in
        :py:meth:`~sensirion_i2c_driver.linux_i2c_transceiver.LinuxI2cTransceiver.__init__`
        was set to ``False``.
        """
        self._file_descriptor = os.open(self._device_file, os.O_RDWR)

    def close(self):
        """
        Close (release) the device file.
        """
        os.close(self._file_descriptor)
        self._file_descriptor = None

    @property
    def description(self):
        """
        Description of the transceiver.

        For details (e.g. return value documentation), please refer to
        :py:attr:`~sensirion_i2c_driver.transceiver_v1.I2cTransceiverV1.description`.
        """
        return str(self._device_file)

    @property
    def channel_count(self):
        """
        Channel count of this transceiver.

        For details (e.g. return value documentation), please refer to
        :py:attr:`~sensirion_i2c_driver.transceiver_v1.I2cTransceiverV1.channel_count`.
        """
        return None  # single channel transceiver

    def transceive(self, slave_address, tx_data, rx_length, read_delay,
                   timeout):
        """
        Transceive an I²C frame in single-channel mode.

        For details (e.g. parameter documentation), please refer to
        :py:meth:`~sensirion_i2c_driver.transceiver_v1.I2cTransceiverV1.transceive`.

        .. note::  The ``timeout`` parameter is not supported (i.e. ignored)
                   since we can't specify the clock stretching timeout. It
                   depends on the underlying hardware whether clock stretching
                   is supported at all or not, and what timeout value is used.
        """
        assert type(slave_address) is int
        assert (tx_data is None) or (type(tx_data) is bytes)
        assert (rx_length is None) or (type(rx_length) is int)
        assert type(read_delay) in [float, int]
        assert type(timeout) in [float, int]

        # Delayed import to avoid errors when importing this module on Windows
        from fcntl import ioctl

        status = self.STATUS_OK
        error = None
        rx_data = b""

        # Set address
        # See https://www.kernel.org/doc/html/latest/i2c/dev-interface.html
        ioctl(self._file_descriptor, 0x0703, slave_address)

        # I2C Write
        if tx_data is not None:
            try:
                os.write(self._file_descriptor, tx_data)
            except OSError as e:
                status = self.STATUS_UNSPECIFIED_ERROR
                error = e

        # Since we use separate commands for write and read, we have to
        # implement the read delay in software
        if read_delay > 0:
            time.sleep(read_delay)

        # I2C Read
        if (rx_length is not None) and (status == self.STATUS_OK):
            try:
                rx_data = os.read(self._file_descriptor, rx_length)
            except OSError as e:
                status = self.STATUS_UNSPECIFIED_ERROR
                error = e

        return status, error, rx_data
