import ctypes
import ctypes.util

libc_name = ctypes.util.find_library('c')
print(f"libc_name: {libc_name}")

if libc_name is None:
    raise Exception("Could not find libc")

libc = ctypes.CDLL(libc_name)
print(libc)
