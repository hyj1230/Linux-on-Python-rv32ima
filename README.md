# Linux-on-Python-rv32ima
Run Linux on Python with RISC-V emulator（使用RISC-V模拟器在Python上运行Linux）

### Project Description
Linux-on-Python-rv32ima is a software emulator that implements the rv32ima RISC-V instruction set architecture entirely in Python. The emulator:

- Executes RISC-V 32-bit instructions (Integer, Multiplication, Atomic extensions)
- Emulates 64MB of physical RAM
- Provides essential peripherals: UART (console I/O), CLINT (timer/interrupts), SYSCON (power control)
- Boots a pre-compiled Linux kernel and root filesystem from `Linux.image`
- Supports interactive console operation on Windows, Linux, and macOS host systems
This is an educational and experimental platform that prioritizes code readability and accessibility over raw performance. The entire emulator core resides in a single Python file with minimal dependencies.

### Starting the Emulator（启动模拟器）
To run the emulator, execute `single.py` directly with Python3/PyPy3:
```sh
python single.py
```
```sh
pypy single.py
```

You can also run the equivalent multi-file version of the code.
```sh
python multiple_src/main.py
```
```sh
pypy multiple_src/main.py
```

### Screenshot
![](emulator_screenshot.png)
