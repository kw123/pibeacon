# -*- coding: utf-8 -*-
# (c) Copyright 2019 Sensirion AG, Switzerland

from __future__ import absolute_import, division, print_function


class I2cDevice(object):
    """
    Base class for all I²C devices. Users should inherit from this class when
    implementing new I²C device drivers.

    The most important functionality of this class is the convenience method
    :py:meth:`~sensirion_i2c_driver.device.I2cDevice.execute` which allows
    derived classes to easily execute an
    :py:class:`~sensirion_i2c_driver.command.I2cCommand` object.
    """
    def __init__(self, connection, slave_address):
        """
        Create an I²C device instance on a given connection.

        :param ~sensirion_i2c_driver.connection.I2cConnection connection:
            The I²C connection used to execute the commands.
        :param byte slave_address:
            The I²C slave address of the device.
        """
        super(I2cDevice, self).__init__()
        self._connection = connection
        self._slave_address = slave_address

    @property
    def connection(self):
        """
        Get the used I²C connection.

        :return: The used I²C connection.
        :rtype: ~sensirion_i2c_driver.connection.I2cConnection
        """
        return self._connection

    @property
    def slave_address(self):
        """
        Get the I²C slave address.

        :return: The I²C slave address.
        :rtype: byte
        """
        return self._slave_address

    def execute(self, command):
        """
        Execute an I²C command on this device.

        :param ~sensirion_i2c_driver.command.I2cCommand command:
            The command to be executed.
        :return:
            The interpreted response of the executed command.
        :rtype:
            Depends on the executed command.
        """
        return self._connection.execute(self._slave_address, command)
