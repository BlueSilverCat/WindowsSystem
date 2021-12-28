import winreg
import time
import datetime
import collections
import os.path
import re

Entry = {
  winreg.HKEY_CLASSES_ROOT: "HKEY_CLASSES_ROOT",
  winreg.HKEY_CURRENT_USER: "HKEY_CURRENT_USER",
  winreg.HKEY_LOCAL_MACHINE: "HKEY_LOCAL_MACHINE",
  winreg.HKEY_USERS: "HKEY_USERS",
  winreg.HKEY_PERFORMANCE_DATA: "HKEY_PERFORMANCE_DATA",
  winreg.HKEY_CURRENT_CONFIG: "HKEY_CURRENT_CONFIG",
}

# 手作業でなくてzipで処理しても良い
Type = {
  winreg.REG_BINARY: "REG_BINARY",  # winreg.REG_BINARY 何らかの形式のバイナリデータ。
  winreg.REG_DWORD: "REG_DWORD",  # winreg.REG_DWORD 32 ビットの数。
  winreg.REG_DWORD_LITTLE_ENDIAN: "REG_DWORD_LITTLE_ENDIAN",  # winreg.REG_DWORD_LITTLE_ENDIAN 32 ビットのリトルエンディアン形式の数。REG_DWORD と等価。
  winreg.REG_DWORD_BIG_ENDIAN: "REG_DWORD_BIG_ENDIAN",  # winreg.REG_DWORD_BIG_ENDIAN 32 ビットのビッグエンディアン形式の数。
  winreg.REG_EXPAND_SZ: "REG_EXPAND_SZ",  # winreg.REG_EXPAND_SZ 環境変数を参照している、ヌル文字で終端された文字列。(%PATH%)。
  winreg.REG_LINK: "REG_LINK",  # winreg.REG_LINK Unicode のシンボリックリンク。
  winreg.REG_MULTI_SZ: "REG_MULTI_SZ",  # winreg.REG_MULTI_SZ ヌル文字で終端された文字列からなり、二つのヌル文字で終端されている配列。 (Python はこの終端の処理を自動的に行います。)
  winreg.REG_NONE: "REG_NONE",  # winreg.REG_NONE 定義されていない値の形式。
  winreg.REG_QWORD: "REG_QWORD",  # winreg.REG_QWORD 64 ビットの数。
  winreg.REG_QWORD_LITTLE_ENDIAN: "REG_QWORD_LITTLE_ENDIAN",  # winreg.REG_QWORD_LITTLE_ENDIAN 64 ビットのリトルエンディアン形式の数。REG_QWORD と等価。
  winreg.REG_RESOURCE_LIST: "REG_RESOURCE_LIST",  # winreg.REG_RESOURCE_LIST デバイスドライバリソースのリスト。
  winreg.REG_FULL_RESOURCE_DESCRIPTOR: "REG_FULL_RESOURCE_DESCRIPTOR",  # winreg.REG_FULL_RESOURCE_DESCRIPTOR ハードウェアセッティング。
  winreg.REG_RESOURCE_REQUIREMENTS_LIST: "REG_RESOURCE_REQUIREMENTS_LIST",  # winreg.REG_RESOURCE_REQUIREMENTS_LIST ハードウェアリソースリスト。
  winreg.REG_SZ: "REG_SZ",  # winreg.REG_SZ ヌル文字で終端された文字列。
}


def getZeroFillString(i, num=100):
  length = len(str(num))
  return str(i).zfill(length)


def getDate(t):
  windowsEpoch = time.strptime("1601-01-01 00:00:00", "%Y-%m-%d %H:%M:%S")
  windowsEpoch = datetime.datetime(*windowsEpoch[:6])
  epoch = time.gmtime(0)
  epoch = datetime.datetime(*epoch[:6])
  t = time.localtime(t * 10e-8)
  t = datetime.datetime(*t[:6])
  return t - (epoch - windowsEpoch)


def join(x, y):
  if x != "":
    return f"{x}\\{y}"
  return y


def removeUnicodeErrorForWindows(string):
  return str(string).encode("cp932", "namereplace").decode("cp932")


def printForWindows(string):
  print(removeUnicodeErrorForWindows(string))


RegistryValue = collections.namedtuple("RegistryValue", "name data type")


