from lib.crawler import URLState, AsyncCrawler, Crawler, LimitCrawler, CrawlerConfig
from lib.logGrabber import ChromeDriver, LogEntryGrabber, LogParser
import argparse, sys, re

CSP_LOG_TAG = "content-security-policy"

class ProgArgHandler:

    def __init__(self, argv: list):
        self.addArgs(argv)

    def addArgs(self, argv):
        self.argv = argv

    def initParser(self):
        self.description = "Web crawler that pulls console logs and matches against a regex"
        self.parser = argparse.ArgumentParser(description=self.description)
        self.parser.add_argument('--domain', '-d', required=True,
                                help='domain name of website you want to map. i.e. "https://scrapethissite.com"')
        self.parser.add_argument('--ofile', '-o',
                                help='define output file to save results of stdout. i.e. "test.txt"')
        self.parser.add_argument('--limit', '-l',
                                help='limit search to the given domain instead of the domain derived from the URL. i.e: "github.com"')
        self.parser.add_argument('--mute', '-m', action="store_true",
                                help='output only the URLs of pages within the domain that are not broken')
        self.parser.add_argument('--asynchronous', 'a',
                                help='run crawler asynchronously at each link')

    def parse(self) -> CrawlerConfig:
        self.args = self.parser.parse_args()
        return CrawlerConfig(
            self.args.domain,
            self.args.ofile,
            self.args.limit,
            self.args.mute,
            self.args.asynchronous
        )

class ConsoleLogMatcher:

    def __init__(self, urls: set, to_match: str = CSP_LOG_TAG):
        self.to_match = to_match
        self.urls = urls
        self.logs = set()

    def getLogs(self):
        for url in self.urls:
            driver = ChromeDriver(url)
            grabber = LogEntryGrabber(driver)
            self.logs = self.logs.union(grabber.slurpLogs())

    def findMatchingLogEntries(self) -> list:
        logParser = LogParser(self.logs)
        logParser.setCaptureRegexAsContains(self.to_match)
        logParser.matchLogs()
        return logParser.matches

def createCrawler(config: CrawlerConfig):
    if config.limit is None:
        if config.asynchronous is None:
            return Crawler(config)
        else:
            return AsyncCrawler(config)
    else:
        return LimitCrawler(config)

def collectUrls(config: CrawlerConfig, crawler, include_foreign: bool = False) -> set:
    urls = set()
    if config.asynchronous is not None:
        urls = urls.union(crawler.url_state.processed_urls)
        urls = urls.union(crawler.url_state.local_urls)
        if (include_foreign):
            urls = urls.union(crawler.url_state.foreign_urls)
        urls = urls.difference(urls.broken_urls)
    else:
        for vals in crawler.tasks_url_state.values():
            urls = urls.union(vals.processed_urls)
            urls = urls.union(vals.local_urls)
            if (include_foreign):
                urls = urls.union(vals.foreign_urls)
            urls = urls.difference(vals.broken_urls)
    return urls

if __name__ == "__main__":
    argHandler = ProgArgHandler()
    argHandler.addArgs(sys.argv[1:])
    argHandler.initParser()
    crawlerConfig = argHandler.parse()

    crawler = createCrawler(crawlerConfig)
    crawler.crawl()

    urls = collectUrls(crawlerConfig, crawler)

    logMatcher = ConsoleLogMatcher(urls, CSP_LOG_TAG)
    logMatcher.getLogs()
    logEntries = logMatcher.findMatchingLogEntries()
    
    for entry in logEntries:
        print(entry)
