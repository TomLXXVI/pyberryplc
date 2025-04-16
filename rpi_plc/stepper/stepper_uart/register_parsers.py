from dataclasses import dataclass


@dataclass
class GCONFRegister:
    """
    Parsed representation of the GCONF register (0x00).
    See TMC2208 datasheet Rev. 1.13, Table 5.1.
    """

    i_scale_analog: bool         # 1 = VREF pin active, 0 = internal current control (IHOLD/IRUN)
    internal_rsense: bool        # 1 = internal Rsense, 0 = external sense resistors
    en_spreadcycle: bool         # 1 = SpreadCycle, 0 = StealthChop
    shaft: bool                  # 1 = inverse motor direction
    index_otpw: bool             # 1 = INDEX = overtemperature warning
    index_step: bool             # 1 = INDEX = step signal
    pdn_disable: bool            # 1 = PDN/UART pin is ignored
    mstep_reg_select: bool       # 1 = microstep resolution set via MSTEP register
    multistep_filt: bool         # 1 = step pulse filter enabled
    test_mode: bool              # 1 = test mode enabled (do not use!)

    def as_dict(self) -> dict[str, bool]:
        return {
            "i_scale_analog": self.i_scale_analog,
            "internal_rsense": self.internal_rsense,
            "en_spreadcycle": self.en_spreadcycle,
            "shaft": self.shaft,
            "index_otpw": self.index_otpw,
            "index_step": self.index_step,
            "pdn_disable": self.pdn_disable,
            "mstep_reg_select": self.mstep_reg_select,
            "multistep_filt": self.multistep_filt,
            "test_mode": self.test_mode,
        }


def parse_gconf(value: int) -> GCONFRegister:
    return GCONFRegister(
        i_scale_analog=bool((value >> 0) & 1),
        internal_rsense=bool((value >> 1) & 1),
        en_spreadcycle=bool((value >> 2) & 1),
        shaft=bool((value >> 3) & 1),
        index_otpw=bool((value >> 4) & 1),
        index_step=bool((value >> 5) & 1),
        pdn_disable=bool((value >> 6) & 1),
        mstep_reg_select=bool((value >> 7) & 1),
        multistep_filt=bool((value >> 8) & 1),
        test_mode=bool((value >> 9) & 1),
    )


@dataclass
class GSTATRegister:
    """
    Parsed representation of the GSTAT register (0x01).
    See TMC2208 datasheet Rev. 1.13, Table 5.1.
    """

    reset: bool                  # 1 = Reset occurred
    drv_err: bool                # 1 = Driver error (overtemperature, short circuit, etc.)
    uv_cp: bool                  # 1 = Charge pump undervoltage

    def as_dict(self) -> dict[str, bool]:
        return {
            "reset": self.reset,
            "drv_err": self.drv_err,
            "uv_cp": self.uv_cp,
        }


def parse_gstat(value: int) -> GSTATRegister:
    return GSTATRegister(
        reset=bool((value >> 0) & 1),
        drv_err=bool((value >> 1) & 1),
        uv_cp=bool((value >> 2) & 1),
    )


@dataclass
class IOINRegister:
    """
    Parsed representation of the IOIN register (0x06).
    See TMC2208 datasheet Rev. 1.13, Table 5.1.
    """

    enn: bool                   # 0 = enabled, 1 = disabled
    ms1: bool                   # MS1 pin state
    ms2: bool                   # MS2 pin state
    diag: bool                  # Diagnostic output
    pdn_uart: bool              # PDN_UART pin state
    step: bool                  # STEP input level
    sel_a: bool                 # Current step resolution A (combined with sel_b)
    dir: bool                   # Direction input
    version: int                # Bits [31:24] indicate IC version (should be 0x21 for TMC2208)

    def as_dict(self) -> dict:
        return {
            "enn": self.enn,
            "ms1": self.ms1,
            "ms2": self.ms2,
            "diag": self.diag,
            "pdn_uart": self.pdn_uart,
            "step": self.step,
            "sel_a": self.sel_a,
            "dir": self.dir,
            "version": self.version,
        }


