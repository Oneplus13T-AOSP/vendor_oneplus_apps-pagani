"""Remove explicitly pinned AXML nodes without recompiling resources."""
import struct

def filter_manifest(data, config):
    libraries = set(config.get('manifest_remove_uses_libraries', []))
    components = set(config.get('manifest_remove_services', []))
    if not libraries and not components:
        return data
    kind, header, size = struct.unpack_from('<HHI', data)
    assert kind == 3 and size == len(data) and header == 8
    strings = None
    chunks = []
    removed = []
    depth = 0
    skip_depth = None
    pos = header
    def length8(buf, at):
        v = buf[at]
        return (((v & 127) << 8) | buf[at+1], at+2) if v & 128 else (v, at+1)
    while pos < len(data):
        typ, hs, n = struct.unpack_from('<HHI', data, pos)
        assert n >= hs >= 8 and pos+n <= len(data)
        chunk = data[pos:pos+n]
        if typ == 1:
            count, styles, flags, start, style_start = struct.unpack_from('<5I', chunk, 8)
            strings = []
            for i in range(count):
                at = start + struct.unpack_from('<I', chunk, hs+4*i)[0]
                if flags & 0x100:
                    _, at = length8(chunk, at)
                    length, at = length8(chunk, at)
                    strings.append(chunk[at:at+length].decode('utf-8'))
                else:
                    length = struct.unpack_from('<H', chunk, at)[0]; at += 2
                    if length & 0x8000:
                        length = ((length & 0x7fff) << 16) | struct.unpack_from('<H', chunk, at)[0]; at += 2
                    strings.append(chunk[at:at+2*length].decode('utf-16le'))
        if typ == 0x102:
            assert strings is not None
            name_index = struct.unpack_from('<I', chunk, hs+4)[0]
            attr_start, attr_size, attr_count = struct.unpack_from('<3H', chunk, hs+8)
            tag = strings[name_index]
            node_name = None
            for i in range(attr_count):
                at = hs+attr_start+i*attr_size
                ns, key, raw = struct.unpack_from('<3I', chunk, at)
                if strings[key] == 'name' and ns != 0xffffffff and strings[ns] == 'http://schemas.android.com/apk/res/android':
                    if raw != 0xffffffff:
                        node_name = strings[raw]
                    elif chunk[at+15] == 3:
                        node_name = strings[struct.unpack_from('<I', chunk, at+16)[0]]
            if skip_depth is None and ((tag == 'uses-library' and node_name in libraries) or
                                       (tag == 'service' and node_name in components)):
                skip_depth = depth
                removed.append(node_name)
            depth += 1
        keep = skip_depth is None
        if typ == 0x103:
            depth -= 1
            if skip_depth is not None and depth == skip_depth:
                skip_depth = None
        if keep:
            chunks.append(chunk)
        pos += n
    assert depth == 0 and skip_depth is None
    assert sorted(removed) == sorted(libraries | components), (removed, libraries, components)
    payload = b''.join(chunks)
    return struct.pack('<HHI', 3, 8, 8+len(payload)) + payload
