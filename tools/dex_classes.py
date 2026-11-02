"""Read standard DEX class definitions for cross-DEX duplicate checks."""
import struct

def class_descriptors(data):
    if not data.startswith(b'dex\n') or len(data) < 112:
        raise ValueError('Not a standard DEX file')
    def word(offset):
        return struct.unpack_from('<I', data, offset)[0]
    strings, strings_off = word(0x38), word(0x3c)
    types, types_off = word(0x40), word(0x44)
    classes, classes_off = word(0x60), word(0x64)
    for count, offset, stride in [(strings, strings_off, 4), (types, types_off, 4), (classes, classes_off, 32)]:
        if offset + count * stride > len(data):
            raise ValueError('DEX table exceeds file size')
    result = []
    for index in range(classes):
        type_index = word(classes_off + index * 32)
        if type_index >= types:
            raise ValueError('Invalid class type index')
        string_index = word(types_off + type_index * 4)
        if string_index >= strings:
            raise ValueError('Invalid type string index')
        position = word(strings_off + string_index * 4)
        for _ in range(5):
            if position >= len(data):
                raise ValueError('Invalid string offset')
            value = data[position]; position += 1
            if value < 128:
                break
        else:
            raise ValueError('Invalid string length')
        end = data.find(b'\0', position)
        if end < 0:
            raise ValueError('Unterminated descriptor')
        result.append(data[position:end].decode('utf-8', errors='replace'))
    return result