class Registry():

  def __init__(self, key, subKey, depth=0, index=0, maxIndex=0, isRoot=True):
    self.keyRoot = key
    self.subKey = subKey
    self.depth = depth  # 表示のためのメンバ。親から見ての階層
    self.index = index  # 表示のためのメンバ。親から見てindex番目のsubKey
    self.maxIndex = maxIndex  # 表示のためのメンバ。親のsubKeyの個数
    self.values = []
    self.valueNum = 0
    self.subKeys = []
    self.subKeyNum = 0
    self.modifiedDate = ""
    self.isRoot = isRoot
    self.init()

  def __repr__(self):
    return f"{self.getKeyString()}: {self.subKeyNum}, {self.valueNum}, {self.modifiedDate}"

  def open(self):
    try:
      key = winreg.OpenKey(self.keyRoot, self.subKey, access=winreg.KEY_READ)
    except FileNotFoundError:
      try:
        key = winreg.OpenKey(self.keyRoot, self.subKey, access=winreg.KEY_READ | winreg.KEY_WOW64_32KEY)  # 64bitのOSで動かすことを前提として、32bitのkeyを表示させる処理
      except FileNotFoundError:
        print(self.getKeyString())
        raise
    return key

  def init(self):
    with self.open() as key:
      self.setQueryInfo(key)
      self.setValues(key)
      self.setSubKeyString(key)
    if self.isRoot:  # ここの仕組みが気に入らない
      self.setSubKey()

  def setQueryInfo(self, key):
    info = winreg.QueryInfoKey(key)
    self.subKeyNum = info[0]
    self.valueNum = info[1]
    self.modifiedDate = getDate(info[2])

  def setValues(self, key):
    self.values = [RegistryValue(*winreg.EnumValue(key, i)) for i in range(self.valueNum)]

  def setSubKeyString(self, key):
    self.subKeys = []
    for i in range(self.subKeyNum):
      subKey = winreg.EnumKey(key, i)
      self.subKeys.append(subKey)
      # reg = Registry(self.keyRoot, join(self.subKey, subKey), depth=self.depth + 1, index=i, maxIndex=self.subKeyNum) # 再帰の方がスッキリと書ける。と言うか再帰から変換したから
      # self.subKeys.append(reg)

  def setSubKey(self):
    stack = [self]
    while len(stack) > 0:
      key = stack.pop()
      for i, subKey in enumerate(key.subKeys):
        if isinstance(subKey, Registry):
          return
        reg = Registry(key.keyRoot, join(key.subKey, subKey), depth=key.depth + 1, index=i, maxIndex=key.subKeyNum, isRoot=False)  # 先頭がバックスラッシュだと開けないことがあるのでjoinを使う。winregのバグか?
        key.subKeys[i] = reg
        stack.append(reg)

  def getKeyString(self):
    return f"{Entry.get(self.keyRoot, '')}\\{self.subKey}"

  def searchSelf(self, string, result=None):
    if result is None:
      result = set()
    pattern = Registry.getCompiled(string)
    self.searchKey(pattern, result)
    self.searchValue(pattern, result)
    return result

  @staticmethod
  def search(registry, string, result=None):
    if result is None:
      result = set()
    registry.searchSelf(string, result)
    if registry in result:
      return result

    stack = registry.subKeys[::-1]
    while len(stack) > 0:
      key = stack.pop()
      key.searchSelf(string, result)
      stack += key.subKeys[::-1]
    return result

  @staticmethod
  def getCompiled(pattern):
    if isinstance(pattern, re.Pattern):
      return pattern
    return re.compile(pattern)

  def searchKey(self, search, result):
    if self in result:
      return
    pattern = Registry.getCompiled(search)
    key = self.getKeyString()
    self.reSearch(pattern, key, result)

  def searchValue(self, search, result):
    if self in result:
      return
    pattern = Registry.getCompiled(search)
    for value in self.values:
      self.reSearch(pattern, value.name, result)
      self.reSearch(pattern, value.data, result)
      # self.reSearch(pattern, value.type, result)

  def reSearch(self, pattern, string, result):
    if not isinstance(string, str):
      return
    match = pattern.search(string)
    if match:
      result.add(self)


