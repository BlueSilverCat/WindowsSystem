import time
import datetime
import re

Iso8601Basic = "%Y%m%dT%H%M%S%z"
Iso8601Extended = "%Y-%m-%dT%H:%M:%S"  # [+-]hh:mm


def getNowTime():
  # return datetime.datetime.now().strftime("%H:%M:%S")
  return time.strftime("%H:%M:%S")


def getDateTime(type="basic"):
  if type == "basic":
    return time.strftime(Iso8601Basic)
  elif type == "extended":
    reTimeZone = re.compile("([+-]\\d\\d)(\\d\\d)")
    timeZone = reTimeZone.sub("\\1:\\2", time.strftime("%z"))
    return time.strftime(f"{Iso8601Extended}{timeZone}")


def epochToStr(e, type="basic"):
  if type == "basic":
    return time.strftime(Iso8601Basic, time.localtime(e))  # gmtime()を使う場合は、tm_gmtoffを加算する
  elif type == "extended":
    timeStr = time.strftime(Iso8601Extended, time.localtime(e))
    reTimeZone = re.compile("([+-]\\d\\d)(\\d\\d)$")
    timeZone = time.strftime("%z", time.localtime(e))
    timeZone = reTimeZone.sub("\\1:\\2", timeZone)
    return timeStr + timeZone


def strToEpoch(str, type="basic"):
  if type == "basic":
    return time.mktime(time.strptime(str, Iso8601Basic))
  elif type == "extended":
    reTimeZone = re.compile("(.+)([+-]\\d\\d):(\\d\\d)$")
    timeStr = reTimeZone.sub("\\1\\2\\3", str)
    return time.mktime(time.strptime(timeStr, f"{Iso8601Extended}%z"))


def timeToLocalTime(t):
  return time.strftime("%H:%M:%S", time.localtime(t))


def getNextHourWait():
  wait = (60 - datetime.datetime.now().minute) * 60 + 30
  return time.time() + wait


def timedeltaToDict(td, showWeeks=False):
  result = {}
  if showWeeks:
    result["weeks"], result["days"] = divmod(td.days, 7)
  else:
    result["days"] = td.days
  result["hours"], work = divmod(td.seconds, 60 * 60)
  result["minutes"], result["seconds"] = divmod(work, 60)
  result["milliseconds"], result["microseconds"] = divmod(td.microseconds, 1000)
  result["totalSeconds"] = td.total_seconds()
  return result


def getTimeString(td, showWeeks=False):
  result = timedeltaToDict(td, showWeeks)
  string = f"{result['hours']:02}:{result['minutes']:02}:{result['seconds']:02}"
  work = ""
  if showWeeks and result["weeks"] > 0:
    work = f"{result['weeks']} weeks, "
  if result["days"] > 0:
    work += f"{result['days']} days, "
  string = work + string

  string += f".{result['milliseconds']:03}" if result["milliseconds"] > 0 else ""
  if result["microseconds"] > 0:
    if result["milliseconds"] > 0:
      string += f"{result['microseconds']:03}"
    else:
      string += f".000{result['microseconds']:03}"

  return string
