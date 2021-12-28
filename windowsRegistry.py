import winreg
import time
import datetime
import collections
import os.path
import re
import sys
import argparse

# 手作業でなくてzipで処理しても良い
Entry = {
  winreg.HKEY_CLASSES_ROOT: "HKEY_CLASSES_ROOT",
  winreg.HKEY_CURRENT_USER: "HKEY_CURRENT_USER",
  winreg.HKEY_LOCAL_MACHINE: "HKEY_LOCAL_MACHINE",
  winreg.HKEY_USERS: "HKEY_USERS",
  winreg.HKEY_PERFORMANCE_DATA: "HKEY_PERFORMANCE_DATA",
  winreg.HKEY_CURRENT_CONFIG: "HKEY_CURRENT_CONFIG",
}

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


def keyFromValue(d, value, unique=True):
  result = [k for k, v in d.items() if v == value]
  if len(result) == 0:
    return None
  return result[0] if unique else result


def getZeroFillString(i, num=10):
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

  def __init__(self, key, subKey, depth=0, index=0, maxIndex=0, parentKey=None):
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
    self.parentKey = parentKey
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
    if self.parentKey is None:  # ここの仕組みが気に入らない
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
        reg = Registry(key.keyRoot, join(key.subKey, subKey), depth=key.depth + 1, index=i, maxIndex=key.subKeyNum, parentKey=key)  # 先頭がバックスラッシュだと開けないことがあるのでjoinを使う。winregのバグか?
        key.subKeys[i] = reg
        stack.append(reg)

  def getKeyString(self):
    return f"{Entry.get(self.keyRoot, '')}\\{self.subKey}"

  def searchSelf(self, string, result=None):
    if result is None:
      result = []
    pattern = Registry.getCompiled(string)
    self.searchKey(pattern, result)
    self.searchValue(pattern, result)
    return result

  @staticmethod
  def search(registry, string, result=None):
    if result is None:
      result = []
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
      if self not in result:
        result.append(self)


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
  def getValuesString(cls, registry, depth):
    return [cls.getValueString(registry, i, depth) for i in range(registry.valueNum)]

  @classmethod
  def getValueString(cls, registry, i, depth):
    indent = cls.getIndent(depth)
    index = cls.getIndex("V", i, registry.valueNum)
    value = registry.values[i]
    if any(value.type == x for x in RegistryString.NoPrint):
      return f"  {indent}{index}\"{value.name}\" ({Type.get(value.type)})"
    return f"  {indent}{index}\"{value.name}\" = \"{value.data}\" ({Type.get(value.type)})"

  @classmethod
  def getTreeString(cls, registry):
    string = cls.getInfoString(registry, False)
    stack = registry.subKeys[::-1]
    while len(stack) > 0:
      key = stack.pop()
      string += cls.getInfoString(key, False)
      stack += key.subKeys[::-1]
    return string

  @classmethod
  def getQueryString(cls, registry, depth, setFullPath):
    indent = cls.getIndent(depth)
    index = cls.getIndex("K", registry.index, registry.maxIndex)
    return f"{indent}{index}{cls.getKeyString(registry, setFullPath)} ({registry.subKeyNum}, {registry.valueNum}, {registry.modifiedDate})\n"

  @classmethod
  def getInfoString(cls, registry, showSubKey=True):
    depth = registry.depth if cls.setIndent else 0
    string = cls.getQueryString(registry, depth, cls.setFullPath)
    values = cls.getValuesString(registry, depth)
    for value in values:
      string += f"{value}\n"
    if showSubKey:
      for subKey in registry.subKeys:
        string += f"{cls.getQueryString(subKey, depth + 1, False)}"
    return string

  @classmethod
  def getIndent(cls, depth):
    return "  " * depth

  @classmethod
  def getIndex(cls, t, i, n):
    return f"{t}{getZeroFillString(i, n)}: " if cls.setIndex else ""

  @classmethod
  def setOption(cls, setIndent, setIndex, setFullPath):
    cls.setIndent = setIndent
    cls.setIndex = setIndex
    cls.setFullPath = setFullPath


def argumentParser():
  parser = argparse.ArgumentParser()
  parser.add_argument("key", help="レジストリキーを指定する")
  parser.add_argument("-o", "--outputPath", default="", help="出力先のパス。指定されなかったら標準出力へ出力する")
  parser.add_argument("-t", "--tree", action="store_true", help="階層構造を表示する。指定されなったらキーとそのサブキーのみ表示する。")
  parser.add_argument("-s", "--search", default="", help="検索文字列を正規表現で指定する")

  parser.add_argument("-ix", "--setIndex", action="store_true", help="インデックスを表示する")
  parser.add_argument("-it", "--setIndent", action="store_false", help="インデントを設定しない")
  parser.add_argument("-fp", "--setFullPath", action="store_false", help="絶対パスで表示しない")
  parser.add_argument("-a", "--showArgument", action="store_true", help="show arguments.")
  return parser.parse_args()


def getKey(key):
  reEntry = re.compile(r"\\?([^\\]+)(?:\\(.*))?")
  match = reEntry.search(key)
  if match is None:
    return None, None
  return keyFromValue(Entry, match.groups("")[0]), match.groups("")[1]


if __name__ == "__main__":
  args = argumentParser()
  if args.showArgument:
    print(args)

  keyRoot, subKey = getKey(args.key)

  print(f"\"{Entry.get(keyRoot, '')}\", \"{subKey}\"")
  if keyRoot is None:
    print(f"invalid key. {args.key}")
    sys.exit(1)

  reg = Registry(keyRoot, subKey)
  output = ""
  RegistryString.setOption(args.setIndent, args.setIndex, args.setFullPath)
  if args.tree:
    output = RegistryString.getTreeString(reg)
  else:
    output = RegistryString.getInfoString(reg)

  if args.search != "":
    # RegistryString.setOption(False, args.setIndex, args.setFullPath)
    result = Registry.search(reg, args.search)
    output += "\nsearch result:\n"
    for i in result:
      output += RegistryString.getInfoString(i)

  if args.outputPath != "":
    with open(args.outputPath, "w", encoding="utf-8") as file:
      file.write(output)
  else:
    printForWindows(output)