class RegistryString():
  NoPrint = (winreg.REG_BINARY,)  # dataがREG_BINARYの場合、表示させない
  setIndent = True
  setIndex = False
  setFullPath = True

  def __new__(cls):
    raise TypeError(f"{cls.__name__} cannot be instantiated")

  @staticmethod
  def getKeyString(registry, setFullPath):
    if setFullPath:
      return f"{Entry.get(registry.keyRoot, '')}\\{registry.subKey}"
    return f"{os.path.basename(registry.subKey)}"  #

  @classmethod
  def getValuesString(cls, registry):
    return [cls.getValueString(registry, i) for i in range(registry.valueNum)]

  @classmethod
  def getValueString(cls, registry, i):
    indent = cls.getIndent(registry.depth)
    index = cls.getIndex("V", i, registry.valueNum)
    value = registry.values[i]
    if any(value.type == x for x in RegistryString.NoPrint):
      return f"  {indent}{index}\"{value.name}\"({Type.get(value.type)})"
    return f"  {indent}{index}\"{value.name}\"=\"{value.data}\"({Type.get(value.type)})"

  @classmethod
  def getTreeString(cls, registry):
    string = cls.getInfoString(registry)
    stack = registry.subKeys[::-1]
    while len(stack) > 0:
      key = stack.pop()
      string += cls.getInfoString(key)
      stack += key.subKeys[::-1]
    return string

  @classmethod
  def getQueryString(cls, registry, setFullPath):
    indent = cls.getIndent(registry.depth)
    index = cls.getIndex("K", registry.index, registry.maxIndex)
    return f"{indent}{index}{cls.getKeyString(registry, setFullPath)}: {registry.subKeyNum}, {registry.valueNum}: ({registry.modifiedDate})\n"

  @classmethod
  def getInfoString(cls, registry, showSubKey=False):
    string = cls.getQueryString(registry, cls.setFullPath)
    values = cls.getValuesString(registry)
    for value in values:
      string += f"{value}\n"
    if showSubKey:
      for subKey in registry.subKeys:
        string += f"  {cls.getQueryString(subKey, False)}"
    return string

  @classmethod
  def getIndent(cls, depth):
    return "  " * depth if cls.setIndent else ""

  @classmethod
  def getIndex(cls, t, i, n):
    return f"{t}{getZeroFillString(i, n)}: " if cls.setIndex else ""

  @classmethod
  def setOption(cls, setIndent, setIndex, setFullPath):
    cls.setIndent = setIndent
    cls.setIndex = setIndex
    cls.setFullPath = setFullPath


# getKeyInfo(winreg.HKEY_CLASSES_ROOT, "AppID\\Acrobat.exe")
# getKeyInfo(winreg.HKEY_CLASSES_ROOT, "Application.Reference")

# # reg = Registry(winreg.HKEY_CLASSES_ROOT, "AppID")
# reg = Registry(winreg.HKEY_CLASSES_ROOT, "AppID\\Acrobat.exe")
# print(reg)
# print(reg.getValuesString())
# print(reg.subKeys)

# with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, r"\*\OpenWithProgids", access=winreg.KEY_READ | winreg.KEY_WOW64_32KEY) as key:
#   info = winreg.QueryInfoKey(key)
#   print(info)

# reg = Registry(winreg.HKEY_CLASSES_ROOT, "")
# reg = Registry(winreg.HKEY_CLASSES_ROOT, "Local Settings")
reg = Registry(winreg.HKEY_CLASSES_ROOT, "Local Settings\MrtCache")
# reg.ff()
# reg = Registry(winreg.HKEY_CLASSES_ROOT, r"*\OpenWithList")
# # print(reg)
# # print(reg.getInfoString(showSubKey=True))
# # print(reg.getTreeString(setFullPath=False))
# printForWindows(reg.getTreeString())
# reg.setPrintOption(True, True, True)
# print(reg.getTreeString())

RegistryString.setOption(True, True, True)
# printForWindows(RegistryString.getKeyString(reg, True))
# printForWindows(RegistryString.getInfoString(reg))
# printForWindows(RegistryString.getValuesString(reg))
printForWindows(RegistryString.getTreeString(reg))
# printForWindows(reg.getTreeString())

#
# result = Registry.search(reg, "IsShortcut")
# result = Registry.search(reg, "{e82a2d71-5b2f-43a0-97b8-81be15854de8}")
result = Registry.search(reg, "Webp")
RegistryString.setIndent = False
for i in result:
  printForWindows(RegistryString.getInfoString(i, True))
