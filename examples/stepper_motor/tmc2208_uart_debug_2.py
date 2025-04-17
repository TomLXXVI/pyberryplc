from pyberryplc.stepper.stepper_uart import TMC2208UART


def test():
    with TMC2208UART(port="/dev/ttyAMA0") as uart:
        print("first read: ")
        uart.read_register("CHOPCONF")
        print("second read: ")
        uart.read_register("CHOPCONF")
        print("first do_single_step: ")
        uart.update_register("CHOPCONF", {"toff": 3})
        print("second do_single_step: ")
        uart.update_register("CHOPCONF", {"mres": 5})


if __name__ == '__main__':
    test()
