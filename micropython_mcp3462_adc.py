# MIT license; Copyright (c) 2021, Planet Innovation
# 436 Elgar Road, Box Hill, 3128, VIC, Australia
# Phone: +61 3 9945 7510
#

from micropython import const

# CONFIG registers
_CMD_ADDR_POS = const(6)
_CMD_CONV_START = const(0b1010_00)
_CMD_FULL_RESET = const(0b1110_00)
_CMD_INC_WRITE = const(0b10)
_CMD_INC_READ = const(0b11)

_REG_ADCDATA = const(0)
_REG_IRQ = const(5)
_REG_MUX = const(6)

_CH_AGND = const(0b1000)
_EN_STP_POS = const(0x1)


class MCP3462:
    """MCP3462 driver."""

    def __init__(self, spi, cs, irq, addr):
        """
        Initialise the driver with:
            - spi: the SPI bus the ADC is on
            - cs: the chip-select pin
            - irq: the IRQ pin
            - addr: the 2 address bits for the MCP3462
        """
        cs.init(cs.OUT, value=1)
        irq.init(irq.IN, irq.PULL_UP)
        self.spi = spi
        self.chip_select = cs
        self.irq = irq
        self.cmd_addr = addr << _CMD_ADDR_POS
        self.buf1 = bytearray(1)
        self.buf2 = bytearray(2)
        self.buf3 = bytearray(3)
        self.reset()

    def _fast_command(self, cmd):
        """Send a fast command to the ADC."""
        buf = self.buf1
        buf[0] = self.cmd_addr | cmd
        self.chip_select(0)
        self.spi.write(buf)
        self.chip_select(1)

    def _write_reg8(self, addr, value):
        """Write an 8-bit register in the ADC."""
        buf = self.buf2
        buf[0] = self.cmd_addr | addr << 2 | _CMD_INC_WRITE
        buf[1] = value
        self.chip_select(0)
        self.spi.write(buf)
        self.chip_select(1)

    def _read_reg8(self, addr):
        """Read an 8-bit register from the ADC, returning an integer."""
        buf = self.buf2
        buf[0] = self.cmd_addr | addr << 2 | _CMD_INC_READ
        self.chip_select(0)
        self.spi.write_readinto(buf, buf)
        self.chip_select(1)
        return buf[1]

    def _read_reg16(self, addr):
        """Read a 16-bit register from the ADC, returning an integer."""
        buf = self.buf3
        buf[0] = self.cmd_addr | addr << 2 | _CMD_INC_READ
        self.chip_select(0)
        self.spi.write_readinto(buf, buf)
        self.chip_select(1)
        return buf[2] | buf[1] << 8

    def reset(self):
        """Reset the ADC."""
        self._fast_command(_CMD_FULL_RESET)
        # Ensure the IRQ register EN_STP (conversion start interrupt) feature is disabled (zero)
        self._write_reg8(_REG_IRQ, self._read_reg8(_REG_IRQ) & ~_EN_STP_POS)

    def convert(self, channel):
        """Begin ADC conversion on the given channel."""
        self._write_reg8(_REG_MUX, channel << 4 | _CH_AGND)
        self._fast_command(_CMD_CONV_START)

    def read_data_s16(self):
        """Read the converted ADC data value."""
        value = self._read_reg16(_REG_ADCDATA)
        if value & 0x8000:
            value -= 0x10000
        return value

    def data_ready(self):
        """Check if there is new data in the ADC data register."""
        return not self.irq()
