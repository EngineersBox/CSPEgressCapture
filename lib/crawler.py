from bs4 import BeautifulSoup
from urllib.parse import urlsplit
from collections import deque
import requests, requests.exceptions, sys, asyncio, uuid
from urlstate import URLState
from crawlerconfig import CrawlerConfig
from reporter import Reporter

class ICrawlerBase:

    def __init__(self, config: CrawlerConfig):
        self.url_state = URLState()
        self.config = config

    def extractResolveLinks(self, response,  url):
        # extract base url to resolve relative links
        parts = urlsplit(url)
        base = "{0.netloc}".format(parts)
        strip_base = base.replace("www.", "")
        base_url = "{0.scheme}://{0.netloc}".format(parts)
        path = url[:url.rfind('/')+1] if '/' in parts.path else url

        # create a beutiful soup for the html document
        soup = BeautifulSoup(response.text, "lxml")

        for link in soup.find_all('a'):
            # extract link url from the anchor
            anchor = link.attrs["href"] if "href" in link.attrs else ''

            if anchor.startswith('/'):
                local_link = base_url + anchor
                self.url_state.local_urls.add(local_link)
            elif strip_base in anchor:
                self.url_state.local_urls.add(anchor)
            elif not anchor.startswith('http'):
                local_link = path + anchor
                self.url_state.local_urls.add(local_link)
            else:
                self.url_state.foreign_urls.add(anchor)

        for i in self.url_state.local_urls:
            if not i in self.url_state.new_urls and not i in self.url_state.processed_urls:
                self.url_state.new_urls.append(i)
        return self.url_state

    def crawlUrlTask(self):
        # a queue of urls to be crawled
        self.url_state = URLState(deque([self.config.domain]))
        # move next url from the queue to the set of processed urls
        url = self.url_state.new_urls.popleft()
        self.url_state.processed_urls.add(url)
        is_broken = False
        # get url's content
        print("Processing %s" % url)
        response = None
        try:
            response = requests.head(url)
        except (requests.exceptions.MissingSchema, requests.exceptions.ConnectionError, requests.exceptions.InvalidURL, requests.exceptions.InvalidSchema):
            # add broken urls to it's own set, then continue
            self.url_state.broken_urls.add(url)
            return self.url_state

        if 'content-type' in response.headers:
            content_type = response.headers['content-type']
            if not 'text/html' in content_type:
                return self.url_state

        try:
            response = requests.get(url)
        except (requests.exceptions.MissingSchema, requests.exceptions.ConnectionError, requests.exceptions.InvalidURL, requests.exceptions.InvalidSchema):
            # add broken urls to it's own set, then continue
            self.url_state.broken_urls.add(url)
            return self.url_state

        # extract base url to resolve relative links
        self.url_state = self.extractResolveLinks(
            self.url_state, response, url)
        return self.url_state

    def reportResults(self):
        reporter = Reporter(self.url_state, self.config)
        if self.config.mute is False:
            if self.config.ofile is not None:
                return reporter.reportToFile()
            else:
                return reporter.report()
        else:
            if self.config.ofile is not None:
                return reporter.muteReportToFile()
            else:
                return reporter.muteReport()

class AsyncCrawler(ICrawlerBase):

    def __init__(self, config: CrawlerConfig):
        super(self, config)
        self.tasks_url_state = {}

    async def crawl(self):
        task_id = str(uuid.uuid4())
        self.tasks_url_state[task_id] = self.crawlUrlTask(self.config.domain)
        next_urls = self.tasks_url_state[task_id].new_urls
        try:
            results = await asyncio.gather(*(self.crawlUrlTask(next_domain) for next_domain in next_urls))
            for res in results:
                self.tasks_url_state[str(uuid.uuid4())] = res
        except KeyboardInterrupt:
            super.reportResponse()

class Crawler(ICrawlerBase):

    def __init__(self, config: CrawlerConfig):
        super(self, config)

    def crawl(self):
        # a queue of urls to be crawled
        self.url_state.new_urls = deque([self.config.domain])
        try:
            # process urls one by one until we exhaust the queue
            while len(self.url_state.new_urls):
                # move next url from the queue to the set of processed urls
                url = self.url_state.new_urls.popleft()
                res = self.crawlUrlTask(url)
                self.url_state.processed_urls = set(self.url_state.processed_urls.union(res.processed_urls))
                self.url_state.broken_urls = set(self.url_state.processed_urls.union(res.broken_urls))
                self.url_state.new_urls = set(self.url_state.processed_urls.union(res.new_urls))
                self.url_state.foreign_urls = set(self.url_state.processed_urls.union(res.foreign_urls))
                self.url_state.local_urls = set(self.url_state.processed_urls.union(res.local_urls))

            print()
            self.reportResults()
        
        except KeyboardInterrupt:
            self.reportResults()
            sys.exit()

class LimitCrawler(ICrawlerBase):

    def __init__(self, config: CrawlerConfig):
        super(self, config)

    def crawlLimitUrlTask(self):
        # move next url from the queue to the set of processed urls
        url = self.url_state.new_urls.popleft()
        self.url_state.processed_urls.add(url)
        # get url's content
        print("Processing %s" % url)
        try:
            response = requests.get(url)
        except (requests.exceptions.MissingSchema, requests.exceptions.ConnectionError, requests.exceptions.InvalidURL, requests.exceptions.InvalidSchema):
            # add broken urls to it's own set, then continue
            self.url_state.broken_urls.add(url)
            return

        # extract base url to resolve relative links
        parts = urlsplit(url)
        base = "{0.netloc}".format(parts)
        strip_base = base.replace("www.", "")
        base_url = "{0.scheme}://{0.netloc}".format(parts)
        path = url[:url.rfind('/')+1] if '/' in parts.path else url

        # create a beutiful soup for the html document
        soup = BeautifulSoup(response.text, "lxml")

        for link in soup.find_all('a'):
            # extract link url from the anchor
            anchor = link.attrs["href"] if "href" in link.attrs else ''
            print(anchor)

            if self.limit in anchor:
                self.url_state.limit_urls.add(anchor)
            else:
                pass

        for i in self.url_state.limit_urls:
            if not i in self.url_state.new_urls and not i in self.url_state.processed_urls:
                self.url_state.new_urls.append(i)

    def reportLimitResults(self):
        reporter = Reporter(self.url_state, self.config)
        if self.config.mute is False:
            if self.config.ofile is not None:
                return reporter.limitReportToFile()
            else:
                return reporter.limitReport()
        else:
            if self.config.ofile is not None:
                return reporter.limitMuteReportToFile()
            else:
                return reporter.limitMuteReport()

    def crawl(self):
        try:
            # process urls one by one until we exhaust the queue
            while len(self.url_state.new_urls):
                self.crawlLimitUrlTask()

            print()
            self.reportLimitResults(self.config.ofile, self.config.mute)

        except KeyboardInterrupt:
            sys.exit()
