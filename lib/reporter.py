from urlstate import URLState
from crawlerconfig import CrawlerConfig

LINE_STRING = "--------------------------------------------------------------------"

class Reporter:

    def __init__(self, url_state: URLState, config: CrawlerConfig):
        self.url_state = url_state
        self.config = config

    def limitReportToFile(self):
        with open(self.config.ofile, 'w') as f:
            print(
                LINE_STRING, file=f)
            print("All found URLs:", file=f)
            for i in self.url_state.processed_urls:
                print(i, file=f)
            print(
                LINE_STRING, file=f)
            print("All " + self.config.limit + "URLs:", file=f)
            for j in self.url_state.limit_urls:
                print(j, file=f)
            print(
                LINE_STRING, file=f)
            print("All broken URL's:", file=f)
            for z in self.url_state.broken_urls:
                print(z, file=f)


    def limitReport(self):
        print(LINE_STRING)
        print("All found URLs:")
        for i in self.url_state.processed_urls:
            print(i)
        print(LINE_STRING)
        print("All " + self.config.limit + " URLs:")
        for j in self.url_state.limit_urls:
            print(j)
        print(LINE_STRING)
        print("All broken URL's:")
        for z in self.url_state.broken_urls:
            print(z)


    def limitMuteReportToFile(self):
        with open(self.config.ofile, 'w') as f:
            print(
                LINE_STRING, file=f)
            print("All " + self.config.limit + " URLs:", file=f)
            for j in self.url_state.limit_urls:
                print(j, file=f)


    def limitMuteReport(self):
        print(LINE_STRING)
        print("All " + self.config.limit + "URLs:")
        for i in self.url_state.limit_urls:
            print(i)


    def reportToFile(self):
        with open(self.config.ofile, 'w') as f:
            print(
                LINE_STRING, file=f)
            print("All found URLs:", file=f)
            for i in self.url_state.processed_urls:
                print(i, file=f)
            print(
                LINE_STRING, file=f)
            print("All local URLs:", file=f)
            for j in self.url_state.local_urls:
                print(j, file=f)
            print(
                LINE_STRING, file=f)
            print("All foreign URLs:", file=f)
            for x in self.url_state.foreign_urls:
                print(x, file=f)
            print(LINE_STRING, file=f)
            print("All broken URL's:", file=f)
            for z in self.url_state.broken_urls:
                print(z, file=f)


    def report(self):
        print(LINE_STRING)
        print("All found URLs:")
        for i in self.url_state.processed_urls:
            print(i)
        print(LINE_STRING)
        print("All local URLs:")
        for j in self.url_state.local_urls:
            print(j)
        print(LINE_STRING)
        print("All foreign URLs:")
        for x in self.url_state.foreign_urls:
            print(x)
        print(LINE_STRING)
        print("All broken URL's:")
        for z in self.url_state.broken_urls:
            print(z)


    def muteReportToFile(self):
        with open(self.config.ofile, 'w') as f:
            print(
                LINE_STRING, file=f)
            print("All local URLs:", file=f)
            for j in self.url_state.local_urls:
                print(j, file=f)


    def muteReport(self):
        print(LINE_STRING)
        print("All local URLs:")
        for i in self.url_state.local_urls:
            print(i)