def parse_ioin(value: int) -> IOINRegister:
    return IOINRegister(
        enn=bool((value >> 0) & 1),
        ms1=bool((value >> 2) & 1),
        ms2=bool((value >> 3) & 1),
        diag=bool((value >> 4) & 1),
        pdn_uart=bool((value >> 6) & 1),
        step=bool((value >> 7) & 1),
        sel_a=bool((value >> 8) & 1),
        dir=bool((value >> 9) & 1),
        version=(value >> 24) & 0xFF,
    )


@dataclass
class CHOPCONFRegister:
    """
    Parsed representation of the CHOPCONF register (0x6C).
    See TMC2208 datasheet Rev. 1.13, Table 5.4.1
    """

    toff: int
    hstrt: int
    hend: int
    tbl: int
    vsense: bool
    mres: int
    intpol: bool
    dedge: bool
    diss2g: bool
    diss2vs: bool

    def as_dict(self) -> dict:
        return {
            "toff": self.toff,
            "hstrt": self.hstrt,
            "hend": self.hend,
            "tbl": self.tbl,
            "vsense": self.vsense,
            "mres": self.mres,
            "intpol": self.intpol,
            "dedge": self.dedge,
            "diss2g": self.diss2g,
            "diss2vs": self.diss2vs,
        }


def parse_chopconf(value: int) -> CHOPCONFRegister:
    return CHOPCONFRegister(
        toff=(value >> 0) & 0xF,
        hstrt=(value >> 4) & 0x7,
        hend=(value >> 7) & 0xF,
        tbl=(value >> 15) & 0x3,
        vsense=bool((value >> 17) & 1),
        mres=(value >> 24) & 0xF,
        intpol=bool((value >> 28) & 1),
        dedge=bool((value >> 29) & 1),
        diss2g=bool((value >> 30) & 1),
        diss2vs=bool((value >> 31) & 1),
    )


@dataclass
class DRVSTATUSRegister:
    """
    Parsed representation of the DRV_STATUS register (0x6F).
    See TMC2208 datasheet Rev. 1.13, Table 39 (p. 35).
    """

    stst: bool         # Standstill indicator
    olb: bool          # Open load on phase B
    ola: bool          # Open load on phase A
    s2gb: bool         # Short to GND on phase B
    s2ga: bool         # Short to GND on phase A
    s2vsb: bool        # Short to supply on phase B
    s2vsa: bool        # Short to supply on phase A
    otpw: bool         # Overtemperature prewarning
    ot: bool           # Overtemperature shutdown
    cs_actual: int     # Actual current control scaler (5 bits)
    stealth: bool      # StealthChop running indicator

    def as_dict(self) -> dict:
        return {
            "stst": self.stst,
            "olb": self.olb,
            "ola": self.ola,
            "s2gb": self.s2gb,
            "s2ga": self.s2ga,
            "s2vsb": self.s2vsb,
            "s2vsa": self.s2vsa,
            "otpw": self.otpw,
            "ot": self.ot,
            "cs_actual": self.cs_actual,
            "stealth": self.stealth,
        }


def parse_drv_status(value: int) -> DRVSTATUSRegister:
    return DRVSTATUSRegister(
        stst=bool((value >> 31) & 1),
        olb=bool((value >> 7) & 1),
        ola=bool((value >> 6) & 1),
        s2gb=bool((value >> 3) & 1),
        s2ga=bool((value >> 2) & 1),
        s2vsb=bool((value >> 5) & 1),
        s2vsa=bool((value >> 4) & 1),
        otpw=bool((value >> 0) & 1),
        ot=bool((value >> 1) & 1),
        cs_actual=(value >> 16) & 0x1F,
        stealth=bool((value >> 30) & 1),
    )
