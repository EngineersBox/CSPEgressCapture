import logging, re
from selenium import webdriver

CONTAINS_STR = ".*%s.*%s"

class ChromeDriver:

    def __init__(self, url):
        self.url = url

    def initWebDriver(self):
        self.capabilities = webdriver.DesiredCapabilities.CHROME.copy()
        self.capabilities["goog:loggingPrefs"] = {"browser": "ALL"}
        self.driver = webdriver.Chrome(desired_capabilities=self.capabilities)
        self.driver.get(self.url)

class LogEntryGrabber:

    def __init__(self, chrome_driver):
        self.chrome_driver = chrome_driver
        self.chrome_driver.initWebDriver()

    def slurpLogs(self):
        """get log entreies from selenium and add to python logger before returning"""
        loglevels = { "NOTSET":0 , "DEBUG":10 ,"INFO": 20 , "WARNING":30, "ERROR":40, "SEVERE":40, "CRITICAL":50}

        #initialise a logger
        browserlog = logging.getLogger("chrome")
        #get browser logs
        self.slurped_logs = self.chrome_driver.get_log("browser")
        for entry in slurped_logs:
            #convert broswer log to python log format
            rec = browserlog.makeRecord("%s.%s"%(browserlog.name,entry["source"]),loglevels.get(entry["level"]),".",0,entry["message"],None,None)
            rec.created = entry["timestamp"] /1000 # log using original timestamp.. us -> ms
            try:
                # Add browser log to python log
                browserlog.handle(rec)
            except:
                print(entry)
        #and return logs incase you want them
        return self.slurped_logs

class LogParser:

    def __init__(self, logs: list):
        self.setLogs(logs)
        self.matches = []

    def setLogs(self, logs: list):
        self.logs = logs

    def setCaptureRegex(self, regex):
        self.prog = re.compile(regex)

    def setCaptureRegexAsContains(self, substring, has_newline=False):
        escaped_substring = re.escape(substring)
        self.prog = re.compile(CONTAINS_STR.format(
            escaped_substring, "\n" if has_newline else ""))

    def matchLogs(self):
        self.matches = []
        for log in self.logs:
            self.matches.append(re.match(self.prog, log))

    def readLogsFromFile(self, ifile):
        with open(ifile, "r") as f:
            line = f.readline()
            while line != "":
                logs.append(line)
                line = f.readline()

    def writeMatchesToFile(self, ofile):
        with open(ofile, "w") as f:
            for match in self.matches:
                f.writelines(match.group(0))
