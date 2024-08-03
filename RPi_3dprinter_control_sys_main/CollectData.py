import time
from smbus2 import SMBus, i2c_msg
from struct import unpack
from multiprocessing import Process, Pipe

def CrcCalculator(data):
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
    width = 8
    polynomial = 0x31
    final_xor = 0x00
    crc = 0xFF
    for value in data:
        crc ^= value
        for i in range(width):
            if crc & (1 << (width - 1)):
                crc = (crc << 1) ^ polynomial
            else:
                crc = crc << 1
            crc &= (1 << width) - 1
    return crc ^ final_xor


def sendData(child_conn, temp, VOC, humidity, nox):
    child_conn.send([temp, VOC, humidity, nox])

def collectData(child_conn):
    # I2C bus 1 on a Raspberry Pi 3B+
    # SDA on GPIO2=Pin3 and SCL on GPIO3=Pin5
    #   sensor +3.3V at Pin1 and GND at Pin6
    DEVICE_BUS = 1

    # device address SEN55
    DEVICE_ADDR = 0x69
    # init I2C
    bus = SMBus(DEVICE_BUS)

    # wait 1 s for sensor start up (> 1000 ms according to datasheet)
    time.sleep(1)

    #Read status of the STAR engine
    msg = i2c_msg.write(DEVICE_ADDR, [0x60, 0xB2])
    bus.i2c_rdwr(msg)

    # wait 10 ms for data ready
    time.sleep(0.01)

    # read 9 bytes in as a sequence of MSB, LSB, CRC
    # offset, slope. time constant
    msg = i2c_msg.read(DEVICE_ADDR, 9)
    bus.i2c_rdwr(msg)

    # merge byte 0 and byte 1 to integer
    t_offset  = int(unpack(">h", msg.buf[0:2])[0]) #different method choosen here due to the possible negative sign in parameter
    t_slope  = (msg.buf[3][0] << 8 | msg.buf[4][0])
    t_time  = (msg.buf[6][0] << 8 | msg.buf[7][0])

    # wait 10 ms for data ready
    time.sleep(0.01)

    #Set new values:
    t_offset = int(-5 * 200)
    t_slope = int(0.01 * 10000)
    t_time = int(10 * 60)

    data = []
    data.append((t_offset & 0xff00) >> 8)
    data.append(t_offset & 0x00ff)

    data.append((t_slope & 0xff00) >> 8)
    data.append(t_slope & 0x00ff)

    data.append((t_time & 0xff00) >> 8)
    data.append(t_time & 0x00ff)

    msg = i2c_msg.write(
        DEVICE_ADDR,
        [0x60, 0xB2,
        data[0], data[1], CrcCalculator(data[0:2]),
        data[2], data[3], CrcCalculator(data[2:4]),
        data[4], data[5], CrcCalculator(data[4:6])]
    )
    bus.i2c_rdwr(msg)

    # wait 10 ms for data ready
    time.sleep(0.01)

    #Read status of the STAR engine
    msg = i2c_msg.write(DEVICE_ADDR, [0x60, 0xB2])
    bus.i2c_rdwr(msg)

    # wait 10 ms for data ready
    time.sleep(0.01)

    # read 3 bytes in as a sequence of MSB, LSB, CRC
    # status
    msg = i2c_msg.read(DEVICE_ADDR, 9)
    bus.i2c_rdwr(msg)

    # merge byte 0 and byte 1 to integer
    t_offset = int(unpack(">h", msg.buf[0:2])[0]) #different method choosen here due to the possible negative sign in parameter
    t_slope = (msg.buf[3][0] << 8 | msg.buf[4][0])
    t_time = (msg.buf[6][0] << 8 | msg.buf[7][0])

    # wait 10 ms for data ready
    time.sleep(0.01)

    # start scd measurement in periodic mode, will update every 2 s
    msg = i2c_msg.write(DEVICE_ADDR, [0x00, 0x21])
    bus.i2c_rdwr(msg)

    # wait for first measurement to be finished
    time.sleep(2)

    # repeat read out of sensor data
    while True:
        msg = i2c_msg.write(DEVICE_ADDR, [0x03, 0xC4])
        bus.i2c_rdwr(msg)

        # wait 1 ms for data ready
        time.sleep(0.01)

        # read 12 bytes; each three bytes in as a sequence of MSB, LSB, CRC
        # co2, temperature, rel. humidity, status
        msg = i2c_msg.read(DEVICE_ADDR, 24)
        bus.i2c_rdwr(msg)

        # merge byte 0 and byte 1 to integer
        # co2 is in ppm
        pm1p0 = (msg.buf[0][0] << 8 | msg.buf[1][0])/10
        pm2p5 = (msg.buf[3][0] << 8 | msg.buf[4][0])/10
        pm4p0 = (msg.buf[6][0] << 8 | msg.buf[7][0])/10
        pm10p0 = (msg.buf[9][0] << 8 | msg.buf[10][0])/10

        # merge byte 3 and byte 4 to integer
        temp = msg.buf[15][0] << 8 | msg.buf[16][0]
        # calculate temperature  according to datasheet
        temp /= 200

        # merge byte 6 and byte 7 to integer
        humidity = msg.buf[12][0] << 8 | msg.buf[13][0]
        # calculate relative humidity according to datasheet
        humidity /= 100

        VOC = (msg.buf[18][0] << 8 | msg.buf[19][0]) / 10
        nox = (msg.buf[21][0] << 8 | msg.buf[22][0]) / 10
        
        sendData(child_conn, temp, VOC, humidity, nox)
        
        # print(VOC)
        # print(temp)
        # wait 2 s for next measurement
        time.sleep(2)
    
    child_conn.close()
    bus.close()
