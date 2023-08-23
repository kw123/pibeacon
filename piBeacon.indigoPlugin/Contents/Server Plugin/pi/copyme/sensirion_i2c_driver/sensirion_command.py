# -*- coding: utf-8 -*-
# (c) Copyright 2019 Sensirion AG, Switzerland

from __future__ import absolute_import, division, print_function
from .command import I2cCommand
from .errors import I2cChecksumError
from struct import pack


class SensirionI2cCommand(I2cCommand):
    """
    Base class for Sensirion-specific I²C commands as used in most Sensirion
    sensor devices. This class extends the base class
    :py:class:`~sensirion_i2c_driver.command.I2cCommand` with following
    functionality:

    - Splitting TX data into command ID and payload data
    - Transparently inserts CRCs into TX data after every 2nd payload byte
    - Transparently verifies and removes CRCs from RX data after every 2nd byte
    """

    def __init__(self, command, tx_data, rx_length, read_delay, timeout, crc,
                 command_bytes=2, post_processing_time=0.0):
        """
        Constructs a new Sensirion I²C command.

        :param int/None command:
            The command ID to be sent to the device. None means that no
            command will be sent, i.e. only ``tx_data`` (if not None) will
            be sent. No CRC is added to these bytes since the command ID
            usually already contains a CRC.
        :param bytes-like/list/None tx_data:
            Bytes to be extended with CRCs and then sent to the I²C device.
            None means that no write header will be sent at all (if ``command``
            is None too). An empty list means to send the write header (even if
            ``command`` is None), but without data following it.
        :param int/None rx_length:
            Number of bytes to be read from the I²C device, including CRC
            bytes. None means that no read header is sent at all. Zero means
            to send the read header, but without reading any data.
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
        :param calleable crc:
            A :py:class:`~sensirion_i2c_driver.crc_calculator.CrcCalculator`
            object to calculate the CRC of the transceived data, or any other
            calleable object or function which takes a bytearray as parameter
            and returns its CRC as an integer. If the command does not contain
            CRC bytes, pass None to disable it.
        :param int command_bytes:
            Number of command bytes. Most Sensirion sensors use a 2-byte
            command (thus it is the default), but there are also sensors using
            only one byte for the command.
        :param float post_processing_time:
            Maximum time in seconds the device needs for post processing of
            this command until it is ready to receive the next command. For
            example after a device reset command, the device might need some
            time until it is ready again. Usually this is 0.0s, i.e. no post
            processing is needed.
        """
        super(SensirionI2cCommand, self).__init__(
            tx_data=self._build_tx_data(command, command_bytes, tx_data, crc),
            rx_length=rx_length,
            read_delay=read_delay,
            timeout=timeout,
            post_processing_time=post_processing_time,
        )
        self._crc = crc

    def interpret_response(self, data):
        """
        Validates the CRCs of the received data from the device and returns
        the data with all CRCs removed.

        :param bytes data:
            Received raw bytes from the read operation.
        :return:
            The received bytes, or None if there is no data received.
        :rtype:
            bytes or None
        :raise ~sensirion_i2c_driver.errors.I2cChecksumError:
            If a received CRC was wrong.
        """
        if self._crc is None:
            return data  # data does not contain CRCs -> return it as-is

        data = bytearray(data)  # Python 2 compatibility
        data_without_crc = bytearray()
        for i in range(len(data)):
            if i % 3 == 2:
                received_crc = data[i]
                expected_crc = self._crc(data[i-2:i])
                if received_crc != expected_crc:
                    raise I2cChecksumError(received_crc, expected_crc, data)
            else:
                data_without_crc.append(data[i])
        return bytes(data_without_crc) if len(data_without_crc) else None

    @staticmethod
    def _build_tx_data(command, command_bytes, tx_data, crc):
        """
        Build the raw bytes to send from given command and TX data.

        :param command: See
            :py:meth:`~sensirion_i2c_driver.sensirion_command.SensirionI2cCommand.__init__`.
        :param command_bytes: See
            :py:meth:`~sensirion_i2c_driver.sensirion_command.SensirionI2cCommand.__init__`.
        :param tx_data: See
            :py:meth:`~sensirion_i2c_driver.sensirion_command.SensirionI2cCommand.__init__`.
        :param crc: See
            :py:meth:`~sensirion_i2c_driver.sensirion_command.SensirionI2cCommand.__init__`.
        :return:
            The raw bytes to send, or None if no write header is needed.
        :rtype:
            bytearray/None
        """
        if (command is None) and (tx_data is None):
            return None
        command_pack_format = {
            1: ">B",
            2: ">H",
        }
        data = bytearray(pack(command_pack_format[command_bytes], command)
                         if command is not None else b"")
        tx_data = bytearray(tx_data or [])  # Python 2 compatibility
        for i in range(len(tx_data)):
            data.append(tx_data[i])
            if (crc is not None) and (i % 2 == 1):
                data.append(crc(tx_data[i-1:i+1]))
        return data
