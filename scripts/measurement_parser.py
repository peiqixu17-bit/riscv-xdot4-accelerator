"""Parse the frozen harness: result is unprefixed hexadecimal; counters decimal."""
import re

def parse_measurement(line):
    tokens=line.split()
    if not tokens or tokens[0]!='MEASURE':
        raise ValueError('Expected MEASURE line')
    values={}
    for token in tokens[1:]:
        match=re.fullmatch(r'([A-Za-z_][A-Za-z_0-9]*)=(\S+)',token)
        if not match:
            raise ValueError('Malformed measurement field')
        key,value=match.groups()
        if key in values:
            raise ValueError('Duplicate measurement field: '+key)
        pattern=r'[0-9a-fA-F]{1,8}' if key=='result' else r'[0-9]+'
        if not re.fullmatch(pattern,value):
            raise ValueError('Malformed measurement value: '+key)
        values[key]=int(value,16 if key=='result' else 10)
    if not {'raw_cycles','kernel_cycles','result'}<=values.keys():
        raise ValueError('Required measurement fields missing')
    return values

def require_result(actual_u32,expected):
    if not 0<=actual_u32<=0xffffffff or not -(1<<31)<=expected<=0xffffffff:
        raise ValueError('Result outside 32-bit representation')
    if actual_u32 != (expected & 0xffffffff):
        raise ValueError(f'Result mismatch: actual={actual_u32:08x}, expected={expected & 0xffffffff:08x}')
